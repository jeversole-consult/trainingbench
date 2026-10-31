# Study Design — TB-US-075 Performant math-example Demo

**Status**: Pre-registration document, written before Phase 2
measurement runs.
**Owned by**: TB-US-075
**Created**: 2026-10-28

This document pre-registers the three disjoint problem sets and
the hypotheses that will be tested in TB-US-075's measurement
phases. Writing this BEFORE Phase 2 runs prevents post-hoc
rationalization and makes the study scientifically defensible.

## Methodology

Classical predictive-modeling train / validate / holdout
pattern:

- **Validation set** (we call it "baseline test") — the model
  gets measured against this before and after training. Fixed
  yardstick.
- **Training set** — derived from the validation set's failures.
  Each failed problem gets paired with its GSM8K ground-truth
  answer. The model is literally being taught the answers to
  problems it failed.
- **Holdout set** — never seen during training. The out-of-sample
  generalization check. Determines what fraction of post-training
  improvement is **memorization** vs. **genuine learning**.

The ratio of (baseline-rerun improvement) to (holdout improvement)
tells us how much the adapter learned the SKILL vs. the specific
problems.

## The three disjoint problem sets

Both GSM8K splits are the data pool. GSM8K ships ~7,473 train
problems + ~1,319 test problems with ground-truth step-by-step
answers.

### Set 1: Baseline test (validation set)

- **Source**: GSM8K **test** split
- **Count**: 200 problems
- **Seed**: 42 (deterministic shuffle)
- **File**: `backend/harnesses/data/math_eval_200.jsonl` (already
  exists; shipped by TB-US-057 Phase A via
  `scripts/prep_math_example_jsonl.py`)
- **Role**: measure baseline (Phase 2) + measure in-sample
  post-training (Phase 6 E1b)
- **Harness pin**: `harness_versions.v2` on agent 3 (math-example)
  — unchanged
- **Rationale**: reusing the existing baseline eval set keeps the
  before/after numbers directly comparable to TB-US-057 Phase B's
  shipped flat baseline (0/200). Any improvement here is
  "did the model learn what we trained it on" — close to a
  memorization threshold.

### Set 2: Holdout test (out-of-sample set)

- **Source**: GSM8K **train** split (same shape as test; different
  pool)
- **Count**: 200 problems
- **Seed**: 43 (deterministic; distinct from any other sampling
  seed in this project to guarantee the holdout is drawn from a
  different random state than the training pool or the existing
  math-example-v1.jsonl)
- **File**: `backend/harnesses/data/math_eval_200_holdout.jsonl`
  (new; sampled via a dedicated script committed with this story)
- **Role**: measure out-of-sample post-training (Phase 6 E_holdout)
- **Harness pin**: `harness_versions.v3` on agent 3 (new; released
  + promoted alongside the new adapter)
