# Sweet Spot Search Log — math-example

**Append-only lab notebook** tracking every decision, trial, and
finding in the sweet-spot search for the math-example agent. Each
entry records WHAT was tried, WHAT came back, WHAT was concluded,
and WHAT came next (with reasoning).

**Why this log exists**: TrainingBench's purpose is iterative
sweet-spot search. The methodology isn't just the measurement
mechanics; it's the discipline of logging decisions + findings
+ next-steps so a reader can trace the whole exploration
without having to reconstruct it from scattered artifacts. The
log IS the roadmap.

**How to read**: entries are chronological, newest at the bottom.
Each entry links to its deep-dive doc + the DB artifacts
(experiments, training runs, versions) that preserve the raw data.

**How to add**: when a trial completes, append an entry. Follow
the 4-field format: `What we did / What we found / What we
decided / Rationale`. Keep it tight; link to deep dives rather
than inlining.

---

## 2026-10-28 — Decision #1: methodology

**What we did**: Pre-registered the classical predictive-modeling
train / validate / holdout methodology for the sweet-spot search.
Three disjoint GSM8K subsets: baseline test (200, test split,
seed=42) + holdout (200, train split, seed=43) + training pool
(remaining train split).

Hypotheses pre-registered BEFORE any trial ran:

- **H1** — Baseline rerun post-training ≥ 50% (close to
  memorization threshold)
- **H2** — Holdout post-training ≥ 10% (generalization signal)
- **H3** — Small gap (≤15 pt) = genuine learning; large gap
  (>40 pt) = memorization-only

**What we found**: N/A (pre-trial)

**What we decided**: Fire TB-US-075 to execute the first trial —
train an adapter on 200 baseline failures, measure in-sample +
out-of-sample.

**Rationale**: Pre-registration locks in interpretation BEFORE
seeing results, preventing post-hoc rationalization. Each
hypothesis has a specific numeric threshold so results are
unambiguously met / not met.

**Artifacts**:
- [`study-design.md`](study-design.md) — the pre-registration
- `TB-US-075` story

---

## 2026-10-31 — Trial #1: adapter v3 (5 epochs × 200 failures)

**What we did**: Trained `adapter_versions.v3` on
`training_set_versions.v4` (200 GSM8K-test-split failures paired
with GSM8K ground-truth CoT answers). Hyperparameters:
LoRA rank 32, alpha 64, lr 2e-4, 5 epochs, batch 4,
gradient_accum 4. Base: Llama 3.1 8B (base variant).

Measured twice with the shipped `harnesses.math_qa_v1`:
- E9 (expt_id=9, in-sample): adapter v3 + harness v2 (baseline
  test, n=200)
- E10 (expt_id=10, out-of-sample): adapter v3 + harness v3
  (holdout, n=200)

**What we found**:
- Training loss curve: eval_loss 2.34 → 1.19 across 5 epochs
  (converged)
- E9 strict: **0 / 200** (0%)
- E10 strict: **0 / 200** (0%)
- E9 lenient re-score (any trailing number): **58 / 200 (29%)**
- E10 lenient re-score: **46 / 200 (23%)**
- **Generalization gap under lenient: 6 pt (29 − 23)** — well
  under H3's 15-pt "strong result" threshold

**Diagnostic**: adapter learned the step-by-step reasoning
pattern (correct arithmetic in representative outputs) but
produces `Final Answer: N` instead of `#### N`. 5 epochs × 200
samples (~65 effective gradient steps) wasn't enough to override
Llama 3.1 8B's pre-trained preference for `Final Answer:`.

Also surfaced F12 — new failure mode: adapter occasionally
solves correctly then repeats `Final Answer: N` dozens of times
until max_new_tokens.

**What we decided**: Fire TB-US-076 as Option C (both A + B)

- **Option A** — patch the harness to accept common final-answer
  formats, re-measure adapter v3
- **Option B** — retrain adapter with more epochs + extra
  format-emphasis data to drive `#### N` format

**Rationale**: Can't tell from this result alone whether the
problem is (a) harness is too strict about format, (b) training
undersized, or both. Testing both options reveals the truth.

**Verdict against H1/H2/H3**:
- H1 (≥50% in-sample): not met either way
- H2 (≥10% holdout): **MET under lenient; not under strict**
- H3 (small gap = learning): **MET under lenient** (6 pt gap)

**Artifacts**:
- [`measured-improvement.md`](measured-improvement.md) — deep
  dive for Trial 1
- Experiments 9 + 10 in `backend/db/trainingbench.db`
- Training run 7 in `training/runs/runs_tracker.db`
- `adapter_versions.v3` in-tree at `adapters/math-example/v3/`
- `TB-US-075` closed with these results

---

