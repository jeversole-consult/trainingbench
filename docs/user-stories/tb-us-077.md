# TB-US-077: Scale up to credible demo numbers — Instruct base + larger training + early stopping

**Status**: Completed
**Created**: 2026-11-01
**Started**: 2026-11-01
**Completed**: 2026-11-02
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on closure commit>

## Story

As a TB maintainer preparing a public demo of the math-example
agent, I want **holdout accuracy in the 50–75% range** — the
"this is actually useful" threshold — so that readers landing on
the Pages site see numbers that validate the methodology beyond
"honest baseline". Fourth trial in the sweet-spot search log;
first attempt at a credible-headline-number adapter.

## Background

Three trials to date (see
[`sweet-spot-search-log.md`](../math-example/sweet-spot-search-log.md)):

- Trial #1 (adapter v3, base variant, 5ep × 200): 0% strict,
  29/23% lenient — hidden by harness bug
- Trial #2 (adapter v3, patched harness): 19% in-sample / 26%
  holdout — real signal visible
- Trial #3 (adapter v4, base variant, 10ep × 300): 6/7.5% —
  overfit; cautionary

**26% holdout is genuine learning but low for a public demo.**
Published GSM8K numbers for comparable 8B-class setups:

- Llama 3.1 8B base + minimal QLoRA (what we have): ~15–30%
- Llama 3.1 8B **Instruct** + no adapter: ~55–70%
- Llama 3.1 8B Instruct + well-trained math LoRA: ~75–85%

**The single biggest unused lever is swapping to the Instruct
variant.** The TB-US-057 Phase C sweet-spot-exploration doc
already identified this. We've been using the *base* variant
pedagogically ("trained from scratch narrative"); the honest
story works equally well with Instruct ("picked a strong
instruction-tuned base + fine-tuned for the task").

Second lever: more training data at the right epoch count +
early stopping to prevent Trial #3's overfitting problem.

**Depends on:**
- TB-US-075, TB-US-076 (closed) — provides methodology,
  harness, holdout, baseline
- Lab machine with ≥24 GB VRAM (same as prior trials)

**Blocks:**
- TB-US-005 public cut desired to have credible demo numbers
  first (not strictly blocking — operator could ship with v3's
  26% and the honest trial log, but credibility would be
  materially stronger with ~60%+)

## Scope (one iteration; same pattern as TB-US-075/076)

Three changes vs. Trial #3's config:

1. **Base model**: `meta-llama/Meta-Llama-3.1-8B-Instruct` (not
   `-8B`). Single string change in the training-run launch
   request + the experiment pins.
2. **Training set**: 500 random GSM8K train-split problems
   (seed=45, strictly disjoint from holdout at seed=43 and
   TB-US-075 training set v4 at seed=42-test-split by
   construction).
3. **Early stopping**: add `transformers.EarlyStoppingCallback`
   to `train.py` with `patience=2`. Set
   `load_best_model_at_end=True`,
   `metric_for_best_model="eval_loss"`,
   `greater_is_better=False`. Model saves the min-eval-loss
   checkpoint rather than the final-epoch one.

## Requirements

### Phase 1 — Pre-registration

- [x] R1: **Update** `docs/math-example/study-design.md` with
      Trial #4 pre-registered hypotheses (see Hypotheses
      below). Append-only addition, not editing existing text.
- [x] R2: **Append Trial #4 planning entry** to
      `sweet-spot-search-log.md` with status "launching"
      (what-we-did section fills in after measurement).

### Phase 2 — Infrastructure (train.py early stopping)

- [x] R3: Edit `training/math/train.py` to add
      `transformers.EarlyStoppingCallback(early_stopping_patience=2)`
      to the Trainer's `callbacks` list.
- [x] R4: Update the `TrainingArguments` call to include
      `load_best_model_at_end=True`,
      `metric_for_best_model="eval_loss"`,
      `greater_is_better=False`.
- [x] R5: Preserve the `report_to="none"` fix from TB-US-066.
- [x] R6: Confirm no regression on existing TB-US-065 integration
      (the callback is additive).

### Phase 3 — Training set v6

- [x] R7: `scripts/prep_math_v6_random_scale.py` — new script.
      500 problems sampled from GSM8K train split with seed=45,
      written to
      `training-sets/math-example-v6-random-scale.jsonl`.
- [x] R8: Disjointness check: `v6 ∩ holdout = ∅`. Fail-fast if
      overlap detected.
