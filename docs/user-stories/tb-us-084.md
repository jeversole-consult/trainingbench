# TB-US-084: Spike — Research methodology support in the TB UI (sans Claude)

**Status**: Backlog
**Type**: Design spike (produces a design doc + prioritized recommendations; NO code change)
**Created**: 2026-11-04
**Author**: Jesse Eversole
**Depends on**: Nothing hard — can land anytime; naturally lands after the
math-example research arc (TB-US-075 through TB-US-082) wraps up so the
design is grounded in validated methodology.

## Story

As a TB operator preparing the platform for ML users who will **not**
have Claude Code (or an equivalent agent) sitting alongside them, I
want **a design spike that identifies the research-methodology work
Claude has been doing during the math-example arc**, catalogs which
parts TB's UI currently supports and which parts it doesn't, and
produces **a prioritized design doc** for closing the gap — so that
the next TB maintainer (or ML user) can do rigorous research in TB
without needing Claude-equivalent support in the loop.

## Background

The math-example research arc (TB-US-075 through TB-US-082) has
developed a substantive methodology:

- Pre-registered hypotheses with decision thresholds
- Multi-seed replicate discipline (Trial #7 established the 6pt noise
  envelope)
- Per-sample pattern analysis (dual-#### retention, harness-priority
  breakdown, within-structure accuracy)
- Cross-trial comparison with noise-aware interpretation
- Deep-dive narrative per trial
- Self-correcting analysis when prior single-draw interpretations
  turn out to be noise

**Almost none of this methodology is expressed in the TB UI today.**
It lives in Claude's judgment, in `docs/math-example/methodology.md`,
and in the per-trial deep dives. A user coming to TB without Claude:

- Would create single experiments, not cohorts → interpret single
  draws as if they were deterministic measurements
- Would see "44% vs 42%" in the UI and read "adapter improved" —
  the UI gives no noise-envelope signal
- Would have no pre-registration form that locks interpretation
  before results are visible
- Would have no cross-trial comparison view
- Would get no automated anomaly flags or next-direction suggestions
- Would skip or do perfunctorily the per-trial deep-dive writeups
- Would likely not notice mid-execution surprises (labeling errors,
  architectural gaps, stochastic-sampling quirks) because the UI
  doesn't surface the underlying mechanisms

The methodology discipline developed during the math-example arc is
roughly 70% Claude-dependent at this point. Shipping TB to ML users
means closing that gap.

## Scope — this is a DESIGN SPIKE

This story's deliverable is a **design doc with prioritized
recommendations**. No code changes in this story. The design doc
becomes the input to subsequent implementation stories.

### Deliverable: `docs/design/research-methodology-support.md`

Expected structure (~3-5 pages):

1. **The problem statement.** What research-methodology work is
   Claude doing today that TB-UI-alone cannot support? Grounded in
   specific examples from TB-US-075 through TB-US-082.

