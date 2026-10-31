# TB-US-076: Reveal the real adapter v3 numbers — harness tolerance + optional retraining

**Status**: Proposed
**Created**: 2026-10-31
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a TB operator wanting the shipped math-example demo to show
real numbers, I want to **unmask adapter v3's actual
in-sample/out-of-sample accuracy** (29% / 23% under lenient
scoring per TB-US-075) that the current strict `#### N` harness
regex hides behind 0/200. Two options; operator decides at
execution time which to run.

## Background

TB-US-075 Phase 6 trained a math-example adapter (v3) on 200
GSM8K-failure examples and measured it on both the baseline test
and a held-out test. **Both experiments scored 0/200 under the
shipped harness** — but a lenient re-scoring of the stored
`per_sample` output revealed **29% in-sample / 23% out-of-sample
(6-point gap)**, which is the real adapter signal.

The gap between strict and lenient scoring is a **format
mismatch**: adapter v3 produces `Final Answer: N` consistently
instead of `#### N`, despite being trained on data that uses
`#### N` and prompted with a system prompt that explicitly
instructs `#### <answer>`. 5 epochs × 200 samples (~65 effective
gradient steps) wasn't enough to override Llama 3.1 8B's
pre-trained preference for `Final Answer:`.

Full analysis:
[`docs/math-example/measured-improvement.md`](../math-example/measured-improvement.md).

### Secondary finding worth addressing — F12

Several post-training outputs show the adapter correctly solving
the problem + then repeating `Final Answer: N` dozens of times
until `max_new_tokens`. Correct answer is present but the
inference pipeline doesn't stop at the first answer. Fix could
be inference-config (stop-token detection) or
training-time (termination examples).

**Depends on:**
- TB-US-075 (In Progress — closes with this draft) — data +
  methodology established

**Blocks:**
- Nothing hard. Shipped docs include the strict/lenient split so
  the honest story is already public.

## Scope options (operator chooses one at fire time)

### Option A — Harness tolerance (fast; recommended)

Modify `backend/harnesses/math_qa_v1.py`'s answer-extraction
regex to accept these formats, in priority order:

1. `#### N` (current)
2. `Final Answer: N` / `Answer: N` (case-insensitive, optional
   leading whitespace)
3. `#### <text>` where the text contains a numeric answer

Then re-run E9 and E10 (no retraining; use existing
`adapter_versions.v3`). Expected result: the lenient numbers
become the strict numbers — 29% / 23% / 6pt gap on the shipped
harness.

**Cost**: ~20 lines of regex changes to the harness module +
~90 min to re-run both experiments at `n_samples=200`.
**Risk**: harness becomes slightly looser; could accept wrong
answers if the model emits numeric content that's not actually
the final answer. Mitigation: tight regex, ordered priority.

### Option B — Retrain with format emphasis (slow; more thorough)

Retrain a new adapter (`adapter_versions.v4`) with changes
aimed at driving the `#### N` format:

- More epochs (10 instead of 5)
- Lower learning rate on later epochs (cosine decay)
- Add format-drill examples (short Q/`#### N`-only pairs) to
  the training set
- Possibly add stop-token hint to inference config to kill
  F12 repetition behavior

**Cost**: training retraining = ~10-15 min; two re-measurements
= ~90 min. Total ~2 hours.
**Risk**: may still not fully override Llama's `Final Answer:`
preference even with more training. If so, falls back to
Option A anyway.

### Option C — Both

Fast first (Option A) → see the real numbers → decide if
retraining is worth it (Option B). This is probably the
sanest path: Option A pays for itself in diagnostic value.

## Requirements

All Rs are conditional on which Option(s) run.

### Option A path

- [ ] R1: Modify `backend/harnesses/math_qa_v1.py`'s answer
      extraction to the three-level priority order above.
- [ ] R2: Register as `harness_versions.v4` on agent 3
      (harness definition_json unchanged except the module
      references a different parsing function OR via a
      definition flag). Operator decides whether to version-up
      the harness (recommended for traceability).
- [ ] R3: Create 2 new experiments (E9c in-sample, E10c
      holdout) pinning adapter v3 + harness v4 + prompt v3.
