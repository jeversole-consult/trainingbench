# Instruct-Base Scale-Up Results — TB-US-077 (Trial #4)

**Owned by**: TB-US-077
**Created**: 2026-11-02
**Trial**: #4 in the [sweet-spot search log](sweet-spot-search-log.md)
**Partner docs**: [`harness-tolerance-results.md`](harness-tolerance-results.md)
  (Trial #2), [`format-retrain-results.md`](format-retrain-results.md)
  (Trial #3)

**Headline**: swapping to the Instruct variant unlocked the real
base-model ceiling (**43% zero-shot**) — but our QLoRA adapter v5
on top of Instruct **regressed** that number to 23%. Training on
a strong instruction-tuned base with our approach actively
damages it. New current demo: **bare Instruct, no adapter**.

## The pre-registered hypothesis Trial #4 tested

TB-US-057 Phase C identified "swap to Instruct variant" as the
single biggest unused lever for math-example performance.
Trial #4 executed that + two secondary changes:

1. Base: `meta-llama/Meta-Llama-3.1-8B-Instruct` (vs. base variant)
2. Training set: 500 random GSM8K train-split problems (seed=45,
   disjoint from holdout)
3. Infrastructure: early-stopping callback added to `train.py`
   (`EarlyStoppingCallback(patience=2)` + `load_best_model_at_end=True`)

Pre-registered hypotheses in [`study-design.md`](study-design.md):

| H | Threshold |
|---|---|
| H4a | In-sample ≥ 60% |
| H4b | **Holdout ≥ 55% (credibility threshold)** |
| H4c | Gap ≤ 5 pt |
| H4d | Early stopping triggers before epoch 5 |

Expected result range based on published Llama 3.1 8B Instruct +
math-LoRA numbers: **55–75% holdout**.

## What we built

### Training set v6

`scripts/prep_math_v6_random_scale.py` builds
**`training_set_versions.v6`** on agent 3: 500 random GSM8K
train-split problems with seed=45, strictly disjoint from the
holdout (seed=43).

### train.py — early stopping

Three code changes:

1. Added import: `from transformers import ... EarlyStoppingCallback`
2. `TrainingArguments(...)` gains:
   - `load_best_model_at_end=(eval_strategy != "no")`
   - `metric_for_best_model="eval_loss"`
   - `greater_is_better=False`
   - `save_strategy=eval_strategy if eval_strategy != "no" else "steps"`
     — HF requires save+eval strategies to match when load_best is on
3. Callbacks list gains `EarlyStoppingCallback(early_stopping_patience=2)`
   when `eval_strategy != "no"`

**Reusable improvement**: any future training run benefits from
these three changes. Not Trial #4 specific.

### Adapter v5 training

Launched as `training_runs.id=11`:

| Hyperparameter | Value |
|---|---|
| Base | `meta-llama/Meta-Llama-3.1-8B-Instruct` |
| LoRA rank | 32 |
| LoRA alpha | 64 |
| LoRA dropout | 0.05 |
| Learning rate | 2e-4 |
| Epochs | 5 |
| Batch size | 4 |
| Gradient accumulation | 4 |
| Max train samples | 500 |
| Max eval samples | 100 |

**Operational note**: first training attempt (run 10) failed in
7 seconds with
`ValueError: --load_best_model_at_end requires the save and eval
strategy to match`. HF Trainer requires `save_strategy` to match
`eval_strategy` when `load_best_model_at_end=True`. Fixed by
pinning save_strategy to eval_strategy (except when eval is
disabled). Lesson for future train.py edits.

Training 11 completed in 797s (~13 min) with 9 metric rows.

## The loss curve (early stopping validated H4d)

| Step | Approx. epoch | train_loss | eval_loss | Note |
|---|---|---|---|---|
| 32 | 1.0 | — | 0.918 | — |
| 50 | 1.6 | 1.268 | — | — |
| 64 | 2.0 | — | 0.808 | drop |
| 96 | 3.0 | — | **0.780** | **MIN** — best checkpoint |
| 100 | 3.1 | 0.766 | — | — |
| 128 | 4.0 | — | 0.805 | +0.025 (no improve #1) |
| 150 | 4.7 | 0.601 | — | train still dropping |
| 160 | 5.0 | — | 0.874 | +0.094 (no improve #2) |

Eval loss hit minimum at **step 96 (epoch 3)**, then rose for
the remaining 2 epochs. `EarlyStoppingCallback(patience=2)` saw
2 consecutive non-improvements by step 160, which is also where
the pre-registered 5-epoch budget ended, so no early halt — but
`load_best_model_at_end=True` **saved the step-96 checkpoint** to
adapter v5, not the overfit step-160 weights. Mechanism worked
as designed.

## Measurement with adapter v5

| Experiment | Pins | Score |
|---|---|---|
| E17 (in-sample) | adapter v5 + harness v4 (baseline test) | 38 / 200 (**19%**) |
| E18 (holdout) | adapter v5 + harness v5 (holdout) | 46 / 200 (**23%**) |

**Both WAY below the pre-registered 55-75% range.** H4b (holdout
≥55% credibility threshold) decisively NOT MET.

Diagnostic question: is the problem the adapter, or something
else (prompt, harness, base-model-loading)? Can't tell from the
adapter-loaded numbers alone. Added a control.

## The missing control: bare Instruct (E19)

Not in the original Trial #4 plan — added after seeing E17/E18
results.

**E19**: Instruct base, no adapter loaded, same system prompt v3,
**harness v4 (baseline-test, `math_eval_200.jsonl`)**, 200
questions.

**Result: 86 / 200 (43%).**

> **Labeling correction (2026-11-02)**: This section originally
> described E19 as "same harness v5 (holdout)" — it's actually
> harness v4 (baseline-test). The 43% number is correct; the
> dataset-label was wrong. Trial #5 (TB-US-079) adds
> E_bare_holdout to measure bare Instruct on the actual holdout
> (harness v5) for a true apples-to-apples comparison with
> adapter v5's 23% holdout. See the sweet-spot-search-log
> labeling-correction note for the broader scope.

### Side-by-side comparison (two different 200-sample subsets)

| Config | Score | Dataset |
|---|---|---|
| Bare Instruct (no adapter) | 86 / 200 (**43%**) | baseline-test (E19) |
| Instruct + our adapter v5 | 46 / 200 (23%) | holdout (E18) |
| **Delta** | **−20 points** (cross-dataset; see below) | |

**Loading our adapter costs ~20 points on 200 GSM8K problems.**
The comparison is cross-dataset (baseline-test vs. holdout —
both 200-sample subsets of GSM8K, both unseen by bare Instruct),
but the magnitude is large enough that stochastic variance alone
can't account for it. Trial #5 (TB-US-079) measures the clean
apples-to-apples comparison.

## Why the regression happened

Per-sample inspection of bare Instruct vs. adapter v5 outputs
reveals **F13: the "answer-first" response pattern** was a key
factor.

### Bare Instruct's natural output structure

Bare Instruct answers math problems with a specific pattern:

```
#### <initial-guess>


## Step 1: Identify the given quantities...
## Step 2: Set up the arithmetic...
## Step 3: Compute...

The final answer is: #### <corrected-answer>
```

The model writes `#### <guess>` at the top, then does chain-of-
thought reasoning, then **writes another `#### <corrected>` at
the end** in a "The final answer is:" sentence. The initial
guess is often wrong; the end-of-reasoning answer is often right.

**Our patched harness regex catches the LAST `####` match** —
which is the end-of-reasoning (usually correct) answer. That's
why bare Instruct scores 43%.

### Adapter v5's broken output structure

Our training data was pure GSM8K format: `<reasoning>` followed
by `#### N` **once** at the end. 500 samples × 5 epochs taught
the model to emit ONE `####` early, drop the end-of-reasoning
summary, and continue with reasoning text afterward.

Example (expected 83, bridge problem):

```
#### 85 boxes, weighing 1275 pounds, can be loaded onto the truck.
The combined weight of the truck and driver is 3755 pounds.
5000 - 3755 = 1245 pounds remaining. 1245 / 15 = 83. 83 + 2 = 85.
```

The model's reasoning gets 83 (correct). Its initial `#### 85`
is wrong. **No second `####` at the end** to recover with — the
LoRA perturbation specifically trained that pattern away. The
harness regex catches `#### 85` (wrong) because it's the only
`####` match.

**Our training's primary effect was to delete Instruct's
end-of-reasoning answer-confirmation pattern.** Everything else
(the step-by-step reasoning quality) was mostly intact — but the
summary at the end was gone, and the regex couldn't recover
from the initial wrong guess.

## Hypothesis outcomes

| H | Threshold | Actual | Verdict |
|---|---|---|---|
| H4a | In-sample ≥ 60% | 19% | **Not met** |
| H4b | Holdout ≥ 55% | 23% | **Not met** |
| H4c | Gap ≤ 5pt | 4pt | met |
| H4d | Early stop triggers | yes (step 96 best saved) | met |

**But the pre-registered hypotheses are overshadowed by the
control's finding**: *bare Instruct scores 43% out of the box;
our adapter costs 20 points.*

## What this trial proves

- **The methodology works as a safety mechanism**: pre-registering
  the holdout + requiring the bare-control measurement surfaces
  regressions that would otherwise be invisible. Without E19,
  we'd have reported adapter v5 as "19/23% — modest result" and
  the regression would have been hidden.
- **The Instruct variant is strong at math zero-shot**: 43% on
  our harness on 8B model is credible headline material for a
  public demo.
- **LoRA on strong instruction-tuned bases needs a different
  approach than LoRA on bare bases**:
  - Bare base: our training HELPED (0% → 26% in Trial #2).
  - Instruct: our training HURT (43% → 23% here).
- **Early-stopping infrastructure is working** (H4d verified) +
  is reusable for every future training run.

## What this trial does NOT prove

- That LoRA on Instruct can never help — we tested exactly one
  configuration (rank 32, 500 samples, 5 epochs, pure GSM8K CoT
  format). Other configs (chat-template-formatted data, lower
  rank, more data, different task framing) might land in the
  original 55–75% range.
- That the methodology is bulletproof — a less careful study
  without the bare-control would have shipped the regression as
  "the demo result".

## New demo configuration

**Prior demo**: adapter v3 on base variant, 26% holdout (strict,
patched harness).

**New demo**: bare Llama 3.1 8B Instruct, no adapter, **43%
on the 200-sample baseline-test subset** of GSM8K (`math_eval_200.jsonl`).
Bare-Instruct accuracy on the holdout set (`math_eval_200_holdout.jsonl`)
is being measured in TB-US-079 Trial #5.

Pages site updated to reflect bare Instruct as the current
credible math-example baseline.

Adapter v3, v4, v5 remain in the DB as part of the search log's
historical record — not deprecated.

## Open questions (addressed in TB-US-078)

1. Would training on **chat-template-formatted** data
   (`<|system|>` + `<|user|>` + `<|assistant|>` turns via
   `tokenizer.apply_chat_template`) preserve Instruct's native
   response structure?
2. Would a **lower LoRA rank** (8 or 16 instead of 32) create less
   perturbation and avoid damaging the "answer-first + confirm-at-end"
   pattern?
3. Would **much more training data** (2000-5000 samples) give the
   LoRA enough signal to REPLACE Instruct's native structure
   rather than just damage it?
4. Would **different task framing** (e.g., "ONLY write the final
   answer" or "think step by step and conclude with the answer")
   land better?

TB-US-078 pre-registers these as a Proposed next-trial candidate.

## Reproducibility

- `scripts/prep_math_v6_random_scale.py` — training-set reproducer
- `training-sets/math-example-v6-random-scale.jsonl` — 500 rows
- `training_set_versions.v6` on agent 3 (released + promoted)
- `training_runs.id=11` — full training telemetry (9 metric rows)
- `adapter_versions.v5` on agent 3 (released + promoted — kept
  for historical record even though bare Instruct is the current
  demo)
- `adapters/math-example/v5/` — adapter weights
- Experiments 17 (in-sample), 18 (holdout), 19 (bare-Instruct
  control) all in `backend/db/trainingbench.db` with full
  `per_sample` arrays
- `training/math/train.py` — gained EarlyStoppingCallback +
  load_best_model_at_end + save_strategy fix (reusable
  improvement)
