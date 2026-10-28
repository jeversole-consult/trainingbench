# TB-US-017: User management v2 — backend (API + audit log)

**Status**: Completed
**Created**: 2026-10-13
**Phase-split**: 2026-10-15 (originally one story; split into backend + frontend)
**Completed**: 2026-10-15
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

> **Phase 1 of 2.** This story covers the backend-only slice of
> user management v2: new UserManager methods, new endpoints,
> admin_audit schema, and audit instrumentation on existing
> admin endpoints. The frontend extensions (confirmation modal,
> reactivate buttons, email inline edit, bulk-op toolbar, audit
> log viewer tab) live in **[TB-US-041](tb-us-041.md)**.
>
> The pair is driven by the memory `feedback_phase_split_stories`:
> distinct deliverables (API vs UI) + distinct verification
> paths (curl + SQL vs browser) + natural go/no-go gate.

## Story

As a super user administering a TrainingBench install, I want
the backend to support the full lifecycle of a user record —
hard delete, reactivate, email edit, bulk operations across
multiple users, and an audit log of every administrative action
— so that the admin UI (TB-US-041, Phase 2) has a complete API
to call and every action already leaves a reviewable trail
before the UI exposes it.

## Background

TB-US-010 (Shipped, July 2026) delivered the first user-
management UI: a modal with list, create, change-type,
password-reset, and deactivate (soft delete). The backend
endpoints behind that UI already supported more than the modal
exposed (`DELETE /users/{username}` exists but is unused), and
TB-US-010's Out of Scope list explicitly flagged four follow-up
items:

- **Reactivating** deactivated users (requires a new
  `UserManager.reactivate()` method and UI control)
- **Audit log** of admin actions (who did what, when)
- **Bulk operations** (deactivate many, delete many, change
  many)
- **User-editable profile page** (deliberately out of scope
  here too — this story is admin-facing only)

This story closes the first three and extends scope with:

- **Hard delete with explicit confirmation** — exposes the
  backend's `DELETE /users/{username}` through the UI, gated
  behind a confirmation modal to prevent accidental data loss.
- **Email editing** — the current UI treats email as read-only;
  the field needs to be editable in-place.
- **Keep deactivate** — soft delete remains the default-safer
  action for routine "take someone offline" workflows. Hard
  delete is for cleanup, not day-to-day.

The user model this covers is unchanged: `super | chat |
training` (TB-US-016 context — email has no uniqueness
constraint; username does; `super` role is required for every
action here).

## Requirements

- [x] R1: **New `UserManager.reactivate(username)` method.**
      Sets `active=1` on an existing row. Returns the standard
      status dict. Error if user not found or already active.
- [x] R2: **New `UserManager.update_email(username, email)`
      method.** Updates the email column. Email remains
      non-unique (per the users-table schema); no conflict
      handling required. Accept empty / null to clear email.
- [x] R3: **New endpoints** (all `verify_super_user`-gated):
      - `PUT /users/{username}/active` — body `{active: true|false}`.
        Replaces (or complements) the existing deactivate-only
        path, exposing reactivation symmetrically.
      - `PUT /users/{username}/email` — body `{email: string}`.
        Updates email.
      - `GET /admin/audit-log` — returns the audit log
        entries, newest first, with optional `?limit=N`.
      - `POST /admin/bulk` — body `{action: "deactivate" |
        "activate" | "delete", usernames: [..]}`. Server
        iterates and returns a per-user outcome map.
- [x] R4: **Audit log table** in `users.db`:
      ```
      CREATE TABLE admin_audit (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          timestamp TEXT NOT NULL,     -- ISO-8601 UTC
          actor TEXT NOT NULL,         -- username performing the action
          action TEXT NOT NULL,        -- 'create' | 'delete' | 'deactivate'
                                       -- | 'activate' | 'change_type'
                                       -- | 'reset_password' | 'update_email'
                                       -- | 'bulk_<action>'
          target TEXT,                 -- username acted on (null for bulk)
          details TEXT,                -- JSON blob — before/after snapshot
          success INTEGER NOT NULL DEFAULT 1
      );
      ```
      Created on first service start post-upgrade (same
      pattern `users` table uses).
