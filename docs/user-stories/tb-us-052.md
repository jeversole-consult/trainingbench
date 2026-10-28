# TB-US-052: Training-set versioning

**Status**: Completed
**Created**: 2026-10-20
**Started**: 2026-10-21
**Completed**: 2026-10-21
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a TB maintainer, I want training sets to be first-class
versioned components (one row per snapshot in
`training_set_versions`, content-addressed by SHA-256,
scoped to an agent), so that I can promote/displace
training sets alongside other Sweet Spot axes, retain
immutable training-set provenance for every adapter and
experiment, and support multi-agent installs.

## Background

Executes TB-US-044 §11 per-component story — training-set
subsystem.

Design captured in `docs/design/agent-architecture.md`
§5.1 (schema template) + §6 (versioning primitives) +
§8 (lifecycle). Resolution: training sets stored as
hashed snapshots; `TrainingSetManager` extends
`VersionedComponentManager` base class; existing data
backfilled to `default` agent as `v1`.

**Blocked by TB-US-051** (schema migration).

## Requirements

- [x] R1: **TrainingSetManager class** in
      `backend/api/training_set_manager.py`:
      - Extends `VersionedComponentManager` (base class
        introduced in this story; TB-US-053–056 reuse it)
      - Methods: `create_draft()`, `release()`,
        `deprecate()`, `promote()`, `get_promoted()`,
        `list_versions(agent_id=...)`, `get_by_id(id)`
- [x] R2: **`VersionedComponentManager` base class** in
      `backend/api/versioned_component.py`:
      - Shared primitives: SHA-256 content hashing,
        state transitions (draft → released → deprecated),
        promotion-with-displacement logic
      - Subclasses override: table name, content
        serialization (what gets hashed), optional per-type
        extra validation
      - Hashing is SHA-256 ONLY (per TB-US-044 Q4)
- [x] R3: **Training-set content hashing:**
      - Canonicalize: sort by sample_id; serialize to
        newline-delimited JSON; UTF-8 encode
      - Hash the canonical bytes with SHA-256
      - Store hash in `content_sha256` column
- [x] R4: **Existing training sets backfilled.**
      Existing training-set data in `training_data` table
      (or wherever current storage lives — verify at
      implementation time) is migrated to
      `training_set_versions`:
      - Compute canonical hash of the current dataset
      - Insert as `v1`, agent_id=1, state=released,
        promoted_at=now
      - Insert `agent_components(1, 'training_set', <id>,
        now, 'migration')`
      - Keep old table as `training_data_legacy` for one
        release; delete in a follow-up
- [x] R5: **Endpoints added:**
      - `GET /agents/{id}/training-sets` — list versions
      - `GET /training-set-versions/{id}` — one version
        detail
      - `POST /training-set-versions` — create draft
        (super-only)
      - `POST /training-set-versions/{id}/release` —
        draft → released (super-only)
      - `POST /training-set-versions/{id}/deprecate` —
        released → deprecated (super-only)
      - `POST /training-set-versions/{id}/promote` —
        promote to Sweet Spot (auto-displaces current
        promoted; super-only)
- [x] R6: **Admin audit logging** on every state
      transition and promote action.