## 2026-10-31 — Trial #2: harness tolerance (TB-US-076 Option A)

**What we did**: Patched `backend/harnesses/math_qa_v1.py` with
real answer-extraction logic (3-priority regex: `#### N` →
`Final Answer: N` → trailing number). Registered as
`harness_versions.v4` (baseline) + `harness_versions.v5`
(holdout). Re-ran against adapter v3:

- E11 (expt_id=11, in-sample): adapter v3 + harness v4, n=200
- E12 (expt_id=12, out-of-sample): adapter v3 + harness v5,
  n=200

**What we found**:
- E11 strict (patched harness): **38 / 200 (19%)**
- E12 strict (patched harness): **52 / 200 (26%)**
- **E12 holdout > E11 in-sample** — unusual but consistent
  within 200-sample noise

**Diagnostic**: Discovered the original harness wasn't even
extracting `#### N` — it was doing a FULL-STRING equality after
whitespace normalization. ANY long model output couldn't match a
short expected answer. The 0/200 in Trial #1 wasn't about `####`
vs. `Final Answer:`; it was that NOTHING would match on a long
output. Patch adds real extraction logic.

**What we decided**:
- Option A validated — the real adapter v3 numbers (19% /
  26%) are now visible on the shipped harness
- Proceed to Option B retrain as planned (even though Option A
  already revealed the real signal, Option B's retrain-with-
  format-emphasis is still a planned test)

**Rationale**: Option A fixes a shipping bug (harness that
couldn't match any CoT output). Option B tests whether more
training can drive the exact `#### N` format into the adapter.

**Verdict against H1/H2/H3** (now applicable with real strict
scoring):
- H1 (≥50% in-sample): not met (19%)
- H2 (≥10% holdout): **MET** (26%)
- H3 small gap: **MET** (holdout actually > in-sample; ~0 gap
  with slight negative direction — stochastic noise consistent
  with genuine learning)

**Artifacts**:
- [`harness-tolerance-results.md`](harness-tolerance-results.md)
  — deep dive for Trial 2
- Experiments 11 + 12
- `harness_versions.v4` + `v5` (released)
- Harness patch in commit (TB-US-076 landing)

---

## 2026-10-31 → 2026-11-01 — Trial #3: adapter v4 retrain (TB-US-076 Option B)

**What we did**: Built `training_set_versions.v5` (300 rows =
200 original failures + 100 extra GSM8K train-split, seed=44,
strictly disjoint from holdout). Trained
`adapter_versions.v4` with:

- LoRA rank 32, alpha 64, dropout 0.05, lr 2e-4
- **10 epochs** (up from 5), batch 4, gradient_accum 4
- 300 training samples (up from 200)
- Target: drive `#### N` format compliance via more exposure
  and more training

Re-measured against patched harness:

- E15 (expt_id=15, in-sample): adapter v4 + harness v4, n=200
- E16 (expt_id=16, out-of-sample): adapter v4 + harness v5,
  n=200

**What we found**: Training 9 completed in 940s (~16 min) with
14 metric rows. Loss trajectory revealed classic overfitting:

| Step | train_loss | eval_loss |
|---|---|---|
| 50 | 1.26 | — |
| 100 | 0.91 | — |
| 152 (ep 8) | — | 1.38 |
| 171 (ep 9) | — | **1.57** ↑ |
| 190 (ep 10) | — | **1.68** ↑ |

Train loss kept dropping while eval loss **rose** in the last
2 epochs → adapter was memorizing training set at the cost of
generalization.

Measurement:
- E15 strict: **12 / 200 (6%)**
- E16 strict: **15 / 200 (7.5%)**
- **Adapter v4 UNDER-performed adapter v3 by ~15-20 pt
  on both measures**

**What we decided**:
- Adapter v4 is a **cautionary data point**, not a win
- Adapter v3 stands as the demo artifact; v4 is retained in the
  DB (not deprecated) for traceability
- TB-US-076 closes with Option A as the real win

**Rationale**: More epochs on a small dataset overfit. The
pre-registered methodology (eval_loss tracked at epoch
boundaries) GAVE US THE WARNING SIGN — eval_loss rose at step
152 and we had the signal that 10 epochs was too many. Lesson
captured for future trials.

**Verdict against H1/H2/H3 for adapter v4**:
- H1 (≥50%): not met (6%)
- H2 (≥10%): **NOT met** (7.5%)
- H3 small gap: trivially small (1.5 pt), but both at low floor

**Operational finding**: Running training immediately after
back-to-back inference experiments OOMs the GPU — the TB
server's allocator cache ~15 GB blocks subprocess spawn (CUDA
needs ~13 GB cold load). **Service restart between back-to-back
training-and-measurement cycles is now a documented required
step** (added to the daemon in the Phase B rerun).

