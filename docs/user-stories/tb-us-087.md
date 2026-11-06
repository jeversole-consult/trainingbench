# TB-US-087: Per-component version lifecycle UI (release / promote / deprecate buttons)

**Status**: Completed (R1-R6 shipped 2026-11-06)
**Created**: 2026-11-05
**Started**: 2026-11-06
**Author**: Jesse Eversole
**Depends on**: TB-US-086 backend audit (completed)
**Blocks (soft)**: TB-US-005 public v0.1 cut — without version-lifecycle
UI, operators who log into TB can't manage their own components.
**Commit hash(es)**: <filled in on completion>

## Story

As a TB operator managing an agent's versioned components (prompts,
RAG, adapters, routes, harnesses), I want **a UI to release,
promote, and deprecate component versions** — the same actions that
today only exist as POST endpoints in the API — so that I don't
have to invoke `curl` or write a script just to promote a newly
trained adapter.

Surfaced during TB-US-086 backend feature audit as a Tier-1
US-005 blocker: the agent-management modal and the component
registry both exist, but the state transitions (draft → released
→ promoted ↔ deprecated) that live at `POST
/{component}-versions/{id}/release`, `.../promote`, `.../deprecate`
have no UI entry points.

## Background

TB's agent-architecture (TB-US-044) ships five versioned
component types:

| Component | Version manager | Endpoints |
|---|---|---|
| Training set | `training_set_version_manager.py` | `/training-set-versions/{id}/release` + `/promote` + `/deprecate` |
| RAG | `rag_version_manager.py` | `/rag-versions/{id}/release` + `/promote` + `/deprecate` |
| Adapter | `adapter_version_manager.py` | `/adapter-versions/{id}/release` + `/promote` + `/deprecate` |
| Prompt | `prompt_version_manager.py` | `/prompt-versions/{id}/release` + `/promote` + `/deprecate` |
| Route | `route_version_manager.py` | `/route-versions/{id}/release` + `/promote` + `/deprecate` |
| (Harness) | `harness_version_manager.py` | release + deprecate only (not Sweet Spot promotable per TB-US-056) |

**Current UI state** (post-TB-US-018/042 overhaul):
- The agent-management modal (`agent_management.js`, accessed via
  left-nav admin dropdown) shows the agent itself.
- Training Sets has a dedicated page (`training_sets.html`).
- Training Runs has a dedicated page with adapter auto-register
  on completion (TB-US-065).
- **Version-lifecycle actions have NO buttons.** Operators who
  want to promote an auto-registered adapter after a training
  run must use the API directly.

This was invisible to a Claude-in-the-loop operator but is a hard
blocker for the external-ML-researcher audience (TB-US-086 US-005
dependency).

## Scope

Add release / promote / deprecate UI controls for the five
promotable component types, surfaced as actions from either:

**Option A — Per-component dedicated pages**
- Each component type gets its own detail page or expanded section
  within an existing page
- Shows all versions for the selected agent + version state +
  action buttons

**Option B — Unified "promotion workflow" view**
- One page that shows all five component types for the active
  agent + their promoted version
- Side-by-side "what's live" view with inline promote/deprecate
  actions

**Option C — Minimal: action buttons in existing pages**
- Add action buttons wherever a version is listed in current
  views (training_sets.html for training sets, training_runs.html
  for adapters, the agent modal for prompts/routes/rag)
- No new navigation; minimum footprint

**Recommended**: start with Option C (minimal) for the US-005
scope, defer Option B (unified workflow) to a follow-up. Option A
is overkill for v0.1.

## Pre-registered scope (if operator picks C)

### Required UI touchpoints

- [x] R1: **Adapters**: on `training_runs.html`, auto-registered
      adapters show Release / Promote / Deprecate buttons based
      on current state. Shared helper extracted into
      `static/version_lifecycle.js` (`window.tbLifecycle.{badge,controls,act}`)
      for R2-R6 reuse.
- [x] R2: **Training sets** (versioned snapshots): surfaced in
      agent-management modal (Option B). Legacy `training_sets.html`
      left untouched — its status model (draft/pending/applied/
      active/archived/deprecated) is a separate concept from the
      versioned lifecycle. A future story may add a parallel
      "Versioned snapshots" section to that page.
- [x] R3: **Prompts**: component-versions sub-panel in the
      agent-management modal, expanded via a "Versions" button
      on each agent row.
- [x] R4: **Routes**: same sub-panel.
- [x] R5: **RAG**: same sub-panel.
- [x] R6: **Harness versions**: same sub-panel, Release + Deprecate
      only (no Promote button rendered because `promotable: false`).