- **Rationale**: GSM8K train split is strictly disjoint from GSM8K
  test split, so the holdout cannot contain any of the baseline
  test problems. The holdout is NOT used in training either (the
  training set comes from Set 1's failures, not Set 2). Therefore
  Set 2 is "unseen by the adapter" — the honest generalization
  check.

### Set 3: Training set (derived from Set 1 failures)

- **Source**: subset of Set 1 (baseline test) that the bare model
  got WRONG, paired with GSM8K ground-truth answers from the
  original `ds["test"]` split
- **Count**: depends on Phase 2's baseline accuracy. If baseline
  is 0/200, training set is 200. If baseline is 50/200, training
  set is 150.
- **File**: `training-sets/math-example-v2-failures.jsonl` (new;
  built during Phase 4)
- **Role**: train the adapter (Phase 5)
- **Pin**: `training_set_versions.v2+` on agent 3 (next version
  from the shipped v3)
- **Rationale**: training on exactly the failures gives us a
  guaranteed signal on the baseline-rerun measurement (because
  we're teaching the model those answers). The holdout
  measurement separates "learned the answers" (memorization,
  shows up on baseline rerun) from "learned the skill" (genuine
  learning, shows up on holdout).

### Note on the existing math-example-v1.jsonl training set

The shipped TB-US-057 Phase A training set at
`training-sets/math-example-v1.jsonl` (500 problems from GSM8K
train split, seed=42) is **not used** in TB-US-075.

TB-US-075's methodology derives the training set from baseline
test failures, not from a pre-sampled train-split subset. The
existing v1 training set remains in the repo as a reference /
historical artifact.

If TB-US-076 later wants to try the alternative strategy (train
on a GSM8K-train-split subset rather than failures), the v1
training set is available.

### Possible overlap with existing v1 training set

The holdout set (Set 2, seed=43) and the v1 training set
(500 problems from train split, seed=42) MAY overlap because
both are drawn from the same GSM8K train-split pool with
different shuffles.

**This does NOT affect TB-US-075's methodology** because the v1
training set is not used here. The actual training (Set 3) comes
from GSM8K test split failures, which are strictly disjoint from
GSM8K train split by construction.

The holdout script will verify that `training_set_v2_failures ∩
holdout = ∅` at construction time. Overlap with v1 is tolerated.

## Pre-registered hypotheses

The following hypotheses are stated BEFORE Phase 2 runs. Phase 7's
measurement report will mark each as **met**, **partial**, or
**not met** with the measured values.

### H1 — Baseline rerun improvement (in-sample)

**Claim**: After training the adapter on the baseline test
failures (paired with GSM8K ground truth), re-running the SAME
200-sample baseline test will show accuracy ≥ **50%**.

**Why 50%**: We're training on exactly those 200 problems with
their correct answers. If the training loop learns anything at
all, the adapter should reproduce at least half of them
correctly. Below 50% would signal either (a) the training didn't
converge, (b) overfitting is somehow failing, or (c) the format
expected by the harness doesn't match what training produces.

**Caveat**: this is close to a memorization threshold — baseline
improvement is NOT the headline finding. H2 is.

### H2 — Holdout improvement (out-of-sample)

**Claim**: After training, the 200-sample holdout accuracy will
be ≥ **10%** (up from a current bare baseline of 0% per
TB-US-057 Phase B).

**Why 10%**: A ten-point lift on NEVER-SEEN problems with the
same shape as training is a defensible "the adapter learned
transferable skill" signal. A 10% hit rate on grade-school math
word problems from an 8B base + minimally-targeted fine-tuning
would be a credible first-iteration result.

**Published-comparable context**: large well-trained math LoRAs
on 8B bases typically reach 25-45% on GSM8K. 10% is a lower
bar aimed at demonstrating "learning happened"; a result of
25%+ would be exceptional for this training-set size.

**Caveat**: a null result (holdout stays ≤ 2%) is a legitimate
finding, not a story failure. It would mean the adapter learned
specific answers but not transferable patterns — pointing
TB-US-076 at larger / more diverse training.

### H3 — Generalization gap (headline interpretation)

**Claim**: The gap `(H1 accuracy − H2 accuracy)` will reveal
the memorization-vs-learning balance:

- **Small gap (≤ 15 points)**: adapter learned the skill;
  generalization happened. **Strong result.**
- **Medium gap (15-40 points)**: mixed; adapter partially
  learned the skill but also memorized a lot. Honest
  intermediate result.
- **Large gap (> 40 points)**: adapter mostly memorized the
  training problems without learning. **Weak result**, but a
  defensible honest finding that informs TB-US-076.

**No specific numeric prediction** for H3 — the gap IS the
measurement. H3 is a pre-registered interpretation framework.

## Base-model decision

**Base model**: `meta-llama/Meta-Llama-3.1-8B` (base variant,
not Instruct) — SAME as TB-US-057 Phase B.

**Rationale for sticking with base, not Instruct**:
- Reuses the exact baseline from TB-US-057 Phase B (which the
  public `docs/pages/staged-progression.md` points at). Any
  improvement is directly attributable to the targeted training
  set + adapter, not a base-model swap.
- Keeps the demo narrative pedagogically clean: "we trained
  everything from scratch on top of a base model". Instruct
  variant muddies this.
- Instruct is identified as the single-largest-lever by
  `docs/math-example/sweet-spot-exploration.md`'s "Path to
  performant numbers" section. If H1/H2 fail with base,
  TB-US-076's first attempt would swap to Instruct — a
  pre-registered next step.

**Decision**: base, this story. If H2 is near-zero, draft
TB-US-076 to try Instruct with the same training set.

## Training hyperparameters (pre-stated)

| Hyperparameter | Value | Rationale |
|---|---|---|
| LoRA rank | 32 | Up from 16 (shipped v2 adapter); more capacity for the failure-mode patterns |
| LoRA alpha | 64 | 2× rank, standard ratio |
| Learning rate | 2e-4 | Same as TB-US-057's shipped settings |
| Epochs | 5 | Up from 3; targeted training on ~200 problems is small, so more epochs help without overfitting-explosion risk |
| Batch size | 4 | Same as TB-US-057 |
| Gradient accumulation | 4 | Same as TB-US-057 |
| Dropout | 0.05 | Light regularization |
| `max_train_samples` | 200 (or whatever Phase 2 produces) | Explicitly all failures; no sampling-down |
| `max_eval_samples` | 50 | During-training eval on a subset; final eval goes through the harness at n=200 |
| Target duration | ~45 min on RTX 3090 | 200 samples × 5 epochs with gradient accumulation 4 → ~250 effective steps; conservative estimate given TB-US-057 Phase B seen ~15 min for 500 samples × 3 epochs |

## Determinism of baseline measurement

GSM8K ground-truth is a fixed string. The baseline test's
sampling is seeded (seed=42). The LLM generation (model's answer
to each problem) depends on sampling parameters.

**For maximum determinism in baseline measurement**: temperature=0
(or very low) + no sampling noise. This gives us a stable
"what does bare Llama 3.1 8B base produce on problem X" answer.

**Current harness default**: review `backend/harnesses/math_qa_v1.py`
and the pipeline config in `backend/api/harness_runner.py` for
temperature setting. If > 0, Phase 2 R4 will test determinism by
re-running E1 once and comparing per-sample outputs. If
reproducible, Phase 3's failure classification is trustworthy.
If stochastic, document the variance and interpret with
appropriate skepticism.

## Deliverable artifacts (pre-registered)

| Phase | Artifact | Path |
|---|---|---|
| 1 (this) | Study design doc | `docs/math-example/study-design.md` |
| 1 | Holdout sampling script | `scripts/prep_math_holdout_jsonl.py` |
| 1 | Holdout JSONL | `backend/harnesses/data/math_eval_200_holdout.jsonl` |
| 1 | Holdout harness registration | `harness_versions.v3` on agent 3 |
| 2 | Bare baseline measurement | E1 run on agent 3 at n=200; results persist |
| 3 | Failure analysis doc | `docs/math-example/baseline-analysis.md` |
| 4 | Training-set strategy doc | `docs/math-example/training-set-strategy.md` |
| 4 | Training set from failures | `training-sets/math-example-v2-failures.jsonl` |
| 5 | Trained adapter | `adapters/math-example/vN/` + `adapter_versions.vN` |
| 6 | In-sample measurement | E1b run (baseline test, new adapter) |
| 6 | Out-of-sample measurement | E_holdout run (holdout harness, new adapter) |
| 7 | Measurement report | `docs/math-example/measured-improvement.md` |
| 7 | Public Pages update | `docs/pages/staged-progression.md` with real numbers |
| 8 (optional) | RAG hypothesis test results | Addendum to measurement doc |
| 9 | Follow-up story draft | TB-US-076 if first iteration doesn't light up ladder |

## Scope caps (reiterated from story)

- **One training iteration only.** If H1/H2 outcomes point at a
  second attempt, TB-US-076 captures it. This story does not
  loop.
- **No automated hyperparameter search.** Hyperparameters are
  pre-stated above.
- **No competition against external benchmarks.** This is a
  TB-method demonstration, not a MetaMath-killer.
- **RAG hypothesis test is conditional.** Phase 8 only runs if
  Phase 7 completes AND operator chooses to extend. A null result
  on RAG is itself a useful finding.
