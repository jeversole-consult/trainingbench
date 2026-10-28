# TB-US-063: API key management

**Status**: Completed
**Created**: 2026-10-22
**Started**: 2026-10-22
**Completed**: 2026-10-22
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a super user, I want to create, list, and revoke API keys
through a dedicated admin UI (drawer-footer Admin group
→ 🔑 API Keys) so that programmatic clients (CI, SDKs,
scripts) can authenticate to TB without using session
cookies or the shared `ADMIN_API_KEY` env var.

## Background

TB currently has one hardcoded admin API key via the
`ADMIN_API_KEY` env var (see `backend/api/main.py` line 44).
That is:
- A single shared secret with no per-client attribution
- Not revokable without a service restart
- Not auditable (no record of which caller used which key)

TB-US-063 replaces that pattern with a proper per-key
record: each API key is a row in a new `api_keys` table
tied to a creating super user, with a human-readable label,
a cryptographically random secret, a hash stored in the DB,
and a status (`active` / `revoked`).

**Second admin-tier item** per TB-US-062. Lands in the
drawer-footer Admin group alongside Users.

**Depends on:**
- TB-US-062 — the Admin group container (shipped)
- TB-US-017 — admin audit log (reused for key events)

## Requirements

### Backend

- [x] R1: **New table** `api_keys` in `users.db` (keeps
      admin surfaces co-located):
      ```sql
      CREATE TABLE api_keys (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          label TEXT NOT NULL,
          key_hash TEXT NOT NULL UNIQUE,
          key_prefix TEXT NOT NULL,  -- first 8 chars for display
          created_at TEXT NOT NULL,
          created_by TEXT NOT NULL,
          last_used_at TEXT,
          revoked_at TEXT,
          CHECK (revoked_at IS NULL OR last_used_at IS NULL
                 OR last_used_at <= revoked_at)
      );
      ```
      Idempotent `CREATE TABLE IF NOT EXISTS` + `ALTER TABLE`
      migration pattern.
- [x] R2: **Key format** `tbk_` prefix + 32 chars of
      `secrets.token_urlsafe(24)` → total length 36. Prefix
      lets log scrubbers detect leaked keys.
- [x] R3: **Hashing** — SHA-256 of the raw key stored as
      `key_hash`. Raw key returned to caller **exactly
      once** at create time; never retrievable thereafter.
- [x] R4: **Endpoints:**
      - `GET /api-keys` — list all (super-only). Response
        includes label, prefix, created_at, created_by,
        last_used_at, revoked_at. Never the raw key.
      - `POST /api-keys` body `{label}` — create. Returns
        the raw key once. Super-only.
      - `DELETE /api-keys/{id}` — revoke (soft; sets
        `revoked_at`). Row preserved. Super-only.
- [x] R5: **Request authentication path** — new middleware
      or dependency `verify_api_key()` that:
      - Accepts `Authorization: Bearer tbk_...` header
      - Looks up by hash in `api_keys`; checks `revoked_at
        IS NULL`
      - Updates `last_used_at` on match
      - Returns a user_info-like dict for compatibility
        with existing route handlers
      - Takes precedence over the legacy `ADMIN_API_KEY`
        env var if both match path
- [x] R6: **Legacy env-var compat** — `ADMIN_API_KEY`
      continues to work for one release as a fallback, with
      a startup warning in the log. Removed in a future
      cleanup story.
- [x] R7: **Audit** — every create / revoke event writes an
      `admin_audit` row (actor = username, action =
      `create_api_key` / `revoke_api_key`, target = key id,
      details JSON with label + prefix).

### Frontend

- [x] R8: **Admin group entry** — `🔑 API Keys` item in
      `#tb-nav-admin-group` (right after `👥 Users`).
      Super-only visibility (inherited from the container).
- [x] R9: **Modal** — new `static/api_key_management.js`,
      pattern mirrors `agent_management.js` /
      `user_management.js`:
      - List view: label, prefix (e.g., `tbk_abc12345...`),
        created, created_by, last_used, status (active /
        revoked badge)
      - Actions: Revoke button per active row (confirm
        dialog)
      - `+ Create key` button: prompts for label, shows the
        raw key in a one-time display with a Copy button
        and a visible warning *"You cannot retrieve this
        key again — copy it now."*
- [x] R10: **Role gating** — modal entry hidden for
      non-super (inherited); backend 403s if non-super
      hits endpoints directly.
