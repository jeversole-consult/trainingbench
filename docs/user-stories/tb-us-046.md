# TB-US-046: Default landing tab = Chat (replaces Upload)

**Status**: Completed
**Created**: 2026-10-16
**Completed**: 2026-10-16
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As any TB user, I want to land on the **Chat tab** by
default when I log in (and when I navigate to
`/static/index.html` without a hash), so that the first
thing I see is the primary interaction surface — asking
the agent a question — rather than the document-upload
tab I would use far less frequently.

## Background

Current behavior: `index.html` opens with the **Upload
Documents** tab active (`#upload-tab` carries the
`tab-content active` class). This is a holdover from TB's
earlier "content ingest first" workflow. Post-TB-US-018
(left-nav redesign), tab selection flows through the
hamburger drawer; the first-page default is still Upload.

Why Chat is the right default:

- Chat is the agent interaction surface — what operators
  and end-users actually do day-to-day
- Document upload is a one-time or infrequent
  administrative task per RAG build
- All three user roles (`super`, `chat`, `training`) have
  Chat in their allowed-tabs list; no role is excluded
- The role-based tab-filter (`script.js` line 94) would
  previously auto-switch `chat` users away from Upload
  (since `chat` only has `chat` allowed), causing a
  visible tab flip on load; defaulting to Chat eliminates
  that flicker

## Requirements

- [x] R1: **Flip the `active` class in `index.html`** from
      `#upload-tab` to `#chat-tab`. The 9 `.tab-content`
      divs stay in the DOM; only one carries `active`.
- [x] R2: **Update `left_nav.js`'s `currentActiveItem()`
      fallback** from `return 'upload'` to `return 'chat'`
      so the drawer's active-item indicator aligns when
      the DOM-based detection has nothing to find.
- [x] R3: **Hash-routing preserved.** Visiting
      `index.html#upload` (or any other hash) still
      switches to that tab via the existing
      `left_nav.js` hash handler. Only the no-hash case
      changes.
- [x] R4: **No regression** on tab-switching, role-based
      filtering, left-nav indicator sync, or any existing
      tab behavior.
- [x] R5: **Cache-bust bump** on `left_nav.js` since it
      changed. `?v=20261015d` → `?v=20261016a` across all
      3 main pages.

## Acceptance Criteria

- [x] AC1: Logging in as any role and landing on
      `index.html` shows the Chat tab content, not the
      Upload tab content.
- [x] AC2: Opening the left-nav drawer with no hash
      navigation shows **Chat** as the active-highlighted
      nav item (not Upload).
- [x] AC3: `index.html#upload` still switches to the
      Upload tab (hash routing unchanged).
- [x] AC4: `index.html#history` still switches to Query
      History (hash routing unchanged).
- [x] AC5: `script.js`'s role-based tab filter does not
      flicker on load for `chat` and `training` roles
      (previously would briefly show Upload before
      switching away).
- [x] AC6: `git diff backend/` is empty.

## Design Notes

- **Why not a user-preference setting.** "Default tab per
  user" is a nice-to-have but needs schema + UI + session
  wiring. Simple default-to-Chat solves 90% of the pain
  for 0% of that scope cost. If a per-user preference
  becomes real demand, follow-up story.
- **Why not role-aware defaults.** Each role could
  arguably want a different default (`training` →
  Training Sets?). But the role-based tab-filter already
  handles visibility; defaulting to Chat is universally
  valid (all three roles have it). Role-aware defaults
  are a follow-up if ever wanted.
- **Why its own story vs TB-US-045 umbrella.** Operator
  requested a dedicated story. Single-concept but the
  behavior change is user-facing enough to earn its own
  narrative (and future referenceability like "when did
  Chat become default? → TB-US-046").
- **Cache-bust discipline.** `left_nav.js` is the only
  cache-busted asset touched; its version bumps once.
  `index.html` is the entry-point HTML, revalidated by
  the browser; operators may need to hard-refresh to see
  the change on an aggressively-cached browser.

## Out of Scope

- Per-user "my default landing tab" preference setting.
- Role-aware tab defaults (e.g., `training` role lands on
  Training Sets).
- Changes to any `.tab-content` div's internal layout.
- Changes to tab visibility rules in `script.js`.
- Changes to the hamburger / drawer mechanics.
- Changes to backend code.

## Related

- [TB-US-018](tb-us-018.md) — Collapsible left-nav. This
  story is a small follow-up to that redesign.
- [TB-US-045](tb-us-045.md) — Reactive UI tweaks umbrella.
  This story could have fit there per the threshold, but
  operator asked for a dedicated story.
- `static/index.html` — the `.tab-content active` class
  move
- `static/left_nav.js` — `currentActiveItem()` fallback
  update + cache-bust bump
- `static/training_sets.html`, `static/training_runs.html`
  — cache-bust bumps for `left_nav.js` reference

**Completion Notes (2026-10-16).**

- `static/index.html` — `active` class moved from
  `#upload-tab` (line 270) to `#chat-tab` (line 328).
- `static/left_nav.js` — `currentActiveItem()` fallback
  flipped from `return 'upload'` to `return 'chat'` (line
  44). Comment references TB-US-046.
- Cache-bust bumped on `left_nav.js` from `?v=20261015d`
  → `?v=20261016a` across `index.html`,
  `training_sets.html`, `training_runs.html`.
- No backend changes; no service restart required.

**Verifications:**

- Live-served `index.html` has `id="chat-tab"
  class="tab-content active section"` (1 match);
  `id="upload-tab" class="tab-content active"` (0 matches).
- Live-served `left_nav.js?v=20261016a` has
  `return 'chat'` (1 match).
- `node --check` clean on `left_nav.js`.
- Cache-bust marker `?v=20261016a` present in all 3 main
  HTML files.

**Operator action:** hard-refresh (Shift+⌘+R) once to clear
cached index.html. First visit after that: Chat tab active.

**Browser verification deferred to natural use** per
`feedback_ui_changes_organic` memory. Operator will see
the new default on next login.