2. **Gap analysis table.** Each row: a methodology capability (e.g.,
   "pre-register hypotheses", "multi-seed replicate", "cross-trial
   comparison", "per-sample pattern analysis", "deep-dive narrative",
   "noise-envelope-aware interpretation", "mid-execution surprise
   detection"). Columns: how Claude did it in this arc; what's in
   TB UI today; what's missing; rough implementation cost.

3. **Categorized candidate solutions.**
   - **Category A — UI mechanics**: "experiment cohort" as a
     first-class concept; pre-registration form at experiment
     creation; trial pages that aggregate training-run + training-set
     + adapter + cohort + interpretation; noise-envelope-aware
     comparison widgets.
   - **Category B — Research scaffolding**: "research mode" wizard;
     published-ranges context overlays; automated anomaly flags.
   - **Category C — Agentic help (TB-eats-its-own-food)**: in-app
     TB-agent that reads trial context and generates narrative,
     flags anomalies, suggests next directions. Uses TB's own
     agent architecture.
   - **Category D — Discoverability**: embedded tooltips /
     explainers; methodology link-outs at decision points.

4. **Prioritized recommendation.** A phased roadmap:
   - **Phase 1 (cheap, high-leverage)**: usually Category A + D.
   - **Phase 2 (research-scaffolding)**: Category B.
   - **Phase 3 (differentiating)**: Category C.
   - Each phase estimates rough effort (sprints) and identifies
     prerequisite work.

5. **Open design questions.** Things the spike must resolve
   explicitly before any Phase 1 story can fire (see "Questions" below).

6. **Scope boundaries.** What this methodology-support work does
   NOT try to solve (e.g., "TB is not trying to teach PhD-level
   statistics"; "TB is not a replacement for domain expertise").

### Not in scope

- Any code change — this is a spike that produces a document.
- A specific UI mockup — recommend patterns, not pixel-perfect designs.
  Pixel work happens in downstream implementation stories.
- Writing the in-app TB-agent's prompts — that's a sub-story under
  Category C if we go there.
- Multi-tenancy or external-user concerns — TB stays single-operator
  per install for v0.1.

## Open design questions (the spike must address)

1. **What's the minimum methodology enforceable via pre-reg UI
   without being annoying?** (Likely: primary hypothesis + success
   threshold + null threshold. Not: full threats-to-validity
   framework.)

2. **Should multi-seed be automatic or opt-in?** Default-to-cohort
   is methodologically correct but doubles-to-quadruples GPU cost
   per trial. The spike should propose a default and a
   change-rationale.

3. **How does the UI surface noise envelopes when the user doesn't
   provide one?** Options: compute from recent cohorts; show a
   literature-default; require user to establish one in a prior
   multi-seed pilot.

4. **For Category C (in-app agent), what context does it need?**
   Reading experiment rows + training-set JSONL + prior-trial deep
   dives + maybe methodology.md. The spike should scope what
   "context window" the TB-agent needs.

5. **How does the design interact with the versioned-component model
   (TB-US-052 agents)?** Cohorts are N experiments pinning the same
   adapter + harness + prompt. Does a cohort get its own row/ID,
   or is it derived from the shared pin pattern?

6. **Does this story imply a change to TB's data model?** E.g., a
   `cohorts` table that groups experiments; a `pre_registrations`
   table or JSON column; a `trials` concept at the row level?

## Requirements (one phase, since this is just a spike)

- [ ] R1: `docs/design/research-methodology-support.md` exists with
      the 6-section structure above.
- [ ] R2: Gap analysis table covers at least 7 methodology
      capabilities drawn from the math-example arc.
- [ ] R3: Each of the 4 categories (A/B/C/D) has at least 2-3
      concrete candidate solutions with 1-paragraph descriptions.
- [ ] R4: Prioritized roadmap identifies a Phase-1 set that could
      ship in 1 sprint and be independently valuable.
- [ ] R5: Open design questions explicitly listed; spike proposes
      a default answer for each but notes which require operator
      review before implementation.
- [ ] R6: Scope-boundaries section included so downstream
      implementation stories have a clear "not our problem" fence.
- [ ] R7: Cross-link from `docs/README.md` (design-docs section)
      and from the math-example `methodology.md` back to the new
      design doc.

## Acceptance Criteria

- [ ] AC1: Design doc exists at
      `docs/design/research-methodology-support.md`, ~3-5 pages.
- [ ] AC2: Gap analysis table present with ≥7 methodology
      capabilities + columns mapped to this arc's specific examples.
- [ ] AC3: Four categorized candidate-solution sections present.
- [ ] AC4: Phased roadmap with estimated effort per phase.
- [ ] AC5: Open design questions explicitly answered OR flagged
      for operator decision.
- [ ] AC6: Scope boundaries explicit.
- [ ] AC7: Cross-links in place.
- [ ] AC8: A follow-up Phase-1 implementation story drafted (TB-US-NNN)
      covering the first 2-3 UI mechanics to land. This is the
      spike's hand-off — it must produce not just a design but
      a next-implementable story.

## Design Notes

- **Why this is a spike, not a direct implementation story.** The
  problem surface area is large enough that jumping straight to
  implementation risks building the wrong thing. A design doc that
  catalogs the gaps and sequences the fixes gets everyone
  (operator, future maintainer, future user) on the same page.
- **Why "research methodology" specifically, not "UI polish".** We
  have UI tweaks (TB-US-045 umbrella) for cosmetic/ergonomic fixes.
  This is different: it's about embedding **methodology discipline**
  into the product. A pre-registration form isn't a UI tweak;
  it's an opinionated stance on how research should be done.
- **Why Category C (in-app agent) is deliberately last.** Building
  an embedded research-agent is TB's long-term differentiator but
  compounds complexity. Phases A/B/D are each independently valuable;
  they ship the methodology discipline without betting on the agent
  working well. If the agent proves out later, it becomes a force
  multiplier on the existing scaffolding rather than the scaffolding's
  only payoff.
- **Why grounded in the math-example arc.** The arc produced a
  concrete, lived methodology. Designing in the abstract ("what SHOULD
  research support look like?") risks over-engineering or missing
  the practical gaps. Designing from "this is what Claude did; now
  package it" is more honest.

## Out of Scope

- Code: no backend, no frontend, no database migration. Pure docs.
- Non-math domains: the initial design focuses on quantitative ML
  research (math-example-style). Qualitative-rating research
  (e.g., TB's chat-evaluation) can extend the design later.
- Multi-user / multi-tenant features — TB is single-operator per
  install.
- Publication-grade reproducibility infrastructure (explicit seeds,
  version-locked pip freeze, deterministic generation) — those are
  separate stories that PRECEDE this methodology-UX layer.

## Related

- The research arc that motivates this design:
  - [TB-US-075](tb-us-075.md) — Methodology foundations
  - [TB-US-076](tb-us-076.md) — Harness tolerance patch
  - [TB-US-077](tb-us-077.md) — Trial #4 regression + methodology win
  - [TB-US-078](tb-us-078.md) — Training-set wiring architectural fix
  - [TB-US-079](tb-us-079.md) — Trial #5 chat-template fix
  - [TB-US-080](tb-us-080.md) — Trial #6 scale-up
  - [TB-US-081](tb-us-081.md) — Trial #7 multi-seed replicate
  - [TB-US-082](tb-us-082.md) — Trial #8 MLP expansion
- The methodology as it stands today:
  - `docs/math-example/methodology.md`
  - `docs/math-example/study-design.md`
  - `docs/math-example/sweet-spot-search-log.md`
  - Per-trial deep dives in `docs/math-example/`
- The system architecture it would integrate with:
  - [TB-US-083](tb-us-083.md) — System architecture documentation
  - `docs/design/agent-architecture.md`
  - `docs/design/sweet-spot-architecture.md`
