# TB-US-090: Spike — Stalite code inspection + fact-check of catch-up design

**Status**: Backlog
**Created**: 2026-11-06
**Author**: Jesse Eversole
**Depends on**: [`stalite-catch-up.md`](../design/stalite-catch-up.md) design doc
**Blocks**: downstream stalite-side port stories (stalite is the
first TB-external use case for PEFT training)
**Commit hash(es)**: <filled in on completion>

## Story

As the operator of both TB and stalite, I want to **inspect
stalite's actual codebase** and turn the status-column hypotheses
in `docs/design/stalite-catch-up.md` §3 into verified facts, so
that when I draft the first stalite-side port story I'm working
from ground truth rather than fork-shape memory.

## Background

The stalite catch-up design doc (committed 2026-11-06) was
drafted without inspection of stalite's codebase. The "Stalite
status (hypothesis)" columns in §3 are inferred from:

- The fork-shape memory
  (`project_stalite_tb_fork_shape.md`): stalite predates TB's
  agent architecture; features shared at the pre-fork point
  include RAG, multi-LLM, training, prompt classification,
  spreadsheet calculator, document processing
- TB-US-086 backend feature audit findings (what TB has today)
- Operator conversation notes

Hypotheses that need verification before the first stalite-side
port story can be scoped honestly:

- "RAG query + vector store — present pre-fork"
- "Multi-LLM backbone — present pre-fork"
- "Multi-DB — present pre-fork"
- "PowerSearch — present pre-fork"
- "Document processing — present pre-fork"
- "Spreadsheet calculator — present pre-fork"
- "Spreadsheet formula EXTRACTION — stalite-only" (the one place
  TB is behind stalite per operator report)
- "Prompt classification — stalite-only" (TB has zero matches per
  TB-US-086 audit)
- "Training-run tracker — may have pre-fork variant; needs
  inspection"
- "API-key mechanism — may exist pre-fork or not; needs
  inspection"
- "User management v2 — may have pre-fork variant"
- Any pre-fork variants of training launch / adapter storage
  paths that would change the port priority

## Scope

Pure inspection + documentation. **No stalite-side code changes.**
No TB-side code changes beyond updating the catch-up design doc's
status columns.

### 1. Repo access + layout

- [ ] R1: Operator provides path to stalite's repo (local clone
      or remote). This story cannot fire without it.
- [ ] R2: Record stalite's top-level layout (`backend/`,
      `static/`, etc.) in a scratch note.
- [ ] R3: Record the approximate fork-point (last TB commit that
      also exists in stalite, if git history is shared; or a
      content-based proximity check if histories diverged
      completely).

### 2. Per-capability verification

For each hypothesis row in §3 of the catch-up doc, verify:

- [ ] R4: **RAG query + vector store** — confirm
      `backend/rag/rag_system.py` or equivalent exists;
      confirm vector store wiring.
- [ ] R5: **Multi-LLM backbone** — confirm Ollama / HuggingFace /
      OpenAI provider selection logic exists.
- [ ] R6: **Multi-DB** — confirm database_manager or equivalent;
      confirm multi-collection ChromaDB support.
- [ ] R7: **PowerSearch** — confirm external-LLM fan-out exists;
      note which services (Gemini / ChatGPT / Grok / others).
- [ ] R8: **Compare Results** — confirm A/B comparison path.
- [ ] R9: **Document processing** — confirm PDF / DOCX / XLSX +
      OCR support.
- [ ] R10: **Spreadsheet calculator** — confirm xlsx formula
      invocation path matches TB's `spreadsheet_calculator.py`
      shape or diverges.
- [ ] R11: **Spreadsheet formula EXTRACTION** — operator-reported
      stalite-only capability. Locate the implementation; capture
      enough detail to describe the port *to* TB (reverse
      direction).
- [ ] R12: **Prompt classification** — operator-reported stalite-
      only. Locate the classifier; capture category set + routing
      logic.