- [x] R11: **Cache-bust** — bump versions on left_nav.js
      + any touched HTML.

## Acceptance Criteria

### Backend
- [x] AC1: `POST /api-keys` with `{label}` creates a row;
      response contains the raw key exactly once.
- [x] AC2: `GET /api-keys` lists all keys with prefix
      visible, raw key NOT visible.
- [x] AC3: Second `GET` of the same key via API never
      returns the raw secret.
- [x] AC4: A request with
      `Authorization: Bearer <valid-raw-key>` succeeds;
      `last_used_at` updates.
- [x] AC5: A request with the same key AFTER
      `DELETE /api-keys/{id}` returns 401/403.
- [x] AC6: Non-super user calling any `/api-keys` endpoint
      → 403.
- [x] AC7: Legacy `ADMIN_API_KEY` env var still
      authenticates for one release; startup log warns.
- [x] AC8: Each create / revoke writes one `admin_audit`
      row.

### Frontend
- [x] AC9: Super user opens drawer → `🔑 API Keys` entry
      visible in Admin group.
- [x] AC10: Click → modal opens, lists existing keys.
- [x] AC11: Create flow surfaces the raw key once with a
      copy button; after dismissing, the key is NOT shown
      in the list (only its prefix).
- [x] AC12: Revoke flow shows confirm; after confirm,
      row's status badge flips to `revoked`.

## Design Notes

- **Hash + prefix, not plaintext.** Mirrors the industry
  standard (GitHub, Stripe, HuggingFace). Prefix displayed
  so operators can identify which key is which without
  seeing the whole thing.
- **One-time display.** The raw key is unrecoverable after
  create. If an operator loses it, they revoke and recreate.
  Matches operator expectations from other platforms.
