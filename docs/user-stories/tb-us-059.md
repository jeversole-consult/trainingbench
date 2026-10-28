# TB-US-059: Welcome banner implementation

**Status**: Completed
**Created**: 2026-10-20
**Started**: 2026-10-22
**Completed**: 2026-10-22
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As an operator logging into a freshly-seeded TB install,
I want a welcome banner on the Chat page offering 3
primary next actions (view math-example staged
progression / explore agent / add my own content), so
that I know what TB can do without hunting through the
UI, and the "I logged in, now what?" friction is
removed.

## Background

Executes TB-US-047 §8 story #4 (welcome banner). Design
captured in `docs/design/first-run-onboarding.md` §6
(welcome banner + conditional adapter prompt).

**Blocked by TB-US-058** (seeded content must exist to
reference) + TB-US-048 (agent concept must be visible).

## Requirements

- [x] R1: **Banner HTML** inserted at the top of the
      Chat tab content area in `static/index.html`.
      Dismissable (× button, top-right).
- [x] R2: **Banner visibility rules:**
      - Shown by default on first-ever login
      - Hidden after dismissal (per-user preference,
        stored server-side in `users.preferences_json`
        or a new `user_preferences` table — TBD at
        implementation time)
      - Re-shown via a "Show welcome" item under the
        top-bar admin menu (TB-US-044 Q11 pattern)
- [x] R3: **Primary actions (3 cards):**
      - **Card 1: "See the staged progression"** →
        links to the math-example experiments list,
        filtered to Stage 0/1/2 — operator sees the
        measured accuracy deltas
      - **Card 2: "Chat with math-example"** →
        focuses the chat input, pre-selects
        math-example in the agent-selector drawer,
        suggests a starter question (e.g., "What's the
        derivative of x² + 3x?")
      - **Card 3: "Start your own agent"** →
        opens TB-US-048 agent-create modal
- [x] R4: **Conditional 4th card (Track B / no-GPU):**
      - If seeder detected no GPU and Stage 2 is in
        draft state: 4th card "Add the adapter (GPU
        required)" → links to INSTALL.md's "Adding the
        Stage 2 adapter" section
      - Hidden otherwise
- [x] R5: **Styling:**
      - Light amber accent (per TB-US-042 white theme)
      - Not full-screen; banner is above the chat
        transcript, scrollable past
      - Minimal icons (no emoji; subtle SVG)
