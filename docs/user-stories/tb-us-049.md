# TB-US-049: Admin password bootstrap implementation

**Status**: Completed
**Created**: 2026-10-20
**Started**: 2026-10-21
**Completed**: 2026-10-21
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As an operator installing TB from GitHub, I want the admin
password to be auto-generated on first boot (random 24-char
passphrase printed to stdout + written to a chmod-600 file)
and then forced to change on first login — so that TB
installs are secure-by-default and the admin credentials
are never the known-weak `admin / changeme` default.

## Background

Executes TB-US-047 §8 story #1 (admin password bootstrap).

Design captured in `docs/design/first-run-onboarding.md` §3
+ Q1 Decision line. Resolution: random passphrase on first
boot; `must_change_password` flag on users table; forced-
change page handles first login; env-var override preserved
for dev/CI (no forced-change flag set).

**Blocking for secure OSS release.** TB-US-005 release-cut
gate.

## Requirements

- [x] R1: **New users table column:** `must_change_password
      INTEGER NOT NULL DEFAULT 0` added to `users` table.
      Migration-safe: existing rows get 0 (not flagged;
      their passwords are intentional).
- [x] R2: **UserManager._init_database modified:**
      - If users table is empty AND `DEFAULT_ADMIN_PASSWORD`
        env var is unset, generate 24-char passphrase via
        `secrets.token_urlsafe(18)`
      - Create admin user with that password hashed + flag
        set to 1
      - Print credentials banner to stdout (visible in
        `systemctl status` / terminal)
      - Write credentials to `logs/first-run-admin.txt`
        with `chmod 600`
      - If env var IS set: use it; do NOT set the flag
- [x] R3: **New endpoint:** `POST /auth/change-password` that
      accepts `{current_password, new_password}`; validates
      current; writes new hash; flips `must_change_password`
      to 0; deletes `logs/first-run-admin.txt` if present.
      Role-gated to the authenticating user (not super-only;
      operators change their own password).
- [x] R4: **Backend `/auth/login` response** includes
      `must_change_password: true|false` field so frontend
      can route accordingly.
- [x] R5: **New frontend page:**
      `static/first-change-password.html` — simple form (new
      password + confirm), min 10 chars enforced inline, no
      other nav; redirects to index.html on success.
- [x] R6: **Frontend login flow modification:** on successful
      login, if `must_change_password` is true, redirect to
      `first-change-password.html` instead of index.html.
- [x] R7: **API client exemption** — if operator used
      `DEFAULT_ADMIN_PASSWORD` env var (flag NOT set),
      login proceeds normally without forced-change
      interrupt.
