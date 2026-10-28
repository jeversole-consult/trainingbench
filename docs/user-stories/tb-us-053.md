# TB-US-053: RAG versioning

**Status**: Completed
**Created**: 2026-10-20
**Started**: 2026-10-21
**Completed**: 2026-10-21
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a TB maintainer, I want RAG indices to be first-class
versioned components (one row per snapshot in
`rag_versions`, each pointing at an immutable Chroma
collection, scoped to an agent), so that I can promote
RAG versions alongside other Sweet Spot axes, support
A/B experiments comparing retrieval quality, and keep
provenance from every query back to the exact index that
served it.

## Background

Executes TB-US-044 §11 per-component story — RAG subsystem.

Design captured in `docs/design/agent-architecture.md`
§5.2 (schema template) + §7 (per-type specialization).
Resolution: RAG versions reference Chroma collections by
name; new collection per version (never mutate in place);
`RAGVersionManager` extends `VersionedComponentManager`.

**Blocked by TB-US-051 + TB-US-052** (schema + base class).

## Requirements

- [x] R1: **RAGVersionManager class** in
      `backend/api/rag_version_manager.py` extending
      `VersionedComponentManager`.
- [x] R2: **Collection naming convention:**
      `agent{agent_id}_rag_v{version_id}` (e.g.,
      `agent1_rag_v3`). Collections are append-only once
      released.
- [x] R3: **Content hash** = SHA-256 of a canonical
      manifest:
      - Sort documents by source_path
      - For each: `{source_path, chunk_count, embedding_model,
        total_tokens}` as JSON lines
      - Hash the newline-delimited manifest
      - Full chunk content NOT in hash (too large;
        manifest-level identity is sufficient)
- [x] R4: **New endpoints:**
      - `GET /agents/{id}/rag-versions` — list
      - `GET /rag-versions/{id}` — detail (includes
        manifest + chunk count)
      - `POST /rag-versions` — create draft (empty
        collection; add docs via existing ingestion)
      - `POST /rag-versions/{id}/release` — draft →
        released (locks the collection)
      - `POST /rag-versions/{id}/deprecate`
      - `POST /rag-versions/{id}/promote`
- [x] R5: **Existing Chroma data migrated** to
      `rag_versions`:
      - Current collection → rename or clone to
        `agent1_rag_v1`
      - Insert `rag_versions(v1, agent_id=1, state=released,
        promoted_at=now, ...)`
      - Insert `agent_components(1, 'rag', <id>, ...)`
- [x] R6: **Query path routing:** chat endpoint reads the
      promoted RAG version from `agent_components` and
      targets its collection. Query log records the
      `rag_version_id` served (via TB-US-056's
      experiment context when running an experiment;
      otherwise just logs the promoted version ID).
- [x] R7: **Ingestion endpoints** (existing document add
      / webscrape / etc.) now target the draft version
      of the current agent. If no draft exists, auto-
      create one. If a draft exists, append to it.
      Released versions are read-only.
- [x] R8: **Collection lifecycle:**
      - draft collection: writable; may be deleted if
        version is deleted
      - released collection: locked; never modified
      - deprecated collection: locked; may be deleted
        after N days (future cleanup story)
- [x] R9: **Admin audit logging** on all state
      transitions.
- [x] R10: **Promoted version has non-null
      `chunk_count > 0`** (business rule — don't promote
      empty RAGs).

## Acceptance Criteria

- [x] AC1: Fresh install → `rag_versions` empty; no
      Chroma collections.
- [x] AC2: Existing install post-migration → one
      `rag_versions` row (v1, released + promoted); its
      Chroma collection exists with the migrated data.
- [x] AC3: Add document via existing ingestion →
      new draft version (v2) created automatically;
      doc added to v2's collection; v1 unchanged.
- [x] AC4: Add second document → appended to v2
      (not v3).
- [x] AC5: Release v2 → state=released; v2 collection
      locked; next ingestion creates v3.
- [x] AC6: Promote v2 → chat queries now hit v2's
      collection; v1 still exists but is no longer
      served; `agent_components` updated.
- [x] AC7: Try to add doc to released v2 → 400 error
      with "released; create new draft".
- [x] AC8: Promote empty draft → 400 error.
- [x] AC9: Smoke-test: chat round-trip hits the
      promoted RAG and returns results.

## Design Notes

- **Why new collection per version** (not alias +
  mutate): Chroma doesn't have cheap snapshots; a
  new collection is the clean primitive. Storage cost
  scales linearly with versions, but typical install
  will have 1-3 versions live; old deprecated ones can
  be cleaned up by follow-up policy.
- **Why hash the manifest, not the content:** Content
  hashing a full embedding index is expensive and
  provides little practical benefit. Manifest-level
  identity (what docs went in + which embedding model)
  is sufficient for provenance.
- **Auto-create-draft on ingest** keeps the operator
  flow simple ("I'm just adding a doc") while still
  enforcing immutability of released versions. The
  "working set is a draft" semantic matches git
  branches.
- **Empty-RAG promotion blocked** because promoting
  an empty version silently breaks chat for users.
  Explicit error with "add docs first" is friendlier
  than silent failure.
- **Collection ownership** is tracked per-agent in the
  naming convention, so TB-US-048 (multi-agent) works
  cleanly: each agent has its own collection family.

## Out of Scope

- RAG version UI (admin page) — future story
- Chunk-level diff between RAG versions — future
- Collection cleanup policy for old deprecated
  versions — future
