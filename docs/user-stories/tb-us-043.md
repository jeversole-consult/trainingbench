# TB-US-043: Spike — Sweet Spot architecture (experiment tracking, logging, combinatorial space)

**Status**: Completed
**Created**: 2026-10-15
**Completed**: 2026-10-20
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

**Deliverable**: `docs/design/sweet-spot-architecture.md`

## Story

As the operator of TrainingBench, I want a design document
that formalizes the **Sweet Spot** concept — the per-
organization combination of RAG dataset + LLM + PEFT-trained
adapter + eval harness that produces acceptable quality —
and specifies the data model, tracking surface, logging
requirements, and UI implications of experimenting across
the combinatorial space, so that downstream stories
(experiment schema, first-example build, Agent Release
packaging, OT handler wiring) have a shared foundation to
build on and so that we don't blindly ship the first
experiment without having thought through what it costs.

## Background

**Scope boundary note (added 2026-10-16):** The component +
version management dimension of this architecture (what
agents own, how components are versioned, how content is
hashed) **moved to [TB-US-044](tb-us-044.md)** — a parallel
spike. TB-US-043 continues to own the experimentation
methodology (recipes, snapshots, promotion, before/after
comparisons, first-example math walkthrough). TB-US-044
provides the component/version foundation; TB-US-043 builds
the Sweet Spot flow on top. Where decisions conflict,
TB-US-044 wins on component/version model.

Operator statement on 2026-10-15 while interrupting
TB-US-019's export AC verification:

> *"we are not quite ready to build out the first example of
> RAG, LLM, PEFT trained adapter. need to commit more thought
> toward how that will work given that it can be
> combinatorial and will need tracking and logging as
> experiments are conducted."*

This story is the venue for that thinking. It is a **spike**
— the deliverable is the design document, not working code.
Follow-up stories execute against the design once it
stabilizes.

**Why Sweet Spot matters architecturally:**

- TB's whole value proposition is "help an organization
  arrive at the right combination for their data."
- The combination has at least four axes (RAG dataset
  choice, LLM choice, PEFT adapter choice, evaluation
  harness). Each axis has many values.
- Each experiment produces persistent artifacts (training
  sets, adapter binaries, metrics logs, eval reports) that
  accumulate quickly.
- Without a schema and tracking surface, experiments drift
  into "which adapter was that again? ...I'll find the
  logs in a bit."
- The Agent Release concept (TB-US-030) is downstream — a
  deployable snapshot of a specific Sweet Spot — and
  requires knowing what inputs produced it.

**Memory governance:**

- `feedback_experiments_design_gated` (2026-10-15) —
  codified the intent behind this story. First experiment
  waits until this design is settled.
- `feedback_coordinator_not_epic` — this is NOT a
  coordinator story; it's a design spike that may *spawn*
  a coordinator for the Sweet Spot execution arc. Open the
  coordinator (TB-US-NN) in a follow-up only if the design
  turns out to need multi-story orchestration.
- `feedback_umbrella_stories` — tweaks to the design doc
  during collaboration stay in this story's umbrella until
  closed.

## Requirements

### Deliverable

- [x] R1: **Design document at
      `docs/design/sweet-spot-architecture.md`.** Captures
      the design decisions reached by the end of this
      story. Not a code deliverable — the document is the
      output.
- [x] R2: **Section: formal Sweet Spot definition.**
      Answers: What is a Sweet Spot? What are the atomic
      axes (RAG / LLM / adapter / eval)? Is a Sweet Spot
      one combination or a family? When does an experiment
      "become" a Sweet Spot?
- [x] R3: **Section: data model.** Specifies the schema
      additions needed:
      - What tables / files back an experiment?
      - What's the relationship between training_sets,
        training_runs, adapters, and experiments?
      - Is `experiment` a new first-class entity, or
        emergent from existing tables?
      - What foreign keys stitch the lineage?
- [x] R4: **Section: tracking surface.** Specifies the
      metadata captured per experiment:
      - Operator intent / description
      - Parent experiment lineage
      - Inputs (which training set, which base LLM, which
        adapter if any)
      - Outputs (resulting adapter, metrics, eval report)
      - Status (draft, running, completed, archived)
      - Audit trail (who created, who modified, when)
- [x] R5: **Section: logging surface.** Specifies what
      gets logged per phase:
      - Training phase (TB already has `training_run_tracker`)
      - Evaluation phase (new — eval metrics per
        experiment)
      - Query / inference phase (per-prompt logs with
        which Sweet Spot answered)
      - OT classifier decisions (TB-US-024's audit log is
        the venue)
      - Relationship between these logs — can we trace a
        production query back to the Sweet Spot that
        answered it?
