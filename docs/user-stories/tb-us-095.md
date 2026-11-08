# TB-US-095: Reverse-port — Query Routes UI from stalite3 (SL-US-010)

**Status**: Completed 2026-11-07
**Created**: 2026-11-07
**Shipped**: 2026-11-07
**Author**: Jesse Eversole
**Depends on**: TB-US-040 (query-routes cache + `_maybe_augment_query`),
TB-US-033 (`/settings/query-routes` GET/PUT endpoints), SL-US-010
(stalite3's UI implementation, committed in stalite3 as
`b87c623` on 2026-11-07)
**Sibling to**: TB-US-094+ (the TB → stalite catch-up arc; this is
the one reverse-port we discovered first)

## Story

As a TB super-user, I want the **UI surface for editing query
routes** that stalite3 already has (SL-US-010), so I can configure
category-biased retrieval augmentations from the TB UI instead of
having to `curl` the `/settings/query-routes` endpoint. TB has had
the backend for this since October 2026 (TB-US-040 + TB-US-033)
but never built the UI; stalite built it in June 2026. This story
ports that UI into TB.

## Background

TB-US-090 inspection of stalite3 (2026-11-07) initially concluded
there were no reverse-port candidates — all capabilities stalite3
had were either in TB already or correctly scoped to stalite's
private fork. **Operator correction**: stalite3's SL-US-010
("Configurable query-routing for category-biased retrieval")
*is* a form of prompt classification (regex pattern → category →
retrieval augmentation), and TB is missing its UI surface.

TB-US-086 backend audit even flagged this: *"Query routes +
persisted RAG prompt — settings endpoints exist, UI exposure
unclear."* We never built the UI. Stalite did.

What stalite3's SL-US-010 adds on top of the pre-fork shared
backend:
- Regex pattern → augmentation routing with prefix/suffix position
- Per-route `enabled` flag
- First-match-wins semantics
- UI for list/add/edit/delete/toggle-enabled
- Audit-log entry on save

TB's existing backend already supports all of the above: the
`QueryRoute` Pydantic model, PUT validation, and the
`_maybe_augment_query` runtime path. **Only the UI was missing.**

## Scope

### Code (completed this story)

- [x] R1: `static/query_routes_management.js` (new) — self-
      contained modal, super-only, modeled on `agent_management.js`
      pattern. Wires to existing `/settings/query-routes` GET
      (for load) and PUT (for save / toggle / delete).
- [x] R2: Admin dropdown entry in `left_nav.js` — new "Query
      Routes" subitem (🧭) alongside Users and API Keys.
- [x] R3: Load the module on all app pages: `index.html`,
      `training_runs.html`, `training_sets.html`,
      `experiments.html`.
- [x] R4: Cache-bust bump on `left_nav.js` across all pages.
- [x] R5: Features ported: list routes, add route, edit route,
      delete route (with confirm), toggle enabled, show last-saved
      timestamp + user.
- [x] R6: Match TB's white-theme + amber-accent styling (not
      stalite3's teal/dark theme).

### Not in scope

- The versioned-routes system (`route_version_manager.py`,
  TB-US-055) — that's a separate agent-scoped surface with its
  own UI already in the TB-US-087 version-lifecycle panel. The
  flat AppSettings routes (what this story's UI edits) are
  service-level; the versioned routes are per-agent. Both exist;
  this story only touches the flat layer.
- The semantic question "is this stalite's version of prompt
  classification sufficient, or do we still need TB-US-023's
  4-category classifier arc?" — TB-US-023 remains a separate
  Proposed story.

## Acceptance Criteria

- [x] AC1: Super-user drawer → Admin dropdown → "Query Routes"
      opens a modal.
- [x] AC2: Existing routes load and display with name, patterns,
      augmentation, position, enabled state.
- [x] AC3: Add/Edit routes writes through the existing PUT
      endpoint (audit log captured server-side).
- [x] AC4: Delete asks for confirmation; writes through PUT with
      the shortened list.
- [x] AC5: Toggle enabled flips the flag and writes through PUT.
- [x] AC6: All behavior is super-only (drawer admin group is
      hidden for non-super users; endpoint also gated).
- [x] AC7: No behavior change to the backend; this is a pure UI
      surface addition.

## Design Notes

- **Why port stalite's UI verbatim rather than reinvent**: SL-US-010
  is a complete, tested implementation of a workflow operators
  already understand. Porting verbatim preserves the mental model
  and reduces the risk of subtle divergence.
- **Why drawer admin dropdown vs. a dedicated tab**: per
  `project_admin_tier_drawer_footer.md` memory, new admin items
  land in the drawer footer admin group, not top-bar avatar menu
  or dedicated tabs.
- **Why "🧭" icon**: routes = navigation of retrieval; compass is
  the associated icon in Unicode's travel/transport set and reads
  cleanly next to 👥 Users and 🔑 API Keys in the dropdown.

## Related

- [`stalite3/sl-us-010.md`](../../../stalite3/sl-us-010.md) — the
  original stalite story (not in TB git; lives in stalite3 repo)
- stalite3 commit `b87c623` — the stalite-side SL-US-010 release
- [TB-US-040](tb-us-040.md) — query-routes cache + rewrite layer
- [TB-US-033](tb-us-033.md) — `/settings/query-routes` endpoints
- [TB-US-055](tb-us-055.md) — versioned routes (agent-scoped;
  separate surface)
- [TB-US-086](tb-us-086.md) — the backend audit that flagged the
  missing UI
- [TB-US-090](tb-us-090.md) — stalite3 inspection where we first
  correctly identified SL-US-010 as a reverse-port candidate
  (after initial miss)
- [TB-US-023](tb-us-023.md) — the richer "4-category classifier +
  specialized handlers" arc; separate Proposed story
