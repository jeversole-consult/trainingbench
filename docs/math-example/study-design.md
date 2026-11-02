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

---

## Methodological framework

**On 2026-11-02, operator shifted the project focus from
"ship a demo" to "produce a publishable study on when PEFT helps
vs. harms strong instruction-tuned bases".** The stable research
protocol lives at [`methodology.md`](methodology.md). Every trial
pre-registered below follows that protocol (reproducibility
checklist, threats to validity, confirmation-bias checks,
pre-registered thresholds locked before result inspection).

Trials below append in chronological order. Earlier trial sections
(above this line) remain as originally registered; interpretation
notes are added via the search log, not via retroactive editing.

### Trials #1–#4 wiring note (added 2026-11-02 retrospectively)

The sections above describing Set 3 (training set) presumed that
`training_set_versions` drove training-data input. **This was
not true for Trials #1 through #4** — see
[`architectural-finding-training-set-wiring.md`](architectural-finding-training-set-wiring.md).
`train.py` unconditionally read raw GSM8K via `load_from_disk`
and selected the first N rows after HF's default shuffle;
`training_set_version_id` was pure provenance decoration until
TB-US-078 fixed the wiring. Hyperparameter comparisons across
Trials #1–#4 remain valid; apparent training-set variation does
not. Trial #5 (TB-US-079) is the first trial under corrected
wiring where the registered `training_set_version` is the actual
training data source.

---

## Trial #5 pre-registration — chat-template PEFT on Instruct (TB-US-079)

**Registered**: 2026-11-02 (updated TB-US-078 → TB-US-079 after
TB-US-078 was rescoped to the architectural fix on the same day)
**Status at registration**: hypothesis-only; no runs yet
**Rationale documents**:
- [`instruct-scale-up-results.md`](instruct-scale-up-results.md)
  (Trial #4 finding — training approach regressed Instruct from
  43% to 23%; F13 format mismatch)
- [`architectural-finding-training-set-wiring.md`](architectural-finding-training-set-wiring.md)
  (why Trial #5 is the first trial where
  `training_set_versions.v7` is the actual training data —
  fixed by TB-US-078)

**Prerequisite**: TB-US-078 smoke-run must pass before Trial #5
launches (confirms the JSONL training path works end-to-end).

### Research question (Trial #5)

Does training on **chat-template-formatted data** (matching
Instruct's native response format) with a **smaller LoRA
perturbation** (rank 16 vs. Trial #4's rank 32) **preserve or
improve** on bare Instruct's 43% holdout accuracy?

### Primary hypothesis (H5-primary)

**Alternative**: a QLoRA adapter trained with these dial changes
will achieve holdout accuracy ≥ **43% ± 5pt** (does not regress
bare Instruct within noise bounds).

**Null**: holdout accuracy < 38% (reproduces Trial #4's
regression signal; approach-change doesn't help).

**Primary decision threshold**: holdout ≥ 43% at `n_samples=200`
= alternative accepted. Below 38% = null supported. 38–43%
inconclusive, treated as null until replicated.

### Secondary hypotheses

| ID | Claim | Measurable |
|---|---|---|
| H5a | Chat-template-formatted outputs preserve dual-`####` structure | per-sample inspection: ≥50% of outputs have 2+ `####` matches (bare Instruct: ~75%; adapter v5 Trial #4: ~15%) |
| H5c | Meaningful improvement over bare | holdout ≥ 50% (bare + 7pt) |
| H5c-strong | Published-range improvement | holdout ≥ 60% |
| H5d | Early stopping triggers before epoch 3 | validated by training 11 pattern — eval loss plateau |

### Training configuration (locked)

| Hyperparameter | Trial #4 | **Trial #5** | Rationale |
|---|---|---|---|
| Base | Instruct | Instruct (same) | isolates data+rank effect |
| **Training data format** | Raw CoT prose | **Chat template** (`apply_chat_template()`) | matches Instruct's SFT format |
| **LoRA rank** | 32 | **16** | smaller perturbation |
| LoRA alpha | 64 | 32 (2× rank) | standard ratio |
| LoRA dropout | 0.05 | 0.05 | unchanged |
| Learning rate | 2e-4 | **1e-4** | slower perturbation |
| Epochs | 5 | 3 | less risk of overfitting |
| Batch size | 4 | 4 | unchanged |
| Gradient accumulation | 4 | 4 | unchanged |
| **Training samples** | 500 | **1000** | more signal to replace, not just damage |
| Max eval samples | 100 | 100 | unchanged |
| Early stopping | enabled | enabled (inherited from Trial #4 infrastructure) | |

### Training set composition (new: v7)

- Source: GSM8K train split
- Count: 1000 problems
- Sampling seed: 46 (distinct from prior sampling seeds)
- Format: each training example formatted via
  `tokenizer.apply_chat_template([{"role":"system","content":"<prompt v3>"}, {"role":"user","content":"<question>"}, {"role":"assistant","content":"<full CoT answer>"}])`
- Disjointness invariant: `v7 ∩ holdout = ∅` (enforced by script)
- Overlap with v4 (failures) and v6 tolerated but reported

### Pre-registered interpretation guide

Decision mapping, locked before results seen:

| Holdout result | Interpretation | Next step |
|---|---|---|
| < 38% | Null; regression confirmed with new approach | TB-US-080: try different lever (larger data, different PEFT method, chat-template format but keeps rank 32) |
| 38–43% | Inconclusive; within noise of bare | Multi-seed replicate OR adjust one dial and rerun |
| 43–50% | Alternative accepted (no regression) | Document; try to push higher in TB-US-080 |
| 50–60% | Meaningful improvement; secondary H5c met | Document as positive result; publication candidate |
| 60–75% | Strong result; close to published range | Headline finding; multi-seed replicate for publication |
| > 75% | Suspect — too good; check for test-set leakage | Audit disjointness, check seeds, re-run with fresh samples |

### Reproducibility declaration

Per [`methodology.md`](methodology.md) reproducibility checklist.
Specific values for Trial #5 locked at run time + captured in
`instruct-chat-template-results.md`.

### Threats to validity flagged (pre-run)

- **Internal**: chat template implementation may vary across HF
  Transformers versions — pin the exact `transformers` version
  used. Verify chat template produces expected format by
  inspecting 1-2 formatted samples before training launches.
- **External**: result applies to Llama 3.1 8B Instruct
  specifically; generalization to other Instruct bases requires
  separate study.
- **Construct**: "no regression" is a weak alternative; a result
  of exactly 43% could be either "didn't help" or "would help
  with more data" — ambiguity acknowledged.
- **Statistical**: single-run; result within ±5pt of 43%
  interpreted as inconclusive, not confirmatory. Multi-seed
  replicate if we land in 38–48% zone.

### Confirmation-bias checklist (apply at close)

- [ ] Did we interpret per pre-registered thresholds, not
      narrative preference?
- [ ] Did we review ≥10 right + ≥10 wrong samples by hand?
- [ ] Is a reasonable alternative explanation ruled out?
- [ ] Would the follow-up be different if the result had been
      the opposite?
