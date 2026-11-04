# Research Methodology — math-example PEFT Study

**Status**: Research protocol, publication-grade. Append to this
document when the methodology itself changes; do NOT rewrite
historical sections.
**Owned by**: TB-US-075 through TB-US-078+ (ongoing research
series)
**Created**: 2026-11-02
**Research mode entered**: 2026-11-02 — operator shifted focus from
"ship a demo" to "produce a publishable study on when PEFT helps
vs. harms strong instruction-tuned bases"

## Research question

**Can parameter-efficient fine-tuning (PEFT) improve a strong
instruction-tuned base model's accuracy on a well-studied
benchmark, and under what conditions?**

Specifically, using Llama 3.1 8B Instruct + GSM8K as our test
case:

1. (Primary) Can PEFT variants achieve holdout accuracy > bare
   Instruct's 43% zero-shot (measured by our harness)?
2. (Secondary) Which training-approach dimensions matter most
   (format alignment, perturbation size, training-set signal
   strength, task framing)?
3. (Tertiary) Does the "fine-tuning helps weak bases, harms
   strong bases" pattern we observed replicate across PEFT
   variants?

## Position relative to prior work

Published literature anchors our expectations:

| Model / Setup | Reported GSM8K (approx) | Source type |
|---|---|---|
| Llama 3.1 8B base, no training | ~0–5% zero-shot | Model card + Trial #1 bare |
| Llama 3.1 8B Instruct, zero-shot | 55–70% depending on harness | Meta model card, HF leaderboards |
| **Llama 3.1 8B Instruct (our harness, baseline-test)** | **43%** | **Trial #4 bare control (E19)** |
| **Llama 3.1 8B Instruct (our harness, holdout)** | **43%** | **Trial #5 bare control (E22)** |
| Llama 3.1 8B Instruct + QLoRA, chat-template format, 1000s×3ep | **44%** | **Trial #5 adapter v7 (E21, our result)** |
| Llama 3.1 8B Instruct + QLoRA, chat-template, **5000s**×3ep | **42.5%** (single draw) → **41.62% mean** (4 draws, Trial #7) | **Trial #6 adapter v8** + Trial #7 revision |
| Llama 3.1 8B Instruct (our harness, holdout, 4 draws) | **41.8% grand mean** (Trials #5+#6 adapters combined, 8 draws) | **Trial #7 multi-seed** |
| **Llama 3.1 8B Instruct + QLoRA, chat-template, 1000s×3ep, +MLP targets** | **53.75% mean** (4 draws, SD 2.78pt, +10.75pt vs bare) | **Trial #8 adapter v9 (our positive result)** |
| Llama 3.1 8B + math LoRA (published) | 60–75% typical | Scattered papers 2024-2025 |
| MetaMath-Mistral-7B (purpose-built) | ~77% | MetaMath paper |
| Deepseek-Math-7B-Instruct | ~82% | Deepseek paper |
| Llama 3.1 70B Instruct | ~85–90% | Larger-model reference |

Our 43% measured for bare Instruct is at the low end of the
published range. Likely explanations:

- Our harness extracts the final `#### N` while some published
  numbers use lenient extraction / numerical equivalence
- Our system prompt framing may not maximally elicit Instruct's
  native capability
- Prompt sensitivity: GSM8K results shift ±10pt with prompt
  wording in published studies
- Stochastic noise: 200-sample measurements have ±~5pt binomial
  variance

We treat our 43% as the ground-truth bare baseline *for our
harness configuration* — comparisons against our own trials are
valid; comparisons across published numbers require harness
normalization.

## Core design: train / validate / holdout

Standard predictive-modeling framework. See
[`study-design.md`](study-design.md) for the specific sets.

- **Baseline test (validation)**: 200 problems, GSM8K test
  split, seed=42
- **Holdout test**: 200 problems, GSM8K train split, seed=43
- **Training set**: varies per trial (derived from failures /
  random train-split / chat-template-formatted / etc.)

Disjointness invariants:
- `baseline ∩ holdout = ∅` (GSM8K test ⊥ train upstream)
- `training ∩ holdout = ∅` (enforced by sampling script at
  training-set construction)

## Hypothesis structure

Every trial pre-registers (in `study-design.md`'s per-trial
addendum, BEFORE running):

1. **Alternative hypothesis** (what we expect to find): e.g.,
   "chat-template-formatted training will produce an adapter
   whose holdout accuracy ≥ 43%".
2. **Null hypothesis** (what we'd see if our approach doesn't
   help): e.g., "chat-template-formatted training produces
   holdout accuracy < 43% within noise bounds".
3. **Numeric decision threshold** (specific, stated in advance):
   e.g., "mark alternative accepted iff holdout ≥ 48% after
   adjusting for ±5pt stochastic variance".
4. **Secondary success criteria** (nice-to-have but not primary):
   e.g., "holdout ≥ 55% = strong result".

Pre-registration locks interpretation BEFORE results. No post-hoc
threshold adjustment.

## Measurement protocol

For each trial:

1. **Training run**: one QLoRA adapter trained with pre-registered
   hyperparameters. Training telemetry (loss curves, elapsed
   time, VRAM) captured in `training_runs` + `training_run_metrics`
   tables.
2. **In-sample measurement**: new experiment pinning the adapter
   + baseline-test harness, at `n_samples=200`.
3. **Out-of-sample (holdout) measurement**: new experiment pinning
   the adapter + holdout harness, at `n_samples=200`.
4. **Bare-base control**: either reuse an existing bare measurement
   OR run a new one. Required for every trial on a new base model
   or substantially new configuration.
5. **Per-sample inspection**: at least 10 right + 10 wrong
   outputs reviewed by hand to characterize failure modes.

## Reproducibility checklist

Every trial captures (in its deep-dive doc):

- [ ] **Base model identifier** including version/revision (e.g.,
      `meta-llama/Meta-Llama-3.1-8B-Instruct` at HF Hub revision
      `0e9e39f249a16976918f6564b8830bc894c89659` or main)
- [ ] **Training data**: source dataset, sampling script path,
      random seed, resulting file path + line count +
      content_sha256 (via `training_set_versions` table)
- [ ] **Training script**: file path + commit hash where the
      script lived at training time
- [ ] **Hyperparameters**: full dict as passed to
      `TrainingArguments` (pre-stated)
- [ ] **Hardware spec**: `nvidia-smi --query-gpu=name,memory.total,
      driver_version --format=csv` output
- [ ] **Software versions**: `pip freeze` snippet for `torch`,
      `transformers`, `peft`, `bitsandbytes`, `accelerate`
- [ ] **Adapter artifact**: `adapter_versions` row (content_sha256
      + files_path)
- [ ] **Measurement harness**: `harness_versions` row (definition_json
      + content_sha256)
- [ ] **Experiment pins**: full `experiment` row (which adapter,
      harness, prompt, llm_identifier)
- [ ] **Random seeds**: Python random seed used in training (if
      explicit), DataLoader seed, generation seed (if any)
- [ ] **Elapsed wall-clock time** for training + each measurement

## Statistical analysis

**Primary analysis**: single-run accuracy comparison (bare vs.
adapter) with ±5pt binomial noise band at n=200.

**Multi-seed replication** (optional for critical trials):
re-run the adapter measurement 3× with different generation
seeds. Report mean + range. Required if a single-run difference
is within ±3pt (indistinguishable from noise).

**Effect size reporting**: raw point difference (adapter − bare)
alongside percentage. "Adapter v5 cost 40 correct answers out of
200 (−20 pt)" is more informative than "20% decrease".

## Threats to validity framework

Each trial's deep-dive addresses:

### Internal validity (did we measure what we think)

- Harness bias: are we scoring correctly? (Patched harness
  v4/v5 fixed the TB-US-056 full-string-equality bug but may
  have residual edge cases)
- Prompt sensitivity: does the system prompt artificially cap
  the base's performance?
- Train-test overlap: enforced disjoint at seed-level but
  double-check per-trial
- Measurement artifact: multiple `####` in output + regex-last
  behavior could cause false positives/negatives

### External validity (does it generalize)

- GSM8K specifically — do findings transfer to other math
  benchmarks? To other domains?
- 8B-model scale — do findings hold at 70B? At 1B?
- Llama 3.1 Instruct specifically — do findings generalize to
  Qwen, Mistral, DeepSeek Instruct variants?

### Construct validity (right concept)

- "Accuracy on GSM8K" is one proxy for math capability; does it
  measure the thing we care about?
- "Improvement from PEFT" is one proxy for method value; is
  there a more informative metric (sample efficiency, final-step
  loss, latency impact)?

### Statistical validity (right conclusions)

- 200 samples has ±5pt binomial variance; single-trial differences
  below that are not conclusive
- No multi-seed replication yet → stochastic noise could be
  misinterpreted as effect
- Multiple comparisons across trials → risk of p-hacking (not
  computing p-values but hypothesis-shopping has same risk)
- Confirmation bias: trial design informed by prior-trial
  results, which can bias toward confirmatory findings

## Known research-process limitations discovered during execution

Research methodologies are works-in-progress. When a limitation
of the infrastructure or protocol is discovered mid-study, it is
documented here (and in a per-finding deep dive) so that
publication readers can distinguish findings-under-the-limitation
from findings-under-the-corrected-protocol.

### 2026-11-02 — `training_set_versions` was never wired into `train.py` (Trials #1–#4)

**Finding**: from TB-US-065 ship date (2026-10-22) through
TB-US-078 fix (2026-11-02), `train.py` unconditionally read raw
GSM8K via `load_from_disk` and did not consult the
`training_set_version_id` for data input. The ID was recorded on
each adapter's provenance row but did not drive training.

**Scope**: Trials #1 through #4 (TB-US-075, 076, 077) all ran at
approximately constant training data (first N rows of
GSM8K.train). Trial-to-trial comparisons on hyperparameters
(rank, epochs, learning rate, base model) remain valid at
approximately-constant-data. Trial-to-trial comparisons that
*appear* to vary training data (e.g., "v4 vs. v5 vs. v6") were
in fact variations in provenance labels only.

**Fix**: TB-US-078 — clean cutover; train.py now reads from
`training_set_versions.v{N}` sidecar JSONL and uses each row's
`text` field verbatim.

**Not re-run**: Trials #1–#4 are not re-run under corrected
wiring. Their findings (harness bug, overfit at 10 epochs,
Instruct regression) do not change under the fix. Reproducibility
documentation (what each adapter was *actually* trained on) is
updated to reflect the as-discovered reality.

**Deep dive**: `architectural-finding-training-set-wiring.md`.

**Trial #5 (TB-US-079) is the first trial under corrected wiring.**

### 2026-11-03 — Harness runner uses stochastic sampling with no explicit RNG seed (Trials #1–#6)

**Finding**: `backend/api/harness_runner.py` creates its HF
pipeline with `do_sample=True, temperature=0.7, top_p, top_k`
and does NOT set an explicit RNG seed. Every experiment run is
thus one stochastic draw from a generation distribution, not a
deterministic measurement. All prior single-run measurements
across Trials #1–#6 are each one draw.

**Scope**: Trials #1–#6 reported single-run accuracy as if it
were the authoritative measurement. The ±5pt binomial noise
band we used is a lower bound; true noise includes generation
stochasticity on top.

**Fix**: Trial #7 (TB-US-081) introduced multi-seed replicate
discipline. Discovered the configuration during pre-registration,
documented it, and used implicit RNG variation via fresh process
state. Measured ~6pt noise envelope for GSM8K at n=200 with our
config.

**Going forward**: trial-to-trial comparisons < 6pt should not
be interpreted as signal without multi-seed replication. For
publication-grade reproducibility, add `generation-seed` param
to the harness runner (potential future story).

**Trials affected (comparison claims re-interpreted)**:
- Trial #5 vs. bare Instruct (+1.5pt): revised to "no detectable
  difference within noise"
- Trial #6 vs. Trial #5 (−2pt): revised to "no detectable
  difference within noise" (Trial #7 explicit resolution)
- Trial #4 vs. bare (−20pt): remains a real finding (far outside
  envelope)
- Trial #2 vs. Trial #5 (−16pt between base-model and
  Instruct-model adapters): remains real

