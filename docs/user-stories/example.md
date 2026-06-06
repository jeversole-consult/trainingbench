# TB-US-EXAMPLE: Add admin UI for user management

<!--
This file is the worked example that accompanies template.md. It shows
how a real user story reads when filled in. When you write your own
story, copy template.md (not this file) and adapt.

Note the ID is "TB-US-EXAMPLE" rather than a real number — when this
story is picked up for implementation it should be renamed to the next
available number (likely TB-US-001).
-->

**Status**: Proposed
**Created**: 2026-06-06
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a super-user administrator of a TrainingBench deployment, I want a
UI to manage users, so that I can create, modify, and remove user
accounts without having to issue API calls by hand.

## Background

TrainingBench already has a full backend user-management API:

- `GET    /users`                    — list users
- `POST   /users`                    — create
- `PUT    /users/{username}/type`    — change role
- `PUT    /users/{username}/password`— reset password
- `DELETE /users/{username}`         — deactivate

All five endpoints are gated to super users via `verify_super_user`
(see `backend/api/main.py:380`). The `UserManager` class
(`backend/api/user_manager.py`) backs them with the corresponding
methods.

What's missing is a frontend. A super user logging in today has no
clickable way to provision a second user — they have to log in via the
API, mint a token, and issue curl requests. That's a rough edge for an
OSS research platform aimed at small teams of researchers, and a
barrier to evaluating the platform.

## Requirements

- [ ] R1: A new "Users" tab in the main UI, visible only when the
      logged-in user has `user_type == "super"`. Other roles do not
      see the tab.
- [ ] R2: The Users tab lists all users in a table: username, role,
      email, created date, last-login date, active/inactive flag.
- [ ] R3: A "Create user" form on the same tab that captures username,
      password, role (one of super / chat / training), and email.
      Submission calls `POST /users`.
- [ ] R4: Inline controls per user to change role (calls
      `PUT /users/{username}/type`).
- [ ] R5: Inline control to reset a user's password
      (`PUT /users/{username}/password`). The new password is
      generated client-side or entered by the admin, then shown once
      so the admin can hand it off.
- [ ] R6: Inline control to deactivate (delete) a user
      (`DELETE /users/{username}`), behind a confirmation dialog.
- [ ] R7: All API errors (validation, conflicts, network) surface
      visibly in the UI rather than failing silently in the console.

## Acceptance Criteria

- [ ] AC1: A user with role `super` sees the Users tab after login;
      users with role `chat` or `training` do not see it, even if
      they manually navigate to its URL fragment.
- [ ] AC2: From the Users tab, an admin can create a new user, see
      that user appear in the list, log out, log in as the new user,
      and see role-appropriate UI.
- [ ] AC3: An admin cannot delete their own account from the UI (the
      delete control is disabled or absent for the logged-in row).
- [ ] AC4: Attempting to create a user with a duplicate username
      surfaces the backend's 409 error message in the UI.
- [ ] AC5: Password reset shows the new password to the admin exactly
      once (not stored, not logged client-side).

## Design Notes

- Reuse the existing tab styling and the `tabPermissions[userType]`
  pattern in `static/script.js:99` to gate visibility.
- Confirmation dialogs for destructive actions follow the existing
  modal pattern used elsewhere in `static/index.html`.
- Avoid building a new state-management library for this — fetch-on-
  demand and re-render the user list after each mutation is fine at
  the scale this is meant for.
- The "cannot demote oneself if last super user" safety check would be
  nice but is **out of scope** here (see below).

## Out of Scope

- Demote-self protection (the last-super-user check). Belongs in a
  follow-up story that may also cover invariants enforced server-side.
- Per-user random password salts. Tracked separately; an architectural
  fix to `_hash_password` rather than a UI change.
- Bulk user import / CSV upload.
- Audit log of user-management actions.

## Related

- backend/api/main.py:1468-1591 — existing endpoints
- backend/api/user_manager.py — UserManager class and methods
- static/script.js:88-260  — existing role-based UI customization
