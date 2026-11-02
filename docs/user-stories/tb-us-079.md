# TB-US-079: Trial #5 — chat-template-formatted training on Instruct (first truly correct-wiring trial)

**Status**: Backlog
**Created**: 2026-11-02
**Author**: Jesse Eversole
**Blocked by**: TB-US-078 (training_set_version JSONL wiring)
**Commit hash(es)**: <filled in on completion>

## Story

As a TB maintainer running the Instruct-PEFT research arc, I
want **a chat-template-formatted training-set version (v7)
trained on Instruct via the newly-correct wiring from TB-US-078**
— so that we can test whether a trained adapter can match or
beat the bare Instruct baseline (43%) when its training data
format aligns with Instruct's native response structure.

Trial #5 in the sweet-spot search log. First trial under the
corrected architecture (training actually reads from the
registered `training_set_version`). Successor to TB-US-078's
original Trial #5 scope, which was moved here after the
architectural finding.

## Background

See TB-US-078 for the architectural finding and
`docs/math-example/instruct-scale-up-results.md` for Trial #4's
F13 regression analysis.

Trial #4 (adapter v5, TB-US-077) regressed Instruct from bare
43% to 23% holdout. Two mechanisms interacted:

1. **Hardcoded template bug**: `format_training_example` deleted
   GSM8K's native `#### N` marker and emitted `Final Answer: N`
   instead. Overwrote Instruct's native end-of-reasoning
   confirmation.
2. **Architectural wiring gap**: the "training set" nominally
   varied per trial (v4/v5/v6) but actually always sliced raw
   GSM8K. Trial-to-trial comparisons were therefore comparisons
   at constant data, not at varied data.

TB-US-078 closes both issues. Trial #5 under the corrected
wiring tests the research hypothesis cleanly for the first time.

## Pre-registered hypotheses

### H5a — Chat-template preserves native `####` structure

**Claim**: adapter v6 outputs end with `#### N` (GSM8K-native),
not `Final Answer: N`. Per-sample inspection: ≥90% of outputs
have `#### N` as the final numerical marker.

**Pre-registered interpretation of unit-prefixed outputs**
(flagged 2026-11-02 from TB-US-078 smoke-run observation):
Instruct sometimes emits the final-answer marker as `#### $43`
or `#### 42%` — with the unit of the answer included between
`####` and the digit. For H5a scoring purposes:

- `#### 43` → **counts as `#### N`** (strict native format)
- `#### $43`, `#### 42%`, `#### $1,234.56` → **counts as `#### N`**
  (native structure preserved; unit prefix is a formatting
  stylism, not a structural change)
- `Final Answer: 43`, `The answer is 43`, bare trailing digits
  with no `####` → **does NOT count** (structure not preserved)

Rationale: the F13 regression mechanism is about the `####`
answer-confirmation habit, not about unit-stripping discipline.
A model that preserves `####` with a unit prefix has preserved
the structure we care about. The harness scoring regex (patched
in TB-US-076) correctly extracts the number via its priority-3
trailing-number heuristic, so unit-prefix outputs score as
right/wrong on actual-value correctness, not on format rigor.

### H5b — Does NOT regress bare Instruct

