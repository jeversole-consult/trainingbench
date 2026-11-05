# TB-US-088: Spreadsheet calculator surface (make the existing capability user-visible)

**Status**: Backlog
**Created**: 2026-11-05
**Author**: Jesse Eversole
**Depends on**: TB-US-086 backend feature audit (completed)
**Soft-blocks**: TB-US-005 public v0.1 cut (if structured-data
handling is part of the pitch)
**Commit hash(es)**: <filled in on completion>

## Story

As a TB operator (or external user landing on a demo), I want
**the spreadsheet-calculator capability to be visible in the
UI** — not just silently wired into the Chat flow via the RAG
system's calculator hook — so that the "TB can do structured
data math" feature isn't buried behind a chat prompt that
happens to reference numbers.

Surfaced during TB-US-086 backend feature audit. TB has
`backend/api/spreadsheet_calculator.py` (SpreadsheetCalculator
class, openpyxl + pandas, formula invocation on structured xlsx
files) and it IS wired into `rag_system.py` via the `calculator`
hook (TB-US-037 closed 2026-10-14). But it is **invisible to
users**: no upload flow for "add a spreadsheet to this agent," no
"this agent has a calculator attached" indicator, and no demo
pointing at the capability.

## Background

Per the audit findings:

- **Backend**: `SpreadsheetCalculator` fully implemented;
  xlsx-only (noted pre-existing finding from TB-US-037).
- **Wiring**: when the RAGSystem is instantiated with a
  `calculator` callable + `TB_SPREADSHEET_PATH` env var pointing
  at an xlsx, the system transparently invokes the calculator
  for numerical queries within the chat flow.
- **UI**: zero mention. The chat tab produces calculator-augmented
  answers if the backend happens to be configured, but a user
  doesn't know this feature exists.

For an external-user demo (TB-US-005 pitch to ML researchers /
educators), this is a lost opportunity. Making the capability
visible costs a minor UI addition.

## Scope options

**Option A — Minimal: documentation + UI hint**
- A one-line note in the Chat tab explaining that uploaded
  xlsx files can be used as calculators
- A doc page describing the capability
- No new backend; no new UI flow
- **Minor effort**, ~2-3 hours

**Option B — Per-agent calculator attachment UI**
- Add a "Calculator" sub-section to the agent-management modal
- Operator can upload an xlsx and attach it to the agent
- Chat tab shows a badge "Calculator attached" when the active
  agent has one
- **Moderate effort**; needs backend endpoint for
  uploading-and-associating an xlsx with an agent (currently it's
  env-var-driven)

**Option C — Dedicated calculator demo tab**
- A new left-nav tab: "Calculator" with upload + test interface
- Non-agent-scoped; user uploads xlsx, asks questions, sees
  answers
- **Moderate effort**; new tab + UI + possibly new endpoint

**Recommended**: Option A for v0.1 (unblocks US-005 pitch with
minimal effort). Option B is a worthwhile follow-up if operators
want per-agent calculator management.

## Pre-registered hypotheses

### H88a — Users can discover the calculator capability

**Claim**: after this story ships (Option A), a user landing on
TB's Chat tab has a visible path to learn that spreadsheet
formulas can be invoked via chat.

**Signal**: user sees the Chat-tab hint, reads the doc, and can
describe the capability back.

### H88b — Backend wiring still works post-UI-change

**Claim**: whichever option is chosen, the existing `/query`
flow that invokes the calculator hook continues to work.

**Signal**: existing math-example chat queries that currently
produce calculator-augmented answers continue to do so.

## Requirements (Option A — minimal)

- [ ] R1: Add a one-line hint to the Chat tab (index.html
      `#chat-tab`) explaining the calculator capability. Example:
      "💡 TB can also invoke formulas from attached spreadsheets —
      see [doc]."
- [ ] R2: Create `docs/pages/spreadsheet-calculator.md` (or
      similar) with a 1-page explanation:
      - What it does (invoke xlsx formulas during chat)
      - How to set it up (`TB_SPREADSHEET_PATH` env var today)
      - Known limitations (xlsx-only per TB-US-037 finding)
      - Example queries
- [ ] R3: Link to the doc from the Chat-tab hint.
- [ ] R4: No backend change.
- [ ] R5: No new UI tab or modal.

### If Option B or C instead

- Design review needed
- Separate story draft

## Acceptance Criteria (Option A)

- [ ] AC1: Chat tab contains the calculator hint.
- [ ] AC2: The linked doc exists and is rendered via TB's docs
      system (`/docs/content`?) or Pages.
- [ ] AC3: Existing chat flow unchanged (regression check).
- [ ] AC4: External user (reading the Pages site + the Chat
      tab) can explain the capability unprompted.

## Design Notes

- **Why Option A for v0.1**: the capability is a credibility
  flag ("TB also handles structured data") rather than a
  headline. A 2-hour investment makes the feature visible without
  committing to a per-agent management flow that may want more
  design.
- **Why xlsx-only matters in docs**: TB-US-037 flagged this as a
  known limitation. Docs should disclose it, not hide it.
- **Open question**: does Option A give enough visibility for an
  external user, or does the pitch need Option B/C? Operator
  decision at fire time.

## Related

- [TB-US-086](tb-us-086.md) — backend feature audit (motivates)
- [TB-US-037](tb-us-037.md) — Wire spreadsheet_calculator into
  /query (completed 2026-10-14; this is the backend foundation)
- `backend/api/spreadsheet_calculator.py` — the capability
- Soft-blocks: [TB-US-005](tb-us-005.md) public v0.1 cut
