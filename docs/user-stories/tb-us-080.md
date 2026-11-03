# TB-US-080: Trial #6 — capability-gain levers on Instruct (post-chat-template)

**Status**: Completed
**Candidate chosen**: **A — Scale training data 5x (1000 → 5000)**
**Pre-registered**: 2026-11-02
**Created**: 2026-11-02
**Started**: 2026-11-02
**Completed**: 2026-11-03
**Author**: Jesse Eversole
**Depends on**: TB-US-079 (chat-template Trial #5 — closed with
positive-null finding: format fix preserves bare Instruct but
doesn't improve it)
**Commit hash(es)**: <filled in on closure commit>

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

## Chosen candidate: A — Scale training data 5x (2026-11-02)

**Why A over B/C/D**: published math-LoRA literature (Qwen,
MetaMath, DeepSeek) typically uses 10,000-50,000+ samples;
Trial #5's 1000-sample run was undersized by an order of
magnitude. Scaling data is the most-cited "capability unlock"
lever in the published work on this exact setup. Operator chose
5x over 10x to balance speed-of-iteration against lift
probability — if 5x doesn't lift, 10x is unlikely to lift
enough more to be worth the extra 2-3h training time without
also varying another lever.

### Locked hyperparameters (Trial #6)

| Hyperparameter | Trial #5 (v7) | **Trial #6 (v8)** | Notes |
|---|---|---|---|
| Base | Instruct | Instruct (same) | isolates data-scale effect |
| Training data format | chat-template v7 | **chat-template v8** | same format discipline |
| **Training-set size** | 1000 | **5000** | **the lever under test** |
| Sampling seed | 46 | **47** | fresh sample; overlap with v7 allowed |
| LoRA rank | 16 | 16 (same) | |
| LoRA alpha | 32 | 32 (same) | 2× rank |
| LoRA dropout | 0.05 | 0.05 (same) | |
| Learning rate | 1e-4 | 1e-4 (same) | |
| Epochs | 3 | 3 (same) | |
| Batch size | 4 | 4 (same) | |
| Grad accum | 4 | 4 (same) | |
| Max eval samples | 200 | 200 (same) | GSM8K test |
| Early stop | patience=2 | patience=2 (same) | **now has 3 evals** → can fire |

**Key difference from Trial #5**: with 5000 samples × 3 epochs,
we'll have ~940 optimizer steps instead of 189. At the default
eval cadence (per-epoch), we get 3 eval checkpoints which
means early-stop patience=2 CAN now fire. H5d (N/A at Trial #5)
is testable here.

### Alternative candidates (deferred to TB-US-081 if H6 misses)

- **Candidate B** — Expand LoRA target modules to MLP
- **Candidate C** — Full fine-tuning (not LoRA)
- **Candidate D** — Multi-seed replicate of Trial #5

Original pre-fire-time listing retained in git history for the
"what did operator consider" record.

### Pre-run observation (noted before training)

GSM8K's train split contains only **7473 rows total**. v8 at 5000
samples = **67% of all available training data**. v7 at 1000
samples = 13%.

**Overlap**: v8 ∩ v7 = 698 rows. So the "new signal" in v8 vs.
v7 is only 302 fresh problems (~30% of v7's size). Expected
overlap by random sampling = 1000 × 5000 / 7473 ≈ 669; observed
698 is right in line.

**Interpretation**: this trial tests "5x the training rows seen"
rather than "5x the training examples universe." If H6-primary
is NOT met, candidate interpretations include:
- (a) 5x same-domain data doesn't add new reasoning signal, OR
- (b) GSM8K's 7473-sample ceiling is simply too small to unlock
      capability for this base; a dataset switch (MATH, MGSM,
      synthetic) may be needed, OR
- (c) non-data levers (B/C) are the right direction

If H6-primary IS met, the lesson is simply "more training rows
seen helps" — and we'd want to test with multi-seed in TB-US-081
to pin the effect size.

## Pre-registered hypotheses (Candidate A, locked 2026-11-02)

### H6-primary — Capability gain over bare Instruct

**Claim**: holdout accuracy ≥ 50% (bare + 7pt).

**Null**: holdout accuracy < 48% (within bare's noise band).

**Decision threshold**: holdout ≥ 50% at n=200 = primary accepted;
< 48% = null supported; 48-50% = inconclusive (recommend
multi-seed replicate in TB-US-081).

### H6a — Within-structure accuracy lift

**Claim**: within-P1-strict accuracy ≥ 50% (vs. Trial #5's 44.7%).

**Signal**: more data helps the model solve more problems within
the (already-locked) `#### N` structural format. Trial #5
demonstrated the adapter CAN learn format rigidity; H6a tests
whether 5x more training signal produces capability inside that
format.

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
  training) — positive-null; motivated this trial
- [TB-US-078](tb-us-078.md) — training-set-version wiring
  (foundation)
- [TB-US-081](tb-us-081.md) — Trial #7 (remaining candidates
  B/C/D); drafted on close
- `docs/math-example/scale-up-5000-results.md` — Trial #6 deep
  dive (**primary deliverable**)
- `docs/math-example/instruct-chat-template-results.md` — Trial
  #5 deep dive
- `docs/math-example/methodology.md`,
  `docs/math-example/study-design.md`,
  `docs/math-example/sweet-spot-search-log.md`

## Completion Notes (2026-11-03)

### Training (Phase 3)

- Run #14 completed in 1h 54min (6835s), 939 optimizer steps
  across 3 epochs. Train loss 2.289 → 0.377. Eval loss (per-epoch):
  0.4170 → 0.4121 (best) → 0.4136.
- Adapter v8 (`adapters/math-example/v8`, `adapter_versions.v8`,
  content_sha256 `45811c85…`) auto-registered with
  `training_set_version_id=8` provenance linkage; released +
  promoted via API.
- `load_best_model_at_end=True` verified correct via MD5 of
  `final/adapter_model.safetensors` matching checkpoint-626
  (epoch 2, best eval), NOT checkpoint-939 (epoch 3).

### Measurement (Phase 4) — two experiments at n=200

| Experiment | Setup | Score |
|---|---|---|
| E23 (E_in_v8) | adapter v8 × baseline-test (harness v4) | 75 / 200 (**37.5%**) |
| E24 (E_holdout_v8) | adapter v8 × holdout (harness v5) — primary | 85 / 200 (**42.5%**) |
| E22 (reused from Trial #5) | bare Instruct × holdout — control | 86 / 200 (43.0%) |

### Analysis (Phase 4)

**Full series comparison** (score; dual-#### retention):

| Setup | baseline-test | holdout |
|---|---|---|
| Bare Instruct | 86/200 (43%); 45.5% | 86/200 (43%); 45.0% |
| Adapter v7 (Trial #5, 1000) | **88/200 (44%); 63.0%** | **89/200 (44.5%); 60.5%** |
| Adapter v8 (Trial #6, 5000) | 75/200 (37.5%); **74.0%** | 85/200 (42.5%); **74.5%** |

### Hypothesis outcomes

- **H6-primary (holdout ≥ 50%)**: ❌ NOT MET (42.5%).
- **H6a (within-P1-strict ≥ 50%)**: ❌ NOT MET (42.9% within-structure
  on holdout vs. Trial #5's 44.7%).
- **H6b (no regression ≥ 43%)**: ❌ NOT MET on baseline-test (37.5%
  is 5.5pt below bare, clearly outside noise band). MARGINAL on
  holdout (42.5%, −0.5pt vs. bare, within noise).
- **H6c-strong (≥60%)**: ❌ NOT MET.
- **H6d (early stop testable)**: ✅ INFRASTRUCTURE VALIDATED — 3
  evals computed; `load_best_model_at_end` verifiably selected
  epoch-2 checkpoint; patience=2 mechanism intact but didn't
  fire (only 1 worsening eval; needs 2 consecutive).

### Key finding

**Scaling training data 5x (1000 → 5000) did not help and modestly
hurt baseline-test accuracy.** Within-structure accuracy per
`#### N` output: bare 48.2% → v7 44.7% → **v8 42.9%**. Each
training step moves farther from bare's within-structure
capability. Simultaneously, dual-#### retention intensified
from 60-63% → **74-74.5%** — the adapter learned the structural
format MORE rigidly as data increased. Trial #5's "format and
capability decoupled" finding is now pronounced into a cascade:
**more training = more format overfitting = less capability.**

### Three plausible mechanisms (not mutually exclusive)

1. **Dataset exhaustion** — 5000/7473 = 67% of GSM8K train;
   marginal new signal only ~302 problems vs. v7 (698/1000
   overlap).
2. **LoRA capacity trap at rank 16** — limited expressive
   bandwidth; format wins at 5000 samples.
3. **Format-overfitting cascade** — more reinforcement of the
   `#### N` pattern replaces bare Instruct's hedged correct
   answers with confident wrong ones.

### Decision

**Current demo**: UNCHANGED (bare Instruct 43%). Adapter v8 is
strictly inferior to adapter v7 on measured dimensions; NOT
promoted. Stays in registry as historical.

**TB-US-081 drafted** with 3 remaining candidates:
- **D (recommended first)** — Multi-seed replicate (resolves
  "is Trial #6's drop real or noise?")
- **B** — Expand LoRA target modules to MLP
- **C** — Full fine-tuning

### Deliverables

- `docs/math-example/scale-up-5000-results.md` deep dive (new)
- `sweet-spot-search-log.md` Trial #6 entry + updated summary
  table
- `scripts/prep_math_v8_chat_template_5000.py` (v8 prep)
- `scripts/tb_us_080_run_experiments.py` (2-experiment runner)
- `scripts/tb_us_080_analysis.py` (per-sample pattern analysis
  across Trials #4-#6)
- `training_set_versions.v8` (5000 samples, released + promoted)
- `adapter_versions.v8` (released + promoted)
- Experiments E23, E24 (both `completed`)
- TB-US-081 draft (Trial #7 — remaining B/C/D candidates)

### Acceptance Criteria status

- ✅ AC1: Candidate A pre-registered before training.
- ✅ AC2: Training completed; adapter v8 auto-registered.
- ✅ AC3: Measurement experiments complete at n=200.
- ✅ AC4: Per-sample pattern analysis documented.
- ✅ AC5: H6a / H6b / H6c / H6c-strong / H6d all recorded.
- ✅ AC6: Trial #6 search log entry with 4-field format.
- ✅ AC7: Deep dive doc exists.
- ✅ AC8: Pages site unchanged (adapter v8 strictly worse than
  adapter v7; no demo swap).
- ✅ AC9: TB-US-081 drafted.
