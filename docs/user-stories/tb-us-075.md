# TB-US-075: Demonstrate a performant math-example ladder via classical predictive-modeling methodology (train / validate / holdout)

**Status**: In Progress
**Created**: 2026-10-28
**Revised**: 2026-10-28 (methodology restructured to standard predictive-modeling train/validate/holdout per operator)
**Started**: 2026-10-28
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a TB operator preparing to show the Sweet Spot workflow with
**credible evidence**, I want **a before/after math-example
demonstration built on classical predictive-modeling methodology**
— baseline measurement to identify what's wrong, a training set
targeted at those specific failures, and out-of-sample
generalization check via a holdout — so that the demo is ironclad:
the measurement scheme is textbook, the pattern is reproducible,
and the result either confirms generalization or honestly reveals
memorization-only improvement.

## Background

TB-US-057 Phase B landed real baseline measurements: bare base,
adapter v2, and adapter v2 + RAG v3 all measured at **0.0 accuracy
on 200 GSM8K samples**. That's the honest floor documented in
`docs/pages/staged-progression.md`. It demonstrates the pipeline
works but not what TB is **for** — measuring the improvement from
targeted training.

TB-US-074 proved the training + experiment pipeline works
end-to-end on a fresh install.

**What's missing**: a demo that applies **standard predictive-
modeling methodology** to the training question — train / validate
/ holdout, error analysis, out-of-sample measurement — and shows
either real generalization or honest null result.

### The methodology (classical predictive modeling)

| Phase | Classical ML | What we do with the adapter |
|---|---|---|
| 1 | Define disjoint sets | Three GSM8K subsets: baseline test (fixed yardstick), holdout test (never-touched in training), training pool (candidate problems for the training set) |
| 2 | Measure baseline | Run bare LLM on baseline test; record which problems are right / wrong |
| 3 | Error analysis | Classify the wrongs to understand failure modes (secondary diagnostic) |
| 4 | Build training set | Pair each failed problem with its GSM8K ground-truth answer; this is the training corpus |
| 5 | Train the model | QLoRA fine-tune on the (problem, correct-answer) pairs |
| 6 | Measure in-sample | Re-run on the baseline test — baseline accuracy should climb substantially (we trained on exactly those failures) |
| 7 | Measure out-of-sample | Run on the holdout test — never-seen problems. Did the skill transfer? |
| 8 | Interpret | Generalization gap = baseline improvement − holdout improvement. Small gap = genuine learning. Large gap = memorization. |

This is textbook methodology. The novelty here is that TB wraps it
with versioned components + reproducible experiments so the whole
chain traces back to pinned artifacts, but the methodology
underneath is standard.

### Why RAG is Phase D (optional, after training-first demo)

Operator (2026-10-28): *"i'm not sure how a RAG could help [for
math]. maybe and that can later be tested."* — tested as a
secondary hypothesis after the main training-first demo. A
measurable null result is itself valuable for the public docs.

**Depends on:**
- TB-US-074 (closed) — training pipeline works
- TB-US-063 (closed) — adapter versioning
- TB-US-057 (closed) — flat-baseline framing + GSM8K harness v1
- Lab machine with ≥24 GB VRAM

**Blocks:** nothing hard; v0.1 can ship without this. Makes the
public demo materially stronger.

## Requirements

### Phase 1 — Define the three disjoint problem sets

The three sets must be chosen BEFORE any measurement, so the whole
study is pre-registered.

- [ ] R1: **Baseline test set** = 200 problems from GSM8K's **test
      split**. Fixed yardstick; this is the "validation set" the
      model gets measured against before AND after training.
      Suggestion: use the existing `backend/harnesses/data/math_eval_200.jsonl`
      which the current harness v1 points at (already sampled from
      GSM8K test split, seed-controlled).
