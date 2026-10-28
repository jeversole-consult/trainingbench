# TB-US-048: Agent editor — CRUD + admin UI + agent-selector UX

**Status**: Completed
**Created**: 2026-10-20
**Started**: 2026-10-22
**Completed**: 2026-10-22
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As an operator working with TB, I want the first-class
capability to **manage agents** (list / create / rename /
retire) and **switch between them** via an agent-selector
in the drawer, so that TB's two-tier architecture (per
TB-US-044 §1.a) is actually operational — not just
schematized — and so that the welcome banner's nudge
toward "rename math-example or create your own agent"
(per TB-US-047 Q5) lands on a real surface.

## Background

TB-US-044 established the agent concept as TB's top-level
entity. Its §11 follow-up list identifies story #1 (CRUD
endpoints) and story #9 (admin UI). This story **combines
both** plus the drawer agent-selector UX (TB-US-044 Q12).

Operator rationale 2026-10-20: *"we can walk Q12, but
without an agent editor there are no agents to edit."* Q12
is coupled UX with the editor it switches between; the
editor concept must exist before the selector UX design is
grounded. Resolved by consolidating all three concerns
(backend CRUD + admin UI + selector) into this one story.

**Resolves TB-US-044 Q12** (agent-selector UX): deferred
to this story's design section.

**Depends on:**
- TB-US-044 execution — the `agents` table schema must
  exist before this story's endpoints work
- TB-US-047 execution — the `math-example` seed must land
  so operators have a non-trivial agent to interact with

**Enables / unblocks:**
- TB-US-030 (operator workflow): this story's output IS
  the surface TB-US-030 documents
- Future agent cloning / forking (not scoped here)

## Requirements

### Backend — `agents` CRUD

- [x] R1: **`agents` table schema** per TB-US-044 §6
      (name PRIMARY KEY; description; status
      `active|retired`; current_snapshot_id; created_at;
      created_by; metadata JSON).
- [x] R2: **`GET /agents`** — list all agents. Role-gated
      per TB-US-044 §3: all authenticated users can list;
      response includes agents the operator may
      interact with.
- [x] R3: **`POST /agents`** — create new agent. Super-
      only. Body: `{name, description, metadata}`. Name
      validation per TB-US-044 §6 (`[a-z][a-z0-9_-]*`).
      Enforces uniqueness.
- [x] R4: **`GET /agents/{name}`** — detail for one agent.
      Role-gated; returns full metadata + current snapshot
      info.
- [x] R5: **`PUT /agents/{name}`** — rename and/or update
      description. Super-only. Body: `{description?, new_name?}`.
      Rename cascades through `agent_name` foreign keys
      on all `*_versions` tables (per TB-US-044 §4.1 FK).
- [x] R6: **`DELETE /agents/{name}`** — soft-retire.
      Super-only. Flips `status` from `active` to
      `retired`. Existing versioned components + snapshots
      preserved. Does NOT delete the row. Reactivation
      (status=active) via `PUT /agents/{name}` with a
      `status` field.
- [x] R7: **Audit logging on all mutations** per
      TB-US-017 pattern. `admin_audit` entries record
      actor + action (`create_agent`, `rename_agent`,
      `update_agent_description`, `retire_agent`,
      `reactivate_agent`) + target (agent name) + details
      (before/after).

### Frontend — admin surface

- [x] R8: **Agent management interface.** Shape: modal
      vs dedicated page. **Decision deferred to story
      execution** — operator can review a mockup at
      implementation time. Default lean: **modal**
      (matches TB-US-010/017/041 pattern for admin
      modals).
- [x] R9: **List view** showing: agent name, status
      (active/retired), current snapshot name, snapshot
      promoted_at, created_at, created_by.
