# TB-US-011: Ownership-based training-set access for training-role users

**Status**: Completed
**Created**: 2026-07-21
**Author**: Jesse Eversole
**Commit hash(es)**: c24ab87

## Story

As a training-role user, I want to create, view, and manage the
training sets I authored, so that I can produce fine-tuning data
without needing an admin to run every operation for me, and without
seeing training sets that belong to other training users.

## Background

Training-role users exist specifically to generate training data:
they enter questions in the chat, rate model responses, and those
ratings feed the training-set pipeline. Today, every path from those
ratings to an actual training set is gated behind `verify_super_user`
in `backend/api/main.py:1703-2035`:

- `GET /training/sets` — super only
- `GET /training/sets/{id}` and `/data` — super only
- `POST /training/sets` (manual create) — super only
- `PUT /training/sets/{id}` — super only
- `DELETE /training/sets/{id}` — super only
- `POST /training/sets/{id}/clone` — super only
- `POST /training/sets/from-query-log` — super only
- `POST /training/sets/from-ratings` — super only

That means a training user has no way to build or even see a training
set from their own ratings — every rating they submit disappears into
a table only super users can pull from. The workflow the training
role is named after is unreachable to that role.

Compounding the confusion, the "🎓 Training Sets" button in the header
of `static/index.html:257` is unconditionally visible to every
authenticated user. A chat, standard, or training user can click it,
land on `training_sets.html`, and hit a wall of 403s.

This story wires ownership-based access: training users see and act on
training sets where `created_by == their username`, and only those.
Super users continue to see and manage everything. Non-training,
non-super users lose access to the button and the page entirely.

## Requirements

- [x] R1: Backend read endpoints for training sets accept
      training-role callers. `GET /training/sets` returns only the
      caller's own sets when the caller is a training user; server
      ignores or overrides any client-supplied `created_by` filter for
      those callers. `GET /training/sets/{id}` and `/data` return 404
      (not 403 — no ownership leak) when a training user requests a
      set they don't own.
- [x] R2: Backend write endpoints for training sets accept
      training-role callers, but only against sets they own. `POST
      /training/sets` accepts training callers (created_by comes from
      the session, not the request body). `PUT`, `DELETE`, `clone` on
      `/training/sets/{id}` succeed for super users and for training
      users who own the target set; return 404 otherwise (same
      no-leak rule as R1).
- [x] R3: `POST /training/sets/from-ratings` accepts training callers,
      with the caller's own username server-forced into the
      `username` filter. A training user cannot build a training set
      from another user's ratings, regardless of what they submit.
- [x] R4: `POST /training/sets/from-query-log` accepts training
      callers, with the caller's own username server-forced into
      `filters['username']` before the manager is invoked. Any
      client-supplied `username` filter is overwritten for
      training callers. Super callers retain unrestricted filter
      control. No schema change is required — master log entries
      already stamp `user_info.username` per query
      (`backend/api/query_logger.py:100-107`), and the manager
      already honors a `username` filter
      (`backend/api/training_manager.py:690`).
- [x] R5: The "🎓 Training Sets" button in `static/index.html` is
      hidden by default and unhidden by `script.js` only when the
      caller's `user_type` is `super` or `training`. Chat and
      standard users no longer see the button.
- [x] R6: `static/training_sets.html` performs a page-level user-type
      check on load. Callers whose `user_type` is not `super` or
      `training` are redirected to `/static/index.html` (same
      pattern `training_runs.html` already uses at line 762).
- [x] R7: In `training_sets.html`, training-role callers see the
      full UI (create, edit, delete, clone, from-ratings,
      from-query-log) — the backend enforces ownership, and the
      UI does not pre-hide tabs based on role. The delete button
      is currently super-gated in JS at line 947; that gate widens
      to also allow the caller when they own the set. The
      `user_type` filter dropdown on the From Query Log tab
      (`training_sets.html:560`) is hidden for training callers
      since they are pinned to their own entries server-side, so
      the dropdown would only mislead.

## Acceptance Criteria

- [x] AC1: Logged in as a training user, the "🎓 Training Sets"
      button appears in the header on `index.html`. Clicking it
      loads `training_sets.html` without a redirect.
