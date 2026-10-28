# TB-US-031: Spike — Feature parity audit, stalite3 → TrainingBench master

**Status**: Completed
**Created**: 2026-10-14
**Completed**: 2026-10-14
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

**Deliverable**: docs/sync/stalite3-tb-parity-audit.md

## Story

As the operator establishing TrainingBench as the master
development line with **stalite3 as a long-lived downstream
branch**, I want a comprehensive written audit of every
capability stalite3 has today, mapped against TB's current
state, with a sync-forward mechanism recommendation and
prioritized gap-closing stories, so that the master →
downstream model has an evidence base rather than a loose
sense of "we think TB covers most of it."

## Background

Operator established on 2026-10-14:

- stalite3 is a **live production RAG agent** for Stalite
  Corporation, a prospective paying EL customer.
- TB is now **master**; stalite3 is effectively a **long-lived
  branch** off TB master.
- Future changes land on TB first, test on TB, propagate to
  stalite3.
- stalite3's data is proprietary to Stalite Corporation and
  is licensed for EL internal testing only; public release
  requires separate review.
- stalite3's data and features are also a broad test surface
  for TB — operator can exercise TB capability against real
  domain data.

The master → downstream relationship requires knowing exactly
what stalite3 has that TB doesn't (so sync-forward has
something to synchronize onto master), what TB has that
stalite3 doesn't (so the propagation plan is complete), and
what both have differently (schema deltas, vocabulary
mismatches like `chat` vs `sales` roles).

Piecemeal findings across prior sessions:

- stalite3 has `formula_calculator.py` (13 Stalite mix
  formulas) + `mix_design_handler.py`; TB has neither.
  OT v0.1's quantitative handler (TB-US-025) will add generic
  calculator framework but no stalite-specific formulas.
- stalite3's `query_logger.py` has a `master_query_log.jsonl`
  that logs richer per-prompt data than TB's current logs.
  OT audit log (TB-US-024) overlaps but may not cover all
  the same fields.
- stalite3 has `user_type` values `super | sales | training`;
  TB has `super | chat | training`. The deferred three-role
  rename story becomes meaningful here.
- stalite3 has spreadsheet ingestion (openpyxl-based,
  `training/scripts/extract_excel_formulas.py`); TB does
  not.
- stalite3 has corporate directory ingestion patterns
  (markdown directory files parsed into the chroma_db);
  TB has `/upload` and `/scrape` but may not have the same
  structured-source handling.
- stalite3 has PEFT adapters already trained
  (`stalite-mix-knowledge-v7`, V5 memorization adapter);
  TB has PEFT training infrastructure but no adapters
  deployed at prod scale.

**This spike is comprehensive — not just "list what we already
found."** The output is an exhaustive table that captures
every stalite3 capability, including ones we haven't yet
surfaced, with explicit TB coverage status for each.

## Requirements

### Audit scope

- [x] R1: **Enumerate every stalite3 feature** across all
  layers:
  - Backend handlers / endpoints
  - User role model + auth
  - Data ingestion mechanisms (upload, scrape, spreadsheet,
    directory)
  - RAG infrastructure (vector store, chroma_db management)
  - Training infrastructure (sets, runs, metrics, logs,
    checkpoints, adapters)
  - Logging / observability (query logger, master log, audit
    trails)
  - Formula / calculator capability
  - Mix design / structured-response handlers
  - UI / static pages
  - Config / settings management
  - Database schemas (users, training sessions, etc.)
  - Scripts / tooling under `training/scripts/`
- [x] R2: **Audit sources.** For each capability area:
  - Code files touched (reference line ranges where useful)
  - Docs referenced (`FORMULA_CALCULATOR_SUMMARY.md`,
    `ADAPTER_COMPARISON_V1_VS_V2.md`,
    `REQUIREMENTS_COMPLETE.md`, etc.)
  - Operational artifacts (logs structure, DB tables)

### Mapping to TB

- [x] R3: **For each stalite3 capability, record TB status:**
  - **✅ Covered** — TB has an equivalent capability. Note
    which TB file/story.
  - **🟡 Partial** — TB has related capability but with
    gaps. Enumerate the gaps.
  - **📅 Planned** — TB story in flight will close the gap.
    Reference the story ID.
  - **❌ Missing** — TB has nothing; no planned story.
    Needs new story.
  - **⚪ Not applicable** — stalite3-specific; TB intentionally
    doesn't have it (e.g., Stalite-mix formulas).
- [x] R4: **Reverse direction.** For each TB capability that
  stalite3 does NOT have, note it separately. This is the
  "what gets pushed to stalite3 via sync-forward" surface.