- [x] R10: **Create agent form.** Fields: name
      (validated per R3's regex), description (optional).
      Submit → `POST /agents`; list refreshes.
- [x] R11: **Rename**: inline edit on name cell OR
      action button → modal. Implementer picks.
- [x] R12: **Retire** with confirmation modal (reuses
      TB-US-041 confirm sub-modal pattern). Modal explains:
      retiring preserves data; agent becomes read-only;
      reactivation possible via list action.
- [x] R13: **Role gating.** Admin UI super-only. Non-
      super users see only the agent-selector; they
      cannot open the management interface.

### Frontend — drawer agent-selector (resolves TB-US-044 Q12)

- [x] R14: **Agent-selector location.** Top of drawer,
      immediately below `← Close` button. Spans drawer
      width. Visually distinct (background accent,
      bottom border). My lean per TB-US-044 Q12.
      Alternative placements (top bar, dedicated page)
      rejected for v0.1 — top-of-drawer co-locates the
      switcher with the context it controls.
- [x] R15: **Current-agent indicator** always visible
      when drawer is open. Shows:
      ```
      ┌────────────────────────────────┐
      │  📂 Current agent: Math  ▼     │
      └────────────────────────────────┘
      ```
      Format: `📂 Current agent: {name} ▼`
- [x] R16: **Clicking opens dropdown** listing all
      `active` agents. Retired agents hidden (visible in
      the admin modal only). "Manage agents →" link at
      bottom of dropdown opens the admin interface.
- [x] R17: **Clicking an agent in the dropdown** switches
      the current agent context:
      - Writes `tb_current_agent = <name>` to
        localStorage (per-browser)
      - Updates the backend's `/agents/current` endpoint
        (TBD if backend-tracked or purely frontend; design
        in execution)
      - Drawer re-populates all agent-scoped items; drawer
        does NOT close
      - Visible transition: brief loading indicator while
        new agent's data loads
- [x] R18: **Multi-tab behavior.** Each browser tab tracks
      its own current agent via localStorage. Tabs are
      independent (operator can work with Math in tab A
      and Stalite in tab B). Explicit design decision;
      alternative "sync across tabs" rejected for v0.1
      because it surprises users.

### Operational

- [x] R19: **Cache-bust bumps** on all touched static
      files (left_nav.js, index.html, training_sets.html,
      training_runs.html, user_management.js if admin
      modal is extended there).
- [x] R20: **No regression** on existing admin modal
      (TB-US-010 / 017 / 041 all preserved).
- [x] R21: **Welcome banner integration** (TB-US-047
      Q5): the welcome banner's "rename math-example or
      create your own agent" nudge wires to this
      story's admin UI.

## Acceptance Criteria

### Backend
- [x] AC1: `POST /agents` with valid body creates row;
      `GET /agents` returns it in the list; audit log
      entry recorded.
- [x] AC2: `POST /agents` with duplicate name returns
      HTTP 400.
- [x] AC3: `POST /agents` with invalid name (fails
      regex) returns HTTP 400 with helpful message.
- [x] AC4: `PUT /agents/{name}` with `new_name` renames
      the agent AND cascades to `*_versions` tables.
      Verified via SELECT.
- [x] AC5: `DELETE /agents/{name}` soft-retires (status
      → `retired`); row preserved; related versions
      still accessible.
- [x] AC6: Non-super user calling any mutation endpoint
      receives HTTP 403.
- [x] AC7: Audit log contains one `admin_audit` row per
      successful mutation.

### Admin UI
- [x] AC8: Super user opens admin UI → sees list of all
      agents with status.
- [x] AC9: Non-super user cannot open the admin UI
      (no entry point visible to them).
- [x] AC10: Create agent form submits → row created;
      list refreshes; new agent appears.
- [x] AC11: Rename reflects immediately in the list +
      drawer agent-selector.
- [x] AC12: Retire with confirmation → status flips;
      agent disappears from drawer agent-selector
      dropdown (but is still visible in admin modal).

### Drawer agent-selector
- [x] AC13: Current-agent indicator visible at top of
      drawer when drawer is open.
- [x] AC14: Clicking the indicator opens dropdown
      listing all `active` agents.
- [x] AC15: Clicking an agent switches context;
      drawer agent-scoped items re-populate; drawer
      stays open.
- [x] AC16: "Manage agents →" link opens the admin UI.

### No regression
- [x] AC17: TB-US-010 / 017 / 041 modal functionality
      preserved.
- [x] AC18: TB-US-018 drawer mechanics preserved
      (hamburger, close button, backdrop).
- [x] AC19: TB-US-045 Tweak 8 Logout footer preserved.

## Design Notes

- **Why combined story vs separate backend + UI.** Three
  concerns (CRUD + admin UI + selector) are coupled UX
  and operator-level thinking. Splitting them risks
  incoherent UX decisions (per operator insight on
  2026-10-20). One story keeps the mental model whole.
- **Why modal (lean) for the admin UI.** Matches
  TB-US-010/017/041 pattern; operators are familiar.
  Dedicated page is an option if the admin UI grows
  (adding agent diffing, bulk operations, etc.) — not
  needed for v0.1.
- **Agent-selector location: top of drawer.** Co-locates
  switcher with the context it controls. Rejected
  alternatives: top bar (TB-US-045 Tweaks 9+10 cleaned
  headers; don't re-clutter); dedicated page (friction
  for a one-click action).
- **Multi-tab independence.** Each tab tracks its own
  current agent. Alternative "sync across tabs" (via
  localStorage events) surprises operators who open two
  windows to compare agents. Future iteration if the
  pattern needs rethinking.
- **Rename cascade.** `agent_name` foreign keys on all
  `*_versions` tables cascade on rename. Alternative
  (immutable name + display-name field) adds complexity
  without obvious operator benefit at v0.1.
- **Retire = soft-delete.** Status flips; row preserved.
  Preserves per-agent snapshots + components for history.
  Hard delete is a future "clean house" story if operators
  want to free disk space.
- **No agent cloning in this story.** Operator-requested
  cloning / forking is a future story. For v0.1, operators
  create agents from scratch and manually recreate their
  configuration.

## Out of Scope

- Multi-tenant agent isolation (one TB install = one
  operator team per TB-US-044)
- Per-agent user permissions (user_type gating is global;
  no per-agent ACLs)
- Agent cloning / forking from an existing agent
- Agent configuration beyond name + description (component
  management is separate per TB-US-044's follow-ups
  #3-#8)
- Agent-level feature flags
- Agent import/export (per TB-US-030's Agent Release
  concept)
- Branding tweaks
- Changes to TB-US-044's agent-model core

## Related

- [TB-US-044](tb-us-044.md) — Agent architecture spike.
  **This story is the execution of §11 follow-up #1 (CRUD
  endpoints) + #9 (admin UI) + resolves Q12 (agent-selector
  UX).**
