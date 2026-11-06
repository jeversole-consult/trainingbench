# Trial #9 — Rank Sweep at Attention + MLP (TB-US-085)

**Status**: Complete 2026-11-06
**Related story**: [TB-US-085](../user-stories/tb-us-085.md)
**Preceded by**: [Trial #8](mlp-expansion-results.md) (rank 16 at
attn+MLP; first positive capability-gain result)

## tl;dr

Doubling LoRA rank from 16 to 32 (adapter v10) on top of Trial
#8's attn+MLP target-module recipe lifted holdout mean from
53.75% to **60.12%** (+6.38pt). The result lands in the
**MARGINAL SIGNAL** bin of the pre-registered noise-envelope
framework (|diff|/pooled-SD = 1.70×, which is in the 1-2× bin
rather than the ≥2× "real signal" bin). Direction is
unambiguously positive; magnitude is uncertain at n=4 draws per
adapter. **Approaching the published 60-75% math-LoRA band for
the first time in the series.**

Secondary findings:
- Standard deviation rose (v9: 2.78pt → v10: 4.52pt), with spread
  10pt across 4 draws vs. v9's 6.5pt. **More capacity = more
  seed-level variability.**
- Within-P1-strict accuracy rose from 54.0% → 60.5%. Real
  reasoning gain.
- **Dual-#### retention re-intensified**: 46.8% (v9, bare-like)
  → 58.6% (v10). Unlike v9 which did NOT learn format rigidity,
  v10 picks it back up — presumably because the larger capacity
  can learn BOTH reasoning AND format rather than being forced
  to choose.
- Eval loss showed early-overfit signal at epoch 3 (0.423 →
  0.443). `load_best_model_at_end=True` captured the epoch-2
  checkpoint. Early stopping didn't fire (only 1 worsening
  observed; needs 2 consecutive).

## Research question

Does doubling LoRA rank from 16 to 32 at the Trial #8 attn+MLP
target-module set continue to help, or does it hit an overfit
wall at 1000 samples × 3 epochs?

## Context

Trial #8 (TB-US-082, closed 2026-11-04) landed the first
positive result in the research arc by expanding LoRA target
modules from 4 (attention) to 7 (attention + MLP) at rank 16.
Mean holdout 53.75% (+10.75pt above bare).

Trial #8's deep dive hypothesized that **the capacity trap at
rank 16 attn-only was specifically about which parameters LoRA
could touch**, not how many. Expanding to MLP gave the adapter
access to reasoning capacity.

Trial #9 tests the complementary question: **once the target
modules include MLP, does more rank continue to help?** Published
math-LoRA work typically uses ranks in the 16-64 range with
various target-module sets. Trial #4 (regression) had used rank
32 but with attention-only + raw-CoT format — a configuration
we now understand was doubly broken.

## Hyperparameters

Identical to Trial #8 EXCEPT LoRA rank (and alpha, which scales
with rank per standard practice):

| Hyperparameter | Trial #8 (v9) | **Trial #9 (v10)** |
|---|---|---|
| Base | Instruct | Instruct (same) |
| Training set | v7 (1000 samples) | **v7 (same — constant data)** |
| Target modules | 7 (attn + MLP) | 7 (same) |
| **LoRA rank** | 16 | **32** |
| **LoRA alpha** | 32 | **64** (2× rank, standard ratio) |
| LoRA dropout | 0.05 | 0.05 (same) |
| Learning rate | 1e-4 | 1e-4 (same) |
| Epochs | 3 | 3 (same) |
| Batch size × grad accum | 4 × 4 | same |
| Max eval samples | 200 | 200 (same) |
| Early stop | patience=2 | patience=2 (same) |

## Training trajectory

- **Duration**: 1732s (28.9 min, run_id 16)
- **Trainable params**: ~67M (~2× Trial #8's ~34M — doubling
  rank doubles LoRA matrices)
