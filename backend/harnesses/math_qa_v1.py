"""TB-US-056: starter harness — math Q&A accuracy.

The harness consumes a JSONL file of
``{"question": "...", "expected_answer": "...", "domain": "..."}``
records, invokes a model via the caller-supplied ``model_fn``, and
returns a result dict with accuracy + per-sample detail.

Called by :mod:`backend.api.harness_runner`. The signature is kept
narrow (dataset path + model_fn + config) so harnesses are easy to
write and the runner stays in control of model-stack construction.

Target: TB-US-047 Q3B staged-progression math-example (bare base
→ +RAG → +adapter). TB-US-057 ships the companion dataset
``backend/harnesses/data/math_eval_200.jsonl``.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


def _normalize_answer(s: str) -> str:
    """Case-fold, strip whitespace, collapse interior whitespace, strip
    trailing punctuation + numeric decoration ($ , %). Numeric answers
    compare after normalization.
    """
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = s.rstrip(".!?,;:")
    # Strip common numeric decoration before compare
    s = re.sub(r"[\$\%,]", "", s)
    return s


# TB-US-076 Option A: tolerant answer extraction.
# Model outputs are long CoT prose; the previous harness compared the
# ENTIRE output to the expected answer via _normalize_answer, which
# meant any multi-line output could not match a short numeric expected
# string. We now extract the model's final numeric answer via one of
# three priority rules + compare that to expected.
#
# Priority 1: #### N (standard GSM8K final-answer marker)
# Priority 2: "Final Answer: N" / "Answer: N" / "answer is N" patterns
# Priority 3: the LAST standalone number in the output
# Fallback: the entire output (previous behavior)
_HARNESS_FINAL_RE = re.compile(r"####\s*([-+]?\d[\d,.]*)")
_HARNESS_LABEL_RE = re.compile(
    r"(?:final\s*answer|answer\s*is|^answer)[:=]?\s*\$?([-+]?\d[\d,.]*)",
    re.IGNORECASE | re.MULTILINE,
)
_HARNESS_TRAILING_NUM_RE = re.compile(r"(?<![\d.])([-+]?\d+(?:\.\d+)?)")


def _extract_predicted_answer(output: str) -> str:
    """Pull the model's final numeric answer from a potentially long CoT
    output. Returns the extracted string (not normalized) or the original
    output if nothing matched (fallback).

    TB-US-076 Option A: added to make the harness tolerant of common
    final-answer formats produced by instruction-tuned models (notably
    "Final Answer: N") in addition to GSM8K's standard "#### N".
    """
    if not output:
        return ""
    # Priority 1: standard GSM8K marker
    m = _HARNESS_FINAL_RE.findall(output)
    if m:
        return m[-1]
    # Priority 2: common instruction-tuned labels
    m = _HARNESS_LABEL_RE.findall(output)
    if m:
        return m[-1]
    # Priority 3: last standalone number anywhere in the output
    m = _HARNESS_TRAILING_NUM_RE.findall(output)
    if m:
        return m[-1]
    # Fallback: original (previous behavior)
    return output


def _load_dataset(dataset_path: str) -> List[Dict]:
    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(
            f"math_qa_v1 dataset not found at {path}; "
            "ship the eval dataset via TB-US-057 or point at your own JSONL"
        )
    samples: List[Dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            samples.append(json.loads(line))
    return samples


def run(
    dataset_path: str,
    model_fn: Callable[[str], str],
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Evaluate ``model_fn`` on the dataset at ``dataset_path``.

    Returns::

        {
            "metric": "accuracy",
            "value": 0.72,
            "n_samples": 200,
            "duration_seconds": 142,
            "per_sample": [
                {"question": "...", "expected": "...",
                 "actual": "...", "correct": True},
                ...
            ],
            "ran_at": "2026-10-21T...Z",
        }
    """
    config = config or {}
    samples = _load_dataset(dataset_path)

    # Optional cap for development / smoke tests.
    n_cap = config.get("n_samples")
    if n_cap and isinstance(n_cap, int) and n_cap > 0:
        samples = samples[:n_cap]

    started = time.time()
    per_sample: List[Dict[str, Any]] = []
    correct_count = 0
    for sample in samples:
        question = sample.get("question", "")
        expected = sample.get("expected_answer", "")
        try:
            actual = model_fn(question)
        except Exception as e:   # harness must not crash the runner
            actual = f"[model_fn error: {e}]"
        # TB-US-076 Option A: extract predicted answer from CoT output before compare
        predicted = _extract_predicted_answer(actual)
        correct = _normalize_answer(predicted) == _normalize_answer(expected)
        if correct:
            correct_count += 1
        per_sample.append({
            "question": question,
            "expected_answer": expected,
            "actual_answer": actual,
            "predicted_answer": predicted,     # TB-US-076: extracted answer for debuggability
            "correct": correct,
            "domain": sample.get("domain"),
        })

    n = len(samples)
    accuracy = (correct_count / n) if n else 0.0

    return {
        "metric": "accuracy",
        "value": accuracy,
        "n_samples": n,
        "correct_count": correct_count,
        "duration_seconds": round(time.time() - started, 2),
        "per_sample": per_sample,
        "ran_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
