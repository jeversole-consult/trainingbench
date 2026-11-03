# TB-US-081: Trial #7 — remaining capability-gain levers (post-scale-up)

**Status**: Backlog
**Created**: 2026-11-03
**Author**: Jesse Eversole
**Depends on**: TB-US-080 (Trial #6 scale-data — closed with
negative result: scaling 1000→5000 modestly regressed accuracy
and intensified format overfitting)
**Commit hash(es)**: <filled in on completion>

## Story

As a TB maintainer who's now tested two capability-gain levers
(Trial #5 chat-template format fix: positive-null; Trial #6
scale data 5x: negative), I want to **test the remaining
candidate levers** — expanded LoRA target modules (B), full
fine-tuning (C), or multi-seed replication (D) — so that we
can either find a working PEFT configuration OR definitively
bound the ceiling for PEFT-on-strong-base at this corpus
scale.

Seventh trial in the sweet-spot search log. Operator picks ONE
candidate at fire time.

## Background

Research arc through Trial #6:

| Trial | Lever tested | Result |
|---|---|---|
| 4 | Instruct scale-up (same format as Base) | Regression −20pt |
| 5 | Chat-template format fix | Preserved bare (no gain) |
| 6 | Scale data 5x (1000 → 5000) | Modest regression (-2pt / -6.5pt); format overfit intensified |

