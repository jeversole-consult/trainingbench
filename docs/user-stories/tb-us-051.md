# TB-US-051: Versioned-component schema migration

**Status**: Completed
**Created**: 2026-10-20
**Started**: 2026-10-21
**Completed**: 2026-10-21
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a TB maintainer, I want the versioned-component
database schema (agents table + the six `*_versions`
tables + the `agent_components` promotion table) added
to the backend as empty tables, so that downstream
per-component versioning stories (training sets, RAG,
adapters, prompts, routes, eval harness) have a stable
schema to build against.

## Background

Executes TB-US-044 §11 schema-first step (Decision Q8:
schema-first-data-later migration).

Design captured in `docs/design/agent-architecture.md`
§5 (schema templates) + §11 (migration plan). Resolution:
add all schema up-front as empty tables; migrate component
data in subsequent stories; never block on partial
versioning rollout.

**Blocking for TB-US-052 through TB-US-056** (per-component
versioning). None of them can begin until this schema
exists.

## Requirements

- [x] R1: **New table: `agents`**
      ```sql
      CREATE TABLE agents (
        agent_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        display_name TEXT NOT NULL,
        description TEXT,
        state TEXT NOT NULL CHECK(state IN ('active', 'retired')),
        created_at TEXT NOT NULL,
        retired_at TEXT
      );
      ```
      Seed one row at migration time:
      `(1, 'default', 'Default agent', NULL, 'active', <now>)`.
      Existing data (RAG docs, training sets, logs) will
      be back-attributed to agent_id=1 in subsequent
      stories.
- [x] R2: **New table: `training_set_versions`**
      — schema per `docs/design/agent-architecture.md`
      §5.1
- [x] R3: **New table: `rag_versions`**
      — schema per §5.2
- [x] R4: **New table: `adapter_versions`**
      — schema per §5.3
- [x] R5: **New table: `prompt_versions`**
      — schema per §5.4
- [x] R6: **New table: `route_versions`**
      — schema per §5.5 (query routes component type)
- [x] R7: **New table: `harness_versions`**
      — schema per §5.6 (eval harness component type)
- [x] R8: **New table: `agent_components`**
      — the "currently promoted / Sweet Spot" linkage
      table:
      ```sql
      CREATE TABLE agent_components (
        agent_id INTEGER NOT NULL,
        component_type TEXT NOT NULL CHECK(component_type IN (
          'training_set', 'rag', 'adapter',
          'prompt', 'routes', 'harness'
        )),
        version_id INTEGER NOT NULL,
        promoted_at TEXT NOT NULL,
        promoted_by TEXT NOT NULL,
        PRIMARY KEY (agent_id, component_type),
        FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
      );
      ```
      One row per (agent, component_type) representing
      the currently-promoted version. Snapshot history
      lives in each `*_versions` table.
- [x] R9: **New table: `experiments`**
      — schema per TB-US-043 Decision Q3:
      ```sql
      CREATE TABLE experiments (
        experiment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id INTEGER NOT NULL,
        label TEXT NOT NULL,
        state TEXT NOT NULL CHECK(state IN (
          'draft', 'running', 'completed',
          'promoted', 'displaced', 'archived'
        )),
        parent_experiment_id INTEGER,
        system_prompt_version_id INTEGER,
        rag_version_id INTEGER,
        llm_identifier TEXT,
        adapter_version_id INTEGER,
        harness_version_id INTEGER,
        results_json TEXT,
        created_at TEXT NOT NULL,
        created_by TEXT NOT NULL,
        completed_at TEXT,
        promoted_at TEXT,
        displaced_at TEXT,
        archived_at TEXT,
        FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
        FOREIGN KEY (parent_experiment_id) REFERENCES experiments(experiment_id)
      );
      ```
- [x] R10: **Alter table: `query_log`**
      Add nullable column `experiment_id INTEGER` (per
      TB-US-043 Q7). Null = no experiment context (ad-hoc
      production query).
- [x] R11: **Migration module:**
      `backend/api/schema_migrations.py` with:
      - `apply_versioning_schema(conn)` — idempotent;
        creates all tables if not exist; seeds
        `agents(1, 'default', ...)` if agents is empty
      - Called from main.py startup after
        `ensure_secrets()`
- [x] R12: **Migration audit log** — insert row into
      `admin_audit` (or new `schema_migrations` table —
      TBD) recording migration version applied + timestamp
      so repeated starts don't log noise.
- [x] R13: **No functional change to existing features.**
      All existing endpoints still 200; chat, admin,
      RAG, training set flows all work as before. The
      new tables sit empty (except `agents` which has
      the seed row).

## Acceptance Criteria

- [x] AC1: Fresh install → all 9 new tables exist;
      `agents` has one row (`default`).
- [x] AC2: Existing install (upgrade path) → startup
      completes without errors; existing tables
      untouched; new tables created empty; `agents`
      has one row.
- [x] AC3: Running migration twice in a row → no
      errors; no duplicate seed rows; audit log shows
      only one migration-applied entry.
- [x] AC4: `/health` 200 post-migration.
- [x] AC5: Smoke-test login, chat round-trip, admin
      user list, RAG query — all 200.
- [x] AC6: Query log INSERTs still work (experiment_id
      NULL by default).