### Sync-forward recommendation

- [x] R5: **Sync mechanism survey.** Document four candidate
  mechanisms:
  - **A — Manual port** — operator applies TB changes to
    stalite3 by hand on a defined cadence
  - **B — Cherry-pick / rebase** — if TB and stalite3 share
    git ancestry, use git-level mechanics
  - **C — Release package** — TB produces an Agent Release
    artifact (per OT concept); stalite3 installs it
  - **D — Shared library** — TB extracts common capabilities
    as installable Python packages; stalite3 pins / imports
  Trade-off analysis per candidate.
- [x] R6: **Recommended mechanism** with reasoning. Not
  obligated to pick one of the four — a hybrid is valid.
- [x] R7: **Live-site preservation rules** regardless of
  mechanism:
  - stalite3's `users.db` must survive sync (SMEs are
    actively using it)
  - stalite3's ratings log, query log, directives log must
    survive sync
  - stalite3's chroma_db and PEFT adapters must survive sync
  - stalite3's local config (`backend/api/mix_design_handler.py`
    constants, formula calculator constants) must survive
    unless an explicit port replaces them

### Gap-closing stories

- [x] R8: **Prioritized follow-up story list.** For every
  "❌ Missing" or "🟡 Partial without planned story" in R3,
  propose a new TB story with:
  - Tentative title
  - One-paragraph scope
  - Priority tier (High / Medium / Low) with justification
  - Which stalite3 feature(s) it addresses
- [x] R9: **Three-role rename priority verdict.** Explicit
  recommendation whether the deferred `chat` → `sales` rename
  rises to High priority or stays deferred, with reasoning.

### Deliverable

- [x] R10: **Written audit** at
  `docs/sync/stalite3-tb-parity-audit.md`. Structure:
  - Executive summary (one page)
  - Capability-by-capability table (R3)
  - Reverse direction (R4)
  - Sync mechanism recommendation (R5, R6)
  - Live-site preservation rules (R7)
  - Prioritized follow-up stories (R8)
  - Appendix: references to source code and docs consulted

## Acceptance Criteria

- [x] AC1: `docs/sync/stalite3-tb-parity-audit.md` exists.
- [x] AC2: The audit covers all 12 capability-area categories
      listed in R1. If any area is "no stalite3 capability
      found," the audit states that explicitly rather than
      silently omitting it.
- [x] AC3: Every stalite3 capability enumerated has a
      TB-coverage status (R3 taxonomy); none left as "to be
      determined."
- [x] AC4: The sync mechanism recommendation (R6) is
      specific — names the chosen mechanism (or hybrid) and
      states what triggers a sync (periodic cadence, release
      event, feature-driven, etc.).
- [x] AC5: The follow-up story list (R8) is specific — each
      proposed story is detailed enough that someone could
      create a `tb-us-NNN.md` entry from it directly.
- [x] AC6: Live-site preservation rules (R7) are enumerated
      and would be verifiable at sync time.
- [x] AC7: The three-role rename recommendation (R9) is
      yes/no with reasoning.
- [x] AC8: No stalite3 code or data is modified by this
      audit (`git diff /home/jeversole/stalite3/` is empty).
- [x] AC9: The audit does **not** include proprietary
      Stalite data (specific customer names beyond operator-
      facing context, specific pricing, specific internal
      process details). References to proprietary capability
      (e.g., "formula calculator for Stalite mix program")
      are at the capability level, not the content level.

## Design Notes

- **This is a spike — the output is a document and a
  decision, not code.** No endpoints added, no migrations
  run, no files copied.
- **Why audit-first instead of "just start porting."** Without
  an exhaustive audit, individual port stories miss things.
  stalite3 has accumulated capability over months; a
  piecemeal approach undercounts. Audit creates the
  comprehensive list; port stories pick it up one at a time.
- **Sync-forward is a real design decision.** Each candidate
  mechanism has concrete trade-offs:
  - Manual port: slow, error-prone, no explicit versioning
  - Cherry-pick / rebase: fast but requires compatible git
    histories, risks divergence
  - Release package: aligns with OT's Agent Release concept
    (TB-US-030), clean versioning, but requires release
    tooling
  - Shared library: cleanest architecture, longest to set
    up, requires Python packaging discipline
  The audit should produce a reasoned recommendation that
  accounts for TB's current maturity and stalite3's live-
  user constraints.
- **Live-site preservation is a hard rule.** stalite3 has
  real users adding training data NOW. Any sync mechanism
  that risks their work is unacceptable. R7 enforces the
  constraint explicitly.