- [ ] R2: **Holdout test set** = 200 problems from GSM8K's **train
      split** (yes, train split — unseen by the baseline test and
      guaranteed disjoint from any test-split problem). Sampled
      deterministically (seed=43 to be distinct from the training
      set's seed=42 convention). Store at
      `backend/harnesses/data/math_eval_200_holdout.jsonl`.
      Register as a new harness definition `v2` so experiments can
      pin it independently.
- [ ] R3: **Training-set pool** = all remaining GSM8K train-split
      problems (7,473 − 200 = 7,273). This is the pool from which
      we'll derive the actual training set in Phase 4 based on
      Phase 2's baseline failures. Store intent in a doc; don't
      preregister a specific subset yet (subset depends on
      baseline results).
- [ ] R4: **Pre-registration doc** at
      `docs/math-example/study-design.md` describing all three
      sets with their deterministic sampling parameters, seeds,
      and intended roles. **Written before Phase 2 runs.**

### Phase 2 — Measure the baseline (validation phase of ML)

- [ ] R5: **Run E1 (bare)** at `n_samples=200` against harness v1
      (the baseline test set). Capture full `per_sample` output.
- [ ] R6: **Classify each result**: `correct` or `wrong`. For
      every `wrong`, record:
      - The GSM8K problem ID (so we can look up the ground-truth
        answer for Phase 4)
      - The model's actual output
      - The ground-truth answer
      - The failure mode (secondary diagnostic — see Phase 3)
- [ ] R7: **Note the baseline accuracy**: X correct / 200. On the
      current shipped artifacts (TB-US-057 Phase B measurement),
      X was 0. Expect similar; if operator re-trains the base or
      uses a different base model, X will change.

### Phase 3 — Error analysis (secondary diagnostic)

- [ ] R8: **Classify failures into failure modes.** Taxonomy
      (same as earlier draft):
      - FM1: Model abandons the question (produces a new Q&A)
      - FM2: Format drift (no `#### N` or wrong placement)
      - FM3: Wrong arithmetic (steps structurally right; digits
        wrong)
      - FM4: Wrong reasoning (steps picked wrong operation)
      - FM5: Partial / truncated (hit max_new_tokens)
      - FM6: Something else
- [ ] R9: **Document in** `docs/math-example/baseline-analysis.md`:
      - Failure-mode distribution across 200 samples
      - 5–10 representative examples per mode
      - Determinism check: rerun once more (temperature=0 or
        very low); which failure modes are deterministic vs.
        stochastic

### Phase 4 — Build the training set from baseline failures

- [ ] R10: **Derive the training set composition.** The core
      training set is the problems the model failed in Phase 2,
      paired with their GSM8K ground-truth answers. If baseline
      accuracy was 0/200, the training set is 200 (problem,
      correct-answer) pairs.
- [ ] R11: **Augment IF the operator decides** (document choice
      with rationale in the strategy doc):
      - **Option A (minimal — recommended first iteration)**:
        just the 200-ish failures with correct answers. Clean test
        of the hypothesis.
      - **Option B (scale-up)**: add N additional problems from
        the training-set pool (R3) at similar failure-mode
        distribution. Larger training signal; muddier causal
        story.
      - **Option C (strategic sampling)**: pick training-set pool
        problems that LOOK LIKE the failed baseline problems
        (same operation types, same complexity). Operator-chosen.
- [ ] R12: **Document the strategy** at
      `docs/math-example/training-set-strategy.md`:
      - Composition decision (A / B / C) + rationale
      - Pre-registered hypotheses:
        - **H1**: Baseline accuracy on the 200-sample baseline
          test will improve from 0 → ≥50% (because we trained on
          those exact failures with their correct answers; this
          is a weak-generalization claim, closer to memorization
          threshold)
        - **H2**: Holdout accuracy on the 200-sample holdout will
          improve from current-bare-baseline to **at least 10%**
          — small but non-zero improvement = genuine
          generalization
        - **H3**: Generalization gap (baseline − holdout) will be
          large if Option A, smaller if Options B/C — pre-stated
          hypothesis
      - **Base-model decision**: stick with Llama 3.1 8B base OR
        swap to Llama 3.1 8B Instruct. Operator chooses +
        documents rationale.
      - **Training hyperparameters**: rank, alpha, lr, epochs,
        batch size — pre-stated.
- [ ] R13: **Register the training set** as
      `training_set_versions.v2+` on the math-example agent.
      Content hash + chunk count land per TB-US-052 flow.

### Phase 5 — Train the adapter

- [ ] R14: **Launch training** via `POST /training/runs/launch`
      (correct nested `hyperparameters` shape per F10 lesson).
      Expect hours on RTX 3090. Full training telemetry lands in
      `training_runs` + `training_run_metrics` + `training_run_logs`.
- [ ] R15: **Verify adapter files + auto-registration** as
      `adapter_versions.vN` (next version from current state).
- [ ] R16: **Release + promote** the new adapter.

### Phase 6 — Measure twice (in-sample + out-of-sample)

- [ ] R17: **Create E1b**: new experiment pinning
      `adapter_version_id = new`, harness v1 (same baseline test
      the Phase 2 bare run used). Run at `n_samples=200`.
      **This is the in-sample re-measurement.**
- [ ] R18: **Create E_holdout**: new experiment pinning
      `adapter_version_id = new`, harness v2 (the HOLDOUT test
      from R2). Run at `n_samples=200`.
      **This is the out-of-sample generalization check.**
- [ ] R19: **Classify both result sets** by correct/wrong + into
      FM1–FM6 taxonomy. Compare to Phase 2's baseline
      distribution.

### Phase 7 — Interpret and document

- [ ] R20: **Produce the measurement report** at
      `docs/math-example/measured-improvement.md`:
      - Three-column table: baseline / baseline-after-training /
        holdout — accuracy and FM distribution for each
      - **Generalization gap** = (baseline-after accuracy − holdout
        accuracy). State whether gap is small (genuine learning)
        or large (memorization-dominated).
      - **Hypothesis outcomes**: H1 / H2 / H3 marked met /
        partial / not-met with the measured values and brief
        interpretation.
      - **Causal attribution** section: based on the three
        numbers, what can we honestly claim the adapter learned?
      - **If generalization is poor**: that's a legitimate
        finding. Document and propose TB-US-076 ("Second-iteration
        strategy — larger / better-curated training set").
- [ ] R21: **Update** `docs/pages/staged-progression.md` with
      real numbers — the current placeholder 0.0 baseline gets
      replaced by baseline-before / baseline-after / holdout
      numbers. Public Pages site now tells a real-ladder story.

### Phase 8 — RAG hypothesis test (conditional, optional)

Only if Phase 7 completes and operator chooses to test RAG.

- [ ] R22: **Design a RAG manifest** targeted at the most common
      remaining failure mode (after Phase 7). E.g., if FM3 (wrong
      arithmetic) persists on holdout, RAG seeds with arithmetic
      reference tables; if FM4 (wrong reasoning), seed with
      worked-example chains by problem type.
- [ ] R23: **Register as rag_versions.v2+**, promote.
- [ ] R24: **Run two experiments**: baseline + RAG, holdout +
      RAG. Measure.
- [ ] R25: **Add Phase 8 section** to the measurement report
      with the Stage 2 numbers. Operator's "maybe RAG can help
      later" hypothesis gets a measurable answer.

### Phase 9 — Deliverables + roll-up

- [ ] R26: **Follow-up story if needed**: TB-US-076 for a second
      iteration if generalization is poor OR scope-cap close if
      ladder lit up on first try.
- [ ] R27: Commit all docs + any training-set / adapter / rag
      scripts to `main`. Push.

## Acceptance Criteria

- [ ] AC1: `docs/math-example/study-design.md` exists with all
      three sets pre-registered (R1–R4)
- [ ] AC2: `docs/math-example/baseline-analysis.md` exists with
      Phase 2's bare-baseline failures classified into FM1–FM6
- [ ] AC3: `docs/math-example/training-set-strategy.md` exists
      with H1/H2/H3 pre-registered + base-model + hyperparameters
      decisions documented
- [ ] AC4: Training set + adapter versions registered, released,
      promoted on the math-example agent
- [ ] AC5: Two new experiments (E1b in-sample + E_holdout
      out-of-sample) run at `n_samples=200`; results persist
- [ ] AC6: `docs/math-example/measured-improvement.md` exists
      with the three-column comparison + H1/H2/H3 outcomes +
      generalization-gap analysis + honest interpretation
- [ ] AC7: Public `docs/pages/staged-progression.md` updated
      with real numbers (replacing the 0.0 flat baseline)
- [ ] AC8: If generalization is poor, TB-US-076 drafted; if
      ladder lit up, close scope-cap is documented
- [ ] AC9: Operator attests the demo is defensible — the end-to-end
      chain (study design → baseline → training set → adapter →
      in-sample measurement → out-of-sample measurement →
      interpretation) is traceable and the methodology
      explicitly cites standard predictive-modeling discipline

## Design Notes

- **Why pre-register the three sets.** Classical ML discipline.
  Picking the holdout after seeing the measurements is p-hacking.
- **Why classify by failure mode (R8) as secondary.** Primary
  measurement is accuracy on baseline + holdout. Failure-mode
  taxonomy is diagnostic — it tells us WHY the adapter helped
  (or didn't), not WHETHER it helped.
- **Why the training set is derived from failures.** Operator's
  framing: train on exactly the problems where the model is
  wrong, with correct answers provided. This guarantees a
  signal on the baseline re-measurement (we're literally
  teaching those answers) while leaving the holdout as the
  honest generalization test.
- **Why holdout comes from GSM8K train split, not test.**
  Current harness v1 samples the baseline from GSM8K test split
  (TB-US-057 Phase A). GSM8K train split is a different pool
  with the same shape (grade-school word problems with step-by-step
  reasoning + numeric answers), making it an ideal holdout.
  Using train split for holdout + train split minus holdout for
  training-set pool keeps the whole study inside GSM8K.
- **Why generalization gap matters more than absolute accuracy.**
  Baseline accuracy going 0 → 80% after training on those exact
  problems proves the training LOOP works, nothing more. Holdout
  accuracy going 0 → 30% is the real signal. The ratio tells us
  what fraction is memorization vs. genuine learning.
- **Why one iteration only in this story.** Iterate-and-measure
  with no bounds is a research loop. One iteration gives a clean
  "done" criterion; TB-US-076 captures iteration 2 if needed.
- **Why Option A (minimal) is the recommended first iteration.**
  Clean causal story. If a 200-sample targeted training set
  shows generalization, that's a strong result on a tiny
  training budget. Operator can scale up in a second iteration
  with that signal already proven.
- **Why operator can't easily front-run the answer.** We don't
  know yet whether training on the specific failures generalizes
  — depends on whether the failures share underlying weaknesses
  (which training would fix) or are each independently random
  (which training wouldn't fix beyond the memorization effect).
  That uncertainty is why the study is worth running.

## Out of Scope

- Multiple training iterations (TB-US-076 if needed)
- Automated hyperparameter search / Bayesian optimization
- Comparing against external published adapters
  (MetaMath, Deepseek-Math, etc.)
- Reporting latency, throughput, VRAM efficiency
- Non-math domains
- Automated before/after UI dashboard
- Changes to GSM8K sampling / preprocessing — reuse existing
  TB-US-057 Phase A scripts

## Related

- [TB-US-057](tb-us-057.md) — honest flat baseline this builds
  on; its `docs/pages/staged-progression.md` placeholder gets
  updated here
- [TB-US-074](tb-us-074.md) — training pipeline fix making this
  runnable
- [TB-US-069](tb-us-069.md) — experiment-time per-version
  model-stack swap required for in-sample vs. out-of-sample runs
- [TB-US-063](tb-us-063.md) — adapter versioning
- [TB-US-056](tb-us-056.md) — harness subsystem (needed to
  register the holdout harness)
- Files touched (during execution):
  - `docs/math-example/study-design.md` (new, Phase 1 pre-reg)
  - `docs/math-example/baseline-analysis.md` (new, Phase 2+3)
  - `docs/math-example/training-set-strategy.md` (new, Phase 4)
  - `docs/math-example/measured-improvement.md` (new, Phase 7, 8)
  - `docs/pages/staged-progression.md` (update, Phase 7)
  - `backend/harnesses/data/math_eval_200_holdout.jsonl` (new, R2)
  - any sampling scripts committed under `scripts/`