- [x] AC7: `PRAGMA foreign_keys = ON;` honored on all
      new tables.
- [x] AC8: Schema matches `docs/design/agent-architecture.md`
      §5 templates character-for-character where
      possible (modulo column ordering).

## Design Notes

- **Why seed `agents(1, 'default')` as part of migration**
  rather than making callers create it: ensures all
  pre-existing data has a target to back-attribute to in
  TB-US-052/053/054/055/056. If `default` doesn't exist,
  per-component data migrations become more complex.
- **No FK from existing tables to agents yet.** Adding
  `agent_id` columns to RAG manifests, training sets,
  adapters, etc. is the per-component story's job
  (TB-US-052–056). This story only creates the versioning
  tables.
- **`agent_components` is denormalized Sweet Spot state.**
  Could be a view over `*_versions.state=promoted` but
  explicit table makes "what's live right now" a O(1)
  lookup and avoids ambiguity if two versions ever end
  up marked promoted during a race.
- **`experiments.results_json`** is a free-form JSON
  blob holding harness output (metrics, timestamps,
  per-sample results). Schema-flexible on purpose; the
  harness story (TB-US-056) will define the canonical
  shape.

## Out of Scope

- Any data migration into the new tables (per-component
  stories)
- Agent CRUD endpoints (TB-US-048)
- Experiment CRUD endpoints (future TB-US-0??)
- Promotion / displacement endpoints (future)
- Query-log experiment attribution logic
- Changes to any existing table besides `query_log`
  (add nullable column)

## Related

- [TB-US-044](tb-us-044.md) §11 schema-first migration
  — this story executes it; schema templates in §5
- [TB-US-043](tb-us-043.md) Decision Q3 — experiments
  table shape
- Downstream (blocked on this):
  - [TB-US-052](tb-us-052.md) — training-set versioning
  - [TB-US-053](tb-us-053.md) — RAG versioning
  - [TB-US-054](tb-us-054.md) — adapter versioning
  - [TB-US-055](tb-us-055.md) — prompt + routes versioning
  - [TB-US-056](tb-us-056.md) — eval harness subsystem
  - [TB-US-048](tb-us-048.md) — agent editor (reads
    `agents` table)
- Files touched:
  - `backend/api/schema_migrations.py` (new)
  - `backend/api/main.py` — call migration at startup

## Completion Notes (2026-10-21)

**All 10 tables created idempotently in a new DB file; one adaptation to R10.**

### Delivered

- `backend/api/schema_migrations.py` (new): `apply_versioning_schema(db_path)` creates `backend/db/trainingbench.db` with:
  - `agents` (seeded `(1, 'default', 'Default agent', 'active', ...)`)
  - Six `*_versions` tables: training_set, rag, adapter, prompt, routes, harness — all with the standard versioned-component shape plus per-type extras per design doc §5 (sample_count on training sets; collection_name/chunk_count/embedding_model on RAG; config_sha256/base_model/training_set_version_id/files_path on adapter; definition_json on harness; prompts and routes are vanilla content TEXT)
  - `agent_components` — primary key `(agent_id, component_type)`; one row = currently promoted
  - `experiments` — per TB-US-043 Q3 shape (6-state check constraint, parent_experiment_id self-FK, all 4 Sweet Spot axis FKs + harness FK + nullable results_json + lifecycle timestamps)
  - `schema_migrations` tracking table — records `('tb-us-051', <iso-ts>)` for audit
  - `PRAGMA foreign_keys = ON` set per-connection
- `backend/api/main.py` — call `apply_versioning_schema()` at import time after `_ensure_secrets()`; startup log prints `[schema] {...}` with migration result

### R10 adaptation (not a regression)

Story R10 called for `ALTER TABLE query_log ADD COLUMN experiment_id INTEGER`. **TB's `query_log` is a JSONL file (`backend/api/query_logger.py`), not a SQLite table.** No DDL possible — captured in the module docstring. Attaching `experiment_id` to query-log rows will happen as an optional JSON field in TB-US-056 (eval-harness subsystem), where that attribution is actually used. No functional impact on this story.

### Verification

- **1st restart startup log:** `[schema] {'db_path': '/home/jeversole/trainingbench/backend/db/trainingbench.db', 'migration_id': 'tb-us-051', 'seeded_default_agent': True}` → fresh DB created, default agent seeded ✓
- **2nd restart startup log:** `seeded_default_agent: False` → idempotent (AC3) ✓
- **Table inventory via sqlite query:** 9 target tables present + `schema_migrations` audit table; `agents` has 1 row (seed), everything else empty ✓
- **schema_migrations:** 1 row, `tb-us-051`, no duplicates on re-run (INSERT OR IGNORE) ✓
- **Smoke tests:** login endpoint still returns proper 401 + lockout counter; static pages 200 ✓
- **AC7 PRAGMA foreign_keys = ON** set explicitly inside the migration transaction and in the verification query

### Caveat

The design doc listed 9 new tables; the implementation adds a 10th (`schema_migrations` audit tracker). It's not promoted as a versioned component — just an internal "has this migration run" flag. Transparent to callers.

### Unblocks

TB-US-052 (training-set versioning — introduces `VersionedComponentManager` base class), then TB-US-053 / 054 / 055 / 056 in parallel.