- **Proprietary data boundary.** Stalite data is Stalite's
  property, licensed for EL internal testing only. The
  audit references stalite3's **capabilities** (what the
  code does) freely, but does not include stalite3's
  **content** (what the data contains) beyond what already
  appears in public TB stories or operator-facing summaries.
- **Three-role rename is the test case for sync model.** If
  TB renames roles and stalite3 inherits via sync, the sync
  mechanism must handle schema migrations. Testing the
  rename on this cycle validates the whole sync-forward
  pattern.
- **This spike is NOT TB-US-032 (the stalite OT example).**
  TB-US-032 (not yet drafted) is a downstream story that
  depends on this audit's output.

## Out of Scope

- **Executing any port** of stalite3 features to TB. The
  audit's recommended stories execute later.
- **Modifying stalite3's codebase** in any way. Audit is
  read-only.
- **Modifying TB's codebase** in any way. The audit's
  recommendations become new stories.
- **Building the stalite OT example** (TB-US-032). Depends
  on this audit.
- **Signing or executing a formal customer contract** with
  Stalite Corporation. Business concern beyond the audit.
- **IP review of any proposed public use** of Stalite data
  or capability. Legal process outside this spike.
- **Benchmarking** stalite3 performance against TB.
- **Branding tweaks.**

## Related

- [PM-US-027](../../../projmgmt/docs/user-stories/pm-us-027.md)
  — projmgmt-side addition of stalite3 to the board as
  Active. Companion to this story.
- [TB-US-022](tb-us-022.md) — OT coordinator. Audit findings
  may influence OT v0.1 handler definitions (particularly
  TB-US-025 quantitative, TB-US-026 lookup).
- [TB-US-024](tb-us-024.md) — OT audit log. Audit will
  compare against stalite3's query_logger.
- **Deferred role-rename story** — audit's R9 recommends
  whether to elevate this.
- (Future) **TB-US-032** — build the stalite OT example on
  TB master. Scoped against this audit's output.
- `/home/jeversole/stalite3/` — read-only subject of the
  audit.
- `MEMORY.md → workflow_projmgmt_pilot` — the pilot rule
  predicted this: projmgmt improvements land first; TB is
  now master for its own domain; the inheritance pattern
  this audit formalizes is similar in spirit.
- Deliverable: `docs/sync/stalite3-tb-parity-audit.md`.

**Completion Notes (2026-10-14).**

Audit delivered at
`/home/jeversole/trainingbench/docs/sync/stalite3-tb-parity-audit.md`
(~470 lines). All 10 Rs and 9 ACs met with one explicit nuance
on AC8:

- **AC8 ("git diff /home/jeversole/stalite3/ is empty")
  nuance.** At audit completion, stalite3's git working tree
  had **pre-existing modifications** (CHANGELOG.md,
  app_settings.py, main.py, rag_system.py, version.py) from
  the operator's independent stalite3 development — not from
  this audit. The audit ran read-only against stalite3; no
  stalite3 files were modified by this spike. The strict
  "git diff empty" check requires stalite3 to have been
  clean before the audit, which is an operator-side
  precondition rather than an audit-side obligation.

*Key audit findings (full detail in the deliverable):*

- TB and stalite3 share substantial module alignment —
  query_logger, session_tracker, training_manager,
  training_run_tracker, power_search, login_tracker,
  app_settings, database_manager, user_manager all have
  near-identical signatures across both.
- Four concrete gaps on TB side: role model (sales vs chat),
  routing config (`/settings/query-routes` + rag-prompt),
  stalite-specific formulas (should stay stalite-only), and
  public training-session endpoints (TB-US-019 addresses).
- Material architectural finding: **TB's
  `spreadsheet_calculator.py` is more generic than stalite3's
  `formula_calculator.py`** — TB wins on architecture;
  stalite3 wins on domain completeness. Neither is strictly
  "ahead."
- Recommended sync mechanism: hybrid **A (manual port)**
  through v0.1, moving to **C (Agent Release package)** for
  v0.2+. Mechanism B (cherry-pick) rejected. Mechanism D
  (shared library) deferred.
- Three-role rename (`chat` → `sales`): **HIGH priority
  verdict**, elevate from deferred.
- 8 follow-up stories proposed, 2 High / 4 Medium / 2 Low
  priority. Numbering suggestions (TB-US-032 through
  TB-US-039) are tentative; actual numbers assigned on
  creation.

*Material finding not pre-known:* stalite3 has
`/settings/query-routes` — user-configurable regex-pattern
routing with augmentation prefixes — which is **proto-OT
routing already live on stalite3**. TB-US-023's OT classifier
should examine stalite3's rule format for ideas (noted in the
audit's Section 3.8).
