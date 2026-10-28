"""TB-US-057 Phase A: first-run seeder for the math-example agent.

On fresh install (or any boot where the math-example agent doesn't
exist), this seeder:

1. Creates the ``math-example`` agent via `AgentManager`
2. Loads the GSM8K-derived training set as ``training_set_versions.v1``
   (released + promoted)
3. Loads the RAG seed corpus as ``rag_versions.v1`` (released +
   promoted; chunk_count = number of markdown files, nominal — real
   Chroma ingestion lands with the chat-path rewiring work)
4. Loads the system prompt as ``prompt_versions.v1`` (released +
   promoted)
5. Loads the ``math_qa_v1`` harness as ``harness_versions.v1``
   (released; harnesses don't promote per TB-US-043 Q5)
6. Creates **three draft experiments** matching TB-US-057 Phase B's
   sequence (operator runs each manually via POST /experiments/{id}/run):

   - E1: bare Llama 3.1 8B — baseline (no RAG, no adapter)
   - E2: + adapter (adapter_version_id left null until operator
     registers the trained adapter)
   - E3: + RAG on top of adapter

**Idempotent:** if the ``math-example`` agent already exists the
seeder is a no-op (operator deletions respected).

**Opt-out:** set env var ``TB_SKIP_FIRST_RUN_SEED=1`` to disable
seeding entirely.

**Failure recovery:** writes a flag file
``logs/first-run-seeder.failed`` on exceptions so repeated boots
don't retry a broken seed. Delete the flag to re-attempt.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RAG_SEED_DIR = REPO_ROOT / "rag-seeds" / "math-example-v1"
TRAINING_SET_PATH = REPO_ROOT / "training-sets" / "math-example-v1.jsonl"
EVAL_DATASET_PATH = REPO_ROOT / "backend" / "harnesses" / "data" / "math_eval_200.jsonl"
SYSTEM_PROMPT_PATH = RAG_SEED_DIR / "system-prompt.txt"
FAILURE_FLAG = REPO_ROOT / "logs" / "first-run-seeder.failed"

AGENT_NAME = "math-example"
AGENT_DISPLAY_NAME = "Math example"
AGENT_DESCRIPTION = (
    "Grade-school math word problems from GSM8K. Shipped with TB as a "
    "pedagogical demonstration (TB-US-057) of the three-stage workflow: "
    "bare base model baseline → +adapter → +RAG on top. Measured via "
    "the math_qa_v1 harness against 200 held-out GSM8K test questions."
)


def seed_math_example() -> Dict[str, object]:
    """Idempotent seeder. Returns a result dict for startup logging."""

    if os.getenv("TB_SKIP_FIRST_RUN_SEED") == "1":
        return {"seeded": False, "reason": "TB_SKIP_FIRST_RUN_SEED=1"}

    if FAILURE_FLAG.exists():
        return {"seeded": False, "reason": f"failure flag present at {FAILURE_FLAG}"}

    # Lazy imports to avoid cycles with main.py.
    from api.agent_manager import AgentManager
    from api.training_set_version_manager import TrainingSetVersionManager
    from api.rag_version_manager import RAGVersionManager
    from api.prompt_version_manager import PromptVersionManager
    from api.harness_version_manager import HarnessVersionManager
    from api.experiment_manager import ExperimentManager

    agents = AgentManager()
    existing = agents.get_by_name(AGENT_NAME)
    if existing:
        return {
            "seeded": False,
            "reason": f"agent {AGENT_NAME!r} already exists (id={existing['agent_id']})",
        }

    # Minimum artifacts to seed: training set JSONL + RAG seed dir +
    # system prompt. Fail soft if any is missing — the operator may be
    # on an install that doesn't ship these.
    missing: list = []
    if not TRAINING_SET_PATH.exists():
        missing.append(str(TRAINING_SET_PATH))
    if not EVAL_DATASET_PATH.exists():
        missing.append(str(EVAL_DATASET_PATH))
    if not SYSTEM_PROMPT_PATH.exists():
        missing.append(str(SYSTEM_PROMPT_PATH))
    if missing:
        return {"seeded": False, "reason": f"missing artifacts: {missing}"}

    try:
        return _do_seed(agents)
    except Exception as e:
        log.exception("first_run_seeder failed")
        FAILURE_FLAG.parent.mkdir(parents=True, exist_ok=True)
        FAILURE_FLAG.write_text(
            f"first_run_seeder failed at {datetime.now().isoformat()}\n{e}\n",
            encoding="utf-8",
        )
        return {"seeded": False, "reason": f"exception; flag written: {e}"}


def _do_seed(agents) -> Dict[str, object]:
    from api.training_set_version_manager import TrainingSetVersionManager
    from api.rag_version_manager import RAGVersionManager
    from api.prompt_version_manager import PromptVersionManager
    from api.harness_version_manager import HarnessVersionManager
    from api.experiment_manager import ExperimentManager

    # 1. Create agent.
    agent = agents.create_agent(
        name=AGENT_NAME,
        display_name=AGENT_DISPLAY_NAME,
        description=AGENT_DESCRIPTION,
    )
    agent_id = agent["agent_id"]

    # 2. Training set v1.
    ts_mgr = TrainingSetVersionManager()
    samples = _load_jsonl(TRAINING_SET_PATH)
    ts_row = ts_mgr.create_draft_with_samples(
        agent_id=agent_id, samples=samples, created_by="seeder",
    )
    ts_mgr.release(ts_row["version_id"])
    ts_mgr.promote(ts_row["version_id"], promoted_by="seeder")

    # 3. RAG v1 — manifest-level only. Chat-path rewiring to actually
    # query this collection is a future story (TB-US-053 scope decision).
    # We record the manifest + mark released+promoted so the experiment
    # row has a valid rag_version_id to pin.
    rag_mgr = RAGVersionManager()
    rag_docs = _build_rag_manifest()
    rag_row = rag_mgr.create_draft_version(agent_id=agent_id, created_by="seeder")
    rag_row = rag_mgr.ingest_docs(rag_row["version_id"], rag_docs)
    rag_mgr.release(rag_row["version_id"])
    rag_mgr.promote(rag_row["version_id"], promoted_by="seeder")

    # 4. Prompt v1.
    prompt_mgr = PromptVersionManager()
    prompt_text = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    prompt_row = prompt_mgr.create_draft_text(
        agent_id=agent_id, text=prompt_text, created_by="seeder",
    )
    prompt_mgr.release(prompt_row["version_id"])
    prompt_mgr.promote(prompt_row["version_id"], promoted_by="seeder")

    # 5. Harness v1 — points at math_qa_v1 + the 200-eval JSONL.
    harness_mgr = HarnessVersionManager()
    harness_def = {
        "module": "harnesses.math_qa_v1",
        "config": {
            "dataset_path": str(EVAL_DATASET_PATH),
            "metric": "accuracy",
            "n_samples": 200,
        },
    }
    harness_row = harness_mgr.create_draft_definition(
        agent_id=agent_id, definition=harness_def, created_by="seeder",
    )
    harness_mgr.release(harness_row["version_id"])

    # 6. Three draft experiments. Adapter_version_id left null —
    # operator populates it after Phase B training completes.
    exp_mgr = ExperimentManager()
    exp_e1 = exp_mgr.create_experiment(
        agent_id=agent_id,
        label="math-example-e1-bare-llama-3.1-8b",
        created_by="seeder",
        system_prompt_version_id=prompt_row["version_id"],
        rag_version_id=None,          # E1: no RAG
        llm_identifier="meta-llama/Meta-Llama-3.1-8B",
        adapter_version_id=None,      # E1: no adapter
        harness_version_id=harness_row["version_id"],
    )
    exp_e2 = exp_mgr.create_experiment(
        agent_id=agent_id,
        label="math-example-e2-plus-adapter",
        created_by="seeder",
        system_prompt_version_id=prompt_row["version_id"],
        rag_version_id=None,          # E2: no RAG, adapter only
        llm_identifier="meta-llama/Meta-Llama-3.1-8B",
        adapter_version_id=None,      # operator will set after Phase B training
        harness_version_id=harness_row["version_id"],
        parent_experiment_id=exp_e1["experiment_id"],
    )
    exp_e3 = exp_mgr.create_experiment(
        agent_id=agent_id,
        label="math-example-e3-plus-rag",
        created_by="seeder",
        system_prompt_version_id=prompt_row["version_id"],
        rag_version_id=rag_row["version_id"],   # E3: RAG on top of adapter
        llm_identifier="meta-llama/Meta-Llama-3.1-8B",
        adapter_version_id=None,                 # operator will set
        harness_version_id=harness_row["version_id"],
        parent_experiment_id=exp_e2["experiment_id"],
    )

    return {
        "seeded": True,
        "agent_id": agent_id,
        "training_set_version_id": ts_row["version_id"],
        "training_set_samples": ts_row.get("sample_count"),
        "rag_version_id": rag_row["version_id"],
        "rag_chunk_count": rag_row.get("chunk_count"),
        "prompt_version_id": prompt_row["version_id"],
        "harness_version_id": harness_row["version_id"],
        "experiments": [
            {"id": exp_e1["experiment_id"], "label": exp_e1["label"]},
            {"id": exp_e2["experiment_id"], "label": exp_e2["label"]},
            {"id": exp_e3["experiment_id"], "label": exp_e3["label"]},
        ],
    }


def _load_jsonl(path: Path) -> list:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _build_rag_manifest() -> list:
    """Enumerate the markdown files in the RAG seed dir and build a
    manifest for :meth:`RAGVersionManager.ingest_docs`. Chunk count is
    nominal (1 per file) since actual Chroma ingestion is TB-US-053
    deferred.
    """
    manifest = []
    for p in sorted(RAG_SEED_DIR.glob("*.md")):
        if p.name == "LICENSES.md":
            continue
        text = p.read_text(encoding="utf-8")
        # Nominal token count: ~1 token per 4 chars (English heuristic).
        manifest.append({
            "source_path": f"rag-seeds/math-example-v1/{p.name}",
            "chunk_count": 1,
            "embedding_model": "all-MiniLM-L6-v2",
            "total_tokens": max(1, len(text) // 4),
        })
    return manifest
