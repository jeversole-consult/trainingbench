# TB-US-089: Math-example retrospective + "how to do this with TB alone" gap analysis

**Status**: Backlog
**Type**: Documentation + gap-analysis spike
**Created**: 2026-11-06
**Author**: Jesse Eversole
**Depends on**: TB-US-085 close (math-example arc has ended;
retrospective can now be written)
**Blocks (soft)**: TB-US-005 (public cut) — the retrospective
becomes part of TB's academic-PEFT documentation surface, and
the gap-analysis informs US-005 scope
**Commit hash(es)**: <filled in on completion>

## Story

As a TB operator closing out the math-example research arc, I
want **two companion artifacts**:

1. A **math-example retrospective** that packages the whole
   9-trial journey as academic/teaching material — the strategy,
   methodology, mechanism findings, and ending state — so that
   a teacher, a student, or an ML researcher can read one doc
   and understand how to approach small-dataset PEFT research
   as it was actually conducted here.
2. A **"how to do this with TB alone" gap analysis** — honest
   accounting of what the research arc required (Claude-driven
   scripting, methodology discipline, narrative writing,
   cross-trial synthesis) vs. what TB today can support via its
   own UI. This becomes concrete motivation for TB-US-084
   (methodology UI design spike) and TB-US-086's Tier-1 resurface
   items.

Both artifacts together answer: "here's what we did, here's what
we found, and here's what a user without Claude could and
couldn't replicate inside TB today."

## Background

The math-example research arc spanned TB-US-075 through
TB-US-085 — nine trials that produced:

- A documented methodology (pre-registration, multi-seed, noise
  envelope, per-sample pattern analysis, deep-dive narratives)
- Four substantive findings (format necessity, capacity trap
  mechanism, MLP target-module unlock, rank-sweep marginal
  gain)
- One positive capability-gain result (adapter v10 at ~60%
  holdout — approaching the published 60-75% math-LoRA band)
- A collection of per-trial deep dives, a chronological search
  log, a methodology doc, and a Pages site demo

**The arc is complete.** Operator decision (2026-11-06):
math-example has served its purpose as academic background on
PEFT; further compute is out of scope.

But the ARC was done with Claude Code driving the mechanical
work (writing prep scripts, launching training via API, creating
+ running experiments, per-sample analysis, deep-dive writing,
pre-registration tracking, cross-trial synthesis). **TB's UI
today cannot replicate most of this flow.** Without Claude, a
user attempting to redo this research would need their own
scripting ability, methodology discipline, and documentation
practice — which raises TB's floor-of-utility above what we'd
want for the external-ML-researcher and educator audiences.

This story captures both the research artifact (retrospective)
AND the honest gap analysis — because the gap analysis is what
actually motivates the methodology-UI work (TB-US-084) and the
resurface roadmap (TB-US-086's Tier-1 items).

## Scope

### Deliverable 1: `docs/math-example/retrospective.md`

**Audience**: teacher, student, ML researcher coming cold.
**Length**: 5-8 pages.

**Structure**:

1. **What the research was about**. The question (can PEFT on
   Llama 3.1 8B Instruct materially improve GSM8K accuracy at
   consumer-GPU scale?). The frame (research-mode methodology,
   not production tuning).

2. **The methodology we developed**. Pre-registration. Multi-seed
   replicates. Noise envelope characterization. Per-sample
   pattern analysis. Deep-dive-per-trial discipline. Mechanism
   confirmation via within-structure accuracy decomposition.

3. **Trial-by-trial narrative** (compact):
   - Trials #1-#3 (base variant era — foundational, with harness
     bug discovery and overfit cautionary tale)
   - Trial #4 (Instruct scale-up REGRESSED by 20pt; methodology
     surfaced the bare-control measurement that revealed the
     regression)
   - Trial #5 (chat-template format fix recovered the regression
     but didn't improve over bare — positive-null; format/capability
     decoupling first observed)
   - Trials #6-#7 (scale-data no-op; multi-seed revealed the
     "regression" was noise; 6pt noise envelope established;
     stochastic-sampling methodology slip discovered)
   - Trial #8 (first positive capability-gain result; attn+MLP
     target modules unlocked reasoning; capacity-trap mechanism
     confirmed)
   - Trial #9 (rank sweep: marginal signal for rank 32; approach
     published band; arc closes)

4. **The mechanism confirmed**. LoRA capacity trap at rank 16
   attn-only; format-reinforcement as compensation when
   reasoning capacity is inaccessible; MLP target-module reach
   as the lever; rank sweep extends the gain at the cost of
   seed variability.

5. **What was NOT pursued and why**. Rank 64 (overfit risk),
   full fine-tune (compute cost), external data (scope),
   best-of-N (scope), 70B model (hardware).

6. **Reproducibility checklist**. Base model identifier + rev,
   training-set sidecar + sha256, hyperparameters, hardware,
   software versions, adapter artifacts, measurement
   configuration.

7. **Links to deep-dive docs** for each trial.

### Deliverable 2: gap-analysis section in the retrospective (or separate file)

**Audience**: TB maintainer, future TB-US-084 implementer.

**Structure**:

Catalog each methodology capability the research arc required,
and whether TB-today's UI supports it:

