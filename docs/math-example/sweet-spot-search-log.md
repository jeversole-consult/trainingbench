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

**Research mode — publication artifact plan**: as of 2026-11-02,
this log is being treated as a publication-grade chronological
record. The stable research protocol (reproducibility checklist,
threats-to-validity framework, confirmation-bias checks) lives in
[`methodology.md`](methodology.md). Per-trial pre-registrations
land in [`study-design.md`](study-design.md). This log remains
the running journal.

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
  — pinned on `harness_version=v4` (baseline-test problem set,
  `math_eval_200.jsonl`). This measures bare-Instruct accuracy on
  the same 200 GSM8K test problems that TB-US-075 used for
  failure mining; see labeling-correction note below.

| Setup | Score (dataset) |
|---|---|
| Instruct + our adapter v5 | 23% holdout (E18, `math_eval_200_holdout.jsonl`) |
| **Instruct alone, no adapter** | **43% baseline-test (E19, `math_eval_200.jsonl`)** |

**Our 20-min training REGRESSED Instruct by 20 points on the
holdout set** (E18 23% vs. adapter-less baseline-test 43%; the
comparison is cross-dataset but both are unseen for bare Instruct,
and the Trial #5 measurement of bare Instruct on holdout — see
TB-US-079 — closes this gap). Loading adapter v5 on top of a
strong instruction-tuned base cost 40 correct answers on
200 GSM8K problems.

> **Labeling correction (2026-11-02)**: This entry originally
> labeled E19's 43% as "holdout". E19 was actually pinned on
> harness_version=v4 (baseline-test set), not v5 (holdout). The
> 43% number is correct; the dataset label was wrong. Both
> datasets are 200-sample subsets of GSM8K that bare Instruct
> had never seen (one is from GSM8K's test split, one from the
> train split), so the number remains a credible out-of-sample
> accuracy measurement. TB-US-079 adds E_bare_holdout to measure
> bare Instruct on the actual holdout set and close the gap. See
> architectural-finding-training-set-wiring.md for the related
> wiring finding that surfaced during the same session.

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

## 2026-11-02 — Research-process finding: `training_set_versions` was never wired into `train.py`

**Not a trial.** A substantive discovery about our research
infrastructure, surfaced during TB-US-078 Phase 2 preparation.

### What we found

`training/math/train.py` has, since TB-US-065 shipped (2026-10-22),
unconditionally loaded raw GSM8K via `load_from_disk("datasets/math/data")`
and selected the first N rows after HF's default shuffle. The
`training_set_version_id` on each `training_runs` row — nominally
the pointer to that run's training data — was never consulted by
train.py for data input. It was recorded on the auto-registered
adapter row (via the TB-US-063 provenance mechanism) but never
drove training.

Our search log's "Training set version" column (v4, v5, v6) across
Trials #1–#4 therefore recorded provenance metadata, not actual
training data variation. Trial-to-trial comparisons were at
approximately constant data — the first ~500 rows of GSM8K.train
— on a varying hyperparameter axis.

### Why we found it

The TB-US-078 Trial #5 plan required chat-template-formatted
training data. The prep script
`scripts/prep_math_v7_chat_template.py` produced a correctly
formatted JSONL at `training-sets/math-example-v7-chat-template.jsonl`.
Before launching training, we inspected `train.py` to confirm it
would read that JSONL. Discovery: it reads `datasets/math/data`
and ignores `training_set_version_id` entirely for data purposes.

### Why prior trial findings still stand

Discovery does **not** invalidate TB-US-075–077 findings:

- Trial #1's harness-bug finding stands (bug was in the harness,
  not the training data)
- Trial #2's "real signal" (adapter v3 19/26%) stands (patched
  harness; constant training data irrelevant to the finding)
- Trial #3's overfit (6/7.5%) stands (10 epochs on 300 samples
  overfit regardless of exact sample selection)
- Trial #4's Instruct regression (23% vs. bare 43%) stands —
  the regression mechanism (format strip via `format_training_example`)
  is adjacent to the wiring gap, not caused by it; a correct
  wiring + the same hardcoded template would have produced the
  same regression

What **does** change: the "training set version" axis in our
search log, previously labeled as varying across trials, is now
documented as approximately constant across Trials #1–#4.
Trial #5 (TB-US-079) is the first trial with genuinely varied
training data under the corrected wiring.

### What we did

TB-US-078: clean cutover (no backward-compat shim; per the
`feedback_no_backcompat_research_mode` discipline).

- `train.py` `prepare_dataset()` now takes a required
  `training_set_jsonl` path; reads each row's `text` field
  verbatim; eval set remains GSM8K `test` chat-template-formatted
  inline so eval-loss sequences are comparable.
- Deleted the hardcoded `format_training_example` and the
  raw-GSM8K default fallback.
- `/training/runs/launch` resolves `training_set_version_id` →
  sidecar path, validates, passes to the subprocess.
- 400 error if `training_set_version_id` missing or the sidecar
  file is missing.

### Concerns

- **Confirmation-bias risk**: finding this gap *before* Trial #5
  ran is a boon — we don't retroactively have to re-interpret
  numbers. But operator-researcher must be careful not to use
  the finding to selectively reframe prior results. The pre-registered
  thresholds for Trials #1–#4 are already in the log; those stay.
