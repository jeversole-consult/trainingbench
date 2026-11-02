# Format-Retrain Results — TB-US-076 Option B (Trial #3)

**Owned by**: TB-US-076
**Created**: 2026-11-01
**Trial**: #3 in the [sweet-spot search log](sweet-spot-search-log.md)
**Partner doc**: [`harness-tolerance-results.md`](harness-tolerance-results.md)
  (Trial #2)

**Headline**: adapter v4 (10 epochs × 300 samples) **under-performed
adapter v3** (5 epochs × 200 samples) on both measures. Classic
overfitting — a cautionary data point, not a win.

## The hypothesis Trial #3 tested

After Trial #1 revealed adapter v3's output format was mostly
`Final Answer: N` rather than `#### N` (even though training
data + system prompt both specified `####`), the natural retrain
hypothesis was:

> **More exposure to `#### N` format examples + more epochs will
> drive the adapter to use the `#### N` marker, matching the
> harness's expected format.**

This was tested in parallel with Trial #2 (harness tolerance) as
part of TB-US-076 Option C. Trial #2 already proved the real
adapter v3 numbers were visible once the harness was patched, so
Trial #3 became "can we also fix the format at the training
level?".

## What we built

### Training set v5

`scripts/prep_math_v5_format_emphasis.py` built
**`training_set_versions.v5`** on agent 3:

- 200 original baseline failures (from TB-US-075 v4 training set)
- 100 additional GSM8K train-split problems (seed=44, strictly
  disjoint from the holdout at seed=43)
- Total: **300 (question, answer) rows**, each answer ending in
  `#### N`

Disjointness invariant preserved: training ∩ holdout = ∅ (all
holdout questions are from GSM8K train split with seed=43; the
new 100 extras exclude those by construction).

### Adapter v4 training

Pre-registered hyperparameters:

| Param | Trial #1 (v3) | Trial #3 (v4) |
|---|---|---|
| LoRA rank | 32 | 32 |
| LoRA alpha | 64 | 64 |
| LoRA dropout | 0.05 | 0.05 |
| learning_rate | 2e-4 | 2e-4 |
| **epochs** | **5** | **10** (doubled) |
| batch_size | 4 | 4 |
| gradient_accumulation | 4 | 4 |
| **max_train_samples** | **200** | **300** |
| max_eval_samples | 50 | 50 |

Steps per epoch for v4: ⌈300 / 16⌉ = 19 effective steps.
Total: 190 effective steps (vs. v3's 65) — **~3× the training**.

Trained as `training_runs.id=9` in 940s (~15.7 min) after the
Phase B rerun (first attempt as training 8 OOM'd — see
Operational section below).

## The loss curve told the story

| Step | Approx. epoch | train_loss | eval_loss |
|---|---|---|---|
| 50 | 2.6 | 1.26 | — |
| 100 | 5.3 | 0.91 | — |
| 150 | 7.9 | 0.72 | — |
| 152 | 8.0 | — | 1.38 |
| 171 | 9.0 | — | **1.57** ↑ |
| 190 | 10.0 | — | **1.68** ↑ |

**Train loss kept dropping** (0.91 → 0.72 across epochs 5→8)
**but eval loss ROSE** in the last two epochs (1.38 → 1.68).

This is the textbook overfitting signature:

- Model is memorizing training set (train loss drops toward 0)
- Loses generalization (eval loss on held-out tunes rises)
- Should have stopped at step 150 or so when eval loss hit minimum

**No early-stopping callback was enabled**, so the training ran
to the pre-registered 10-epoch budget. Adapter v4 was saved from
the final (worst-eval) step.

## Experiments

Registered post-restart (service restart freed VRAM after
training — see Operational section):

- **E15** (`experiment_id=15`): `tb-us-076b-rerun-e9e-in-sample-adapter-v4-harness-v4`
- **E16** (`experiment_id=16`): `tb-us-076b-rerun-e10e-holdout-adapter-v4-harness-v5`

Each 200-sample, ~40 min, strict scoring under the patched
harness v4/v5.

## Results

| Trial | Adapter | In-sample strict | Holdout strict |
|---|---|---|---|
| #2 (Trial 2 baseline for comparison) | **v3** (5 ep × 200) | **38 / 200 (19%)** | **52 / 200 (26%)** |
| #3 (this trial) | v4 (10 ep × 300) | **12 / 200 (6%)** | **15 / 200 (7.5%)** |

**Adapter v4 lost 13 pt in-sample + 18 pt holdout**. More
training made it worse, not better.

## H1/H2/H3 verdict for adapter v4

| Hypothesis | Threshold | Result | Verdict |
|---|---|---|---|
| H1 (in-sample ≥ 50%) | 50% | 6% | Not met |
| H2 (holdout ≥ 10%) | 10% | 7.5% | **NOT MET** |
| H3 (gap ≤ 15 pt) | 15 pt | 1.5 pt | Trivially met at low floor |

Adapter v4 fails H2 (where adapter v3 passed). Methodology
correctly flags this as a regression.

## Why it overfit

**Hypothesis mechanics**: 10 epochs on 300 small (short-form)
samples is a lot of exposure. The model had ~190 gradient steps
to memorize 300 specific problem→solution pairs. With no
regularization strong enough to prevent memorization (dropout
0.05 is light), the adapter learned the training set's specific
patterns rather than the underlying skill.

**Why Trial #1 (v3) didn't overfit**: 5 epochs × 200 samples =
65 steps. Just enough to pick up the general reasoning pattern
without memorizing specifics. v3's eval_loss trajectory
monotonically decreased (2.34 → 1.19) across all 5 epochs — no
rising-eval-loss warning.

**Lesson**: on small training sets, less is more. The
pre-registered "more exposure drives format" hypothesis was
wrong — more exposure drove memorization.

## Operational finding — service restart required

First attempt (TB-US-076 original chain daemon, training run 8)
**OOM'd within 60 seconds** of launch:

```
OutOfMemoryError: CUDA out of memory. Tried to allocate 112.00 MiB.
GPU 0 has a total capacity of 23.68 GiB of which 11.88 MiB is free.
Process 496911 has 15.47 GiB memory in use.
```

The culprit: TB server (pid 496911) was holding ~15 GB in its
PyTorch allocator cache from the just-finished E10c experiment.
QLoRA training needs ~13 GB cold, so the subprocess spawn
failed.

**Fix**: Phase B rerun daemon added `sudo systemctl restart
trainingbench.service` between the training completion and the
subsequent E9e/E10e experiment launches. Also, the daemon
re-mints a session token after the restart (token serializer
state is preserved across restart but token issuance is
atomic).

**Pattern**: when launching training after inference-heavy
sequences, insert a service restart to free the allocator pool.
This should become a documented part of the chain-daemon
pattern.

## What this trial proves

- **More training is NOT always better** on small datasets
- **Pre-registered methodology caught the regression**: H2
  verdict ("not met") is unambiguous; adapter v3 remains the
  demo artifact
- **Eval loss trajectory is the operational warning sign**:
  rising eval loss while train loss drops = stop training
- **Service restart matters**: back-to-back
  training-after-experiment chains need a VRAM reset

## What this trial does NOT prove

- That the 300-row v5 training set is bad — it may be fine with
  the right epoch count
- That the Instruct variant wouldn't do better — TB-US-057
  Phase C's "largest lever" is still untested
- That the shipped math-example demo should NOT retrain —
  retraining with early stopping or 5 epochs on v5 might still
  improve on v3

## Open questions (candidate next trials)

1. **Retrain adapter v5 at 5-7 epochs on the v5 training set**
   (same data, fewer epochs). Does more data at the right epoch
   count beat v3?
2. **Add early-stopping callback to `train.py`** so future runs
   auto-stop at min eval loss. Prevents this class of
   overfitting entirely.
3. **Smaller training set with higher weight / repetition**:
   drill the 100 extra examples heavier than the 200 failures?
4. **Swap base to Instruct variant**: likely the single biggest
   remaining lever.

None of these are drafted as stories. Operator picks what to
fire next.

## Reproducibility

- `scripts/prep_math_v5_format_emphasis.py` — training set
  reproducer (deterministic with seed=44)
- `training-sets/math-example-v5-format-emphasis.jsonl` — the
  built file (300 rows)
- `training_set_versions.v5` on agent 3 (released + promoted)
- `training_runs.id=9` in `training/runs/runs_tracker.db` — full
  training telemetry
- `adapter_versions.v4` on agent 3 (released + promoted) — files
  at `adapters/math-example/v4/`
- Experiments 15 + 16 in `backend/db/trainingbench.db`