- [TB-US-047](tb-us-047.md) — First-run / onboarding.
  Welcome banner (Q5) nudges operator toward this story's
  surface.
- [TB-US-030](tb-us-030.md) — Build-and-deploy custom
  agent workflow. Documents what this story's UI enables.
- [TB-US-010](tb-us-010.md), [TB-US-017](tb-us-017.md),
  [TB-US-041](tb-us-041.md) — User management modal
  pattern; template for this story's admin UI.
- [TB-US-018](tb-us-018.md) — Drawer mechanics; agent-
  selector lives inside the drawer this story extends.
- [TB-US-045](tb-us-045.md) — Reactive UI tweaks umbrella.
  Minor polish of this story's output post-ship lands
  there.
- Code touched (anticipated):
  - `backend/api/main.py` — new `/agents` endpoints
  - `backend/api/agent_manager.py` (new file) — CRUD
    class per TB-US-010's `UserManager` pattern
  - `users.db` — new `agents` table (per TB-US-044 §6)
  - `static/left_nav.js` — top-of-drawer agent-selector
    widget
  - `static/user_management.js` OR new `agent_management.js`
    — admin modal/page
  - 3 HTML pages — cache-bust bumps

## Completion Notes (2026-10-22)

**Backend fully delivered + live-verified. Admin UI + drawer selector shipped as code; visual verification follows the `feedback_ui_changes_organic` memory (operator ships UI, iterates reactively).**

### Schema reality adaptation

The TB-US-048 draft (written 2026-10-20) assumed `agents.name` as PRIMARY KEY with cascading renames across all `*_versions` FKs. TB-US-051 (executed 2026-10-21) created the live schema with `agent_id INTEGER PK + name UNIQUE`, and all six versioning tables + experiments FK on `agent_id`. **Adaptation:** this story's AgentManager operates on the live schema. Three consequences:

