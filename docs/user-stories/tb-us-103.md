# TB-US-103: Decomposed-accuracy harness infra (per-schema reporting + multi-seed scaffold)

**Status**: Skeleton — awaiting SL-US-011 kickoff to drive the
specifics of the harness contract.
**Created**: 2026-11-09
**Author**: Jesse Eversole
**Companion**: [SL-US-011](../../../stalite3/sl-us-011.md) (the
first client-side research study using this infra; stalite-private)

## Story

As a TB operator (any TB user, not stalite-specific) running a
PEFT research study on a small domain-specific dataset, I want the
harness runner + comparison modal to report **decomposed accuracy
by schema / primitive / complexity** — not just aggregate — so I
can tell whether PEFT lifts the baseline *overall* or lifts
*specific sub-classes* of problems.

This generalizes the methodology lesson from TB-US-092 (format-
decoding compensation can hide behind aggregate numbers) and the
one from the Claude-chat exchange on 2026-11-09:
> "Measure what specifically improved. Decompose accuracy by
> schema, by primitive, by complexity level. Don't settle for
> aggregate numbers."

## Background

The math-example arc measured accuracy as a single aggregate
number per experiment. That worked for a single-schema benchmark
(GSM8K is all one type: grade-school word problems). It fails
when the client dataset has mixed schemas — e.g. stalite's
customer-service dataset has lookup / quantitative / mixed types,
each with different performance characteristics.

The per-run report should:
- Bucket samples by a `schema` field each sample carries
- Compute accuracy per bucket
- Expose per-bucket means on the experiment detail page + compare
  modal
- Support N-way decomposition (schema is just the first axis;
  operator may also want primitive or complexity)

## Scope

### Harness-side contract

- [ ] R1: Extend the harness module signature so each `per_sample`
      entry can carry arbitrary tag fields:
      ```python
      per_sample.append({
          "question": ..., "expected_answer": ..., "actual_answer": ...,
          "correct": bool,
          "schema": "quantitative",      # new: arbitrary tag
          "primitive": "tonnage_from_volume",   # new
          "complexity": "two-step",       # new
      })
      ```
- [ ] R2: Dataset JSONL format supports the tag fields alongside
      the existing `{question, expected_answer}`. Harness module
      copies them through to per_sample output.
- [ ] R3: `math_qa_v1.py` (already in TB) stays backward-compatible
      — if a tag field is absent in input, it's absent in output.
      No GSM8K re-labeling required.

### Runner / results aggregation

- [ ] R4: Extend the harness_runner's final results dict with
      optional decomposition:
      ```python
      {
          "metric": "accuracy", "value": 0.72, "n_samples": 200,
          "per_sample": [...],
          "decomposed": {
              "schema": {
                  "lookup": {"correct": 18, "total": 20, "accuracy": 0.90},
                  "quantitative": {"correct": 7, "total": 13, "accuracy": 0.54},
                  "mixed": {"correct": 1, "total": 2, "accuracy": 0.50},
              },
          },
      }
      ```
- [ ] R5: Harness config honors `decompose_by: ["schema", ...]` to
      control which tag fields get aggregated (default: everything
      present on at least 50% of samples).
- [ ] R6: Backwards compat — absence of `decomposed` key means
      operator ran against an un-tagged dataset, UI falls back to
      aggregate-only display.

### UI surface (TB-side `experiments.html` detail view)

- [ ] R7: Experiments-page detail view: when `_stack.results` has
      `decomposed`, render a per-bucket breakdown table beneath
      the main metric panel.
- [ ] R8: Compare modal (`training_runs.html`): when two runs
      both have `decomposed` output on the same schemas, show
      per-schema rows in the compare table so operator can see
      *per-schema* delta rather than just aggregate.
- [ ] R9: Winner highlight per schema row works the same way
      TB-US-091's aggregate highlight does.

### Multi-seed scaffold

- [ ] R10: TB already has subprocess-per-experiment (from TB-US-070
      Phase 2). Expose a lightweight wrapper
      `scripts/tb_multi_seed_runner.py` that takes a list of
      `{condition_label, experiment_pins}` entries and fires N
      seeds per condition serially. Records seed index on each
      experiment as a tag. Reusable for any study — not
      stalite-specific.
- [ ] R11: Reports a per-condition summary when done:
      `{condition: mean, SD, n_seeds, pooled_SD vs each other
      condition}` so operator can evaluate pre-registered
      hypotheses without hand-math.

### Documentation

- [ ] R12: Operator-facing doc at
      `docs/pages/decomposed-accuracy.md` describing:
      - Why aggregate accuracy hides sub-class effects
      - How to tag dataset samples
      - How to interpret the decomposed table
      - Link to TB-US-092 as the motivating cautionary tale
- [ ] R13: Methodology section in `docs/math-example/methodology.md`
      updated to note "decompose by schema when the dataset has
      multiple sub-classes" alongside existing discipline
      (chat-template, multi-seed, baseline sanity-check).

## Acceptance Criteria

- [ ] AC1: Harness module + runner support `per_sample` tag fields
      passthrough.
- [ ] AC2: Results dict carries `decomposed` when any tag is
      present on ≥50% of samples; absent otherwise.
- [ ] AC3: `math_qa_v1.py` unchanged in behavior for the GSM8K
      arc — existing experiments re-run produce same aggregate.
- [ ] AC4: `experiments.html` detail view renders decomposed table.
- [ ] AC5: `training_runs.html` compare modal supports per-schema
      row comparison.
- [ ] AC6: Multi-seed runner helper exists + usable by any study.
- [ ] AC7: Operator doc explains + justifies.

## Not in scope

- Any stalite-specific dataset or schema — those stay in SL-US-011.
- Classifier-based schema detection (automatic labeling of samples)
  — this story takes tags as given input.
- New experiment UI primitives beyond what TB-US-070 + TB-US-087 +
  TB-US-091 already shipped.

## Design Notes

- **Why in TB mainline rather than stalite-only**: the next three
  TB users running a PEFT study on small-domain data will hit the
  same question (does aggregate hide sub-class effects?). This is
  trunk infrastructure, not client-specific.
- **Why tags are free-form strings rather than an enum**: different
  clients will have different schema vocabularies (stalite has
  lookup/quantitative/mixed; another might have
  retrieval/calculation/reasoning). The harness treats tags
  opaquely; UI renders whatever keys appear.
- **Multi-seed decomposed stats** — at the SL-US-011 scale
  (n=35 held-out, 4 seeds per condition), the multi-seed statistics
  may already be noisier than the per-schema subset sizes can
  support. The report should surface confidence intervals when
  bucket size is small so operator knows which "deltas" are
  interpretable.
- **Upstream-to-TB flow**: this is the first "client-driven
  research produces TB-trunk infra" cycle. Operator's long-term
  pattern: proprietary data stays in clients' private forks;
  methodology artifacts flow upstream to TB mainline where any
  future TB user benefits.

## Related

- [SL-US-011](../../../stalite3/sl-us-011.md) — motivating client
  study
- [TB-US-092](tb-us-092.md) — methodology framework (format
  mismatch + multi-seed insufficiency)
- [TB-US-081](tb-us-081.md) — multi-seed noise envelope
- [TB-US-070](tb-us-070.md) — experiments UI base
- [TB-US-087](tb-us-087.md) — version lifecycle UI
- [TB-US-091](tb-us-091.md) — accuracy backfill + compare-modal
  source-experiment deep-link (the pattern this extends per-schema)
