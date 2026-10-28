# TB-US-044: Spike — Agent architecture + versioned-component management

**Status**: Completed
**Created**: 2026-10-16
**Completed**: 2026-10-20
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

**Deliverable**: `docs/design/agent-architecture.md`

## Story

As the operator of TrainingBench, I want a design document
that formalizes the **agent** as TB's top-level organizing
entity and specifies how its subcomponents (RAG, training
sets, PEFT adapters, system prompts, eval harnesses, query
routes) are versioned, lifecycle-managed, and integrity-
tracked — so that TB's experimentation and promotion flows
(TB-US-043 Sweet Spot) have a solid foundation to build on
and so that reproducing or auditing any deployed agent is a
deterministic operation rather than an archaeological dig.

## Background

Operator design signal on 2026-10-15/16, after walking
through the Sweet Spot concept:

> *"i had been thinking that training bench needed the
> concept of a project just like claude code uses. now i
> think the concept of an agent may solve a lot of problems
> with managing all the components of an agent. there is a
> massive version control dimension to this product model.
> it is very similar to software version management. each
> file in an application has its own individual version and
> the combination of all those are used for a release. note
> that there is a difference between code and data. if we
> want to experiment with different RAGs we need to track
> all the RAGs and what is in them. when we PEFT train to
> produce a particular adapter we could have several
> different training set configurations."*

Followed by:

> *"need to write a spike story to iron out the agent
> approach and the version control dimension that involves
> versions of subcomponents. this will be an architecture
> for how to construct and manage a training bench agent."*

This story is the venue for that architecture.

**Why split from TB-US-043:**

TB-US-043 (Sweet Spot architecture) was already going deep
on experimentation methodology — recipes, snapshots,
promotion, before/after comparisons. The version-management
dimension is a separate (and foundational) concern. It
answers "how are agent components stored, versioned, and
tracked" — upstream of "how do we experiment and promote."
Clean phase gate: TB-US-044 ships the component-and-version
model; TB-US-043 builds the Sweet-Spot/experimentation flow
on top. Both spikes can draft in parallel but TB-US-044's
decisions should resolve first where they conflict.

## Requirements

### Deliverable

- [x] R1: **Design document at
      `docs/design/agent-architecture.md`.** Captures the
      agent + versioned-component architecture decisions
      reached by the end of this spike. Not a code
      deliverable.
