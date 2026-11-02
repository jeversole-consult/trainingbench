# TB-US-078: Investigate training approaches that would HELP (not regress) the Instruct base

**Status**: Proposed
**Created**: 2026-11-02
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a TB maintainer who just discovered that LoRA on Llama 3.1 8B
Instruct **actively regressed** accuracy (43% bare → 23% with our
adapter v5), I want **a methodical investigation of what training
approach WOULD help Instruct** — chat-template-formatted data,
smaller LoRA rank, larger training set, different task framing —
so that we can establish whether a trained adapter can beat the
bare 43% ceiling or whether bare Instruct is in fact the
sweet-spot for this task.

Trial #5 in the sweet-spot search log. First attempt at
constructive-not-destructive training on Instruct.

## Background

TB-US-077 Trial #4 was pre-registered to deliver 55–75% holdout
accuracy. Actual result: adapter v5 landed at **23%** —
substantially WORSE than bare Instruct (43%). The methodology
caught the regression because we required the bare-Instruct
control measurement (E19).

Deep-dive in
[`instruct-scale-up-results.md`](../math-example/instruct-scale-up-results.md).
Per-sample inspection revealed the regression's root cause: F13
"answer-first" pattern mismatch between Instruct's native
response structure (`#### <guess>` + reasoning + `#### <corrected>`
at end) and our training-data format (reasoning + `#### <answer>`
once at the end). Our 500-sample × 5-epoch LoRA at rank 32
**deleted** Instruct's end-of-reasoning answer-confirmation
behavior without replacing it with equivalent competence.

Trial #5's job: test variations that preserve or replace that
behavior.

**Depends on**:
- TB-US-077 (closed) — provides the bare-Instruct baseline + the
  regression finding
- Lab machine with ≥24 GB VRAM

**Blocks**:
- Nothing hard. Bare Instruct (43%) is a defensible public demo
  without a successful adapter.

## Scope (one iteration, same pattern as TB-US-075-77)

Trial #5 tests ONE combination of variations at a time, not all
of them at once. Pre-registering the specific combination before
running maintains the methodology's discipline.

**Suggested first combination** (operator decides at fire time):

- **Base**: Llama 3.1 8B Instruct (unchanged)
- **Training data format**: chat-template-formatted via
  `tokenizer.apply_chat_template()` — `<|system|>` + `<|user|>`
  + `<|assistant|>` turns rather than raw CoT prose. Preserves
  Instruct's native response structure.
- **LoRA rank**: 8 (down from 32). Smaller perturbation; less
  likely to delete Instruct's native behavior.
- **Training set size**: 500 samples (same as Trial #4 for
  cross-trial comparability)
- **Epochs**: 3 (down from 5). Light touch; early stopping
  may trigger sooner.
- **Learning rate**: 1e-4 (down from 2e-4). Slower perturbation.