**Open questions raised by this trial**:
- Would 5-7 epochs on the 300-row v5 training set land in the
  sweet spot? (More data, fewer epochs; same budget)
- Would an early-stopping callback that watches eval_loss have
  caught the overfitting at step 150?
- Would format-only drill rows (short Q→`#### N` pairs, no CoT)
  be more efficient per step than full CoT examples?

**Artifacts**:
- [`format-retrain-results.md`](format-retrain-results.md) —
  deep dive for Trial 3
- Experiments 15 + 16
- Training run 9 in `runs_tracker.db`
- `adapter_versions.v4` in-tree at `adapters/math-example/v4/`
- `training_set_versions.v5` (300 rows, released + promoted)
- `scripts/prep_math_v5_format_emphasis.py` — reproducer

---

## 2026-11-02 — Trial #4: Instruct variant + 500 random + early stopping (TB-US-077)

**What we did**: swapped the base to Llama 3.1 8B **Instruct**
(previously `-8B` base variant). Trained `adapter_versions.v5`
on `training_set_versions.v6` (500 random GSM8K train-split
problems, seed=45, disjoint from holdout). Hyperparameters:
LoRA rank 32, alpha 64, dropout 0.05, lr 2e-4, 5 epochs, batch 4,
grad_accum 4. **New infrastructure**: added `EarlyStoppingCallback(patience=2)`
+ `load_best_model_at_end=True` + `metric_for_best_model="eval_loss"`
to `training/math/train.py`. Measured in-sample (E17 against
harness v4) and holdout (E18 against harness v5). After seeing
unexpectedly low numbers, added a bare-Instruct control (E19,
no adapter, same prompt + harness).

**What we found**: training 11 completed in 797s (~13 min).
Loss trajectory showed early-stopping-worthy behavior: eval_loss
dropped 0.918 → 0.780 by epoch 3, then rose 0.780 → 0.874 by
epoch 5. `load_best_model_at_end` correctly saved the step-96
(epoch 3) checkpoint — H4d verified.

Measurement with adapter v5 on top of Instruct:
- E17 (in-sample): 38/200 (19.0%)
- E18 (holdout):   46/200 (23.0%)

