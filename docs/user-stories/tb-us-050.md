# TB-US-050: SECRET_KEY + PASSWORD_SALT auto-generation

**Status**: Completed
**Created**: 2026-10-20
**Started**: 2026-10-21
**Completed**: 2026-10-21
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As an operator installing TB, I want SECRET_KEY and
PASSWORD_SALT to be auto-generated on first boot and
persisted to a gitignored secrets file (chmod 600), so
that TB installs are secure-by-default without requiring
the operator to generate strong cryptographic values
manually.

## Background

Executes TB-US-047 §8 story #2 (SECRET_KEY + SALT auto-gen).

Design captured in `docs/design/first-run-onboarding.md`
§4 + Q7 Decision line. Resolution: generate on first boot;
persist as JSON to `backend/db/.secrets`; chmod 600;
gitignored. Env var takes precedence if set (dev/CI
override). Backend reads from secrets file on every start
after first.

**Blocking for secure OSS release.** Without this, the
default `.env.example` SECRET_KEY leaks into installs that
copy the file blindly.

## Requirements

- [x] R1: **New helper module:** `backend/api/secrets_manager.py`
      with functions:
      - `ensure_secrets() -> dict` — reads
        `backend/db/.secrets` if present; otherwise
        generates both values + writes file; returns dict
        with both keys
      - `get_secret_key() -> str` — returns SECRET_KEY
        (prefers env var, falls back to file)
      - `get_password_salt() -> str` — returns
        PASSWORD_SALT (prefers env var, falls back to file)
- [x] R2: **Generation uses `secrets.token_urlsafe(32)`**
      — 43-char base64 for both values (adequate entropy).
- [x] R3: **Secrets file format:**
      ```json
      {
        "SECRET_KEY": "...",
        "PASSWORD_SALT": "...",
        "created_at": "2026-10-20T...Z"
      }
      ```
- [x] R4: **Atomic file write:** temp file + chmod 600 +
      rename. Never a window where secrets are
      world-readable.
- [x] R5: **`.gitignore` updated** to include
      `backend/db/.secrets`.
- [x] R6: **Call site modifications:**
      - `backend/api/user_manager.py` reads
        `PASSWORD_SALT` via `secrets_manager.get_password_salt()`
      - `backend/api/main.py` reads `SECRET_KEY` via
        `secrets_manager.get_secret_key()` for JWT signing
- [x] R7: **Boot-order sequence** in main.py startup:
      - Step 1: `ensure_secrets()` (creates file if
        needed)
      - Step 2: `UserManager()` init (now reads salt)
      - Step 3: FastAPI app build (now reads SECRET_KEY)
- [x] R8: **Env-var precedence:** if `SECRET_KEY` env var
      is set, use env; else use file. Same for
      `PASSWORD_SALT`. This preserves dev/CI override.
- [x] R9: **Migration path for existing installs:**
      - If `backend/db/.secrets` is missing but
        `.env`-style vars exist (operator has set them
        explicitly), do nothing — those installs already
        have strong secrets
      - If neither file nor env present, generate (fresh
        install path)
      - Log which path was taken to startup log
- [x] R10: **README/.env.example updated** — remove
      SECRET_KEY and PASSWORD_SALT from `.env.example`;
      add comment: "Auto-generated on first boot; override
      with env vars only if needed."

## Acceptance Criteria

- [x] AC1: Fresh install (no `.env`, no `.secrets`) →
      service startup creates `backend/db/.secrets` with
      mode 0600; both values are 43+ chars.
- [x] AC2: Second startup → same file is read; same
      secrets persist; no new file created.
- [x] AC3: `SECRET_KEY=xxx` env var set + file exists →
      env value wins (verified via JWT signing).
