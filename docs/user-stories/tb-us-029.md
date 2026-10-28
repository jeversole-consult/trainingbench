# TB-US-029: Verification example — math-domain OT agent

**Status**: In Progress
**Created**: 2026-10-14
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

**Deliverable**: training/examples/math-ot/verification-report.md

## Story

As the operator of TrainingBench, I want a concrete working
math-domain OT agent — labeled test queries, configured
calculator and lookup sources, and a verification report
demonstrating correct classification and handler execution
across all four categories — so that TB-US-023 through TB-US-028
are proven to work end-to-end on real inputs rather than only
in unit tests, and so that the first real OT example exists
as a reference for later domains.

## Background

Per the operator on 2026-10-14: *"an example will be needed to
test the new features."* This story is that example — a
test-fixture agent purpose-built to exercise every OT path.

Math was chosen as the first domain because:

- GSM8K is already in TB's benchmark set (natural quantitative
  coverage).
- Math has clean quantitative queries ("what is 2 + 2") that
  exercise the calculator framework (TB-US-025).
- Math also has qualitative queries ("explain long division")
  that exercise the RAG path (TB-US-028).
- A small math-reference lookup table (e.g., famous constants)
  exercises the lookup handler (TB-US-026).
- Compound prompts ("explain long division and compute
  847 ÷ 23") exercise the mixed handler (TB-US-027).

The deliverable is both a **working configured example** on
disk (so future stories can run it as a regression test) and a
**written verification report** (so the OT v0.1 arc can be
reviewed and signed off).

## Requirements

### Example scaffolding

- [ ] R1: **Directory**
      `training/examples/math-ot/` holds everything the
      example needs:
      - `config/calculators.json` or similar — not required
        if TB-US-025's calculator registry handles math_basic
        by default
      - `config/lookup/math-constants.json` — small lookup
        source: π, e, Avogadro, etc.
      - `labeled-queries.jsonl` — the test query set
      - `verification-report.md` — written report produced by
        running the example

### Labeled query set

- [ ] R2: **At least 20 labeled queries** in
      `labeled-queries.jsonl`, each line:
      ```json
      {"prompt": "...", "expected_category": "...",
       "expected_handler": "...", "notes": "..."}
      ```
      Coverage requirements:
      - ≥ 5 quantitative (`"what is 2+2"`, `"calculate 15%
        of 240"`, `"how much is 847 divided by 23"`, …)
      - ≥ 5 qualitative (`"explain long division"`, `"why
        does PEMDAS matter"`, `"what is the significance of
        pi"`, …)
      - ≥ 5 lookup (`"what is the value of pi"`, `"what is
        Avogadro's number"`, …)
      - ≥ 5 mixed (`"explain long division and compute 847
        / 23"`, `"what is e and what is 10 * e"`, …)
      - **At least one adversarial / ambiguous case per
        category** — a query that could plausibly be mis-
        classified, included to make the verification
        rigorous rather than a rubber-stamp.

### Running the verification

- [ ] R3: **Runner script** at
      `training/examples/math-ot/run-verification.py`
      (or similar) that:
      1. Reads the labeled query set.
      2. For each query: calls `/ot/query` (via HTTP or via
         direct function import — implementer picks).
      3. Collects: actual_category, actual_handler, response.
      4. Compares against expected_category /
         expected_handler.
      5. Emits a summary: pass count, fail count, breakdown
         by category.
- [ ] R4: **Verification report (deliverable).**
      `training/examples/math-ot/verification-report.md`
      containing:
      - Date of run
      - TB build / commit hash
      - Summary table (expected vs actual per query)
      - Per-category pass/fail counts
      - Any failures with analysis — was the classifier
        wrong? the handler wrong? the labeled query
        incorrect?
      - A verdict: ready-to-ship or needs-fix per OT v0.1
        gates
- [ ] R5: **Audit log inspection.** The report cites the
      OT audit log entries corresponding to each run (via
      `entry_id`), so a reader can navigate from the summary
      into the raw audit trail.

### Role

- [ ] R6: **Run the verification as an authenticated user**
      with appropriate role for each category. Super user
      is sufficient for v0.1 since all handlers are
      role-flat in TB-US-028.

### No regression

- [ ] R7: **Running the verification does not modify
      production state.** The example writes only to
      `training/examples/math-ot/` and to the OT audit log
      (which is append-only by design). It does not
      modify the users DB, projects.json, or any other
      operational state.

## Acceptance Criteria

- [ ] AC1: `training/examples/math-ot/labeled-queries.jsonl`
      exists with ≥ 20 entries meeting the category
      coverage requirements (R2).
- [ ] AC2: Running
      `python training/examples/math-ot/run-verification.py`
      (or equivalent) executes all queries against the
      OT router and produces the verification report at
      the deliverable path (R4).
- [ ] AC3: The verification report shows ≥ 80% pass rate on
      classification (expected_category == actual_category).
      v0.1 is a baseline; a passing rate below 80%
      indicates the classifier rules + LLM fallback need
      tuning before the OT arc closes.
- [ ] AC4: The verification report shows ≥ 90% pass rate on
      handler dispatch (expected_handler == actual_handler,
      conditional on correct classification). Mis-dispatch
      indicates a router bug (TB-US-028) rather than a
      classifier issue.
- [ ] AC5: Each failing query has an analysis entry in the
      report that identifies the root cause (classifier,
      router, handler) and either (a) proposes a fix within
      this story or (b) spawns a follow-up story reference.
- [ ] AC6: The report includes the `entry_id` for every
      query, enabling a reader to look up the raw audit
      log entry.
- [ ] AC7: The example directory is self-contained — a
      future reviewer can run the verification without
      consulting the TB codebase (beyond the running TB
      service providing `/ot/query`).

## Design Notes

- **Why 20 queries, not 100.** v0.1 verification is proof of
  architecture, not statistical confidence. 20 queries with
  deliberate category coverage + adversarial cases are
  enough to signal correctness. If the operator wants
  larger-scale verification later, that's a follow-up.
- **Adversarial cases matter.** Queries chosen because
  they *should* be hard are what make verification
  meaningful. Examples: `"compute the meaning of life"`
  (quantitative-sounding, actually qualitative); `"what is
  pi"` (lookup OR qualitative depending on taste —
  verification should expose which).
- **Why run against `/ot/query` and not inline function
  calls.** The HTTP path exercises the full stack:
  auth, rate limiting, serialization, error handling.
  Inline function calls would bypass real-world failure
  modes. If the implementer wants a faster-feedback inline
  mode during development, that's fine as a dev convenience
  — the official verification report uses HTTP.
- **The report is the deliverable.** The runner script is
  tooling; the report is the artifact that proves v0.1
  works. The audit log entries referenced in the report
  make it reproducible.
- **Why math first.** See Background. If math turns out to
  be too narrow or too focused on quantitative, a second
  example (legal or medical) could be added as a follow-up
  story in the OT arc.
- **This example will be re-run post-v0.2.** When a trained
  classifier adapter replaces the v0.1 rules + LLM, the
  same labeled query set re-runs; the comparison between
  v0.1 and v0.2 reports is a key output of v0.2.
- **No training here.** This story only verifies v0.1's
  OT routing. Any training (PEFT, LoRA) happens in other
  stories.

## Out of Scope

- **Verification examples for domains other than math.**
  Legal, medical, agricultural, cybersecurity — each is a
  separate story if that domain comes online.
- **Statistical / large-scale verification.** v0.1 is 20
  labeled queries. Statistical significance comes later.
- **Automated regression test harness** (run on every
  commit). The verification can be run manually at v0.1;
  CI integration is a later concern.
- **Performance / latency benchmarking** beyond what
  `latency_ms` already captures. If latency becomes a
  concern, open a specific perf story.
- **Model comparison** (same labeled set across different
  classifier LLMs). Separate story if useful.
- **Training a classifier adapter from this verification
  data.** That's v0.2.
- **UI for running / viewing the verification.** CLI is
  enough for v0.1.
- **Branding tweaks.**

## Related

- Parent: [TB-US-022](tb-us-022.md) — OT coordinator;
  verification example is R7 of the coordinator.
- Depends on: [TB-US-023](tb-us-023.md) (classifier),
  [TB-US-024](tb-us-024.md) (audit log),
  [TB-US-025](tb-us-025.md), [TB-US-026](tb-us-026.md),
  [TB-US-027](tb-us-027.md), [TB-US-028](tb-us-028.md)
  (handlers + router). All six must land before this story
  can produce a meaningful report.
- Consumed by: [TB-US-030](tb-us-030.md) — the operator
  workflow references this verification report as proof
  that the OT architecture works.
- Example directory: `training/examples/math-ot/`.
- Context: `docs/ot-context-for-claude-code_1.md` lines
  219–224 (verification considerations), 101–119 (why OT
  produces better results — the claims this verification
  tests).