- [x] R8: **Audit logging** — password-change event logged
      to `admin_audit` with action=`change_password` (adds
      to TB-US-017's audit log).
- [x] R9: **No regression** on existing user-management
      flows (TB-US-010 / 017 / 041 modal still works).
- [x] R10: **Cache-bust bumps** on login.html, index.html,
      main scripts touched.

## Acceptance Criteria

- [x] AC1: Fresh install with no `DEFAULT_ADMIN_PASSWORD`
      → service startup prints credentials banner;
      `logs/first-run-admin.txt` present with chmod 600.
- [x] AC2: Login as auto-admin → redirected to
      `/static/first-change-password.html`; cannot access
      index.html directly.
- [x] AC3: Password change with <10 chars → form error,
      no submission.
- [x] AC4: Password change with 10+ chars → success;
      `must_change_password=0`; `logs/first-run-admin.txt`
      deleted; redirect to index.html.
- [x] AC5: Second login (post-change) → routes directly to
      index.html, no forced-change.
- [x] AC6: Fresh install with `DEFAULT_ADMIN_PASSWORD=X`
      → auto-admin created with X; `must_change_password=0`;
      login proceeds normally without forced-change.
- [x] AC7: Super user creating another user via admin modal
      → new user does NOT get `must_change_password=1`
      flag (per Q4b scope).
- [x] AC8: `admin_audit` row created on successful
      password change.
- [x] AC9: Smoke-test other endpoints 200 post-restart.

## Design Notes

- **`secrets.token_urlsafe(18)` produces 24 chars** —
  ample entropy; URL-safe characters avoid shell-escape
  issues.
- **File write + chmod MUST be atomic** — write to temp
  path, chmod 600, then rename. Prevents a brief window
  where the file is readable.
- **Deleting `logs/first-run-admin.txt` on first change**
  reduces credential leakage window. Pre-change the operator
  can recover from the file; post-change the file was
  only valid for the already-changed password.
- **Forced-change page is bare-chrome** — no nav drawer,
  no welcome banner, no agent-selector. Just the form.
  Reduces operator confusion ("what IS this page?").
- **Change-password endpoint is open to all authenticated
  users** (not super-only). Any user can change their own
  password at any time. Admin-forced changes for other
  users still go through the super-only
  `PUT /users/{username}/password` endpoint from TB-US-017.

## Out of Scope

- Password strength beyond min-length (TB-US-003 full policy)
- Password rotation policy / expiry
- Password reset-by-email flow
- MFA
- Changes to session_tracker or query_logger
- Branding tweaks

## Related

- [TB-US-047](tb-us-047.md) §8 story #1 — this story
  executes it; design in §3 of the deliverable
- [TB-US-003](tb-us-003.md) (Deferred) — per-user salts;
  this story's hashing is still global salt
- [TB-US-005](tb-us-005.md) — v0.1 release-cut; this
  story is a release gate
- [TB-US-017](tb-us-017.md), [TB-US-041](tb-us-041.md) —
  admin user-management; this story extends the audit log
- Files touched:
  - `backend/api/user_manager.py` — schema migration,
    init logic, env-var check
  - `backend/api/main.py` — new `/auth/change-password`
    endpoint; `must_change_password` in login response
  - `static/first-change-password.html` (new)
  - `static/login.html` — flow modification
  - `static/script.js` — redirect-on-login logic
  - `.gitignore` — add `logs/first-run-admin.txt`

## Completion Notes (2026-10-21)

**Delivered in one pass.**

### Backend

- `backend/api/user_manager.py`:
  - Added `must_change_password INTEGER NOT NULL DEFAULT 0` to users table (R1); schema migration via try/except on `ALTER TABLE ADD COLUMN` for existing installs — idempotent across restarts
  - `_init_database`: branches on `DEFAULT_ADMIN_PASSWORD` env var. Unset → `secrets.token_urlsafe(18)` + flag=1 + stdout banner + atomic chmod-600 write to `logs/first-run-admin.txt`. Set → preserves prior behavior with flag=0 (R2, R7)
  - `create_user` now accepts `must_change_password` kwarg (default 0) so super-created users (TB-US-017 path) don't get flagged (AC7)
  - `authenticate` returns `must_change_password` on the user dict
  - New `must_change_password(username)` returns bool
  - New `self_change_password(username, current, new)`: verifies current hash, enforces 10-char minimum, writes new hash, clears flag, deletes credentials file (R3)
  - New `_write_first_run_admin_file` / `_delete_first_run_admin_file` helpers (atomic temp + chmod 600 + rename)
- `backend/api/main.py`:
  - `LoginResponse` extended with `must_change_password: bool = False` (R4)
  - `/auth/login` populates the flag from `authenticate` result (R4)
  - `/auth/verify` populates the flag from `user_manager.must_change_password()` so index.html can gate access
  - New `SelfChangePasswordRequest` model + `POST /auth/change-password` endpoint — authenticated-user-scoped; writes to `admin_audit` on success + failure (R3, R8)

### Frontend

- `static/first-change-password.html` (new) — bare-chrome amber-accented form; inline client-side validation (min 10, confirm match, differs from current); calls `/auth/change-password`; success → index.html (R5)
- `static/login.js` — on successful login response, if `must_change_password`, redirect to `/static/first-change-password.html` (R6)
- `static/script.js` — in `checkAuth()`, if `/auth/verify` returns `must_change_password=true`, redirect; this prevents AC2 bypass (typing index.html directly)
- Cache-bust bumps on `login.js` (new `?v=20261021a`) and `script.js` (`?v=20261017a` → `?v=20261021a`) in login.html + index.html (R10)

### Infra

- `.gitignore` adds `logs/first-run-admin.txt`

### Verification

- **Unit tests** against isolated DB `/tmp/tb_us_049_test.db` (via `venv/bin/python`):
  - Scenario A (auto-gen path): PASS — password generated, flag=1, file exists with mode 600
  - Scenario B (self_change_password lifecycle): PASS — wrong current rejected, short new rejected, correct change clears flag + deletes file
  - Scenario C (env-var override): PASS — password honored, flag=0, no file written
- **Schema migration verified live**: `users.db` on this install picked up the new column cleanly; all 4 existing users (admin, chat_user, tedcorvette, sfevers) default to must_change_password=0 — their passwords stay as-is
- **Service restart**: clean; uvicorn startup complete; `/static/login.html` and `/static/first-change-password.html` both 200; `/auth/login` returns proper 401 on bad credentials with lockout counter
- **AC1 and AC2 code-verified** — not live-verified end-to-end because that would require wiping users.db (destructive to the running install). The auto-gen branch is covered by the Scenario A unit test, which exercises the same code paths

### Caveats / known limits

- Existing install's current admin (`admin`) is not flagged — the migration adds the column defaulting to 0, matching the existing-passwords-are-intentional principle in R1. Operator can set the flag manually via SQL if desired, but the design doc explicitly preserves existing credentials
- Password hashing still uses the global `PASSWORD_SALT` — TB-US-003 (Deferred) is the per-user-salt follow-up
- Env-var exemption (R7) covers CI/dev; secrets-manager-based secrets (TB-US-050) is the next release-gate step

**Release gate status:** closes 1 of 2 for TB-US-005's security-by-default criteria. TB-US-050 remains.