- [x] R9: Register as `training_set_versions.v6` on agent 3 via
      API; release + promote.

### Phase 4 — Training (adapter v5)

- [x] R10: Launch training via `POST /training/runs/launch` with
      pre-registered hyperparameters:
      - base_model: `meta-llama/Meta-Llama-3.1-8B-Instruct`
      - training_set_version_id: 6 (v6)
      - lora_rank: 32, alpha: 64, dropout: 0.05
      - learning_rate: 2e-4
      - **epochs: 5** (early stopping will trim if applicable)
      - batch_size: 4, gradient_accumulation_steps: 4
      - max_train_samples: 500, max_eval_samples: 100
- [x] R11: Confirm service restart freed VRAM before training
      (per TB-US-076 operational lesson)
- [x] R12: Monitor training; capture full loss trajectory in
      metrics table
- [x] R13: Adapter auto-registered as `adapter_versions.v5`;
      release + promote

### Phase 5 — Measurement

- [x] R14: Create E_in (in-sample baseline test; adapter v5 +
      harness v4 + prompt v3) and E_holdout (adapter v5 +
      harness v5 + prompt v3)
- [x] R15: Serial-run both at `n_samples=200`
- [x] R16: Capture results in both strict (harness
      answer-extraction) scoring

### Phase 6 — Documentation

- [x] R17: Trial #4 entry in `sweet-spot-search-log.md` filled
      in with what-we-did / what-we-found / what-we-decided /
      rationale
- [x] R18: Deep dive at
      `docs/math-example/instruct-scale-up-results.md`
- [x] R19: Update `docs/pages/staged-progression.md` with
      Trial #4's numbers (replaces or supplements Trial #2's
      19%/26%)
- [x] R20: Update `docs/math-example/sweet-spot-exploration.md`
      with Phase E section + pointer to Trial #4
- [x] R21: Update summary table in `sweet-spot-search-log.md`

### Phase 7 — Close

- [x] R22: Commit + push + close TB-US-077 + fire notification
- [x] R23: Candidate follow-up stories drafted (if any
      pre-registered hypothesis didn't land)

## Pre-registered hypotheses (Trial #4)

Written BEFORE training runs, locked into
`study-design.md` as the Trial #4 addendum. Phase 7's
measurement will mark each met / partial / not-met with the
measured values.

### H4a — In-sample

**Claim**: in-sample accuracy ≥ **60%** on the 200-problem
baseline test under the patched harness.

**Why 60%**: with Instruct base + 500 training examples + 5
epochs, we're training on top of a model that already achieves
~55–70% on GSM8K. The adapter should push in-sample to the
upper end of that range. Below 60% would indicate the training
is actively hurting (confusingly, this is possible with
Instruct bases + ill-matched LoRA data).

### H4b — Holdout (the headline)

**Claim**: holdout accuracy ≥ **55%** on the 200-problem
holdout test under the patched harness.

**Why 55%**: a floor that's clearly above the "bare Instruct
baseline" of ~55–70% suggests the adapter is contributing
something. If holdout matches or exceeds published Instruct
baselines (which it should), we've demonstrated the
train-on-domain-data pattern works end-to-end.

**Credibility threshold**: 55%+ holdout IS the "credible demo"
signal. Below that, we're not meaningfully improving on the
Instruct base.

### H4c — Generalization gap

**Claim**: `(in-sample − holdout)` ≤ **5 points**.

**Why 5pt**: a tight generalization gap on a well-trained
adapter is the methodology's gold-standard signal. Instruct
base + 500 samples + early stopping should land close to a
near-zero gap because the Instruct base is already good at
the task and we're reinforcing — not re-learning — the
behavior.

### H4d — Early stopping behavior

**Claim**: training will NOT run to 5 epochs; early stopping
will trigger around epoch 2–4 when eval_loss plateaus.

**Why**: Trial #3's eval loss started rising at epoch 8–9 (10
total). On a stronger Instruct base, the model is closer to
its performance ceiling faster, so eval loss should plateau
earlier. Running to 5 epochs anyway would indicate the task
needs even more training (unlikely for 500 samples on an
already-strong base).

## Acceptance Criteria

- [x] AC1: Early-stopping callback integrated in `train.py` + no
      regression on TB-US-065's launch flow
- [x] AC2: Training set v6 (500 random GSM8K train-split
      problems) registered on agent 3, released + promoted,
      strictly disjoint from holdout
