"""TB-US-056 + TB-US-069: harness runner.

Loads an experiment, resolves its pinned (prompt, RAG, LLM, adapter)
version IDs into a concrete model stack, invokes the referenced
harness, and writes the result dict back to
``experiments.results_json``. Non-blocking: typically invoked via
FastAPI ``BackgroundTasks`` so chat traffic continues during long
harness runs.

TB-US-069 (2026-10-25) replaced the earlier global-``rag_system``
stub with per-experiment stack construction in
``_build_experiment_stack``:

- ``adapter_version_id`` → load the adapter dir via
  ``AutoPeftModelForCausalLM`` (base model pulled from the adapter's
  ``adapter_config.json``). If null, load the bare base named in
  ``experiments.llm_identifier``.
- ``rag_version_id`` → construct a :class:`VectorStore` against the
  version's Chroma collection. If null, no retrieval.
- ``system_prompt_version_id`` → read ``prompt_versions.content``
  and template-fill with ``{context}`` + ``{question}``.

Production ``/query`` is explicitly untouched (TB-US-067 scope).
Harness runs are serial per TB-US-064. Each run loads its own stack
from scratch (~1-2 min of model loading); VRAM is freed in
``run_experiment``'s ``finally`` block before the next run starts.
"""

from __future__ import annotations

import gc
import importlib
import json
import logging
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from api.experiment_manager import ExperimentManager, ExperimentError
from api.harness_version_manager import HarnessVersionManager
from api.adapter_version_manager import AdapterVersionManager
from api.rag_version_manager import RAGVersionManager
from api.prompt_version_manager import PromptVersionManager


log = logging.getLogger(__name__)

_experiments = ExperimentManager()
_harnesses = HarnessVersionManager()
_adapters = AdapterVersionManager()
_rags = RAGVersionManager()
_prompts = PromptVersionManager()


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _build_experiment_stack(experiment: Dict) -> Dict[str, Any]:
    """TB-US-069: construct the per-experiment inference stack.

    Returns a dict with:
    - ``model_fn(question: str) -> str`` — the harness-compatible
      callable
    - ``refs`` — dict of objects the caller holds for cleanup
      (model, tokenizer, pipeline, vector_store). Caller must
      ``del`` these + ``torch.cuda.empty_cache()`` after the harness
      finishes.
    - ``summary`` — brief dict of what got resolved; used for logging
    """
    # Lazy imports to avoid loading heavy ML libs at module import time.
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

    # Import constants from rag_system for generation params + import
    # VectorStore. These live in backend/rag/ which is on sys.path via
    # main.py's sys.path manipulation at startup.
    from rag.vector_store import VectorStore
    from rag.rag_system import (
        LLM_MAX_NEW_TOKENS,
        LLM_TEMPERATURE,
        LLM_TOP_P,
        LLM_TOP_K,
    )

    adapter_vid = experiment.get("adapter_version_id")
    rag_vid = experiment.get("rag_version_id")
    prompt_vid = experiment.get("system_prompt_version_id")
    llm_identifier = experiment.get("llm_identifier") or "meta-llama/Meta-Llama-3.1-8B-Instruct"

    # Resolve adapter files_path
    adapter_path = None
    if adapter_vid:
        row = _adapters.get_by_id(adapter_vid)
        if row is None:
            raise ExperimentError(f"adapter_version_id {adapter_vid} not found")
        rel = row["files_path"]
        adapter_path = str(REPO_ROOT / rel) if not os.path.isabs(rel) else rel
        if not os.path.exists(adapter_path):
            raise ExperimentError(f"Adapter files_path missing: {adapter_path}")

    # Resolve system prompt
    prompt_text = ""
    if prompt_vid:
        row = _prompts.get_by_id(prompt_vid)
        if row is None:
            raise ExperimentError(f"system_prompt_version_id {prompt_vid} not found")
        prompt_text = row.get("content") or ""

    # Resolve RAG collection + build VectorStore
    collection_name = None
    vector_store = None
    if rag_vid:
        row = _rags.get_by_id(rag_vid)
        if row is None:
            raise ExperimentError(f"rag_version_id {rag_vid} not found")
        collection_name = row.get("collection_name")
        if collection_name:
            try:
                vector_store = VectorStore(collection_name=collection_name)
            except Exception as e:
                log.warning(f"VectorStore construction failed for {collection_name}: {e}; experiment will run without retrieval")
                vector_store = None

    log.info(
        "[runner] experiment %s: base=%s adapter=%s rag=%s prompt_chars=%d",
        experiment["experiment_id"], llm_identifier,
        adapter_path or "(none)", collection_name or "(none)",
        len(prompt_text),
    )

    # Load model + tokenizer. If an adapter is pinned, go through the
    # PEFT loader which pulls the base from the adapter_config.json
    # declaration. Otherwise load the bare base.
    if adapter_path:
        from peft import AutoPeftModelForCausalLM
        log.info("[runner] loading PEFT adapter from %s (base pulled from adapter_config.json)", adapter_path)
        model = AutoPeftModelForCausalLM.from_pretrained(
            adapter_path,
            device_map="auto",
            torch_dtype=torch.float16,
        )
        tokenizer = AutoTokenizer.from_pretrained(adapter_path)
    else:
        log.info("[runner] loading bare base model %s", llm_identifier)
        model = AutoModelForCausalLM.from_pretrained(
            llm_identifier,
            device_map="auto",
            torch_dtype=torch.float16,
        )
        tokenizer = AutoTokenizer.from_pretrained(llm_identifier)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=LLM_MAX_NEW_TOKENS,
        temperature=LLM_TEMPERATURE,
        do_sample=True,
        top_p=LLM_TOP_P,
        top_k=LLM_TOP_K,
    )

    def _model_fn(question: str) -> str:
        # Retrieve context if RAG is pinned
        context = ""
        if vector_store is not None:
            try:
                results = vector_store.similarity_search(question, k=4)
                if isinstance(results, list):
                    # Each result may be a dict with 'document' / 'content' / 'text'
                    parts = []
                    for r in results:
                        if isinstance(r, dict):
                            parts.append(r.get("document") or r.get("content") or r.get("text") or "")
                        else:
                            parts.append(str(r))
                    context = "\n\n".join(p for p in parts if p)
            except Exception as e:
                log.warning(f"[runner] retrieval failed; proceeding without context: {e}")
                context = ""

        # Build the full prompt
        if prompt_text:
            # Prompt v1 template has {context} + {question} placeholders; honor them if present.
            if "{context}" in prompt_text and "{question}" in prompt_text:
                full_prompt = prompt_text.format(context=context, question=question)
            elif "{question}" in prompt_text:
                full_prompt = prompt_text.format(question=question)
            else:
                # Treat as system prompt; append the question
                if context:
                    full_prompt = f"{prompt_text}\n\nContext:\n{context}\n\nQuestion: {question}\n\nAnswer:"
                else:
                    full_prompt = f"{prompt_text}\n\nQuestion: {question}\n\nAnswer:"
        else:
            # No prompt text at all; just send the question
            full_prompt = question if not context else f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"

        # Generate
        try:
            output = pipe(full_prompt, return_full_text=False, num_return_sequences=1)
            if isinstance(output, list) and output:
                text = output[0].get("generated_text", "")
                return str(text).strip()
            return ""
        except Exception as e:
            return f"[model_fn generation error: {e}]"

    return {
        "model_fn": _model_fn,
        "refs": {
            "model": model,
            "tokenizer": tokenizer,
            "pipe": pipe,
            "vector_store": vector_store,
        },
        "summary": {
            "base": llm_identifier,
            "adapter": adapter_path,
            "rag_collection": collection_name,
            "prompt_chars": len(prompt_text),
        },
    }


