# TB-US-027: Mixed handler — naive decomposer / composer (v0.1)

**Status**: In Progress
**Created**: 2026-10-14
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As the operator of an OT-equipped TrainingBench agent, I want a
**mixed handler** that takes a prompt classified as mixed,
decomposes it into typed sub-prompts, routes each sub-prompt to
the appropriate single-category handler, and composes the
results into a single coherent response, so that compound
prompts (combining qualitative + quantitative, or lookup +
qualitative, etc.) don't fall through the cracks.

## Background

Per the OT context doc, mixed is the catch-all for prompts
that combine elements requiring multiple handlers. Example:
`"Who's the CFO and how much is our Q3 budget?"` — half
lookup, half quantitative. The handler's job is to
**decompose** that into
`["Who's the CFO?", "How much is our Q3 budget?"]`, route
each to the right single-category handler, and
**compose** the results into one answer.

**v0.1 is explicitly "naive".** The OT context doc notes that
"v0.1 implementation is naive; v0.2+ will develop more
sophisticated capability." This story honors that framing —
simple heuristic decomposition, simple string-join
composition. v0.2 and later get smarter decomposition
(LLM-assisted splitting, sub-prompt rewriting, dependency
resolution).

## Requirements

### Decomposition

- [ ] R1: **Heuristic decomposer.** Function
      `decompose(prompt: str) -> List[str]` that splits a
      mixed prompt on simple heuristics:
      - Conjunctions: `" and "`, `", and "`, `"; "`
      - Question boundaries: splits on `"? "` into separate
        questions (preserving the `?`)
      - Fallback: if no splitter matches, return
        `[prompt]` (treat as unsplittable — handler returns a
        best-effort response).
- [ ] R2: **Sub-prompt classification.** For each
      decomposed sub-prompt, call TB-US-023's
      `classify_prompt()` to determine its category.
- [ ] R3: **Sub-prompt dispatch.** Each sub-prompt is
      routed to its classified handler. **A sub-prompt
      classified as mixed by itself does NOT recurse** —
      the handler stops at one level of decomposition in
      v0.1. Mark the recursive mixed sub-prompt as
      "unresolved" in the composed response and log it in
      the audit entry.
- [ ] R4: **Composition.** Simple string-join composition:
      number each sub-prompt's response and concatenate.
      Example output:
      ```
      1. Jesse Eversole is the CFO.
      2. The Q3 budget is $4,250,000.
      ```
      Composition is deliberately mechanical in v0.1 —
      smarter composition (narrative stitching, redundancy
      removal, cross-reference resolution) is v0.2+.

### Handler entry point

- [ ] R5: **`handle_mixed(prompt: str, audit_entry: dict)
      -> str`** that:
      1. Decomposes.
      2. For each sub-prompt: classifies, dispatches,
         collects response.
      3. Composes.
      4. Logs decomposition + per-sub-prompt classifications
         + per-sub-prompt handler results to the audit entry
         via a `sub_entries` field.
      5. Returns the composed response.
- [ ] R6: **Audit log sub-entries.** The audit entry for a
      mixed-handler call has an additional nested field:
      ```json
      "handler": {
        "name": "mixed",
        "sub_entries": [
          {"sub_prompt": "...", "classification": {...},
           "handler": {...}, "response": "..."},
          ...
        ],
        "latency_ms": 123,
        "success": true,
        "error": null
      }
      ```
      Each sub-entry mirrors the single-handler audit shape
      from TB-US-024.

### No-decomposition fallback

- [ ] R7: **Fallback for unsplittable prompts.** If
      `decompose()` returns a single-element list (no split
      found), the handler routes the whole prompt through
      the qualitative handler as a best-effort and logs a
      `handler.decomposition = "unsplit"` marker. This is
      not ideal; v0.2 should classify the prompt more
      accurately in the first place.

### No-regression on sibling handlers

- [ ] R8: **No regression.** TB-US-025 / TB-US-026 /
      TB-US-028 are not modified by this story.

## Acceptance Criteria

