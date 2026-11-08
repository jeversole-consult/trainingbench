# TB-US-102: Port — TB drawer + admin modals + endpoint wire-up to stalite3

**Status**: Completed 2026-11-08 — stalite3 commit `0471d9f`
**Depends on**: TB-US-094, TB-US-100, TB-US-101 (backend foundation)
**Blocks**: TB-US-103 (structural rewrite of index.html to drop
tab bar in favor of drawer)

## Scope — drawer installed additively

Drawer + modals installed over stalite3's existing tab-based
UI. Tab bar not touched. Backend endpoints wired so the installed
modals work end-to-end against real data.

### Static assets ported verbatim

- `static/left_nav.js` (509 L) — drawer, hamburger, agent
  selector, admin dropdown, logout. TB-US-018.
- `static/agent_management.js` (302 L) — agent CRUD modal + nested
  version-lifecycle sub-panel. TB-US-048 + TB-US-087.
- `static/api_key_management.js` (204 L) — API-key CRUD modal.
  TB-US-063.
- `static/query_routes_management.js` (306 L) — query-routes editor
  modal. TB-US-095 (which itself was reverse-ported from
  stalite3's own SL-US-010).
- `static/version_lifecycle.js` (90 L) — shared helpers for
  release/promote/deprecate buttons. TB-US-087.
- `static/version_check.js` (102 L) — auto-reload banner.
- `static/active_run_strip.js` (222 L) — sticky training-run strip.
  TB-US-066.
- `static/active_experiment_strip.js` (232 L) — sticky experiment
  strip. TB-US-070.

Total: ~2,000 LOC of UI code ported verbatim.

### Backend wire-up (`backend/api/main.py`)

- Instantiate `agent_manager` + `api_key_manager` at boot
  alongside existing managers.
- Pydantic models: `CreateAgentRequest`, `UpdateAgentRequest`,
  `CreateApiKeyRequest`.
- 5 `/agents` endpoints (list, get, post, put, delete) with
  rename/description/state semantics. Super-only for writes.
  Mirrors TB-US-048.
- 3 `/api-keys` endpoints (list, post, delete). Strip `key_hash`
  from responses. TB-US-063. Super-only.
- `/version/build` endpoint (reads git HEAD SHA at boot + process
  boot_time) so auto-reload banner has something to poll.

### Index.html wiring (additive)

All 8 new JS modules loaded via `<script>` tags before
`script.js`. Tab bar + existing structure preserved.

## Acceptance Criteria

- [x] AC1: All 8 new JS files land in stalite3/static/.
- [x] AC2: main.py syntax clean; full boot chain applies all 5
      schema migrations.
- [x] AC3: 5 new endpoints registered on the FastAPI app.
- [x] AC4: `agent_manager` + `api_key_manager` instantiated at
      module import time.
- [x] AC5: `/version/build` returns `{sha, boot_time, ts}`.

## Not in scope

- Structural rewrite of index.html to drop tab bar — TB-US-103.
- Port of `experiments.html` / `training_runs.html` /
  `training_sets.html` / `docs.html` — TB-US-104.
- CSS refresh (white-theme) — TB-US-103.
- Wire `verify_api_key` into existing stalite3 endpoints — operator
  decision per-endpoint.
