# TB-US-080: Trial #6 — capability-gain levers on Instruct (post-chat-template)

**Status**: Backlog
**Created**: 2026-11-02
**Author**: Jesse Eversole
**Depends on**: TB-US-079 (chat-template Trial #5 — closed with
positive-null finding: format fix preserves bare Instruct but
doesn't improve it)
**Commit hash(es)**: <filled in on completion>

## Story

As a TB maintainer who's just confirmed in Trial #5 that **the
chat-template format fix preserves but does not augment bare
Instruct's GSM8K accuracy** (44.5% vs. 43%), I want **a trial
that specifically targets capability gain** (lifting past 43% in
a way that exceeds stochastic noise) — so that we can either (a)
discover a working PEFT configuration for math on Instruct or
(b) empirically bound the ceiling for PEFT-on-strong-base.

Sixth trial in the sweet-spot search log. Three candidate levers
to pick ONE from at fire time; the first that lands a positive
result (holdout ≥ 50%) ships as the demo adapter.

## Background

Trials #1-#5 established:

| Trial | Base | Approach | Holdout | Finding |
|---|---|---|---|---|
| 1-2 | Base | QLoRA, 200 failures, 5ep | 26% | Baseline from zero |
| 3 | Base | QLoRA, 300 random, 10ep | 7.5% | Overfit |
| 4 | Instruct | QLoRA rank 32, 500 random, 5ep, raw CoT | 23% | **Regressed** (-20pt) |
| **4-control** | **Instruct** | **bare, no adapter** | **43%** | **New baseline** |
| 5 | Instruct | QLoRA rank 16, 1000 chat-template, 3ep | 44.5% | **Preserves, no gain** |

Trial #5's deep dive
([`instruct-chat-template-results.md`](../math-example/instruct-chat-template-results.md))
identified the "decoupling finding": chat-template training taught
the model format rigidity (dual-#### retention 60% vs. bare's 45%;
100% P1_strict catching vs. bare's 84%) but did NOT improve
within-structure accuracy (44.7% within P1_strict vs. bare 48.2%
within P1_strict).

**Hypothesis for next direction**: capability gain requires MORE
TRAINING SIGNAL than Trial #5 provided. Three forms of "more
signal":

1. **More data (scale)**: Trial #5 was 1000 samples. Published
   math-LoRA work typically uses 10,000-50,000+. Does scaling
   data unlock capability?
2. **More parameters (reach)**: Trial #5 touched 4 attention
   modules per layer. Published work often targets MLP as well
   (7 modules per layer). Does scaling LoRA footprint unlock
   capability?
3. **More freedom (full-fine-tuning)**: LoRA perturbs within a
   low-rank subspace. Full fine-tuning has no such constraint.
   Expensive but informative.

Trial #6 picks ONE of these at fire time (per Sweet Spot
discipline — one iteration, one variable).

## Candidate levers (operator picks ONE at fire time)

### Candidate A — Scale training data 5-10x

- `training_set_versions.v8` or v9: 5000-10000 random GSM8K
  train-split samples, chat-template-formatted, seed=47
- Other hyperparameters: unchanged from Trial #5
- Expected training time: ~2-4 hours on 24GB GPU
- Hypothesis: more training signal lifts within-structure
  accuracy from 44.7% toward the published 70-85% range
- Risk: at larger data, could trigger overfit — early stop
  patience needs to be exercised (≥5 epochs → multiple evals)

### Candidate B — Expand LoRA target modules to MLP

- Same v7 training set (1000 samples, chat-template-formatted)
- Change `lora_target_modules` from
  `["q_proj", "v_proj", "k_proj", "o_proj"]` (4) to
  `["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]` (7)
- Rank 16, 3 epochs, lr 1e-4
- Expected training time: ~45-60 min (more trainable params)
- Hypothesis: MLP layers hold more math-reasoning capacity than
  attention alone; expanding reach unlocks capability
- Risk: more parameters = more overfit potential

### Candidate C — Full fine-tuning (not LoRA)

- Same v7 training set
- `--full-fine-tune` flag (needs train.py extension)
- Smaller batch size (requires more VRAM per sample)
- Expected training time: significantly longer; may need
  gradient checkpointing to fit
- Hypothesis: unconstrained parameter updates unlock capability
  that low-rank LoRA cannot access
- Risk: largest-perturbation; most likely to overwrite Instruct's
  SFT'd capabilities elsewhere (e.g., chat quality on other
  tasks). Only measure math accuracy; non-math regressions
  invisible.

### Candidate D — Multi-seed replication of Trial #5

- No training change; re-run Trial #5 with 3 different
  generation seeds
- Expected time: ~45 min per experiment × 3 = ~2-3 hours
- Hypothesis: Trial #5's +1.5pt improvement over bare is
  partially real (not purely noise). Multi-seed average
  tightens the confidence interval.
- Risk: expensive if the real effect is 0; still informative
  (bounds the result).

**Operator default recommendation**: **Candidate A (scale data)**
is the "most likely to show lift" option per published
math-LoRA literature. Candidate B is the "cheapest to try" option.
Candidate D is the "most rigorous but doesn't move the ceiling"
option.

## Pre-registered hypotheses (filled at fire time based on
candidate chosen)

### H6-primary — Capability gain over bare Instruct

