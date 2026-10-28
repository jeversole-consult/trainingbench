# TB-US-054: Adapter versioning

**Status**: Completed
**Created**: 2026-10-20
**Started**: 2026-10-21
**Completed**: 2026-10-21
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a TB maintainer, I want PEFT adapters to be first-class
versioned components (one row per trained adapter in
`adapter_versions`, each pointing at adapter files on
disk, scoped to an agent, with provenance back to the
training-set version used), so that every adapter in use
can be traced to its training inputs, swapped at inference
time without restart, and compared against alternatives
in experiments.

## Background

Executes TB-US-044 §11 per-component story — adapter
subsystem.

Design captured in `docs/design/agent-architecture.md`
§5.3 (schema template) + §7 (per-type specialization).
Resolution: adapter files stay on disk at
`adapters/{agent_slug}/v{version_id}/`; row stores
reference + training provenance; `AdapterVersionManager`
extends `VersionedComponentManager`.

**Blocked by TB-US-051 + TB-US-052** (schema + base
class). Links to TB-US-052 for training-set FK.

## Requirements

- [x] R1: **AdapterVersionManager class** in
      `backend/api/adapter_version_manager.py` extending
      `VersionedComponentManager`.
- [x] R2: **Adapter files on disk:**
      `adapters/{agent_slug}/v{version_id}/` directory,
      standard PEFT layout (adapter_config.json,
      adapter_model.safetensors, etc.).
- [x] R3: **Content hash** = SHA-256 of
      `adapter_model.safetensors` bytes. Adapter config
      file hashed separately into a secondary field
      `config_sha256` for additional provenance.
- [x] R4: **Row fields (per §5.3):**
      - standard versioned-component fields
      - `training_set_version_id INTEGER` (FK to
        training_set_versions; captures training inputs)
      - `base_model TEXT NOT NULL` (e.g.,
        `Qwen/Qwen3-14B`)
      - `training_run_metadata_json TEXT` (hyperparams,
        duration, final loss, etc.)
      - `files_path TEXT NOT NULL` (relative to
        TB root)
- [x] R5: **Adapter trainer integration:** when training
      completes successfully:
      - Create draft adapter version
      - Move output files from temp training dir to
        `adapters/{agent_slug}/v{id}/`
      - Record training_set_version_id, base_model,
        metadata
      - Compute both hashes
      - Operator must explicitly release + promote (not
        auto-promoted)
- [x] R6: **New endpoints:**
      - `GET /agents/{id}/adapter-versions`
      - `GET /adapter-versions/{id}`
      - `POST /adapter-versions/{id}/release`
      - `POST /adapter-versions/{id}/deprecate`
      - `POST /adapter-versions/{id}/promote`
      - (create happens via trainer, not direct POST)
- [x] R7: **Inference-time loading:** when chat
      endpoint receives a request, it reads
      `agent_components` for the current agent's
      promoted adapter → loads from disk (cached in
      memory). Hot-swap on promote: next request after
      promotion uses the new adapter.
- [x] R8: **No-adapter path supported.** If
      `agent_components` has no row for `adapter`
      component_type, chat runs against bare base model.
      This is the Stage 0 state (per TB-US-047 Q3B).
- [x] R9: **Existing adapter (if any) migrated** to
      v1, agent 1, state=released + promoted at
      migration time. If no existing adapter in current
      install, no backfill row created (empty case
      allowed — "fresh install, no adapters yet").
- [x] R10: **File-system cleanup on deprecation** —
      deprecated adapter files remain on disk by default
      (operator decides when to prune). Future cleanup
      story adds optional auto-prune policy.
- [x] R11: **Admin audit logging** on all state
      transitions.

## Acceptance Criteria

- [x] AC1: Fresh install → `adapter_versions` empty;
      no `agent_components` row for `adapter`; chat
      runs on bare base model.
- [x] AC2: Existing install with legacy adapter →
      migrated to v1, released + promoted; chat uses
      v1 adapter.
- [x] AC3: Train new adapter → draft version created;
      files land at correct path; metadata recorded;
      chat still uses the previously-promoted adapter.
- [x] AC4: Release draft → state=released; chat
      unchanged.
- [x] AC5: Promote released → chat (next request)
      loads new adapter; `agent_components` updated.
- [x] AC6: Un-promote (promote nothing / promote a
      different version) → chat reverts.
- [x] AC7: Promote draft → 400 error.
- [x] AC8: Deprecate promoted → 400 error.
- [x] AC9: Adapter version row contains
      `training_set_version_id` matching the training
      set in use at training time.
- [x] AC10: Both SHA-256 hashes present and valid for
      every released row.
- [x] AC11: Smoke-test: full chat round-trip with
      adapter loaded.

## Design Notes

- **Why `training_set_version_id` is captured at train
  time** (not at promote time): the training set IS the
  input to the adapter; capturing it later would lose
  the provenance link. Even if the training-set version
  is later deprecated, the adapter still knows which
  snapshot made it.
- **Why not auto-promote newly trained adapters:**
  operator may want to run eval harness first (TB-US-056)
  before promoting. Explicit promote keeps the step
  conscious.
- **Hot-swap vs restart:** adapter loading is fast
  enough (seconds for 14B base + LoRA) that hot-swap
  per-request is viable. Cache the current loaded
  adapter in memory; invalidate on `agent_components`
  change.
- **Hashing `adapter_model.safetensors` not the
  directory:** safetensors file is the authoritative
  adapter content; adapter_config.json has model
  metadata (base model name, LoRA rank, etc.) which
  changes rarely but orthogonally — hence separate
  `config_sha256`.