- [x] AC3: Adapter v5 trained successfully with Instruct base;
      full loss trajectory captured
- [x] AC4: In-sample experiment at `n_samples=200` completes
      with results
- [x] AC5: Holdout experiment at `n_samples=200` completes
      with results
- [x] AC6: Trial #4 entry in `sweet-spot-search-log.md`
      populated with findings + decision + rationale
- [x] AC7: `instruct-scale-up-results.md` deep dive exists
- [x] AC8: Public `staged-progression.md` reflects Trial #4
      results
- [x] AC9: If H4b (≥55% holdout) is NOT met, follow-up story
      drafted with the next-trial-candidate scope (per
      TB-US-068 AC8 pattern)
- [x] AC10: Operator attests the Trial #4 result is credible
      enough for public demo (soft criterion)

## Design Notes

- **Why Instruct, not base.** Operator's framing on 2026-11-01:
  "19 and 26% will seem very low... how do we get that
  performance up?" The single biggest lever is the base-model
  swap identified in TB-US-057 Phase C's "path to performant
  numbers" section. Instruct variant is already instruction-tuned
  (follows `#### N` format naturally) + already weakly tuned for
  problem-solving (~60% zero-shot on GSM8K). Fine-tuning on top
  of that lands in the 70–85% range in published work.
- **Why 500 training samples, not 200 or 1000.** 200 was Trial
  #1's floor (just the failures); 1000 would be more but
  marginal returns on an already-strong base. 500 is a credible
  middle ground that trains in ~20–30 min on RTX 3090 and gives
  the adapter enough signal.
- **Why random sampling, not failure-targeted.** Trial #1's
  failure-targeted training set was pedagogically clean on a
  weak base (showed training explicitly fixing failures).
  Instruct base doesn't have the same failure profile — the
  bare model already handles many problems. Random sampling
  gives better coverage of the task distribution.
- **Why early stopping is an infrastructure addition, not a
  one-off config.** It's a reusable improvement to `train.py`
  benefiting every future training run. Trial #3's overfitting
  wouldn't have happened with early stopping; future retrains
  are protected by default.
- **Why NOT add format-drill examples.** Instruct variant
  natively produces `#### N` when prompted correctly (we have
  system prompt v3 which instructs this). The format-mismatch
  problem that Trial #1 surfaced was a base-model issue; we
  don't need to compensate for it on Instruct.
- **Pre-registration locks interpretation**: H4a-H4d numeric
  thresholds are stated BEFORE Phase 4-5 runs. No post-hoc
  adjustment.
- **One iteration only.** Same scope-cap as TB-US-075/076. If
  H4b doesn't land ≥55%, TB-US-078 captures the next attempt.

## Out of Scope

- Hyperparameter grid search / Bayesian optimization
- Multi-seed averaging (one run per experiment; stochastic
  variance accepted)
- RAG augmentation (TB-US-075 Phase 8 — still skippable)
- Alternative base models (DeepSeek, Mistral, Qwen) — stay
  on Llama 3.1 family for continuity
- Model distillation / larger-model comparisons
- Multiple-shot vs. zero-shot prompt engineering
- UI changes to display Trial #4 results automatically — manual
  doc updates only

## Related

- [TB-US-075](tb-us-075.md) — methodology + Trial #1
- [TB-US-076](tb-us-076.md) — Trials #2 + #3; harness patch;
  this story continues the search log
- [TB-US-057](tb-us-057.md) — Phase C's "biggest lever" path
  this story executes
- [TB-US-065](tb-us-065.md) — training launcher (early-stopping
  integration lands against)
- Files touched (during execution):
  - `training/math/train.py` (R3-R6, early stopping)
  - `scripts/prep_math_v6_random_scale.py` (new, R7)
  - `training-sets/math-example-v6-random-scale.jsonl` (new, R7)
  - `docs/math-example/study-design.md` (R1, append Trial #4)
  - `docs/math-example/sweet-spot-search-log.md` (R2, R17,
    R21 — entries + table)
  - `docs/math-example/instruct-scale-up-results.md` (R18, new)
  - `docs/math-example/sweet-spot-exploration.md` (R20)
  - `docs/pages/staged-progression.md` (R19)
  - `training_set_versions.v6` (R9)
  - `adapter_versions.v5` (R13)
  - `training_runs.id=10` (approx; R10)
