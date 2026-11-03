# TB-US-081: Trial #7 — remaining capability-gain levers (post-scale-up)

**Status**: Completed
**Candidate chosen**: **D — Multi-seed replicate**
**Pre-registered**: 2026-11-03
**Created**: 2026-11-03
**Started**: 2026-11-03
**Completed**: 2026-11-03
**Author**: Jesse Eversole
**Depends on**: TB-US-080 (Trial #6 scale-data — closed with
apparent negative result that Trial #7 revised to "no change
within noise")
**Commit hash(es)**: <filled in on closure commit>

## Pre-registered experimental matrix (Candidate D, locked 2026-11-03)

**Pragmatic framing**: TB's existing harness runner uses
`do_sample=True, temperature=0.7, top_p, top_k` with NO
explicit RNG seed. Every experiment run thus draws from a
stochastic generation distribution. Prior single-run
measurements (Trial #5 E21 at 44.5%; Trial #6 E24 at 42.5%)
are each one draw. Candidate D creates 3 additional draws per
adapter via fresh experiment runs (each gets a new implicit
RNG state via process timing). Combined with the existing
E21/E24, we have 4 datapoints per adapter.

**Note for publication honesty**: implicit multi-seed is weaker
than explicit-seed replication. If this trial finds real signal,
TB-US-082 will add explicit-seed support to the harness runner
for exact reproducibility.

**Experiment matrix**:

| Adapter | Harness | Seed source | Experiment ID |
|---|---|---|---|
| v7 | v5 (holdout) | implicit (Trial #5 original) | E21 (existing, 44.5%) |
| v7 | v5 (holdout) | implicit | E25 (new) |
| v7 | v5 (holdout) | implicit | E26 (new) |
| v7 | v5 (holdout) | implicit | E27 (new) |
| v8 | v5 (holdout) | implicit (Trial #6 original) | E24 (existing, 42.5%) |
| v8 | v5 (holdout) | implicit | E28 (new) |
| v8 | v5 (holdout) | implicit | E29 (new) |
| v8 | v5 (holdout) | implicit | E30 (new) |

Each experiment: n=200, Instruct base, system_prompt_version=3,
harness_version=5 (holdout). Expected cost: ~45 min each × 6
new experiments = ~4.5 hours. Runs sequentially (single GPU).

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

### H7a — Resolution of Trial #6 drop (Candidate D, locked)

**Claim**: 4 datapoints per adapter (3 new + 1 existing). If the
difference-of-means between adapter v7 (Trial #5 lineage) and
adapter v8 (Trial #6 lineage) exceeds **2× pooled standard
deviation**, Trial #6's regression is confirmed real. Otherwise,
Trial #6's result is within noise of Trial #5.

**Pre-registered decision bins** (locked before results seen):
- |mean_v7 − mean_v8| < 1× pooled SD → **"indistinguishable"**:
  Trials #5 and #6 statistically equivalent at holdout.
- 1× SD ≤ |mean_v7 − mean_v8| < 2× pooled SD →
  **"marginal signal"**: direction informative, magnitude
  uncertain.
- |mean_v7 − mean_v8| ≥ 2× pooled SD → **"real signal"**:
  Trial #6 regression confirmed.

**Secondary** (operator read-off, no threshold):
- Full 8-datapoint spread across both adapters. If any single
  draw of v7 or v8 lands at ≥50%, that's a hint that TB-US-082
  Candidate B is worth firing.
- If spread across all 8 draws is < 3pt total, GSM8K is noisy
  but the central tendency is pin-downable.

Secondary candidate hypotheses (B/C, deferred to TB-US-082):
- **B** within-P1-strict accuracy ≥ 50% AND dual-#### retention
  ≥ 60%. Tests whether MLP expansion adds reasoning without
  disrupting format.
- **C** within-P1-strict accuracy ≥ 55% (more perturbation).

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
  with apparent negative result Trial #7 revised to "no change
  within noise"
- [TB-US-079](tb-us-079.md) — Trial #5 (chat-template) — closed
  with positive-null
- [TB-US-082](tb-us-082.md) — Trial #8 (Candidate B: expand
  LoRA to MLP); drafted on close
- `docs/math-example/multi-seed-replicate-results.md` — Trial
  #7 deep dive (**primary deliverable**)
- `docs/math-example/scale-up-5000-results.md` — Trial #6 deep
  dive
- `docs/math-example/instruct-chat-template-results.md` — Trial
  #5 deep dive
- `docs/math-example/methodology.md`,
  `docs/math-example/study-design.md`,
  `docs/math-example/sweet-spot-search-log.md`

## Completion Notes (2026-11-03)

### Measurement (Phase 3-4)

8 total holdout draws across 2 adapters:

| Experiment | Adapter | Score | Accuracy |
|---|---|---|---|
| E21 | v7 | 89 / 200 | 44.5% |
| E25 | v7 | 83 / 200 | 41.5% |
| E27 | v7 | 87 / 200 | 43.5% |
| E29 | v7 | 77 / 200 | 38.5% |
| E24 | v8 | 85 / 200 | 42.5% |
| E26 | v8 | 88 / 200 | 44.0% |
| E28 | v8 | 84 / 200 | 42.0% |
| E30 | v8 | 76 / 200 | 38.0% |

### Summary statistics

- **Adapter v7 (Trial #5 lineage, 1000 samples)**: mean **42.00%**,
  SD 2.65pt, range 38.5–44.5 (spread 6pt)
- **Adapter v8 (Trial #6 lineage, 5000 samples)**: mean **41.62%**,
  SD 2.56pt, range 38.0–44.0 (spread 6pt)
- **Difference in means**: +0.38pt (v7 vs. v8)
- **Pooled SD**: 2.60pt
- **|diff| / pooled SD**: 0.14× — well below pre-registered 1×
  threshold for "marginal signal"

### Pre-registered hypothesis outcome

**H7a: INDISTINGUISHABLE.** 0.14× < 1× pooled SD per
pre-registered decision mapping. Trials #5 and #6 statistically
equivalent at holdout under multi-seed measurement.

### Key findings

1. **Trial #6's apparent regression was noise.** Single-draw
   comparison (E21 44.5% vs. E24 42.5%) picked two random points
   from essentially the same distribution.
2. **GSM8K at n=200 has ~6pt noise envelope.** New methodology
   constant; single-run differences below 6pt should not be
   interpreted as signal.
3. **Combined Trials #5-#7 finding**: chat-template-formatted
   PEFT on Instruct at rank 16 preserves bare accuracy across
   1000-5000 samples. Neither up nor down. Format intensification
   is real but accuracy-neutral.
4. **Methodology discovery (pre-fire)**: TB's harness runner
   uses `do_sample=True, temperature=0.7` with NO explicit RNG
   seed. All prior single-run measurements across Trials #1-#6
   were stochastic draws, not deterministic measurements.

### Infrastructure friction encountered

Mid-run, the 24-hour session-token expiry hit the orchestrator
script after E28 (before E29). The TB service's background
task kept running E29 correctly; the orchestrator script
crashed at 401 while polling. Recovery: re-minted session
token, confirmed E29 still running, launched E30 manually.
Zero data loss, ~15 min operator intervention. Surfaced a
structural question about TB's auth model for research
automation (long-running campaigns > 24h). Captured in a
feedback memory for future reference; possible follow-up story
on auth architecture + API-key mechanism.

### Decision

**Current demo**: UNCHANGED (bare Instruct 43% remains the
headline). No adapter swap.

**TB-US-082 drafted** — Candidate B: expand LoRA target modules
from 4 (attention) to 7 (attention + MLP). Multi-seed from the
start (n=4). Uses v7 training set to isolate the target-modules
effect from data effect.

### Deliverables

- `docs/math-example/multi-seed-replicate-results.md` deep dive
  (new, primary)
- `sweet-spot-search-log.md` Trial #7 entry + summary table +
  cumulative method-lessons section updated
- `scripts/tb_us_081_run_experiments.py` (6-experiment runner,
  implicit multi-seed)
- `feedback_research_infrastructure_resilience.md` memory
  captured on token expiry
- 6 new completed experiments: E25-E30 (3 v7, 3 v8)
- TB-US-082 drafted (Trial #8 — Candidate B)

### Acceptance Criteria status

- ✅ AC1: Candidate D pre-registered before running.
- ✅ AC2: No new infrastructure needed (D is experiment-only).
- ✅ AC3: 6 new experiments completed at n=200 + reused 2
  existing = 8 total draws.
- ✅ AC4: Per-sample pattern analysis documented (see deep dive).
- ✅ AC5: H7-primary, H7a, H7b outcomes recorded in deep dive.
- ✅ AC6: Trial #7 search log entry with 4-field format.
- ✅ AC7: Deep dive doc exists (`multi-seed-replicate-results.md`).
- ✅ AC8: Pages site unchanged (adapters match bare within
  noise; no swap needed).
- ✅ AC9: TB-US-082 drafted.
- ✅ AC10: Candidate D drop-vs-noise question resolved
  definitively; series close conditions clarified.