- [x] R2: **Section: formal agent definition.** Answers:
      What is an agent? What does an agent own? What's the
      scope boundary between agents (what shares across
      agents vs what doesn't)? What's its lifecycle
      (created, active, retired)?
- [x] R3: **Section: component types owned by an agent.**
      Enumerates the component types (RAG, training set,
      adapter, prompt, harness, query routes) with
      rationale for each inclusion. Flags any component
      types we're deliberately NOT making agent-owned.
- [x] R4: **Section: versioned-component pattern.** The
      uniform schema template applied to every component
      type: version_tag, content_sha256, status, parent
      lineage, metadata. Component-specific columns on top
      of the template.
- [x] R5: **Section: per-component schema.** For each of
      the 5-6 component types, specifies:
      - The versioned-components row shape (template +
        specific columns)
      - Where the content lives on disk (if applicable)
      - How content is hashed for integrity
      - Current TB state (does TB already have an
        unversioned equivalent to migrate from?)
- [x] R6: **Section: component lifecycle.** The status
      model for versioned components (draft / released /
      deprecated). Transitions, implications. Can versions
      be edited? When do they become immutable?
- [x] R7: **Section: code vs data distinction.** TB
      application code is git-managed externally; TB agent
      artifacts are versioned internally. Enumerates what
      falls into each bucket. Documents the decision not to
      integrate external MLOps tooling (DVC / MLflow /
      W&B) in v0.1.
- [x] R8: **Section: content hashing + integrity.** How
      hashes get computed per component type. How
      drift-detection works (if a RAG collection is edited
      post-release, how is that caught). The audit
      traceability chain.
- [x] R9: **Section: migration from current TB state.** TB
      already has `training_sets` (table + file), `adapters`
      (via `training_run_tracker`), `database_config.json`
      for chroma collections, `AppSettings.rag_prompt` and
      `query_routes`. For each, specifies: does it migrate
      to the versioned pattern, how, with what data loss
      risk, with what reversibility.
- [x] R10: **Section: URL schema implications.** Does TB's
      REST surface shift from flat (`/training/sets`) to
      nested (`/agents/{name}/training-sets`)? Decided in
      the spike; execution left to a follow-up.
- [x] R11: **Section: follow-up stories.** Enumerates the
      downstream TB-US-NN stories this architecture
      unlocks. One-liner scope each. Flags blocking vs
      optional.
- [x] R12: **Section: open questions for operator
      decision.** Questions where operator judgment is
      needed before the architecture is executable.

### Process

- [x] R13: **Iterative, operator-collaborative drafting.**
      Same pattern as TB-US-043 — doc evolves across turns;
      operator contributes decisions and corrections.
- [x] R14: **No code changes in this spike.** Deliverable
      is the doc. If execution-oriented ideas surface,
      capture them for the follow-ups in R11.
- [x] R15: **Reference existing TB building blocks.** TB's
      current state is the migration starting point.
      Design should build on existing tables where
      possible, not reinvent.
- [x] R16: **Coordinate with TB-US-043.** Both spikes
      touch "what gets snapshotted" and "what makes an
      agent an agent." Where decisions conflict, TB-US-044
      (this spike) wins on component/version model;
      TB-US-043 wins on experimentation flow.

## Acceptance Criteria

- [x] AC1: `docs/design/agent-architecture.md` exists with
      all sections R2-R12 populated to the operator's
      satisfaction.
- [x] AC2: The versioned-component pattern is defined
      precisely enough that a follow-up story can run a
      migration script directly from it.
- [x] AC3: At least one open question has an explicit
      operator **Decision:** line captured.
- [x] AC4: At least 3 follow-up stories identified
      (R11) with one-line scopes, covering: agent schema +
      CRUD, versioned-components schema + CRUD, migration
      from current TB state. Minimum arc for first
      versioned agent.
- [x] AC5: Operator confirms "the architecture is ready to
      execute against" — i.e., the next arc can start
      without further design conversation.
- [x] AC6: No code changes in this story. `git diff
      backend/` is empty for this story's scope.
- [x] AC7: TB-US-043's design doc is updated to reference
      this one as upstream for component/version decisions
      (not duplicate them). Done by the end of this spike.

## Design Notes

- **Why "agent" over "project."** Operator-captured
  reasoning (2026-10-15/16): project is a scoping concept
  (what folder, what context); agent is an ownership
  concept (what deployed thing + what artifacts). Agents
  have real inventory — RAG corpora, training sets, trained
  adapters — in a way that Claude-Code-style projects do
  not. The agent-as-owner framing cleanly subsumes the
  project framing.
- **Why versioning is architectural, not a feature.** TB's
  value proposition is "help an operator arrive at a
  deployable agent." Deployable means reproducible means
  version-pinned. Without versioning, Sweet Spot promotion
  silently drifts: someone edits the RAG, the deployed
  agent isn't the one that was promoted. Operator analogy:
  software release engineering — individual files have
  versions; a release pins specific versions together. TB
  does this for agent components instead of source files.
- **Why not external MLOps tooling.** DVC, MLflow, Weights
  & Biases, Comet.ml all solve pieces of this. For TB
  v0.1 with a single-operator team, the overhead of
  integrating + onboarding + their failure modes isn't
  worth the win. SQLite + content hashes + on-disk
  snapshots is enough. Integrate later if TB scales to
  multi-team.
- **Code vs data boundary is sharp.** TB application code
  lives in git; TB agent artifacts live in TB's own
  internal versioning. The spike doesn't blur the two.
- **The versioned-component pattern applies uniformly.**
  Every component type gets the same schema template plus
  component-specific columns. Reduces mental overhead for
  operators (every component works the same way for
  create / list / release / deprecate).
- **Snapshots (TB-US-043) are lockfiles.** They pin exact
  component version IDs. The snapshot's recipe.yaml file
  dereferences everything for reproducibility; the
  database row carries version IDs for traceability.
- **One agent at a time.** Multi-tenant / multi-team is
  Out of Scope. One TB install, one operator team, N
  agents.

## Out of Scope

- Implementing any part of the design. All implementation
  lives in follow-up stories identified by R11.
- Changes to TB's experimentation flow — TB-US-043
  owns that.
- Agent Release packaging format — TB-US-030 owns that.
- Multi-tenant / multi-team isolation.
- GPU scheduling / distributed training coordination.
- Model-weight versioning beyond adapter names (LLM
  versioning stays Ollama's responsibility).
- First-example agent build.
- External MLOps tool integration (DVC / MLflow / W&B).
- UI mockups.
- Branding tweaks.
- Changes to stalite3.

## Related

- [TB-US-043](tb-us-043.md) — **Sweet Spot architecture
  (parallel spike).** TB-US-044 is foundational;
  TB-US-043's experimentation + promotion flow builds on
  top. Where they conflict, TB-US-044 wins on
  component/version model.
- [TB-US-022](tb-us-022.md) — OT classifier coordinator.
  Alignment moment: are OT handler configs agent-owned
  versioned components, or do they live in AppSettings?
  Resolved in TB-US-044's Q18-equivalent.
- [TB-US-030](tb-us-030.md) — Build-and-deploy agent
  workflow. Consumer of this architecture.
- [TB-US-010](tb-us-010.md), [TB-US-017](tb-us-017.md),
  [TB-US-041](tb-us-041.md) — User management modal
  pattern (reference for admin-side UI once versioned-
  component UI stories drop).
- `MEMORY.md → feedback_experiments_design_gated` —
  governed the deferral of the first experiment, which
  cascaded into this architectural need.
- `MEMORY.md → feedback_coordinator_not_epic` — governs
  whether a coordinator spawns from this architecture.
- `backend/api/training_manager.py` — current unversioned
  training_sets model to migrate from.
- `backend/api/training_run_tracker.py` — current adapter-
  tracking (via training runs) to migrate from.
- `backend/api/app_settings.py` — current unversioned
  system prompt + query routes.
- `database_config.json` — current unversioned RAG
  (chroma) collections config.
- Deliverable: `docs/design/agent-architecture.md`.

**Completion Notes (2026-10-20).**

**Design spike closed with all 13 open questions resolved.**

**Deliverable:** `docs/design/agent-architecture.md`
(~1800 lines) covering: two-tier architecture (agents at
top, admin tier separate), six versioned component types,
versioned-component schema pattern, agent entity schema,
component lifecycle, migration strategy, URL schema, and
13 decisions.

**13 decisions reached:**

- **Q1** — Agent is TB's top-level entity (per operator
  insight: "agents are at the top of the food chain
  except for administrative management like users and
  keys")
- **Q2** — Agent lifecycle: 2 states (active / retired)
- **Q3** — All 6 component types in v0.1 (RAG / training-set
  / adapter / prompt / harness / query routes)
- **Q4** — Content hashing: SHA-256 only
- **Q5** — Query routes agent-owned (not global)
- **Q6** — No cross-agent component sharing (now or
  near-term)
- **Q7** — Component lifecycle: 3 states (draft /
  released / deprecated)
- **Q10** — Versioning primitives: Python base class
  (SQL per-table; shared logic in `VersionedComponentManager`)
- **Q11** — Admin surface: top-bar avatar/account menu
  (super-only admin items; identity cue for all users)
- **Q12** — Agent-selector UX: deferred to TB-US-048
- **Q13** — Zero-agent / default-agent: resolved via
  TB-US-047 (ship math-example staged progression; zero
  allowed after operator action)
- **Q8** — Migration timing: schema-first-data-later
  (hybrid)
- **Q9** — URL schema: soft (flat routes remain as
  aliases indefinitely)

**Follow-up stories (per §11):**

Of the 9 originally enumerated, one is now drafted:

- #1 (agents CRUD) + #9 (admin UI) + Q12 selector →
  **merged into TB-US-048 (Proposed)**

Remaining 7 to be drafted when execution ordering is
chosen:

- Schema migration (Q8 step 1) — adds all `*_versions`
  tables
- Training-set versioning (Q8 step 2a)
- RAG versioning (Q8 step 2b)
- Adapter versioning (Q8 step 2c)
- Prompt + routes versioning (Q8 step 2d)
- Eval harness subsystem (Q8 step 2e)
- URL schema (nested routes added additively per Q9)

**Cross-references:**

- Q13 resolved via TB-US-047 (first-run onboarding) —
  decision log entry in both docs
- Q12 deferred to TB-US-048 (agent editor) — decision log
  entry in both docs; TB-US-048 drafted + Proposed

**AC verifications:**

- AC1 ✓ Deliverable exists with all sections R2-R12
  populated
- AC2 ✓ Versioned-component pattern defined precisely
  enough for migration script
- AC3 ✓ Multiple questions have explicit Decision lines
  (11 in-doc + 2 cross-referenced)
- AC4 ✓ Follow-up stories enumerated in §11 (9 identified;
  1 drafted — TB-US-048)
- AC5 ✓ Operator confirmed closure via "take leans on
  Q8+Q9"
- AC6 ✓ No code changes in this story
- AC7 ✓ TB-US-043 referenced; this spike resolved first
  for the component/version decisions it feeds

**Downstream work unblocked:**

- TB-US-048 (agent editor; Proposed) — ready to execute
  after schema migration lands
- 6 additional per-component versioning stories (to be
  drafted)
- TB-US-043 (Sweet Spot architecture) — can resume
  walking its open questions; TB-US-044 decisions
  underpin TB-US-043's design

**No code changes in this story.** Pure design spike.
