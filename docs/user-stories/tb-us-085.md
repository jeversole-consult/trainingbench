# TB-US-085: Trial #9 — rank sweep at attn+MLP (closing trial of math-example arc)

**Status**: Completed
**Created**: 2026-11-05 (conversational launch during strategic discussion)
**Started**: 2026-11-05
**Completed**: 2026-11-06
**Author**: Jesse Eversole
**Depends on**: TB-US-082 (Trial #8 attn+MLP positive result)
**Commit hash(es)**: <filled in on closure commit>

## Note on this story's late drafting

This story's number (TB-US-085) was originally **reserved for
Candidate C (full fine-tune)** in the TB-US-082 close notes —
to be used only if Trial #8 (attn+MLP at rank 16) had failed to
produce a positive result. Trial #8 succeeded, so Candidate C
was never needed.

The slot was then re-used when Trial #9 (rank sweep at attn+MLP)
launched during a conversational strategy discussion. The
training run was named `tb-us-085-trial9-adapter-v10-rank32-mlp`
and the experiments were labeled `tb-us-085-trial9-eholdout-*`.
This story is drafted retroactively to document what actually
happened in the slot.

Any future full fine-tune work would get a new story number
(TB-US-090 or later). See the "Methodological note" section below
for the implications of this retroactive drafting.

## Story

As a TB operator closing out the math-example research arc, I
want **a rank sweep at the Trial #8 attn+MLP target-module set**
— specifically doubling rank from 16 to 32 while holding
everything else constant — to test whether more LoRA capacity
continues to help, or whether rank 32 hits an overfit wall at
1000 samples × 3 epochs.

This is the arc's closing trial. Operator decision (2026-11-06):
math-example has served its purpose as PEFT demonstration;
further trials (rank 64, full fine-tune, external data,
best-of-N inference, 70B model swap) are out of scope given cost
+ TB strategy. Research continues on stalite's side with
different priorities (small-dataset PEFT, deployment pathway,
proprietary-vs-open-source separation).

## Background

Trial #8 (TB-US-082, closed 2026-11-04) delivered the first
positive capability-gain result by expanding LoRA target modules
from 4 (attention) to 7 (attention + MLP) at rank 16. Mean
holdout 53.75%, +10.75pt vs bare Instruct.

Trial #8's mechanism finding: the "capacity trap at rank 16
attn-only" was specifically about **which** parameters LoRA
touched, not **how many**. Expanding to MLP unlocked reasoning
capacity.

Trial #9 tests the natural complementary question: now that the
target modules include MLP, does more rank continue to help?
Published math-LoRA work typically uses ranks in the 16-64 range
with varied target-module sets. Rank 32 is the next step in a
rank sweep.

**Risk**: Trial #4 had used rank 32 (with attention-only + raw-CoT
format) and REGRESSED by 20pt. But Trial #4 had two concurrent
bugs (format strip + wiring gap); the rank was not the root
cause. Trial #9's rank 32 is at the proper attn+MLP target set
with chat-template format — a configuration we understand works.

## Hyperparameters

Identical to Trial #8 EXCEPT LoRA rank (and alpha, which scales
with rank per standard practice):

| Hyperparameter | Trial #8 (v9) | **Trial #9 (v10)** |
|---|---|---|
| Base | Instruct | Instruct (same) |
| Training set | v7 (1000 samples) | **v7 (same — constant data)** |
| Target modules | 7 (attn + MLP) | 7 (same) |
| **LoRA rank** | 16 | **32** |
| **LoRA alpha** | 32 | **64** (2× rank, standard ratio) |
| LoRA dropout | 0.05 | 0.05 (same) |
| Learning rate | 1e-4 | 1e-4 (same) |
| Epochs | 3 | 3 (same) |
| Batch size × grad accum | 4 × 4 | same |
| Max eval samples | 200 | 200 (same) |
| Early stop | patience=2 | patience=2 (same) |

## Methodological note

**This trial was fired conversationally during an
audience/strategy discussion.** Unlike Trials #5-#8 which
followed formal pre-registration discipline (hypotheses +
thresholds locked BEFORE results seen), Trial #9 launched
without a formal H-threshold spec. The result stands but the
methodology was weaker than prior trials.

Post-hoc hypothesis framing (for narrative clarity only, NOT
pre-registered thresholds):
- Did rank 32 at attn+MLP continue to help? **Yes** (marginal
  signal; direction clear)
- Did it overfit catastrophically? **No** (eval rose 0.02 at
  epoch 3; load_best_model_at_end caught epoch-2 checkpoint)
- Did it approach the published math-LoRA band? **Yes** (60.12%
  is at the low end of the 60-75% published range)

## Deliverables

- [x] R1: Adapter v10 trained via `/training/runs/launch`
      (run_id 16, 28.9 min)
- [x] R2: Adapter v10 released + promoted
- [x] R3: 4 multi-seed holdout experiments (E36-E39) at n=200
- [x] R4: Per-sample pattern analysis
      (`scripts/tb_us_085_analysis.py`)