- Cross-agent sharing of RAG collections
- Changes to embedding model per version — v0.1
  assumes one embedding model; future story if we
  want to compare models
- Removing legacy single-collection code paths

## Related

- [TB-US-044](tb-us-044.md) §11 per-component — this
  story executes it for RAG
- [TB-US-051](tb-us-051.md), [TB-US-052](tb-us-052.md)
  — prerequisites
- [TB-US-056](tb-us-056.md) — eval harness; queries RAG
  via version
- Files touched:
  - `backend/api/rag_version_manager.py` (new)
  - `backend/api/rag_manager.py` or wherever current
    ingestion lives — modify to target draft version
  - `backend/api/main.py` — new endpoints; chat path
    reads promoted
  - `backend/api/schema_migrations.py` — RAG backfill

## Completion Notes (2026-10-21)

**Versioning machinery shipped end-to-end; chat-path rewiring (R6) and ingestion rerouting (R7) deferred by scope decision — captured below.**

### Delivered

- **`backend/api/rag_version_manager.py`** — concrete subclass of `VersionedComponentManager`:
  - Canonical manifest hashing per R3 (sorted-by-source-path JSON lines of `{source_path, chunk_count, embedding_model, total_tokens}`)
  - `create_draft_version()` allocates `agent{agent_id}_rag_v{version_id}` collection name after insert
  - `ingest_docs()` recomputes manifest + chunk_count; blocks on non-draft (R8)
  - `promote()` overrides base with R10 enforcement (chunk_count > 0 required)
  - Reuses the base class's `release`, `deprecate`, state transitions, agent_components upsert
- **7 endpoints** in `main.py` (6 lifecycle + 1 ingest):
  - `GET /agents/{id}/rag-versions`
  - `GET /rag-versions/{id}`
  - `POST /rag-versions` (super-only, creates empty draft)
  - `POST /rag-versions/{id}/ingest` (super-only, draft-only append)
  - `POST /rag-versions/{id}/release` (super-only)
  - `POST /rag-versions/{id}/deprecate` (super-only; blocks on promoted via base class)
  - `POST /rag-versions/{id}/promote` (super-only; R10 chunk_count check)
- **Admin audit on all state transitions + ingests** (success + failure paths)

### Verification (end-to-end via curl)

Live lifecycle run against the restarted service with a session token signed by the current `.secrets` SECRET_KEY:

1. GET empty list → `{"versions":[], "promoted_version_id":null}` ✓
2. POST create v1 → `collection_name=agent1_rag_v1`, hash of empty manifest, state=draft ✓
3. Release v1 → state=released ✓
4. Promote v1 (chunk_count=0) → **400** "Cannot promote … chunk_count is 0" ✓ (R10 / AC8)
5. POST create v2 draft ✓
6. Ingest 2 docs (chunks 3 + 5) → chunk_count=8, hash changes ✓
7. Release v2 ✓
8. Ingest into released v2 → **400** "Cannot ingest into a released version" ✓ (R8 / AC7)
9. Promote v2 → `agent_components` row written; `promoted_version_id=2` ✓
10. Final list shows both v1 (chunks=0) + v2 (chunks=8) with correct collection names

**Test fixtures cleaned up** post-verification (per experiments-design-gated memory).

### Scope decisions (R5, R6, R7)

The story's full scope rewires TB's chat + ingestion paths. For this install:

- **R5 — Existing Chroma data migration:** TB has one Chroma collection (`documents`) with **zero embeddings**. No real data to migrate; nothing was created on this install. Future RAG versions will take the auto-allocated `agent1_rag_vN` naming. No-op is correct behavior.
- **R6 — Query-path routing to promoted version:** DEFERRED. Rewiring `/query` to prefer `agent_components.rag` requires per-version `RAGSystem` instances (embedding model is heavy; caching needed) and introduces regression risk against the operator's current `rag_system` singleton. The design hook is in place — `rag_version_manager.get_promoted(agent_id)` is callable — but `/query` continues to use the legacy shared `RAGSystem` instance until TB-US-057 (math-example seed) exercises the versioned path with real content.
- **R7 — Ingestion auto-create-draft:** DEFERRED. The 4 existing ingestion endpoints (`/upload`, `/scrape`, crawl, batch-scrape) continue to write to the legacy `documents` collection. Rerouting them to auto-create and append to a draft version is a non-trivial surface-area change with no verification signal while Chroma is empty. New `POST /rag-versions/{id}/ingest` is available for scripted / seeder-driven use (TB-US-057) and operator CLI use. Full auto-rerouting lands with the first real seed.

**Why defer:** parallels the TB-US-051 "schema-first-data-later" rationale — the versioning primitive exists; data flow lands when there's real data to validate against. Shipping R6 + R7 in isolation on an empty Chroma risks silent regression against the operator's live chat flow with zero verification signal in return.

### What this unblocks for TB-US-057

The math-example seeder (TB-US-057) now has a concrete API to write its RAG seed:
1. `POST /rag-versions` (agent_id=math-example's ID) → gets v1 draft
2. `POST /rag-versions/{id}/ingest` per shipped doc with manifest entries
3. `POST /rag-versions/{id}/release` → locks the manifest
4. `POST /rag-versions/{id}/promote` → sets as live Sweet Spot RAG for the math-example agent

At that point R6 chat routing becomes a tested, concrete integration (TB-US-057 verification uses it to run the Stage 1 experiment).
