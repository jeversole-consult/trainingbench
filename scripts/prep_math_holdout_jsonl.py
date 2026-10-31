#!/usr/bin/env python3
"""TB-US-075 Phase 1 R2: prep math_eval_200_holdout.jsonl from GSM8K train split.

The holdout set is the out-of-sample generalization check for the
TB-US-075 train/validate/holdout methodology. Sampled from GSM8K's
train split (not test split) so it's guaranteed disjoint from the
baseline test set (`math_eval_200.jsonl`, from test split).

Format matches math_eval_200.jsonl exactly so the same harness
module (harnesses.math_qa_v1) can run against both.

Seed=43 is deliberate: distinct from seed=42 used in
scripts/prep_math_example_jsonl.py, so the random state is
independent. Overlap with the shipped math-example-v1 training
set (also from train split, seed=42) is tolerated but reported;
math-example-v1 is NOT used in TB-US-075's methodology anyway.

See docs/math-example/study-design.md for the full methodology.
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

from datasets import load_from_disk


REPO = Path(__file__).resolve().parent.parent
GSM8K_PATH = REPO / "datasets" / "math" / "data"
HOLDOUT_PATH = REPO / "backend" / "harnesses" / "data" / "math_eval_200_holdout.jsonl"
BASELINE_PATH = REPO / "backend" / "harnesses" / "data" / "math_eval_200.jsonl"
V1_TRAIN_PATH = REPO / "training-sets" / "math-example-v1.jsonl"

HOLDOUT_N = 200
SEED = 43


_FINAL_RE = re.compile(r"####\s*(.+)\s*$", re.MULTILINE)


def extract_final_answer(gsm8k_answer: str) -> str:
    """Pull the final numeric answer from a GSM8K answer string."""
    m = _FINAL_RE.search(gsm8k_answer)
    if not m:
        return ""
    return m.group(1).strip().rstrip(".").replace(",", "")


def load_question_set(path: Path, key: str = "question") -> set[str]:
    """Load the question strings from a JSONL file into a set."""
    if not path.exists():
        return set()
    out: set[str] = set()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.add(json.loads(line)[key])
    return out


def main() -> None:
    ds = load_from_disk(str(GSM8K_PATH))
    train = list(ds["train"])
    test = list(ds["test"])
    print(f"loaded GSM8K: {len(train)} train / {len(test)} test")

    rng = random.Random(SEED)
    rng.shuffle(train)
    holdout_rows = train[:HOLDOUT_N]

    HOLDOUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HOLDOUT_PATH.open("w", encoding="utf-8") as f:
        for i, ex in enumerate(holdout_rows):
            final = extract_final_answer(ex["answer"])
            row = {
                "sample_id": f"gsm8k_holdout_{i:04d}",
                "question": ex["question"],
                "expected_answer": final,
                "domain": "grade_school_math_word_problems",
            }
            f.write(json.dumps(row) + "\n")
    print(f"wrote {len(holdout_rows)} holdout rows to {HOLDOUT_PATH}")

    # Disjointness checks.
    holdout_qs = {ex["question"] for ex in holdout_rows}

    baseline_qs = load_question_set(BASELINE_PATH)
    baseline_overlap = holdout_qs & baseline_qs
    if baseline_overlap:
        raise SystemExit(
            f"ERROR: holdout overlaps baseline test set by {len(baseline_overlap)} "
            f"question(s). Baseline test must be disjoint from holdout for the "
            f"out-of-sample check to be valid."
        )
    print(f"baseline-overlap check: PASS (0/{len(baseline_qs)} baseline qs in holdout)")

    v1_train_qs = load_question_set(V1_TRAIN_PATH)
    v1_overlap = holdout_qs & v1_train_qs
    # Overlap with v1 training set is tolerated (v1 isn't used in TB-US-075),
    # but we report it for the study-design doc record.
    print(f"v1-training-set overlap: {len(v1_overlap)}/{len(v1_train_qs)} "
          f"v1 qs are in holdout (tolerated; v1 not used in TB-US-075)")


if __name__ == "__main__":
    main()
