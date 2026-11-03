# TB-US-082: Trial #8 — expand LoRA target modules to MLP (Candidate B)

**Status**: In Progress
**Pre-registered**: 2026-11-03
**Created**: 2026-11-03
**Started**: 2026-11-03
**Author**: Jesse Eversole
**Depends on**: TB-US-081 (Trial #7 multi-seed — closed with
"indistinguishable" verdict: Trial #6's apparent regression was
noise; both adapters equivalent to bare Instruct at ~42% within
6pt noise envelope)
**Commit hash(es)**: <filled in on closure commit>

## Story

As a TB maintainer who has now ruled out data scale as the
missing capability lever (Trial #6 at 5000 samples ≈ Trial #5 at
1000 samples), I want to **test whether expanding LoRA's target
modules to include the MLP layers** (not just attention) unlocks
the math-reasoning capability that attention-only training did
not. Eighth trial in the series; tests whether rank 16 is a
capacity trap specifically because of WHICH parameters it
touches, not just HOW MANY.

## Background

Research arc through Trial #7:

| Trial | Lever tested | Mean holdout (multi-seed where available) | Finding |
|---|---|---|---|
| 4 | Instruct + raw-CoT training | 23% (single draw) | Regression −20pt (real) |
| 5 | Chat-template format fix | 42.00% (4 draws, SD 2.65) | Preserved bare Instruct within noise |
| 6 | Scale data 1000 → 5000 | 41.62% (4 draws, SD 2.56) | No change vs. Trial #5 (noise envelope) |
| **Bare Instruct** | — | ~43% (2 single draws, consistent) | Baseline across both datasets |

Current state: bare Instruct 43% remains the headline. Adapters
v7 and v8 match bare within noise but don't exceed it. **Chat-template
format alignment is necessary to avoid regression (Trial #4
lesson) but NOT sufficient to improve.**

