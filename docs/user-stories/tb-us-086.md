# TB-US-086: Spike — TB backend feature audit (what's there, what's UI-exposed, what to resurface pre-US-005)

**Status**: Backlog
**Type**: Design spike (produces a design doc; NO code change)
**Created**: 2026-11-05
**Author**: Jesse Eversole
**Depends on**: Nothing hard. Naturally lands before TB-US-005
(public v0.1 cut) because the US-005 pitch depends on what TB
actually exposes.
**Commit hash(es)**: <filled in on completion>

## Story

As a TB operator preparing for a public v0.1 launch (TB-US-005,
Proposed), I want **a clear audit of what TB's backend actually
has** — capabilities inherited from the stalite fork, features
added during the agent-architecture buildout, dormant modules
that lost UI exposure during the TB-US-018/TB-US-042 UI overhaul
— so that the US-005 launch pitch promises only what TB can
honestly demo, and so that the backlog of "resurface this
dormant feature in the new UI" is explicit rather than hidden.

## Background — the problem this solves

During strategic planning (2026-11-05 conversation), operator
clarified that TB inherited the stalite codebase at fork time
and therefore should already have many of the capabilities that
had been treated as "stalite-only":

- Multi-LLM backbone
- Spreadsheet-related capabilities (calculator wiring + document
  processing)
- Session tracking + query log (confirmed; TB-US-034 ported)
- Routes + prompts persistence (confirmed; TB-US-033/040 ported)

A quick grep confirmed significant backend presence (`llm_identifier`
is a pinnable field on every experiment; `spreadsheet_calculator.py`
and `document_processor.py` exist; multi-LLM references exist in
~7 backend files). What's unclear is:

1. **Which capabilities have UI entry points post-overhaul**
   (TB-US-018 + TB-US-042 rebuilt the UI around the new
   agent-management flows)
2. **Which are dormant backend-only** (code exists; no button
   reaches it)
3. **Which don't exist at all** (e.g., prompt classification —
   zero grep matches; matches TB-US-023's "Proposed" status)
4. **Which need to be resurfaced in the UI** to make the
   US-005 launch pitch defensible

Without this audit, US-005 planning either over-promises (ships
a pitch TB can't demo) or under-promises (ships a pitch narrower
than TB actually supports).

## Scope — this is a design spike

This story's deliverable is a **design document with a
prioritized resurface roadmap**. No code changes in this story.
The design doc becomes the input to subsequent implementation
stories (which may be multiple TB-US-NNN stories, one per
feature resurfaced).

### Deliverable: `docs/design/backend-feature-audit.md`

Expected structure (~3-5 pages):

1. **Audit methodology.** What constitutes "a capability" in
   this audit (a backend module + endpoints + any UI touchpoints),
   how dormancy is distinguished from missing (grep evidence +
   endpoint existence + UI entry-point search).

