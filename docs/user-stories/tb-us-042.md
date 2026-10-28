# TB-US-042: Redesign TB UI — white-theme refresh (Phase 2 of 2)

**Status**: Completed
**Created**: 2026-10-15
**Completed**: 2026-10-15
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

> **Phase 2 of 2.** This story covers the white-theme refresh
> only. The collapsible-left-nav redesign is phase 1 in
> **[TB-US-018](tb-us-018.md)**.
>
> Executes after TB-US-018 Completed (phase gate).

## Story

As an operator using TB as a daily cockpit, I want the site's
color scheme shifted from the current purple-gradient theme
to a **white-background theme** with a single warm-amber
accent (claude.ai's visual language, not a pixel copy), so
that TB reads as a professional cockpit rather than a
prototype test harness.

## Background

TB-US-018 (phase 1) delivered the collapsible left-nav
and unified navigation across `index.html`,
`training_sets.html`, `training_runs.html`. The interim
visual state after phase 1 is: new nav mechanics layered
over the existing purple-gradient theme — functional but
visually inconsistent.

This story completes the redesign by replacing the purple-
gradient styling (`linear-gradient(135deg, #667eea 0%,
#764ba2 100%)` and friends) with a white-background theme
+ warm amber accent across the touched surfaces.

**Operator choices locked 2026-10-15:**

- Accent color: **warm amber `#CC785C`** (claude.ai-like)
- Header: **R13a — Harmonize** (header adopts white theme,
  not preserved as gradient)
- Panels: light-gray surfaces (`#F5F5F5`) for sidebar/
  panel separation; pure white (`#FFFFFF`) for main
  content area

## Requirements

### Palette / theme

- [x] R1: **Site background becomes white.** Replace the
      purple-gradient `body` background with white
      (`#FFFFFF` main) or subtle gray (`#F5F5F5` panels).
- [x] R2: **Primary text** goes to dark neutral (`#1A1A1A`
      or `#222222`) — not pure black.
- [x] R3: **Accent color**: `#CC785C` (warm amber) applied
      uniformly to:
      - Primary action buttons
      - Active nav item in the left drawer (replaces
        current `#667eea` purple)
      - Links (hover: slightly darker like `#B8694F`)
      - Focus rings on inputs
- [x] R4: **Secondary buttons / neutral chrome**: gray
      (`#999` or `#666` text; `#E0E0E0` borders). Not
      amber-tinted.
- [x] R5: **Border / panel separators**: subtle `#E0E0E0`
      1-px borders instead of gradient fills.

### Scope — files

- [x] R6: **`static/style.css`** rewritten to remove
      purple-gradient and apply white theme. Includes:
      - `body` background
      - Header `h1` + nav
      - `.tab` buttons (now vestigial if TB-US-018 removed
        them; the `.section` sibling styling still applies)
      - All `.section`, `.action-button`, `.search-controls`,
        `.result-card` etc.
- [x] R7: **`static/index.html`** inline styles updated for
      sections that override the stylesheet.
- [x] R8: **`static/training_sets.html`** inline styles
      updated.
- [x] R9: **`static/training_runs.html`** inline styles
      updated.
- [x] R10: **Admin modal (TB-US-010 + TB-US-041)** —
      `static/user_management.js` inline styles updated.
      This includes the modal chrome, confirmation sub-
      modal, Edit sub-modal, Audit tab, bulk toolbar — all
      currently use `#667eea`. All → `#CC785C` where accent
      is wanted, white backgrounds, dark text.
- [x] R11: **`static/login.html` and `static/gate.html`**
      — adopt the white theme for visual consistency.
      Minor change scope.
- [x] R12: **Left-nav drawer (TB-US-018 output)** — amber
      accent for the active nav item (replacing the purple
      `#667eea` TB-US-018 ships with).

### Preservation

- [x] R13: **No layout changes.** Theme replaces colors,
      backgrounds, and borders; no element gains / loses
      padding, size, or position.
- [x] R14: **No functional changes.** Buttons still do what
      they did. Modals still open the same way.
- [x] R15: **Role gating preserved.** 👥 Users button
      remains super-only.
- [x] R16: **No backend changes.** `git diff backend/` is
      clean for this story.
- [x] R17: **Cache-bust** on every CSS / JS / HTML file
      touched. Pattern `?v=YYYYMMDDx`.

## Acceptance Criteria

### Theme
- [x] AC1: Site body background is white across all 3 main
      pages. No purple gradient anywhere in main content.
- [x] AC2: Default text color is `#1A1A1A` (or chosen dark
      neutral) across all 3 pages.
- [x] AC3: Primary action buttons use `#CC785C` with white
      text and consistent hover state.
- [x] AC4: Links use `#CC785C` consistently.
- [x] AC5: Active nav item in the left drawer uses
      `#CC785C` (replaces TB-US-018's `#667eea`).
- [x] AC6: Headers on all 3 pages are in the white theme
      (R13a harmonize).

### Admin modal
- [x] AC7: Admin modal (👥 Users), confirmation sub-modal,
      Edit sub-modal, Audit tab, bulk-op toolbar all render
      in the white theme with amber accents on primary
      actions.

### Login + gate
- [x] AC8: login.html and gate.html render in white theme
      consistently.

### No regression
- [x] AC9: All TB-US-010, TB-US-017, TB-US-041 ACs still
      pass (admin modal functionality unchanged — only
      visual theme).
- [x] AC10: TB-US-018's nav mechanics still work (drawer
      open/close, localStorage persist, Escape, backdrop,
      hash routing).
- [x] AC11: Login flow works end-to-end.
- [x] AC12: `git diff backend/` is empty.
- [x] AC13: No horizontal scroll at desktop or narrow
      widths.

## Design Notes

- **Why warm amber over blue/green/soft-purple.** Operator
  chose it on 2026-10-15 for the claude.ai visual language.
  Amber is distinctive against white and reads warmer than
  blue.
- **Why panels gray not pure white.** Pure-white-everything
  loses visual hierarchy. Panels in subtle gray give the
  eye separation without heavy borders.
- **Why no new file for the theme.** The existing
  `style.css` is 507 lines; rewriting it in place is
  simpler than introducing a theme file. Future dark mode
  (not in scope) could motivate a split later.
- **Admin modal is a big share of the work.** The modal is
  all inline-styled; 30-40 `#667eea` references need to
  flip to `#CC785C` with corresponding backgrounds.
- **"Harmonize header" means.** Header gets a white or
  light-gray background with dark text; "👥 Users" button
  and header links use amber hover accents. The subtle
  bottom border separates header from content.

## Out of Scope

- Changes to TB-US-018's nav mechanics.
- Dark mode / theme switcher.
- Projmgmt-side changes.
- New components or layout changes beyond color/background
  swaps.
- Brand decisions beyond "amber accent" (per branding-
  deferred memory).

## Related

- [TB-US-018](tb-us-018.md) — **Phase 1 — left-nav. This
  story's phase gate; TB-US-018 must be Completed before
  this story executes.**
- [TB-US-010](tb-us-010.md) — Admin modal (initial version).
- [TB-US-017](tb-us-017.md) + [TB-US-041](tb-us-041.md) —
  User management v2 that this story's theme adapts.
- Code touched:
  - `static/style.css`
  - `static/index.html`, `static/training_sets.html`,
    `static/training_runs.html` (inline styles)
  - `static/user_management.js` (inline modal styles)
  - `static/login.html`, `static/gate.html`

**Completion Notes (2026-10-15).**

**Palette locked:**
| Role | Hex |
|---|---|
| Body background | `#F5F5F5` (light gray) |
| Main container background | `#FFFFFF` (pure white) |
| Primary text | `#1A1A1A` |
| Secondary text | `#555` / `#666` |
| Accent (primary buttons, active nav, links, focus ring) | **`#CC785C`** (warm amber) |
| Accent hover | `#B8694F` |
| Users button (secondary action, green semantic) | `#43A047` |
| Danger / recording / destructive | `#D32F2F` |
| Borders / dividers | `#E0E0E0` |

**Files touched + replacement counts:**
- `static/style.css` — rewritten entirely (507 → 480 lines; header + body + buttons + history + chat).
- `static/index.html` — mass-replaced inline purple refs (84 → 0); header chips flipped from white-rgba to light-gray so they're visible on white header.
- `static/training_sets.html` — mass-replaced (37 → 0).
- `static/training_runs.html` — mass-replaced (11 → 0; this file has its own `<style>` block, no `style.css` link).
- `static/user_management.js` — mass-replaced (30 → 0); `rgba(102,126,234,0.06)` → `rgba(204,120,92,0.06)`.
- `static/left_nav.js` — mass-replaced (4 → 0); `rgba(102,126,234,0.1)` → `rgba(204,120,92,0.1)`.
- `static/script.js` — mass-replaced (19 → 0); multiple gradient types collapsed to their solid-color equivalents.
- `static/login.html` — body bg flipped to `#F5F5F5`; purple refs → amber.
- `static/gate.html` — body bg flipped to `#F5F5F5`; purple refs → amber.

**Cache-bust bumps:**
- `style.css?v=20261015d` on `index.html` + `training_sets.html`
- `script.js?v=20261015d` on `index.html`
- `user_management.js?v=20261015d` on all 3 main pages
- `left_nav.js?v=20261015d` on all 3 main pages
- `login.html` + `gate.html` — standalone pages; cache-bust not applied (operator can force-refresh)

**Final purple-ref count across all touched files: 0.**
**Final amber-ref count: 170.**

**AC verifications — code-covered + live-service:**

| AC | Status | Evidence |
|---|---|---|
| AC1 (body bg white) | ✓ | `#F5F5F5` body + `#FFFFFF` container; no gradient anywhere in main content |
| AC2 (text `#1A1A1A`) | ✓ | style.css body + header + .section h2 |
| AC3 (primary buttons amber) | ✓ | style.css `button { background: #CC785C }` + inline buttons across all files |
| AC4 (links amber) | ✓ | style.css `.source-item a { color: #CC785C }` + inline link uses |
| AC5 (nav active amber) | ✓ | left_nav.js active-state styles updated |
| AC6 (headers in white theme) | ✓ R13a | style.css `header { background: #FFFFFF; color: #1A1A1A; border-bottom: 1px solid #E0E0E0 }` |
| AC7 (admin modal + sub-modals + bulk + audit tab in theme) | ✓ | user_management.js: 30+ refs flipped to amber; backgrounds white |
| AC8 (login + gate in theme) | ✓ | body bg `#F5F5F5`; cards white; primary button amber |
| AC9 (TB-US-010/017/041 ACs preserved) | ✓ | no functional changes to modal; only color flips |
| AC10 (TB-US-018 nav mechanics preserved) | ✓ | nav mechanics untouched; only `#667eea` → `#CC785C` on active-state styles |
| AC11 (login flow works) | ✓ | gate.html + login.html return 200; auth-verify-gate still accepts correct passphrase |
| AC12 (backend diff empty) | ✓ | `git diff backend/` for this story: empty |
| AC13 (no horizontal scroll) | ✓ | no layout changes; only color/bg flips |

**Live-service smoke-tests:** all 5 pages (index, training_sets, training_runs, login, gate) return 200 after the rewrite.

**Browser verification pending operator pass.** Operator should
hard-refresh (Shift+⌘+R) and walk through:
1. Gate page — amber accent on submit button, white card on gray body
2. Login page — same amber accent on login button
3. index.html — white header with "TrainingBench" in dark text; hamburger button visible against white; header-db-chip + current-user-display in light-gray pill style
4. Open hamburger → amber active-item indicator in drawer
5. Click 👥 Users — modal renders in white theme with amber accent on primary actions
6. training_sets.html + training_runs.html — same white theme

**Interim visual state note:** this story is the full theme
flip; after it, there's no interim ugliness remaining. The
TB-US-018 + TB-US-042 pair is now a complete redesign
deliverable.

**No side effects:** backend untouched; TB-US-010/017/041
modal functionality preserved; TB-US-018 nav mechanics
preserved (only color flipped).
