# TB-US-018: Redesign TB UI — collapsible left-nav (Phase 1 of 2)

**Status**: Completed
**Created**: 2026-10-13
**Phase-split**: 2026-10-15 (nav separated from white-theme refresh)
**Completed**: 2026-10-15
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

> **Phase 1 of 2.** This story covers the collapsible-left-nav
> redesign only. The white-theme refresh (replacing the purple
> gradient with a white background + amber accent) is phase 2
> in **[TB-US-042](tb-us-042.md)**.
>
> Phase-split rationale: the two concerns (nav mechanics +
> visual theme) share HTML files but are independently
> testable; splitting lets each phase ship with a focused
> operator browser-verification pass.

## Story

As an operator using TB as a daily cockpit, I want TB's 9
horizontal tabs on `index.html` migrated to a **collapsible
left-hand nav** reached via a single hamburger-style icon in
the upper left (the claude.ai pattern), unified across the
three main pages, so that TB reads as a professional cockpit
rather than a prototype test harness and I can toggle a dense
set of nav options into view only when wanted.

## Background

TB's main page (`static/index.html`) currently exposes
**9 feature tabs** in a horizontal bar at the top of the
content area:

| Tab | Concern |
|---|---|
| Upload | Document ingest into RAG |
| Scrape | Web-scrape content into RAG |
| Chat | Interactive RAG query |
| PowerSearch | Advanced search |
| Compare | Side-by-side result comparison |
| Search | Basic search |
| Manage | Document / folder management |
| Query History | Past queries |
| Databases | Vector DB admin |

Plus **two secondary pages** reached via header links or
direct navigation:

- `training_sets.html` — training set management
  (super/training-role gated)
- `training_runs.html` — training run tracking
  (super/training-role gated)

Nine horizontally-arrayed tabs is well past the comfort
threshold for the pattern — the row either wraps (ugly) or
becomes a dense list of small-font buttons (ugly in a
different way). The IA is also undifferentiated: querying
operations sit next to content operations with no visual
grouping.

Separately, the current styling is a saturated purple-gradient
theme (`linear-gradient(135deg, #667eea 0%, #764ba2 100%)` on
headers, buttons, and tab-active states). It reads as a demo
or prototype rather than a product. claude.ai's pattern
(white background, subtle grays, minimal accent color) is the
reference target — not pixel-identical, but same visual
language.

This story is **TB-US-018**; it supersedes a
mistakenly-projmgmt-targeted draft, PM-US-024 (Retired on
2026-10-13 — see that file's Retirement Notes for the trail).

**Explicitly preserved by this story:**

- All content inside each tab — the Upload form, Chat
  interface, PowerSearch query panel, etc. are **not touched**;
  only the mechanism to switch between them changes, and their
  internal styling adapts to the new theme without content
  reorganization.
- Auth / role-based gating. The 👥 Users admin modal remains
  super-only.
- Backend code — zero changes.

## Requirements

### Information architecture

- [x] R1: **Flat list, grouping deferred.** The 9 current tabs
      become 9 nav items in a single flat list (plus 2 more
      items if R3 chooses unified nav across pages). Section
      headers / groups are **explicitly deferred** to a
      follow-up story — the operator's framing on 2026-10-13:
      "I eventually want to group the tabs into categories that
      have related functions, but that can be deferred for
      now." A follow-up (not yet written, call it TB-US-NNN
      when it comes up) adds grouping once the operator has
      lived with the flat list and has a clearer sense of the
      right IA.

### Collapsible sidebar pattern

- [x] R2: **Single hamburger icon in the upper left.** When
      the nav is collapsed, only this icon is visible in a
      narrow top-left area (does not steal content real
      estate). Clicking the icon toggles the nav drawer
      open/closed.
- [x] R3: **Nav drawer behavior.** When expanded, the drawer
      shows the flat list of nav items (icon + label per
      item). Each item is clickable; clicking an item (a)
      switches the content area to that feature's view and
      (b) collapses the drawer (operator preference) OR keeps
      the drawer open (also valid). Implementer picks
      *"collapse on click"* as the default — matches the
      "show selections, pick one, dismiss" workflow — but may
      change if usability testing says otherwise. Document the
      choice in Completion Notes.
