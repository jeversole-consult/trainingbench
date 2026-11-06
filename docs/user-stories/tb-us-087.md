# TB-US-087: Per-component version lifecycle UI (release / promote / deprecate buttons)

**Status**: In Progress (R1 shipped; R2-R6 pending)
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
      on current state. Clicking either fires the endpoint + refreshes
      state. Shared helper (`tbLifecycleAct`, `tbLifecycleBadge`,
      `tbLifecycleControls`) lives inline in `training_runs.html`;
      R3-R6 will reuse or copy it.
- [ ] R2: **Training sets**: ~~on `training_sets.html`~~ —
      **approach pending**. The existing `training_sets.html` lists
      *legacy* `/training/sets` rows (status model:
      draft/pending/applied/active/archived/deprecated), not versioned
      snapshots (`/agents/{id}/training-sets`). Two options:
      (A) add a new "Versioned snapshots" section to
      `training_sets.html` scoped to the active agent, or
      (B) surface versioned training-sets in the agent-management
      modal alongside R3-R5. Decision deferred to the R3-R6 commit.
- [ ] R3: **Prompts**: in the agent-management modal, a "Prompts"
      sub-section lists versions for the active agent with
      Release / Promote / Deprecate.
- [ ] R4: **Routes**: similar sub-section in agent-management
      modal.
- [ ] R5: **RAG**: similar sub-section.
- [ ] R6: **Harness versions**: Release + Deprecate only (not
      promotable); could live in agent-management or a settings
      sub-page.
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

- [ ] R9: Confirm Option C (minimal; add buttons to existing
      pages) is the right scope; operator may choose Option A or
      B instead.
- [ ] R10: Confirm UX details: icon vs. text buttons;
      confirmation dialog on promote (which displaces another
      promoted version) yes/no; etc.

### Phase 2 — Implementation

- [ ] R11: Add buttons to the pages identified in R1-R6.
- [ ] R12: Each button calls the corresponding endpoint with the
      session token.
- [ ] R13: Success: visual confirmation + page refresh of the
      affected version(s).
- [ ] R14: Error: toast or inline error message with the backend's
      detail string.

### Phase 3 — Verification

- [ ] R15: Smoke test each lifecycle action end-to-end via the
      UI. Confirm backend state transition.
- [ ] R16: Confirm existing pages unchanged.
- [ ] R17: Browser-test on operator's primary environment.

### Phase 4 — Close

- [ ] R18: Close-out commit + push.

## Acceptance Criteria

- [ ] AC1: All five promotable component types have release +
      promote + deprecate UI access.
- [ ] AC2: Harness versions have release + deprecate UI access.
- [ ] AC3: State is visually indicated on each listed version.
- [ ] AC4: End-to-end UI test passes for at least one component
      type (adapters as the natural choice).
- [ ] AC5: No regression on `training_sets.html`,
      `training_runs.html`, or agent-management modal.
- [ ] AC6: Consistent with TB-US-018/042 UI design language.

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
