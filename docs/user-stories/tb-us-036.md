# TB-US-036: Spike — Deep-verify `query_logger.py` field parity between TB and stalite3

**Status**: Completed
**Created**: 2026-10-14
**Completed**: 2026-10-14
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

**Deliverable**: docs/sync/query-logger-parity-verification.md

## Story

As the operator closing out TB-US-031's audit findings, I want
`backend/api/query_logger.py` on both TB and stalite3 compared
line-by-line to confirm that the module (identical by
signature per the audit) is also behaviorally identical in
practice, so that TB-US-024's OT audit log work can safely
assume the pre-OT query log on both installs produces the same
field shape and so that no silent drift is hiding under the
"both have query_logger.py" line in TB-US-031's Section 3.6.

## Background

TB-US-031's Section 3.6 flagged that both TB and stalite3 have
`query_logger.py` with "near-identical signatures" and that
field-level parity was "not deep-verified." This spike closes
that uncertainty — either confirms parity or produces a port
story to close any gap found.

## Requirements

- [x] R1: **Diff the two files** byte-for-byte.
- [x] R2: **Analyze any divergence.** For each difference,
      classify: cosmetic (docstring/comment), behavioral
      (actual logic), or schema (fields written to log).
- [x] R3: **Port any trivial divergence** that aligns the two
      — treating stalite3 as a direct-port target if TB is
      ahead on correctness.
- [x] R4: **Produce a short verification report** at
      `docs/sync/query-logger-parity-verification.md`
      capturing: diff output, classification, port actions
      taken, verdict.

## Acceptance Criteria

- [x] AC1: Verification report exists.
- [x] AC2: Report states a specific verdict — parity confirmed,
      parity achieved after port, or parity requires a
      follow-up story (with specifics).
- [x] AC3: Any ports executed are reversible (snapshot before
      change if touching a live install).
- [x] AC4: TB-side has no file changes from this spike (the
      spike reads TB; it may change stalite3 to match).

## Design Notes

- **Spike, not implementation.** The deliverable is the
  report. Any port executed is a small side-effect, not the
  story's primary output.
- **Direction bias.** If divergence is found and one side
  is correct, the operator's `principle_role_names_describe_interface`
  memory + the TB-is-master posture mean **TB wins**;
  stalite3 is updated to match.
- **No behavior test needed if diff is cosmetic.** For a
  single-docstring difference, inspection is enough. For
  schema/behavior differences, the spike would need to add
  a test-send comparison; flagged conditionally.

## Out of Scope

- Changes to TB's `query_logger.py`.
- Comparing the content of actual log files (prior
  entries). Only the module behavior.
- Testing against future OT audit log (TB-US-024).
- Branding tweaks.

## Related

- Parent: [TB-US-031](tb-us-031.md) Section 3.6.
- Sibling (feature parity close-out): TB-US-033, 034, 035,
  037.
- Deliverable: `docs/sync/query-logger-parity-verification.md`.

**Completion Notes (2026-10-14).**

- Pre-spike diff revealed exactly one line of divergence —
  a docstring on line 73 referencing `(super, sales,
  training)` on stalite3 that was stale after TB-US-032's
  rename.
- Classified cosmetic. No behavioral or schema divergence
  found. Both files produce identical `queries.jsonl` and
  `master_query_log.jsonl` entries.
- Ported stalite3's docstring to match TB. Post-port MD5
  match confirms byte-identical files.
- Verification report at
  `docs/sync/query-logger-parity-verification.md` with full
  diff output, classification, schema confirmation, and
  rollback note.
- No TB-side file changes (TB was already correct).
- No stalite3 service restart required (docstring-only).
- No follow-up stories spawned. Section 3.6 of TB-US-031's
  audit closed cleanly.