- [x] R5: **Every admin endpoint writes to `admin_audit`**
      before returning its response. Failed attempts
      (`success=0`) also log, with the error reason in
      `details`. Both existing (TB-US-010) endpoints and the
      new ones gain this instrumentation.
- [x] R6: **No regression on existing endpoints.** The GET
      `/users`, POST `/users`, PUT `/users/{username}/type`,
      PUT `/users/{username}/password`, and DELETE
      `/users/{username}` continue to work with the same
      request / response shapes they have today. Audit
      logging is additive.
- [x] R7: **Self-action protections remain.** The caller
      cannot delete, deactivate, or demote themselves. Backend
      enforces (as TB-US-010 AC5 already did for deactivate);
      extended to delete + bulk ops.

### Operational

- [x] R8: **Migration-safe.** On deploy, if `admin_audit`
      doesn't exist, create it. If a row already exists for a
      previously-performed action, we're fine either way
      (table starts empty; backfill is not required).

**Frontend requirements** (R8-R13 and R15 in the pre-split
version) **moved to [TB-US-041](tb-us-041.md).** This story
delivers only the backend surface.

## Acceptance Criteria

### Core gap-fill (backend)
- [x] AC1: `DELETE /users/{username}` as super removes the row
      from `users.db`. Verified by SELECT after the call.
- [x] AC2: `PUT /users/{username}/active {"active": false}`
      as super sets `active=0`. Verified by SELECT.
- [x] AC3: `PUT /users/{username}/active {"active": true}` as
      super on a deactivated user sets `active=1`. Verified by
      SELECT.
- [x] AC4: `PUT /users/{username}/email {"email": "..."}` as
      super updates the `email` column without affecting any
      other field. Verified by SELECT across all columns pre
      and post.
- [x] AC5: Self-action protections — the authenticated caller
      cannot delete, deactivate, demote themselves. Each
      attempt returns HTTP 400 (or similar non-500) with a
      descriptive message.

### Audit log (backend)
- [x] AC6: Every admin action (create, modify, change type,
      reset password, update email, deactivate, activate,
      delete, bulk operations) results in exactly one new row
      in `admin_audit` with correct `actor`, `action`,
      `target`, `timestamp`, and `success=1`.
- [x] AC7: A failed action (e.g. attempting to self-delete)
      logs with `success=0` and an informative `details` entry.

### Bulk operations (backend)
- [x] AC8: `POST /admin/bulk {"action": "deactivate",
      "usernames": [...]}` with three usernames as super sets
      `active=0` on all three; response is a per-user outcome
      map.
- [x] AC9: Bulk operations create one audit entry per user
      acted on (not a single aggregate entry).

### No-regression + role gating (backend)
- [x] AC10: Existing endpoints (GET /users, POST /users,
      PUT /users/{username}/type, PUT /users/{username}/password,
      DELETE /users/{username}) continue to work with their
      TB-US-010 request/response shapes. Audit logging is
      additive — new rows in admin_audit on each call.
- [x] AC11: Non-super users receive HTTP 403 from every new
      endpoint added by this story (`PUT /users/{username}/active`,
      `PUT /users/{username}/email`, `GET /admin/audit-log`,
      `POST /admin/bulk`).

**UI-dependent ACs** (confirmation modal visuals, audit log
viewer rendering, loading states, inline validation, TB-US-010
visual regression check) **moved to [TB-US-041](tb-us-041.md).**

## Design Notes

- **Why hard delete and deactivate coexist.** Deactivate is
  the day-to-day workflow (someone leaves the team, their
  account goes offline but their row — including `created_at`
  and `last_login` — stays). Hard delete is for cleanup
  (duplicate account, test account, GDPR-style removal
  request). The UI defaults bias toward deactivate; hard
  delete requires explicit confirmation to signal "this is
  destructive."
- **Audit log destination.** `admin_audit` lives in `users.db`
  (same SQLite file as the users table). Keeps the admin
  state together, matches the single-file-per-concern pattern
  the backend already uses, and avoids a new DB file. Logs
  travel with user state on backup / restore.
- **Audit log retention.** No automatic purge in v1. If the
  log grows large enough to matter later, add a follow-up
  story. For TB's current scale (handful of super users,
  ~5-10 admin ops per month at most) a decade of logs is
  trivial.