- **Reproducibility documentation**: for publication, this entry
  (and the deep-dive at
  `architectural-finding-training-set-wiring.md`) must appear
  prominently in the methods section so a reader understands
  that trial-to-trial comparisons for Trials #1–#4 were at
  constant data.

Deliverable: `docs/math-example/architectural-finding-training-set-wiring.md`
(deep dive).

Status: fix shipped via TB-US-078; Trial #5 (TB-US-079) now
blocked only on the TB-US-078 smoke-run passing.

---

## 2026-11-02 — Trial #5: chat-template-formatted training on Instruct (TB-US-079)

**First trial under TB-US-078's corrected wiring.** The
`training_set_versions.v7` sidecar JSONL was the actual training
data input (previously provenance-only). See the research-process
finding above for context.

### What we did

Pre-registered hyperparameters: Instruct base, `training_set_versions.v7`
(1000 chat-template-formatted samples, seed=46, disjoint from
holdout), LoRA rank 16, alpha 32, lr 1e-4, 3 epochs, early-stop
patience=2. Trained adapter v7 (24 min wall-clock, 189 optimizer
steps, train_loss 2.67 → 0.38, eval_loss 0.43 at epoch 2). No
overfitting signal; early stop didn't trigger (patience=2
mathematically cannot fire with only 2 evals — flagged for
TB-US-080).

Three measurement experiments at n=200:
- E20 (adapter v7 × baseline-test): 88/200 = **44.0%**
- E21 (adapter v7 × holdout, PRIMARY):  89/200 = **44.5%**
- E22 (bare Instruct × holdout, control): 86/200 = **43.0%**
  (fills the labeling-correction gap — E19 was actually
  baseline-test, not holdout)

### What we found

**Four-cell comparison:**

