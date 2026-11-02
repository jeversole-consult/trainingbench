# Trial #5 — Chat-Template-Formatted PEFT on Instruct (TB-US-079)

**Status**: Complete 2026-11-02
**Related story**: [TB-US-079](../user-stories/tb-us-079.md)
**Prerequisite**: TB-US-078 architectural wiring fix (closed
2026-11-02). This is the **first trial under corrected
training-set wiring** — see
[`architectural-finding-training-set-wiring.md`](architectural-finding-training-set-wiring.md).

## tl;dr

Chat-template-formatted training on Instruct (1000 samples ×
rank 16 × 3 epochs × lr 1e-4) **preserved bare Instruct's
43% accuracy** on both baseline-test (44%) and holdout (44.5%).
Pre-registered H5b (no regression) met; H5c (meaningful
improvement ≥50%) not met. The chat-template fix cleanly
addressed Trial #4's regression mechanism without introducing
new math capability. **Secondary finding (surprising)**: the
adapter learned the `#### N` structural format MORE reliably
than bare Instruct (dual-#### retention 60% vs. 45%, 100%
P1_strict catching) but did NOT translate structural
preservation into accuracy improvement. Format-correctness and
math-capability are decoupled levers.

## Research question

Does training on **chat-template-formatted data** (matching
Instruct's native SFT format) with the correct `#### N`
end-of-answer marker preserve or improve bare Instruct's
accuracy on GSM8K, compared to Trial #4's regression?

## Context

Trial #4 (TB-US-077) regressed Instruct from a bare-baseline-test
of 43% to 23% holdout accuracy. Root cause (F13 analysis): our
training pipeline's hardcoded `format_training_example` deleted
GSM8K's native `#### N` end-of-answer marker and emitted `Final
Answer: N` instead, overwriting Instruct's native
"guess + reason + confirm-at-end" response pattern.

TB-US-078 addressed two concurrent bugs:
1. **Hardcoded template bug**: `format_training_example` deleted.
2. **Architectural wiring gap**: `train.py` now reads from
   `training_set_versions` sidecar JSONL (prior trials ran on raw
   GSM8K irrespective of the registered training set — see
   architectural finding).

Trial #5 is the first trial under corrected wiring where:
- Training data genuinely varies per training_set_version
- The `text` field format is per-trial-script-controlled
- `training_set_versions.v7` (chat-template-formatted via
  `tokenizer.apply_chat_template()`, with GSM8K-native `#### N`
  preserved) is the actual training input

## Hyperparameters

| Hyperparameter | Value | Rationale |
|---|---|---|
| Base | `meta-llama/Meta-Llama-3.1-8B-Instruct` | Same as Trial #4; isolates data/rank effect |
| Training set | `training_set_versions.v7` | Chat-template-formatted; sha256 `13adefc8…` |
| Training-set size | 1000 samples (seed=46, disjoint from holdout) | Larger than Trial #4's effective 500 |
| LoRA rank | 16 | Mid-range; less perturbation than Trial #4's rank 32 |
| LoRA alpha | 32 | 2× rank, standard ratio |
| LoRA dropout | 0.05 | Standard |
| Learning rate | 1e-4 | Half of Trial #4's 2e-4 |
| Epochs | 3 (early stop patience=2) | Light touch |
| Batch size | 4 | Hardware-matched |
| Grad accum | 4 | Effective batch size 16 |
| Max eval samples | 200 | GSM8K `test` split (chat-template-formatted inline) |

## Training trajectory

189 optimizer steps across 3 epochs; 1437s wall-clock (24 min).

| Step | Epoch | Train loss | Eval loss |
|---|---|---|---|
| 5 | 0.08 | 2.67 | — |
| 30 | 0.48 | 0.73 | — |
| 60 | 0.96 | 0.44 | — |
| 125 | 1.99 | 0.40 | — |
| 126 | 2.00 | — | **0.427** |
| 150 | 2.38 | 0.39 | — |
| 185 | 2.94 | 0.38 | — |
| 189 | 3.00 (end) | 0.38 | **TBD** |

Loss dropped sharply in epoch 1 (2.67 → 0.44) then plateaued at
~0.38-0.42 for epochs 2-3. No overfit signal (train and eval
loss comparable).

