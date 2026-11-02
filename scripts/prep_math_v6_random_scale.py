#!/usr/bin/env python3
"""TB-US-077 Trial #4: build training set v6 for Instruct-base scale-up.

Composition: 500 random GSM8K train-split problems (seed=45,
strictly disjoint from the holdout at seed=43 and from v4 failures
at test-split-seed=42-by-construction).

Format: {sample_id, question, answer} with full CoT ending in
`#### N`. Matches math-example-v4-failures.jsonl shape so
train.py can consume unchanged.

Rationale: Trial #3 (adapter v4, 10 ep × 300 base variant)
overfit. Trial #4 pivots to the Instruct variant + random sampling
+ early stopping. Random sampling gives better task-distribution
coverage than failures-targeted sampling (which was pedagogical
for the weak base in Trials #1-3).

See docs/user-stories/tb-us-077.md.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from datasets import load_from_disk


REPO = Path(__file__).resolve().parent.parent
GSM8K_PATH = REPO / "datasets" / "math" / "data"
HOLDOUT_PATH = REPO / "backend" / "harnesses" / "data" / "math_eval_200_holdout.jsonl"
V4_FAILURES_PATH = REPO / "training-sets" / "math-example-v2-failures.jsonl"
V5_EMPHASIS_PATH = REPO / "training-sets" / "math-example-v5-format-emphasis.jsonl"
OUTPUT_PATH = REPO / "training-sets" / "math-example-v6-random-scale.jsonl"

SAMPLE_N = 500
SEED = 45  # distinct from seed=42 (test split subset), seed=43 (holdout),
           # seed=44 (v5 extra 100). All sampling seeds in the family are
           # distinct so the random states don't accidentally overlap.


def load_questions(path: Path) -> set[str]:
    out: set[str] = set()
    if not path.exists():
        return out
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.add(json.loads(line)["question"])
    return out


def main() -> None:
    ds = load_from_disk(str(GSM8K_PATH))
    train = list(ds["train"])
    print(f"loaded GSM8K: {len(train)} train rows")

    # Must be strictly disjoint from holdout (TB-US-075 methodology
    # requires the holdout stays unseen in training).
    holdout_qs = load_questions(HOLDOUT_PATH)
    print(f"holdout qs: {len(holdout_qs)}")

    # Shuffle with distinct seed; take first SAMPLE_N excluding holdout.
    rng = random.Random(SEED)
    rng.shuffle(train)
    picked: list[dict] = []
    for ex in train:
        if ex["question"] in holdout_qs:
            continue
        picked.append(ex)
        if len(picked) >= SAMPLE_N:
            break
    assert len(picked) == SAMPLE_N, (
        f"got {len(picked)} unique picks; need {SAMPLE_N}"
    )

    # Emit (sample_id, question, answer) in the shape train.py expects.
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        for i, ex in enumerate(picked):
            row = {
                "sample_id": f"gsm8k_v6_{i:04d}",
                "question": ex["question"],
                "answer": ex["answer"],
            }
            f.write(json.dumps(row) + "\n")

    # Audit: v6 ∩ holdout = ∅ (we excluded above; sanity-double-check)
    v6_qs = {ex["question"] for ex in picked}
    overlap = v6_qs & holdout_qs
    assert not overlap, f"ERROR: v6 overlaps holdout by {len(overlap)}"

    # Report overlap with v4 (failures) and v5 (300-row mix) for the record.
    # Overlap is tolerated — v4 and v5 aren't used in Trial #4.
    for other_name, other_path in [("v4 (failures)", V4_FAILURES_PATH),
                                     ("v5 (300-row mix)", V5_EMPHASIS_PATH)]:
        if other_path.exists():
            other_qs = load_questions(other_path)
            o = v6_qs & other_qs
            print(f"overlap with {other_name}: {len(o)}/{len(other_qs)}  (tolerated; not used in Trial #4)")

    print(f"wrote {len(picked)} rows to {OUTPUT_PATH}")
    print(f"disjointness vs holdout: PASS (0 overlap)")


if __name__ == "__main__":
    main()
