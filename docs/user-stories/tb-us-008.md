# TB-US-008: Move Database Statistics from top of admin page to per-database controls

**Status**: Proposed
**Created**: 2026-07-09
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a super-user managing multiple RAG databases, I want per-database
statistics to live next to the database in the Manage Databases
tab, not in an always-visible header block, so that the admin page
gives me stats in context of a specific database and does not
consume vertical space above the tab I actually want to use.

## Background

Today, the admin page opens with an always-visible "Database
Statistics" section at the top (`static/index.html` lines 256-274)
that shows five metric tiles (Web Pages, Uploaded Docs, Document
Chunks, Total Queries, Avg Response Time) for the **currently active**
database, plus a "Refresh Stats" button and a "Clear Database"
button.

The always-visible placement predates the multi-database feature.
Once databases became switchable (see `#database-selector` in the
same section), the stats block became a per-database view rendered
in a page-level position. That mismatch has two costs:

1. It hides the tabs below the fold on smaller screens.
2. It makes "which database am I looking at?" a question the user
   answers by cross-referencing the selector, instead of the stats
   being visually adjacent to the database they describe.

The Manage Databases tab (`#databases-tab`, index.html:608-629)
already lists every available database via `#databases-list`. Each
row is the natural home for that database's stats and destructive
actions.

## Requirements

- [ ] R1: The always-visible "Database Statistics" section at the
      top of the admin page is removed. The active-database
      selector migrates elsewhere (see R2). Zero page-level
      metric tiles remain above the tabs.
- [ ] R2: The active-database selector remains reachable from any
      tab — either as a compact header control (small
      chip/dropdown near the user badge) or as a control at the
      top of every tab that needs it. Switching databases
      continues to route to the same `switchActiveDatabase()`
      handler.
- [ ] R3: In the Manage Databases tab, every row rendered by
      `#databases-list` gains a "Statistics" control that reveals
      the same five metrics currently displayed at the top
      (Web Pages, Uploaded Docs, Document Chunks, Total Queries,
      Avg Response Time) *for that specific database*.
- [ ] R4: The "Clear Database" destructive action, currently a
      page-level button in the Statistics section, moves to a
      per-row control in Manage Databases. Confirmation prompt
      names the database being cleared.
- [ ] R5: The `refreshStats()` JS function either becomes
      per-database (accepts a database ID) or is replaced by an
      equivalent per-database call. Callers that used it purely
      to refresh the top block are updated or removed.
- [ ] R6: Role-based UI hiding still works: users whose tab
      permissions exclude Manage Databases do not see the stats
      controls. The previous `hide the entire database statistics
      section` code paths (script.js lines 125, 141) are updated
      accordingly.

## Acceptance Criteria

- [ ] AC1: Loading the admin page as a super-user shows tabs
      immediately below the header — no metric tiles above the
      tabs.
- [ ] AC2: Opening Manage Databases and clicking Statistics on a
      row shows the five metrics for that row's database. Opening
      Statistics on a different row shows *that* database's
      metrics.
- [ ] AC3: Clicking Clear Database on a row prompts with the
      database name and, on confirm, clears only that database's
      contents. The row's Statistics view refreshes.
- [ ] AC4: A user whose role is not super does not see the
      Statistics or Clear Database controls anywhere. The Manage
      Databases tab is either hidden or read-only per prior
      role-tab rules.
- [ ] AC5: The active-database selector is discoverable from the
      Chat / Ask Questions tab (or wherever queries actually run)
      so a user still knows which database will answer their
      query.

## Design Notes

- **UI pattern for the per-row stats reveal** — subject to
  refinement during implementation. Three viable options:
  1. **Inline expander** — clicking Statistics slides open a
     stats panel below the row.
  2. **Modal** — clicking Statistics opens a modal with the
     metrics.
  3. **Inline always-shown** — every row shows a compact stats
     row alongside the database metadata (name, description).
  Option 1 is the current recommendation because it scales to any
  number of databases without stacking large metric tiles.
- **Selector placement** — a small chip in the header near the
  user badge is the current recommendation. Alternative:
  duplicate at the top of Chat and Search tabs.
- **Metric parity** — the five metrics currently displayed are the
  starting set. Adjusting the metric set (add "Last query at",
  drop "Avg Response Time", etc.) is out of scope; this story
  only relocates the existing set.
- **Backend endpoint(s)** — `/stats` today returns metrics for
  the active database. If per-database stats need a
  `?database_id=...` parameter, that is in scope for this story.
  If the backend can already scope by active-database context,
  reuse it.

## Out of Scope

- **Changing which metrics are shown.** Add/remove/rename metrics
  belongs in a separate story.
- **Cross-database aggregate view.** "Show me totals across all
  databases" is a distinct feature.
- **Stats history / trends over time.** Just the current snapshot.
- **Redesigning the Manage Databases tab beyond adding the
  per-row controls.** Layout polish of create-form, list
  ordering, and search-in-list are separate.
- **Redesigning the header / user badge area** to accommodate a
  new selector chip — if the header needs a bigger rework, that
  is a separate story.

## Related

- `static/index.html:256-274` — the always-visible stats block
  being removed.
- `static/index.html:608-629` — Manage Databases tab where the
  new per-row controls land.
- `static/script.js` — `refreshStats`, `clearDatabase`,
  `switchActiveDatabase`, `#databases-list` renderer.
- Backend `/stats` and `/clear` endpoints — verify per-database
  scoping.
