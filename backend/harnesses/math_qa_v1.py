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
    trailing punctuation. Numeric answers compare after normalization.
    """
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = s.rstrip(".!?,;:")
    return s


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
        correct = _normalize_answer(actual) == _normalize_answer(expected)
        if correct:
            correct_count += 1
        per_sample.append({
            "question": question,
            "expected_answer": expected,
            "actual_answer": actual,
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