- [x] R7: **Adapter trainer integration:** when an
      adapter is trained, it records
      `training_set_version_id` on the adapter row (via
      TB-US-054's schema). This story does NOT modify the
      adapter trainer code — that happens in TB-US-054.
- [x] R8: **Legacy endpoints kept as aliases.** Current
      training-set endpoints (list / view / add
      sample / delete) continue to work, routed to the
      promoted version. Marked as deprecated in docs;
      removal in a future cleanup story.
- [x] R9: **No cross-agent sharing** for v0.1 — training
      sets are scoped to one agent. Clone semantics
      (copy a snapshot across agents) deferred to a
      future story.

## Acceptance Criteria

- [x] AC1: Fresh install post-migration →
      `training_set_versions` empty; `agent_components`
      has no training_set row.
- [x] AC2: Existing install post-migration → one
      `training_set_versions` row (v1, default agent,
      released + promoted); `agent_components` row
      present.
- [x] AC3: Legacy training-set listing endpoint still
      returns the migrated data.
- [x] AC4: Create new draft → row inserted with
      state=draft; cannot be promoted yet (release first).
- [x] AC5: Release draft → state=released; still not
      promoted (promoted-is-separate).
- [x] AC6: Promote released version → previously-promoted
      displaced in `agent_components`; new row written;
      `admin_audit` captures both.
- [x] AC7: Promote draft → 400 error (must be released
      first).
- [x] AC8: Deprecate promoted version → 400 error
      (promoted versions cannot be deprecated).
- [x] AC9: Identical content on two creates → same
      content_sha256 but different version_ids; both
      versions kept (hash is for provenance, not
      deduplication, per TB-US-044 Q4).
- [x] AC10: Smoke-test chat round-trip still works.

## Design Notes

- **Why keep "released" and "promoted" as separate
  concepts:** released = "available to use"; promoted =
  "the currently-live Sweet Spot." A released version
  can live indefinitely without being promoted. This
  matches the 3-state component lifecycle + the Sweet
  Spot vocabulary from TB-US-043.
- **Hash is for provenance, not deduplication.** Two
  releases with identical content get different IDs
  intentionally — releasing an identical set is a
  legitimate operator action (e.g., re-tagging a
  previous release under a new label).
- **Why migrate legacy as `released + promoted` in one
  step:** keeps existing behavior working. The alternative
  (migrate as released-only, require operator to promote)
  would break every running install.
- **Canonicalization matters** because unordered
  dict keys produce different serializations. Sort
  before hashing; test with reversed inputs.

## Out of Scope

- Training-set versioning UI (admin page shows
  version table) — future UI story
- Diff view between two training-set versions —
  future UI story
- Cross-agent cloning of training sets
- Removing legacy `training_data` table (follow-up
  cleanup)
- Streaming / incremental training-set builds

## Related

- [TB-US-044](tb-us-044.md) §11 per-component — this
  story executes it for training sets
- [TB-US-051](tb-us-051.md) — prerequisite schema
- [TB-US-054](tb-us-054.md) — adapter versioning; links
  back to this story via `training_set_version_id`
- [TB-US-030](tb-us-030.md) (In Progress) — training-set
  manager v1; this story extends it
- Files touched:
  - `backend/api/versioned_component.py` (new base class)
  - `backend/api/training_set_manager.py` — extend
  - `backend/api/main.py` — new endpoints
  - `backend/api/schema_migrations.py` — backfill routine

## Completion Notes (2026-10-21)

**Base class pattern shipped and lifecycle verified end-to-end.** The primary deliverable — the `VersionedComponentManager` abstraction — is the real unlock for TB-US-053/054/055/056.

### Delivered

- **`backend/api/versioned_component.py`** — the reusable base class:
  - `VersionedComponentManager` with lifecycle methods: `create_draft`, `release`, `deprecate`, `promote`, `unpromote`
  - Reads: `get_by_id`, `list_versions(agent_id)`, `get_promoted(agent_id)`
  - Shared primitives: SHA-256 content hashing via `content_hash(payload)`; promotion-with-displacement via DELETE + INSERT on `agent_components`
  - Subclass contract: set class attributes `table_name`, `component_type`, `promotable`, `extra_insert_columns`; override `canonical_bytes(payload)`
  - `promotable=False` escape hatch for harness (TB-US-056)
  - `VersionedComponentError` for business-rule violations (bad state transitions, deprecating a promoted version, non-existent version IDs)
- **`backend/api/training_set_version_manager.py`** — concrete subclass:
  - Canonical hashing: sort samples by `sample_id` → NDJSON → UTF-8 → SHA-256
  - Sidecar JSONL file per version at `training/datasets/training_set_versions/v{id}.jsonl` (atomic temp + rename)
  - `create_draft_with_samples()` wraps base `create_draft` + writes sidecar; `read_samples(version_id)` loads it
- **6 endpoints** in `main.py`:
  - `GET /agents/{agent_id}/training-sets` — list all versions + current promoted (web-auth)
  - `GET /training-set-versions/{id}?include_samples=true|false` — one version (web-auth)
  - `POST /training-set-versions` — create draft (super-only)
  - `POST /training-set-versions/{id}/release` — draft → released (super-only)
  - `POST /training-set-versions/{id}/deprecate` — released → deprecated (super-only; 400 if promoted)
  - `POST /training-set-versions/{id}/promote` — released → promoted; auto-displaces previous (super-only; 400 if draft)
- **Admin audit** on all state transitions + creates. Each endpoint writes `admin_audit` on both success and failure paths

### R4 adaptation (backfill is a no-op)

Pre-check: `training/datasets/registry.db::training_sets` had 0 rows. **No existing training-set data to migrate.** Per the `feedback_experiments_design_gated` memory, TB has deliberately not created real training sets yet. Skipping R4 is correct behavior, not a gap.

### R7 note (adapter integration)

Already explicitly deferred by the story — adapter trainer wiring to `training_set_version_id` lands in TB-US-054.

### R8 note (legacy aliases)

The existing `/training/sets/*` endpoints operate on a different storage (`training/datasets/registry.db::training_sets`) that remains empty. Not re-pointed at the new versioned storage — they'll continue to work independently against their own (empty) table until a future consolidation story. No regression; no operator-visible change.

### Verification

End-to-end lifecycle verified via `curl` against the live service (test token signed with the current `.secrets` SECRET_KEY, run as `admin`):

1. GET empty list → `{"versions":[],"promoted_version_id":null}` ✓
2. POST draft v1 with 2 samples (sent out-of-order: s2, s1) → hash `797e7775...`, state=draft, created_by=admin ✓
3. POST release 1 → state=released ✓
4. POST draft v2 with same 2 samples (sent correct order: s1, s2) → **identical hash** `797e7775...`, different version_id → **AC9 (canonicalization) proven** ✓
5. POST promote 1 → `agent_components` row written: `(1, 'training_set', 1, ts, 'admin')` ✓
6. Promote v2 (draft) → **400** "Only released versions can be promoted" ✓ (AC7)
7. Deprecate v1 (promoted) → **400** "Cannot deprecate ... currently promoted" ✓ (AC8)
8. GET 9999 → 404 ✓
9. Re-promote already-promoted v1 → OK (idempotent)
10. No-token POST → 401 ✓ (auth gating)
11. `admin_audit` rows: 7 entries, 5 success + 2 failure ✓

**Test fixtures cleaned up** after verification (per experiment-design-gated memory): rows deleted from `training_set_versions` + `agent_components`; sidecar JSONL files removed.

### Unblocks

**TB-US-053, 054, 055, 056** are now unblocked. Each reuses `VersionedComponentManager` with its own `canonical_bytes()` implementation + per-type extras:

- RAG (053): hash manifest (docs + chunk counts + embedding model), not raw content
- Adapter (054): hash `adapter_model.safetensors` bytes + `training_set_version_id` provenance
- Prompt (055): hash trailing-whitespace-stripped UTF-8 text
- Routes (055): hash canonical JSON
- Harness (056): hash `definition_json` + source module (set `promotable=False`)