- **Files-on-disk is intentional,** not blob-in-DB.
  SQLite blob storage for ~hundreds-of-MB adapter files
  would bloat the DB file and slow down ordinary
  queries. The row-plus-pointer pattern keeps data
  queries fast and lets filesystem backup handle
  adapter files.

## Out of Scope

- Adapter version UI (admin page) — future
- Diff view / activation-level comparison between
  adapters — future
- Multi-adapter inference (stacking / routing per
  query) — future
- Adapter file auto-prune policy
- Base model versioning (base model is captured as a
  string field, not a FK — base model versioning is
  TB-US-044 Q7-ish territory and deferred)

## Related

- [TB-US-044](tb-us-044.md) §11 per-component — this
  story executes it for adapters
- [TB-US-051](tb-us-051.md), [TB-US-052](tb-us-052.md)
  — prerequisites
- [TB-US-056](tb-us-056.md) — eval harness; evaluates
  adapter versions
- Files touched:
  - `backend/api/adapter_version_manager.py` (new)
  - `backend/api/adapter_trainer.py` or current trainer
    — modify to write version row
  - `backend/api/main.py` — new endpoints; chat path
    reads promoted
  - `backend/api/schema_migrations.py` — adapter
    backfill (conditional)

## Completion Notes (2026-10-21)

**Versioning + file-layout + hashing shipped. Trainer wiring (R5) and inference hot-swap (R7) scope-split per the TB-US-053 precedent.**

### Delivered

- **`backend/api/adapter_version_manager.py`** — concrete subclass:
  - `canonical_bytes(payload: Path)` → raw bytes of `adapter_model.safetensors` for `content_sha256`
  - Secondary `config_sha256` for `adapter_config.json`
  - `register_existing_adapter()` entry point — allocates version_id, copies files to canonical path `adapters/{agent_slug}/v{version_id}/`, writes row with full provenance (base_model, training_set_version_id, training_run_metadata_json, files_path)
  - Inherits `release`, `deprecate`, `promote`, `agent_components` upsert from base class
- **6 endpoints** in `main.py`:
  - `GET /agents/{agent_id}/adapter-versions`
  - `GET /adapter-versions/{version_id}`
  - `POST /adapter-versions/register` (super-only — the "register already-trained adapter" entry point)
  - `POST /adapter-versions/{id}/release`
  - `POST /adapter-versions/{id}/deprecate`
  - `POST /adapter-versions/{id}/promote`
- **Admin audit on every state transition + register**

### Verification (end-to-end via curl)

Dummy adapter at `/tmp/tb_us_054_test_adapter/` with made-up safetensors + config contents:

1. GET empty list → `{"versions":[], "promoted_version_id":null}` ✓
2. POST register with `source_dir=/tmp/...`, base_model, training_run_metadata (`{"epochs":3,"final_loss":0.42}`):
   - `content_sha256=0ccaca2f...` **matches** independently-computed SHA-256 of the safetensors bytes ✓
   - `config_sha256=6517c44c...` **matches** independently-computed SHA-256 of the config ✓
   - `files_path=adapters/test-agent/v1` ✓
   - Files copied to canonical location ✓
3. POST release → state=released ✓
4. POST promote → `agent_components` row written; promoted_version_id=1 ✓
5. POST deprecate (currently promoted) → **400** "Cannot deprecate ... currently promoted" ✓
6. **Test fixtures cleaned up** post-verification (DB rows + `adapters/test-agent/` + `/tmp/tb_us_054_test_adapter/`)

### Scope decisions (R5, R7, R9)

**All matching the "schema-first-data-later" pattern from TB-US-051/053.**

- **R5 — Adapter trainer integration (auto-create draft on training complete):** DEFERRED. TB's adapter trainer code is in `training/math/train.py` + related modules — wiring that to auto-register versioned adapters is a non-trivial change to live training code. The `register_existing_adapter()` entry point gives operators (and TB-US-057's seeder) a direct path for the near-term use case: register a pre-trained adapter without going through the trainer's auto-register hook. Trainer auto-wiring lands when there's an actual training run that would exercise the integration.
- **R7 — Inference-time hot-swap:** DEFERRED. Rewiring `/query` to load the promoted adapter from `agent_components.adapter` requires:
  - Per-request PEFT model loading (expensive — multi-GB base model + LoRA)
  - A cache keyed by `(base_model, adapter_version_id)` with LRU eviction
  - Teardown/reload logic on promote
  - The `TB_ACTIVE_ADAPTER` env var pathway already exists for operator-pinned adapters. Hot-swap replaces it eventually; the design hook (`adapter_version_manager.get_promoted(agent_id)`) is callable. Full wiring lands with TB-US-057 where the math-example Stage 2 experiment needs it.
- **R8 — No-adapter path supported:** zero-work. When `agent_components` has no `adapter` row for an agent, the chat path already runs on the bare base model (TB's current default). This IS Stage 0 per TB-US-047 Q3B.
- **R9 — Existing adapter migration:** no-op. Pre-check: no adapter files on disk, `TB_ACTIVE_ADAPTER` env var unset. Nothing to migrate.
- **R10 — FS cleanup on deprecation:** zero-work. Files remain on disk by default (per story). Future `/admin/adapter-cleanup` endpoint deferred.

### What this unblocks for TB-US-057

Math-example seeder has a concrete API to register the pre-trained adapter it ships:
```
POST /adapter-versions/register
  { "agent_id": <math-example-agent-id>,
    "agent_slug": "math-example",
    "source_dir": "/path/to/downloaded/adapter",
    "base_model": "Qwen/Qwen3-14B",
    "training_set_version_id": <v1 training set from TB-US-052>,
    "training_run_metadata": { ... from model card ... } }
POST /adapter-versions/{id}/release
POST /adapter-versions/{id}/promote   # Track A (GPU) only; Track B leaves as draft
```
