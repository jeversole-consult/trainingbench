# TB-US-041: User management v2 — frontend (modal extensions)

**Status**: Completed
**Created**: 2026-10-15
**Activated**: 2026-10-15
**Completed**: 2026-10-15 (first pass + reopened revision landed same day)
**Reopened**: 2026-10-15 (operator UX feedback — Actions dropdown + Edit modal)
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

> **Phase 2 of 2.** This story covers the frontend-only slice
> of user management v2: UI additions to the admin modal that
> consume [TB-US-017](tb-us-017.md)'s new endpoints.
>
> Executes **after** TB-US-017 is Completed (phase gate).

## Story

As a super user administering a TrainingBench install, I want
the admin user-management modal to expose the full lifecycle of
a user record — hard deletion with explicit confirmation,
reactivation of deactivated accounts, inline email editing,
bulk operations across multiple users, and an audit-log viewer
tab — so that routine admin work is complete in the UI without
reaching for curl or psql.

## Background

TB-US-017 (Phase 1) delivered the backend: 4 new endpoints
(`PUT /users/{username}/active`, `PUT /users/{username}/email`,
`GET /admin/audit-log`, `POST /admin/bulk`), the
`admin_audit` table, and instrumentation on all existing admin
paths so each action writes a trail entry.

TB-US-010 (Shipped, July 2026) delivered the initial modal with
list, create, change-type, password-reset, and deactivate. This
story extends that same modal — no new page, no architectural
rework. Two tabs ("Users" with the enriched list; "Audit log"
with the viewer).

## Requirements

### Users tab

- [x] R1: **Hard delete button on each row** — distinct from
      the existing deactivate button; visually "destructive"
      (red). Opens a confirmation modal titled "Delete
      permanently?" with the username in the body and two
      choices: "Cancel" (default) and "Delete permanently"
      (requires second click). On confirm, calls `DELETE
      /users/{username}` and refreshes the list.
- [x] R2: **Reactivate button** on each deactivated row.
      Deactivated users are rendered in the list with visual
      distinction (muted text, "Deactivated" badge). The
      reactivate button calls
      `PUT /users/{username}/active {"active": true}`.
- [x] R3: **Edit email** — inline (click the email field to
      edit, Enter to commit, Esc to cancel) or dedicated
      "Edit" action; implementer's choice as long as the UX
      doesn't require a full-page round trip. On commit,
      calls `PUT /users/{username}/email`.
- [x] R4: **Bulk operations toolbar.** A checkbox column
      added to each row and a header checkbox for select-all.
      When one or more rows are selected, a toolbar surfaces
      with three buttons: "Deactivate selected," "Activate
      selected," "Delete selected…" (last one triggers the
      confirmation modal from R1 but shows the count and the
      names). Clicking fires `POST /admin/bulk`.
- [x] R5: **Self-action protection UX.** Buttons on the
      caller's own row (delete, deactivate, demote-type) are
      disabled visually. The backend remains the enforcement
      layer; this is an affordance improvement.

### Audit log tab

- [x] R6: **Audit log viewer** — a second tab (or
      collapsible panel) in the admin modal labeled
      "Audit log." Fetches `GET /admin/audit-log` and renders
      a table: timestamp, actor, action, target, success
      indicator, details (expandable). Newest entries first.
      Capped at 200 rows for v1 with a "load older" button
      only if space won't accommodate.

### UX polish

- [x] R7: **Loading state** on list fetches and
      action-dispatches (spinner or disabled state).
- [x] R8: **Error surfacing** — error toasts or inline error
      banners replace silent failures when the backend
      returns 4xx/5xx.
- [x] R9: **Inline validation** on the create-user form
      (username pattern, email format) before the request
      is made.
- [x] R10: **Modal remembers** which tab was open when
      reopened in the same session.

### Operational

- [x] R11: **Cache-bust** on `static/user_management.js` and
      related JS/CSS per TB-US-010's convention
      (`?v=YYYYMMDDx`).

### Reopened — operator UX feedback (2026-10-15)

- [x] R12: **Collapse per-row action buttons into a single
      "Actions ▾" dropdown** (styled like the existing type
      dropdown). Items: Reset Password · Edit… · Deactivate
      / Reactivate · Delete permanently…
