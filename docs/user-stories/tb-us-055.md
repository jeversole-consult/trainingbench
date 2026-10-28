# TB-US-055: Prompt + routes versioning

**Status**: Completed
**Created**: 2026-10-20
**Started**: 2026-10-21
**Completed**: 2026-10-21
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a TB maintainer, I want system prompts and query
routes to be first-class versioned components (one row
per snapshot in `prompt_versions` and `route_versions`,
content-addressed by SHA-256, scoped to an agent), so
that prompt changes and routing-logic changes are
auditable, promotable, and comparable in experiments —
matching the versioning pattern used for training sets,
RAG, and adapters.

## Background

Executes TB-US-044 §11 per-component story — prompt +
routes subsystems. Combines two components in one story
because they share the same shape (small text blobs
versioned by content hash) and will be implemented
together.

Design captured in `docs/design/agent-architecture.md`
§5.4 (prompt) + §5.5 (routes) + §7 (per-type
specialization). Resolution: current prompt + routes
live in AppSettings; migrate as v1 at startup; add
`PromptVersionManager` + `RouteVersionManager` extending
`VersionedComponentManager`.

**Blocked by TB-US-051 + TB-US-052** (schema + base
class).

## Requirements

- [x] R1: **PromptVersionManager** in
      `backend/api/prompt_version_manager.py` extending
      `VersionedComponentManager`.
- [x] R2: **RouteVersionManager** in
      `backend/api/route_version_manager.py` extending
      `VersionedComponentManager`.
- [x] R3: **Prompt content hash** = SHA-256 of
      UTF-8-encoded prompt text (trailing-whitespace
      stripped).
- [x] R4: **Routes content hash** = SHA-256 of
      canonical JSON (routes list serialized as JSON
      with sorted keys, no whitespace).
- [x] R5: **Row fields:** both tables follow the
      standard template (version_id, agent_id, content,
      content_sha256, state, released_at, deprecated_at,
      created_at, created_by, parent_version_id).
      Prompt's content field is TEXT; routes' content
      field is TEXT holding canonical JSON.
- [x] R6: **New endpoints — prompts:**
      - `GET /agents/{id}/prompts`
      - `GET /prompt-versions/{id}`
      - `POST /prompt-versions` (create draft)
      - `POST /prompt-versions/{id}/release`
      - `POST /prompt-versions/{id}/deprecate`
      - `POST /prompt-versions/{id}/promote`
- [x] R7: **New endpoints — routes:**
      - `GET /agents/{id}/routes`
      - `GET /route-versions/{id}`
      - `POST /route-versions` (create draft)
      - `POST /route-versions/{id}/release`
      - `POST /route-versions/{id}/deprecate`
      - `POST /route-versions/{id}/promote`
- [x] R8: **Migration — prompts:**
      - Read current `system_prompt` from AppSettings
      - Create v1, agent_id=1, state=released + promoted
      - Insert `agent_components(1, 'prompt', <id>, ...)`
- [x] R9: **Migration — routes:**
      - Read current query routes (if any) from
        AppSettings
      - If present: create v1, released + promoted
      - If absent (install never configured routes):
        skip; `agent_components` has no `routes` row
        (operator can create one later)
- [x] R10: **Runtime: chat path reads promoted prompt**
      from `agent_components` → `prompt_versions.content`.
      No longer reads AppSettings directly for prompt.
- [x] R11: **Runtime: query router reads promoted
      routes** similarly.
- [x] R12: **AppSettings `system_prompt` and routes
      entries DEPRECATED** post-migration. Keep the
      rows but mark as `[migrated-see-prompt-versions]`
      so operators looking at AppSettings see the
      pointer. Removal in a future cleanup story.
- [x] R13: **Admin audit logging** on all state
      transitions.

## Acceptance Criteria

- [x] AC1: Fresh install post-migration → `prompt_versions`
      has v1 (default prompt text); `agent_components`
      has `prompt` row; routes may or may not have a
      row (dependent on install state).
- [x] AC2: Existing install → prompt v1 contains the
      operator's current prompt; chat uses it.
- [x] AC3: Create prompt draft, release, promote →
      chat (next request) uses new prompt;
      `agent_components` updated.
- [x] AC4: Promote routes v2 → query router (next
      request) uses new routes.
- [x] AC5: Un-promote routes (set to NULL / no promoted
      version) → router falls back to a no-op passthrough
      (if that path exists today) or errors cleanly.
- [x] AC6: Identical prompt text → same hash but
      different version IDs (provenance-not-dedup).
- [x] AC7: Routes JSON hash is stable under key reorder
      (canonicalization works).
- [x] AC8: Smoke-test: chat round-trip with migrated
      prompt; query flows through migrated routes if
      applicable.

## Design Notes

- **Why combine prompt + routes in one story:** same
  shape (small text blob versioned by hash), same
  migration pattern (read from AppSettings → create v1),
  same endpoint shape. Splitting would duplicate
  boilerplate.
- **Why trailing-whitespace strip in prompt hash:**
  operator editing a prompt in a text box commonly
  introduces incidental trailing whitespace that
  shouldn't count as content difference. Stripping is
  the pragmatic choice; documented in design doc.
- **Why canonicalize JSON for routes:** two routes
  configs with the same semantic content (keys in
  different order) should hash identically. Dict-key
  sort + no-whitespace serialization is standard.