**Alternative combinations** (if the first doesn't land):

| Variant | Hypothesis |
|---|---|
| Rank 16 instead of 8 | Finer control over the perturbation magnitude |
| 2000 samples instead of 500 | Enough signal to REPLACE Instruct's behavior |
| Add `apply_chat_template` even to v6 unchanged | Format alone fixes it; rank/data don't matter |
| Prompt variations (ask for `#### N` at END only) | System prompt alone may suffice |

## Pre-registered hypotheses

### H5a — Chat-template beats raw CoT

**Claim**: training on chat-template-formatted data will produce
an adapter whose output structure PRESERVES Instruct's native
"guess + reason + confirm at end" pattern.

**Measurable signal**: per-sample inspection shows most outputs
have 2+ `####` markers (initial + corrected-at-end), like bare
Instruct does. Current adapter v5 outputs have exactly 1.

### H5b — Does NOT regress bare Instruct

**Claim**: holdout accuracy with the new adapter ≥ 43% (bare
Instruct's result). Threshold: **do not fall below the bare
baseline**.

**If H5b fails** (adapter v6 < 43%), the hypothesis "LoRA at
scale can help Instruct" is weakened and TB-US-079 would try a
different direction (e.g., much larger training set or
full-fine-tuning instead of LoRA).

### H5c — Beats bare Instruct meaningfully

**Claim**: holdout accuracy ≥ 50% (bare + 7 points). This is
the "we actually improved on an already-good base" signal.

**Below 50% but above 43%**: methodology works + we're close but
need more iteration.
**Above 50%**: Trial #5 ships as the new demo adapter.

### H5d — Early stopping handles overfitting gracefully

**Claim**: `load_best_model_at_end=True` + `EarlyStoppingCallback(patience=2)`
(both from TB-US-077's infrastructure) catches and saves the
min-eval-loss checkpoint without manual intervention.

## Requirements

### Phase 1 — Pre-registration

- [ ] R1: Update `study-design.md` with Trial #5 hypotheses + the
      specific variant combination being tested
- [ ] R2: Append Trial #5 planning entry to
      `sweet-spot-search-log.md` with status "launching"

### Phase 2 — Build training data

- [ ] R3: `scripts/prep_math_v7_chat_template.py` — new script.
      Takes GSM8K train-split samples + applies the Instruct
      chat template so each training example looks like:
      ```
      <|system|>You are a math tutor...<|end_of_system|>
      <|user|>{question}<|end_of_user|>
      <|assistant|>{full CoT answer with #### N at end}<|end_of_assistant|>
      ```
      500 samples with seed=46 (distinct from all prior sampling
      seeds), strictly disjoint from holdout
- [ ] R4: Register as `training_set_versions.v7` on agent 3,
      release + promote

### Phase 3 — Train adapter v6

- [ ] R5: Launch training via `POST /training/runs/launch` with:
      - base_model: `meta-llama/Meta-Llama-3.1-8B-Instruct`
      - training_set_version_id: 7
      - lora_rank: 8 (vs. 32)
      - lora_alpha: 16 (2× rank, as before)
      - lora_dropout: 0.05
      - learning_rate: 1e-4
      - epochs: 3
      - batch_size: 4
      - gradient_accumulation_steps: 4
      - max_train_samples: 500
      - max_eval_samples: 100
- [ ] R6: Service restart before training to free VRAM
- [ ] R7: Monitor loss trajectory; verify early stopping saves
      the min-eval-loss checkpoint
- [ ] R8: Auto-registered adapter → release + promote

### Phase 4 — Measurement

- [ ] R9: Create E_in + E_holdout experiments pinning the new
      adapter + harness v4 (baseline test) + harness v5 (holdout)
- [ ] R10: Launch sequentially; measure both strict (via
      patched harness) and lenient (post-hoc)

### Phase 5 — Interpretation

- [ ] R11: Compare 4 columns:
      - Bare Instruct (E19, 43%)
      - Adapter v5 (E18, 23%)
      - Adapter v6 (E_holdout, new result)
      - Lenient re-score of adapter v6 (sanity check vs. strict)
- [ ] R12: Per-sample inspection: do adapter v6 outputs have
      the dual-`####` structure like bare Instruct?
- [ ] R13: Mark H5a-H5d met / partial / not-met with concrete
      numeric values

### Phase 6 — Documentation

- [ ] R14: Trial #5 entry in search log (4-field format: what-did
      / what-found / what-decided / rationale)
- [ ] R15: Deep dive at `docs/math-example/instruct-chat-template-results.md`
- [ ] R16: Update summary table in search log
- [ ] R17: If H5c met (≥50% holdout): update Pages +
      sweet-spot-exploration with the new adapter as the demo
- [ ] R18: If H5b failed (< 43%): draft TB-US-079 with the next
      direction to try

### Phase 7 — Close

- [ ] R19: Commit + push + close TB-US-078 + fire notification

## Acceptance Criteria

- [ ] AC1: Training-data script v7 produces chat-template-formatted
      output; disjoint from holdout
- [ ] AC2: Training set v7 registered + promoted
- [ ] AC3: Adapter v6 trained + auto-registered + released +
      promoted
- [ ] AC4: Both measurement experiments complete at n=200 strict
- [ ] AC5: Trial #5 entry in search log with 4 required fields
      populated
- [ ] AC6: `instruct-chat-template-results.md` deep dive exists
- [ ] AC7: H5a-H5d all have outcomes recorded
- [ ] AC8: Pages site reflects whichever is the current best
      demo (bare Instruct if H5c failed; adapter v6 if H5c met)
- [ ] AC9: If H5b failed, TB-US-079 drafted
- [ ] AC10: If multiple sub-hypotheses need separate trials,
      each gets its own TB-US-NNN

## Design Notes

- **Why chat-template format is the primary hypothesis.** The
  F13 analysis in `instruct-scale-up-results.md` shows our raw
  CoT training format deleted Instruct's `####-at-end` summary
  behavior. Instruct is trained on chat-template-formatted
  conversations; aligning our training format with that should
  preserve the native structure.
- **Why rank 8 (smallest reasonable).** Rank 32 (Trial #4)
  evidently perturbed too much. Rank 8 is the minimum "credibly
  non-trivial" rank for an 8B model. If rank 8 + chat template
  doesn't help, the issue isn't rank; it's training data or
  framing.
- **Why only 500 samples (same as Trial #4).** Keeps the sample
  count cross-trial-comparable so we can isolate the effect of
  format + rank changes. If this trial fails, TB-US-079 can
  scale up data.
- **Why 3 epochs instead of 5.** Instruct is already good at
  this task. Less training = less perturbation = less chance
  of damaging native behavior. Early stopping will trim further
  if eval loss plateaus early.
- **One iteration per story**: same scope-cap as TB-US-075-077.
  Prevents open-ended research loops.

## Out of Scope

- Non-Llama base models (DeepSeek-math, Mistral, Qwen) — stay
  Llama 3.1 family for continuity
- Full fine-tuning (not LoRA) — too expensive on 8B
- Multi-run averaging (one run; stochastic noise accepted)
- RAG augmentation (TB-US-075 Phase 8, still skippable)
- Hyperparameter grid search

## Related

- [TB-US-077](tb-us-077.md) — Trial #4 (base scale-up); produced
  the regression finding this story investigates
- [`instruct-scale-up-results.md`](../math-example/instruct-scale-up-results.md)
  — Trial #4 deep dive; F13 analysis motivates H5a
- [TB-US-075](tb-us-075.md), [TB-US-076](tb-us-076.md) —
  prior trials in the search
- Files touched (during execution):
  - `scripts/prep_math_v7_chat_template.py` (new, R3)
  - `training-sets/math-example-v7-chat-template.jsonl` (new, R3)
  - `training_set_versions.v7` (R4)
  - `adapter_versions.v6` (R8)
  - `training_runs.id` ≈ 12 (R5)
  - 2 new experiments (E_in, E_holdout)
  - `docs/math-example/study-design.md` (R1, append Trial #5)
  - `docs/math-example/sweet-spot-search-log.md` (R2, R14, R16)
  - `docs/math-example/instruct-chat-template-results.md` (R15, new)
  - `docs/pages/staged-progression.md` (R17, conditional)