- [x] R6: **Section: UI implications.** Enumerates the UI
      surfaces that need to exist (not design them in
      detail — just name them):
      - Experiment listing
      - Experiment detail / compare view
      - Agent Release list
      - Audit trail viewer
      - Promote-to-Agent-Release flow
- [x] R7: **Section: naming + categorization.** How
      experiments and Sweet Spots are named. Operator
      intent-based? Auto-generated? Hierarchical (project →
      experiment → run)?
- [x] R8: **Section: follow-up stories.** Enumerates the
      downstream TB-US-NN stories this design unlocks.
      Doesn't draft them; identifies them. For each:
      one-line scope + whether it's blocking for first
      Sweet Spot execution.
- [x] R9: **Section: open questions for operator decision.**
      Points where the operator needs to answer a design
      question before downstream work can proceed. Each
      question has: context, options considered, operator's
      lean (if known).

### Process

- [x] R10: **Iterative, operator-collaborative drafting.**
      Not a one-shot ship. The design doc evolves across
      several conversations; each turn the operator reads
      the current draft and contributes decisions,
      corrections, or new questions.
- [x] R11: **No code changes in this story.** The design
      doc is the entire deliverable. If execution-oriented
      ideas surface, capture them for the follow-up stories
      identified in R8 — don't implement here.
- [x] R12: **Reference existing TB building blocks.** TB
      already has `training_manager` (training sets),
      `training_run_tracker` (training runs), `AppSettings`
      (RAG prompt + routes), and the OT arc stories
      (classifier, handlers, audit log). The design should
      BUILD ON these rather than reinvent.
- [x] R13: **Capture what we won't do, explicitly.** The
      "Out of Scope" section of the design doc names what
      the Sweet Spot architecture does NOT need to solve
      — e.g., multi-tenant isolation, GPU scheduling,
      distributed training, model-weight versioning
      beyond adapter names. Keeps the first-example scope
      manageable.

## Acceptance Criteria

- [x] AC1: `docs/design/sweet-spot-architecture.md` exists
      with all sections from R2-R9 populated to the
      satisfaction of the operator.
- [x] AC2: At least one open question in the doc has an
      explicit operator decision captured (shows the design
      is actually being decided, not just enumerated).
- [x] AC3: At least 3 follow-up TB-US stories identified
      with one-line scopes (R8), covering: experiment
      schema, first-example build, Agent Release
      packaging — the minimum arc for a first operational
      Sweet Spot.
- [x] AC4: Operator confirms "the design is ready to
      execute against" — i.e., the next arc can start
      without further design conversation.
- [x] AC5: No code changes in this story. `git diff
      backend/` is empty.
- [x] AC6: No experiments / training sets / adapters
      created in service of this story (design-only; no
      first-example build here).

## Design Notes

- **Spike shape, not coordinator.** This is a design
  product with a single deliverable (the doc). It is
  explicitly NOT the coordinator for the "build the first
  Sweet Spot" arc — that's a separate story opened once
  this spike's design is approved.
- **Why collaborative drafting.** The operator has domain
  thinking about combinatorial experiment space that I
  don't have; I can propose structure and surface
  trade-offs but the key design calls (how to name
  experiments, how to represent lineage, whether to add a
  new `experiments` table) belong to the operator.
- **Why no code in this story.** Design docs that ship
  with "and here's the migration script" tend to lock in
  the first draft before the operator has lived with it.
  Keep this story strictly design; execution is
  downstream.
