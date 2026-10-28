# TB-US-062: Admin tier — drawer-footer coordinator

**Status**: In Progress
**Created**: 2026-10-22
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a TB operator, I want the administrative-tier functions
(user management, API key management, system config, audit viewers)
to live in a single, consistent **drawer-footer Admin group**
above Logout — physically separated from the agent-tier
functions in the main drawer — so that the two-tier
architecture established in TB-US-044 §1.a is visible and
discoverable, not just schematized.

## Background

TB-US-044 established the two-tier architecture:

- **Agent tier (top of food chain):** everything that scopes
  to a specific agent — RAG, training sets, adapters, prompts,
  routes, harnesses, experiments. These live in the main
  drawer nav items (Chat / Upload / Documents / Databases /
  Training Sets / Training Runs / etc.) and are agent-scoped
  by the drawer agent-selector widget.
- **Administrative tier:** everything that is **not**
  agent-scoped — users, API keys, system-level config, cross-
  agent audit viewers. These are install-wide concerns held
  by super users.

TB-US-044 Q11 (admin-surface shape) considered a top-bar
avatar/account menu as the admin-tier surface. That decision
was deferred and is being **reshaped** by the recent arc:

- TB-US-045 Tweak 8 moved Logout to the drawer footer
- TB-US-045 Tweak 19 (2026-10-22) added an Admin group above
  Logout and relocated the `👥 Users` entry there
- Operator (2026-10-22): *"the user management button
  belongs under an admin function and should be moved off
  the horizontal top bar to an admin function just above
  logout at the bottom of the left nav."*

**Resolution:** admin tier = drawer-footer group above Logout.
Avatar/account menu is NOT shipped. This story is the coordinator
that captures the pattern + links to sub-stories per admin item.

## Requirements

### Container (shipped via TB-US-045 Tweak 19)

- [x] R1: **Admin group container exists** in the drawer footer
      (`#tb-nav-admin-group` in `static/left_nav.js`), above
      Logout, with a small-caps "ADMIN" label.
- [x] R2: **Super-only visibility** — the container is hidden
      by default; `static/script.js` reveals it on auth-
      verify success for super users.
- [x] R3: **Logout preserved as independent** below the Admin
      group, per TB-US-045 Tweak 8 (confirmed by operator
      2026-10-20).

### Items (phase-gated sub-stories)

- [x] R4: **Users** — ships via TB-US-010 (initial mgmt),
      TB-US-017 (v2 backend + audit), TB-US-041 (v2 frontend),
      TB-US-045 Tweak 19 (relocation to drawer-footer Admin
      group).
- [x] R5: **API key management** — see
      [TB-US-063](tb-us-063.md). **Shipped 2026-10-22.**
      Backend CRUD + admin UI modal + role gating + audit.
      Second entry in the Admin group.
- [ ] R6: **System configuration viewer / editor** — future
      sub-story. Covers AppSettings-style settings
      (rag_prompt, query_routes, SECRET_KEY rotation, etc.)
      exposed through a super-only UI. Deferred.
- [ ] R7: **Admin audit log viewer** — future sub-story.
      TB-US-017 built the `admin_audit` table + API; this
      item surfaces it as a sortable / filterable viewer
      in the Admin group. Deferred (operator opens via SQL
      today).

### Pattern maintenance

- [ ] R8: **New admin items follow the container pattern** —
      each adds a `.tb-nav-admin-item` div inside
      `#tb-nav-admin-group` in `left_nav.js`, hidden-by-
      default, super-only gated by `script.js`. No new
      containers; no new UI surfaces for the admin tier
      outside this group.
- [ ] R9: **If Admin group grows past 6-7 items**, revisit
      the design (consider sub-grouping, collapsible
      sections, or a dedicated admin page). Not needed at
      v0.1 scale.

## Acceptance Criteria

- [x] AC1: Super user, drawer open → "ADMIN" label visible
      above Logout; `👥 Users` entry present and functional
      (via TB-US-045 Tweak 19 verification).
- [x] AC2: Non-super user, drawer open → no Admin group
      visible; Logout only.
- [x] AC3: User-management modal opens when clicking the
      drawer Users entry.
- [x] AC4: API key management (TB-US-063) sub-story
      completed → `🔑 API Keys` entry appears in the Admin
      group alongside Users for super users.
- [x] AC5: Role gating verified for API keys: non-super
      can't see entry, can't call endpoints. (Live-verified
      via `chat_user` → 403 on GET /api-keys.)
- [x] AC6: Admin group retains visual consistency across
      items (icon + label pattern, hover affordance). Both
      Users and API Keys use `.tb-nav-admin-item` with the
      same CSS pattern.

## Design Notes

- **Why coordinator, not single story.** Admin tier is a
  multi-story arc (Users / API keys / System config / Audit
  viewer). Per the `feedback_coordinator_not_epic` memory,
  the right shape is an ordinary coordinator story
  referencing sub-stories, not a mega-story and not an
  "epic" artifact. This story is the coordinator.
- **Why drawer-footer, not top-bar avatar menu.** TB-US-044
  Q11 leaned toward a top-bar avatar menu, but the arc has
  shifted:
  - TB-US-045 Tweaks 8/9/10 cleaned the top bar; adding an
    avatar menu would re-clutter it
  - Admin items are deliberately infrequent for most users;
    drawer-footer (collapsed by default) matches the usage
    pattern
  - Logout already lives there (Tweak 8); grouping all
    account-level actions in one location is clean
- **Why not a dedicated admin page.** A full `/admin` page
  is overkill for the current scope (3-4 planned items).
  The modal pattern (TB-US-010/017/041) is already proven;
  each admin item opens its own modal from the drawer entry.
- **Why super-only.** Admin items affect install-wide state
  (users, keys, system config). Non-super users should
  never see them.
- **Independence from agent-selector.** The Admin group is
  install-scoped, not agent-scoped. Switching the drawer
  agent-selector does NOT change the Admin group's
  visibility or contents — this is a deliberate contrast
  with the agent-tier drawer items.

## Out of Scope

- Full `/admin` dedicated page (future, if Admin group
  grows beyond ~6-7 items)
- Per-admin-item route-level deep linking (admin items
  open as modals, not URLs)
- Admin-item ordering / customization UI (fixed order)
- Analytics on admin-item usage
- Breadcrumb navigation inside admin modals (modals are
  self-contained)
- Changes to TB-US-044's agent-model core

## Related

- [TB-US-044](tb-us-044.md) §1.a — two-tier architecture
  design; Q11 (admin surface) resolved **by this story**
  from avatar-menu lean to drawer-footer group
- [TB-US-010](tb-us-010.md), [TB-US-017](tb-us-017.md),
  [TB-US-041](tb-us-041.md) — User management
  (already-shipped admin item)
- [TB-US-045](tb-us-045.md) Tweak 8 — Logout moved to
  drawer footer
- [TB-US-045](tb-us-045.md) Tweak 19 — Admin group
  container + Users relocation (closes R1-R4)
- [TB-US-063](tb-us-063.md) — API key management (first
  pending sub-story)
- Files touched (coordinator layer):
  - `static/left_nav.js` — Admin group container
  - `static/script.js` — super-only visibility toggle
  - `static/index.html` — top-bar Users button removal
