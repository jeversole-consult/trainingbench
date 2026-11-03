# Trial #7 — Multi-Seed Replicate (TB-US-081 Candidate D)

**Status**: Complete 2026-11-03
**Related story**: [TB-US-081](../user-stories/tb-us-081.md)
**Preceded by**: [Trial #5](instruct-chat-template-results.md) (chat-template
format, positive-null) and [Trial #6](scale-up-5000-results.md)
(scale data 5x, apparent negative — now revised to null).

## tl;dr

Multi-seed replicate of adapter v7 (Trial #5, 1000 samples) and
adapter v8 (Trial #6, 5000 samples) produced **4 holdout draws
per adapter**. Means: **42.00% (v7)** and **41.62% (v8)**.
Difference 0.38pt; pooled SD 2.60pt; |diff|/pooled-SD = **0.14×**
— **INDISTINGUISHABLE** per the pre-registered 1× SD threshold.
**Trial #6's apparent 2pt regression was stochastic noise, not
real signal.** Revised narrative: scaling 1000 → 5000 samples
intensified format rigidity (dual-#### retention 60% → 74% — real
per-sample measurement) but **did NOT change accuracy** in either
direction. GSM8K at n=200 has a ~6pt noise envelope; single-run
differences below that threshold should not be interpreted as
signal. Trial #4's regression (−20pt) remains real; Trials
#5-#7 all equivalent at ~42% holdout, within noise of bare
Instruct (43%).

## Research question

Was Trial #6's apparent −2pt drop (adapter v8 at 42.5% vs.
adapter v7 at 44.5% on holdout) a real regression of the data-scale
lever, or was it stochastic noise from TB's `do_sample=True,
temperature=0.7` inference?

## Pre-fire discovery (methodological)

While pre-registering Candidate D, discovered that TB's harness
runner (`backend/api/harness_runner.py:157-166`) uses
`pipeline(..., do_sample=True, temperature=LLM_TEMPERATURE=0.7,
top_p, top_k)` with **no explicit RNG seed**. Every experiment
run is thus one stochastic draw from a generation distribution,
not a deterministic measurement. **All prior single-run
measurements across Trials #1-#6 are single draws.** The ±5pt
binomial noise band we had been using is a lower bound — true
measurement noise includes generation stochasticity on top.

This discovery is itself a methodology finding and is documented
at `methodology.md` under "Known research-process limitations
discovered during execution."

## Experimental design

4 holdout draws per adapter (1 existing + 3 new):

| Adapter | Experiments | Source |
|---|---|---|
| adapter v7 (Trial #5) | E21, E25, E26, E27, E29 | 1 existing + 3 new (E25, E27, E29) |
| adapter v8 (Trial #6) | E24, E26, E28, E30 | 1 existing + 3 new (E26, E28, E30) |

(Note: E26 is v8, not v7 — the experiment labels in the DB are
authoritative.)

Each experiment: n=200, Instruct base, system_prompt v3, harness
v5 (holdout dataset `math_eval_200_holdout.jsonl`). Fresh
experiment runs each get a new implicit RNG state via process
timing; no explicit seed variation.

**Caveat for publication**: implicit multi-seed via process
timing is weaker than explicit-seed replication. If future
trials require exact reproducibility, add a `generation-seed`
param to the harness runner (potential follow-up story).

## Pre-registered decision thresholds (locked before results seen)

| |mean_v7 − mean_v8| vs. pooled SD | Verdict | Series implication |
|---|---|---|
| < 1× pooled SD | **Indistinguishable** | Trials #5 & #6 statistically equivalent; data scale alone didn't help or hurt |
| 1× ≤ diff < 2× SD | **Marginal signal** | Direction informative, magnitude uncertain |
| ≥ 2× SD | **Real signal** | Trial #6 regression confirmed |

## Results — 8 draws

| Experiment | Adapter | Score | Accuracy |
|---|---|---|---|
| E21 | v7 | 89 / 200 | 44.5% |
| E25 | v7 | 83 / 200 | 41.5% |
| E27 | v7 | 87 / 200 | 43.5% |
| E29 | v7 | 77 / 200 | **38.5%** ← new low |
| E24 | v8 | 85 / 200 | 42.5% |
| E26 | v8 | 88 / 200 | 44.0% |
| E28 | v8 | 84 / 200 | 42.0% |
| E30 | v8 | 76 / 200 | **38.0%** ← new low |

### Summary statistics

**Adapter v7 (Trial #5, 1000 samples):**
- Draws: 44.5, 41.5, 43.5, 38.5
- Mean: **42.00%**
- SD (sample, n−1): 2.65pt
- Range: 38.5% – 44.5% (spread 6pt)

**Adapter v8 (Trial #6, 5000 samples):**
- Draws: 42.5, 44.0, 42.0, 38.0
- Mean: **41.62%**
- SD (sample, n−1): 2.56pt
- Range: 38.0% – 44.0% (spread 6pt)

**Difference in means**: +0.38pt (v7 − v8)
**Pooled SD**: ((2.65² + 2.56²) / 2)^½ = **2.60pt**
**|diff| / pooled SD**: 0.14×

## Pre-registered decision outcome

**Verdict: INDISTINGUISHABLE.** 0.14× pooled SD is well below
the 1× threshold for "marginal signal." Trials #5 and #6 are
statistically equivalent at holdout under this measurement
discipline.

## Interpretation

### Trial #6's apparent regression was noise

The single-draw comparison that drove Trial #6's "regression"
narrative — E21 (v7, 44.5%) vs. E24 (v8, 42.5%) — picked two
random points from essentially the same distribution. With 4
draws each, the means are 42.00% and 41.62%, within 0.4pt. The
2pt "drop" was an artifact of looking at 2 points instead of 8.

**Revised Trial #6 narrative**: scaling training data from 1000
→ 5000 samples at this configuration **did not change holdout
accuracy in either direction**. It did intensify format
rigidity (dual-#### retention 60% → 74%, a real per-sample
measurement independent of generation noise). Format and
accuracy continued to be decoupled — the finding from Trial #5
— but this time the decoupling had no net effect on gross
accuracy, not a negative effect.

### The format-overfitting cascade is real, but doesn't translate

Trial #6's deep dive identified three plausible mechanisms for
the apparent regression: dataset exhaustion, LoRA capacity trap,
format-overfitting cascade. The multi-seed data invalidates the
cascade's accuracy consequence but not its structural signature:

- **Structural signature of cascade**: 74% dual-#### outputs
  (confirmed real, not a noise artifact — dual-#### count per
  output is deterministic given the output).
- **Accuracy consequence**: 42.5% single-draw vs. 44.5% for v7
  (NOT confirmed — within noise envelope).

Interpretation: more training reinforces the output format MORE
but this does NOT translate to either more OR fewer correct
answers. The adapter learns format intensity in a way that is
neutral to accuracy. "Confidence without correctness" from
Trial #6 is incorrect — the adapter emits `#### N` more
confidently at scale, but it's neither more nor less right.

### GSM8K at n=200 has ~6pt noise envelope

**Observation**: both adapters had 6pt spread across 4 draws.
That's the practical measurement noise for our configuration
(Instruct + LoRA + do_sample T=0.7 + harness v5). **Any
single-run measurement is ±3pt relative to the central tendency,
which means ±5-6pt comparisons to a different single-run
measurement should not be interpreted as signal.**

This retroactively applies to:
- Trial #4 (−20pt): clearly outside the noise envelope, remains
  a real finding
- Trial #2 (26% holdout on base): sitting below the envelope
  of adapter v7/v8/bare at ~42%, so real signal (adapter v3 on
  Base is indeed much worse than any Instruct variant)
- Trial #3 (7.5% holdout): well outside envelope, overfit
  cautionary remains real
- **Trial #6 vs. Trial #5**: within envelope — now revised to
  "no real difference"
- **Trial #5 vs. bare Instruct (+1.5pt holdout)**: within
  envelope — revised to "no real difference" (consistent with
  Trial #5's own hedge: "within noise, direction positive")
- **Adapter v7 vs. adapter v8**: within envelope (this trial's
  finding)

### Both adapters are indistinguishable from bare Instruct

Multi-seed grand mean across all 8 adapter draws (v7 and v8
combined): **41.8%** (N=8). Bare Instruct single-draw E22: 43.0%.
Delta: −1.2pt, well inside the noise envelope.

**Combined finding across Trials #5-#7**: Chat-template-formatted
PEFT on Instruct at rank 16 preserves bare Instruct's accuracy
across 1000–5000 training samples. **Does not add capability.
Does not regress capability.** The lever is a no-op on gross
accuracy within this corpus and configuration.

## Threats to validity (post-run review)

- **Measurement noise characterized** — this trial's chief
  contribution. ~6pt spread observed per adapter at n=4; pooled
  SD ≈ 2.6pt.
- **Implicit multi-seed**: fresh process RNG; weaker than
  explicit-seed replication. If published, should either (a) add
  explicit-seed support to harness_runner, or (b) increase n to
  8+ draws per adapter for tighter CIs, or (c) switch to a
  larger eval set (n=500 or 1000) to reduce binomial variance.
- **4 draws per adapter is small** — SD estimate itself has
  ~30% error at n=4. For publication-grade statistics, 8+ draws
  recommended. Pre-registered threshold (1× / 2× SD) is
  conservative given small-n.
- **Harness scoring unchanged across all 8 draws**: priority-1
  (`#### N` strict) catches 98-100% of v7 and v8 outputs. The
  harness extraction is stable; variance is in model generation,
  not scoring.

## Confirmation-bias checklist

- [x] **Interpreted per pre-registered thresholds**. 0.14× < 1×
      → indistinguishable per the pre-reg mapping. Did not shift
      thresholds post-hoc.
- [x] **Reviewed all 8 draws individually** before computing
      means. Confirmed no outlier is hiding the story (both
      arms span 38-45% range cleanly).
- [x] **Reasonable alternative explanations considered**:
      implicit multi-seed may not fully capture generation
      variance (process timing isn't a controlled seed). Future
      explicit-seed replication could sharpen; current result is
      conservative under that uncertainty.
- [x] **Would the follow-up be different if the result inverted?**
      Pre-registered: if drop confirmed real, pursue B/C against
      solid baseline. If indistinguishable, series conclusion
      "data scale alone doesn't help" firms up and B/C become
      higher priority for finding ANY capability lever. The
      current outcome strengthens the case for TB-US-082
      Candidate B (expand LoRA to MLP) because we've now ruled
      out data scale as the hidden-noise culprit.

## Decision + next-trial direction

**Trial #7 outcome**: Trial #6's apparent regression was noise.
Revised series state: Trials #5 and #6 statistically equivalent
at holdout, both equivalent to bare Instruct within noise.

**Current demo**: UNCHANGED (bare Instruct 43% remains the
headline).

**TB-US-082 queued** with 2 remaining capability-gain candidates:
- **Candidate B** — Expand LoRA target modules to MLP. Tests
  the "LoRA capacity trap at rank 16" mechanism directly.
  Cheapest. Uses v7 training set (keeps data constant with
  Trial #5 for clean comparison).
- **Candidate C** — Full fine-tuning (not LoRA). Expensive.
  Tests the "low-rank constraint is the capability ceiling"
  mechanism.

**Recommendation**: **Candidate B first**. Cheap enough to be
worth trying before investing in C. If B lifts accuracy, we
have a working capability lever. If B doesn't lift, C becomes
the deciding test for whether LoRA rank itself is the ceiling
vs. something deeper about this base-model + task combination.

**Series close condition**: if B and C both fail to achieve
H6/H7/H8-primary (holdout ≥ 50%), close the arc with the final
paper-draft section: "QLoRA on Llama 3.1 8B Instruct does not
materially improve GSM8K accuracy across the 1k-5k sample
scale, at rank 16, with attention-only or attention+MLP target
modules, at lr 1e-4, 3 epochs. Chat-template format alignment
is necessary to avoid regression (Trial #4's lesson); scaling
within these dimensions is a no-op on gross accuracy." That's
a publishable negative finding with real scientific value.

## Reproducibility

- Base model: `meta-llama/Meta-Llama-3.1-8B-Instruct`
- Adapter v7: `adapter_versions.v7`, sha256
  `0dcdbdeac53fff4af90c42f045ca99bd48e9f2556b0fb55c2d8149c69d559653`
- Adapter v8: `adapter_versions.v8`, sha256
  `45811c85fc22cba24eb91aad1176252618885b39e7ed286581401defcf09de9e`
- Harness: harness_version=5 (holdout, `math_eval_200_holdout.jsonl`)
- System prompt: `rag-seeds/math-example-v1/system-prompt.txt`
- Inference config: `do_sample=True, temperature=0.7, top_p=?, top_k=?`
  (from `backend/rag/rag_system.py` defaults;
  `LLM_TEMPERATURE=0.7`)
- RNG: implicit via process timing (NO explicit seed)
- Experiments: E21 (Trial #5 original), E25/E27/E29 (Trial #7
  new) for v7; E24 (Trial #6 original), E26/E28/E30 (Trial #7
  new) for v8
- Analysis: `scripts/tb_us_081_run_experiments.py` (orchestrator;
  note: original invocation hit a 24h session-token expiry
  mid-run; E29/E30 were manually resumed with a re-minted token
  — see "Related infrastructure friction" note at the bottom of
  this doc)
- Hardware: RTX 3090, 24 GB VRAM
- Software: TB-US-074 compat (`transformers` 5.x), bitsandbytes
  4-bit QLoRA

## Related infrastructure friction (process note)

Mid-run, the 24-hour session-token expiry hit the experiment
runner script after E28 completed (before E29). The script
crashed at a 401 while polling experiment state; the TB
service's background task kept running E29 correctly, but the
runner couldn't observe its completion. Recovery: re-minted
the session token, confirmed E29 still running, launched E30
manually. Zero data loss but ~15 minutes of operator
intervention.

This surfaced a structural question about TB's auth model:
session tokens are designed for interactive browser use with
24h windows; research automation running > 24h needs either
long-lived API keys or configurable session windows. Discussed
at length with operator (see conversation log 2026-11-03);
follow-up story may file an auth-architecture + API-key
mechanism (TBD — operator considering).