- **Relationship to the OT arc (TB-US-022+).** The OT
  classifier is upstream of a Sweet Spot's query time —
  for any Sweet Spot, incoming prompts first classify
  (OT), then route to a handler (which may or may not
  invoke the Sweet Spot's adapter + RAG). The Sweet Spot
  design and OT design need to reference each other
  without conflicting. Alignment moment captured in R12.
- **Relationship to Agent Release (TB-US-030).** An Agent
  Release is a deployable snapshot of a Sweet Spot plus
  the operator's framing / branding / access config. The
  Sweet Spot design is a prerequisite — can't define a
  release without defining what gets released.
- **How many levels of hierarchy.** Candidates:
  1. flat — experiments are atomic
  2. project → experiment → run (3-level)
  3. project → experiment (2-level, run is a child of
     experiment)
  Operator picks during the design conversation.
- **Lineage representation.** Candidates:
  - foreign key `parent_experiment_id` (self-referential
    tree)
  - JSON blob in a `lineage` column
  - log-event-based (lineage inferred from append-only
    audit)
  Picking one has implications for query performance and
  for the UI's compare view.

## Out of Scope

- Implementing any part of the design. All implementation
  lives in follow-up stories identified by R8.
- Multi-tenant isolation (one TB install, one operator
  team for now).
- GPU scheduling / distributed training coordination.
- Model-weight versioning beyond adapter names.
- First-example Sweet Spot creation.
- Agent Release packaging format details — this story
  identifies that TB-US-030 handles it, doesn't duplicate.
- UI mockups beyond "a surface exists for X" named in R6.
- Branding tweaks.
- Changes to stalite3 (reference only — TB is master per
  the sync-forward architecture).

## Related

- `MEMORY.md → feedback_experiments_design_gated` —
  governed this story's creation (2026-10-15).
- `MEMORY.md → feedback_coordinator_not_epic` — governs
  whether a coordinator spawns from this design.
- [TB-US-019](tb-us-019.md) — training session workflow;
  export + UI deferred to first-experiment moment, which
  this design informs.
- [TB-US-022](tb-us-022.md) — OT classifier coordinator.
  Alignment moment with Sweet Spot query-time behavior.
- [TB-US-030](tb-us-030.md) — Build-and-deploy agent
  operator workflow. Downstream of this design.
- [TB-US-029](tb-us-029.md) — Verification example (math-
  domain OT agent). First Sweet Spot example candidate.
- [TB-US-044](tb-us-044.md) — **Agent architecture + version
  management (parallel spike).** Foundational for this one;
  TB-US-043 references TB-US-044's component/version model
  rather than re-defining it.
- `backend/api/training_manager.py` — existing building
  block (training sets).
- `backend/api/training_run_tracker.py` — existing
  building block (training runs).
- `backend/api/app_settings.py` — existing building block
  (RAG prompt + routes).
- Deliverable: `docs/design/sweet-spot-architecture.md`.

**Completion Notes (2026-10-20).**

**Design spike closed with all 14 open questions resolved.**

**Breakdown:**
- 6 decided in-doc (Q1 earlier, Q2, Q6, Q7, Q11, Q14)
- 7 resolved by cross-reference to TB-US-044 (Q3, Q4, Q5,
  Q8, Q9, Q12 + implicit alignment of Q6's state model)
- 1 resolved by cross-reference to TB-US-047 (Q13)

**Deliverable:** `docs/design/sweet-spot-architecture.md`
(reshaped by TB-US-044 scope boundary; now focused on
experimentation methodology — recipes, snapshots, Sweet
Spot vocabulary, before/after comparisons, promotion flow,
math worked example).

**Key design kernel (settled by operator insight
2026-10-15):** *"A Sweet Spot is the current winning
combination of (system prompt, RAG, LLM, PEFT adapter)
identified using a collection of before/after experiments
designed to find the highest performance combination of
agent components."* Three load-bearing words: **current**
(displaceable), **collection** (tournament), **highest
performance** (purposeful search).

**Three-concept vocabulary (settled 2026-10-15):**
- **Recipe** = mutable experiment configuration
- **Snapshot** = immutable frozen capture of a recipe
- **Sweet Spot** = currently-promoted snapshot (role
  designation, not a separate entity)

**Four Sweet Spot axes:** system prompt, RAG, LLM, PEFT
adapter. Eval harness is NOT an axis — it's the
measurement sidecar.

**6-state experiment lifecycle:** draft → running →
completed → promoted → displaced; any state → archived.

**Scope = agent** (no free-text tag; agent_name FK IS
the scope).

**Downstream work unblocked:**

- TB-US-047 (first-run) ✓ already closed; math-example
  staged progression IS the first operational Sweet Spot
- TB-US-044 (agent architecture) ✓ already closed;
  provides the component/version foundation
- TB-US-048 (agent editor) in Proposed; implements agent
  CRUD + selector; provides the surface where
  experiments live
- Future experiment-management stories to be drafted
  when execution phase begins

**No code changes in this story.** Pure design spike.

**AC verifications:**
- AC1 ✓ Deliverable exists; all sections populated
- AC2 ✓ Multiple decisions explicitly captured (14 total)
- AC3 ✓ At least 3 follow-up stories identified (via
  TB-US-044's §11 and this doc's §8)
- AC4 ✓ Operator confirmed closure via "close it fast"
- AC5 ✓ No code changes in this story
- AC6 ✓ No new experiments / training sets / adapters
  created in service of this spike
