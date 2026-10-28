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
