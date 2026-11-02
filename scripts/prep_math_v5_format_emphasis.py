#!/usr/bin/env python3
"""TB-US-076 Option B: build training set v5 for format-emphasis adapter v4 retrain.

Composition: 200 TB-US-075 baseline failures + 100 additional
GSM8K train-split problems (seed=44, strictly disjoint from
holdout set at seed=43).

The extra 100 problems provide more exposure to the `#### N`
format marker without introducing new task shapes. Each GSM8K
answer ends with `#### N`.

Total output: 300 (question, answer) rows.

Overlap-safe:
- GSM8K test split ⊥ GSM8K train split (upstream disjoint)
- The 200 failures come from test split (TB-US-075 Phase 4)
- The 100 extra come from train split (seed=44)
- The holdout 200 are from train split (seed=43)
- Script verifies 100-extra ∩ holdout = ∅

See docs/user-stories/tb-us-076.md Option B.
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

from datasets import load_from_disk


REPO = Path(__file__).resolve().parent.parent
GSM8K_PATH = REPO / "datasets" / "math" / "data"
BASE_TRAIN_PATH = REPO / "training-sets" / "math-example-v2-failures.jsonl"
HOLDOUT_PATH = REPO / "backend" / "harnesses" / "data" / "math_eval_200_holdout.jsonl"
OUTPUT_PATH = REPO / "training-sets" / "math-example-v5-format-emphasis.jsonl"

EXTRA_N = 100
SEED = 44  # distinct from the holdout's seed=43


def load_questions(path: Path) -> set[str]:
    out: set[str] = set()
    if not path.exists():
        return out
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.add(json.loads(line)["question"])
    return out


def main() -> None:
    ds = load_from_disk(str(GSM8K_PATH))
    train = list(ds["train"])
    print(f"loaded GSM8K: {len(train)} train rows")

    # Load existing TB-US-075 v4 training set as the base
    base_rows: list[dict] = []
    with BASE_TRAIN_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                base_rows.append(json.loads(line))
    print(f"loaded TB-US-075 base: {len(base_rows)} rows")

    # Load the holdout so we can exclude any overlap
    holdout_qs = load_questions(HOLDOUT_PATH)
    base_qs = {r["question"] for r in base_rows}
    print(f"holdout qs: {len(holdout_qs)}  base qs: {len(base_qs)}")

    # Shuffle train with distinct seed; pick first EXTRA_N that don't
    # overlap with holdout or base
    rng = random.Random(SEED)
    rng.shuffle(train)
    extra: list[dict] = []
    for ex in train:
        if ex["question"] in holdout_qs:
            continue
        if ex["question"] in base_qs:
            continue  # don't double-count TB-US-075 failures
        extra.append(ex)
        if len(extra) >= EXTRA_N:
            break
    assert len(extra) == EXTRA_N, f"got {len(extra)} unique extras; need {EXTRA_N}"

    # Format as (sample_id, question, answer) rows
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        for row in base_rows:
            f.write(json.dumps(row) + "\n")
        for i, ex in enumerate(extra):
            row = {
                "sample_id": f"gsm8k_train_extra_{i:04d}",
                "question": ex["question"],
                "answer": ex["answer"],
            }
            f.write(json.dumps(row) + "\n")

    # Final disjointness audit against holdout
    all_qs = base_qs | {ex["question"] for ex in extra}
    overlap = all_qs & holdout_qs
    assert not overlap, (
        f"ERROR: v5 training set overlaps holdout by {len(overlap)} questions"
    )
    print(f"wrote {len(base_rows) + len(extra)} total rows to {OUTPUT_PATH}")
    print(f"  base failures: {len(base_rows)}")
    print(f"  extra GSM8K train (seed={SEED}): {len(extra)}")
    print(f"disjointness check vs. holdout: PASS (0 overlap)")


if __name__ == "__main__":
    main()