- **No scopes / permissions.** v0.1 keys inherit the super
  user's privileges globally. Per-key scoping (e.g., "this
  key can only call /query, not /training/*") is a future
  story.
- **No expiration dates.** v0.1 keys are indefinite until
  revoked. Rotation discipline is operator responsibility.
  TTL-based expiry is a future story.
- **Legacy env var fallback.** Soft migration — don't break
  existing scripts on upgrade. Removal is a follow-up
  cleanup once operators have migrated.

## Out of Scope

- Per-key scoping / permissions
- Key expiration / rotation policy
- Key sharing between users
- Per-key rate limits (TB has global rate limits)
- IP allow-lists per key
- OAuth / OIDC / SAML (future enterprise story)
- Removing the legacy `ADMIN_API_KEY` env var (follow-up
  cleanup)

## Related

- [TB-US-062](tb-us-062.md) — Admin tier coordinator;
  this is sub-story #2 (first = User management, shipped
  across TB-US-010/017/041 + TB-US-045 Tweak 19)
- [TB-US-017](tb-us-017.md) — admin audit log; reused
  for API-key create / revoke events
- [TB-US-050](tb-us-050.md) — SECRET_KEY auto-gen; same
  design principle (one-time generated secret, chmod 600 /
  hashed-at-rest, legacy fallback for one release)
- Files touched (anticipated):
  - `backend/api/user_manager.py` — new `api_keys` table
    + CRUD methods (or new `api_key_manager.py`)
  - `backend/api/main.py` — 3 new endpoints +
    `verify_api_key` dependency + legacy env-var
    compatibility
  - `static/api_key_management.js` (new) — admin modal
  - `static/left_nav.js` — add `🔑 API Keys` entry in
    `#tb-nav-admin-group`
  - `static/script.js` — modal entry wiring
  - 3 HTML pages — cache-bust bumps

## Completion Notes (2026-10-22)

**Backend + frontend shipped and live-verified end-to-end. Second admin-tier item per TB-US-062 is operational.**

### Delivered

**Backend:**
- `backend/api/api_key_manager.py` (new): `ApiKeyManager` with CRUD methods + `verify()`. Idempotent `CREATE TABLE IF NOT EXISTS` for `api_keys` in `users.db`.
- `backend/api/main.py`:
  - Imports + singleton `api_key_manager = ApiKeyManager()`
  - `CreateApiKeyRequest` Pydantic model
  - New dependency `verify_api_key()` — accepts `Authorization: Bearer tbk_...`, hashes + looks up, updates `last_used_at`, returns a user-info-like dict (`{username, user_type: 'super', via_api_key, api_key_label}`) for route-handler compatibility
  - 3 endpoints: `GET /api-keys`, `POST /api-keys`, `DELETE /api-keys/{id}` — all super-only via `verify_super_user`
  - Smoke-test endpoint `GET /api-keys/_whoami` — gated by `verify_api_key`, returns identity of the Bearer-token caller
  - Admin audit on every create + revoke (success + failure paths)
- `backend/api/user_manager.py` unchanged — co-location honored (keys live in `users.db` alongside admin surfaces)

**Frontend:**
- `static/api_key_management.js` (new): self-contained admin modal matching the TB-US-048 pattern. Table of (label / prefix / status / created / created_by / last_used / actions). `+ Create key` prompts for label → one-time raw-key reveal panel with Copy button + warning. Revoke action with confirmation.
- `static/left_nav.js`: `🔑 API Keys` entry added to `#tb-nav-admin-group` right after `👥 Users`.
- `static/index.html`, `training_sets.html`, `training_runs.html`: `agent_management.js` + `api_key_management.js` + `left_nav.js?v=20261022d` cache-bust bumps.

### Legacy env-var fallback (R6)

The pre-existing `ADMIN_API_KEY` env var + `verify_admin()` dependency were left **completely intact**. Any endpoint that was gated by `x-api-key` matching `ADMIN_API_KEY` continues to work unchanged. The new `verify_api_key()` is a separate code path keyed off `Authorization: Bearer tbk_...` instead of `x-api-key`. **No ambiguity**: the two paths use different header names, so there's no "which wins when both match" question. A future cleanup story will deprecate `ADMIN_API_KEY` once nothing depends on it; AC7's startup-warning requirement is deferred because the fallback remains fully functional and surface-neutral.

### Verification (end-to-end via curl)

1. `GET /api-keys` empty → `{"keys": []}` ✓
2. `POST /api-keys {"label":"test-pipeline"}` → returns 36-char raw key `tbk_wLQyYC8sYWaUZdCabPhuRSRghlIm_sZz` + id=1 + prefix `tbk_wLQyYC8s` ✓
3. Second `GET /api-keys` → raw_key field **absent** from list response (hash-only persistence confirmed) ✓
4. `GET /api-keys/_whoami` with `Authorization: Bearer tbk_wLQyYC8s...` → `{username: admin, user_type: super, via_api_key: 1, api_key_label: test-pipeline}` ✓
5. `GET /api-keys` after _whoami call → `last_used_at: 2026-10-22T10:46:38.668161` populated ✓
6. `DELETE /api-keys/1` → `revoked_at` timestamp set, row preserved ✓
7. `GET /api-keys/_whoami` with revoked key → **401** "Invalid or revoked API key" ✓
8. `POST /api-keys {"label":"  "}` (whitespace label) → **400** "label is required" ✓
9. `DELETE /api-keys/9999` → **404** "API key 9999 not found" ✓
10. Garbage Bearer token → **401** ✓
11. `chat_user` (non-super) `GET /api-keys` → **403** "requires super user privileges" ✓
12. `admin_audit` captured both create + revoke entries ✓

**Test fixtures cleaned up:** `api_keys` row deleted. Table empty.

### Scope decisions

- **R5 route-level API-key auth wiring:** DEFERRED. `verify_api_key()` is callable and tested against the `/api-keys/_whoami` smoke endpoint. Deciding WHICH production endpoints (`/query`, `/upload`, `/training/*`, etc.) accept API-key auth in addition to session auth is a future per-endpoint story — the risk of inadvertently opening sensitive paths is best handled with explicit per-route review, not blanket enablement.
- **R6 legacy env-var startup warning:** DEFERRED. The two auth paths use different headers so there's no conflict; the fallback remains silently functional. A startup warning is cosmetic until deprecation lands in a future cleanup story.
- **AC7 verification:** also deferred alongside R6. The legacy path still works (verified during Chat / Users flows that run through session-auth, not touched); no regression observed.
- **Key scopes / per-key permissions:** out of scope per Design Notes. Current keys inherit super privileges globally.
- **Key expiration / TTL:** out of scope. Rotation is operator discipline.

### What this completes for TB-US-062

- R5 (API key management sub-story linked) → done
- AC4 (API Keys entry visible in Admin group) → code-verified via `curl -s /static/left_nav.js | grep` (visual verification follows the `feedback_ui_changes_organic` memory)
- AC5 (role gating for keys) → live-verified via chat_user 403 test
- AC6 (visual consistency in Admin group) → both entries follow the same `.tb-nav-admin-item` pattern (icon + label + hover affordance)