def _free_stack(refs: Dict[str, Any]) -> None:
    """Release references + empty CUDA cache. Best-effort."""
    try:
        import torch
    except ImportError:
        torch = None  # type: ignore

    for k in list(refs.keys()):
        refs[k] = None
    gc.collect()
    if torch is not None and hasattr(torch, "cuda"):
        try:
            torch.cuda.empty_cache()
        except Exception:
            pass


def run_experiment(experiment_id: int) -> Dict:
    """Execute the harness for an experiment and save results.

    Preconditions: experiment is in state ``running`` (caller flipped
    it from ``draft`` before scheduling the background task). This
    function transitions ``running → completed`` with results on
    success, or ``running → archived`` with error details on failure.

    Returns the final experiment row.
    """
    experiment = _experiments.get_by_id(experiment_id)
    if experiment is None:
        raise ExperimentError(f"Experiment {experiment_id} not found")
    if experiment["state"] != "running":
        raise ExperimentError(
            f"run_experiment requires state=running; got {experiment['state']!r}"
        )

    stack: Optional[Dict[str, Any]] = None
    try:
        harness_row = _harnesses.get_by_id(experiment["harness_version_id"])
        if harness_row is None:
            raise ExperimentError(
                f"Harness version {experiment['harness_version_id']} not found"
            )
        definition = json.loads(harness_row["definition_json"])
        module_dotted = definition.get("module")
        config = definition.get("config", {})
        if not module_dotted:
            raise ExperimentError("Harness definition is missing 'module' key")

        harness_mod = importlib.import_module(module_dotted)
        if not hasattr(harness_mod, "run"):
            raise ExperimentError(
                f"Harness module {module_dotted} does not expose a run() function"
            )

        # TB-US-069: build the per-experiment stack
        stack = _build_experiment_stack(experiment)
        model_fn = stack["model_fn"]
        dataset_path = config.get("dataset_path")

        log.info(
            "harness_runner: experiment %s → module %s dataset %s stack %s",
            experiment_id, module_dotted, dataset_path, stack["summary"],
        )
        results = harness_mod.run(dataset_path=dataset_path, model_fn=model_fn, config=config)
        # Attach the stack summary to the results for audit
        results["_stack"] = stack["summary"]
        return _experiments.save_results(experiment_id, results)

    except Exception as e:
        # Capture failure as results and archive so the trace is preserved.
        error_results = {
            "metric": "error",
            "value": None,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }
        log.exception("harness_runner failed for experiment %s", experiment_id)
        try:
            _experiments.transition_state(
                experiment_id, "archived",
                extra={"results_json": json.dumps(error_results, sort_keys=True)},
            )
        except ExperimentError:
            pass
        raise
    finally:
        # TB-US-069: always free the per-experiment stack so the next
        # experiment starts with clean VRAM.
        if stack is not None:
            _free_stack(stack.get("refs", {}))