2. **Capability-by-capability table.** Each row:
   - Capability name (e.g., "multi-LLM routing," "spreadsheet
     formula extraction," "prompt classification")
   - **Backend presence**: file paths + module names + endpoints
   - **UI exposure**: which page/tab/button reaches it today,
     or "none"
   - **Status**: surfaced / partial / dormant / missing
   - **US-005 relevance**: pitch-critical / pitch-adjacent /
     post-launch / N/A
   - **Resurface effort estimate**: minor (connect existing
     endpoint to new UI button) / moderate (new UI tab +
     wire-up) / major (needs backend work too)

   Minimum capabilities to audit (based on operator's capability
   list + what the grep surfaced):
   - Multi-LLM backbone (llm_identifier pin + inference-time resolution)
   - Multi-LLM comparison (same prompt → multiple LLMs; is this a feature or just a code pattern?)
   - External-LLM API plugins (OpenAI, Anthropic, etc.)
   - Spreadsheet calculator invocation (TB-US-037 wired)
   - Spreadsheet formula EXTRACTION (parse xlsx → discover formulas)
   - Document processor (`document_processor.py` — what does it do?)
   - Prompt classification (operator: stalite-only; grep confirmed)
   - Multi-DB (operator: stalite feature; grep inconclusive)
   - RAG (confirmed in TB; what's the UI story?)
   - Session tracking (TB-US-034)
   - Query routes + persisted RAG prompts (TB-US-033/040)
   - PEFT adapter training (confirmed; UI post-TB-US-018 overhaul)
   - Sweet Spot experiment management (versioned components + experiments UI)

3. **Prioritized resurface roadmap for US-005.**
   - **Tier 1 — Must resurface before US-005 pitch is honest**:
     the features operator plans to lead with in the launch
     pitch
   - **Tier 2 — Resurface post-US-005 if dormant**: valuable but
     not pitch-critical
   - **Tier 3 — Backlog**: dormant + low-value or intentionally
     scoped out
   - Each tier line references a follow-up TB-US-NNN story
     (drafted during this spike OR flagged to be drafted later)

4. **Gaps that need backend work** (not resurface — net-new).
   The one clear gap: **prompt classification** (zero TB grep
   matches; TB-US-023 draft exists as "Proposed"). Are there
   others? The audit should flag them so US-005 scope is clear.

5. **Open questions.** Things the audit must resolve before any
   resurface story fires:
   - Does "multi-LLM comparison" mean compare-side-by-side
     (which requires UI work) or already-supported-via-separate-
     experiments (just a recommendation)?
   - Does `document_processor.py` do formula extraction, or
     something else entirely?
   - Is the TB-US-023 prompt-classification draft still the
     right shape, or does stalite's working classification
     suggest a different design?

6. **Scope boundaries.** What this audit does NOT cover:
   - Deep code review of each module (surface presence +
     purpose only)
   - Writing any new feature code
   - Reconciling stalite's specific implementation details with
     TB's (that's per-feature story work)
   - Front-end mockups / pixel work (that's per-feature story
     work)

### Not in scope

- Any code change — pure docs.
- Specific UI mockups — audit identifies what to resurface;
  implementation stories handle how.
- Stalite deep-dive (operator confirmed stalite is proprietary
  reference; audit focuses on TB codebase).
- Methodology-UI capabilities — those are TB-US-084's territory
  (research methodology support). Overlap possible; the two
  spikes should cross-reference.

## Requirements (single phase since this is a spike)

- [ ] R1: `docs/design/backend-feature-audit.md` exists with
      the 6-section structure above.
- [ ] R2: Capability-by-capability table with at least 13 rows
      (the minimum list above).
- [ ] R3: Each capability has a backend-presence entry (file
      paths + endpoints), UI-exposure entry, status, US-005
      relevance tag, resurface effort estimate.
- [ ] R4: Tier-1/Tier-2/Tier-3 roadmap identifies the Tier-1
      set that would unblock US-005.
- [ ] R5: For each Tier-1 feature, a follow-up TB-US-NNN story
      is drafted (status Backlog) OR flagged to be drafted.
- [ ] R6: Backend gaps section lists any net-new-feature work
      beyond resurface.
- [ ] R7: Open design questions explicitly listed; operator
      decision points flagged.
- [ ] R8: Cross-link from `docs/README.md` and from the US-005
      story (when it eventually fires, referenced by this audit).

## Acceptance Criteria

- [ ] AC1: Design doc at `docs/design/backend-feature-audit.md`,
      ~3-5 pages.
- [ ] AC2: Capability table covers ≥ 13 capabilities; every row
      has 5 populated columns.
- [ ] AC3: Prioritized 3-tier roadmap present.
- [ ] AC4: At least 3 Tier-1 implementation stories drafted
      OR explicitly flagged for drafting.
- [ ] AC5: Backend gaps section identifies the net-new work
      (prompt classification confirmed; others to-be-found).
- [ ] AC6: Scope boundaries explicit.
- [ ] AC7: Cross-links in place.

## Design Notes

- **Why this is a spike, not implementation.** The problem is
  "what IS TB today" — not "fix this specific thing." Jumping
  straight to resurface work risks fixing the wrong thing, or
  fixing features in the wrong order relative to US-005's
  actual needs.
- **Why it blocks US-005 soft-logically.** US-005 is Proposed
  deliberately — operator has been holding off because the TB
  pitch would overclaim or underclaim without this audit.
  Finishing this audit unlocks a grounded US-005 scope decision.
- **Why it also cross-references TB-US-084.** The methodology-UI
  spike proposed "cohorts, pre-reg forms, trial pages" as net-
  new UI work. Some overlap with this audit: Trial pages might
  surface existing experiment-management capabilities that are
  already backend-present but not currently a first-class UI
  concept. The two spikes should reference each other.
- **Why it's grounded in grep + operator knowledge.** The audit
  starts from what grep shows (observable code evidence) plus
  operator's recollection of what stalite had at fork time.
  Those two sources together give a reasonable first-cut
  catalog without exhaustive code review.

## Out of Scope

- Code: no backend, no frontend, no database work.
- Stalite feature comparison in depth — references stalite only
  as "where this feature was developed / exists working," not
  as a reference implementation to copy.
- The TB-US-023 OT redesign specifically — that's a different
  story's scope. This audit just notes the gap exists.
- Deployment / install docs.

## Related

- Motivated by TB-US-005 (public v0.1 cut, Proposed — deliberately
  held pending this audit)
- Cross-references:
  - [TB-US-084](tb-us-084.md) — Research methodology UI design
    spike. Some overlap with trial-page UI concepts.
  - [TB-US-083](tb-us-083.md) — System architecture doc. Provides
    the component framework this audit operates within.
- Historical context — stalite → TB fork:
  - TB-US-031 — Feature parity audit, stalite3 → TB master
  - TB-US-032 through TB-US-040 — the feature-parity close-out
    arc from Oct 2026
- TB UI overhaul:
  - TB-US-018 — Redesign TB UI, collapsible left-nav
  - TB-US-042 — White-theme refresh (Phase 2)
- The one clear gap:
  - TB-US-023 — Four-category prompt classifier (Proposed; no
    backend implementation yet)