- [x] AC2: Logged in as a chat or standard user, the "🎓 Training
      Sets" button does not appear on `index.html`, and directly
      navigating to `/static/training_sets.html` redirects back to
      `index.html`.
- [x] AC3: Two training users (say `trainer_a` and `trainer_b`) each
      create a training set. `trainer_a` sees only their set in the
      list; `trainer_b` sees only theirs. Neither sees the other's.
- [x] AC4: A super user sees both `trainer_a`'s and `trainer_b`'s
      training sets in the list, along with any super-authored sets.
- [x] AC5: `trainer_a` requesting `GET /training/sets/{trainer_b_set_id}`
      directly (via curl or dev tools) receives 404, not the set data.
      Same for `/data`, `PUT`, `DELETE`, `clone`.
- [x] AC6: A training user runs "From Ratings" with a username
      filter set to another user's name in the request body. The
      returned training set contains only the caller's own ratings
      (server-forced), and `created_by` is the caller.
- [x] AC7: A training user runs "From Query Log" with either no
      username filter or a filter naming another user. The
      returned training set contains only entries where
      `user_info.username == the caller`, and `created_by` is
      the caller.

## Design Notes

- **Ownership check is a backend concern.** Client-side hiding is
  defense-in-depth only. The tests that matter are the direct-API
  ones in AC5 / AC6 / AC7.
- **Returning 404, not 403, for cross-user access.** A 403 tells the
  caller "this set exists but isn't yours," which leaks the ID
  namespace. 404 keeps ownership private.
- **Shared helper for the ownership check.** Suggest a small
  `_authorize_training_set(user_info, ts_id) -> training_set` that
  fetches the set, and either returns it (super, or training-owner)
  or raises `HTTPException(404)`. Used by the four
  `/training/sets/{id}` handlers to keep the rule in one place.
- **`from-ratings` server-forced filter.** Simplest: overwrite
  `ratings_req.username` with `user_info['username']` when
  `user_info['user_type'] == 'training'`, before passing to the
  builder. Log a warning if the client sent a different value so
  it's visible during testing.
- **`from-query-log` server-forced filter.** Same pattern:
  before invoking `training_manager.create_from_query_log(...)`,
  if the caller is a training user, set
  `filters['username'] = user_info['username']`. This is safe
  because the master log stamps `user_info.username` on every
  entry and the manager already filters by it.
- **No schema change.** `training_sets.created_by` already stores
  the authoring username (training-set ownership). Master query
  log entries already embed `user_info.username` per entry
  (query-log ownership). Both ownership models exist in the data
  today — this story just wires enforcement.
- **The button visibility toggle** lives next to the existing
  `user-mgmt-btn` and `header-db-chip` toggles in `script.js` around
  line 267–274. Same lifecycle, same authenticated-user gate, just
  a wider role set (`super` OR `training`).

## Out of Scope

- **Shared training sets across training users.** A "share this set
  with trainer_b" flow requires a new sharing table and UI. Not this
  story.
- **Team / group ownership.** Same as above — this story is strict
  single-owner.
- **Reassigning ownership.** No "transfer created_by to another
  user" operation is added; if this comes up, separate story.
- **Rate-limiting or quota per training user.** How many training
  sets a single trainer can create — separate concern.
- **Training-user access to `/static/training_runs.html`.** Runs are
  distinct from sets. Runs page stays super-only until a separate
  story revisits it.
- **Aggregate cross-user query-log training sets for training
  users.** A training user building a set from *everyone's* query
  log (e.g., topic-based sampling across all users) is out of
  scope — the story hard-scopes training callers to their own
  entries. Super users retain the unrestricted filter path.

## Related

- `backend/api/main.py:1703-2035` — training-set endpoints being
  regated.
- `static/index.html:257` — Training Sets button losing its
  unconditional visibility.
- `static/script.js` — new visibility toggle for the button.
- `static/training_sets.html` — page-level access check + hide the
  "From Query Log" tab for training callers.
- `static/training_sets.html:947` — the delete button role gate
  that needs to also allow training-owning callers.
- TB-US-010 — the pattern for hidden-by-default header buttons
  unhidden via `script.js` (👥 Users button).
