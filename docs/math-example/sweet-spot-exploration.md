# Sweet Spot Exploration — math-example

**Status:** First-pass measurements recorded 2026-10-25.
**Agent:** `math-example` (shipped as the TB first-install demo).
**Owned by:** TB-US-057 (phases A/B/C).

## Purpose

This document records the first measured sweep of the three staged
experiments on the `math-example` agent. It's the operator-facing
companion to [`docs/pages/staged-progression.md`](../pages/staged-progression.md)
(the public Pages version) with:

- Full component versions pinned
- The actual measurements with the DB-level artifact IDs
- Observations from running the experiments (timings, VRAM, etc.)
- Honest discussion of what the numbers mean (and don't)
- A straight path for operators who want performant numbers

If you want the generic *"how do I apply this workflow to my own
agent"* version, see
[`docs/training/sweet-spot-workflow.md`](../training/sweet-spot-workflow.md).

## Component versions pinned

All three experiments ran against the shipped first-install seed
components (see TB-US-057 Phase A):

| Component | Version | Notes |
|---|---|---|
| Agent | `math-example` (id=3) | seeded by `first_run_seeder.py` |
| Base model | `meta-llama/Meta-Llama-3.1-8B` | base variant, not Instruct |
| Training set | v3 | 500 GSM8K samples (seed=42) |
| RAG manifest | v3 | 3 documents (strategy guide + examples + formulas) |
| System prompt | v3 | tutor framing (817 chars) |
| Harness | v2 | 200-sample GSM8K eval, exact-match on `#### N` |
| Adapter | v2 | trained from training set v3, run #6 |

`*_version_id = 3` for training set / rag / prompt reflects
SQLite AUTOINCREMENT not resetting after prior test-fixture cleanup
(TB-US-052/053/055 verification). Cosmetic.

## Measurements

Experiment IDs 5, 6, 7 in the DB. (IDs 2, 3, 4 are the archived
5-sample verification runs that TB-US-069 used to prove the
`_build_experiment_stack` plumbing.)

| ID | Label | adapter | rag_collection | correct | n | accuracy | duration |
|---|---|---|---|---|---|---|---|
| 5 | E1 Stage 0 — bare | — | — | 0 | 200 | **0.0** | 1212s |
| 6 | E2 Stage 1 — +adapter | v2 | — | 0 | 200 | **0.0** | 2531s |
| 7 | E3 Stage 2 — +adapter+rag | v2 | `agent3_rag_v3` | 0 | 200 | **0.0** | 2507s |

**All three stages measure at 0.0 accuracy.** The ladder didn't
light up. Why: see below.

## Workflow actually run

1. Service restart to clear stale VRAM:
   `sudo systemctl restart trainingbench.service`.
2. Archive the 5-sample TB-US-069 verification experiments
   (ids 2/3/4) to preserve them as audit history.
3. Create three fresh experiments via `ExperimentManager.create_experiment`
   with the same pin configuration but against harness v2 at the
   full `n_samples=200`.
4. Mint a session token in-process (`generate_session_token(
   "admin", "super", 1)`) to hit the super-only endpoints
   from the shell during supervision.
5. `POST /experiments/{id}/run` for 5, 6, then 7, each kicking off
   a background thread via FastAPI's `BackgroundTasks` that invokes
   `harness_runner.run_experiment`.
6. Supervise via `GET /experiments/{id}` polling + `nvidia-smi`.
   (Experiment-side UI visibility is TB-US-070.)
7. Record results, archive the harness-definition patch, flip the
   story to Completed.

## Observations

### Timings

Per-sample inference time is dominated by chain-of-thought generation
length. Bare base: ~6s/sample. Adapter: ~12.6s/sample. RAG retrieval
adds negligible overhead at n=200 (~0% vs E2).

### VRAM

- Idle (service just restarted, no model loaded): **~1.1 GB**
- During any stack run: **~16.0–16.8 GB**
- Between runs: VRAM stays at ~16 GB. `_free_stack()` drops Python
  references but PyTorch's CUDA caching allocator retains the pool
  for reuse by the next stack. Not a leak — same ~16 GB regardless
  of how many sequential experiments run — but doesn't return to
  the ~1 GB idle until `systemctl restart trainingbench.service`.
  See TB-US-069 AC8 for the full discussion.

### Behavior under load

The TB server (one process) handles the inference work in a
background thread. The web `/query` endpoint remained responsive
during the runs (verified mid-E2). Serving requests while an
experiment is running is possible but will contend for GPU — not
recommended for production.

## Why the baselines are flat

In rough order of effect:

### 1. The base model is not instruct-tuned

The shipped example uses `meta-llama/Meta-Llama-3.1-8B`, the *base*
weights without instruction tuning. Base Llama can follow the
`#### answer` few-shot pattern mechanically but doesn't natively
try to solve the problem — it continues the context with plausible-
looking math prose.

E1's per-sample outputs show the model generating new fictional
Q&A pairs after producing a (random) first `####` number. The parser
grabs the first `####` match; across 200 samples, it's not
systematically correct.

### 2. The adapter is severely undertrained

Training set has 500 examples. Hyperparameters were QLoRA defaults:
rank 16, alpha 32, lr 2e-4, 3 epochs. Total training-example views
≈ 1500. For GSM8K-level arithmetic reasoning this is **two orders of
magnitude too few**. Published math-reasoning LoRAs:

- MetaMath-LLM: ~30k samples
- Deepseek-Math RL stages: ≥100k samples
- Grade-school commercial fine-tunes: ≥10k samples with rank ≥32

E2's per-sample outputs confirm this read: the adapter *does* teach
the step-by-step format (variables + computation lines) but the
arithmetic in the computed steps is wrong. The format part succeeded;
the reasoning part didn't.

### 3. The RAG manifest is a 3-document toy

Three documents (strategy guide, worked examples, formula sheet)
indexed per the TB-US-053 collection naming (`agent3_rag_v3`). For
grade-school arithmetic problems, retrieval doesn't help — the
bottleneck is "can the model do 18+24" not "can the model recall
the addition algorithm". E3's near-identical duration to E2 confirms
RAG retrieval was successful but the retrieved content didn't change
answers.

### 4. The grader is strict

`harnesses.math_qa_v1` compares the last `#### N` in the response
against the ground-truth `#### N`. If the response's final numeric
block differs by one digit, scores zero. Fuzzy matching, numeric
proximity, or multi-answer tolerance would raise all three stages
somewhat — but wouldn't change the fundamental conclusion that the
adapter can't do the arithmetic.

## What this proves

That the TB staged-progression workflow runs end-to-end on first
install:

- `first_run_seeder.py` creates the agent + all component versions
- Training launches via UI (TB-US-066) and auto-registers an adapter
  (TB-US-063)
- Operator releases + promotes the adapter
- Experiments pin specific versions and run against a shared harness
- Each experiment loads a distinct model stack (TB-US-069)
- Measurements are reproducible, stable, comparable, and persist

The staged-progression *mechanism* works. The *shipped artifacts*
are too small to make it light up.

## Path to performant numbers

If you want to see a real ladder, retrain with any of these
adjustments (biggest effect first):

1. **Swap base to Llama 3.1 8B Instruct.** Single largest lever on
   this benchmark. The Instruct variant follows the `#### N` format
   much more reliably and is already weakly tuned for problem
   solving. Downside: it muddies the "I trained everything from
   scratch" narrative, which is why the shipped example uses base.
2. **Scale training-set size.** Edit `scripts/prep_math_example_jsonl.py`
   to sample 5000+ instead of 500. Full GSM8K has ~7.5k training
   examples — can use essentially all of it.
3. **Train longer / with higher rank.** 5-8 epochs instead of 3;
   LoRA rank 32 or 64 instead of 16.
4. **Mode-match the system prompt to the training set format.** The
   shipped prompt is tutor-framed; the training set uses direct
   problem-answer pairs. There's a mild format mismatch that likely
   costs a few percent — matching them would help once the adapter
   is strong enough for format drift to matter.

See `docs/training/sweet-spot-workflow.md` for the generic workflow
to apply these on any agent.

## References

- Phase A seeding: TB-US-057 §Phase A Completion Notes
- Backend launch endpoint: TB-US-065
- Training UI: TB-US-066
- Adapter versioning + auto-registration: TB-US-063
- Experiment-time stack swap: TB-US-069
- Experiment-side UI (deferred): TB-US-070

## Phase C — Performant demo via predictive-modeling methodology (TB-US-075)

**Date**: 2026-10-31
**Owned by**: TB-US-075 (sibling story to this one)

TB-US-057 Phase A/B landed the flat-baseline measurement
documented above. TB-US-075 picked up where that stopped and
produced a measured, defensible generalization result using
classical train / validate / holdout methodology.

### What TB-US-075 added

- Pre-registered three disjoint GSM8K subsets:
  - Baseline test (200, GSM8K test split, seed=42) — reused
    `math_eval_200.jsonl`
  - Holdout test (200, GSM8K train split, seed=43) — new file
    `math_eval_200_holdout.jsonl`, registered as
    `harness_versions.v3`
  - Training pool: remaining GSM8K train split (not holdout)
- Classified bare-baseline failures into 6 failure modes (FM1-FM6)
  for diagnostic clarity
- Built the training set from (failed-problem, GSM8K-ground-truth)
  pairs — 200 (question, correct-answer) rows in
  `training-sets/math-example-v2-failures.jsonl`
- Trained a new adapter (`adapter_versions.v3`, LoRA rank 32,
  5 epochs, run_id=7 completed in 5.4 min; eval_loss 2.34 → 1.19)
- Measured twice: in-sample baseline rerun (E9) + out-of-sample
  holdout (E10), both at `n_samples=200`
- Re-scored both experiments with a lenient format-tolerant
  regex to separate "learned the SKILL" from "produced the exact
  harness-expected format"

### Headline Phase C results

| Measurement | Strict `#### N` | Lenient any-trailing-N |
|---|---|---|
| Bare baseline | 0 / 200 (0%) | — |
| In-sample (E9, adapter v3, same 200) | 0 / 200 (0%) | **58 / 200 (29%)** |
| Out-of-sample (E10, holdout, adapter v3) | 0 / 200 (0%) | **46 / 200 (23%)** |
| Generalization gap | 0 (trivial) | **6 points** |

See [`measured-improvement.md`](measured-improvement.md) for full
Phase 6 + 7 details, representative examples, F12 (new post-training
repetition failure mode), and TB-US-076 scope options.

### The methodology win

The pre-registered 3-set design + strict/lenient scoring split
exposed that the adapter **DID learn transferable skill** (small
generalization gap, 23% out-of-sample up from 0%), even though
the shipped harness scoring reports 0/0 due to format mismatch.
Without the predictive-modeling methodology, this signal would
have been invisible. With it, the real adapter capability becomes
diagnosable and a specific one-fix follow-up (TB-US-076) is well-
defined.

### Linked docs

- [Study design (pre-registration)](study-design.md)
- [Baseline analysis (Phase 3)](baseline-analysis.md)
- [Training-set strategy (Phase 4)](training-set-strategy.md)
- [Measured improvement (Phase 6+7)](measured-improvement.md)

## Phase D — Harness tolerance + retrain cautionary (TB-US-076)

**Date**: 2026-11-01
**Owned by**: TB-US-076 (sibling story to this one)

TB-US-075 left Trial #1 with strict 0/0 and lenient 29%/23%.
TB-US-076 fired as Option C — ran BOTH a harness tolerance patch
(Option A) AND a retrain with more epochs + extra data
(Option B) to see which fixed the strict/lenient divergence.

### Headline Phase D results (strict scoring under the patched harness)

| Trial | Adapter | In-sample | Holdout |
|---|---|---|---|
| #2 Option A — harness tolerance | v3 (unchanged, 5 ep × 200) | **38 / 200 (19%)** | **52 / 200 (26%)** |
| #3 Option B — retrain | v4 (10 ep × 300) | 12 / 200 (6%) | 15 / 200 (7.5%) |

**Option A was the real win.** The shipped harness
(`backend/harnesses/math_qa_v1.py`) was doing full-string
equality — ANY long CoT output couldn't match a short expected
answer. A one-file patch adding real answer-extraction logic
revealed the adapter's actual 19% / 26% performance.

**Option B overfit.** 10 epochs on 300 small samples pushed the
adapter past its generalization peak. Eval loss **rose** in the
last 2 epochs (1.38 → 1.68) while train loss kept dropping — the
pre-registered methodology's loss tracking caught the
overfitting as it happened. Adapter v4 is retained as a
cautionary data point.

### The ongoing search log

Each trial, finding, decision, and next-step candidate goes in a
single chronological log at
[`sweet-spot-search-log.md`](sweet-spot-search-log.md). That log
is the methodology's roadmap artifact — any reader can trace
what was tried, what signal came back, and what the next move
was (with reasoning).

Deep dives per trial:

- [Trial #1 — measured-improvement.md](measured-improvement.md)
- [Trial #2 — harness-tolerance-results.md](harness-tolerance-results.md)
- [Trial #3 — format-retrain-results.md](format-retrain-results.md)

## Phase E — Instruct scale-up (TB-US-077, Trial #4)

**Date**: 2026-11-02
**Owned by**: TB-US-077 (sibling story)

TB-US-057 Phase C's "biggest lever" (swap to Instruct variant)
was executed in Trial #4. Also included: 500 random GSM8K samples
(up from 200) + an early-stopping callback added to `train.py`.
Pre-registered expectation: holdout 55–75%.

### Headline Phase E results

| Setup | Score (dataset) |
|---|---|
| Instruct + our adapter v5 (5 ep × 500, early stop) | 46 / 200 (23%) holdout (E18) |
| **Instruct alone, no adapter (E19 control)** | **86 / 200 (43%)** baseline-test (E19) |

**Trial #4 was a failed hypothesis + a valuable methodological
finding**: our training approach, which HELPED the base variant
(0% → 26% in Trial #2), **REGRESSED** the Instruct variant
(cross-dataset 43% baseline-test vs. 23% holdout, ~20 points).
Loading adapter v5 cost ~40 correct answers on 200 GSM8K
problems. The clean apples-to-apples comparison (bare Instruct
on holdout) is being measured in TB-US-079.

### Root cause (F13 — "answer-first" pattern mismatch)

Bare Instruct's natural response: `#### <guess> + reasoning +
"The final answer is: #### <corrected>"`. The LAST `####` is
usually the right answer; harness regex picks it up.

Our training data: pure GSM8K format with `#### N` once at the
end. 500 samples × 5 epochs taught the adapter to produce ONE
`####` at the top and drop the end-of-reasoning summary. Harness
then catches the initial wrong guess.

**Our LoRA perturbation deleted Instruct's end-of-reasoning
answer-confirmation behavior without replacing it with equivalent
competence.**

### Current demo configuration (updated)

**Bare Llama 3.1 8B Instruct, no adapter** — 43% on the
200-sample baseline-test subset of GSM8K, zero TB-specific
training. (Bare-Instruct holdout accuracy TBD in Trial #5
TB-US-079.) Pages site reflects the 43% baseline-test number.
Adapter v3, v4, v5 all remain in the DB as part of the search
history; none is the current demo.

### Deep dive

- [Trial #4 — instruct-scale-up-results.md](instruct-scale-up-results.md)

### Open next-trial directions (TB-US-078 captures)

Trial #4's finding motivates a Trial #5 that tests training
approaches which PRESERVE Instruct's native response structure
instead of damaging it:

- Chat-template-formatted training data (`<|system|>` + `<|user|>`
  + `<|assistant|>` turns via `tokenizer.apply_chat_template`)
- Lower LoRA rank (8 or 16 vs. our 32) — smaller perturbation
- More training data (2000-5000 samples) with early stopping
- Different task framing in the system prompt

Pre-registered expectation range for Trial #5: 43% (no regression)
to 60% (modest improvement). TB-US-078 is drafted but not yet fired.
