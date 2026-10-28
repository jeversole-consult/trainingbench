# TrainingBench Documentation

Welcome. This is TB's internal documentation surface — design
docs, user stories, operator notes, and sync audits — all in
one navigable place.

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

### Sync audits — `docs/sync/`

Comparisons between TB master and downstream deployments
(stalite3). These docs capture feature parity work and
verification spikes.

- **[Feature Parity Audit](sync/stalite3-tb-parity-audit.md)**
  — the 2026-10-14 audit that drove the sync-forward arc
- **[query_logger Parity Verification](sync/query-logger-parity-verification.md)**
  — the TB-US-036 spike that confirmed byte-level
  equivalence

### Sprints — `docs/sprints/`

Historical sprint logs. TB currently operates arc-scoped
(coordinator stories like TB-US-015, TB-US-022) rather than
on sprint cadence; sprint files remain for reference.

### Operator docs — `docs/user/`

End-user-facing documentation for operating TB.

### OpenClaw skills — `openclaw/skills/trainingbench/`

Claude Code skill definitions for operating TB from the CLI.

### OT context — `docs/ot-context-for-claude-code_1.md`

The Orthogonal Training architectural brief that governs
the OT classifier arc (TB-US-022 through TB-US-030).

## How to navigate

- **Sidebar** (left) — all markdown files, grouped by
  folder, collapsed by default. Click a folder label to
  expand it. Filter box at the top for keyword search —
  matching groups auto-expand.
- **This landing page** — `docs/README.md`. Updates
  accumulate here over time; it's the first thing new
  operators see.
- **Current page title** shows above (breadcrumb).

## Current state (as of 2026-10-16)

- **Latest shipped:** TB UI redesign (left-nav + white
  theme); user management v2; sync-forward feature parity
  with stalite3; dependency prune
- **In design:** Agent architecture + Sweet Spot
  methodology (both collaborative-draft)
- **In flight (OT arc):** Four-category prompt classifier,
  audit log, 4 handlers, verification example
- **Deferred:** First-example Sweet Spot build (pending
  the agent-architecture spike)

See `BACKLOG.md` at the project root for the full list.

## Updating this landing page

This file is `docs/README.md`. Edit it directly as the docs
grow. Changes land immediately — the docs page re-fetches
on every visit.