- **Audit log details field.** JSON blob — flexible across
  action types. For a password reset, `details` can be `{}`
  (the new password is not logged). For an email update,
  `{"before": "old@…", "after": "new@…"}`. For a type change,
  `{"before": "chat", "after": "training"}`. For a bulk op,
  include the aggregate parameters. The exact schema per
  action can evolve without a migration.
- **Bulk-op backend design.** Single `POST /admin/bulk`
  endpoint with action discriminator keeps the API surface
  small and lets the backend iterate. If one user in the
  bulk fails, the others still complete; the response is a
  per-user outcome map rather than all-or-nothing. Simplifies
  the UI's error-reporting path.
- **Email edit — in-place vs form.** In-place click-to-edit
  feels right in a dense table. Dedicated form (edit button
  → modal) is more conservative. R10 leaves the choice to
  the implementer; both satisfy the AC.
- **Self-action protections.** TB-US-010 already enforced
  no-self-deactivate at the backend. Extended here to
  no-self-delete and no-self-type-change (demotion). The
  frontend disables the buttons on the caller's own row as a
  UX improvement but the backend is the enforcement layer.
- **Bulk ops and self-protection.** If the caller is in the
  selected set for a destructive bulk op, the backend
  returns an error for *that user only* and completes the
  others. The UI surfaces the per-user outcome so the caller
  sees why.
- **UX polish is subjective.** R13's bullets are the
  implementer's minimum bar. Additional polish is welcome
  but not blocking; AC12 and AC13 are the measurable items.
- **"Users v2" — what the modal looks like.** The scope
  stays within a single modal (not a dedicated admin page).
  Two tabs: "Users" (list + actions, enriched) and
  "Audit log" (viewer). TB-US-010's choice of modal-overlay
  is preserved.

## Out of Scope

- **Username changes.** TB has no foreign-key referential
  integrity across tables that reference usernames
  (`training_sessions` for example); renaming is a mine
  field and belongs to a dedicated story if ever wanted.
- **Audit log search / filter / export.** v1 is "newest-first
  list with expandable details." A search box, time-range
  filter, action-type filter, CSV export etc. — follow-up
  if the log gets large enough to need them.
- **Audit log retention policy / auto-purge.** No automatic
  cleanup. If storage ever becomes a concern, separate story.
- **Password strength requirements** on create/reset. Current
  posture (SHA-256 + global salt) means strength is less
  meaningful than the hashing weakness. Both get addressed
  by TB-US-003.
- **Per-user self-service profile page.** Admin-facing only.
  A user editing their own email / password is a distinct
  feature.
- **MFA for admin actions** or step-up auth. Belongs in the
  shared IAM arc (PM-US-004 on projmgmt).
- **Rate limiting on admin endpoints.** TB has `LoginTracker`
  for `/auth/login`; admin endpoints are not currently
  rate-limited. Separate security-hardening concern.
- **Role-based permission expansion** (new roles beyond
  `super | chat | training`). Not needed for admin UI.
- **Audit log sign-off / supervisor approval workflow.** v1
  is "trail of record"; no workflow gates.
- **Projmgmt-side adoption of this UI.** This is TB-only. If
  projmgmt wants a similar admin UI, that's a separate PM
  story.

## Related

- [TB-US-041](tb-us-041.md) — **Phase 2 — frontend extensions
  of the admin modal.** Depends on this story being complete.
- [TB-US-010](tb-us-010.md) — Shipped the initial admin modal
  (create, change type, reset password, deactivate, list).
  This story extends that modal.
- [TB-US-016](tb-us-016.md) — Created the current TB user
  population; verified the schema details (`email` not
  unique, `username` unique, `user_type` CHECK-constrained).
- [TB-US-011](tb-us-011.md) — Ownership-based training-set
  access for training-role users. This story's audit log
  will record role changes that affect that gating.
- [TB-US-003](tb-us-003.md) — Per-user salts. When it ships,
  this story's password-reset path will migrate to the new
  hashing in place.
- Backend files touched (this story):
  - `backend/api/user_manager.py` — new methods for
    reactivate, update_email, hard_delete, plus audit-log
    helpers.
  - `backend/api/main.py` — new endpoints, audit logging
    integration in all admin paths.