- [ ] R4: Launch sequentially + wait (chain daemon or manual).
- [ ] R5: Document in a new `docs/math-example/harness-tolerance-results.md`
      with before/after strict scoring numbers.
- [ ] R6: Update `docs/pages/staged-progression.md` with the
      new table — strict scoring now shows real numbers.
- [ ] R7: Update `docs/math-example/measured-improvement.md`
      with a Phase D section pointing at R5's results.

### Option B path

- [ ] R8: Build a format-drill supplementary training set
      (format-only Q→`#### N` pairs; ~50-100 rows). Register
      as `training_set_versions.v5` on agent 3.
- [ ] R9: Train adapter v4 with the enhanced config.
- [ ] R10: Release + promote v4 (optionally keeping v3 as
      displaced-not-archived).
- [ ] R11: Run two new experiments pinning adapter v4; measure
      both strict and lenient.
- [ ] R12: Document in a new
      `docs/math-example/format-retrain-results.md`.

### Cross-cutting

- [ ] R13: Address F12 (repetition failure mode) if it
      persists after R6/R11. Candidate: add stop-token for
      repeated identical lines to inference config.

## Acceptance Criteria

- [ ] AC1: If Option A ran: `docs/math-example/harness-tolerance-results.md`
      exists; strict-scoring shows ≥25% in-sample and ≥20%
      out-of-sample on E9c/E10c.
- [ ] AC2: If Option B ran: `docs/math-example/format-retrain-results.md`
      exists; adapter v4 shows ≥20% strict in-sample.
- [ ] AC3: `docs/pages/staged-progression.md` updated with the
      new real-numbers table.
- [ ] AC4: `docs/math-example/measured-improvement.md` updated
      with Phase D section pointing at the new results.
- [ ] AC5: F12 (repetition failure mode) addressed or explicitly
      scope-deferred to a separate story.
- [ ] AC6: Honest "we had a format mismatch; here's the fix"
      narrative lands on the public Pages site.

## Design Notes

- **Why "fast first" (Option A).** Harness tolerance costs ~20
  lines of regex + ~90 min of GPU; produces a 100% diagnostic
  signal (the lenient numbers become visible as strict numbers).
  Low cost, high clarity.
- **Why Option B is still worth considering.** A format-drilled
  adapter would show "trained adapter correctly uses the shipped
  harness's expected format" — a cleaner story than "we had to
  tolerate the adapter's format in the harness". If the public
  demo matters a lot, Option B produces the stronger artifact.
- **Why F12 is captured here, not a separate story.** F12 is
  tightly coupled to adapter v3's behavior. If Option B produces
  a new adapter, F12 might disappear naturally; if Option A keeps
  v3, F12 is still with us. Either way, resolution is scoped to
  this story.
- **Why not retrain from scratch with completely different
  base/config.** That's TB-US-057 Phase C's "Path to performant
  numbers" territory (swap base to Instruct, etc.). TB-US-076 is
  about **revealing adapter v3's real signal**, not about chasing
  state-of-the-art accuracy. Different story.

## Out of Scope

- Swapping base model to Llama 3.1 8B Instruct (that's a bigger
  change; separate story)
- Automated hyperparameter search
- Multi-run averaging for determinism (one run per experiment)
- RAG augmentation (TB-US-075 Phase 8 — still skippable)

## Related

- [TB-US-075](tb-us-075.md) — produced the format-vs-skill
  divergence this story resolves
- [TB-US-057](tb-us-057.md) — ships the shipped math-example
  harness that will get the tolerance update under Option A
- [TB-US-056](tb-us-056.md) — harness subsystem; version-up
  pattern follows TB-US-056 R3's lifecycle
- Files touched (during execution):
  - `backend/harnesses/math_qa_v1.py` (Option A R1)
  - `harness_versions.v4` registration (Option A R2)
  - `docs/math-example/harness-tolerance-results.md` (Option A R5)
    OR `docs/math-example/format-retrain-results.md` (Option B R12)
  - `docs/pages/staged-progression.md` (R6)
  - `docs/math-example/measured-improvement.md` (R7)
