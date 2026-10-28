# TB-US-045: Reactive UI tweaks — rolling umbrella

**Status**: In Progress
**Created**: 2026-10-16
**Author**: Jesse Eversole
**Commit hash(es)**: <per-tweak hash in each entry below>

## Story

As the operator of TrainingBench, I want a single rolling
umbrella story to collect **small UI/UX tweaks surfaced
reactively during feature-testing or ad-hoc use** — rather
than spawning a new TB-US-NNN per tweak — so that the
backlog stays clean, the audit trail is one scrollable
history, and operators landing here see "what changed
recently" without hunting through N micro-stories.

## Background

Pattern established in this session (2026-10-16) after
the operator asked how incremental UI changes are being
captured. Earlier memory
(`feedback_ui_changes_organic`) said "ship UI work and
collect improvements reactively," but didn't specify a
tracking vehicle. Six tweaks shipped untracked before this
umbrella opened; this story is both (a) the retroactive
home for those tweaks and (b) the forward-looking catch-all
for future reactive tweaks.

## Threshold — when a tweak lands here vs its own story

| Change shape | Vehicle |
|---|---|
| Small single-concept tweak (default state flip, icon added, button repositioned, inline copy edit, bounded one-function refactor) | **This umbrella** |
| Multi-file coordinated small change that's still single-concept (e.g., move a button across 3 pages) | **This umbrella** |
| Full component redesign, new feature surface, architectural refactor, multi-page coordinated redesign | **Its own story** |

Pattern references:
- TB-US-018 + TB-US-042 — architectural (left-nav refactor;
  white-theme refresh). Their own stories.
- TB-US-041 Actions-dropdown reopen — reopened an existing
  umbrella rather than spawning. Umbrella-adjacent pattern.
- This story — rolling catch-all when no obvious umbrella
  exists.

## Requirements

- [ ] R1: **Each tweak is a dated entry** in §Completion
      Notes below. Format: date + operator ask (verbatim or
      summarized) + what changed + files touched +
      verification done.
- [ ] R2: **Retroactive capture** — the 6 tweaks shipped
      earlier this session (2026-10-16) are documented in
      §Session 2026-10-16.
- [ ] R3: **Forward-looking** — future tweaks land here
      until the pattern shifts (new focused UI story opens
      and starts folding tweaks into itself).
- [ ] R4: **Umbrella closes under one of two conditions:**
      (a) a successor umbrella opens and takes over, or (b)
      an architectural UI story opens that absorbs
      remaining pending tweaks. Not closed by reaching N
      entries.

## Acceptance Criteria

- [ ] AC1: §Completion Notes documents every tweak
      shipped against this umbrella with the format from R1.
- [ ] AC2: `feedback_ui_changes_organic` memory
      references this story as the vehicle for reactive
      tweaks.
- [ ] AC3: Future tweaks surfaced during feature-testing
      of other stories (e.g., operator notices a UI issue
      while exercising a TB-US-NN feature) land here, not
      spawning a new story.
- [ ] AC4: When this umbrella closes, its §Completion
      Notes serves as a scrollable changelog of
      incremental UI/UX changes to TB.

## Design Notes

- **Why a story, not a `CHANGELOG.md`.** Stories are TB's
  documentation history (per the
  `principle_stories_are_documentation` memory). A story
  format naturally integrates with the backlog, the
  notification pipeline, and the completion-notes
  convention. A separate CHANGELOG duplicates the
  mechanism.
- **Why one umbrella, not three (per surface — docs
  page, main app, admin modal).** Operator cognitive
  overhead. One umbrella is scannable; three means
  "which umbrella does this fit?"
- **Why no AC verification bar.** Tweaks are small; each
  entry's verification is captured inline. No separate
  AC for "does the hamburger close-arrow work" — the
  tweak-entry has that evidence.
- **In-flight tweaks stay visible via BACKLOG.md.** This
  story's row carries a 1-line summary of the most
  recent tweak so operators scanning the backlog see
  recent movement.

## Out of Scope

- Architectural UI redesigns (those get their own
  stories).
- Backend changes (even those triggered by UI work;
  belong in a backend-focused story).
- Changes that need operator design review before
  execution (those get their own story with explicit
  scope + ACs).
- Branding tweaks (per the deferred-branding memory).

## Related

- `MEMORY.md → feedback_ui_changes_organic` — governs
  reactive-tweak workflow; references this story.