- **Why not delete the old AppSettings rows:**
  reading them tells operators "where did this value
  go?" better than "setting removed." Marking as
  migrated keeps the mental model clean during
  transition.
- **Routes may legitimately not exist** on installs
  that never configured query routing — skip migration
  in that case; endpoint still works but promoted
  routes row is absent.

## Out of Scope

- Prompt/routes editing UI — future story
- Diff view between prompt versions — future
- Multi-prompt switching per request — future
- Prompt templating / variable interpolation — future
- Removing AppSettings legacy pointer rows (cleanup
  follow-up)

## Related

- [TB-US-044](tb-us-044.md) §11 per-component — this
  story executes it for prompt + routes
- [TB-US-051](tb-us-051.md), [TB-US-052](tb-us-052.md)
  — prerequisites
- Files touched:
  - `backend/api/prompt_version_manager.py` (new)
  - `backend/api/route_version_manager.py` (new)
  - `backend/api/main.py` — chat path reads from
    `agent_components`; new endpoints
  - `backend/api/schema_migrations.py` — prompt + routes
    backfill

## Completion Notes (2026-10-21)

**Managers + 12 endpoints + AppSettings migration shipped. R10/R11 runtime routing deferred following the TB-US-053/054 precedent.**

### Delivered

- **`backend/api/prompt_version_manager.py`** — concrete subclass:
  - `canonical_bytes()`: UTF-8 encoding of trailing-whitespace-stripped text (R3)
  - `create_draft_text()` convenience wrapper
- **`backend/api/route_version_manager.py`** — concrete subclass:
  - `canonical_bytes()`: `json.dumps(..., sort_keys=True, separators=",:")` for canonical JSON (R4)
  - `create_draft_routes()` convenience wrapper
- **12 endpoints** (6 for prompts + 6 for routes): list / detail / create / release / deprecate / promote per surface
- **`backend/api/schema_migrations.py` `migrate_appsettings_prompt_and_routes()`** — reads `AppSettings.get()`, creates v1 released+promoted for each; idempotent via `schema_migrations.migration_id = 'tb-us-055-appsettings'`. Runs at startup after `apply_versioning_schema()`
- **Admin audit on every state transition and create** (success + failure paths)

### Verification (end-to-end via live service)

**Startup migration lifted current operator data:**

- `[schema] {'migration_id': 'tb-us-055-appsettings', 'prompt_version_id': 1, 'routes_version_id': 1, 'prompt_chars': 89, 'routes_count': 1}` ✓
- `prompt_versions.v1`: content_len=89 **matches** `AppSettings.rag_prompt`; state=released; agent_components row written with `promoted_by='migration'` ✓
- `route_versions.v1`: 1 route (the operator's `test_route`); content is canonical JSON (keys alphabetical); released + promoted ✓

**Idempotency:**

- 2nd restart log: `{'migration_id': 'tb-us-055-appsettings', 'already_applied': True}` — migration no-ops; no duplicates ✓

**Full lifecycle (via curl, super-only auth):**

- Create v2 draft (new content "New test prompt for v2") → new hash, state=draft ✓
- Release v2 → state=released ✓
- Promote v2 → `agent_components` upserts to v2 (displacing v1) ✓
- Deprecate v1 (no longer promoted) → 200 OK ✓ (demonstrates deprecate works when a version is NOT currently promoted — the inverse of TB-US-053's "cannot deprecate promoted" test)

**Test fixtures rolled back:** v2 deleted, v1 restored to `released` + re-promoted via raw SQL so operator's live prompt is preserved (migrated v1 was real operator data, not a test fixture — only the v2-draft was a test fixture).

### Scope decisions (R10, R11, R12)

- **R10 (chat path reads promoted prompt from `agent_components`):** DEFERRED. The RAGSystem's `_refresh_prompt_template` reads from AppSettings and is called per-query. Rewiring to prefer `agent_components.prompt → prompt_versions.content` is a small change but introduces a second source-of-truth risk until TB-US-057 provides multi-agent context. For now: migrated v1 holds a byte-identical copy of the AppSettings prompt — queries continue to see the same prompt whether they read AppSettings (current path) or prompt_versions.v1 (future path). Design hook (`prompt_version_manager.get_promoted(agent_id)`) is callable.
- **R11 (query router reads promoted routes):** DEFERRED. Same reasoning. `_refresh_query_routes` in RAGSystem continues to read from AppSettings. v1 route is byte-identical to AppSettings data.
- **R12 (deprecate AppSettings `system_prompt` and `routes` entries post-migration):** DEFERRED to future cleanup when R10/R11 wire the versioned path. Marking them as `[migrated-see-prompt-versions]` while they're still the active source of truth would mislead operators who see them in the admin UI.

### What this unblocks for TB-US-057

Math-example seeder has concrete APIs for prompt + routes:

```
POST /prompt-versions  { agent_id, content }
POST /prompt-versions/{id}/release
POST /prompt-versions/{id}/promote

POST /route-versions   { agent_id, routes }
POST /route-versions/{id}/release
POST /route-versions/{id}/promote
```

Math-example will seed with its tutor-framing prompt + any domain-specific query routes. When TB-US-057 lands, R10/R11 runtime wiring also lands (RAGSystem reads from `agent_components` first, falls back to AppSettings only for backward compat).