**Headline from the control** (added as a diagnostic, not in the
original Trial #4 plan):
- **E19 (bare Instruct, no adapter): 86/200 (43.0%)**

| Setup | Score |
|---|---|
| Instruct + our adapter v5 | 23% holdout |
| **Instruct alone, no adapter** | **43% holdout** |

**Our 20-min training REGRESSED Instruct by 20 points.** Loading
adapter v5 on top of a strong instruction-tuned base cost 40
correct answers on the same 200 holdout questions.

Per-sample inspection confirms the cause (F13 "answer-first"
pattern): both bare Instruct and adapter v5 produce `#### N` at
the TOP of the output. But bare Instruct **also writes a second
`#### N` at the end** inside a "The final answer is: #### N"
sentence that corrects its initial guess. Our harness regex picks
the last `####` → gets the correct final answer. Adapter v5 learned
to produce ONE `####` early (matching our GSM8K training-answer
format) + drops the end-of-reasoning summary → the regex catches
the wrong initial guess.

**Pre-registered hypotheses outcome**:

| H | Threshold | Result | Verdict |
|---|---|---|---|
| H4a | in-sample ≥60% | 19% | not met |
| H4b | holdout ≥55% (credibility) | 23% | **NOT MET** |
| H4c | gap ≤5pt | 4pt | met |
| H4d | early stop triggers | yes (step 96 checkpoint saved) | met |

**But the real finding supersedes H1-H4**: training on top of a
strong instruct-tuned base with our current approach **actively
regresses performance**. The methodology correctly surfaced this
by requiring the bare-Instruct control.

**What we decided**:
- Trial #4 is a **failed-hypothesis** result — but a **valuable
  methodological finding**. "LoRA on Instruct with GSM8K-formatted
  training data at 5 epochs regressed accuracy from 43% to 23%."
- The current best math-example demo is **bare Instruct (43%)**
  with zero TB-specific training.
- Public Pages site now ships the 43% number as the credible demo
  headline instead of adapter v3's 26%.
- Followup drafted (TB-US-078) for investigating what training
  approach would HELP Instruct — chat-template-formatted data,
  smaller LoRA rank, larger training set, different task framing.

**Rationale**: Instruct is already instruction-tuned by Meta via
expensive SFT + RLHF. A 500-sample × 5-epoch QLoRA on top of
that is a small perturbation that disrupts the sophisticated
"guess + reason + confirm" response structure. The LoRA doesn't
train hard enough to replace the native pattern with something
equally sophisticated — it just damages what was working.

**Open questions**:
- Would training on **chat-template-formatted** data (`<|system|>`,
  `<|user|>`, `<|assistant|>` turns) rather than raw CoT help
  preserve Instruct's native response structure?
- Would a **lower LoRA rank** (8 or 16 vs. our 32) create less
  perturbation and leave Instruct's natural reasoning intact?
- Is there a **minimum training-set size** below which LoRA on
  Instruct is net-negative? (Our 500 samples wasn't enough.)
- Would **task-prompting changes** (e.g., ask the model to think
  before answering, use the proper Instruct chat template)
  recover the lost accuracy?

**Operational findings**:
- First training attempt (run 10) failed in 7s with
  `ValueError: --load_best_model_at_end requires the save and eval
  strategy to match`. HF Trainer requires `save_strategy="epoch"`
  when `eval_strategy="epoch"` + `load_best_model_at_end=True`.
  Fixed by adding `save_strategy=eval_strategy if eval_strategy
  != "no" else "steps"` to TrainingArguments. Lesson: when adding
  `load_best_model_at_end`, also pin save strategy to match.
- `EarlyStoppingCallback` is additive — no regression on
  TB-US-065's existing launch flow.

**Artifacts**:
- [`instruct-scale-up-results.md`](instruct-scale-up-results.md) —
  Trial 4 deep dive
- Training run 11 in `runs_tracker.db`
- Experiments 17 + 18 + 19 in `backend/db/trainingbench.db`
- `adapter_versions.v5` on agent 3 (released + promoted;
  **retained but not current demo** — bare Instruct wins)
- `training_set_versions.v6` on agent 3 (released + promoted)
- `scripts/prep_math_v6_random_scale.py` — reproducer
- `train.py` patch: `EarlyStoppingCallback` + `load_best_model_at_end` +
  `save_strategy` fix

---

## Summary table (as of 2026-11-02)

| Trial | Base | Adapter | Epochs × Samples | Strict in-sample | Strict holdout | Verdict |
|---|---|---|---|---|---|---|
| 1 | 8B base | v3 (shipped harness pre-patch) | 5 × 200 | 0 / 200 | 0 / 200 | Hidden by harness bug |
| 2 | 8B base | v3 (patched harness) | — | **38 / 200 (19%)** | **52 / 200 (26%)** | Real signal; previous demo result |
| 3 | 8B base | v4 (10 epochs) | 10 × 300 | 12 / 200 (6%) | 15 / 200 (7.5%) | Overfit; cautionary |
| 4 | 8B Instruct | v5 (early stop, 5 ep × 500) | 5 × 500 | 38 / 200 (19%) | 46 / 200 (23%) | Adapter REGRESSED Instruct |
| 4-control | **8B Instruct** | **none (bare)** | — | — | **86 / 200 (43%)** | **New demo result — strongest** |

**Current demo configuration**: **bare Llama 3.1 8B Instruct, no
adapter**. 43% on 200 holdout GSM8K problems with zero TB-specific
training. Pages site reflects this as of 2026-11-02.

**Key method lesson from Trial #4**: training on top of a strong
instruction-tuned base with our current approach (CoT-formatted
GSM8K + LoRA rank 32 + 500 samples × 5 epochs) **actively
regresses accuracy**. The methodology surfaced this by requiring
the bare-Instruct control (E19) — without it, adapter v5's 23%
would have looked like "weak improvement from zero" instead of
"regression from 43%".

**Open next-trial candidates** (not yet drafted; TB-US-078 captures
the Instruct-training-approach investigation):

1. **TB-US-078** (drafted): investigate what training approach
   would HELP Instruct — chat-template-formatted data, smaller
   LoRA rank (8 or 16), larger training set (2000-5000 samples),
   different task framing
2. Retrain adapter v3-shape (base + 5 ep × 200 failures) with
   early stopping — see if the Trial #2 result holds up with
   current infrastructure
3. Format-only short-drill training set (would require a new
   training-set version with Q→`#### N` short pairs)
4. RAG hypothesis test (TB-US-075 Phase 8, deferred) — likely
   null result given math problems don't need retrieval

Operator picks what to fire next (if anything).

---

## How to append to this log

New entry template:

```
## YYYY-MM-DD — Trial #N (or Decision #N): short label

**What we did**: ...

**What we found**: ... (concrete numbers; link to deep dive)

**What we decided**: ...

**Rationale**: ...

**Open questions**: ... (optional)

**Artifacts**:
- [`deep-dive.md`](deep-dive.md)
- Experiment IDs, training run IDs, commit hashes
```

Keep entries tight (< 1 screen each). Deep dives go in separate
files. Numbers go in the summary table at the bottom.