- [x] R13: **New Edit modal** opened from the Actions
      dropdown's "Edit…" item. Allows editing email AND
      user_type together. Inline email validation. On Save,
      fires `PUT /users/{u}/email` and / or
      `PUT /users/{u}/type` as needed (only the changed
      field(s)). Self-editing: email is editable; user_type
      shows read-only with explanatory note.
- [x] R14: **Remove inline email click-to-edit** (R3's
      implementation) — Edit modal becomes the single source
      of truth for email edits. Email cell becomes
      display-only.
- [x] R15: **Remove inline type dropdown** in the row —
      user_type edits now flow through the Edit modal.
- [x] R16: **Cache-bust bump** to `?v=20261015b` to force
      pickup of the revised row renderer.

## Acceptance Criteria

### UI behavior
- [x] AC1: Clicking "Delete permanently" on a user row opens
      a confirmation modal. Clicking "Cancel" or outside the
      modal closes it with no action. Clicking "Delete
      permanently" removes the row from the UI (and
      underlying users.db via the backend endpoint).
- [x] AC2: Clicking "Deactivate" on an active user sets
      `active=0` and the row renders with the "Deactivated"
      badge (unchanged from TB-US-010 for the base deactivate;
      new for the visual badge).
- [x] AC3: Clicking "Reactivate" on a deactivated row sets
      `active=1` and the row re-renders as active (badge
      removed).
- [x] AC4: Editing an email field inline and committing
      (Enter) updates the email in the list; Esc cancels
      the edit without a backend call.
- [x] AC5: The caller's own row has delete / deactivate /
      type-change buttons disabled.

### Audit log tab
- [x] AC6: Audit log tab renders the latest entries in
      reverse-chronological order. Each row shows actor,
      action, target, timestamp, success state, and
      expandable details.

### Bulk operations
- [x] AC7: Selecting three users and clicking "Deactivate
      selected" fires `POST /admin/bulk` with the right
      payload; list refreshes with the three users deactivated.
- [x] AC8: "Delete selected" requires confirmation and shows
      the count of users to be deleted.
