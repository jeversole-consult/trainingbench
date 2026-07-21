# TB-US-010: Add in-app user management UI for super users

**Status**: Completed
**Created**: 2026-07-21
**Author**: Jesse Eversole
**Commit hash(es)**: f7910ef

## Story

As a super user administering a TrainingBench install, I want a user
management UI accessible from the web app, so that I can create users,
change their roles, reset passwords, and deactivate accounts without
shelling into the server to run `backend/api/user_manager.py`.

## Background

The backend has always exposed a full user-management surface at
`/users` (GET, POST) and `/users/{username}/{type,password}` (PUT) and
`/users/{username}` (DELETE), all gated by `verify_super_user`. The
only client for those endpoints was the CLI in
`backend/api/user_manager.py`, which requires SSH to the box.

That gap made routine admin work — onboarding a new user, resetting a
forgotten password, taking someone's account offline — a task that
only the server operator could do. In an install where the operator
and the "admin" super user aren't the same person, or where the admin
isn't comfortable at the shell, this is a real blocker.

This story wires the existing endpoints to a browser UI. It ships as
a **modal overlay** rather than a separate page or an `index.html`
tab because:

- Admin work is transient — you dip into it, do one thing, close it —
  so a modal that leaves the surrounding page state intact matches the
  workflow better than a full page navigation.
- The overlay blocks the parent view (dimmed backdrop, body-scroll
  lock) so it's visually clear that admin actions are a distinct mode,
  not a mixed-in tab.
- A shared JS module can be included on every super-user-facing page
  without cloning HTML into each page.

## Requirements

- [x] R1: A new `static/user_management.js` module injects a modal into
      the DOM on demand and exposes `openUserManagement()` /
      `closeUserManagement()` on `window`. The module is
      self-contained (no dependency on `script.js` globals) so it can
      be included from pages that don't load `script.js`.
- [x] R2: The modal supports all five user-management operations:
      list users, create user, change user type, reset password,
      deactivate user. Each op calls the corresponding existing
      backend endpoint with the caller's session token.
- [x] R3: A "👥 Users" button appears in the header on `index.html`,
      `training_sets.html`, and `training_runs.html`. On
      `index.html` the button is hidden by default and unhidden by
      `script.js` only when the authenticated user's `user_type` is
      `super`. On the two training pages the button is always shown
      (those pages are already super-user-gated on load).
- [x] R4: The modal covers the full viewport with a dimmed backdrop
      (`z-index: 2000`) and locks `document.body.style.overflow` on
      open, so the parent page cannot be interacted with until the
      modal is closed.
- [x] R5: Backend is not modified. The five endpoints already exist
      and are `verify_super_user`-gated.

## Acceptance Criteria

- [x] AC1: Logging in as a super user and reloading tbench shows the
      green "👥 Users" button in the header on the main app,
      training_sets, and training_runs pages.
- [x] AC2: Logging in as a non-super user does NOT show the button on
      `index.html`. (The training pages already redirect non-super
      users, so button visibility there is a moot point.)
- [x] AC3: Opening the modal fetches the current user list and renders
      a table with username, type, email, status, last login, and
      action buttons.
- [x] AC4: Creating a user via the form results in a new row appearing
      in the list without a page reload. Changing a user's type via
      the dropdown, resetting their password via the prompt, and
      deactivating them via the button all round-trip to the backend
      and reflect in the refreshed list.
- [x] AC5: Attempting to deactivate the caller's own account returns
      HTTP 400 from the backend (already-enforced) and the modal
      surfaces the error inline instead of silently failing.

## Design Notes

- The module is written as an IIFE that reads `session_token` from
  `sessionStorage` and derives `API_BASE` from `window.location.origin`.
  This intentional decoupling from `script.js` is what lets
  `training_runs.html` (which has its own local `checkAuth`) use the
  same module without refactor.
- The button visibility toggle lives in `script.js` next to the
  existing `current-user-display` and `applyRoleBasedUI()` calls —
  same lifecycle point, same authenticated-user gate.
- No new backend endpoints, no schema changes, no restart required
  when deploying: this is a pure static-file change.
- Cache-bust convention: `?v=YYYYMMDDx` on the script tags. The
  parent HTML files already have `Cache-Control: no-store` from the
  middleware added in commit `270196f`, so the version suffix only
  matters for the JS files themselves.

## Out of Scope

- **Per-user random salts / bcrypt migration.** The `user_manager.py`
  module still uses a global SHA-256 salt. Fixing that is a separate
  security-hardening story flagged in the module's docstring.
- **Bulk user import / CSV upload.** Onboarding one user at a time is
  the operator workflow this UI targets.
- **User-editable profile page.** This story is admin-facing; letting
  a non-super user change their own password or email is a distinct
  feature.
- **Audit log of admin actions.** Who reset whose password, who
  deactivated whom — worth having, separate story.
- **Reactivating deactivated users from the UI.** The backend
  `UserManager` has no reactivate method today. Adding it is a small
  backend + UI story.

## Related

- Backend endpoints: `backend/api/main.py:1499-1656` (all five
  `/users` handlers, all gated by `verify_super_user`).
- CLI predecessor: `backend/api/user_manager.py` — the ops this UI
  replaces at the shell.
- `static/user_management.js` — new module.
- `static/index.html`, `static/script.js`, `static/training_sets.html`,
  `static/training_runs.html` — header button + script include.