Current state: bare Instruct 43% remains the headline. Neither
adapter v7 (Trial #5) nor adapter v8 (Trial #6) is promoted —
v7 ties bare within noise; v8 is strictly worse than v7.

Trial #6's deep dive proposed three mechanisms for the data-scale
negative result:
1. **Dataset exhaustion** (5000/7473 = 67% of GSM8K train)
2. **LoRA capacity trap at rank 16** (format wins the capacity
   competition)
3. **Format-overfitting cascade** (more training = more
   confident wrong answers)

The remaining candidates test different mechanisms:
- **D (multi-seed)** tests whether Trial #6's drop is noise vs.
  real.
- **B (MLP target modules)** tests mechanism #2 by adding
  parameter capacity.
- **C (full fine-tune)** tests mechanisms #2 and #3 by removing
  the low-rank constraint entirely.

## Candidate levers (operator picks ONE at fire time)

### Candidate D — Multi-seed replicate (RECOMMENDED FIRST)

- Re-run E_holdout_v7 and E_holdout_v8 with 2-3 different
  generation seeds each
- Report mean + range + ±1-standard-deviation band
- Expected cost: ~45 min per experiment × 4-6 experiments = 3-5h
- Hypothesis: Trial #6's -2pt holdout drop vs. Trial #5 is
  partially real. If multi-seed average confirms real drop,
  candidates B/C are tested against confirmed baseline. If
  drop is noise, Trials #5 and #6 are equivalent and the "data
  scale didn't help" conclusion is confirmed without needing
  bigger-ticket experiments.
- Risk: expensive if the real effect is 0; still informative.

### Candidate B — Expand LoRA to MLP

- Same v7 training set (1000 samples) — keeps data constant with
  Trial #5 for clean apples-to-apples
- Change `lora_target_modules` from `["q_proj", "v_proj",
  "k_proj", "o_proj"]` (4) to add
  `["gate_proj", "up_proj", "down_proj"]` (7 total)
- Rank 16, 3 epochs, lr 1e-4 — unchanged
- Expected cost: ~45-60 min training + ~1.5h experiments = ~2.5h
- Hypothesis: MLP layers hold more math-reasoning capacity than
  attention alone; expanding reach unlocks capability without
  needing more data.
- Risk: more parameters = more overfit potential — early-stop
  infrastructure handles this.

### Candidate C — Full fine-tuning

- Same v7 training set
- Add `--full-fine-tune` flag to train.py (new code path;
  requires VRAM profiling)
- Smaller batch size (requires more VRAM per sample)
- Expected cost: significantly longer; may need gradient
  checkpointing to fit in 24GB
- Hypothesis: unconstrained parameter updates unlock capability
  that low-rank LoRA cannot access.
- Risk: largest-perturbation; overwrites Instruct's SFT'd
  capabilities on non-math tasks (we don't measure these).

## Pre-registered hypotheses (fill at fire-time based on candidate)

### H7-primary — Capability gain over bare Instruct

**Claim** (D): resolved comparison of adapter v7 vs. v8 vs. bare
with multi-seed means + confidence intervals. Deliverable:
whether the +1.5pt/−2pt differences are real.

**Claim** (B/C): holdout accuracy ≥ 50% (bare + 7pt). Same
decision mapping as TB-US-080.

### H7a (candidate-specific)

- **D**: 3 seeds of adapter v7 holdout + 3 seeds of adapter v8
  holdout. Mean + range. If v7 mean − v8 mean > 2× SD, the drop
  is real.
- **B**: within-P1-strict accuracy ≥ 50% AND dual-#### retention
  ≥ 60%. Tests whether MLP expansion adds reasoning without
  disrupting format.
- **C**: within-P1-strict accuracy ≥ 55% (more perturbation = larger
  expected lift if the lever works).

### H7b — Does not re-regress

Holdout ≥ 43% (bare). All candidates must at minimum preserve
bare performance.

### H7c (strong success) — Published-range improvement

Holdout ≥ 60%. If any candidate hits this, deliverable is
adapter promotion + Pages demo swap + multi-seed replicate for
publication.

## Requirements

### Phase 1 — Fire-time pre-registration

- [ ] R1: Operator picks ONE candidate (B/C/D). Lock H7a as
      candidate-specific.
- [ ] R2: Append Trial #7 planning entry to search log.

### Phase 2 — Build training infrastructure (if needed)

- [ ] R3: Candidate B: no new training set; use v7.
- [ ] R4: Candidate C: train.py extension for `--full-fine-tune`.
      Design doc at `docs/design/full-fine-tune.md` before code.
- [ ] R5: Candidate D: no training change; experiment-only.

### Phase 3 — Train (candidates B/C) or Run (D)

- [ ] R6: Service restart; launch training (B/C) with
      pre-registered hyperparameters, or batch-queue experiments
      (D).
- [ ] R7: Monitor training trajectory; verify eval loss
      progression.

### Phase 4 — Measurement

- [ ] R8: Candidate B/C: 2 experiments (E_in + E_holdout) at
      n=200.
- [ ] R9: Candidate D: 4-6 experiments at n=200 with varied
      generation seeds.

### Phase 5 — Analysis + decision

- [ ] R10: Candidate-specific comparison tables.
- [ ] R11: Per-sample pattern analysis (`tb_us_080_analysis.py`
      extended).
- [ ] R12: Decision mapping per pre-registered thresholds.

### Phase 6 — Documentation + close

- [ ] R13: Deep dive at `docs/math-example/trial-7-<candidate>-results.md`.
- [ ] R14: If H7-primary met: promote new adapter + update Pages
      site.
- [ ] R15: If H7-primary not met and remaining candidates exist:
      TB-US-082 drafted.
- [ ] R16: If no capability-gain lever works across the series:
      close the research arc with a final paper-draft bullet
      "PEFT doesn't help Instruct for GSM8K at this scale /
      corpus."

### Phase 7 — Commit + push + close

- [ ] R17: Close-out commit + push + flip TB-US-081 to Completed.

## Acceptance Criteria

- [ ] AC1: One candidate pre-registered before training/running.
- [ ] AC2: Infrastructure built if needed (new training set,
      train.py extension, or batch-experiment runner).
- [ ] AC3: All planned experiments completed at n=200.
- [ ] AC4: Per-sample pattern analysis documented.
- [ ] AC5: H7-primary / H7a / H7b / H7c outcomes recorded.
- [ ] AC6: Trial #7 entry in search log with 4-field format.
- [ ] AC7: Deep dive doc exists.
- [ ] AC8: Pages site reflects whichever is the current best
      demo.
- [ ] AC9: If H7-primary not met and remaining candidates exist,
      TB-US-082 drafted.
- [ ] AC10: If no capability-gain lever works across the series,
      final paper-draft bullet captured in `methodology.md`.

## Design Notes

- **Why D first (recommendation)**: Trial #6's -2pt holdout is
  within ±5pt noise but marginally directional-down. Multi-seed
  resolves this cheaply before investing in B or C. If drop is
  real, we have a confirmed negative result as the baseline
  for B/C comparisons. If drop is noise, Trial #5 and #6 are
  equivalent and the series conclusion "data scale alone
  doesn't help" is firm.
- **Why B second**: cheapest of the capacity-expanding levers.
  Tests the "LoRA rank 16 is a capacity trap" mechanism directly.
- **Why C last**: largest cost, largest risk of unmeasured
  side-effects (overwrites Instruct's SFT'd behaviors elsewhere).
  Only worth the cost if B hints at the capacity direction.
- **Series close conditions**: if B/C both pursued and both fail
  H7-primary, close the series. The negative finding becomes
  the paper's section 4: "PEFT doesn't help Llama 3.1 8B
  Instruct on GSM8K at the 1-5k sample scale with rank 16-full
  LoRA."

## Out of Scope

- External data (synthetic, MATH, MGSM) — potentially follow-up
  story
- Other base models (Qwen, Mistral)
- Prompt engineering sweeps
- Multiple candidates in one trial
- RAG augmentation

## Related

- [TB-US-080](tb-us-080.md) — Trial #6 (scale data) — closed
  with negative result
- [TB-US-079](tb-us-079.md) — Trial #5 (chat-template) — closed
  with positive-null
- `docs/math-example/scale-up-5000-results.md` — Trial #6 deep
  dive
- `docs/math-example/instruct-chat-template-results.md` — Trial
  #5 deep dive
- `docs/math-example/methodology.md`,
  `docs/math-example/study-design.md`,
  `docs/math-example/sweet-spot-search-log.md`