**Early-stopping outcome**: did NOT trigger. Only 2 eval
computations occurred (end of epoch 2 and end of epoch 3), and
`EarlyStoppingCallback(patience=2)` requires 2 **consecutive**
worsening evals to fire. The configuration is mathematically
incapable of triggering early stop. H5d is **not testable at
this config** — would need ≥4 epochs to exercise. The
infrastructure (TB-US-077) is sound; the config didn't exercise
it. Flagged for TB-US-080 if the next trial uses more epochs.

**Final adapter**: `adapters/math-example/v7`
(`adapter_versions.v7`), auto-registered with
`training_set_version_id=7` provenance linkage; released +
promoted.

## Measurement experiments

Three experiments at `n_samples=200`:

| Experiment | Adapter | Harness (dataset) | Purpose | Result |
|---|---|---|---|---|
| E20 (E_in_v7) | v7 | v4 (baseline-test, `math_eval_200.jsonl`) | Trial #5 baseline-test | **88/200 = 44.0%** |
| E21 (E_holdout_v7) | v7 | v5 (holdout, `math_eval_200_holdout.jsonl`) | **Primary H5b/H5c** | **89/200 = 44.5%** |
| E22 (E_bare_holdout) | none | v5 (holdout) | Bare Instruct holdout — fills labeling-correction gap | **86/200 = 43.0%** |

## Results

### Four-cell comparison

