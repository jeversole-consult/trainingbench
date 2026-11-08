# TB-US-101: Port — api_key_manager to stalite3

**Status**: Completed 2026-11-07 — stalite3 commit `9c91f95`
**Depends on**: none (independent backend module)
**Blocks**: nothing critical; endpoint + UI wire-up are later ports

## Scope

- [x] Port `backend/api/api_key_manager.py` verbatim from TB-US-063
      (no path changes). Stores keys in stalite3's `users.db`;
      table self-initializes on first operation via `_init_table()`.

## Capabilities

- `create_key(label, created_by)` — 32-char raw key + SHA-256 hash
- `list_keys(include_revoked=True)`
- `get_by_id(key_id)`
- `revoke(key_id)` — soft-revoke timestamp
- `verify(raw_key)` — active-key lookup

## Acceptance Criteria

- [x] AC1: ApiKeyManager instantiates, table auto-initializes.
- [x] AC2: Full create → list → revoke → verify flow works.

## Not in scope

- `/api-keys/*` endpoints (endpoint-port story)
- API-key auth decorator wire-up in main.py
- `api_key_management.js` UI (UI-port story)