**Claim**: holdout accuracy ≥ 50% (bare + 7pt).

**Null**: holdout accuracy < 48% (within bare's noise band).

**Decision threshold**: holdout ≥ 50% at n=200 = primary accepted;
< 48% = null supported; 48-50% = inconclusive (requires
multi-seed replicate).

### H6a (candidate-specific)

For Candidate A: within-structure accuracy (per-P1-strict output)
≥ 50%. Signal: more data helps the model solve more problems
within its (already-locked) format.

For Candidate B: within-structure accuracy ≥ 50% AND dual-####
retention remains ≥ 60%. Signal: MLP expansion adds reasoning
capacity without disrupting format.

For Candidate C: within-structure accuracy ≥ 55% (more
perturbation = larger expected lift if the lever works). Signal:
full-fine-tuning unlocks capacity LoRA couldn't access.

### H6b — Does not re-regress

Holdout ≥ 43% (bare baseline). All candidates must at minimum
preserve bare performance; if any regresses, that's an
important finding about how aggressive training perturbs
Instruct.

### H6c (strong success) — Published-range improvement

Holdout ≥ 60%. If any candidate hits this, the deliverable is
"we have a math-specialist adapter" + demo page swap.

## Requirements

### Phase 1 — Fire-time pre-registration

- [ ] R1: Operator picks ONE candidate (A/B/C/D). Updates this
      story's status + fills in H6a as candidate-specific.
- [ ] R2: Append Trial #6 planning entry to search log.

### Phase 2 — Build training infrastructure (if needed)

- [ ] R3: Candidate A: new prep script
      `scripts/prep_math_v8_chat_template_5000.py` (or similar).
      Register as `training_set_versions.v8`.
- [ ] R4: Candidate B: no new training set; use v7.
- [ ] R5: Candidate C: train.py extension to support
      `--full-fine-tune` flag (new code path; requires VRAM
      profiling).
- [ ] R6: Candidate D: no training change; experiment-only.

### Phase 3 — Train adapter v8 (or re-use v7 for D)

- [ ] R7: Service restart; launch training with pre-registered
      hyperparameters.
- [ ] R8: Monitor loss trajectory; verify early-stop
      infrastructure engages at ≥4 epochs for Candidates A/C.

### Phase 4 — Measurement

- [ ] R9: E_in and E_holdout experiments at n=200
- [ ] R10: Candidate D: 3 generation-seed runs of E_holdout
- [ ] R11: Per-sample pattern analysis via
      `scripts/tb_us_079_analysis.py` extended

### Phase 5 — Analysis + close

- [ ] R12: Four-cell comparison + per-sample breakdown
- [ ] R13: Decision mapping per candidate's thresholds
- [ ] R14: Deep dive at
      `docs/math-example/trial-6-<candidate>-results.md`
- [ ] R15: If H6-primary met → promote new adapter + update
      Pages site; demo configuration changes
- [ ] R16: If H6-primary not met → TB-US-081 drafts next
      candidate (or we close the series as "PEFT doesn't help
      Instruct for GSM8K at this scale")

### Phase 6 — Commit, push, close

- [ ] R17: Close-out commit + push + flip to Completed

## Acceptance Criteria

- [ ] AC1: One candidate (A/B/C/D) pre-registered before training
- [ ] AC2: Training completed + adapter auto-registered (or
      Candidate D's 3-seed experiments completed)
- [ ] AC3: Measurement experiments completed at n=200 per
      candidate's requirement
- [ ] AC4: Per-sample pattern analysis documented
- [ ] AC5: H6a / H6b / H6c outcomes recorded
- [ ] AC6: Trial #6 entry in search log with 4-field format
- [ ] AC7: Deep dive doc exists
- [ ] AC8: Pages site reflects whichever is the current best demo
- [ ] AC9: If H6-primary not met, TB-US-081 drafted OR series
      closed with final writeup

## Design Notes

- **Why "one lever per trial" discipline is firm here.** Three
  candidate directions × combinatorial interactions would make
  the search log a mess and dilute the publication narrative.
  Pick one, measure it, learn, next.
- **Why multi-seed replication (Candidate D) is a legitimate
  trial.** The +1.5pt result from Trial #5 is within noise but
  the direction is interesting (format fix + light training
  → marginal lift). Resolving noise → signal is itself a
  methodological contribution.
- **Why not RAG augmentation here.** TB-US-075 Phase 8
  explicitly deferred RAG for math (retrieval won't help with
  procedural math problems). Can revisit later if TB-US-080
  closes the PEFT direction without a win.

## Out of Scope

- Other base models (Qwen, Mistral, DeepSeek)
- Other benchmarks (MATH, MGSM, SVAMP) — stay GSM8K
- RAG augmentation
- Prompt-engineering sweeps
- Multiple candidates in one trial

## Related

- [TB-US-079](tb-us-079.md) — Trial #5 (chat-template-formatted
  training) — positive-null; motivates this trial
- [TB-US-078](tb-us-078.md) — training-set-version wiring
  (foundation)
- `docs/math-example/instruct-chat-template-results.md` — Trial
  #5 deep dive
- `docs/math-example/methodology.md`,
  `docs/math-example/study-design.md`,
  `docs/math-example/sweet-spot-search-log.md`
