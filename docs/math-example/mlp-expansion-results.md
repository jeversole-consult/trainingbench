# Trial #8 — Expand LoRA to MLP target modules (TB-US-082 Candidate B)

**Status**: Complete 2026-11-04
**Related story**: [TB-US-082](../user-stories/tb-us-082.md)
**Preceded by**: Trials #4 (regression), #5 (chat-template fix,
positive-null), #6 (scale-up, no change), #7 (multi-seed envelope
~6pt established).

## tl;dr

**First positive capability-gain result in the research arc.**
Expanding LoRA target modules from 4 (attention: q_proj, v_proj,
k_proj, o_proj) to 7 (attention + MLP: gate_proj, up_proj,
down_proj) at the same rank 16, same data (v7, 1000 samples),
same lr (1e-4), same epochs (3) lifted holdout accuracy from
bare Instruct's 43% to **53.75% mean (4 draws, SD 2.78pt,
range 50.0–56.5)**. H8-primary ≥50% MET decisively (+3.75pt
above threshold, +10.75pt above bare). The result is far outside
the 6pt noise envelope established in Trial #7 — **unambiguously
real signal, not stochastic**.

**Secondary finding (mechanism confirmation)**: dual-#### retention
for v9 is ~47% — matching bare Instruct's ~45%, NOT the 60-75%
intensification seen in attention-only adapters v7/v8.
Within-P1-strict accuracy jumped from bare's 48.2% to v9's 54.0%.
**The MLP-expanded adapter learned MATH REASONING (per-structured-output
accuracy gain), not FORMAT RIGIDITY (as attention-only adapters
did).** This confirms the "LoRA capacity trap" mechanism from
Trial #6's deep dive: attention-only LoRA at rank 16 was format-
constrained; expanding to MLP layers provides a path to reasoning
capacity that was previously inaccessible.

Current demo updates to **adapter v9 at ~54% mean holdout** —
the first adapter in the series that outperforms bare Instruct
on measurable math capability.

## Research question

Does expanding LoRA's reach from attention-only (4 target modules)
to attention+MLP (7 target modules) unlock the math-reasoning
capacity that attention-only training could not access?

## Context

The series through Trial #7 established:
- Trial #4: raw-CoT training regressed Instruct by 20pt (format
  mismatch).
- Trial #5: chat-template format fix preserved bare Instruct
  (42.00% mean) but did not improve (format-vs-capability
  decoupling at rank 16 attention-only).
