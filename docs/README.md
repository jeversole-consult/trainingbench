# TrainingBench Documentation

Welcome. This is TB's internal documentation surface — design
docs, user stories, operational workflows, release reviews, and
the math-example demo companion — all in one navigable place.

## What's here

### Design docs — `docs/design/`

The architectural thinking that governs how TB is built.
Both docs are currently in-progress collaborative drafts
with open operator decisions tracked inline.

- **[Agent Architecture](design/agent-architecture.md)** —
  the top-level `agent` entity, versioned-component pattern,
  component lifecycle. Foundational for everything else.
- **[Sweet Spot Architecture](design/sweet-spot-architecture.md)**
  — the experimentation methodology: recipes, snapshots,
  before/after comparisons, promotion flow. Builds on the
  agent architecture.

### User stories — `docs/user-stories/`

Every piece of TB work lives as a user story file
(`tb-us-NNN.md`). Stories are permanent documentation; their
status (Proposed / In Progress / Completed / Deferred /
Withdrawn) is updated in place rather than deleted. See
`BACKLOG.md` (project root) for the authoritative index.

### Operational workflows — `docs/training/`

How to actually do things with TB — build an agent, fix a bug,
cut a release.

- **[Sweet Spot Workflow](training/sweet-spot-workflow.md)** —
  generic how-to for applying the TB staged-progression
  pattern to your own agent (TB-US-057 Phase C deliverable).
- **[Maintenance Fix Workflow](training/maintenance-fix-workflow.md)**
  — the 9-phase bug-fix pattern (observe → draft → fire → fix
  → commit → push → downstream verify → close → review-doc
  update). Worked examples: TB-US-071, TB-US-074
  (TB-US-073 deliverable).
- **[Upgrade Publishing Workflow](training/upgrade-publishing-workflow.md)**
  — release-cut flow (pre-release checklist, private
  rehearsal, tagging convention, public cut). Worked example:
  TB-US-068 (TB-US-073 deliverable).

### Release reviews — `docs/release/`

Audit docs from release-cut rehearsals + a reusable UI
acceptance checklist template.

- **[v0.1.0-rc1 Rehearsal Review](release/v0.1.0-rc1-rehearsal-review.md)**
  — findings from the private release-cut rehearsal
  (TB-US-068) + the lab-machine UI acceptance sweep
  (TB-US-072)
- **[UI Acceptance Checklist Template](release/ui-acceptance-checklist-template.md)**
  — reusable 10-phase template for future releases
  (TB-US-072 deliverable)

### Math-example demo — `docs/math-example/`

Operator-facing companion docs for the shipped math-example
agent (TB-US-057's pedagogical demo).

- **[Sweet Spot Exploration](math-example/sweet-spot-exploration.md)**
  — first-pass measurements + honest-baseline analysis +
  path to performant numbers (TB-US-057 Phase C deliverable)

### Public Pages scaffold — `docs/pages/`

Jekyll Pages site content for TB's public-facing docs
(TB-US-060 deliverable). Built via
`.github/workflows/pages-build.yml`.

### Sprints — `docs/sprints/`

Historical sprint logs. TB currently operates arc-scoped
(coordinator stories like TB-US-015, TB-US-022) rather than
on sprint cadence; sprint files remain for reference.

### Operator docs — `docs/user/`

Pre-TB-reshape end-user documentation. Flagged for review
during TB-US-068 Phase A audit as potentially stale against
the current agent-centric UI; operator decision pending on
delete / review-update / move-to-legacy.

## How to navigate

- **Sidebar** (left) — all markdown files, grouped by
  folder, collapsed by default. Click a folder label to
  expand it. Filter box at the top for keyword search —
  matching groups auto-expand.
- **This landing page** — `docs/README.md`. Updates
  accumulate here over time; it's the first thing new
  operators see.
- **Current page title** shows above (breadcrumb).

See `BACKLOG.md` at the project root for the authoritative
list of what's shipped, in flight, proposed, and deferred.

## Updating this landing page

This file is `docs/README.md`. Edit it directly as the docs
grow. Changes land immediately — the docs page re-fetches
on every visit.