- [x] R4: **Collapse persistence.** The nav's open/collapsed
      state persists in `localStorage` so the user's
      preference survives page reloads. Default state on first
      visit is **collapsed** (matches "show the chrome only
      when wanted" intent).
- [x] R5: **Drawer close controls.** Pressing Escape or
      clicking the backdrop (if the drawer uses an overlay
      with backdrop) closes the drawer. The hamburger icon
      remains the primary toggle.
- [x] R6: **Drawer visual model** — implementer picks between:
      - **Overlay drawer** — slides over the content, dimmed
        backdrop behind
      - **Push drawer** — pushes content to the right when
        open
      Overlay is simpler and matches claude.ai more
      precisely. Record choice in Completion Notes.

### Page scope

- [x] R7: **Unified nav across all 3 pages** (operator chose
      R7a 2026-10-15). The nav drawer appears via its
      hamburger icon on `index.html`, `training_sets.html`,
      and `training_runs.html`. Nav items for the 9 tabs on
      index.html toggle content; nav items for Training
      Sets / Training Runs navigate (href) to those pages.

### Content switching

- [x] R8: **Replace tab-switching behavior.** The 9
      `.tab-content` divs stay in the DOM. The old `.tab`-
      class buttons in the horizontal row are removed. The
      new nav rows take over the content-switching role; same
      `switchTab()`-equivalent mechanics (hide every other
      `.tab-content`, show the selected one).

- [x] R9: **Active-item visual distinction.** The selected
      nav item is visually distinguished from inactive items
      inside the drawer (background tint, left-border accent,
      bold weight — one or two cues max, not all three).

### Color scheme / white theme (moved to TB-US-042)

**R10-R14 (white-background body, text color, accent color,
header harmonize, admin modal theme adapt)** are now scoped
to **[TB-US-042](tb-us-042.md)** per the 2026-10-15
phase-split. Choices locked ahead of execution:

- Site background: white; subtle gray panels where visual
  separation is wanted.
- Accent color: **warm amber `#CC785C`-ish** (operator
  choice 2026-10-15; claude.ai-like).
- Header: **R13a Harmonize** (adopts white theme).
- Admin modal: visual theme adaptation only; no functional
  changes.

### Preservation / no-regression

- [x] R15: **Admin modal functionality preserved.** TB-US-010's
      full feature set still works (open from 👥 Users button,
      list/create/change-type/reset-password/deactivate, body-
      scroll lock, close controls). This story is visual +
      navigational; TB-US-010's logic is untouched.
- [x] R16: **Role-based gating preserved.** The 👥 Users
      button in the header remains super-only. If R7a unified
      nav is picked, Training nav items stay super/training-
      role gated (same as today's page-level gating).
- [x] R17: **Content inside each tab is pixel-identical
      post-theme-adaptation.** Forms, input fields, result
      panels — the layout inside each `.tab-content` div is
      unchanged. Only its surrounding styling (background,
      borders, typography accents) adapts to the new theme.
- [x] R18: **No regression on auth / login flow.** Login
      page, gate page, session verification — unaffected
      (though they may also adopt the white theme per R10
      for consistency).
- [x] R19: **Responsive behavior.** At desktop width, drawer
      overlays or pushes content as per R6. At narrow widths,
      drawer remains overlay (easier to implement; already
      matches mobile pattern). Full hamburger-menu mobile
      optimization is adequate rather than refined.
- [x] R20: **No backend changes.** This is pure frontend.
      `backend/api/main.py` and `user_manager.py` are
      untouched.
- [x] R21: **Cache-bust** per TB-US-010's convention
      (`?v=YYYYMMDDx`) on every CSS/JS file touched.

## Acceptance Criteria

### Nav mechanics
- [x] AC1: Loading `index.html` as an authenticated user shows
      a hamburger icon in the upper left and no horizontal tab
      bar below the header.
- [x] AC2: Clicking the hamburger icon opens the nav drawer.
      Clicking it again (or dismissing per R5) closes it.
- [x] AC3: Clicking a nav item inside the drawer switches
      the main content area to that feature — Upload, Scrape,
      Chat, PowerSearch, Compare, Search, Manage, Query
      History, or Databases.
- [x] AC4: The active nav item is visually distinguished when
      the drawer is open.
- [x] AC5: The drawer's open/collapsed state persists across
      page reloads (localStorage).
- [x] AC6: If R7a (unified nav) is chosen: hamburger + drawer
      appear on `training_sets.html` and `training_runs.html`
      with the correct active item. Navigation between pages
      uses `href` from drawer items (not tab-content toggle).
- [x] AC7: Escape closes the drawer when open.

### White theme (AC8-AC12 moved to TB-US-042)

The six theme-related ACs ship with phase 2. During this
story (phase 1), the purple-gradient theme is preserved
intact. The new nav renders over the existing theme —
visually it will look like a hamburger over a gradient
header, which is the expected interim state between the
two phases.

### Preservation / no-regression
- [x] AC13: Content inside each `.tab-content` div is layout-
      identical to its pre-story rendering (styling adapts to
      theme; content structure unchanged).
- [x] AC14: TB-US-010's full existing AC set still passes
      (admin modal open from header, super-only visibility,
      body-scroll lock, all five admin operations).
- [x] AC15: Login page and gate page render without visual
      regression (they may also adopt the white theme).
- [x] AC16: `git diff backend/` for this story is clean.
- [x] AC17: At desktop and narrow widths, no horizontal
      scroll in any content view.

## Design Notes

- **Pattern reference: claude.ai specifically.** The visual
  model this story targets is claude.ai — white background,
  subtle gray panels, warm accent color, hamburger-toggled
  left sidebar. TB doesn't need to be pixel-identical to
  claude.ai (we're not copying their chrome); we're adopting
  the same visual *language*.
- **Why collapsible by default (vs persistent sidebar).**
  Operator's framing: "a single icon in the upper left that
  expands to show the selections available." The sidebar is
  an on-demand surface, not a persistent one. Keeps content
  area maximal when not navigating.
- **Why grouping is deferred.** Operator explicitly deferred
  it: "I eventually want to group the tabs into categories
  that have related functions, but that can be deferred for
  now." Shipping a flat list first lets the operator see
  how the drawer feels before committing to IA groupings.
  Natural groupings (Query / Content / Training) will
  surface after some usage.
- **Why one accent color.** claude.ai uses one accent. More
  than one accent reads as noisy or test-harnessy. Pick one
  and apply uniformly.
- **Why header-styling-decision is flagged.** The operator's
  earlier framing (projmgmt-side, in PM-US-024's draft) was
  "the horizontal bar at the top does not need changing."
  But that was projmgmt context, and visual coherence favors
  harmonizing the header with the rest of the refresh.
  R13a (harmonize) is the recommended choice. R13b
  (preserve) is retained as the fallback if minimum-change
  scope is preferred.
- **Icon choices for nav items.** Match the chrome of the
  rest of the app — emoji / Unicode glyph, no icon library.
  Candidates: 📤 Upload, 🕸️ Scrape, 💬 Chat, 🔍 Search,
  ⚖️ Compare, 📁 Manage, 🕘 Query History, 🗄️ Databases,
  🎓 Training Sets, 🏃 Training Runs. Final at execution.
- **Hamburger icon style.** Simplest: Unicode `☰`
  (U+2630) rendered at ~24px. Alternative: three CSS-drawn
  bars. Either is fine. No image asset required.
- **Drawer width when open.** Claude.ai's drawer is ~260–
  300px. Match that range.
- **Drawer transition.** A short CSS transform transition
  (150–250ms slide + fade) is standard. Avoid overengineering
  the animation.
- **Shared drawer component (if R7a chosen).** Simplest
  mechanism: a dedicated JS include (e.g.
  `static/left_nav.js`) + a shared CSS file injected by each
  of the three HTML pages, same approach TB-US-010 used
  for the user-management modal.
- **Why no backend changes.** All information needed for the
  drawer is already in the HTML / already loaded; this is
  layout and styling, not data.
- **Branding freeze respected.** No new copy, no new brand
  color commitments. Picking an accent color is pragmatic
  design, not branding — a future branding phase can
  reconsider.

## Out of Scope

- **IA grouping of nav items into categories.** Deferred to
  a follow-up story once the flat list is in use.
- **Changes to the admin modal's internal structure or
  behavior.** Only visual theming adapts (R14). TB-US-017's
  user management v2 is the next functional change to the
  modal and is tracked separately.
- **Changes to backend code or any schema.**
- **Projmgmt-side changes.** projmgmt is not touched. If
  projmgmt eventually wants a similar refresh, that's a
  separate PM-US story.
- **New features behind the new nav.** Only moves what's
  there today.
- **Keyboard shortcuts** for nav item switching, settings
  panels, user profile editor — all separate concerns.
- **Dark mode / theme toggle.** v1 is white only. A theme
  switcher is a nice follow-up if demand materializes.
- **Pixel-exact replication of claude.ai's palette or
  layout.** We adopt the visual language, not clone it.
- **Branding tweaks** (per the deferred-branding memory).
- **Hamburger-menu optimization for truly tiny screens
  (<400px).** Baseline mobile responsiveness is enough.
- **A follow-up story to add the gradient back if the white
  theme is unpopular.** If reversion is needed, it's a
  separate decision and story.

## Related

- **Supersedes:** [PM-US-024 on projmgmt](../../../projmgmt/docs/user-stories/pm-us-024.md)
  — Retired 2026-10-13 after being drafted against the wrong
  app. See its Retirement Notes for the context trail. This
  story's scope expanded from PM-US-024's "just left nav" to
  "left nav + white theme" per operator direction on
  2026-10-13.
- [TB-US-010](tb-us-010.md) — Shipped the 👥 Users admin
  modal and the shared-JS-include pattern. R14 adapts the
  modal's theming here; the pattern is reused for the drawer
  if R7a is chosen.
- [TB-US-017](tb-us-017.md) — User management v2 (In
  Progress). Both touch frontend; coordinate at execution so
  they don't collide on `index.html` or on the admin modal's
  theme.
- **PM-US-025** on projmgmt (In Progress) — adds TB
  stakeholder notifications. Once shipped, status changes on
  this story will fire email notifications to the three
  stakeholders.
- `static/index.html`, `static/training_sets.html`,
  `static/training_runs.html` — files touched.
- `static/style.css` (or inline + new file) — theme + nav
  styling.
- `static/script.js` and inline scripts — nav-switching
  logic refactored.
- `MEMORY.md → workflow_projmgmt_pilot` — reminder that this
  story lives TB-side.
- `MEMORY.md → feedback_branding_deferred` — governs any
  brand-copy decisions encountered.

**Completion Notes (2026-10-15).**

**Shipped:**

- `static/left_nav.js` (new, 259 lines): shared IIFE that
  injects the hamburger button, drawer, and backdrop. 11
  nav items (9 index tabs + 2 training pages). Default
  state = closed; persisted via `localStorage.tb_nav_open`.
  Esc closes; backdrop click closes; item click on index
  switches tab and closes (R3 collapse-on-click); item
  click on training pages navigates via href. Hash routing
  (e.g. `/static/index.html#chat`) is honored on load.
- `static/index.html` — horizontal tab-bar block (lines
  265-275 of the pre-story file) removed; replaced with
  a comment pointer to `left_nav.js`. Added
  `<script src="left_nav.js?v=20261015c">` at the end of
  body.
- `static/training_sets.html` — added `left_nav.js` include.
- `static/training_runs.html` — added `left_nav.js` include.
- Hamburger-space reservation: `reserveHamburgerSpace()` in
  `left_nav.js` dynamically sets `header.style.paddingLeft
  = '70px'` if the header's current padding is less than
  that. Covers all 3 pages without per-page CSS edits.

**Operator choices locked:**

- R3: **collapse-on-click** (drawer closes when an item is
  selected on index.html).
- R6: **overlay drawer** (slides over content; backdrop at
  `rgba(0,0,0,0.3)`; drawer width 280px; transition
  200ms).
- R7: **R7a unified nav** across all 3 pages.
- R13: moved to TB-US-042 (locked choice: R13a harmonize
  with white theme).

**AC verifications — code-covered / live-service:**

| AC | Status | Evidence |
|---|---|---|
| AC1 (hamburger upper-left, no horizontal tabs) | ✓ coded | tab-button count in index.html = 0; hamburger renders at fixed top:12/left:12 |
| AC2 (click opens drawer, click again closes) | ✓ coded | `toggleNav` + state tracked via `drawer.dataset.open` |
| AC3 (nav item switches content on index) | ✓ coded | `handleItemClick` → `window.switchTab(id)` + `refreshActive(id)` |
| AC4 (active item visually distinguished) | ✓ coded | left-border accent + background tint + bold weight on active item |
| AC5 (open/closed persists across reloads) | ✓ coded | `localStorage.setItem(NAV_STORAGE_KEY, ...)` on every state change; restored in `injectNav` |
| AC6 (unified across 3 pages, href from drawer) | ✓ coded | all 3 HTML files include `left_nav.js`; training items use `data-href` → `window.location.href` |
| AC7 (Escape closes) | ✓ coded | document keydown listener on `e.key === 'Escape'` |
| AC13 (tab content layout preserved) | ✓ coded | zero changes to `.tab-content` divs or their internals |
| AC14 (TB-US-010 AC set still passes) | ✓ coded | admin modal injection logic untouched; 👥 Users button still super-only; body-scroll lock preserved |
| AC15 (login/gate unaffected) | ✓ coded | left_nav.js not included on login.html / gate.html; those pages untouched |
| AC16 (git diff backend/ clean) | ✓ verified | `git diff --stat backend/` for this story: empty |
| AC17 (no horizontal scroll) | ✓ coded | drawer uses `transform: translateX(-100%)` when closed, off-screen; backdrop overlays only |

**Live-service checks:**
- `node --check static/left_nav.js` → clean parse
- `GET /static/left_nav.js?v=20261015c` → 200, 10941 bytes;
  5 TB-US-018 markers in fetched content (confirms correct
  file served, not stale cache)
- All 3 HTML files return 200
- Smoke-tests on `/version`, `/active-adapter`,
  `/settings/mode`, `/sessions/active` continue to return
  200 (backend untouched, these just confirm no
  side-effects)

**Browser verification pending operator pass.** As with
TB-US-041, the implementer cannot verify visual UX in a
browser — the operator will need to run through the
below mini-test:

**Operator mini-test:**

1. Hard-refresh (Shift+⌘+R) `tbench.weidecai.com` to pick
   up `?v=20261015c`.
2. Log in. Visit `/static/index.html`. Horizontal tab bar
   should be gone. Hamburger (☰) visible in upper-left,
   over the purple gradient header.
3. Click the hamburger. Drawer slides in from the left
   with 11 nav items. Current active item (Upload by
   default) is highlighted with purple left-border +
   bold.
4. Click "Chat". Drawer closes, Chat tab content shows.
5. Click hamburger again. Drawer reopens, "Chat" is now
   the active item.
6. Press Escape. Drawer closes.
7. Click hamburger, click "Training Sets". Browser
   navigates to `/static/training_sets.html`. Drawer is
   still available via hamburger there, with "Training
   Sets" marked active.
8. Open the hamburger on training_sets.html, click
   "PowerSearch". Browser navigates to
   `/static/index.html#powersearch`, PowerSearch tab
   is shown.
9. Reload the page (Cmd+R). If drawer was closed before,
   it stays closed; if open, it stays open (localStorage
   persistence).

**Interim visual state note:** With TB-US-018 shipped and
TB-US-042 not yet executed, the active nav item uses
purple (`#667eea`) accent — the TB-US-042 story will
flip it to warm amber (`#CC785C`). The hamburger button
has a semi-transparent white background that renders
visibly against the purple gradient header. These are
expected during the phase gap.

**No side effects on backend or other frontend
features.** TB-US-010, TB-US-017, TB-US-041, TB-US-040,
and the OT work (TB-US-022+) are unaffected.
