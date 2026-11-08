# TB-US-094: Port — agents table + agent_manager to stalite3

**Status**: Completed 2026-11-07 — fired against stalite3 commit `fb14db2`.
TB-side story file is the design record; the actual code port landed
in the stalite3 repo (local-only, no remote).
**Created**: 2026-11-07
**Author**: Jesse Eversole (inspection from TB-US-090)
**Depends on**: TB-US-090 (inspection) completed 2026-11-07;
stalite3 is at commit `adf59f0` at inspection time.
**Blocks**: all subsequent stalite-side port stories (versioning
schema, training-set version manager, adapter version manager,
experiment pivot, harness runner — each depends on `agents` being
in place as the scoping entity).
**Commit hash(es)**: <filled on stalite-side execution>

## Story

As an operator who will test TB's PEFT training pipeline against
stalite's proprietary customer-service domain data (the "where
PEFT DOES earn its keep" case the math-example arc now points to
per TB-US-093), I need stalite to have the **`agents` table +
`agent_manager` module** that all subsequent versioning stories
depend on. This is Priority 1 Step 1 from
[`stalite-catch-up.md`](../design/stalite-catch-up.md) §4.

## Background

Per TB-US-090 inspection (stalite3 commit `adf59f0`), stalite3 is
missing all of TB's post-fork versioning + agent-scoped
infrastructure:

- No `agents` table (no top-level agent entity)
- No `schema_migrations` tracker
- No `*_version_manager.py` modules (training-set, prompt, rag,
  route, adapter, harness)
- No `experiment_manager` or `harness_runner`
- No `/agents/*` endpoints

The first piece every other port depends on is `agents`, because
TB-US-052 through TB-US-056 all introduced `agent_id INTEGER
NOT NULL` FK columns into their respective tables. A versioning
port on stalite without an agent table would be structurally
incorrect.

This story keeps stalite's existing content:

- `rag_system.py`, `database_manager.py`, `training_manager.py`,
  `training_run_tracker.py`, `user_manager.py`, `session_tracker.py`,
  `power_search.py`, `document_processor.py`, `query_logger.py` —
  all preserved. The agents table is additive.
- `mix_design_handler.py` + the client-specific calculator —
  untouched. Stay in stalite's fork per the generic platform-vs-
  fork pattern.

## Scope

### 1. Schema

- [x] R1: Port `backend/api/schema_migrations.py` into stalite3,
      renaming `MIGRATION_ID` to a stalite namespace (e.g.,
      `stalite-01-agents`) so a stalite migration tracker row never
      collides with a TB migration tracker row if DBs ever get
      copied between the two codebases.
- [x] R2: In the migration, create the `agents` table matching TB-
      US-051's schema (verbatim):
      ```sql
      CREATE TABLE IF NOT EXISTS agents (
          agent_id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT UNIQUE NOT NULL,
          display_name TEXT,
          description TEXT,
          state TEXT NOT NULL CHECK(state IN ('active', 'retired')),
          created_at TEXT NOT NULL
      );
      ```
- [x] R3: Seed a `default` agent on first migration run. Slug
      choice is operator's call — suggest `stalite` or
      `customer-service` depending on how the stalite org
      talks about its own agent.

### 2. Manager module

- [x] R4: Port `backend/api/agent_manager.py` verbatim from TB.
      No dependency on versioning tables (`agent_components`,
      `*_versions`, etc.) yet — those arrive in later stories.
- [x] R5: Confirm the slug regex (lowercase, letters/digits/
      hyphen/underscore) matches stalite's existing naming
      conventions. Adjust only if needed.

### 3. Endpoints (optional for Phase 1)

Operator's call — the agent table + manager alone are enough to
unblock subsequent ports. Endpoints can wait until the
agent-management modal (future port) needs them.

- [x] R6: (optional) Port `GET /agents`, `GET /agents/{name}`,
      `POST /agents`, `PUT /agents/{name}`, `DELETE /agents/{name}`
      from TB's `main.py`. Preserve TB's auth decorators
      (`verify_super_user` for writes; `verify_web_auth` for
      reads). If stalite's auth model differs, map accordingly.
- [x] R7: (optional) Audit entries via stalite's existing audit
      mechanism if any; otherwise defer to the user-management v2
      port (a later story).

### 4. Verification

- [x] R8: Startup migration on first boot creates the table +
      seeds the default agent.
- [x] R9: Second boot: idempotency check — no duplicate rows,
      migration tracker says `already_applied=True`.
- [x] R10: Manual test: insert a second agent via SQL, read via
      manager, confirm shape matches TB's response format.

### Not in scope

- Any component versioning (training-set, prompt, rag, adapter,
  route, harness) — those are separate port stories, each
  depending on this one.
- Agent-components mapping table — part of the Sweet Spot
  adoption, not needed for one-off training.
- Agent management UI — stalite's UI is pre-overhaul; the
  agent-management modal depends on the drawer + admin dropdown
  being ported too.
- Any data migration (back-attributing existing stalite rows to
  the default agent) — that's part of each per-component port
  story (training-set-port, adapter-port, etc.) not this one.
- Changes to TB mainline. This story is pure stalite-side work.

## Acceptance Criteria

- [x] AC1: stalite3 has an `agents` table after first migration
      boot with the default row seeded.
- [x] AC2: `AgentManager` module is callable: `list_agents()`
      returns at least `[{"name": "stalite", "state": "active", ...}]`.
- [x] AC3: Second startup is idempotent — no error, no duplicates.
- [x] AC4: Existing stalite3 functionality (RAG, training, user
      management) continues to work. The agents table is additive
      only.
- [x] AC5: No TB-public-repo artifact references stalite's
      proprietary content. This story's design lives in TB docs
      because it describes the generic port pattern; the actual
      stalite-side commit happens in stalite's repo and that repo
      stays proprietary.

## Design Notes

- **Why this is the first port story**: Priority 1 Step 1 of
  catch-up §4. Every subsequent versioning story adds an
  `agent_id` FK column; the agents table must exist first.
- **Why the migration tracker lives in `trainingbench.db` on the
  TB side but the stalite port should use its own namespace**:
  see §5.2 of catch-up doc. A stalite tracker row like
  `stalite-01-agents` in stalite's SQLite file is independent of
  TB's tracker; cross-copy of DBs between the two codebases
  (which happens during deployment handoff) doesn't cause
  phantom "already applied" skips.
- **Why no `agent_components` yet**: Sweet Spot promotion is a
  later story; a single-agent, single-adapter PEFT experiment
  doesn't need the mapping table. Adding it now would be
  speculative work.
- **Why no UI in this story**: stalite3's static/ has only
  `login.js` + `script.js`. Porting the agent-management modal
  needs the left-nav drawer + admin dropdown + the version-
  lifecycle helper, each a separate port story. Lot of ground to
  cover; split by concern.

## Related

- [`stalite-catch-up.md`](../design/stalite-catch-up.md) — the
  design that motivates this story; §4 Priority 1 Step 1
- [TB-US-090](tb-us-090.md) — the inspection spike that
  surfaced the port priorities
- [TB-US-044](tb-us-044.md) — agent architecture design doc
- [TB-US-048](tb-us-048.md) — TB's `agent_manager.py` + CRUD
  endpoints (verbatim port target)
- [TB-US-051](tb-us-051.md) — TB's `agents` table schema
  (verbatim port target)