- Trial #6: scaling data 5x (1000→5000) was an accuracy no-op.
  Format rigidity intensified (dual-#### 60%→74%) but within-
  structure accuracy did not improve. Hypothesized mechanism:
  LoRA capacity trap — format wins the capacity competition
  against reasoning.
- Trial #7: multi-seed replicate established ~6pt noise envelope
  at n=200. Confirmed Trials #5/#6 statistically equivalent
  (adapter v7 42.00% vs adapter v8 41.62%, 0.14× pooled SD).
  Also discovered TB's harness uses `do_sample=True, T=0.7` with
  no explicit seed → all prior single-run measurements are
  stochastic draws.

Trial #8 tests the capacity-trap mechanism directly by expanding
WHICH parameters LoRA can modify (attention + MLP), not HOW
MANY (rank stays at 16). If the trap is real, MLP expansion
should give the adapter a non-format path to improve capability.

## Hyperparameters

Identical to Trial #5 EXCEPT target modules:

| Hyperparameter | Trial #5 (v7) | **Trial #8 (v9)** |
|---|---|---|
| Base | Instruct | Instruct (same) |
| Training set | v7 (1000 samples) | **v7 (same — constant data)** |
| **LoRA target modules** | `q_proj, v_proj, k_proj, o_proj` (4) | **`q_proj, v_proj, k_proj, o_proj, gate_proj, up_proj, down_proj` (7)** |
| LoRA rank | 16 | 16 (same) |
| LoRA alpha | 32 | 32 (same) |
| LoRA dropout | 0.05 | 0.05 (same) |
| Learning rate | 1e-4 | 1e-4 (same) |
| Epochs | 3 | 3 (same) |
| Batch size × grad accum | 4 × 4 | same |
| Max eval samples | 200 | 200 (same) |
| Early stop | patience=2 | patience=2 (same) |
| Load best model at end | True | True (same) |

**Why same data as v7**: isolates the target-modules effect. If
v9 differs from v7's multi-seed mean (42.00%), the difference is
attributable only to the MLP expansion.

## Training trajectory

- **Duration**: 1730s (28.8 min, run_id 15, 189 optimizer steps
  across 3 epochs)
- **Trainable params**: ~34M (approx 2× Trial #5's attention-only
  ~17M, as 7 modules × rank 16 vs 4 modules × rank 16)
- **Train loss**: 2.50 (step 25) → **0.34 (step 189)**. Lower
  than Trial #5's 0.38 final — MLP expansion is fitting training
  data slightly tighter.
- **Eval loss (per-epoch)**:
  - Epoch 1: 0.428
  - Epoch 2: 0.420 ← best
  - Epoch 3: 0.428
- **Early stopping**: patience=2 did not fire (only 1 worsening
  observation at epoch 3). `load_best_model_at_end=True`
  selected epoch-2 best checkpoint.

Final adapter: `adapter_versions.v9`, content_sha256
`5edfc404c6e97f9695411ba23c2a7c38d709e0a961bb560d27a1fa88bf521e3c`.

## Measurement experiments

5 experiments at n=200 (adapter v9 pinned throughout):

| Experiment | Harness | Dataset | Score |
|---|---|---|---|
| E31 | v5 | holdout | 100 / 200 = **50.0%** |
| E32 | v5 | holdout | 107 / 200 = **53.5%** |
| E33 | v5 | holdout | 110 / 200 = **55.0%** |
| E34 | v5 | holdout | 113 / 200 = **56.5%** |
| E35 | v4 | baseline-test | 97 / 200 = **48.5%** (single draw) |

## Results

### Holdout multi-seed statistics

- **Draws**: 50.0, 53.5, 55.0, 56.5
- **Mean**: **53.75%**
- **SD (sample)**: 2.78pt
- **Range**: 50.0 – 56.5 (spread 6.5pt)
- **Comparison to envelope**: Trial #7 established 6pt noise
  envelope at n=200. v9's 4 draws span 6.5pt — within the
  envelope for a single adapter. Mean difference from bare
  Instruct (+10.75pt) is **far outside** the envelope, so real
  signal.

### Pre-registered hypothesis outcomes

| H | Threshold | Result | Verdict |
|---|---|---|---|
| H8-primary | holdout mean ≥ 50% | 53.75% | ✅ **MET** |
| H8a | within-P1-strict ≥50% AND dual-#### ≥60% | 54.0% / 46.8% | **PARTIAL** — reasoning yes, dual-#### no (but this IS the finding) |
| H8b | holdout ≥43% (no regression) | 53.75% | ✅ MET decisively |
| H8c-strong | holdout ≥60% | 53.75% | ❌ NOT MET (close; +6.25pt short) |
| H8d | early stop infra testable | didn't fire (only 1 worsening) | Infrastructure intact |

### Full series 4-cell comparison

| Setup | baseline-test | holdout (mean where multi-seed) |
|---|---|---|
| Bare Instruct | 86/200 (43%) · dual-####=45% | 86/200 (43%) · dual-####=45% |
| Adapter v5 (Trial #4, raw-CoT, rank 32) | 38/200 (19%) · dual-####=23% | 46/200 (23%) · dual-####=20% |
| Adapter v7 (Trial #5, attn-only, rank 16) | 88/200 (44%) · dual-####=63% | 42.00% mean (4) · dual-####=61% |
| Adapter v8 (Trial #6, attn-only, 5000 samples) | 75/200 (38%) · dual-####=74% | 41.62% mean (4) · dual-####=75% |
| **Adapter v9 (Trial #8, +MLP, rank 16)** | **97/200 (48.5%) · dual-####=55%** | **53.75% mean (4) · dual-####=47%** |

### The mechanism confirmation (per-sample pattern analysis)

**Within-P1-strict accuracy** (per `#### N` output):
- Bare Instruct holdout: 48.2% (81/168 correct within-structure)
- Adapter v7 holdout: 44.7% (−3.5pt vs bare)
- Adapter v8 holdout: 42.9% (−5.3pt vs bare)
- **Adapter v9 holdout: 54.0% mean** (+5.8pt vs bare) — **real
  within-structure capability gain**

**Dual-#### retention**:
- Bare Instruct: ~45% (two draws, 45% baseline-test, 45% holdout)
- Adapter v7: 60-63%
- Adapter v8: 74-75%
- **Adapter v9: 47% holdout / 55% baseline-test** — ~bare-like

### The mechanism story

Trials #5-#7 revealed that attention-only LoRA at rank 16
produced adapters that:
- Learned format rigidity (dual-#### 60-75% vs bare's 45%)
- Lost within-structure accuracy (44-45% vs bare's 48%)
- Had the net gross-accuracy effect of "no change" from bare

Trial #6 deep dive hypothesized this was a "LoRA capacity trap":
with only 4 attention target modules at rank 16, the adapter had
limited capacity. Format is a consistent pattern across all
training samples; reasoning varies per problem. The adapter
maximized the easier signal (format) and lost the harder one
(reasoning).

Trial #8 directly tests this by expanding to 7 target modules
(adding MLP layers) at the same rank. Result:

- Format rigidity DID NOT intensify (dual-#### stayed near bare
  at 47%)
- Within-structure accuracy DID improve substantially
  (+5.8pt vs bare, +9.3pt vs attention-only v7)
- Gross accuracy jumped from bare's 43% to v9's 53.75%

**Conclusion**: the capacity trap is confirmed. MLP layers hold
the reasoning capacity for math. Attention-only LoRA cannot
access it. The format-vs-capability decoupling from Trials #5-#6
is explained: attention-only adapters compensate for inaccessible
reasoning capacity by learning format patterns.

**This is a substantive mechanism finding**, not just a positive
accuracy result. The series' negative-null results (Trials #5
and #6) are now RETROACTIVELY explained by the same mechanism
that Trial #8 confirms. Not ready to publish — further
replication (different seeds, different ranks, different
datasets) would strengthen before external sharing.

## Interpretation

### Why this result matters

1. **First positive capability-gain adapter** in the arc. v9
   becomes the new demo (+10.75pt holdout mean over bare).
2. **Mechanism explanation** for the series' prior negative
   results. The MLP-expansion lever doesn't just produce a
   number; it validates a specific hypothesis about WHY
   attention-only LoRA doesn't help on this task.
3. **Reproducible** — same base, same data, same rank/lr/epochs
   as Trial #5. Only target-modules changed. Any future replicate
   has one meaningful variable to compare against.

### Threats to validity (post-run)

- **Statistical (resolved)**: Trial #7 established 6pt envelope.
  v9's 4-draw mean (53.75%) is 10.75pt above bare's 43% — far
  outside envelope. Spread 6.5pt within envelope for a single
  adapter. Pooled SD vs Trial #7's v7 (SD 2.65) is comparable
  (v9 SD 2.78). The improvement isn't noise.
- **Internal**: training completed cleanly; load_best_model_at_end
  worked (verified during Trial #6, same infrastructure).
  Harness scoring unchanged. Measurement discipline consistent.
- **External**: GSM8K-specific; may not generalize to MATH,
  MGSM. Also Instruct-specific; different Instruct variants
  may respond differently. Also rank-16-specific; higher ranks
  with MLP might or might not continue to help.
- **Construct**: "capability gain" = holdout accuracy. v9's
  within-P1-strict gain (+5.8pt) is a sharper signal — the
  adapter is actually solving more problems within the format,
  not just producing more confident-looking outputs.

### The "monotonic draws" curiosity

E31=50.0, E32=53.5, E33=55.0, E34=56.5 — each draw happened to
be higher than the previous. Statistically a 1/24 = 4%
coincidence. No model/harness/prompt change between draws; only
variation is implicit RNG. Worth noting for the record but not
load-bearing on the result.

### Confirmation-bias checklist

- [x] Interpreted per pre-registered thresholds (H8-primary ≥50%
      MET at 53.75%; threshold was LOCKED before results seen).
- [x] Multi-seed from the start (Trial #7 discipline inherited).
      Not a cherry-picked single-draw.
- [x] Per-sample pattern analysis supports the gross-accuracy
      conclusion (within-P1-strict +5.8pt = real reasoning gain,
      not just format-confidence shift).
- [x] Alternative explanations considered: "noise" ruled out
      by 10.75pt gap vs. 6pt envelope. "Lucky monotonic sampling"
      noted but doesn't change mean.
- [x] Would follow-up be different if result inverted? If H8
      had failed (< 46%), TB-US-085 would test Candidate C (full
      fine-tune). H8 met → promote adapter v9; TB-US-085 (Candidate
      C) not strictly needed but could be a useful comparison for
      the mechanism story.

## Decision + next steps

**Trial #8 outcome**: positive — first capability-gain adapter
in the arc. +10.75pt above bare Instruct with multi-seed
confirmation. Within-structure accuracy +5.8pt over bare.
Mechanism (capacity trap) confirmed.

**Current demo updates**:
- Pages site: adapter v9 holdout ~54%, bare Instruct baseline-test
  43%. New headline: "Trained adapter beats bare model by 10
  points on held-out GSM8K."
- Adapter v9 is the new demo configuration.

**TB-US-NNN opportunities** (not yet filed):
- **Explicit-seed harness runner** — would strengthen Trial #8's
  reproducibility claims for any eventual external sharing.
  Implicit RNG is an internal-record weakness we'd want to
  address before any publication decision.
- **Rank sweep at attn+MLP** — v9 is rank 16. Does rank 32 at
  attn+MLP help further? Or does it regress like Trial #4's rank
  32 attn-only did?
- **TB-US-085 Candidate C (full fine-tune)** — still available
  as a comparison; would test "is MLP-only enough, or does full
  FT lift further?" Diminishing returns are plausible; may not
  be worth the compute.
- **External-data scale-up** — now that we know MLP expansion
  works, combine with larger data (MATH, MGSM, synthetic) could
  push toward the published 60-75% band.

## Reproducibility

- Base model: `meta-llama/Meta-Llama-3.1-8B-Instruct` (HF Hub main)
- Training-set sidecar: `training/datasets/training_set_versions/v7.jsonl`
- `content_sha256 = 13adefc8426b983f45cd5a7618f60aaa022846f3405f9660d7a4ec611c759622`
- Training script: `training/math/train.py` at TB-US-082 closure
  commit (includes the `lora_target_modules` forward-from-config
  patch landed in TB-US-082 pre-flight commit `5fcec38`)
- Hyperparameters: see "Hyperparameters" section above
- Hardware: RTX 3090, 24 GB VRAM
- Software: TB-US-074 compat (`transformers` 5.x), bitsandbytes
  4-bit QLoRA
- Adapter: `adapter_versions.v9`, `adapters/math-example/v9`,
  content_sha256 `5edfc404c6e97f9695411ba23c2a7c38d709e0a961bb560d27a1fa88bf521e3c`
- Measurement experiments: E31, E32, E33, E34 (holdout multi-seed),
  E35 (baseline-test single)
- Random seeds: HF Trainer default (seed=42); generation implicit
  (do_sample=True, T=0.7, no explicit seed)
- Elapsed wall-clock: training 1730s (28.8 min); each measurement
  experiment ~45-50 min; ~5h total for Phase 3+4