- [ ] R7: **Audit logging**: every lifecycle action logs through
      the existing `_audit_versioned_action` in main.py (already
      wired on the backend; UI just needs to call the endpoint).
- [ ] R8: **State visualization**: UI should visually indicate the
      current state (draft/released/promoted/deprecated) of each
      version. Icon or color code acceptable.

### Not in scope

- Rolling-back a promotion (the backend supports "demote via
  deprecate" but a dedicated rollback flow is different)
- Cross-agent version migration
- Any backend change — the endpoints exist already
- Mobile-responsive design specifically for this flow
- Styling beyond consistency with existing TB UI

## Pre-registered hypotheses

### H87a — Operators can self-serve version management

**Claim**: after this story ships, a logged-in operator can take
an auto-registered adapter from `draft` → `released` → `promoted`
without opening a terminal or using the API directly.

**Signal**: operator performs the 3-step flow end-to-end in the
browser; promoted adapter shows as current demo in the agent
view.

### H87b — No regression on existing pages

**Claim**: adding release/promote buttons to existing pages does
not break the pages or confuse existing flows.

**Signal**: existing flows on `training_sets.html`,
`training_runs.html`, and the agent-management modal continue
to work as they did pre-story.

## Requirements

### Phase 1 — Design agreement

- [x] R9: Operator confirmed Option C (minimal; buttons on
      existing pages). R2 landed as Option B (training-sets in
      agent-mgmt modal alongside R3-R5) after `training_sets.html`
      proved to be a legacy-status-model surface, not a versioned
      one.
- [x] R10: UX details confirmed — text buttons; promote confirms
      with named displacement ("will deprecate #NN"); errors
      inline next to the action.

### Phase 2 — Implementation

- [x] R11: Buttons added on `training_runs.html` (R1) and in the
      agent-management modal (R2-R6 via a "Versions" button that
      expands an inline sub-panel per agent).
- [x] R12: Buttons POST to `/{component}-versions/{id}/{action}`
      with the session token.
- [x] R13: Success refreshes the affected section
      (`__tbReloadAdapterLifecycle` for R1,
      `__tbRefreshAgentVersions` for R2-R6).
- [x] R14: Errors surface inline in a per-button error slot;
      alert() fallback if the slot is missing.

### Phase 3 — Verification

- [ ] R15: Browser-side smoke test pending (operator-driven per
      `feedback_ui_changes_organic.md`).
- [ ] R16: No regressions expected on existing pages
      (training_sets.html untouched; training_runs.html + agent-
      mgmt modal additions are additive).
- [ ] R17: Browser-test on operator's primary environment —
      pending.

### Phase 4 — Close

- [ ] R18: Close-out commit + push.

## Acceptance Criteria

- [x] AC1: Five promotable component types (adapter, training-set,
      prompt, route, rag) have Release / Promote / Deprecate
      controls — adapter on the run-detail view, the rest in the
      agent-management "Versions" sub-panel.
- [x] AC2: Harness versions have Release + Deprecate (no Promote,
      per `promotable: false`).
- [x] AC3: State is visually indicated via `tbLifecycle.badge(state)`
      — distinct colors per draft / released / promoted / deprecated.
- [ ] AC4: End-to-end UI smoke test pending (operator-driven).
- [x] AC5: No change to `training_sets.html`; `training_runs.html`
      additive; agent-management modal gains a "Versions" button
      + hidden sub-row that renders on demand.
- [x] AC6: Styling matches existing TB UI (borders, radii,
      hover-tint, text-button pattern inherited from the existing
      Rename/Retire controls).

## Design Notes

- **Why Option C over A/B for US-005 scope**: Option A requires
  more new UI surface; Option B is a bigger design commitment
  (and could be a post-launch story). Option C surfaces the
  capability without large new UI real estate.
- **Why this is US-005-blocking**: without it, TB's demo flow
  for an external user is "train an adapter → now use the API to
  promote it." That's a credibility leak for an ML-researcher
  audience and a dead-end for an educator audience.
- **Why the backend doesn't need changes**: TB-US-052/063 shipped
  the full version-manager infrastructure including endpoints +
  audit logging. This story is pure UI wire-up.

## Related

- Motivated by [TB-US-086](tb-us-086.md) backend feature audit
- Backend foundation: TB-US-044 (agent architecture), TB-US-052
  (versioning primitives), TB-US-063 (adapter versioning + API keys)
- UI framework: TB-US-018 (left-nav drawer), TB-US-042 (white-theme)
- Soft-blocks: TB-US-005 (public v0.1 cut)