Three hypothesized mechanisms for why data scale alone didn't
help (from Trial #6 deep dive, partially revised by Trial #7):

1. **Dataset exhaustion** — 5000/7473 = 67% of GSM8K train; not
   much more corpus to scale into. **Still plausible** but not
   directly testable without external data.
2. **LoRA capacity trap at rank 16 (attention-only)** —
   limited expressive bandwidth for the complexity of GSM8K
   reasoning. **This story tests this mechanism.**
3. **Format-overfitting cascade (structural signal)** — real
   per-sample (dual-#### retention 60% → 74%), but Trial #7
   showed it does NOT translate to accuracy regression. The
   cascade exists but is accuracy-neutral.

Candidate B tests mechanism #2 by expanding the parameters LoRA
touches without changing rank, data, or other dials.

## Scope

Train a new adapter (v9) with **the ONLY variable changed being
`lora_target_modules`**, from 4 attention modules to 7 modules
(attention + MLP).

**Hyperparameters (locked)**:

| Hyperparameter | Trial #5 (v7) | **Trial #8 (v9)** |
|---|---|---|
| Base | Instruct | Instruct (same) |
| Training set | v7 (1000 samples) | **v7 (same — keeps data constant)** |
| **LoRA target modules** | `q_proj, v_proj, k_proj, o_proj` (4) | **`q_proj, v_proj, k_proj, o_proj, gate_proj, up_proj, down_proj` (7)** |
| LoRA rank | 16 | 16 (same) |
| LoRA alpha | 32 | 32 (same) |
| LoRA dropout | 0.05 | 0.05 (same) |
| Learning rate | 1e-4 | 1e-4 (same) |
| Epochs | 3 | 3 (same) |
| Batch size × grad accum | 4 × 4 = 16 effective | same |
| Max eval samples | 200 | 200 (same) |
| Early stop | patience=2 | patience=2 (same) |
| Load best model at end | True | True (same) |

**Why same training set as v7**: isolates the target-modules
effect. If v9 scores differently from v7 (multi-seed mean), the
difference is from the parameter-expansion, not from data,
seed, or any other confounded variable.

## Pre-registered hypotheses

### H8-primary — Capability gain over bare Instruct

**Claim**: holdout mean accuracy (across 4 draws) ≥ **46%**
(bare + 3pt, a modest signal).

**Null**: holdout mean accuracy < 44% (within the 6pt noise
envelope of bare Instruct / v7 / v8).

**Decision threshold**: holdout mean ≥ 46% at n=4 draws × 200
= primary accepted. ≤ 42% = null supported. 42-46% = marginal
(may warrant more draws).

**Rationale for threshold**: Trial #7 established a 6pt noise
envelope for our configuration. "+3pt mean above bare" sits at
the edge of noise but not inside it; +5pt would be more defensible
but harder to achieve. Keeping the bar at +3 reflects that we're
searching for ANY detectable capability lever, not demanding
publication-ready magnitude.

### H8a — MLP expansion changes the structural signature

**Claim**: dual-#### retention differs from Trial #5's 60-63%
(v7, attention-only). Direction unpredicted; could go either
way. Reporting the value is the signal, not a threshold.

**Signal**: if structural signature changes meaningfully (e.g.,
bare-like 45% or further intensified 80%+), the MLP expansion
is doing something structurally. If unchanged (58-65%), MLP
layers aren't carrying the format-learning mechanism.

### H8b — Does not re-regress

**Claim**: holdout mean ≥ 43% (bare baseline). Floor is "do no
harm" — any regression below bare is a real negative finding
about the MLP-expansion lever.

### H8c-strong — Published-range improvement

**Claim**: holdout mean ≥ 60%. If met, promote adapter v9 as
the demo, update Pages, draft multi-seed replication story for
publication.

### H8d — Early stopping fires or doesn't (observational)

7 target modules × rank 16 at the same training data roughly
doubles trainable parameters from Trial #5's ~17M to ~33M.
More capacity may lead to overfit earlier. If early-stop fires
before epoch 3, that's informative. Not a primary hypothesis;
observational signal.

## Requirements

### Phase 1 — Pre-flight

- [ ] R1: Service restart to free VRAM post-Trial #7
- [ ] R2: Verify train.py accepts `--lora-target-modules` with
      7 modules (existing CLI should; sanity check)
- [ ] R3: Confirm `training_set_versions.v7` still promoted
      (no change needed; v7 is already the active)

### Phase 2 — Train adapter v9

- [ ] R4: Launch training via `POST /training/runs/launch`:
      - base_model: Meta-Llama-3.1-8B-Instruct
      - training_set_version_id: 7
      - lora_target_modules: `[q_proj, v_proj, k_proj, o_proj,
        gate_proj, up_proj, down_proj]`
      - lora_rank: 16, alpha: 32, dropout: 0.05
      - lr: 1e-4, epochs: 3
      - batch_size: 4, grad_accum: 4
      - max_train_samples: 1000, max_eval_samples: 200
      - warmup_steps: 20, logging_steps: 5
- [ ] R5: Monitor loss trajectory; verify train and eval losses
      track (no instability); observe whether early-stop fires
- [ ] R6: Auto-registered adapter v9 → release + promote

### Phase 3 — Measurement (multi-seed from the start)

- [ ] R7: Create 4 experiments: `tb-us-082-trial8-eholdout-v9-
      replicate-1` through `-replicate-4`, all pinning adapter
      v9 + harness v5 + prompt v3 + Instruct
- [ ] R8: Sequential execution (~45 min each × 4 = ~3h). All
      implicit-seed (TB default harness runner). Uses the same
      measurement discipline established in Trial #7.
- [ ] R9: For completeness, create 1 baseline-test experiment
      (adapter v9 + harness v4) for cross-reference.

### Phase 4 — Analysis

- [ ] R10: Compute mean + SD + range across 4 v9 holdout draws.
- [ ] R11: 3-way comparison: v7 mean (Trial #7), v9 mean (Trial
      #8), bare Instruct (E22 single draw + optionally multi-seed
      E22 replicates if we want tighter baseline).
- [ ] R12: Per-sample pattern analysis (`tb_us_080_analysis.py`
      extended): dual-#### retention, harness-priority
      breakdown, within-P1_strict accuracy.
- [ ] R13: Decision per pre-registered thresholds.

### Phase 5 — Documentation

- [ ] R14: Trial #8 entry in search log (4-field format).
- [ ] R15: Deep dive at `docs/math-example/mlp-expansion-results.md`.
- [ ] R16: Summary table update in search log.
- [ ] R17: If H8-primary met: update Pages, promote v9 as demo
      adapter.
- [ ] R18: If H8-primary not met: draft TB-US-084 for Candidate
      C (full fine-tune) OR close the series with final writeup.

### Phase 6 — Close

- [ ] R19: Close-out commit + push + flip TB-US-082 → Completed.

## Acceptance Criteria

- [ ] AC1: Candidate B pre-registered before training.
- [ ] AC2: Training completed, adapter v9 auto-registered with
      training_set_version_id=7 linkage.
- [ ] AC3: 4 holdout multi-seed experiments complete at n=200
      (+ optional 1 baseline-test for cross-reference).
- [ ] AC4: Per-sample pattern analysis documented.
- [ ] AC5: H8-primary / H8a / H8b / H8c-strong / H8d outcomes
      recorded.
- [ ] AC6: Trial #8 entry in search log with 4-field format.
- [ ] AC7: Deep dive doc exists.
- [ ] AC8: Pages site reflects whichever is the current best
      demo.
- [ ] AC9: If H8-primary not met, TB-US-084 drafted (for
      Candidate C) OR series closed with final paper-draft
      bullet.

## Design Notes

- **Why keep v7 training set**: isolates the lever. If we
  changed both data AND target modules, we couldn't attribute
  the result to either. Trial #7 proved data at 1000 vs. 5000
  is a wash; v7 is the "canonical" data point.
- **Why multi-seed from the start**: Trial #7 taught us that
  single-draw measurements have 6pt noise envelopes. Any claim
  about Trial #8's result requires multi-seed to distinguish
  signal from noise. 4 draws is minimum for an estimable SD.
- **Why MLP specifically, not rank increase**: rank 32
  (Trial #4's configuration) was correlated with regression,
  but Trial #4 also had the format bug. Can't cleanly attribute.
  MLP expansion at rank 16 adds parameters along a different
  axis (which layers) without raising the perturbation magnitude
  in any single layer. If this helps, we know MLPs hold the
  reasoning capacity. If it doesn't, rank-increase isn't the
  likely next lever either; the ceiling is probably somewhere
  else (data variety, base model, inference-time scaffolding).
- **Why +3pt threshold for H8-primary**: Trial #7's 6pt noise
  envelope means "beating bare" requires at minimum a mean 3pt
  above bare to be detectable. The decision mapping has room
  for "marginal" (42-46%) but the primary bar is "detectable
  above noise."

## Out of Scope

- Candidate C (full fine-tune) — deferred to TB-US-084 if B
  doesn't lift
- External data (synthetic math, MATH, MGSM)
- Prompt engineering
- Multi-adapter ensembles
- Other base models (Qwen, Mistral, DeepSeek)

## Related

- [TB-US-081](tb-us-081.md) — Trial #7 (multi-seed) — closed
  with "indistinguishable" verdict; established 6pt noise
  envelope
- [TB-US-080](tb-us-080.md) — Trial #6 (scale data)
- [TB-US-079](tb-us-079.md) — Trial #5 (chat-template format)
- `docs/math-example/multi-seed-replicate-results.md` — Trial
  #7 deep dive
- `docs/math-example/methodology.md` —
  research protocol
- `docs/math-example/sweet-spot-search-log.md` — chronological
  record