- [ ] AC1: Calling `handle_mixed("Who's the CFO and how
      much is our Q3 budget?", audit_entry={})` returns a
      composed response like:
      ```
      1. The CFO is Jesse Eversole.
      2. The Q3 budget is $4,250,000.
      ```
      (With appropriate matching lookup + quantitative
      sources configured.)
- [ ] AC2: The audit entry for AC1's call has a
      `handler.sub_entries` array of length 2, each with
      its own classification and handler result.
- [ ] AC3: Calling with a prompt that has no decomposition
      split returns a best-effort qualitative response (R7)
      and logs `handler.decomposition = "unsplit"`.
- [ ] AC4: A sub-prompt classified as mixed by itself (bug
      case) does not recurse — it is logged as "unresolved"
      in the composed response.
- [ ] AC5: `handle_mixed()` is importable and callable from
      the OT router without HTTP.
- [ ] AC6: If a sub-handler raises, the mixed handler
      catches it, marks that sub-entry's `success = false`,
      and continues with remaining sub-prompts. One failing
      sub-prompt does not fail the whole mixed call.
- [ ] AC7: Total `latency_ms` for the mixed handler is the
      sum of its sub-handler latencies plus a small overhead.
      Verified by comparing against standalone sub-handler
      calls.

## Design Notes

- **Naive by design.** The OT context doc explicitly says
  v0.1 mixed handling is naive. Don't try to be clever
  here. The point of shipping v0.1 is to prove the
  architecture; the point of v0.2 is to make it smart.
- **Why heuristic splitting instead of LLM splitting.**
  v0.1 ships without a splitting LLM to keep the critical
  path fast and deterministic. An LLM-splitter is a
  legitimate v0.2 upgrade.
- **Why no recursion.** Recursive mixed-handling can blow
  up (a mis-classified prompt that keeps getting marked
  mixed loops forever). v0.1 explicitly stops at one level.
  v0.2+ can add a bounded-depth recursion with cycle
  detection.
- **Composition is deliberately mechanical.** A real
  narrative-stitching composer needs the LLM, and the
  whole point of OT is to NOT send everything through the
  LLM. Numbered-list composition is honest about what the
  v0.1 handler is: a dispatcher plus a staple.
- **Sub-entry shape in audit.** Mirroring the top-level
  shape makes export + analysis straightforward — a single
  parser can handle both single-handler and
  nested-sub-handler entries.
- **"Unsplit" prompts route to qualitative** because that's
  the most permissive fallback. If the LLM can give a
  partial answer, the user gets something; if the lookup
  or quantitative was wrong, they get a specific error.
- **Where the OT classifier should have caught it.** If a
  mixed prompt is actually not mixed (e.g., classifier
  false-positive), that's a classifier bug, not a
  mixed-handler bug. The handler's job is to handle
  what the classifier gives it; classifier improvements
  are separate.

## Out of Scope

- **LLM-assisted decomposition.** v0.2+ or later.
- **Recursive mixed handling** beyond one level.
- **Smart composition** (narrative stitching, dedup,
  cross-reference resolution).
- **Dependency ordering** between sub-prompts (sub-prompt A
  needs sub-prompt B's result to proceed). v0.1 runs
  sub-prompts independently.
- **Parallel sub-handler execution.** v0.1 is sequential.
  Parallel is an optimization for a later story.
- **Partial-result caching** across repeated mixed prompts.
- **Direct-invocation HTTP endpoint.**
- **Branding tweaks.**

## Related

- Parent: [TB-US-022](tb-us-022.md) — OT coordinator.
- Called by: [TB-US-028](tb-us-028.md) — OT router
  dispatches classified-mixed prompts here.
- Logs to: [TB-US-024](tb-us-024.md) — audit module (with
  nested sub-entries).
- Depends on: [TB-US-023](tb-us-023.md) — classifier
  (for sub-prompt classification), and all sibling handlers
  (TB-US-025, TB-US-026, TB-US-028) for sub-prompt dispatch.
- Verified by: [TB-US-029](tb-us-029.md) — the math example
  may include mixed prompts if a natural lookup+quantitative
  pattern fits the domain.
- Context: `docs/ot-context-for-claude-code_1.md` lines
  39–42 (category), 91–97 (handler, including the "naive at
  v0.1" acknowledgment).