- [x] R5: Deep dive at `docs/math-example/rank-sweep-results.md`
- [x] R6: Trial #9 entry in `sweet-spot-search-log.md`
- [x] R7: Summary table row for Trial #9 in search log
- [x] R8: `methodology.md` position table updated
- [x] R9: Pages site `staged-progression.md` updated to lead with
      adapter v10 at 60.12%
- [x] R10: BACKLOG row + this story close notes

## Acceptance Criteria

- [x] AC1: Adapter v10 trained + auto-registered with
      `training_set_version_id=7`
- [x] AC2: 4 holdout multi-seed experiments complete at n=200
- [x] AC3: Per-sample pattern analysis documented
- [x] AC4: Mean + SD + range computed; noise-envelope framework
      applied
- [x] AC5: Verdict recorded (MARGINAL SIGNAL per Trial #7 bins)
- [x] AC6: Deep dive doc exists
- [x] AC7: Pages site reflects new demo (adapter v10 at 60%)
- [x] AC8: Research arc closed with operator-stated reasons

## Completion Notes (2026-11-06)

### Headline

**Adapter v10 (rank 32 attn+MLP) holdout mean 60.12% (SD 4.52pt,
4 draws, range 54.0-64.0).** +6.38pt over adapter v9's 53.75%
mean. Pre-registered Trial #7 noise-envelope verdict: **MARGINAL
SIGNAL** (|diff|/pooled-SD = 1.70×, in the 1-2× bin). Direction
unambiguously positive; magnitude uncertain at n=4 per adapter.

### Secondary findings

- **Approaching the published 60-75% math-LoRA band for the
  first time in the series.**
- **SD jumped** (v9: 2.78pt → v10: 4.52pt). More capacity = more
  seed variability. Likely explanations: larger adapter = more
  seed sensitivity; overfit proximity; small-n SD-estimate
  noise.
- **Within-P1-strict accuracy +12.3pt vs. bare** (bare 48.2% →
  v9 54.0% → v10 60.5%). Real reasoning capacity gain.
- **Dual-#### retention re-intensified** (v9: 47% → v10: 59%).
  Unlike v9 which was bare-like, v10 learns both reasoning
  AND format rigidity. Larger capacity means the adapter doesn't
  have to choose.
- **Eval loss showed early-overfit signal** at epoch 3 (0.423 →
  0.443). `load_best_model_at_end=True` captured the epoch-2
  checkpoint. Early stop didn't fire (only 1 worsening observed;
  needs 2 consecutive).

### Research arc closes here

Operator decision 2026-11-06: math-example has served its
purpose as **academic background on PEFT**. Further gains
require compute we're not investing (70B model, full-FT), data
engineering (MATH/MGSM augmentation), or inference-time tricks
(best-of-N) — all out of scope for TB's current strategy.

**Current demo**: adapter v10 at ~60% mean holdout. Approaches
published math-LoRA band; demonstrates what PEFT can accomplish
on a single consumer GPU with 1000 training samples. Pages site
updated.

**Research continues on stalite's side** with different
priorities: small-dataset PEFT research (operator's genuine
interest), deployment pathway (open question), proprietary-vs-
open-source separation (structural).

### Deliverables

- `docs/math-example/rank-sweep-results.md` deep dive (primary)
- `sweet-spot-search-log.md` Trial #9 entry + updated summary
  table + updated cumulative-method-lessons
- `methodology.md` position-vs-prior-work table row added
- `docs/pages/staged-progression.md` demo swap v9 → v10 +
  nine-trial narrative + mechanism explanation + reproduction
  snippet
- `scripts/tb_us_085_run_experiments.py` (4-experiment runner)
- `scripts/tb_us_085_run_remaining.py` (recovery runner used
  when the initial runner died after E36)
- `scripts/tb_us_085_analysis.py` (per-sample analysis)
- `adapter_versions.v10` (released + promoted)
- Experiments E36-E39 (all `completed`)
- Research arc close noted in search log cumulative-lessons
  section

## Out of Scope

- Rank 64 or higher (overfit risk at this training data size)
- Full fine-tuning (operator cost decision)
- External-data augmentation (operator scope decision)
- Best-of-N inference (operator scope decision)
- 70B model swap (hardware cost)
- Any new trial in math-example series

## Related

- [TB-US-082](tb-us-082.md) — Trial #8 attn+MLP positive result
  (direct predecessor; motivated this trial)
- [TB-US-081](tb-us-081.md) — Trial #7 multi-seed (established
  noise envelope framework used here)
- [TB-US-079](tb-us-079.md) — Trial #5 chat-template format fix
  (foundation)
- `docs/math-example/rank-sweep-results.md` — Trial #9 deep dive
  (primary deliverable)
- `docs/math-example/mlp-expansion-results.md` — Trial #8 deep dive
- `docs/math-example/sweet-spot-search-log.md` — chronological
  record
- `docs/math-example/methodology.md` — research protocol