- `MEMORY.md → feedback_umbrella_stories` — the
  umbrella pattern this story instantiates.
- `MEMORY.md → principle_stories_are_documentation` —
  why we track in a story vs a separate CHANGELOG.
- [TB-US-018](tb-us-018.md) — collapsible left-nav
  (the nav that §Pending Next entry #1 extends).
- [TB-US-042](tb-us-042.md) — white-theme refresh (the
  theme that header buttons currently live in).
- [TB-US-041](tb-us-041.md) — user management modal (one
  surface that may accumulate tweaks).

---

## Completion Notes

### Session 2026-10-16 — retroactive capture (6 tweaks)

**Tweak 1 — docs.html sidebar: default-collapsed.**
- Operator ask: *"on the docs page the left nav defaults
  to expanded, i need it to default to compacted"*
- Change: `renderSidebar()` gained a `collapsedByDefault`
  parameter (default `true`). Initial load calls with
  `true` → all dir groups render with the existing
  `.collapsed` class. Filter path calls with `false` so
  search matches stay visible.
- Files: `static/docs.html` (3 locations: function
  signature, dir-group markup, filterFiles callsite)
- Verification: live-fetched docs.html; counted
  `collapsedByDefault` refs; opened docs page and
  observed collapsed-by-default behavior.

**Tweak 2 — TOC + anchors on `agent-architecture.md`.**
- Operator ask: *"can you put a table of contents in the
  architecture document and link the 1 tier headings to
  the sections?"*
- Change: added TOC block near top (after metadata
  blockquotes); added `<a id="sec-N"></a>` anchors
  before each of 14 `## N.` headings.
- Files: `docs/design/agent-architecture.md`
- Verification: counted 14 anchors + 14 TOC links in the
  live-served content.

**Tweak 3 — TOC + anchors on `sweet-spot-architecture.md`.**
- Operator ask: *"i need you to do a table of contents
  for the sweetspot architecture doc as well just like
  the architecture doc"*
- Change: same pattern as tweak 2; 12 anchors + 12 TOC
  entries.
- Files: `docs/design/sweet-spot-architecture.md`
- Verification: same as tweak 2 (counts match).

**Tweak 4 — Docs landing page (`docs/README.md`) +
auto-load wiring.**
- Operator ask: *"on the main docs page when i first
  click to get there it just says Select a markdown
  file from the sidebar to view it here. that is clunky
  at best. needs a better docs landing page"*
- Change: (a) created `docs/README.md` as a curated
  landing with sections, important links, current
  state, how-to-navigate; (b) modified `loadFileList()`
  in docs.html to auto-load `docs/README.md` on initial
  render if present (defensive — falls back to
  placeholder if missing).
- Files: `docs/README.md` (new), `static/docs.html`
- Verification: live GET `/docs/content?path=docs/README.md`
  returns 3178-char content; auto-load hook present in
  served docs.html.

**Tweak 5 — Exclude `README.md` + `BACKLOG.md` from docs
page.**
- Operator ask: *"when i land on the doc homepage i see
  3 links to .md files, install, readme, and backlog.
  i'm not sure the backlog is meant for this page.
  backlog is a project management issue and this page is
  current documentation. the readme file is PEFT
  demonstration research. that doesn't belong at the
  top."*
- Change: added `EXCLUDE_FILES = {'README.md',
  'BACKLOG.md'}` to the `/docs/list` endpoint logic.
  Exclusion applies **only to root-level** files —
  per-folder READMEs stay visible.
- Files: `backend/api/main.py` (one function; service
  restart required and performed)
- Verification: live `/docs/list` call confirms only
  `INSTALL.md` appears at root.

**Tweak 6 — Nested-tree sidebar rendering.**
- Operator ask: *"why /math is in the title of datasets
  and training folder doesn't make sense. these are
  high level folder that should have subject matter
  data categorized under their heading."*
- Change: `renderSidebar()` refactored to build a nested
  tree from flat paths and render recursively.
  `datasets/math` now shows as `📂 datasets > 📂 math`;
  `openclaw/skills/trainingbench` shows three levels
  deep. Added CSS rule for nested-dir-group padding.
- Files: `static/docs.html` (renderSidebar function +
  new `.dir-files .dir-group` CSS rule)
- Verification: live-fetched docs.html; confirmed
  `renderNode` function + nested-indent CSS rule.

---

### Session 2026-10-17

**Tweak 7 — Hamburger drawer close-affordance.**
- Operator ask (2026-10-16, re-raised 2026-10-17): *"when
  i click on the hamburger and it expands, i don't have a
  back arrow to collapse the menu. if i click on the
  selection it will collapse, but that is not intuitive
  so i need a back arrow to collapse the expanding left
  nav."*
- Change: added a header row at the top of the drawer
  containing a `← Close` button. Clicking it calls
  `closeNav()`. Existing close methods preserved (Esc,
  backdrop click, item click). Drawer's old `padding:
  60px 0 20px 0` reduced to `0 0 20px 0` since the new
  header-bar occupies the top area that previously held
  blank space for the overlapping hamburger button.
  Hover affordance on the Close button (subtle gray
  background on hover). Exposed `window.__tbNavClose`
  for the inline onclick.
- Files: `static/left_nav.js`
- Cache-bust: bumped on all 3 main pages from
  `?v=20261016a` → `?v=20261017a` (index.html,
  training_sets.html, training_runs.html).
- Verification: `node --check` clean; live-served
  `left_nav.js?v=20261017a` has 3 Tweak-7 markers and
  the "Close" button text in-place; all 3 HTML files
  reference the new version.

**Tweak 8 — Move Logout button to drawer bottom.**
- Operator ask (2026-10-16, executed 2026-10-17): *"what
  if i want to move the logout button in the upper right
  corner to the bottom of the left nav as is done with
  many other platforms."*
- Change: converted drawer to flex-column; added a
  `.tb-nav-footer` region pinned at the bottom with a
  "🚪 Logout" item separated by a `border-top`. Clicking
  invokes `window.__tbNavLogout()`, which dispatches to
  the page's existing `logout()` definition (script.js
  on index/training_sets; inline function in
  training_runs.html). Fallback cleanup if no page-level
  logout is defined. Removed the Logout button + its
  listener from all 3 page headers.
- Pre-existing nuance preserved (not fixed here):
  `training_runs.html`'s own `logout()` does lighter
  cleanup than `script.js`'s version (no POST to
  `/auth/logout`, no training-state localStorage clear).
  Pre-dates this story. If operator wants unification,
  worth a separate tweak.
- Files: `static/left_nav.js`,
  `static/index.html`, `static/training_sets.html`,
  `static/training_runs.html`
- Cache-bust bumped `?v=20261017a` → `?v=20261017b` on
  all 3 main pages
- Verification: `node --check` clean; served
  `left_nav.js?v=20261017b` has 3 Tweak-8 markers +
  door icon; `id="logout-btn"` / `id="logoutBtn"`
  absent from all 3 pages (0 matches each); all pages
  return 200.

**Tweak 9 — Remove redundant Training Sets button from headers.**
- Operator ask (2026-10-17): *"it appears that the
  training sets button is redundant and is on the left
  nav, can you verify and if that is the case remove the
  top right training sets button."*
- Verification: confirmed. `#training-sets-btn` in
  `index.html` header + `Training Sets` link in
  `training_runs.html` header both duplicate the left-
  nav drawer's `🎓 Training Sets` item. Operator asked
  about the index.html case specifically; I removed
  both for consistency since both carry the same
  redundancy.
- Change:
  - `static/index.html` — `#training-sets-btn` button
    markup removed (replaced with HTML comment)
  - `static/training_runs.html` — Training Sets `<a>`
    link in header-actions removed (replaced with HTML
    comment)
  - `static/script.js` — 3-line dead-code block that
    showed/hid `#training-sets-btn` based on role removed
    (replaced with comment pointer)
- NOT removed (also redundant but kept pending operator
  decision):
  - `training_runs.html` header's "Main App" link to
    index.html — technically redundant with any index
    nav-item in the drawer, but different semantic
    (home vs specific tab). Flagged in response; not
    removed.
- Files: `static/index.html`, `static/training_runs.html`,
  `static/script.js`
- Cache-bust: `script.js` bumped from `?v=20261015d` →
  `?v=20261017a` on both pages that reference it
  (`index.html`, `training_sets.html`). Also upgraded
  `training_sets.html`'s script.js reference from
  no-cache-bust to `?v=20261017a` for consistency.
- Verification: `node --check` clean on script.js;
  zero live JS refs to `training-sets-btn` or
  `trainingSetsBtn`; all 3 pages return 200; served
  `script.js?v=20261017a` has the dead block gone.

**Tweak 10 — Remove "Main App" link from training_runs.html.**
- Operator ask (2026-10-17): *"remove it, it is not
  needed and confusing for that page."*
- Context: Tweak 9 flagged this link as redundant but
  conservatively kept. On re-examination with TB-US-046
  (Chat as default tab) in play, drawer → any index-tab
  item lands on index.html same as the Main App button;
  the semantic distinction ("home" vs "specific tab")
  no longer meaningful. Operator confirmed removal.
- Change: `<a href="/static/index.html">Main App</a>`
  removed from `training_runs.html` header; replaced
  with a descriptive HTML comment.
- Files: `static/training_runs.html` only
- Cache-bust: not needed — training_runs.html is an
  entry-point HTML (browsers revalidate on each visit);
  no other asset changed
- Verification: zero `href="/static/index.html"`
  references remain in the file; live-fetched
  `/static/training_runs.html` returns 200; the only
  "Main App" string match is the descriptive comment
  I left in place.

**Tweak 11 — "Manage" nav icon: 📁 → 📑.**
- Operator ask (2026-10-17): *"there is a manage selection
  on the left nav that uses a folder icon. it is not a
  folder, it links to the manage documents page."*
- Context expanded over the turn into a broader
  architectural discussion (two-tier System vs Agent;
  drawer as agent-contextualized workspace). Those
  structural changes are captured in TB-US-044's design
  doc; this tweak is the minimal cosmetic fix that doesn't
  commit to any drawer restructure. Executed in isolation
  per operator's "capture it + ship the icon fix"
  direction.
- Change: `NAV_ITEMS[manage].icon` changed from `📁`
  (folder) to `📑` (bookmarked documents) in
  `static/left_nav.js`. Label `Manage` unchanged for now
  — the full renaming to "Manage Documents" waits for the
  drawer restructure driven by TB-US-044.
- Files: `static/left_nav.js`, cache-bust bumped on
  `index.html`, `training_sets.html`, `training_runs.html`
  from `?v=20261017b` → `?v=20261017c`
- Verification: live-fetched `left_nav.js?v=20261017c`
  contains the 📑 marker; zero `icon: '📁'` refs remain;
  `node --check` clean.

**Tweak 12 — Agent-selector widget icon: 📂 → 🤖.**
- Operator ask (2026-10-22, immediately after live-testing TB-US-048):
  *"the folder icon on the Current Agent widget needs to change
  to something that looks either like a robot or use the icon of
  the runner currently used for training runs."*
- Lean: 🤖 (robot) — semantically ties to "agent" and matches
  the agent-management modal header icon.
- Change: `static/left_nav.js` agent-selector widget inner span
  updated from 📂 to 🤖.

**Tweak 13 — Top-bar DB chip replaced with Agent chip.**
- Operator ask (2026-10-22): *"my thinking is that where the
  default database is displayed on the horizontal bar should be
  replaced with the default agent."* Rationale: the drawer applies
  to the current agent; the top-bar context indicator should
  reflect the primary mental-model entity.
- Change:
  - `static/index.html` header: removed `#header-db-chip` + its
    `#database-selector` dropdown; added `#header-agent-chip`
    with amber-tinted styling (`🤖 Agent: <strong>{name}</strong>`),
    visible to all authenticated users (not super-only).
  - `static/script.js`: removed the dead `headerDbChip` show-
    logic. Added `syncHeaderAgentChip()` helper that reads
    `sessionStorage.tb_current_agent` on load and on the
    `tb:agent-changed` CustomEvent fired by the drawer.
- Database switcher functionality preserved via the **Databases**
  tab in the drawer; the only change is the top-bar display
  (not the underlying feature).

**Tweak 14 — "Manage" nav label → "Documents".**
- Operator ask (2026-10-22): *"the manage widget is not a general
  document management function so that should be titled Documents
  rather than Manage."*
- Change: `NAV_ITEMS[manage].label` → `Documents` in
  `static/left_nav.js`. Tab ID `manage` kept so inner
  `#manage-tab` + the h2 "Manage Documents" page content remain
  consistent; the nav-level label is the only operator-visible
  change in the drawer.

**Cache-bust bumped on all 3 touched static files:**
`?v=20261022a` → `?v=20261022b` on `left_nav.js` and `script.js`
across `index.html`, `training_sets.html`, `training_runs.html`.

**Tweak 15 — Agent-management modal action buttons didn't look clickable.**
- Operator ask (2026-10-22, in-session browser test of TB-US-048):
  *"the agent management dialog shows grayed out button for the
  default agent, i don't think that is right."*
- Diagnosis: the Rename button was styled with
  `background: #f5f5f5; border: 1px solid #ddd` — a classic
  "disabled" look. Operator read it as unavailable even though
  it was clickable. The Retire button had an orange tint and
  looked fine. The Reactivate button (shown only for retired
  agents) had a pale-blue tint and would have the same problem.
- Change: `static/agent_management.js` action buttons rewritten
  with outlined-button style — white background, colored
  (amber for Rename / red-orange for Retire / blue for
  Reactivate) 1px border + matching text color + hover
  fill-in. Semantics preserved (same handlers, same confirm
  dialogs, same audit paths); only the visual affordance
  changed.
- Cache-bust bumped: `agent_management.js?v=20261022a` →
  `?v=20261022b` across `index.html`, `training_sets.html`,
  `training_runs.html`.

**Tweak 16 — Agent-management modal close button was blank.**
- Operator ask (2026-10-22): *"the upper right close box should
  have an X in it. it is blank"*
- Diagnosis: button content was `×` (U+00D7 multiplication sign)
  at `font-size: 1em`. Multiplication sign is tiny / thin in
  most system fonts; combined with no explicit color (black
  default) and short line-height, the glyph was invisibly small
  or font-missing on operator's environment.
- Change: content → `&#x2715;` (BALLOT X U+2715, explicitly a
  close/dismiss glyph) via HTML entity so parsing is
  unambiguous; `font-size: 1.4em`; `line-height: 1`;
  `color: #555`; `font-weight: 600`; `title="Close"` tooltip.
- Cache-bust bumped: `agent_management.js?v=20261022b` →
  `?v=20261022c` across all 3 pages.

**Tweak 17 — TB-US-059 welcome banner never rendered.**
- Operator ask (2026-10-22): *"i'm on the home landing page of
  Training Bench and i have no idea what you are talking about"
  / "i see none of this"*
- Diagnosis: scope bug in TB-US-059 wiring. `script.js` DOMContentLoaded
  handler contained `currentUser.welcome_banner_dismissed =
  !!data.welcome_banner_dismissed; renderWelcomeBanner();` —
  but `data` is a local variable inside `checkAuth()`, not
  accessible in the handler. The `ReferenceError` silently aborted
  the init block including the `renderWelcomeBanner()` call that
  followed. Other pieces (agent chip, user chip) rendered fine
  because they ran before the bad line.
- Fix: moved the flag assignment inside `checkAuth()` where
  `data` is in scope. `renderWelcomeBanner()` in DOMContentLoaded
  now reads from the already-populated `currentUser` global.
- Cache-bust bumped: `script.js?v=20261022c` → `?v=20261022d`.

**Tweak 18 — Agent added to Chat tab's workflow strip (upfront view).**
- Operator ask (2026-10-22): *"in the view workflow horizontal
  with the list from left to right we need to put the agent name
  to the far left, it is ok to leave the DB, Model, and Adapter
  that belong to the agent so the user can see those right there.
  this gives the user an upfront view."*
- Change: added `Agent: <span id="current-agent-label">` as the
  first entry in the amber-outlined workflow strip in
  `static/index.html` (above the chat input, inside `#chat-tab`),
  followed by a `|` separator. Reads from the same
  `sessionStorage.tb_current_agent` the drawer and top-bar
  chip use. `syncHeaderAgentChip()` in `static/script.js`
  extended to update both the header chip label AND the
  workflow-strip label in one call so a single agent switch
  updates all three visible agent indicators (drawer selector,
  top-bar chip, workflow strip).
- Cache-bust bumped: `script.js?v=20261022d` → `?v=20261022e`.

**Tweak 19 — Users entry moved to drawer-footer Admin group (starts admin-tier surface).**
- Operator ask (2026-10-22): *"the user management button
  belongs under an admin function and should be moved off the
  horizontal top bar to an admin function just above logout at
  the bottom of the left nav."*
- Context: operator asked which story owns "admin independent
  functions from the agent" — the answer is **none yet**.
  TB-US-044 Q11 was the design decision for the admin surface
  (lean: top-bar avatar menu, deferred). Tweak 8 moved Logout
  to the drawer footer; this tweak starts the drawer-footer
  **Admin group** above Logout, reshaping TB-US-044 Q11's
  resolution from avatar-menu toward drawer-footer-group.
- Change:
  - `static/left_nav.js`: new `#tb-nav-admin-group` container
    inside the drawer footer, between the footer border and
    Logout. Contains a small-caps "ADMIN" label + a `👥 Users`
    item that calls `openUserManagement()`. Hidden by default;
    `display: none`.
  - `static/script.js`: existing super-user guard that showed
    `#user-mgmt-btn` now toggles `#tb-nav-admin-group`
    visibility instead. Super-only.
  - `static/index.html`: removed the top-bar `👥 Users`
    button; left a TB-US-045 Tweak 19 comment in its place for
    future readers.
- Pattern established: future admin items (API keys,
  system config, audit log viewer, etc.) land in
  `#tb-nav-admin-group` as additional `.tb-nav-admin-item`
  divs. If the group grows past ~3-4 items, this becomes a
  candidate for its own story (operator open question — see
  TB-US-048 completion notes handoff).
- Cache-bust: `left_nav.js?v=20261022b` → `?v=20261022c`,
  `script.js?v=20261022e` → `?v=20261022f`.
  Bumped on all 3 pages (index, training_sets, training_runs).

**Tweak 20 — Admin group collapsed to a single dropdown entry.**
- Operator ask (2026-10-22, after TB-US-063 ship): *"admin
  should be the single listing on the left nav and for now
  put in a dropdown with the two selections where each on
  goes to a management function."*
- Change: `static/left_nav.js` admin footer group restructured.
  Was: small-caps "ADMIN" label + 2 always-visible items
  (`👥 Users`, `🔑 API Keys`) = 3 drawer lines visible.
  Now: 1 collapsed trigger line (`⚙️ Admin ▼`) that toggles
  a nested dropdown containing both sub-items (indented
  44px left-padding, slightly muted font, grey background
  tint `#F5F5F5` for group affordance). Caret flips ▼↔▲
  on toggle; `aria-expanded` kept in sync.
- Pattern: future admin items (System config, Audit viewer)
  add as `.tb-nav-admin-subitem` divs inside
  `#tb-nav-admin-dropdown` — same indentation, same hover,
  same super-only gating via container visibility.
- Cache-bust: `left_nav.js?v=20261022d` → `?v=20261022e`
  on all 3 pages.

**Tweak 21 — User management modal was behind the drawer.**
- Operator ask (2026-10-22): *"when you click on users the
  user management popup is dimmed, but if you click on it
  the left nav drops off and the popup goes bright. this is
  not the behavir of the api keys management popup which
  pops up ready to go."*
- Diagnosis: `user_management.js` was built before the
  drawer existed (TB-US-010 era) and its modal uses
  `z-index: 2000`. Drawer backdrop is `2040`, drawer is
  `2060`. So the user-mgmt modal literally rendered BELOW
  the drawer stack — the backdrop sat over it, giving the
  "dimmed" look. Clicking the dimmed modal area was actually
  clicking the backdrop, which triggers `closeNav()` — so
  the drawer closed and the modal "went bright".
  The newer `agent_management.js` (TB-US-048) and
  `api_key_management.js` (TB-US-063) both use `z-index:
  3000` and pop cleanly on top.
- Fix: bump `user-mgmt-modal` from `2000` → `3000` matching
  the newer admin modals. Sub-modals (`um-confirm-modal`,
  `um-edit-modal`) bumped from `2100` → `3100` to preserve
  their stacking above the parent.
- Cache-bust: `user_management.js?v=20261015d` →
  `?v=20261022a` across all 3 pages.

**Tweak 22 — In-drawer dropdowns persisted their expanded state across drawer close/reopen.**
- Operator ask (2026-10-22): *"when the left nav opens and
  then you click on a drop down then you close the left nav
  and reopen the drop down is still expanded down even
  though the Chat widget is highlighted."*
- Change: `closeNav()` in `static/left_nav.js` now calls
  `_collapseDrawerDropdowns()` which hides the agent-
  selector dropdown AND the admin-group dropdown, resets
  their carets to ▼, and clears `aria-expanded` on the
  admin trigger. Drawer re-opens in a clean state every
  time.
- Applied to both drawer dropdowns (agent + admin), not
  just admin, for consistency. The nav item active-
  indicator (amber border-left on Chat / current tab)
  is unaffected — it's set from the DOM's `.active` class,
  not from any dropdown state.
- Cache-bust: `left_nav.js?v=20261022e` → `?v=20261022f`
  on all 3 pages.

### Pending (no entries right now — add here when a new reactive tweak is proposed)