- [ ] R13: **Training surface** — does stalite have any training
      path today? If so, what shape (subprocess? direct call?
      tracker table?).
- [ ] R14: **Adapter storage** — if stalite has training, where
      do adapter weights live? Any versioning or just a directory?
- [ ] R15: **API-key mechanism** — present / absent / partial.
- [ ] R16: **User management** — shape of users / sessions /
      audit tables.
- [ ] R17: **UI shape** — pre-overhaul (likely) or has stalite
      done its own UI work post-fork? Note any UI additions
      stalite made that TB doesn't have.

### 3. Deliverables

- [ ] R18: **Update `docs/design/stalite-catch-up.md` §3**: flip
      every "(hypothesis)" status column to a verified value
      (**present**, **absent**, **partial**, or **differs** with
      a short note). Preserve the section header language
      indicating that values are now verified against
      <stalite-commit-sha>.
- [ ] R19: **Surface any surprises**: capabilities stalite has
      that TB doesn't (beyond the two already known —
      prompt-classification + spreadsheet-extraction). Each gets
      a line in a new §3.4 "Features stalite has that TB
      doesn't (reverse-port candidates)."
- [ ] R20: **Flag priority changes**: if inspection reveals a
      pre-fork variant that materially changes a priority in §4
      (e.g., stalite already has a training-run tracker in some
      form), update §4 accordingly.
- [ ] R21: **Draft the first stalite-side port story** as a
      follow-up to this one. Scope: whatever became
      the smallest honest unit of work given the verified
      inventory. Typically that's "add agents table + agent
      manager + idempotent migration to stalite" (priority 1
      step 1 of the catch-up doc §4).

### 4. Not in scope

- Any code change in stalite.
- Any new design docs beyond updating the existing catch-up doc
  and drafting one follow-up story.
- Decisions about which port priorities actually get executed —
  that's for the operator to resolve once this spike delivers
  the verified inventory.
- Reverse-direction port (stalite → TB) for prompt classification
  or spreadsheet-extraction: those are separate stories
  (TB-US-023 arc is already drafted for prompt classification;
  spreadsheet-extraction would need its own).

## Acceptance Criteria

- [ ] AC1: Every hypothesis row in catch-up §3 has a verified
      status against a specific stalite commit SHA.
- [ ] AC2: Any capability stalite has that TB doesn't — beyond
      the two already identified — is cataloged in a new §3.4.
- [ ] AC3: The catch-up doc's §4 port priorities are updated for
      any discoveries that change the order.
- [ ] AC4: A first stalite-side port story is drafted (not
      fired).
- [ ] AC5: The inspection notes do not contain proprietary
      stalite content (customer-service prompts, domain data,
      client identifiers). If any such content is discovered,
      it's acknowledged in the inspection notes without being
      reproduced in the TB-side design doc. (Stalite is
      proprietary; the catch-up doc lives in TB's public repo.)

## Design Notes

- **Why a spike and not just "do the port":** the catch-up
  doc's §3 hypotheses may be wrong in ways that change the
  priority ordering in §4. Firing a port story on top of wrong
  hypotheses risks wasting work on capabilities stalite already
  has in a different shape.
- **Why operator-gated:** this story needs stalite-repo access
  which may be gated by the operator's hardware / credentials.
  Draft-and-hold is the right posture until the operator is
  ready to execute.
- **Why the AC5 proprietary carve-out:** the catch-up doc is
  public (lives in TB mainline under Apache-2.0). This spike
  must not leak stalite's proprietary content into a public doc.
  Status columns say "present" or "absent" — they don't say
  "present, and here's the customer-service prompt."

## Related

- [`stalite-catch-up.md`](../design/stalite-catch-up.md) — the
  design doc this spike verifies
- `project_stalite_tb_fork_shape.md` — the memory motivating this
  spike
- [TB-US-086](tb-us-086.md) — the TB-side feature audit (model
  for how to structure the inventory)
- [TB-US-023](tb-us-023.md) — prompt classifier (reverse-port
  candidate; stalite has, TB doesn't)