**Deep dive**: `multi-seed-replicate-results.md`.

## Negative results are first-class

TB-US-077 Trial #4 produced a REGRESSION (adapter v5 at 23% vs.
bare 43%). This is a **publishable finding**, not a failure.
Studies that show "approach X doesn't work in setting Y" are
scientifically valuable and under-reported in ML literature.

Our methodology captures negative results with the same rigor
as positive ones:
- Pre-registered threshold not met → explicit statement
- Mechanism of failure characterized (F13 "answer-first" pattern)
- Follow-up design (TB-US-078) addresses the identified mechanism

## Confirmation-bias checks

Before closing any trial, operator + researcher review:

1. **Did we interpret the result as the pre-registered thresholds
   dictate**, not as our expectations wanted?
2. **Did the per-sample inspection include samples that would
   contradict our story**, not just samples that confirm it?
3. **Could a reasonable alternative explanation** account for the
   result (e.g., harness bug, prompt artifact, lucky/unlucky
   seed)?
4. **If the result pointed the OTHER way**, would we have
   proposed the follow-up differently? (Yes = sign of
   over-fitting the narrative to the result.)

## Publication artifact plan

Toward a future technical report / preprint:

- `methodology.md` (this doc) → **Methods section**
- `study-design.md` → **Experimental design appendix**
- `sweet-spot-search-log.md` → **Chronological results narrative**
- Per-trial deep dives (`measured-improvement.md`,
  `harness-tolerance-results.md`,
  `format-retrain-results.md`,
  `instruct-scale-up-results.md`, future) → **Per-experiment
  detail appendices**
- Future: a summary paper draft at
  `docs/math-example/paper-draft.md` once ≥ 2 trials in the
  Instruct-PEFT direction complete

**Working title (placeholder)**: *"When PEFT Helps and When It
Harms: A Methodology for Investigating Fine-Tuning on
Instruction-Tuned Bases"*

## Scope boundary

This methodology document is **stable**. It describes HOW we do
research. Changes to the methodology itself (e.g., switching
from single-run to multi-seed as the default) require their own
story + rationale.

Trial-specific design decisions live in `study-design.md`
addendum (per trial). The chronological record lives in
`sweet-spot-search-log.md`.