- **Train loss**: 2.55 → **0.296** (slightly lower than Trial
  #8's 0.34 final — fits training data a bit tighter)
- **Eval loss (per-epoch)**:
  - Epoch 1 (step 63): **0.426**
  - Epoch 2 (step 126): **0.423** ← best, selected via
    `load_best_model_at_end`
  - Epoch 3 (step 189): **0.443** ← rose +0.020 (early-overfit
    signal)
- **Early stopping**: patience=2 did not fire (1 worsening
  observed, needs 2 consecutive). `load_best_model_at_end=True`
  verifiably captured epoch-2 checkpoint (same mechanism as
  Trial #8).

Final adapter: `adapter_versions.v10`, content_sha256
`0c51dc8940a11c5ee207cd922e95b67576181246ddca9071ca55f2ff076d964f`.

## Measurement experiments

4 holdout experiments at n=200 (multi-seed per Trial #7 noise
envelope discipline):

| Experiment | Score |
|---|---|
| E36 (replicate-1) | 126 / 200 = **63.0%** |
| E37 (replicate-2) | 108 / 200 = **54.0%** |
| E38 (replicate-3) | 128 / 200 = **64.0%** |
| E39 (replicate-4) | 119 / 200 = **59.5%** |

**No baseline-test experiment** was run this trial — v9 already
established the attn+MLP adapter's baseline-test behavior
(48.5%); rank-32 baseline-test is a legitimate follow-up but
not needed for the primary mean-holdout comparison.

## Results

### Holdout multi-seed statistics

- Draws: 63.0, 54.0, 64.0, 59.5
- **Mean**: **60.12%**
- SD (sample, n-1): **4.52pt**
- Range: 54.0 – 64.0 (spread **10.0pt**)

### Pre-registered noise-envelope outcome (vs. v9)

Using the 2026-11-03 Trial #7 framework:

- v9 mean (Trial #8): 53.75% (SD 2.78pt)
- v10 mean (this trial): 60.12% (SD 4.52pt)
- Difference in means: **+6.38pt**
- Pooled SD: **3.75pt**
- |diff| / pooled SD: **1.70×**

| Threshold | Bin | Verdict |
|---|---|---|
| < 1× pooled SD | Indistinguishable | — |
| **1-2× pooled SD** | **Marginal signal** | ✅ this trial |
| ≥ 2× pooled SD | Real signal | — |

**MARGINAL SIGNAL**. Direction clearly positive; magnitude
uncertain at n=4 per adapter. Resolving would require more
seeds (n=8+ per adapter) or lower-variance measurement
(larger n per experiment, explicit-seed replication).

### Per-sample pattern analysis

**Within-P1-strict accuracy** (per `#### N` output):
- Bare Instruct: 48.2%
- Adapter v7 (attn-only, Trial #5): 44.7%
- Adapter v8 (attn-only, 5000 samp, Trial #6): 42.9%
- Adapter v9 (+MLP, Trial #8): 54.0%
- **Adapter v10 (+MLP, rank 32, Trial #9)**: **60.5%** (+5.8pt
  over v9; +12.3pt over bare)

**Dual-#### retention**:
- Bare: 45%
- Adapter v7: 61% (intensified)
- Adapter v8: 75% (more intensified)
- Adapter v9: 47% (bare-like, NOT intensified — Trial #8 finding)
- **Adapter v10: 58.6%** (**re-intensified** — unlike v9)

### Full-series comparison (holdout; multi-seed means)

| Setup | Holdout mean | Dual-#### | Within-P1-strict |
|---|---|---|---|
| Bare Instruct | 43.0% (single draw) | 45% | 48.2% |
| Adapter v5 (Trial #4, raw-CoT, rank 32) | 23.0% (single draw) | 20% | 24.3% |
| Adapter v7 (Trial #5, attn-only, rank 16) | 42.00% ± 2.65 (n=4) | 61% | 44.7% |
| Adapter v8 (Trial #6, attn-only, 5000) | 41.62% ± 2.56 (n=4) | 75% | 42.9% |
| Adapter v9 (Trial #8, +MLP, rank 16) | 53.75% ± 2.78 (n=4) | 47% | 54.0% |
| **Adapter v10 (Trial #9, +MLP, rank 32)** | **60.12% ± 4.52 (n=4)** | **59%** | **60.5%** |

## Interpretation

### More capacity, used differently

Trial #8's finding: rank 16 attn+MLP learns reasoning (within-P1
+5.8pt vs bare) but not format rigidity (dual-#### bare-like).

Trial #9's finding: rank 32 attn+MLP learns reasoning MORE
(within-P1 +12.3pt vs bare — more than double v9's improvement)
AND also learns format rigidity (dual-#### 59%, back up from
v9's 47%).

**Interpretation**: with 2× more capacity at the same target
modules, the adapter is no longer forced to choose between
format and reasoning — it can allocate capacity to both. v10's
larger overall accuracy (+6.4pt over v9) comes from the
reasoning gain; the format re-intensification is a byproduct
of extra capacity, not the driver of accuracy.

Contrast this with Trial #6 (5000 samples at rank 16 attn-only),
which ALSO intensified dual-#### (75%) but did NOT gain
within-P1 accuracy (42.9%). There, more training signal
reinforced the format pattern without unlocking reasoning
(capacity trap still in effect). Trial #9 shows that WITH MLP
reach + more rank, more training signal DOES produce reasoning
gains, not just format reinforcement.

### The SD jump

v10's SD (4.52pt) is ~63% larger than v9's (2.78pt). Possible
explanations:

1. **Larger adapters have higher seed sensitivity**: more
   trainable params = more degrees of freedom, so the specific
   loss landscape minimum found depends more on initialization
   + draw-level randomness.
2. **Overfit proximity**: v10's epoch-3 eval loss rose; it's
   training closer to the overfit wall. Samples near the wall
   may have less stable behavior across stochastic generations.
3. **Pure sampling variance** at n=4: the SD estimate itself
   has ~30% error at n=4, so the gap v9 → v10 may be partially
   SD-estimation noise.

Distinguishing these would require more draws. For the series
conclusion, the key observation is: **v10 is noisier than v9**,
not necessarily more stable in production.

### Overfit proximity concern

v10's training did show an early-overfit signal (epoch 3 eval
+0.020 vs. epoch 2). `load_best_model_at_end=True` caught the
right checkpoint. But this is a warning for anyone attempting
further rank increases or longer training at this data size:
rank 32 is near the overfit wall at 1000 samples × 3 epochs.
Rank 64 at the same data would likely overfit harder.

### Pre-registered hypothesis outcomes (Trial #9 did not pre-register formal hypotheses)

This trial fired without the formal H9a/H9b etc. structure
earlier trials used because it was launched conversationally
during audience/strategy discussion. Post-hoc:

- Does rank 32 at attn+MLP continue to help? ✅ YES (marginal
  signal; direction clear)
- Does it overfit catastrophically? NO (eval rose 0.02 at epoch
  3, but best-model-at-end caught the right checkpoint)
- Does it approach the published math-LoRA band? ✅ YES
  (60.12% is at the low end of the 60-75% published range)

**Not pre-registering was a methodological slip** that should
be noted for future trials. The result stands but the discipline
was weaker than Trials #5-#8.

## Decision + next-direction

**Trial #9 outcome**: positive, marginal-signal. Research arc
closes here per operator's 2026-11-06 decision (math arc has
served its purpose as PEFT demonstration; further compute is
not cost-justified for the current TB strategy).

**Current demo UPDATES**: adapter v10 at ~60% mean holdout
becomes the new demo. Pages site swap needed. v9 remains in
registry as historical.

**Not pursued** (operator decision, cost-conscious):
- Multi-seed resolution of the marginal-signal verdict
- Rank 64 at same target modules (overfit risk)
- Data scale-up at rank 32 attn+MLP
- Full fine-tune (Candidate C, TB-US-085's original conditional
  reservation)
- Best-of-N inference
- External-data augmentation (MATH, MGSM, synthetic)
- 70B model swap (hardware cost)

**Future direction** (stalite side, not TB):
- Small-dataset PEFT research (operator's genuine interest)
- Deployment pathway (open question)
- Proprietary-data vs. open-source separation (structural)

## Threats to validity (post-run)

- **Statistical (acknowledged)**: n=4 per adapter + 4.52pt SD
  places this result in the "marginal signal" bin, not "real
  signal." Direction is confident; magnitude is uncertain.
- **No pre-registration** (acknowledged): trial fired
  conversationally without formal H-threshold discipline.
  Result is still interpretable but the methodology was weaker.
- **No baseline-test for v10**: Trial #9 skipped the baseline-
  test cross-reference that Trial #8 included. Could run
  retroactively if operator wants.
- **Single-trial confidence**: no replication of the specific
  v10 configuration. A second v10-equivalent training with
  different training-seed might land anywhere in the measured
  spread (54-64%).
- **GSM8K-specific**: all prior external-validity caveats
  apply.

## Reproducibility

- Base model: `meta-llama/Meta-Llama-3.1-8B-Instruct` (HF Hub main)
- Training-set sidecar:
  `training/datasets/training_set_versions/v7.jsonl`
- content_sha256: `13adefc8426b983f45cd5a7618f60aaa022846f3405f9660d7a4ec611c759622`
- Training script: `training/math/train.py` at TB-US-085 close commit
- Hyperparameters: see "Hyperparameters" section
- Hardware: RTX 3090, 24 GB VRAM
- Software: `transformers` 5.x + bitsandbytes 4-bit QLoRA
- Adapter v10: `adapter_versions.v10`, `adapters/math-example/v10`,
  content_sha256 `0c51dc8940a11c5ee207cd922e95b67576181246ddca9071ca55f2ff076d964f`
- Measurement experiments: E36, E37, E38, E39 (all holdout,
  harness v5); no baseline-test for this trial
- Random seeds: HF Trainer default (seed=42); generation
  implicit stochastic (do_sample=True, temperature=0.7, no
  explicit seed) — same as Trials #7-#8
- Elapsed wall-clock: training 1732s (28.9 min); each
  measurement experiment ~45-50 min; ~4h total for Phase 3