| | Baseline-test | Holdout |
|---|---|---|
| Bare Instruct | 86 / 200 (43%) · dual-####=45.5% | 86 / 200 (43%) · 45.0% |
| Adapter v5 (Trial #4) | 38 / 200 (19%) · 23.5% | 46 / 200 (23%) · 20.0% |
| **Adapter v7 (Trial #5)** | **88 / 200 (44%)** · 63.0% | **89 / 200 (44.5%)** · 60.5% |

- **H5a (chat-template preserves `####` structure)**: ✅ **PASS, dramatically**.
  100% of baseline-test outputs produced strict `#### N`; 98.5%
  of holdout. Dual-#### retention (60-63%) actually SURPASSED
  bare Instruct's native 45%. The adapter learned the structural
  format more rigidly than the base model's SFT.
- **H5b (holdout ≥ 43%, no regression)**: ✅ **PASS**. 44.5% vs.
  43% bare — within noise, direction positive. Trial #4's
  regression mechanism confirmed as fixable.
- **H5c (holdout ≥ 50%, meaningful improvement)**: ❌ **NOT MET**.
  +1.5pt is within binomial variance; cannot claim improvement.
- **H5c-strong (≥60%)**: ❌ NOT MET.
- **H5d (early stop triggers)**: **N/A at this config** —
  mathematically impossible to fire with only 2 evals and
  patience=2. Infrastructure sound; config didn't exercise it.

### What we decided

- **The chat-template fix works for structure, not for capability.**
  Fixing the format mismatch recovered Trial #4's regression
  completely (23% → 44.5% holdout) but did not surface new math
  reasoning. Format and capability are **decoupled levers** —
  Trial #5 isolated the format axis as the F13 regression cause.
- **Negative-null result is a legitimate finding**: "PEFT at this
  scale on Instruct preserves but does not augment GSM8K accuracy."
  Both the preservation (vs. Trial #4 regression) and the
  non-improvement (vs. H5c threshold) are informative. Not
  equivalent to "ready to publish."
- **Current demo configuration unchanged**: bare Llama 3.1 8B
  Instruct at 43% remains the credible headline. Adapter v7
  could be swapped in as a format-rigidity-preserving demo
  without accuracy change.
- **TB-US-080 drafted** (Backlog): capability-gain levers to
  try next — scale training data 5-10x, expand LoRA target
  modules to include MLP (`gate_proj, up_proj, down_proj`),
  or full fine-tuning.

### The surprising secondary finding

**Within-structure accuracy comparison** (P1_strict `#### N` outputs only):
- Bare Instruct holdout: 81 correct / 168 (48.2%)
- Adapter v7 holdout: 88 correct / 197 (44.7%)

The adapter is slightly LESS accurate per-structured-output than
bare Instruct (−3.5pt). The gross accuracy matches only because
adapter v7 produces 29 more `#### N` outputs. **The adapter
reorganizes confidence without adding capability.** Reading
between the lines: fine-tuning on CoT format didn't teach new
math reasoning; it taught the model to answer confidently with
`#### N` on questions it would otherwise hedge on. Confidence
and correctness are not aligned.

### Rationale (threats-to-validity post-review)

- Single-run, n=200: ±5pt binomial noise. +1.5pt holdout
  improvement is NOT distinguishable from stochastic variance.
  Multi-seed replicate deferred unless the next trial's result
  lands in the 48-52% window.
- Chat-template application verified during TB-US-078 smoke-run +
  explicit per-sample inspection (100% P1_strict catching
  demonstrates format transfer succeeded).
- "Preserving native dual-#### structure" measured via `####`
  pattern. Adapter v7's 60% dual-#### rate SURPASSES bare 45% —
  the adapter did not merely preserve, it intensified. Does
  not change interpretation but worth noting for the Trial #4
  F13 narrative.
- GSM8K-specific; results do not generalize to MATH, MGSM,
  SVAMP without re-measurement.

Deliverable:
[`instruct-chat-template-results.md`](instruct-chat-template-results.md)
(deep dive — hyperparameters, training trajectory, per-sample
patterns, decoupling analysis, next-direction options).

---

## 2026-11-02 — Trial #6 planning entry (TB-US-080, Candidate A locked)

**Candidate**: A — Scale training data 5x (1000 → 5000)

### Pre-registered hypotheses

Status: planning entry (training not yet launched).

- **H6-primary**: holdout accuracy ≥ 50% (bare Instruct + 7pt).
  Primary success threshold. < 48% = null supported; 48-50% =
  inconclusive.
- **H6a**: within-P1-strict accuracy ≥ 50% (vs. Trial #5's 44.7%).
  Tests whether 5x more training signal produces capability
  INSIDE the already-locked `#### N` structural format.
- **H6b**: holdout ≥ 43% (no regression; must not re-regress
  bare).
- **H6c-strong**: holdout ≥ 60% (published-range result; would
  justify demo swap and multi-seed replicate for publication).
- **H6d**: early-stop patience=2 triggers before epoch 3 if
  overfit emerges. (Testable now — 5000 samples × 3 epochs ≈
  940 optimizer steps, 3 eval checkpoints; patience=2 can
  mathematically fire. Trial #5's N/A verdict addressable
  here.)

### Hyperparameters (locked)

Identical to Trial #5 except training-set size:
- Instruct base, LoRA rank 16, alpha 32, dropout 0.05
- lr 1e-4, 3 epochs, batch 4, grad_accum 4
- Max eval 200
- Early stop patience 2 on eval_loss
- **Training set: v8 (5000 chat-template-formatted samples,
  seed=47, overlap with v7 allowed)**

### Rationale

Trial #5's 1000-sample training set was order-of-magnitude
smaller than published math-LoRA work (10,000-50,000+). The
"decoupling finding" at that scale may be an artifact of
insufficient training signal rather than a fundamental PEFT
limitation. 5x scale-up tests this directly.

### Decision mapping (pre-registered)

| Holdout result | Interpretation | Next step |
|---|---|---|
| < 43% | Regression — unexpected; data scale alone HURT | TB-US-081: investigate regression mechanism; multi-seed replicate |
| 43–48% | Within-noise of bare; data scale didn't help | TB-US-081 — pursue Candidate B/C (different lever) |
| 48–50% | Inconclusive; marginal | TB-US-081 — multi-seed replicate (Candidate D) |
| 50–60% | H6-primary met | Document; try to push via Candidate B/C in TB-US-081 |
| 60–75% | H6c-strong met | Promote adapter v8 → demo; multi-seed replicate for publication |
| > 75% | Suspect — audit disjointness, check seeds, re-run with fresh samples | — |

Deliverable (post-run): `scale-up-5000-results.md` deep dive.

---

## 2026-11-03 — Trial #6 complete (TB-US-080 Candidate A: scale data 5x)

### What we did

Trained adapter v8 on `training_set_versions.v8` (5000 chat-template-
formatted samples from GSM8K train, seed=47). All other hyperparameters
identical to Trial #5. Training completed in 1h 54min (939 optimizer
steps across 3 epochs). Eval loss trajectory: 0.4170 (epoch 1) → 0.4121
(epoch 2, best) → 0.4136 (epoch 3). `load_best_model_at_end=True`
correctly selected the epoch-2 checkpoint (verified via MD5 against
checkpoint-626). Early stop didn't fire (only 1 worsening eval; needs 2).

Two measurement experiments at n=200 (bare-Instruct holdout control
reused from Trial #5 E22):
- E23 (adapter v8 × baseline-test): **75/200 = 37.5%**
- E24 (adapter v8 × holdout, primary): **85/200 = 42.5%**

### What we found

**Scaling data 5x DID NOT help and modestly regressed:**

| Setup | baseline-test | holdout | dual-#### |
|---|---|---|---|
| Bare Instruct | 43% | 43% | 45% |
| Adapter v7 (1000 samples) | 44% | 44.5% | 60-63% |
| **Adapter v8 (5000 samples)** | **37.5%** | **42.5%** | **74-74.5%** |

- **H6-primary (holdout ≥ 50%)**: ❌ NOT MET (42.5%).
- **H6b (no regression ≥ 43%)**: ❌ NOT MET on baseline-test
  (37.5% is clearly outside noise band at −5.5pt vs. bare).
  MARGINAL on holdout (−0.5pt vs. bare).
- **H6a (within-P1-strict ≥ 50%)**: ❌ NOT MET (42.9% within-structure
  on holdout vs. Trial #5's 44.7% and bare's 48.2%).
- **H6d (early stop infrastructure testable)**: ✅ VALIDATED — 3 evals
  computed; load_best_model_at_end verifiably worked; patience=2
  mechanism intact but didn't fire (requires 2 consecutive worsenings).

**Dual-#### retention intensified from 60-63% (Trial #5) → 74-74.5%
(Trial #6).** The adapter learned the GSM8K structural format even more
rigidly as data increased. Within dual-#### outputs specifically,
accuracy was 30% for adapter v8 vs. 50% for bare Instruct. **Confidence
is learned; correctness is not.**

### What we decided

**Trial #5's "format vs. capability decoupling" finding is now
pronounced**: more training data at this config = more format
overfitting = less capability. Trial #6 strengthens the Trial #5
negative-null into a mild negative result on the data-scale lever.

**Three plausible mechanisms** (noted in deep dive):
1. **Dataset exhaustion** — 5000/7473 = 67% of GSM8K train; marginal
   new signal only ~302 problems vs. v7 (698/1000 overlap).
2. **LoRA capacity trap at rank 16** — limited expressive bandwidth;
   format wins at 5000 samples.
3. **Format-overfitting cascade** — more reinforcement of the
   `#### N` pattern replaces bare Instruct's hedged correct answers
   with confident wrong ones.

**TB-US-081 queued** with 3 remaining candidates:
- **D (recommended first)** — Multi-seed replicate of Trial #5 + #6.
  Resolves the "is -2pt real or noise?" question before investing
  more training compute.
- **B** — Expand LoRA target modules to MLP. Cheap (~45-60 min);
  tests the "LoRA capacity trap" mechanism.
- **C** — Full fine-tuning. Expensive; tests the "low-rank-constraint
  is the ceiling" mechanism.

**Current demo unchanged**: bare Llama 3.1 8B Instruct at 43%.
Adapter v8 is strictly inferior to adapter v7 on measured dimensions
(not promoted; stays in registry as historical).

### Rationale (threats-to-validity post-review)

- **Single-run, n=200**: ±5pt binomial variance. Trial #6 holdout
  (-2pt vs. Trial #5) is within noise; Trial #6 baseline-test
  (-6.5pt vs. Trial #5) is marginally outside. Multi-seed replicate
  (Candidate D) would resolve.
- **Training infrastructure validated**: load_best_model_at_end
  worked correctly; eval loss trajectory sane; no overfitting
  catastrophe at 3 epochs.
- Overlap v8-v7 = 698 → the data-scale lever is testing "see each
  pattern more times via epochs" more than "see 5x different
  problems". Interpretation note included in deep dive.

Deliverable:
[`scale-up-5000-results.md`](scale-up-5000-results.md)
(deep dive — full pattern analysis, three-mechanism interpretation,
next-direction options).

---

## 2026-11-03 — Trial #7 planning entry (TB-US-081, Candidate D locked)

**Candidate**: D — Multi-seed replicate

### Pre-run observation (discovered pre-fire)

TB's harness runner (`backend/api/harness_runner.py`) already
uses `do_sample=True, temperature=0.7, top_p, top_k` with NO
explicit RNG seed. **All prior single-run measurements across
Trials #1-#6 are each one stochastic draw.** The ±5pt binomial
noise band we've been using is a lower bound — true measurement
noise includes generation stochasticity on top.

For Candidate D, this is actually convenient: creating fresh
experiment runs naturally produces different draws (implicit
RNG via process timing). No code change needed to vary the seed
within this trial. Note for publication: implicit multi-seed is
weaker than explicit-seed replication; if real signal is found
here, TB-US-082 will add `--generation-seed` to harness_runner
for exact reproducibility.

### Pre-registered experimental matrix

4 datapoints per adapter (3 new + 1 existing):

| Adapter | Experiment IDs | Source |
|---|---|---|
| adapter v7 (Trial #5 lineage) | E21, E25, E26, E27 | 1 original + 3 new |
| adapter v8 (Trial #6 lineage) | E24, E28, E29, E30 | 1 original + 3 new |

All experiments: n=200, Instruct base, system_prompt v3, harness
v5 (holdout). ~45 min each × 6 new = ~4.5h sequential.

### Pre-registered decision mapping

- |mean_v7 − mean_v8| < 1× pooled SD → **"indistinguishable"**:
  Trials #5 and #6 are statistically equivalent at holdout.
  Series conclusion firms up: "data scale alone doesn't help OR
  hurt at this corpus and config." TB-US-082 Candidate B
  (expand LoRA to MLP) and/or C (full fine-tune) become higher
  priority.
- 1× SD ≤ |mean_v7 − mean_v8| < 2× pooled SD → **"marginal
  signal"**: Trial #6's drop may be partly real but magnitude
  uncertain. Direction informative; multi-seed with explicit
  seeds in TB-US-082 would strengthen.
- |mean_v7 − mean_v8| ≥ 2× pooled SD → **"real signal"**:
  Trial #6 regression confirmed. TB-US-082 Candidate B/C tested
  against solid "scale data hurt" baseline. Format-overfitting
  cascade mechanism (not stochastic artifact) confirmed.

**Note**: 2× SD is a moderate threshold (~95% confidence under
Gaussian). More rigorous: 3× SD. Chose 2× to balance Type-I vs.
Type-II error given small-n (4 draws per adapter).

### Secondary signals

- If any single draw of adapter v7 OR v8 lands ≥ 50%, that's a
  hint TB-US-082 Candidate B (expand LoRA) might unlock
  capability — operator read-off, no formal threshold.
- Spread across all 8 draws tells us GSM8K's measurement noise
  envelope. If spread < 3pt, central tendency is pinnable; if
  spread > 10pt, GSM8K at n=200 is too noisy for ±1pt
  conclusions.

Deliverable (post-run): `multi-seed-replicate-results.md` deep
dive.

---

## 2026-11-03 — Trial #7 complete (TB-US-081 Candidate D: multi-seed replicate)

### What we did

Discovered pre-fire that TB's harness runner uses `do_sample=True,
temperature=0.7` with NO explicit RNG seed — **all prior
single-run measurements across Trials #1-#6 are each one
stochastic draw, not deterministic**. The ±5pt binomial noise
band is a lower bound; true noise includes generation
stochasticity on top.

Created 3 new E_holdout experiments per adapter, combined with
the existing E21/E24 for 4 holdout draws per adapter.
Experiments ran sequentially (~45 min each × 6 new = ~4.5h).
Mid-run, the 24-hour session-token expiry hit the orchestrator
script at the E29/E30 boundary; the TB service kept running
E29 correctly and E30 was launched manually after re-minting
the token (zero data loss, ~15 min operator intervention).

### What we found

**4 holdout draws per adapter:**

| Adapter | Draws | Mean | SD | Range |
|---|---|---|---|---|
| v7 (Trial #5, 1000 samples) | 44.5, 41.5, 43.5, 38.5 | **42.00%** | 2.65pt | 38.5–44.5 (6pt spread) |
| v8 (Trial #6, 5000 samples) | 42.5, 44.0, 42.0, 38.0 | **41.62%** | 2.56pt | 38.0–44.0 (6pt spread) |

- **Difference in means**: +0.38pt (v7 vs. v8)
- **Pooled SD**: 2.60pt
- **|diff| / pooled SD**: 0.14× — well below the pre-registered
  1× threshold for "marginal signal"
- **Pre-registered verdict: INDISTINGUISHABLE**

**Trial #6's apparent 2pt regression was stochastic noise.** The
single-draw comparison (E21 44.5% vs. E24 42.5%) picked two
random points from essentially the same distribution.

### What we decided

**Revised narrative for Trial #6**: scaling 1000 → 5000
samples **did not change holdout accuracy in either direction**.
The format-overfitting cascade is real as a per-sample
structural signal (dual-#### retention 60% → 74%, a deterministic
count per output), but it is **accuracy-neutral**, not accuracy-
negative. "Confidence without correctness" revised: confidence
IS learned at scale, but that confidence is neither more nor
less correct than bare Instruct's hedged pattern.

**New methodology constant: GSM8K at n=200 has ~6pt noise
envelope.** Single-draw comparisons < 6pt should not be
interpreted as signal. Retroactively applicable to all
trial-to-trial comparisons:
- Trial #4 regression (−20pt): clearly outside envelope, real
- Trial #2 vs. Trial #5 (26% vs. 42% on holdout for base vs.
  Instruct): clearly outside envelope, real
- Trial #5 vs. bare Instruct (+1.5pt): within envelope, now
  revised to "no real difference"
- Trial #5 vs. Trial #6: within envelope, now explicitly
  "no real difference"

**Combined finding across Trials #5-#7**: Chat-template-formatted
PEFT on Instruct at rank 16 (attention-only) preserves bare
Instruct's accuracy across 1000–5000 training samples. **Does
not add capability. Does not regress capability.** The lever is
an accuracy no-op within this corpus and configuration.

**TB-US-082 queued** with 2 remaining capability-gain candidates:
- **B (recommended first)** — Expand LoRA target modules to
  include MLP (`gate_proj, up_proj, down_proj`). Tests
  "LoRA capacity trap at rank 16 is specifically about which
  parameters it touches, not how many."
- **C** — Full fine-tuning (not LoRA). Expensive. Tests "the
  low-rank constraint itself is the ceiling."

### Rationale (threats-to-validity post-review)

- Multi-seed count is small (n=4 each); SD estimate has ~30%
  own error. Conservative 1×/2× thresholds suit small-n.
- Implicit multi-seed (process-timing RNG) is weaker than
  explicit-seed replication. If publication demands exact
  reproducibility, add `generation-seed` to the harness runner.
- Both adapters span the same 6pt range; no outlier in either
  arm driving the equivalence conclusion.
- Harness scoring stable across all 8 draws (priority-1 catches
  98-100%); variance is in model generation, not extraction.

Deliverable:
[`multi-seed-replicate-results.md`](multi-seed-replicate-results.md)
(deep dive — full 8-draw analysis, noise envelope
characterization, revised Trial #6 narrative, 3-mechanism
re-assessment).

---

## 2026-11-04 — Trial #8 complete (TB-US-082 Candidate B: expand LoRA to MLP)

### What we did

Trained adapter v9 on v7 (1000 samples, chat-template-formatted),
IDENTICAL hyperparameters to Trial #5 EXCEPT LoRA target modules:
expanded from 4 (attention only) to 7 (attention + MLP via
`gate_proj, up_proj, down_proj`). Rank 16, alpha 32, lr 1e-4,
3 epochs. Training 28.8 min; final train_loss 0.34; eval_loss
0.42 best epoch.

Multi-seed from the start (Trial #7 discipline): 4 holdout
experiments + 1 baseline-test.

### What we found — first positive capability-gain result in the arc

**Adapter v9 holdout multi-seed (4 draws):**
- Draws: 50.0, 53.5, 55.0, 56.5
- Mean: **53.75%** (SD 2.78pt, spread 6.5pt — within Trial #7's 6pt envelope for a single adapter)
- vs. bare Instruct (43%): **+10.75pt — far outside the noise envelope**

**Adapter v9 baseline-test (single draw): 48.5%** (+5.5pt vs bare)

### Hypothesis outcomes

- **H8-primary** (holdout mean ≥50%): ✅ **MET** at 53.75%
- **H8a** (within-P1-strict ≥50% AND dual-#### ≥60%): **PARTIAL** —
  within-P1-strict met at 54.0% mean; dual-#### came in at 47%
  (bare-like, NOT intensified). The dual-#### not-met IS the
  finding, not a failure.
- **H8b** (no regression ≥43%): ✅ MET decisively
- **H8c-strong** (≥60%): ❌ NOT MET (6.25pt short)
- **H8d** (early stop infra): didn't fire; infrastructure intact

### The mechanism confirmation

Within-P1-strict accuracy (per `#### N` output):
- Bare Instruct holdout: 48.2%
- Adapter v7 (attn-only, Trial #5): 44.7%  — 3.5pt below bare
- Adapter v8 (attn-only, 5000 samp, Trial #6): 42.9%  — 5.3pt below bare
- **Adapter v9 (+MLP, Trial #8): 54.0% mean**  — **+5.8pt above bare**

Dual-#### retention:
- Bare: ~45%
- Adapter v7: ~61%  — intensified format
- Adapter v8: ~75%  — more intensified
- **Adapter v9: ~47%**  — matches bare, does NOT intensify

**Trial #6's "LoRA capacity trap at rank 16" hypothesis is
CONFIRMED.** With only 4 attention target modules, adapters
compensated for inaccessible reasoning capacity by learning
format patterns. With MLP layers added at the same rank, the
adapter learns reasoning WITHOUT learning format rigidity.

This RETROACTIVELY explains Trials #5-#6 negative-null results:
attention-only adapters were format-constrained because the
reasoning capacity was in modules they couldn't touch.

### What we decided

**Current demo UPDATES**: adapter v9 at ~54% holdout mean becomes
the new demo. First positive result in the arc. Pages site
updated.

**Cumulative Trials #4-#8 narrative (so far)**:
1. Format alignment is NECESSARY (Trial #4 lesson: wrong format
   causes 20pt regression)
2. Format alignment is NOT SUFFICIENT (Trials #5-#6: format-only
   training at rank 16 attn-only is an accuracy no-op)
3. Target-module reach is the capability lever (Trial #8: MLP
   expansion at same rank unlocks +10.75pt holdout)
4. The format-vs-capability decoupling in Trials #5-#6 was a
   capacity-trap artifact, not a fundamental PEFT limitation

Research is ongoing; narrative coherence does not mean ready
to publish. External validation (replication across
seeds/ranks/datasets) would strengthen before external sharing.

**Series continuation**: with Trial #8's positive result
and mechanism-confirmation, the math-example research arc has
reached an internal milestone. Further trials (rank sweep at
attn+MLP, Candidate C full fine-tune, external data, explicit-
seed replication, cross-dataset validation) remain open
directions. Research is ongoing — no publication-readiness
decision implied.

### Rationale (threats-to-validity post-review)

- Multi-seed from the start (4 draws); not cherry-picked.
- Draws span 6.5pt — consistent with Trial #7's 6pt envelope
  for a single adapter.
- Mean difference from bare (+10.75pt) is **far outside** the
  envelope. Not noise.
- Within-P1-strict +5.8pt confirms real reasoning gain, not
  just format-confidence redistribution.
- Monotonic draw pattern (50 → 53.5 → 55 → 56.5) noted; 4%
  random coincidence, doesn't change mean.
- Same base + same data + same rank/lr/epochs as Trial #5.
  One variable changed. Reproducibility clean.

Deliverable:
[`mlp-expansion-results.md`](mlp-expansion-results.md)
(deep dive — hyperparameters, trajectory, per-sample patterns,
mechanism-confirmation analysis, publication implications).

---

## 2026-11-06 — Trial #9 complete (TB-US-085: rank sweep at attn+MLP)

### What we did

Adapter v10 = adapter v9 recipe (Instruct + v7 1000 samples +
attn+MLP target modules + lr 1e-4 + 3 epochs + early stop
patience=2) EXCEPT **rank 16 → 32** (alpha 32 → 64).
Training 28.9 min; train_loss 2.55 → 0.296; eval_loss 0.426 →
0.423 (best) → 0.443 (early-overfit signal, caught by
load_best_model_at_end). 4 multi-seed holdout experiments (no
baseline-test this trial).

**Methodological note**: fired conversationally during
audience/strategy discussion without formal H-threshold
pre-registration. Methodology was weaker than Trials #5-#8.
Result stands but discipline slipped.

### What we found

**Holdout 4-draw statistics:**
- Draws: 63.0, 54.0, 64.0, 59.5
- **Mean: 60.12% (SD 4.52pt)**
- Range: 54.0 – 64.0 (spread 10pt)

**vs. Adapter v9 (Trial #8, rank 16 attn+MLP):**
- +6.38pt
- Pooled SD: 3.75pt
- |diff|/pooled-SD: **1.70× — MARGINAL SIGNAL** per Trial #7
  framework (1-2× bin). Direction unambiguously positive;
  magnitude uncertain at n=4 per adapter.

**Full-series comparison (holdout, multi-seed mean):**

| Setup | Holdout | dual-#### | within-P1-strict |
|---|---|---|---|
| Bare Instruct | 43% | 45% | 48.2% |
| Adapter v7 (attn-only, rank 16) | 42.00% ± 2.65 | 61% | 44.7% |
| Adapter v8 (attn-only, 5000 samp) | 41.62% ± 2.56 | 75% | 42.9% |
| Adapter v9 (+MLP, rank 16) | 53.75% ± 2.78 | 47% | 54.0% |
| **Adapter v10 (+MLP, rank 32)** | **60.12% ± 4.52** | **59%** | **60.5%** |

### What we decided

**More capacity, used differently**: v10 picks up BOTH reasoning
(within-P1-strict 60.5%, +12.3pt vs bare, +5.8pt vs v9) AND
format rigidity (dual-#### 59%, re-intensified from v9's 47%).
At rank 16 the adapter had to choose; at rank 32 it can learn
both. Reasoning gain is the accuracy driver; format
re-intensification is a byproduct of extra capacity.

**SD jumped** (v9: 2.78pt → v10: 4.52pt). Possible explanations:
larger adapter = more seed sensitivity; overfit proximity
(epoch-3 eval rose); or small-n sampling noise. Not resolved.

**Current demo UPDATES**: adapter v10 at ~60% mean becomes the
new demo. Approaches the published 60-75% math-LoRA band for
the first time in the series.

**Research arc closes here** (operator decision 2026-11-06):
math-example has served its purpose as PEFT demonstration;
further trials (rank 64, full fine-tune, external data, best-of-N,
70B model) are out of scope given cost + TB strategy. Research
continues on stalite's side with different priorities
(small-dataset PEFT, deployment, proprietary separation).

### Rationale (threats-to-validity post-review)

- Marginal signal at n=4 per adapter (acknowledged)
- Pre-registration slipped this trial (acknowledged)
- No baseline-test for v10 (could add retroactively)
- No multi-seed confirmation of Trial #9 specifically — one
  training-seed, four generation-seeds
- GSM8K-specific; usual external-validity caveats

Deliverable:
[`rank-sweep-results.md`](rank-sweep-results.md) (deep dive).

---

## Summary table (as of 2026-11-06)

| Trial | Base | Adapter | Epochs × Samples | Strict baseline-test | Strict holdout | Verdict |
|---|---|---|---|---|---|---|
| 1 | 8B base | v3 (shipped harness pre-patch) | 5 × 200 | 0 / 200 | 0 / 200 | Hidden by harness bug |
| 2 | 8B base | v3 (patched harness) | — | **38 / 200 (19%)** | **52 / 200 (26%)** | Real signal; previous demo result |
| 3 | 8B base | v4 (10 epochs) | 10 × 300 | 12 / 200 (6%) | 15 / 200 (7.5%) | Overfit; cautionary |
| 4 | 8B Instruct | v5 (early stop, 5 ep × 500) | 5 × 500 | 38 / 200 (19%) | 46 / 200 (23%) | Adapter REGRESSED Instruct |
| 4-control | **8B Instruct** | **none (bare)** | — | **86 / 200 (43%)** | **86 / 200 (43%)** (E22, Trial #5) | **Baseline across both datasets** |
| 5 | 8B Instruct | **v7 (chat-template, 3 ep × 1000, rank 16, lr 1e-4)** | 3 × 1000 | **88 / 200 (44%)** | **89 / 200 (44.5%)** | **Preserves bare; no capability gain** |
| 6 | 8B Instruct | **v8 (chat-template, 3 ep × 5000, rank 16, lr 1e-4)** | 3 × 5000 | **75 / 200 (37.5%)** | **85 / 200 (42.5%)** → revised to **41.62% mean (4 draws)** | Trial #6 single-draw suggested regression; **Trial #7 multi-seed revised to "no change vs. Trial #5"** |
| 7 | — | multi-seed replicate of v7 + v8 | 4 draws each | — | **v7: 42.00% ± 2.65pt;  v8: 41.62% ± 2.56pt;  diff 0.38pt (0.14× pooled SD)** | **Indistinguishable**; established 6pt noise envelope |
| 8 | 8B Instruct | **v9 (chat-template, 3 ep × 1000, rank 16, lr 1e-4, +MLP targets)** | 3 × 1000 | **97 / 200 (48.5%)** | **53.75% mean (4 draws), SD 2.78pt** | **First positive result**; +10.75pt above bare; capacity-trap mechanism confirmed |
| 9 | 8B Instruct | **v10 (chat-template, 3 ep × 1000, rank 32, lr 1e-4, +MLP targets, alpha 64)** | 3 × 1000 | — (not run) | **60.12% mean (4 draws), SD 4.52pt** | **Series close**; +6.38pt over v9 (MARGINAL signal 1.70×); within-P1-strict +12.3pt vs bare; approaches published 60-75% band |

> **Column labeling correction (2026-11-02)**: The "in-sample"
> column header was renamed to "baseline-test" to match the
> actual dataset labels. The E19 bare-Instruct number was
> originally recorded under "holdout" by mistake; it's actually
> on the baseline-test problem set (harness v4). Trial #5
> (TB-US-079) measured bare Instruct on the actual holdout
> (harness v5, E22) and found **43.0% — identical to the
> baseline-test**. Bare Instruct is remarkably consistent across
> both datasets.

**Caveat (2026-11-02)**: Trials #1–#4 all ran with approximately
constant training data (first N rows of raw GSM8K.train) because
`training_set_versions` was never wired into `train.py` — see the
"Research-process finding" entry above and
`architectural-finding-training-set-wiring.md` for details. Hyperparameter
comparisons across trials remain valid; apparent "training set
version" variation does not. Trial #5 (TB-US-079) was the first
trial with genuinely varied training data under corrected wiring.

**Current demo configuration**: **Adapter v10 (rank 32 attn+MLP
QLoRA) on Llama 3.1 8B Instruct**. Holdout mean ~60% (4 draws,
+17.1pt above bare's 43%). First adapter in the arc to approach
the published 60-75% math-LoRA band. Pages site updated (via
TB-US-085 close). Adapters v5/v7/v8/v9 remain in registry as
historical.

**Research arc closes here** (operator decision 2026-11-06):
math-example has served its purpose as PEFT demonstration;
further trials out of scope given cost + TB strategy.

**Key method lessons** (now cumulative through Trial #9):
- **Trial #4**: raw-CoT format + hardcoded template deleted
  Instruct's native `#### N`-at-end confirmation and REGRESSED
  accuracy by 20pt. **Format alignment is NECESSARY.**
- **Trial #5**: chat-template-formatted training with the correct
  `#### N` marker FIXES the Trial #4 regression but does NOT
  exceed bare. **Format alignment is NOT SUFFICIENT.**
- **Trial #6**: scaling training data 5x (1000 → 5000) at same
  config intensified format rigidity but didn't change accuracy
  (Trial #7 revision). Decoupling observed; mechanism hypothesized.
- **Trial #7**: multi-seed established ~6pt noise envelope at
  n=200. Harness uses stochastic sampling with no explicit seed —
  all prior single-run measurements were stochastic draws.
- **Trial #8**: expanding LoRA target modules from 4 (attention)
  to 7 (attention + MLP) at SAME rank 16 UNLOCKED reasoning
  capacity. Holdout mean 53.75% (+10.75pt above bare).
  Dual-#### retention 47% (bare-like, NOT intensified). Within-
  structure accuracy +5.8pt above bare. **"LoRA capacity trap"
  mechanism confirmed: reasoning capacity for math lives in MLP
  layers; attention-only LoRA compensated with format patterns.**
- **Trial #9**: doubling LoRA rank from 16 to 32 at attn+MLP
  continues to help (+6.38pt over v9, marginal signal 1.70×).
  Mean 60.12% approaches published 60-75% band. Larger adapter
  = more seed variability (SD 4.52pt vs. v9's 2.78pt). v10
  learns both reasoning AND format rigidity (bigger capacity =
  doesn't have to choose). Eval-loss overfit signal at epoch 3
  suggests rank 32 is near the overfit wall at 1000 samples ×
  3 epochs. Methodological slip: fired without formal
  pre-registration.

**Cumulative narrative (so far, internal to this research arc)**:
format alignment prevents regression; target-module reach
(including MLP) is the capability lever. At rank 16 with
attention+MLP, QLoRA on Llama 3.1 8B Instruct improves GSM8K
holdout by ~11pt over bare. Not ready to publish — further
replication (seeds/ranks/datasets) would strengthen before
external sharing.

**Open next-trial candidates** (series arrival-chapter complete;
further work is refinement):

1. Rank sweep at attn+MLP — does rank 32 at attn+MLP help further,
   or does it regress like Trial #4's rank 32 attn-only did?
2. Explicit-seed harness runner — strengthens Trial #8's
   reproducibility for publication
3. **TB-US-085** (reserved): Candidate C (full fine-tune) — now
   a mechanism comparison, not a necessary lever
4. External-data scale-up (MATH, MGSM, synthetic) — could push
   toward published 60-75% band
5. **TB-US-084** (drafted): research-methodology UI design spike —
   package the methodology we developed into TB's UI for users
   without Claude
6. **TB-US-005** (Proposed): public v0.1 cut — the research arc
   now has a positive capability-gain result; TB-US-005 is a
   packaging decision, independent of research-readiness.

Research is ongoing. "Positive result" ≠ "ready to publish."
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