| Capability | What Claude did | What TB UI supports | Gap |
|---|---|---|---|
| Prep scripts (training-set-version JSONL files from GSM8K) | Python script per trial | nothing — API registration OK but no in-UI prep | **Major** |
| Training launches with pinned hyperparameters | API call via script | ✓ (training-run launch UI exists) | — |
| Multi-seed experiment replicates (n=4) | Script runs 4 experiments sequentially | create 1 experiment at a time via UI (TB-US-070 Proposed = Experiments UI; cohorts not a first-class concept) | **Moderate** |
| Noise-envelope-aware result interpretation | Claude computed SD + pooled-SD + verdict | nothing — UI shows raw numbers | **Major** |
| Pre-registration (hypothesis + thresholds locked before results) | Markdown in story file | nothing — no UI concept | **Major** |
| Per-sample pattern analysis (dual-#### retention, within-P1-strict accuracy, harness-priority breakdown) | Python scripts | nothing — raw per-sample output stored in `experiments.results_json` but not surfaced | **Moderate** |
| Deep-dive narrative per trial | Claude authored | nothing — no auto-narrative | **Major** (or just: accept that narrative is operator-authored) |
| Cross-trial comparison + summary tables | Claude synthesized | nothing — each experiment is its own row | **Moderate** |
| Mid-execution surprise detection (labeling error, stochastic sampling, capacity trap) | Claude noticed during execution | nothing — operator-dependent | **Open** (hard to automate; may be inherent to research) |

For each gap, map to the TB-US-NNN story that would address it
(if any). TB-US-084 covers the big ones (cohorts, pre-reg,
noise-envelope-aware UI, trial pages). TB-US-086's Tier-1
(experiments UI, version-lifecycle UI) covers some mechanics
but not methodology.

## Requirements

- [ ] R1: Draft `docs/math-example/retrospective.md` with the
      7-section structure
- [ ] R2: Gap-analysis table included (either in the same doc
      or a separate `docs/design/methodology-gap-analysis.md`)
- [ ] R3: Cross-link from `docs/README.md` ("Math-example
      research arc — retrospective" under the math-example
      demo section)
- [ ] R4: Cross-link from the methodology.md "Publication
      artifact plan" section (now appropriate since arc is done)
- [ ] R5: TB-US-084 story updated to reference this
      gap-analysis as concrete grounding for its design doc
- [ ] R6: TB-US-086 story updated to reference this gap analysis
      as the methodology-side companion to the feature-side
      audit
- [ ] R7: Length target met (retrospective ≈ 5-8 pages;
      gap-analysis ≈ 2 pages)

## Acceptance Criteria

- [ ] AC1: Retrospective doc exists at the target path
- [ ] AC2: Gap analysis exists (either embedded or standalone)
- [ ] AC3: All 7 retrospective sections present
- [ ] AC4: Gap table covers ≥ 9 capabilities (minimum of the
      list above)
- [ ] AC5: Each gap maps to a story (TB-US-084, TB-US-086
      tier-1, or "no story — inherent limitation")
- [ ] AC6: Cross-links in place
- [ ] AC7: The retrospective reads as self-contained — a teacher
      or ML researcher can pick it up with no prior TB context
      and understand both the research arc and the methodology

## Design Notes

- **Why this is a design/documentation story, not implementation.**
  The research arc is done; there's no new code to write. The
  question is how to PACKAGE what we learned so it serves the
  academic/teaching purpose + motivates the UI work.
- **Why bundle retrospective + gap-analysis into one story.**
  They answer two different questions but from the same source
  material. Writing them separately would duplicate the trial-by-
  trial synthesis. Also: the gap-analysis only makes sense IF a
  reader has absorbed the retrospective (knows what was done
  before learning what couldn't be done without Claude).
- **Why the methodology-UI story (TB-US-084) doesn't subsume this.**
  TB-US-084 is a design spike that proposes what UI changes could
  close the methodology gap. This story provides the grounded
  evidence of what the gap actually is, tied to the specific
  research arc that revealed it. The two are complementary.
- **Why NOT ready to publish externally.** Per the
  `feedback_research_not_ready_to_publish` memory: research-grade
  documentation standard-of-care applies, but external-publication
  readiness is a separate decision. The retrospective is TB's
  internal academic artifact; external sharing (paper, blog post)
  is an operator decision after further validation (multi-seed
  Trial #9, cross-dataset, replication).

## Out of Scope

- Any new experiments or research
- Re-running or extending math-example
- Full publication-grade write-up (preprint, conference paper)
- Cross-dataset validation (MATH, MGSM, etc.)
- Explicit-seed replication (separate story if we want to invest)

## Related

- [TB-US-085](tb-us-085.md) — Trial #9 close (arc end state)
- [TB-US-082](tb-us-082.md) — Trial #8 first positive result
- [TB-US-084](tb-us-084.md) — Methodology UI design spike
  (companion; this story grounds it)
- [TB-US-086](tb-us-086.md) — Backend feature audit (companion)
- `docs/math-example/methodology.md` — research protocol
- `docs/math-example/sweet-spot-search-log.md` — chronological
  record
- Per-trial deep dives (measured-improvement.md,
  harness-tolerance-results.md, format-retrain-results.md,
  instruct-scale-up-results.md,
  architectural-finding-training-set-wiring.md,
  instruct-chat-template-results.md,
  scale-up-5000-results.md, multi-seed-replicate-results.md,
  mlp-expansion-results.md, rank-sweep-results.md)