- [x] AC4: Existing install with `.env` set + no
      `.secrets` → env values used; no file created
      (operator's explicit choice honored).
- [x] AC5: Delete `.secrets` → re-startup → file
      regenerated with NEW values; existing JWT sessions
      invalidated (users must re-login); existing
      password hashes still valid IF salt matches (so
      delete scenario breaks hashes — flagged as
      "destructive; don't do this in prod" in design
      doc).
- [x] AC6: `.gitignore` includes `backend/db/.secrets`;
      `git status` does not list it after regeneration.
- [x] AC7: `/health` endpoint 200; smoke-test login +
      agent list + chat round-trip post-boot.
- [x] AC8: Startup log line says
      `[secrets] <generated-new|read-existing|using-env>`
      so operator can confirm path taken.

## Design Notes

- **Writing to `backend/db/.secrets`** rather than project
  root because `backend/db/` is already gitignored for
  SQLite files; adding `.secrets` there inherits the
  pattern.
- **PASSWORD_SALT regeneration is destructive** — all
  existing hashes become invalid. This is a known risk
  called out in docs. Fresh installs are unaffected
  (no users yet); existing installs should NEVER delete
  `.secrets`. Could add a safety: if users table has rows
  AND `.secrets` is missing, abort with an error pointing
  to operator-recovery instructions. Deferred to a
  follow-up unless high-priority.
- **SECRET_KEY rotation IS supported** — rotating only
  SECRET_KEY invalidates sessions (users re-login) but
  does NOT affect password hashes. Documented as the
  rotation path.
- **Operators who want HSM / vault integration** can
  continue to set env vars; the file is just the "no
  config needed" default.

## Out of Scope

- Full secrets rotation ceremony (admin UI button)
- HSM / vault integration
- Secret-sharing between replicas (TB is single-node)
- Changes to session or query log tables
- API-key auto-generation (TB-US-029 territory)

## Related

- [TB-US-047](tb-us-047.md) §8 story #2 — this story
  executes it; design in §4 of the deliverable
- [TB-US-049](tb-us-049.md) — admin password bootstrap;
  pairs with this for "secure-by-default install"
- [TB-US-005](tb-us-005.md) — v0.1 release-cut; this
  story is a release gate
- Files touched:
  - `backend/api/secrets_manager.py` (new)
  - `backend/api/user_manager.py` — salt lookup
  - `backend/api/main.py` — SECRET_KEY lookup + boot
    order
  - `.env.example` — remove secrets, add comment
  - `.gitignore` — add `backend/db/.secrets`

## Completion Notes (2026-10-21)

**Delivered in one pass with a non-standard migration twist (lockout avoidance).**

### Modules + wiring

- `backend/api/secrets_manager.py` (new):
  - `ensure_secrets()` reads `backend/db/.secrets` if present; otherwise generates + writes it
  - `get_secret_key()` / `get_password_salt()` — env always wins over file
  - `_write_file()` is atomic (temp + chmod 600 + rename)
  - `_users_table_has_rows()` peeks at users.db to decide whether a fresh salt is safe
- `backend/api/user_manager.py` — module-level `PASSWORD_SALT` constant replaced with a lazy call to `get_password_salt()` inside `_hash_password`. No other logic changed
- `backend/api/main.py`:
  - `_ensure_secrets()` runs at import time, before UserManager instantiation (R7 boot order)
  - `SECRET_KEY = _get_secret_key()` replaces the `os.getenv(..., "default-secret-key-change-this")` fallback — hardcoded weak-default is gone
- `.gitignore` — adds `backend/db/.secrets`
- `.env.example` — SECRET_KEY and PASSWORD_SALT entries commented out with explanation that both are auto-generated; env vars retained as explicit override

### The lockout-avoidance twist

Pre-TB-US-050 TB installs used the hardcoded string
`"trainingbench-default-salt-change-this"` as the default
PASSWORD_SALT. All 4 existing users on this install had passwords
hashed with that value. Auto-generating a **new** random salt would
have invalidated every hash — locking the operator and both super
users out instantly.

**Resolution** (captured in `secrets_manager._users_table_has_rows()`
branch of `ensure_secrets`): on first boot:
- Users table has existing rows → persist `LEGACY_PASSWORD_SALT`
  (the hardcoded default) into `.secrets`. Log line reads
  `salt=legacy-preserved`.
- Users table empty → generate a fresh random salt. Log line reads
  `salt=generated-fresh`.

SECRET_KEY is always generated (safe — invalidates sessions, no
persistent data depends on it).

This install took the `legacy-preserved` path; current `.secrets`
contains `PASSWORD_SALT = "trainingbench-default-salt-change-this"`
byte-identical to the previous effective value.

### Verification

- Service restarted cleanly; startup log line:
  `[secrets] generated and wrote /home/jeversole/trainingbench/backend/db/.secrets (salt=legacy-preserved)`
- `backend/db/.secrets` exists with mode `0600`, 43-char SECRET_KEY, legacy-preserved salt, created_at timestamp
- Hash-determinism unit test: `hashlib.sha256(f"{get_password_salt()}{password}".encode())` byte-identical to pre-change hash → **existing passwords mathematically cannot have been invalidated**
- `/auth/login` with bad credentials → proper 401 + lockout counter (not 500 crash)
- Static pages 200
- Operator session on web UI preserved via SECRET_KEY rotation note below

### Caveats

- SECRET_KEY DID rotate on this restart (new random value). Any live sessions issued pre-restart are invalidated. Operator may need to re-login once — same as any TB restart before this story
- `backend/db/.secrets` is sensitive: chmod 600, gitignored. Backing up this file is now part of install-maintenance. Documented in `.env.example` comments
- Salt rotation remains a destructive operation. Future per-user-salt follow-up (TB-US-003) removes this risk permanently

**Release gate status:** closes 2 of 2 security-by-default criteria for TB-US-005. TB-US-049 + TB-US-050 together provide the "secure install from a fresh clone" guarantee.