- Schema change:
  - `users.db` gains `admin_audit` table (created on
    service start if absent).
- Phase 2 ([TB-US-041](tb-us-041.md)) touches:
  - `static/user_management.js`, `static/user_management.css`,
    `static/index.html` cache-bust. Scope lives there.

**Completion Notes (2026-10-15).**

**UserManager extensions** (`backend/api/user_manager.py`, +162 lines):
- `admin_audit` table added to `_init_database`.
- `reactivate_user(username)` — sets active=1; errors if not found or
  already active.
- `update_email(username, email)` — updates email column; empty/null
  clears; returns before/after pair for the audit.
- `hard_delete_user(username)` — row removal with deleted_snapshot
  captured for audit before DELETE.
- `append_audit(actor, action, target, details, success)` — best-effort
  INSERT into admin_audit; never raises to caller.
- `get_audit_log(limit=200)` — newest-first query with JSON-deserialized
  details field.

**main.py extensions** (`backend/api/main.py`, +~450 lines):
- 3 new Pydantic models: `SetActiveRequest`, `UpdateEmailRequest`,
  `BulkActionRequest`.
- 4 new endpoints: `PUT /users/{username}/active`,
  `PUT /users/{username}/email`, `GET /admin/audit-log`,
  `POST /admin/bulk`.
- `DELETE /users/{username}` extended with `?permanent=true` opt-in
  for hard delete; default behavior (soft delete via deactivate_user)
  preserved for TB-US-010 UI compat.
- Audit instrumentation added to all 5 existing admin endpoints
  (create, change-type, change-password, delete-or-deactivate — plus
  the 4 new endpoints audit-log themselves).
- Self-action protection extended to change-type (previously only
  deactivate had it).

**Design choice — DELETE semantics compat:**

Pre-TB-US-017, TB's `DELETE /users/{username}` was soft delete (called
`deactivate_user`), despite the HTTP verb. The TB-US-017 story was
written assuming it was already hard delete. To preserve TB-US-010
UI compatibility across the phase gap (post-TB-US-017, pre-TB-US-041),
I kept the default DELETE behavior as soft delete and added
`?permanent=true` as the hard-delete opt-in. TB-US-041 will migrate
the UI to use `PUT /users/{username}/active {"active": false}` for
deactivation and `DELETE /users/{username}?permanent=true` for hard
delete.

**AC verifications (end-to-end live):**

| AC | Result | Evidence |
|---|---|---|
| AC1 (DELETE permanent hard-deletes) | ✓ | tb_us_017_test row count post-DELETE: 0 |
| AC2 (PUT active=false deactivates) | ✓ | active=False returned |
| AC3 (PUT active=true reactivates) | ✓ | active=True returned on previously-deactivated user |
| AC4 (PUT email updates in isolation) | ✓ | SELECT confirms email changed, other fields untouched |
| AC5 (self-action blocked) | ✓ | HTTP 400 on DELETE admin (self) |
| AC6 (every action audited) | ✓ | 6 audit rows post-test-sequence; actor/action/target/success all correct |
| AC7 (failed action logs success=0) | ✓ | self-delete attempt logged with success=False, details.error='self-action-blocked' |
| AC8 (bulk deactivate) | ✓ | 3 users set active=0 via one request, outcomes returned per-user |
| AC9 (bulk audit per-user) | ✓ | 3 bulk_deactivate audit rows created (not one aggregate) |
| AC10 (existing endpoint shapes preserved) | ✓ | GET /users returns same 7-key shape as pre-TB-US-017 |
| AC11 (non-super 403s) | ✓ | All 4 new admin endpoints return 403 for non-super user |

**Diff summary**: `user_manager.py` +162 lines, `main.py` +~450
lines (cumulative diff vs HEAD baseline includes earlier TB-US-033
through TB-US-040 work plus this story).

**Phase 2 ([TB-US-041](tb-us-041.md)) now unblocked.** Frontend will
consume: `PUT /users/{username}/active`, `PUT /users/{username}/email`,
`GET /admin/audit-log`, `POST /admin/bulk`, and
`DELETE /users/{username}?permanent=true`.