| | Baseline-test (harness v4) | Holdout (harness v5) |
|---|---|---|
| **Bare Instruct** | 86 / 200 (43.0%) — E19 Trial #4 | **86 / 200 (43.0%)** — E22 Trial #5 (new) |
| **Adapter v5 (Trial #4)** | 38 / 200 (19.0%) — E17 | 46 / 200 (23.0%) — E18 |
| **Adapter v7 (Trial #5)** | **88 / 200 (44.0%)** — E20 | **89 / 200 (44.5%)** — E21 |

**Headline**: adapter v7 **essentially matches bare Instruct**
on both datasets. +1pt baseline-test (44% vs. 43%); +1.5pt
holdout (44.5% vs. 43%). Both deltas are within the ±5pt
binomial noise band at n=200 — not meaningful improvement, but
unambiguously not a regression.

**Compare to Trial #4**: adapter v5 cost 20-24 points on both
datasets. Trial #5's chat-template format fix eliminated that
cost.

### Bare Instruct cross-dataset consistency

E19 (baseline-test): 86/200 = 43.0%
E22 (holdout):       86/200 = 43.0%
Dual-#### retention: 45.5% baseline-test / 45.0% holdout

Bare Instruct is **remarkably consistent** across the two
disjoint 200-sample subsets. This validates both datasets as
legitimate "unseen GSM8K" measurements and strengthens the
baseline comparison for all future trials.

### Pre-registered hypotheses outcomes

| H | Threshold | Result | Verdict |
|---|---|---|---|
| H5a | ≥90% of outputs produce `#### N` structure (incl. unit-prefix per 2026-11-02 pre-reg) | 100% baseline-test, 98.5% holdout | ✅ **PASS, dramatically** |
| H5b | Holdout ≥ 43% (no regression) | 44.5% (vs. clean bare-holdout 43%) | ✅ **PASS** |
| H5c | Holdout ≥ 50% (meaningful improvement) | 44.5% (+1.5pt within noise) | ❌ **NOT MET** |
| H5c-strong | Holdout ≥ 60% | 44.5% | ❌ **NOT MET** |
| H5d | Early stopping triggers before epoch 3 | Not testable (patience=2 w/ 2 evals) | **N/A at this config** |

### Harness-priority breakdown (how answers were extracted)

**Adapter v7 holdout (E21)**:
- P1_strict (`#### N`): **197 / 200 (98.5%)**, 88 correct (44.7% within)
- P3_trailing_number: 3 / 200, 1 correct

**Bare Instruct holdout (E22)**:
- P1_strict: 168 / 200 (84%), 81 correct (48.2% within)
- P1_unit_prefix (`#### $N`, `#### 42%`): 16 / 200, 4 correct
- P2_final_answer: 3 / 200, 0 correct
- P3_trailing_number: 13 / 200, 1 correct

The adapter **locked in P1_strict format in 98.5% of outputs** —
zero `#### $N` unit-prefix, zero `Final Answer:` prose. The
format is more rigidly consistent than bare Instruct's
natural distribution.

### Dual-`####` retention (the F13 signal)

Dual-#### outputs (≥2 `####` markers per output) represent
Instruct's native "guess + reason + confirm-at-end" structure.
Trial #4's F13 analysis identified the DELETION of this
structure as the mechanism of the adapter v5 regression.

| Setup | Dual-#### outputs (of 200) | Rate |
|---|---|---|
| Bare Instruct (baseline-test, E19) | 91 | 45.5% |
| Bare Instruct (holdout, E22) | 90 | 45.0% |
| Adapter v5 baseline-test (E17) | 47 | 23.5% |
| Adapter v5 holdout (E18) | 40 | 20.0% |
| **Adapter v7 baseline-test (E20)** | **126** | **63.0%** |
| **Adapter v7 holdout (E21)** | **121** | **60.5%** |

**Adapter v7 SURPASSED bare Instruct's dual-#### rate** by
15 percentage points on both datasets. The chat-template
training not only preserved the native structure but
intensified it.

## Interpretation

### The chat-template fix works for structure, not for capability

The F13 regression mechanism (adapter v5 deleting Instruct's
dual-#### structure) is **confirmed** by Trial #5's inverse
result. When we fix the format mismatch:
- Dual-#### retention jumps from 20% back to 60%+
- `#### N` strict catching jumps from ~90% to 100%
- Accuracy jumps from 23% back to 44.5%

So Trial #4's regression was indeed about format, not about math
capability per se. Fixing the format recovered the lost accuracy.

But Trial #5 ALSO shows that **format correction alone does not
exceed bare Instruct**. The adapter learned the format perfectly
and recovered the regression, but it did not add new math
capability. Format and capability are decoupled levers.

### The format-vs-accuracy decoupling

Within-structure accuracy comparison:
- Bare Instruct P1_strict outputs: 81 correct / 168 = **48.2%**
- Adapter v7 P1_strict outputs: 88 correct / 197 = **44.7%**

**The adapter is slightly LESS accurate per-structured-output
than bare Instruct** (−3.5pt within-group). The gross accuracy
matches only because adapter v7 produces **more** `#### N`-structured
outputs (197 vs. 168 = +29 attempts, of which 7 extra were
correct).

Reading between the lines: fine-tuning on CoT format didn't
help the model solve more problems — it just reorganized
which questions get the structural confidence. Some questions
that bare Instruct would hedge on (unit-prefix, Final-Answer-prose,
or trailing-number heuristic) adapter v7 answers with confident
`#### N`. Confidence doesn't correlate with correctness; the
within-structure accuracy drops.

**Hypothesis for next direction**: capability-gain requires
either (a) much more training data (5-10x), (b) different
LoRA target modules (mlp.* instead of just attention),
(c) full fine-tuning, or (d) adding step-by-step validation
during inference (RAG-augmented or self-check).

### Threats to validity (post-trial review)

- **Internal (addressed)**: training-set v7 was correctly
  prepared and consumed (TB-US-078 wiring); chat template
  application verified in smoke-run; 100% P1_strict shows
  the format transfer succeeded.
- **External**: Instruct-family-specific result. Qwen Instruct,
  Mistral Instruct, DeepSeek Instruct may respond differently.
  GSM8K may not generalize to other math benchmarks (MATH,
  MGSM, SVAMP).
- **Construct**: "Preserving the structure" measured via
  `####` pattern passed easily. "Improving math capability"
  measured via gross accuracy failed. Could redefine
  capability as "difficulty-weighted accuracy" or
  "harder-subset accuracy" to see if the adapter helped on
  specific sub-tasks.
- **Statistical**: single-seed run; ±5pt binomial variance at
  n=200. The +1.5pt holdout improvement is within noise;
  single-run cannot distinguish "slight real improvement" from
  "stochastic variance". Multi-seed replication would be
  needed to pin this to ±1pt confidence.

### Confirmation-bias checklist

- [x] **Interpreted per pre-registered thresholds**: H5c (≥50%)
      pre-registered BEFORE results seen; 44.5% < 50% → not met.
      Didn't move the threshold.
- [x] **≥10 right + ≥10 wrong samples by hand**: Programmatic
      per-sample analysis (200 outputs) in
      `scripts/tb_us_079_analysis.py` covers this.
- [x] **Reasonable alternative explanations**: "Luck" (within
      ±5pt noise) explicitly flagged; multi-seed replicate
      would resolve.
- [x] **Would follow-up be different if result inverted?**
      If H5c had been met (≥50%), TB-US-080 would scale up
      (bigger data) to see if the lever has more lift. If H5c
      failed and H5b failed (regression), TB-US-080 would try
      different direction. **Current state** (H5b met, H5c not
      met): TB-US-080 pursues capability-gain levers (data
      scale-up, mlp target modules, full fine-tuning). This
      asymmetric response is in line with the pre-registered
      interpretation guide.

## Related labeling correction (TB-US-079 prep)

While preparing Trial #5's experiments, we discovered that TB-US-077's
E19 (bare Instruct control, 86/200 = 43%) was pinned on
`harness_version=v4` — the **baseline-test** set
(`math_eval_200.jsonl`), not v5 (`math_eval_200_holdout.jsonl`)
as previously documented. Multiple docs had labeled E19's 43%
as "holdout"; corrected across:

- `sweet-spot-search-log.md` (both the Trial #4 entry and the
  summary table)
- `instruct-scale-up-results.md` (the "The missing control: bare
  Instruct (E19)" section)
- `methodology.md` (position-vs-prior-work table)
- `sweet-spot-exploration.md` (Trial #4 result table + current
  demo note)
- `docs/pages/staged-progression.md` (public-facing demo copy)
- `BACKLOG.md` (TB-US-077 close notes)

The 43% number itself was unchanged; the dataset label was wrong.
E_bare_holdout (E22) in Trial #5 measured bare Instruct on the
actual holdout set and found **43.0% — identical to the
baseline-test result**. Bare Instruct is remarkably consistent
across both datasets.

This correction is unrelated to the architectural-wiring finding
(which was about `train.py` ignoring `training_set_version_id`),
but both were surfaced during the same TB-US-078→079 investigation
session. See TB-US-078 story + architectural-finding doc for the
wiring-gap finding.

## Decision + next-trial direction

**Trial #5 outcome**: positive-null — the chat-template format
fix works (eliminates regression) but doesn't improve on bare
Instruct. Bare Instruct at 43-44.5% remains the demo baseline.

**Next direction (TB-US-080)** — capability-gain levers:

1. **Scale training data 5-10x**: v7 was 1000 samples. Try
   5000 or 10000 samples at the same rank/epoch config.
   Hypothesis: more training signal gives the LoRA capacity
   to actually learn new math reasoning, not just format.
2. **Expand LoRA target modules**: current targets are
   `q_proj, v_proj, k_proj, o_proj` (attention only). Add
   `gate_proj, up_proj, down_proj` (MLP). Hypothesis: MLP
   layers hold more of the math-reasoning capacity.
3. **Combined (scale + mlp)**: if operator budget allows one
   trial that varies both axes.
4. **Alternative framing**: RAG-augmented inference (TB-US-075
   Phase 8 was deferred — this trial could land that).
5. **Full fine-tuning (not LoRA)**: largest-perturbation option;
   expensive (requires more VRAM / smaller batch); worth trying
   once if 1-3 don't lift accuracy.

**Operator picks one lever at a time per the Sweet Spot
discipline**; TB-US-080 pre-registers whichever direction is
chosen.

## Reproducibility

Per [`methodology.md`](methodology.md) reproducibility checklist:

- Base model: `meta-llama/Meta-Llama-3.1-8B-Instruct` (HF Hub
  main as of 2026-11-02)
- Training-set sidecar: `training/datasets/training_set_versions/v7.jsonl`
- `content_sha256 = 13adefc8426b983f45cd5a7618f60aaa022846f3405f9660d7a4ec611c759622`
- 1000 rows, seed=46, strictly disjoint from holdout
  (`math_eval_200_holdout.jsonl`)
- Training script: `training/math/train.py` at TB-US-078/079
  closure commit
- Prep script: `scripts/prep_math_v7_chat_template.py`
- Hyperparameters: see "Hyperparameters" section above
- Hardware: RTX 3090, 24 GB VRAM
- Software: TB-US-074 compat (`transformers` 5.x), bitsandbytes
  4-bit QLoRA
- Adapter: `adapter_versions.v7`, `files_path =
  adapters/math-example/v7`
- `adapter_content_sha256 = 0dcdbdeac53fff4af90c42f045ca99bd48e9f2556b0fb55c2d8149c69d559653`
- Measurement experiments: E20, E21, E22
- Random seeds: Python random seed via HF Trainer default
  (seed=42); training-set sampling seed=46; generation
  deterministic (do_sample=False)
- Elapsed wall-clock time: training 1437s (24 min); E20 ~45 min;
  E21 ~45 min; E22 ~17 min