**Claim**: holdout accuracy ≥ 43% (bare Instruct's E19 result).
Threshold: do not fall below bare baseline.

**If H5b fails**: file TB-US-080 to investigate whether any
PEFT configuration can help Instruct on this task, or whether
bare Instruct is the sweet spot for GSM8K.

### H5c — Beats bare Instruct meaningfully

**Claim**: holdout accuracy ≥ 50%. The "we actually improved on
an already-good base" signal.

**50-55%**: methodology works, close to the gain threshold.
**55%+**: strong result; adapter v6 ships as the demo.

### H5d — Early stopping handles overfitting gracefully

**Claim**: `EarlyStoppingCallback(patience=2)` +
`load_best_model_at_end=True` catch and save the min-eval-loss
checkpoint without manual intervention. (TB-US-077 infrastructure
exercised cleanly.)

## Hyperparameters (locked at this story's fire time)

| Hyperparameter | Value | Rationale |
|---|---|---|
| Base model | `meta-llama/Meta-Llama-3.1-8B-Instruct` | Instruct, same as Trial #4; isolates format change |
| Training set | `training_set_versions.v7` (chat-template-formatted) | The variable under test |
| Training-set size | 1000 samples (seed=46, disjoint from holdout) | Larger than Trial #4's 500 to improve signal |
| LoRA rank | 16 | Mid-range; smaller than Trial #4's 32 (less perturbation) |
| LoRA alpha | 32 | 2× rank |
| LoRA dropout | 0.05 | Standard |
| Learning rate | 1e-4 | Lower than Trial #4's 2e-4; slower perturbation |
| Epochs | 3 | Light touch; early stopping may trim |
| Batch size | 4 | Hardware-matched |
| Grad accum | 4 | Effective batch size 16 |
| Max eval samples | 200 | Comparable to prior trials |
| Early stopping | patience=2 on eval_loss | TB-US-077 infrastructure |

Rationale note: hyperparameters chosen to minimize overlap with
Trial #4's exact config while maximally testing the chat-template
hypothesis. Lower rank + lower lr + more epochs = gentler
training; larger data = more signal.

## Requirements

### Phase 1 — Pre-flight (TB-US-078 close-out should have handled)

- [ ] R1: Verify TB-US-078 closed and smoke-run passed
- [ ] R2: Verify training_set_versions.v7 released + promoted
- [ ] R3: Verify train.py reads from JSONL (sanity check — TB-US-078 proved it)

### Phase 2 — Train adapter v6

- [ ] R4: Service restart before launch (free VRAM)
- [ ] R5: Launch training run via `POST /training/runs/launch`:
      - training_set_version_id: 7
      - base_model: Meta-Llama-3.1-8B-Instruct
      - lora_rank: 16, alpha: 32, dropout: 0.05
      - lr: 1e-4, epochs: 3
      - batch_size: 4, grad_accum: 4
      - max_train_samples: 1000, max_eval_samples: 200
- [ ] R6: Monitor loss trajectory; verify early stopping behavior
- [ ] R7: Auto-registered adapter → release + promote

### Phase 3 — Measurement

- [ ] R8: Create E_in experiment pinning adapter v6 + baseline
      harness (v4) at n=200
- [ ] R9: Create E_holdout experiment pinning adapter v6 +
      holdout harness (v5) at n=200
- [ ] R10: Run both sequentially (service restart between
      training completion and inference)

### Phase 4 — Analysis

- [ ] R11: 4-column comparison:
      - Bare Instruct (E19, 43%)
      - Adapter v5 (E18, 23%)
      - Adapter v6 E_in
      - Adapter v6 E_holdout
- [ ] R12: Per-sample inspection: count outputs ending with
      `#### N` vs. `Final Answer: N` vs. other patterns
- [ ] R13: Mark H5a-H5d met / partial / not-met with concrete
      numeric values

### Phase 5 — Documentation

- [ ] R14: Trial #5 entry in sweet-spot-search-log.md (4-field
      format)
- [ ] R15: Deep dive: `docs/math-example/instruct-chat-template-results.md`
- [ ] R16: Update summary table in search log
- [ ] R17: If H5c met (≥50%): update Pages site + sweet-spot-exploration
- [ ] R18: If H5b failed (<43%): draft TB-US-080 with next direction

### Phase 6 — Close

- [ ] R19: Commit + push + close TB-US-079 + fire notification

## Acceptance Criteria

- [ ] AC1: Adapter v6 trained, auto-registered with correct
      training_set_version_id=7 linkage
- [ ] AC2: Both measurement experiments complete at n=200
- [ ] AC3: All four H5 hypotheses have recorded outcomes
- [ ] AC4: Trial #5 entry in search log with 4 required fields
- [ ] AC5: `instruct-chat-template-results.md` deep dive exists
- [ ] AC6: Per-sample `####` analysis documented
- [ ] AC7: Pages site reflects whichever is the current best demo
- [ ] AC8: If H5b failed, TB-US-080 drafted

## Design Notes

- **First truly correct-wiring trial.** Prior trials' "data"
  axis was a mirage (TB-US-078 finding). Trial #5 is the first
  trial where the registered training-set-version actually drives
  training. Note this prominently in the search-log entry — it
  materially affects how to interpret trial-to-trial comparisons.
- **Why not rank 8.** TB-US-078's original scope suggested rank
  8 (smaller perturbation). Moved up to 16 because the format
  fix is the dominant intervention; rank 16 gives us more capacity
  to actually learn without being the aggressive rank 32 of
  Trial #4.
- **Negative-result value preserved.** If adapter v6 doesn't
  beat bare Instruct, that's a publishable finding about PEFT
  on strong instruction-tuned bases — same scientific value as
  a positive result.

## Out of Scope

- Other base models (DeepSeek-math, Mistral, Qwen)
- Full fine-tuning (not LoRA)
- Multi-seed replication (deferred unless Trial #5 is within
  ±3pt of a decision threshold)
- RAG augmentation
- Hyperparameter grid search

## Related

- [TB-US-078](tb-us-078.md) — architectural fix; blocks this story
- [TB-US-077](tb-us-077.md) — Trial #4; produced the regression
  finding that motivates Trial #5
- `docs/math-example/architectural-finding-training-set-wiring.md`
  — context for why Trial #5 is the first correct-wiring trial
- `docs/math-example/instruct-scale-up-results.md` — Trial #4
  deep dive
- `docs/math-example/methodology.md`, `study-design.md`,
  `sweet-spot-search-log.md`