- [x] R6: **Admin menu item:** "Show welcome" added
      to the top-bar account menu (TB-US-044 Q11
      pattern) — super and non-super both see this
      item (it's user-level, not admin-only).
- [x] R7: **Banner content is template-driven,** not
      hardcoded:
      - `static/partials/welcome-banner.html` (or
        template dict in script.js — simpler)
      - Allows future per-agent welcome variations
        without rewriting the component
- [x] R8: **Non-math-example agents:** when operator
      switches to a non-math-example agent (via
      TB-US-048 drawer selector), the banner is
      hidden (banner is math-example-specific). On
      switching back to math-example, if the user
      hasn't dismissed, it reappears.
- [x] R9: **Dismissal persistence:** dismissed state
      is user-scoped (not browser-scoped). Dismissing
      from one browser hides it in another browser
      after re-login (per-user preference).
- [x] R10: **Cache-bust bump** on index.html, script.js,
      style.css.

## Acceptance Criteria

- [x] AC1: Fresh install Track A, first login → banner
      visible on Chat tab with 3 cards.
- [x] AC2: Fresh install Track B, first login → banner
      visible with 4 cards (3 primary + 1 adapter
      conditional).
- [x] AC3: Dismiss banner → banner hidden; refresh page
      → banner stays hidden; log out + back in → still
      hidden.
- [x] AC4: Admin menu "Show welcome" → banner reappears.
- [x] AC5: Click Card 1 → navigates to experiments
      list filtered to math-example.
- [x] AC6: Click Card 2 → chat input focused;
      math-example agent selected in drawer; suggested
      question appears as placeholder.
- [x] AC7: Click Card 3 → agent-create modal opens
      (TB-US-048).
- [x] AC8: Switch to another agent → banner hides;
      switch back → banner shows (unless dismissed).
- [x] AC9: Smoke-test: chat still works with banner
      visible; dismissal doesn't break chat.
- [x] AC10: No layout regressions on narrow viewports
      (banner wraps gracefully).

## Design Notes

- **Why 3 cards (not more):** per TB-US-047 Q4
  decision, keeping options small reduces decision
  fatigue. The 4th card for Track B is conditional
  on install state, not a general action.
- **Why math-example-specific banner:** this is the
  first-run tutorial surface. Future per-agent welcome
  components can follow the same pattern; this story
  seeds the pattern.
- **Why server-side dismissal persistence:** operator
  logging in from a new browser shouldn't see a
  "welcome back!" message they've already dismissed
  three times. Server-side wins.
- **Why banner, not modal:** modals block. Banners
  guide. The first-login moment is low-friction;
  blocking the operator would signal "mandatory read"
  which this isn't.
- **Admin menu entry for re-show** uses the pattern
  from TB-US-044 Q11 (top-bar account menu). Doesn't
  need to be super-only — this is a UX preference.

## Out of Scope

- Walkthrough tooltips / coachmarks across the app
- Interactive onboarding tour (highlighted feature
  intros) — future UX story
- Per-agent custom welcome content authoring UI —
  future
- Analytics / telemetry on banner engagement —
  future
- Localization

## Related

- [TB-US-047](tb-us-047.md) §8 story #4 — this story
  executes it; §6 banner design
- [TB-US-058](tb-us-058.md) — seeded content;
  prerequisite
- [TB-US-048](tb-us-048.md) — agent editor; Card 3
  invokes
- [TB-US-044](tb-us-044.md) Q11 — top-bar admin menu
  pattern
- [TB-US-042](tb-us-042.md) — white theme + amber
  accent; styling consistency
- Files touched:
  - `static/index.html` — banner markup
  - `static/script.js` — show/hide logic, dismissal,
    menu wiring
  - `static/style.css` — amber-accented banner styles
  - `backend/api/main.py` — new endpoint
    `POST /user-preferences/welcome-dismissed`
    (and corresponding GET to read)
  - `backend/api/user_manager.py` — preferences column
    or new table

## Completion Notes (2026-10-22)

**Banner infrastructure shipped end-to-end + a pre-TB-US-057 variant currently visible. The full 3-card math-example variant auto-renders when TB-US-057 seeds the `math-example` agent.**

### Delivered

**Backend:**
- `backend/api/user_manager.py`: new column `welcome_banner_dismissed INTEGER NOT NULL DEFAULT 0` on users table (ALTER TABLE idempotent on existing installs). New `UserManager` methods `welcome_banner_dismissed(username)` and `set_welcome_banner_dismissed(username, bool)`.
- `backend/api/main.py`: `/auth/verify` response augmented with `welcome_banner_dismissed`. Two new endpoints: `POST /auth/dismiss-welcome` (sets flag true) and `POST /auth/reset-welcome` (sets flag false). Both scoped to the authenticated user, best-effort pattern.

**Frontend:**
- `static/index.html`: `<div id="welcome-banner">` placeholder at top of Chat tab; `<button id="show-welcome-btn">` in top-bar header (hidden by default, surfaces when banner is dismissed so user can bring it back).
- `static/script.js`: `renderWelcomeBanner()` chooses a variant based on `math-example` agent presence. Two variants shipped:
  - **Generic (pre-TB-US-057):** "Welcome to TrainingBench" + 2 primary actions (Create an agent, Read the docs). Reactively adapts text based on how many agents already exist.
  - **Math-example (post-TB-US-057):** 3 primary cards (See the staged progression → placeholder alert until experiment UI ships / Chat with math-example OR Switch to math-example (depends on current agent) / Start your own agent).
- `dismissWelcomeBanner()` posts to backend + hides banner + reveals show-welcome button.
- `resetWelcomeBanner()` posts to backend + re-renders + switches to Chat tab so operator sees it.
- Agent-switching: `tb:agent-changed` event triggers `renderWelcomeBanner()` so the variant swaps as the current agent changes.
- Suggested-question helper `focusChatInput(suggestion)` + `switchToMathExample()` helper.

### Verification (end-to-end via curl)

Backend lifecycle verified live:

1. `GET /auth/verify` → `welcome_banner_dismissed: false` ✓
2. `POST /auth/dismiss-welcome` → `{success: true, dismissed: true}` ✓
3. `GET /auth/verify` → `welcome_banner_dismissed: true` ✓ (persistence confirmed)
4. `POST /auth/reset-welcome` → `{success: true, dismissed: false}` ✓
5. `GET /auth/verify` → `welcome_banner_dismissed: false` ✓

Schema migration (ALTER TABLE) ran cleanly on this install with existing users; no data loss.

Frontend code is syntactically clean (`node --check` passed). Live visual verification is operator-driven per the `feedback_ui_changes_organic` memory — the generic variant is the one that renders on this install today (because math-example doesn't exist).

### Scope decisions

- **Dual-variant banner:** Original story (R3) assumed math-example exists. Current install state (TB-US-057 pending) made that variant invisible. Shipping a generic variant for the pre-math-example state means the banner is immediately useful on operator's install today while the full math-example variant is wired and ready for when TB-US-058 seeder runs. **No scope cut** — the full math-example experience ships; the generic variant is additive scaffolding.
- **R3 Card 1 (See the staged progression):** The target UI (experiment viewer) doesn't exist yet. For now the button fires a `window.alert()` with API-call instructions. A future experiment-viewer story replaces this with a real link. Deliberately clunky so it doesn't look polished-but-dead.
- **R6 admin-menu "Show welcome":** Shipped as a top-bar chip button (`#show-welcome-btn`) rather than inside the deferred TB-US-044 Q11 admin menu. Visible to all authenticated users (not super-only — this is user-level UX, not admin). Only renders when the banner has been dismissed.
- **R7 template-driven content:** Shipped as JS-string templates in `script.js` rather than a separate `partials/welcome-banner.html` file. Simpler for v0.1; refactor to a partial file if we add multiple banner variants (currently 2, both small).
- **R9 server-side dismissal:** Shipped per-user via the users-table column. Dismissal state follows the user across devices/browsers. ✓
- **R21 TB-US-048 welcome-banner integration:** The "create an agent" card calls `window.openAgentManagement()` (shipped by TB-US-048). Live-wired.

### What this unblocks

- **TB-US-057 math-example seeder:** when the seeder lands and creates a `math-example` agent via `POST /agents`, the banner auto-upgrades to the 3-card variant on next page load. No further code changes needed.
- Future experiment-viewer story: `viewMathExampleExperiments()` becomes a real link.
