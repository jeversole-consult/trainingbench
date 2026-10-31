#!/usr/bin/env python3
"""TB-US-075 Phase 4 R10: build the training set from baseline failures.

Methodology: for each problem the bare model failed in Phase 2
(experiment 8 on dev tree, bare Llama 3.1 8B base at n=200), look
up the full GSM8K chain-of-thought ground-truth answer and emit as
a (question, answer) training example.

Format matches training-sets/math-example-v1.jsonl so the existing
train.py pipeline can consume it unchanged.

The baseline test (math_eval_200.jsonl) was sampled from GSM8K's
test split with seed=42. We re-derive the same subset here by
re-shuffling with the same seed and taking the first 200. Then for
each one where E8 scored correct=False, we add it to the output
file with its full GSM8K answer.

Since E8 scored 0/200, all 200 problems become training examples —
training set is 200 (question, correct-answer) pairs.

See docs/math-example/study-design.md + baseline-analysis.md.
"""

from __future__ import annotations

import json
import random
import re
import sqlite3
from pathlib import Path

from datasets import load_from_disk


REPO = Path(__file__).resolve().parent.parent
GSM8K_PATH = REPO / "datasets" / "math" / "data"
BASELINE_PATH = REPO / "backend" / "harnesses" / "data" / "math_eval_200.jsonl"
DB_PATH = REPO / "backend" / "db" / "trainingbench.db"
OUTPUT_PATH = REPO / "training-sets" / "math-example-v2-failures.jsonl"

BASELINE_EXPERIMENT_ID = 8  # TB-US-075 Phase 2 bare baseline on dev tree
EVAL_N = 200
SEED = 42  # must match prep_math_example_jsonl.py so we hit the same subset


def main() -> None:
    # 1. Rebuild the baseline-test subset deterministically. Must match
    #    the subset in math_eval_200.jsonl exactly.
    ds = load_from_disk(str(GSM8K_PATH))
    test = list(ds["test"])
    rng = random.Random(SEED)
    rng.shuffle(test)
    eval_rows = test[:EVAL_N]
    print(f"loaded + reshuffled GSM8K test: took first {len(eval_rows)} with seed={SEED}")

    # Sanity-check that this matches math_eval_200.jsonl's question strings.
    with BASELINE_PATH.open("r", encoding="utf-8") as f:
        baseline_rows = [json.loads(line) for line in f if line.strip()]
    assert len(baseline_rows) == len(eval_rows), (
        f"baseline file has {len(baseline_rows)} rows but reshuffle produced "
        f"{len(eval_rows)}; something changed"
    )
    for i, (reshuffled, baseline) in enumerate(zip(eval_rows, baseline_rows)):
        if reshuffled["question"] != baseline["question"]:
            raise SystemExit(
                f"MISMATCH at index {i}: baseline sample_id={baseline['sample_id']} "
                f"doesn't match reshuffled question. seed convention changed?"
            )
    print("sanity check: reshuffle matches math_eval_200.jsonl question-for-question")

    # 2. Load E8's per_sample to find which were wrong (correct=False).
    with sqlite3.connect(str(DB_PATH)) as c:
        c.row_factory = sqlite3.Row
        row = c.execute(
            "SELECT results_json FROM experiments WHERE experiment_id = ?",
            (BASELINE_EXPERIMENT_ID,),
        ).fetchone()
    if not row or not row["results_json"]:
        raise SystemExit(
            f"experiment {BASELINE_EXPERIMENT_ID} has no results_json; "
            f"did Phase 2 R5 run?"
        )
    per_sample = json.loads(row["results_json"])["per_sample"]
    assert len(per_sample) == EVAL_N, (
        f"experiment {BASELINE_EXPERIMENT_ID} has {len(per_sample)} per_sample "
        f"rows; expected {EVAL_N}"
    )
    # Line up per_sample[i] with eval_rows[i] by question text — the per_sample
    # order should match the baseline-file order which matches the reshuffle.
    for i, (ps, eval_row) in enumerate(zip(per_sample, eval_rows)):
        if ps["question"] != eval_row["question"]:
            raise SystemExit(
                f"per_sample[{i}] question doesn't match eval_rows[{i}]; "
                f"ordering inconsistency"
            )
    print("sanity check: E8 per_sample order matches reshuffled test subset")

    # 3. Build the failure training set.
    wrong_indices = [i for i, ps in enumerate(per_sample) if not ps.get("correct")]
    print(f"wrong indices: {len(wrong_indices)}/{EVAL_N}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        for pos, i in enumerate(wrong_indices):
            eval_row = eval_rows[i]
            # eval_row["answer"] is the full GSM8K CoT answer with #### N.
            # Emit in the same shape as math-example-v1.jsonl.
            out = {
                "sample_id": f"gsm8k_test_fail_{pos:04d}",
                "question": eval_row["question"],
                "answer": eval_row["answer"],
            }
            f.write(json.dumps(out) + "\n")
    print(f"wrote {len(wrong_indices)} failure-training rows to {OUTPUT_PATH}")

    # 4. Final disjointness sanity-check: training set must NOT overlap holdout.
    HOLDOUT_PATH = REPO / "backend" / "harnesses" / "data" / "math_eval_200_holdout.jsonl"
    if HOLDOUT_PATH.exists():
        with HOLDOUT_PATH.open("r", encoding="utf-8") as f:
            holdout_qs = {json.loads(line)["question"] for line in f if line.strip()}
        training_qs = {eval_rows[i]["question"] for i in wrong_indices}
        overlap = training_qs & holdout_qs
        assert not overlap, (
            f"ERROR: training set overlaps holdout by {len(overlap)} question(s); "
            f"holdout must be strictly disjoint from training"
        )
        print(f"disjointness check: PASS ({len(training_qs)} training ∩ "
              f"{len(holdout_qs)} holdout = 0; strictly disjoint)")


if __name__ == "__main__":
    main()
