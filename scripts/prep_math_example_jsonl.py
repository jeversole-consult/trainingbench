#!/usr/bin/env python3
"""TB-US-057 Phase A: prep math_eval_200.jsonl + math-example-v1.jsonl from GSM8K.

GSM8K answers include <<a=b>> inline computations and a `#### N` final marker.
This script:
- Picks 200 test examples → backend/harnesses/data/math_eval_200.jsonl
  (format: {question, expected_answer, domain} — compatible with
   backend/harnesses/math_qa_v1.py)
- Picks 500 train examples → training-sets/math-example-v1.jsonl
  (format: {sample_id, question, answer} — full CoT for adapter training)
- Overlap-safe: GSM8K train and test are disjoint sets.
- Deterministic: fixed random seed so the eval set is stable across runs.

See TB-US-057 Phase A completion notes for full rationale.
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

from datasets import load_from_disk


REPO = Path(__file__).resolve().parent.parent
GSM8K_PATH = REPO / "datasets" / "math" / "data"
EVAL_PATH = REPO / "backend" / "harnesses" / "data" / "math_eval_200.jsonl"
TRAIN_PATH = REPO / "training-sets" / "math-example-v1.jsonl"

EVAL_N = 200
TRAIN_N = 500
SEED = 42


_FINAL_RE = re.compile(r"####\s*(.+)\s*$", re.MULTILINE)


def extract_final_answer(gsm8k_answer: str) -> str:
    """Pull the final numeric answer from a GSM8K answer string.

    GSM8K answers end with ``#### <number>``. Return that number as a string
    with no decoration so the harness normalizer can do a clean comparison.
    """
    m = _FINAL_RE.search(gsm8k_answer)
    if not m:
        return ""
    return m.group(1).strip().rstrip(".").replace(",", "")


def main() -> None:
    ds = load_from_disk(str(GSM8K_PATH))
    train = list(ds["train"])
    test = list(ds["test"])
    print(f"loaded GSM8K: {len(train)} train / {len(test)} test")

    rng = random.Random(SEED)

    # Eval set: 200 from test (shuffled, deterministic).
    rng.shuffle(test)
    eval_rows = test[:EVAL_N]
    EVAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVAL_PATH.open("w", encoding="utf-8") as f:
        for i, ex in enumerate(eval_rows):
            final = extract_final_answer(ex["answer"])
            row = {
                "sample_id": f"gsm8k_test_{i:04d}",
                "question": ex["question"],
                "expected_answer": final,
                "domain": "grade_school_math_word_problems",
            }
            f.write(json.dumps(row) + "\n")
    print(f"wrote {len(eval_rows)} eval rows to {EVAL_PATH}")

    # Train set: 500 from train (shuffled, deterministic). Train and test
    # are disjoint sets upstream so no overlap by construction.
    rng.shuffle(train)
    train_rows = train[:TRAIN_N]
    TRAIN_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TRAIN_PATH.open("w", encoding="utf-8") as f:
        for i, ex in enumerate(train_rows):
            row = {
                "sample_id": f"gsm8k_train_{i:04d}",
                "question": ex["question"],
                "answer": ex["answer"],  # full chain-of-thought with #### marker
            }
            f.write(json.dumps(row) + "\n")
    print(f"wrote {len(train_rows)} train rows to {TRAIN_PATH}")

    # Overlap sanity check — compare question strings.
    eval_qs = {r["question"] for r in eval_rows}
    train_qs = {r["question"] for r in train_rows}
    overlap = eval_qs & train_qs
    assert not overlap, f"UNEXPECTED OVERLAP: {len(overlap)} questions in both sets"
    print("overlap check: PASS (eval and train disjoint)")


if __name__ == "__main__":
    main()