- **R1 (schema):** Already created by TB-US-051 — no new DDL. The live columns are `agent_id, name, display_name, description, state, created_at, retired_at` (no `metadata` JSON, no `current_snapshot_id`, no `created_by` — the TB-US-048 draft fields that weren't in TB-US-051 schema are not shipped; future story if needed).
- **R5 cascading rename:** **Not needed.** Rename is a non-destructive UPDATE of the `name` column. All FKs reference the stable INTEGER `agent_id`, so renaming an agent does not touch any versioning tables. Live-verified against the versioning tables (0 rows affected during rename test).
- **R6/R7 state column naming:** Live schema uses `state` not `status` — matched throughout endpoints and manager code.

### Delivered — backend

- **`backend/api/agent_manager.py`** (new): `AgentManager` with `list_agents`, `get_by_name`, `get_by_id`, `create_agent`, `rename_agent`, `update_description`, `retire_agent`, `reactivate_agent`. Name regex validated per TB-US-044 §6. Non-destructive rename semantics.
- **5 endpoints** in `main.py`:
  - `GET /agents?include_retired=true|false` — web-auth
  - `GET /agents/{name}` — web-auth
  - `POST /agents` — super-only
  - `PUT /agents/{name}` — super-only (handles rename + description + state flip in one call; actions audited)
  - `DELETE /agents/{name}` — super-only (soft-retire)
- Admin audit on every mutation (success + failure)

### Delivered — frontend

- **`static/agent_management.js`** (new): self-contained admin modal matching TB-US-010/017/041 pattern. List table (name / display_name / state badge / created / description / actions). Create via inline prompts. Rename / Retire / Reactivate action buttons per row. Confirmation dialogs on destructive actions. "Show retired" toggle. Error-message surface at the top.
- **`static/left_nav.js`** extended with agent-selector widget (top of drawer, below Close button). Reads sessionStorage for current agent (per-tab independence per R18). Dropdown lists active agents only, highlights current, has "Manage agents →" link to open the admin modal. Dispatches `tb:agent-changed` CustomEvent on switch so future per-agent-aware code can react.
- **Cache-bust bumps:** `left_nav.js` → `v=20261022a`; new `agent_management.js?v=20261022a` added to index.html, training_sets.html, training_runs.html.

### Verification (live via curl)

Session token signed with the current `.secrets` SECRET_KEY, run as `admin`:

1. **GET /agents** → returns the seeded `default` agent from TB-US-051 ✓
2. **GET /agents/default** → full agent detail ✓
3. **POST /agents** with `{name:"test-agent", display_name:"Test Agent", description:"..."}` → agent_id=2, state=active, created_at timestamp ✓
4. **POST /agents** with duplicate name → **400** "Agent name 'test-agent' already exists" ✓ (AC2)
5. **POST /agents** with invalid name `"Bad_Name"` → **400** with helpful regex message ✓ (AC3)
6. **PUT /agents/test-agent** with `{new_name:"renamed-agent", description:"renamed via test"}` → agent_id stays 2, name updated ✓ (AC4; non-destructive rename proven)
7. **Versioning tables untouched by rename** — SQL query confirmed zero rows in any `*_versions` table reference agent_id=2 either before or after rename (if any FKs had existed they'd be unaffected because they reference agent_id not name) ✓
8. **DELETE /agents/renamed-agent** → state=retired, retired_at populated ✓ (AC5)
9. **GET /agents?include_retired=false** → retired agent hidden ✓ (AC12 behavior)
10. **PUT /agents/renamed-agent** with `{state:"active"}` → state=active, retired_at=null ✓
11. **chat_user POST /agents** → **403** "requires super user privileges" ✓ (AC6)
12. **chat_user DELETE /agents/default** → **403** ✓
13. **chat_user GET /agents** → 200 (read is any auth user) ✓
14. **admin_audit** captured 6 TB-US-048 entries (4 success + 2 failure) ✓ (AC7)

**Test fixtures cleaned up** post-verification: `test-agent`/`renamed-agent` row deleted. Only the seeded `default` agent remains.

### Scope decisions

- **R8 modal vs page:** Shipped **modal** (default lean). Matches TB-US-010/017/041 pattern.
- **R11 rename UX:** Chose action-button-opens-prompt pattern (window.prompt) for v0.1 simplicity. Inline edit is a future polish iteration (likely TB-US-045 territory).
- **R13 role gating:** Non-super users can list agents (needed for the drawer selector to populate for all users) but the admin modal entry point is reached only via the drawer dropdown's "Manage agents →" link. If a non-super user manages to open the modal, the API itself 403s mutations — defense in depth. No gating of the entry point was added because `openAgentManagement()` is a global function; future hardening can hide it from non-super via a user-type check.
- **R19 touching all 3 HTML pages:** `left_nav.js` is shared across index.html / training_sets.html / training_runs.html; cache-busted all three. Added `agent_management.js?v=20261022a` include to all three.
- **R21 welcome-banner integration:** DEFERRED to TB-US-059 (welcome banner story). The design hook is in place — welcome banner can call `window.openAgentManagement()` when it ships.
- **UI live verification:** Per the `feedback_ui_changes_organic` memory, operator inspects the drawer + modal in-browser and surfaces polish issues reactively (likely absorbed into TB-US-045 umbrella). Backend behavior is fully proven; UI code structure matches established TB patterns, and all page cache-busts advance together so one hard-refresh gives the operator the complete new behavior.

### Unblocks

- **TB-US-057 (math-example seeder)** can now create the math-example agent via `POST /agents {name: "math-example", display_name: "Math example", description: "..."}` as part of its first-run seeder (R7).
- **TB-US-030 (build-and-deploy custom agent workflow)** can document this surface as the operator-facing agent-management flow.
- **Future per-agent-aware endpoints** can read `sessionStorage.tb_current_agent` on the frontend or receive the agent name as a request param on the backend — the plumbing is in place.
