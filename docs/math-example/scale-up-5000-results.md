# Trial #6 — Scale Up to 5000 Samples (TB-US-080 Candidate A)

**Status**: Complete 2026-11-03
**Related story**: [TB-US-080](../user-stories/tb-us-080.md)
**Preceded by**: [Trial #5](instruct-chat-template-results.md) — chat-template
format fix preserved bare Instruct but didn't improve on it

## tl;dr

Scaling training data 5x (1000 → 5000 chat-template-formatted
samples) did NOT lift accuracy and **modestly regressed** vs.
both Trial #5 and bare Instruct. Adapter v8 scored **37.5%
baseline-test** (vs. Trial #5's 44.0%, bare's 43%) and **42.5%
holdout** (vs. Trial #5's 44.5%, bare's 43%). Within-noise on
holdout but direction DOWN; clearly outside noise on
baseline-test. **Dual-#### retention intensified from 60% →
74%**, meaning the adapter learned the structural format even
more rigidly while losing accuracy. **The Trial #5 "format and
capability are decoupled" finding is now pronounced: more
training data at this config = more format overfitting = less
capability.** Published math-LoRA literature predicts data
scale-up as a lift lever; it did not work here. Three plausible
mechanisms (dataset exhaustion, LoRA capacity trap, cascade
overfitting). TB-US-081 queued with 3 remaining candidate levers
(B expand to MLP / C full fine-tune / D multi-seed resolve the
noise question).

## Research question

Does scaling the training set 5x (1000 → 5000 chat-template-
formatted samples) unlock the capability-gain that Trial #5
confirmed was missing (format fix alone did not add math
reasoning)?

## Context

Trial #5 (TB-US-079) landed a positive-null: chat-template-
formatted PEFT **preserved** bare Instruct's 43% but did NOT
**improve** on it. Within-structure accuracy was slightly LOWER
than bare's (adapter v7 44.7% vs. bare 48.2% per P1_strict
output). Published math-LoRA literature (Qwen, MetaMath,
DeepSeek) uses 10,000-50,000+ samples; Trial #5's 1000 was
undersized by an order of magnitude.

Candidate A pre-registered: scale to 5000 samples (5x) with
all other hyperparameters identical to Trial #5. Pre-registered
decision thresholds locked before results seen.

**Note flagged pre-run**: GSM8K's train split contains only
**7473 rows total**. 5000 = 67% of all available data. Overlap
with v7 was 698/1000 (random-sampling-expected 669), so "new
signal" vs. v7 is only ~302 fresh problems. The experiment is
closer to "see each sample ~3x more via epochs" than "see 5x
different samples".

## Hyperparameters

Identical to Trial #5 except training-set size.

| Hyperparameter | Trial #5 (v7) | **Trial #6 (v8)** |
|---|---|---|
| Base | Instruct | Instruct |
| Training set | v7 (1000 samples, seed=46) | **v8 (5000 samples, seed=47)** |
| LoRA rank | 16 | 16 |
| LoRA alpha | 32 | 32 |
| Learning rate | 1e-4 | 1e-4 |
| Epochs | 3 | 3 |
| Batch size × grad accum | 4 × 4 = 16 effective | same |
| Max eval samples | 200 | 200 |
| Early stop | patience=2 | patience=2 |
| Load best model at end | True | True |

## Training trajectory

- **Duration**: 6835s (1h 54min, 939 optimizer steps vs. Trial
  #5's 189)
- **Train loss**: 2.289 (step 25) → 0.377 (step 925). Smooth
  convergence; no instability.
- **Eval losses (per-epoch)**:
  - Epoch 1 (step 313): **0.4170**
  - Epoch 2 (step 626): **0.4121** ← best, selected via
    `load_best_model_at_end=True`
  - Epoch 3 (step 939): **0.4136** ← slight worsening (+0.0015)
- **Early stopping** (patience=2) did NOT fire — only 1 worsening
  eval observed (epoch 3 vs. epoch 2); needs 2 consecutive to
  trigger. **Infrastructure validated** (3 evals computed,
  `load_best_model_at_end` correctly selected checkpoint-626
  — MD5 of final/adapter_model.safetensors matches
  checkpoint-626, not checkpoint-939).

Final adapter: `adapter_versions.v8`, released + promoted,
content_sha256 `45811c85…`, from epoch-2 (best eval) checkpoint.

## Measurement experiments

Two experiments at n=200 (reuses E22 as bare-Instruct holdout
control from Trial #5):

| Experiment | Setup | Score |
|---|---|---|
| E23 (E_in_v8) | adapter v8 × baseline-test | **75 / 200 (37.5%)** |
| E24 (E_holdout_v8) | adapter v8 × holdout — primary | **85 / 200 (42.5%)** |

## Results

### Full series comparison

| Setup | baseline-test | holdout | dual-#### retention |
|---|---|---|---|
| Bare Instruct | 86/200 (43.0%) | 86/200 (43.0%) | 45-46% |
| Adapter v5 (Trial #4) | 38/200 (19.0%) | 46/200 (23.0%) | 20-24% |
| Adapter v7 (Trial #5, 1000) | 88/200 (44.0%) | 89/200 (44.5%) | 60-63% |
| **Adapter v8 (Trial #6, 5000)** | **75/200 (37.5%)** | **85/200 (42.5%)** | **74-74.5%** |

### Pre-registered hypothesis outcomes

| H | Threshold | Result | Verdict |
|---|---|---|---|
| H6-primary | holdout ≥ 50% | 42.5% | ❌ NOT MET |
| H6a | within-P1-strict accuracy ≥ 50% | 42.9% (holdout) | ❌ NOT MET |
| H6b | holdout ≥ 43% (no regression) | 42.5% (holdout); 37.5% (baseline-test) | ❌ MARGINAL on holdout; **failed on baseline-test by 5.5pt** |
| H6c-strong | holdout ≥ 60% | 42.5% | ❌ NOT MET |
| H6d | early stopping triggers | infrastructure validated; didn't fire (only 1 worsening eval, needed 2) | ✅ INFRASTRUCTURE WORKED (verifiably) |

### Pre-registered decision mapping outcome

From the TB-US-080 pre-registered table:

> | 43–48% | Within-noise of bare; data scale didn't help | TB-US-081 — pursue Candidate B/C (different lever) |

Trial #6 holdout = 42.5% → within-noise of bare 43%, direction
down. Falls in the **"data scale didn't help"** bucket, with
the extra wrinkle that baseline-test clearly regressed (-5.5pt)
beyond the noise band. Pre-registered next step: pursue B/C/D
levers in TB-US-081.

### Harness-priority breakdown (holdout only — primary)

**E24 (adapter v8 holdout)**:
- P1_strict (`#### N`): 198/200 (99%), 85 correct (42.9% within)
- P3_trailing_number: 2/200, 0 correct

**E21 (adapter v7 holdout, Trial #5)**:
- P1_strict: 197/200 (98.5%), 88 correct (44.7% within)
- P3_trailing_number: 3/200, 1 correct

**E22 (bare Instruct holdout)**:
- P1_strict: 168/200 (84%), 81 correct (48.2% within)
- P1_unit_prefix: 16/200, 4 correct
- P2_final_answer: 3/200, 0 correct
- P3_trailing_number: 13/200, 1 correct

Adapter v8 → v7 → bare progression in within-P1-strict accuracy:
**42.9% → 44.7% → 48.2%**. Each training step moves farther from
the base's within-structure capability.

### Dual-`####` retention — the surprising intensification

| Setup | dual-#### retention (holdout) |
|---|---|
| Bare Instruct | 45.0% |
| Adapter v7 (Trial #5) | 60.5% |
| **Adapter v8 (Trial #6)** | **74.5%** |

The adapter learned the GSM8K-native dual-#### structure MORE
intensely as training data increased. v8 produces dual-#### in
74.5% of outputs vs. bare's 45%. Yet accuracy per output is
LOWER (42.9% vs. 48.2% within P1_strict).

Within dual-#### outputs specifically:
- Bare holdout, 2+ `####` outputs: 51.4% + 49.1% ≈ 50% correct
- Adapter v8 holdout, 2+ `####` outputs: 25.0% + 33.3% ≈ 30% correct

**The adapter learned to CONFIDENTLY emit dual-#### on 74.5% of
outputs, but those confidently-emitted answers are wrong 70% of
the time.** Confidence is learned; correctness is not.

## Interpretation

### The decoupling finding, intensified

Trial #5 observed that format and capability are decoupled
(adapter v7 learned format perfectly but matched bare accuracy).
Trial #6 pronounces this: as training data increases, the
adapter learns the format EVEN MORE intensely while LOSING
within-structure accuracy.

### Three plausible mechanisms (not mutually exclusive)

1. **Dataset exhaustion**. 5000/7473 = 67% of GSM8K training.
   The marginal 302 fresh problems (vs. v7) may carry diminishing
   returns. Beyond some threshold, scaling within a fixed corpus
   just means "see each pattern more times" — reinforcing
   whatever is strongest in the data. In GSM8K's case, the
   strongest signal is the dual-#### formatting pattern.
2. **LoRA capacity trap at rank 16**. The LoRA has limited
   expressive capacity. When training data increases, the model
   must allocate that capacity across patterns. Format
   (consistent across all 5000 samples) competes with reasoning
   (varies per problem). At 1000 samples the balance tipped
   toward format-and-some-reasoning. At 5000 samples format wins
   decisively. Higher rank (32, 64) might change this balance.
3. **Format-overfitting cascade**. The adapter is explicitly
   trained to produce `#### N`-ended outputs. More training
   examples = more reinforcement of the pattern = model emits
   `#### N` confidently even for problems where it's uncertain.
   Confident wrong answers replace hedged correct ones (bare
   Instruct's 11-16 unit-prefix + 13 trailing-number outputs
   are all gone in v8).

### What this means for the research question

The research question for Trial #6 was: does more training data
unlock capability? **The answer is no at this configuration.**
Three downstream possibilities:
- (a) Data alone isn't the lever (TB-US-081 B/C needed to test
  parameter-capacity and perturbation-magnitude levers).
- (b) GSM8K is too small a corpus; need to add external data
  (synthetic, MATH, MGSM) — out of scope for this series.
- (c) The result is partially noise; multi-seed replicate
  (TB-US-081 Candidate D) would resolve.

### Threats to validity (post-run)

- **Statistical** (most important): single-run comparison at
  n=200. Trial #5 (44.5%) and Trial #6 (42.5%) are within ±5pt
  binomial noise of each other. Only multi-seed replicate can
  tell real-signal from noise. Noted in TB-US-081.
- **Internal**: training completed cleanly (eval loss progression
  monotonic 0.417 → 0.412 → 0.414; infrastructure validated).
  Load-best-model-at-end verified via MD5 check of final/
  against checkpoints. V8 training set verified disjoint from
  holdout. No wiring bugs detected.
- **External**: GSM8K-specific; may not generalize to MATH,
  MGSM, SVAMP. Also Instruct-specific; different Instruct
  variants (Qwen, Mistral) may respond differently.
- **Construct**: "capability gain" = holdout accuracy by our
  harness. Alternative definitions (hard-subset accuracy,
  reasoning quality) could show lift that gross accuracy misses.

### Confirmation-bias checklist

- [x] Interpreted per pre-registered thresholds (H6-primary ≥50%,
      not met at 42.5%; H6b 43%, not met at 42.5% holdout and
      37.5% baseline-test; H6c-strong ≥60%, not met).
- [x] Reviewed ≥10 right + ≥10 wrong samples by hand via
      programmatic per-sample analysis in `tb_us_080_analysis.py`.
- [x] Reasonable alternative explanations considered (noise,
      capacity trap, dataset exhaustion, cascade overfit).
- [x] Would follow-up be different if result inverted?
      Pre-registered mapping: H6c-met → multi-seed replicate +
      Pages promotion. H6-primary-not-met + no regression →
      pursue B/C in TB-US-081. H6-regression-on-baseline-test
      (observed) → additional caution; multi-seed replicate is
      a high priority to confirm the direction.

## Decision + next trial direction

**Trial #6 outcome**: negative — scaling data did not help and
modestly hurt. Format decoupling intensified.

**Current demo**: UNCHANGED. Bare Llama 3.1 8B Instruct at 43%
remains the credible headline. Adapter v7 (Trial #5) is the
format-rigid variant with matching accuracy; adapter v8 (Trial
#6) is strictly inferior to v7 on measured dimensions.

**TB-US-081 (next trial)** — three remaining candidates from
TB-US-080's original scope:

- **Candidate B**: Expand LoRA target modules to include MLP
  (`gate_proj, up_proj, down_proj`). Tests whether MLP layers
  hold more math-reasoning capacity than attention alone.
  Cheapest to iterate (~45-60 min training).
- **Candidate C**: Full fine-tuning (not LoRA). Largest
  perturbation; tests whether the LoRA low-rank constraint is
  the capability ceiling.
- **Candidate D**: Multi-seed replicate of Trial #6 (and ideally
  Trial #5 too). Resolves the "is Trial #6's drop real or noise?"
  question. Doesn't move the ceiling but tightens interpretation.

**Recommendation (operator-decision)**: **Candidate D first**. If
Trial #6's regression is real, Candidates B and C are both
testable against a confirmed-not-noise baseline. If Trial #6's
drop is noise, we should know before investing in B or C.

If operator wants progress on the capability axis instead of
precision axis: **Candidate B**. Cheap enough that running it
first doesn't preclude D afterwards.

## Reproducibility

- Base model: `meta-llama/Meta-Llama-3.1-8B-Instruct` (HF Hub
  main)
- Training-set sidecar: `training/datasets/training_set_versions/v8.jsonl`
- `content_sha256 = ee83b5990044f94688f153b57d2b59d1cb9453ec715cb2a42022b9f93f66b03e`
- 5000 rows, seed=47, disjoint from holdout, 698-row overlap with v7
- Training script: `training/math/train.py` at TB-US-080 closure
  commit
- Prep script: `scripts/prep_math_v8_chat_template_5000.py`
- Hyperparameters: see "Hyperparameters" section
- Hardware: RTX 3090, 24 GB VRAM
- Software: TB-US-074 compat (`transformers` 5.x), bitsandbytes
  4-bit QLoRA
- Adapter: `adapter_versions.v8`, `adapters/math-example/v8`
- `adapter_content_sha256 = 45811c85fc22cba24eb91aad1176252618885b39e7ed286581401defcf09de9e`
- Measurement experiments: E23, E24 (bare control reuses E22)
- Random seeds: HF Trainer default (seed=42); training-set
  sampling seed=47; generation deterministic (do_sample=False)
- Elapsed wall-clock: training 6835s (1h 54min); E23 ~45 min;
  E24 ~45 min