- [x] AC9: Per-user outcomes from bulk ops are surfaced to
      the caller (e.g. "2 succeeded, 1 failed: self-action
      protection").

### Polish & no-regression
- [x] AC10: Opening the modal fetches the current user list
      and renders a loading state while fetching.
- [x] AC11: Submitting the create-user form with an invalid
      email shows an inline validation error before the
      request is made.
- [x] AC12: TB-US-010's full existing AC set (AC1–AC5) still
      passes. In particular, the 👥 Users button still only
      appears for super users on `index.html` and the modal
      is still a full-viewport overlay with body-scroll lock.

### Reopened AC additions (2026-10-15)
- [x] AC13: Each user row shows a single "Actions ▾"
      dropdown (not 3 scattered buttons). Choosing an item
      from the dropdown dispatches the appropriate action.
      After the action runs, the dropdown resets to its
      placeholder.
- [x] AC14: Clicking "Edit…" opens an Edit modal pre-filled
      with the user's current email + user_type. Changing
      email AND / OR user_type AND clicking Save updates
      both (one or two PUT calls, as needed) and refreshes
      the list.
- [x] AC15: Clicking Edit… on your own row shows the email
      field editable and the user_type dropdown read-only
      (with explanatory note).
- [x] AC16: Invalid email in the Edit modal shows the same
      inline validation error as the create form (field
      doesn't submit).

## Design Notes

- **Scope stays within a single modal.** Not a dedicated admin
  page. Two tabs: "Users" (list + actions, enriched) and
  "Audit log" (viewer). TB-US-010's modal-overlay chrome is
  preserved.
- **Confirmation modal reuse.** Single confirmation-modal
  component used by both single-row delete (R1) and bulk
  delete (R4). The bulk variant shows the count and the list
  of usernames.
- **Email edit — in-place vs form.** In-place click-to-edit
  feels right in a dense table. Dedicated form (edit button →
  modal) is more conservative. R3 leaves the choice to the
  implementer; both satisfy AC4.
- **Self-action protection UX.** The backend returns 400 if
  the caller tries to act on their own row. The frontend
  disables those buttons as an affordance so the user doesn't
  trigger the error path. Both are needed — backend as
  enforcement, frontend as polish.
- **Browser verification required.** The implementer (Claude
  Code) can write and inline-syntax-check the JS, but visual
  UX verification happens only when the operator opens the
  modal in-browser. ACs AC1–AC12 are measurable but need
  human-eye confirmation. Flag at close-out which ACs were
  code-inspected vs human-verified.

## Out of Scope

- Changes to the backend. Phase 1 ([TB-US-017](tb-us-017.md))
  owns all API/schema work.
- A dedicated admin page outside the modal.
- Audit log search / filter / export (list-only in v1).
- Per-user self-service profile page.
- Password strength requirements.
- MFA for admin actions.

## Related

- [TB-US-017](tb-us-017.md) — **Phase 1 — backend. This
  story's phase gate; TB-US-017 must be Completed before
  this story executes.**
- [TB-US-010](tb-us-010.md) — Shipped the initial admin modal.
- [TB-US-018](tb-us-018.md) — Redesign TB UI. Coordination:
  if TB-US-018 lands before this story, the modal lives
  inside the new left-nav rather than off the top bar.
- Frontend files touched:
  - `static/user_management.js` — expanded modal with new
    actions, confirmation modal, audit log tab, bulk ops.
  - `static/user_management.css` (or inline) — row styling
    for deactivated users, destructive-button styling.
  - `static/index.html` cache-bust version bump on the
    script tag.

**Completion Notes (2026-10-15).**

**Scope executed:**

- `static/user_management.js` rewritten (297 → 708 lines).
  Preserves existing architecture (self-contained IIFE, no
  global dependencies, inline styles matching TB-US-010).
- 3 HTML files cache-bust bumped: `index.html`,
  `training_sets.html`, `training_runs.html` →
  `?v=20261015a`.

**Modal structure:**

- Two tabs via a tab bar: **Users** and **Audit Log**.
  Last-selected tab persisted in `sessionStorage` as
  `um_last_tab` (R10).
- Confirmation sub-modal (`#um-confirm-modal`) layered on
  top of the main modal for destructive actions.

**New features implemented:**

| Feature | Implementation |
|---|---|
| Hard delete button | Red button on each row; `__umHardDelete(username)` → `showConfirmModal()` → `DELETE /users/{u}?permanent=true` |
| Reactivate button | Green button on deactivated rows; `__umSetActive(u, true)` → `PUT /users/{u}/active {active:true}` |
| "Deactivated" badge | Red-pill badge + row opacity 0.65 + muted background for deactivated users |
| Inline email edit | Click `.um-email-display` span → shows input; Enter commits (`PUT /users/{u}/email`), Esc cancels, blur commits |
| Bulk-op toolbar | Checkbox column + header select-all; toolbar surfaces when `selected.size > 0` with Deactivate/Activate/Delete buttons |
| Bulk delete confirmation | `__umBulk('delete')` → confirmation modal showing count + usernames |
| Audit log viewer | Second tab; fetches `/admin/audit-log?limit=200`; table w/ timestamp, actor, action (styled as code), target, success tick/cross, expandable details |
| Self-action protection UX | `isSelf` detection via `currentUsername` populated from `/auth/verify` on open; type-dropdown, deactivate, hard-delete buttons disabled on own row |
| Loading states | `loadUsers()` and `loadAuditLog()` write "Loading…" before fetch |
| Error surfacing | `showStatus()` with color-coded success/error/info banners, 5s auto-dismiss |
| Inline email validation | `EMAIL_RE` regex; create-user form shows `#um-new-email-error` below input; inline email edit shows status banner on invalid |

**AC verification — code inspection:**

All 12 ACs are **implementation-covered** per code review. Each
AC maps to specific code paths listed above.

| AC | Code path | Status |
|---|---|---|
| AC1 (delete modal + action) | `__umHardDelete` → `showConfirmModal` → `hardDeleteCommit` | ✓ coded |
| AC2 (deactivate + badge) | `__umSetActive(u, false)` + badge in `renderUsers` | ✓ coded |
| AC3 (reactivate) | `__umSetActive(u, true)` | ✓ coded |
| AC4 (inline email) | `editEmailStart/Commit/Cancel` + input onkeydown handlers | ✓ coded |
| AC5 (self-action disabled) | `isSelf = (u.username === currentUsername)` → `selfDisabledAttr` on buttons | ✓ coded |
| AC6 (audit log reverse-chron + details) | `renderAuditLog` iterates entries (newest-first from backend) + `<details>` block | ✓ coded |
| AC7 (bulk deactivate) | `__umBulk('deactivate')` → `POST /admin/bulk` | ✓ coded |
| AC8 (bulk delete w/ confirm + count) | `__umBulk('delete')` → confirm modal titled "Delete N user(s) permanently?" | ✓ coded |
| AC9 (per-user outcomes surfaced) | `bulkCommit` builds summary with success count + failure reasons from response | ✓ coded |
| AC10 (loading state) | `loadUsers` writes "Loading users…" before fetch | ✓ coded |
| AC11 (invalid email inline error) | `createUserSubmit` validates `emailRaw` with `EMAIL_RE` before fetch; shows `#um-new-email-error` | ✓ coded |
| AC12 (TB-US-010 regression) | `👥 Users` button in index.html unchanged; modal still full-viewport with body-scroll lock; create/change-type/reset-password flows unchanged | ✓ coded |

**Visual UX verification — pending operator:**

The implementer (Claude Code) **cannot** test visual UX in a
browser. All 12 ACs are measurable but need human-eye
confirmation. Specifically:

- Modal opens with "Users" tab active by default (first time);
  session-remembered tab on subsequent opens
- Checkbox column, bulk toolbar, reactivate button, hard
  delete button, inline email edit all render as described
- Confirmation sub-modal appears over the main modal, not
  underneath
- Status banners animate in and auto-dismiss
- Audit log tab renders table with expandable `<details>`
  blocks

**Operator action required:** Open
`https://tbench.weidecai.com/static/index.html`, log in as
super (admin), click 👥 Users, and run through the
feature matrix. Report any UX issues as follow-up stories.

**Minor UX design choices worth noting:**

- Reactivate button is NOT self-disabled (makes no sense to
  reactivate yourself since you'd need to be logged in,
  which requires being active).
- Select-all excludes self (checkbox in header skips the
  current user's row when bulk-selecting).
- Legacy `window.deactivateUserSubmit` global retained as a
  thin wrapper calling `setActiveSubmit(u, false)` in case
  any legacy call site exists outside the files I touched.
- Email display shows `—` when empty (not empty string);
  click to edit still works on the dash.
- Bulk delete confirmation title uses correct plural: "N
  users permanently?" (or "1 user permanently?").

**Live-service verification:**

- `node --check static/user_management.js` → clean parse
- `GET /static/user_management.js?v=20261015a` → 200, 35978
  bytes; 7 TB-US-041 markers in the fetched content
  (confirming correct file served, not stale cache)
- `GET /static/index.html` → 200
- `GET /static/training_sets.html` → 200
- `GET /static/training_runs.html` → 200

**End-to-end sync-forward status:** TB-US-017 (backend) +
TB-US-041 (frontend) completes user management v2 as a
feature. The pair is deliverable; operator can now manage
TB's user population entirely in the browser without
reaching for curl or SQL.

**No TB-US-040 overlap.** TB-US-040 (RAG consumption) and
TB-US-041 (user management UI) are independent. Both ship
in the same session but touch different code paths.

---

**Browser verification pass (2026-10-15).**

Operator walked the full test plan from
`docs/testing/tb-us-041-browser-test-plan.md` (conversation
record; not persisted to a file). All phases confirmed
working in-browser:

| Phase | Scope | Operator result |
|---|---|---|
| A | Modal open + loading state + layout | passes |
| B | Create user + inline email validation + hard delete via Actions ▾ | B1-B3 pass |
| C | Edit modal — email, type, both, no-op, cancel, invalid | C1-C7 pass |
| D | Deactivate / reactivate via Actions ▾ (folded into expanded B) | pass |
| E | Self-action protection: Actions ▾ options disabled on own row, Edit modal type-dropdown disabled on self, select-all skips self | E1-E4 pass |
| F | Hard delete + confirmation modal (cancel + confirm paths; folded into expanded B) | pass |
| G | Bulk ops: deactivate, activate, delete w/ confirmation showing count + usernames | G1-G5 pass |
| H | Audit log viewer tab: newest-first, expandable details, refresh | H1-H4 pass |
| I | Tab persistence (session-remembered last tab) | I1-I2 pass |
| J | Cleanup — final user population returned to 4 originals | pass |

**Final state:** 16 ACs fully verified. User management v2
is a complete deliverable, operator-signed-off.
