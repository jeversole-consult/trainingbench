---
title: Staged Progression
description: The math-example agent runs three measured experiments showing how adapter training and RAG retrieval each contribute to accuracy.
---

# Staged Progression

The shipped **math-example agent** is TrainingBench's pedagogical
demo: a Llama 3.1 8B base, a 500-example GSM8K training set, a small
reference RAG, a tutor-framed system prompt, and a 200-question eval
harness. All pre-wired. Running the three experiments shows what the
TB staged-progression workflow does and how each component is pinned
and measured.

> **Methodology correction applied 2026-11-07** ([TB-US-092](https://github.com/jeversole-consult/trainingbench/blob/main/docs/user-stories/tb-us-092.md),
> [TB-US-093](https://github.com/jeversole-consult/trainingbench/blob/main/docs/user-stories/tb-us-093.md)).
> Nine PEFT trials run through 2026-11-06 reported adapter gains of
> up to +17pt vs. bare Llama 3.1 8B Instruct. Those measurements
> used a harness that built inference prompts via raw-string
> concatenation (`"Question: ...\n\nAnswer:"`) while the training
> script applies the Llama 3.1 Instruct chat template. That
> **train/eval format mismatch** suppressed the bare-Instruct
> baseline by ~37pt (48% on broken harness vs. 84.1% on fixed) and
> was the entire source of the apparent lift. After fixing the
> harness and re-measuring with multi-seed discipline, **both
> trained adapters (v9, v10) regress ~10pt below bare Instruct**
> on the same holdout. Adapter v10 is deprecated as of 2026-11-07;
> the math-example demo now ships bare Llama 3.1 8B Instruct. The
> reframed arc is more pedagogically valuable than the original
> claim — see [*What this arc actually teaches*](#what-this-arc-actually-teaches)
> below.

## Real baselines (shipped artifacts, measured 2026-10-25)

| # | Label | Prompt | RAG | Adapter | Base | Correct | Duration |
|---|---|---|---|---|---|---|---|
| E1 | `math-example-e1-bare-llama-3.1-8b` | tutor | — | — | Llama 3.1 8B | **0 / 200** | 20 min |
| E2 | `math-example-e2-plus-adapter` | tutor | — | ✅ v2 | Llama 3.1 8B | **0 / 200** | 42 min |
| E3 | `math-example-e3-plus-rag` | tutor | ✅ v3 | ✅ v2 | Llama 3.1 8B | **0 / 200** | 42 min |

**All three stages measure at 0.0 accuracy** with the shipped
pedagogical artifacts. The workflow is what the first-install example
demonstrates — not performance.

## The current demo: bare Llama 3.1 8B Instruct (2026-11-07)

After nine PEFT trials + a harness fairness fix + an honest
re-baseline, the math-example demo ships as **bare Llama 3.1 8B
Instruct with no PEFT adapter**. Both trained adapters we had
previously promoted are now deprecated.

| Setup | GSM8K-200 holdout accuracy (fixed harness, chat template) |
|---|---|
| **Llama 3.1 8B Instruct (bare)** | **84.1% mean** (4 draws, SD 1.4pt, range 82.5–85.5) |
| + adapter v9 (rank 16 attn+MLP QLoRA) | 74.4% mean (SD 3.2pt) → **−9.75pt** vs. bare, 3.96× pooled SD |
| + adapter v10 (rank 32 attn+MLP QLoRA) | 73.6% mean (SD 3.0pt) → **−10.5pt** vs. bare, 4.55× pooled SD |

Both adapters regress ~10pt on a correctly-measured baseline.
The v10-vs-v9 difference is indistinguishable noise (0.24× pooled
SD). As of 2026-11-07, adapter v10 is `state=deprecated`, the
math-example agent runs bare, and the "+17pt" lift claimed in
earlier versions of this page has been withdrawn.

**Our 84.1% bare-Instruct number** is in line with Meta's reported
Llama 3.1 8B Instruct GSM8K performance (published as high-80s to
low-90s on various GSM8K evaluations) — accounting for subset
sampling, grader differences, and stochastic generation. See
[Meta Llama 3.1 model card](https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/MODEL_CARD.md)
and [Cobbe et al. 2021](https://arxiv.org/abs/2110.14168) (GSM8K).

## What this arc actually teaches

The math-example arc is now a research-methodology lesson, not a
PEFT-performance demo. The useful takeaways:

### 1. Train/eval format mismatch produces false capability gains

Our training pipeline applied the Llama 3.1 Instruct chat template.
Our inference pipeline did raw-string concatenation. The model had
to decode our informal "Question: ...\n\nAnswer:" prompts into
something it could answer — and the adapters got extra reward for
learning this decoding during training. Bare Instruct, denied the
chat template, had to struggle with the raw-string format too — so
it scored unnaturally low (48%). The +17pt "capability gain" was
entirely format-decoding compensation.

**Check for this before trusting any PEFT measurement:** do training
and inference use the same prompt format? If you're using a chat-
tuned base, do both apply `tokenizer.apply_chat_template()`? If your
baseline bare measurement sits far below published numbers, suspect
format mismatch first.

### 2. Multi-seed discipline alone doesn't catch format artifacts

We established a 6pt noise envelope at n=200 via multi-seed replication
([TB-US-081](https://github.com/jeversole-consult/trainingbench/blob/main/docs/user-stories/tb-us-081.md)).
The adapter's +17pt gain was outside that envelope. Multi-seed told
us the comparison was statistically clean — but the signal it was
measuring was an artifact, not a capability. Multi-seed is necessary
but not sufficient. **Always sanity-check your baseline against
published numbers for the same model + benchmark.**

### 3. The adapter made the model worse on fair measurement

Not because fine-tuning is bad. Because we were **competing on the
flagship labs' home turf, on a benchmark their models had already
been trained against, with ~0.001% of their compute**:

- GSM8K is a well-known public benchmark. Meta, OpenAI, Anthropic,
  and others have optimized their models directly or indirectly
  against it.
- Llama 3.1 8B Instruct carries that optimization. Its 84.1% on our
  holdout is Meta's work, not ours.
- Our PEFT (QLoRA, rank 16-32, 1-5K training samples, single RTX
  3090) tried to add capability a far larger-scale optimization had
  already saturated. Modest fine-tuning in that regime doesn't add
  — it distorts the pretrained distribution and costs more than it
  adds.

## When PEFT DOES earn its keep

Our math-example arc shows what NOT to do with PEFT. Here's what
TO do instead:

| Use PEFT when… | Avoid PEFT when… |
|---|---|
| Your domain data is proprietary / internal / novel (customer-service corpora, internal knowledge, specialized scientific data) — things no flagship lab trained against | You're targeting a public benchmark flagship models have already been optimized against (GSM8K, MMLU, HumanEval, HellaSwag, etc.) with modest data + compute |
| Starting from a weaker / smaller / less-tuned base model with real capability headroom to fill | Starting from a strong Instruct variant at its natural ceiling for your task |
| Training on a reasonably-sized domain corpus (10K-100K+ labeled examples) | Training on 1-5K examples hoping to move a well-tuned model |
| Pursuing a novel task framing the pretrained model hasn't been optimized for | Pursuing an obvious capability the pretrained model already has |

**TB's value proposition for operators**: take this math-example arc
as the cautionary tale it ends up being. Then point TB at *your* data
— the domain nobody has trained against, where your knowledge is the
headroom. That's where PEFT earns its keep.

## The nine trials (historical)

The measurements below used the pre-fix harness; they are preserved
here as the arc record. Direct comparisons between trials are
internally consistent (same harness bug applied to all), but the
absolute numbers overstate everything by the format-decoding margin.
See the Trial #10 entry in
[`sweet-spot-search-log.md`](https://github.com/jeversole-consult/trainingbench/blob/main/docs/math-example/sweet-spot-search-log.md)
for the corrected numbers against the fixed harness.

- Trial #4: first attempt at an Instruct-base adapter regressed
  accuracy by 20 points — attributed at the time to a format bug
  deleting Instruct's `#### N` pattern. **Retroactive reading** (per
  TB-US-092): the regression was likely a milder version of what
  v9/v10 later did — PEFT distorting a well-tuned baseline. The
  "format-mismatch bug" we fixed was real but not the whole story.
- Trial #5: chat-template-formatted training restored accuracy to
  "bare-equivalent" — which, retroactively, was still against a
  suppressed bare baseline.
- Trial #6: scaling training data 5x was an accuracy no-op. Correct
  conclusion; unchanged by the re-baseline.
- Trial #7: multi-seed replication established the ~6pt noise
  envelope at n=200. Methodology finding; unchanged by the
  re-baseline and still the right discipline.
- Trial #8: expanding LoRA target modules from 4 (attention only) to
  7 (attention + MLP) was reported as "unlocking reasoning capacity"
  (+10.75pt vs bare). **Retroactive reading**: the apparent gain was
  format-decoding compensation, not reasoning unlock. The adapter's
  within-structure accuracy claim (54.0% vs bare 48.2%) was
  measured against the same suppressed bare baseline.
- Trial #9: doubling LoRA rank from 16 to 32 (adapter v10) added
  another +6.38pt. **Retroactive reading**: fixed-harness means put
  v10 at 73.6% vs. v9 at 74.4% — essentially tied (0.24× pooled SD).
  The "rank sweep helps" conclusion was noise.
- **Trial #10** (TB-US-092 Phase 2): re-baseline against the fixed
  harness. Bare 84.1%, v9 74.4%, v10 73.6%. Both adapters regress.
  Arc closes honestly.

Deep dives (preserved with mismatched-harness measurements; refer
to Trial #10 for corrected comparisons):

- [Trial #8 mlp-expansion-results.md](https://github.com/jeversole-consult/trainingbench/blob/main/docs/math-example/mlp-expansion-results.md)
- [Trial #9 rank-sweep-results.md](https://github.com/jeversole-consult/trainingbench/blob/main/docs/math-example/rank-sweep-results.md)

## Reproduce the current demo

```python
# Current math-example demo: bare Llama 3.1 8B Instruct, no adapter.
# Measured 84.1% on a 200-item GSM8K holdout via the fixed harness
# (chat template + <|eot_id|> stop criterion).
from transformers import AutoTokenizer, AutoModelForCausalLM
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Meta-Llama-3.1-8B-Instruct")
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Meta-Llama-3.1-8B-Instruct",
    # ... fp16 or 4-bit QLoRA via bitsandbytes
)
# Harness: backend/harnesses/math_qa_v1.py
# Prompting: tokenizer.apply_chat_template(messages, add_generation_prompt=True)
# Stop criterion: eos_token_id=[<|eot_id|>, tokenizer.eos_token_id]
```

---

## Historical: Targeted retraining on the base variant (2026-10-31)

To prove the workflow does more than "ships at zero",
[TB-US-075](https://github.com/jeversole-consult/trainingbench/blob/main/docs/user-stories/tb-us-075.md)
applied the classical **train / validate / holdout** methodology to
targeted retraining:

- **Baseline test** (200 problems from GSM8K test split) — measure
  bare model to find failures
- **Training set** — the 200 baseline failures paired with their
  GSM8K ground-truth answers
- **Holdout test** (200 problems from GSM8K train split, seed=43,
  strictly disjoint from everything else) — out-of-sample
  generalization check

Pre-registered hypothesis: if the adapter learned the SKILL (not
just memorized the answers), both the baseline rerun AND the
holdout should improve, with the gap between them small.

### Results

Measured under the shipped harness **after a one-line fix**
(TB-US-076 added real answer-extraction to `math_qa_v1.py`):

| Measurement | Correct | % |
|---|---|---|
| Bare baseline (adapter=None) | 0 / 200 | 0% |
| **In-sample post-training (adapter v3)** | **38 / 200** | **19%** |
| **Out-of-sample holdout (adapter v3)** | **52 / 200** | **26%** |

**Generalization**: holdout performance (26%) is actually
*higher* than in-sample (19%) — a strong rejection of
memorization. The adapter learned transferable skill, not
specific-answer lookups.

### What this means

The adapter went from **0% bare baseline → 26% out-of-sample on
200 problems it never saw during training**. On an 8B base model
after a 5-minute QLoRA fine-tune, that's a credible first result
for grade-school math reasoning.

**Representative output** (the model's step-by-step work for
Jared's typing problem, correctly solved):

```
Q: Jared is trying to increase his typing speed. He starts with
   47 WPM. After some lessons his speed increases to 52. If he
   continues to increase it once more by 5 words, what will be
   the average of the three measurements?

Adapter output:
   47 + 5 = 52
   52 + 5 = 57
   (47 + 52 + 57) / 3 = 52

   Final Answer: 52
```

Correct arithmetic, correct final answer. The TB-US-076 harness
patch now extracts `52` from `Final Answer: 52` and compares it
to expected `52` — match. Before the patch, the shipped harness
did full-string equality and matched nothing.

### We also tried retraining — and it got worse

TB-US-076 also tested *more training* (10 epochs × 300 samples
instead of 5 × 200) to see if more exposure would improve
results. The adapter v4 result dropped to **6% in-sample / 7.5%
holdout** — the eval loss curve during training showed classic
overfitting (eval loss rose in the last 2 epochs while train
loss kept dropping). **Lesson captured for the demo**: more
training is not always better on small datasets.

### The search log

The whole trial-and-error journey — three trials across two
stories, with hypotheses, findings, decisions, and next-step
candidates — is logged chronologically in
[`docs/math-example/sweet-spot-search-log.md`](https://github.com/jeversole-consult/trainingbench/blob/main/docs/math-example/sweet-spot-search-log.md).
That log IS the methodology's roadmap artifact.

Deep dives:

- [Trial #1 (adapter v3 initial measurement)](https://github.com/jeversole-consult/trainingbench/blob/main/docs/math-example/measured-improvement.md)
- [Trial #2 (harness tolerance patch; the real-numbers win)](https://github.com/jeversole-consult/trainingbench/blob/main/docs/math-example/harness-tolerance-results.md)
- [Trial #3 (adapter v4 retrain; overfitting lesson)](https://github.com/jeversole-consult/trainingbench/blob/main/docs/math-example/format-retrain-results.md)

**What the shipped example proves:**
- Training launches, backgrounds, auto-registers an adapter ✅
- Experiments pin specific component versions and run against a
  shared hold-out eval ✅
- Each experiment loads a distinct model stack (bare vs. +adapter
  vs. +adapter+rag) with correct version resolution ✅
- Measurements are reproducible, stable, and comparable ✅

**What it doesn't prove, by design:** that a 500-example LoRA at
minimal hyperparameters produces a performant GSM8K solver. See
*Why the baselines are flat* below for why that's expected.

## Why the baselines are flat

Four reasons, in rough order of effect:

1. **Base model is not instruct-tuned.** Llama 3.1 8B *base* follows
   the few-shot `#### answer` format pattern well, but it doesn't
   solve the problems — it continues with plausible-looking math
   prose. E1's outputs show the model generating new fictional
   question-and-answer pairs rather than solving the posed problem.
2. **500-sample LoRA is undertrained.** 500 training examples × 3
   epochs on GSM8K-level reasoning is roughly 1500 training-example
   views. Published math-reasoning LoRAs typically train on ≥10k
   examples with higher LoRA rank. The shipped 500-sample set is
   pedagogical scaffolding, not a performant corpus.
3. **RAG manifest is a 3-document toy.** Grade-school word problems
   are language-parsing, not formula-lookup — adding three reference
   documents doesn't help the model do arithmetic.
4. **Grader is strict.** The harness compares the final `####
   number` against ground truth. Any format drift or wrong number
   scores zero.

None of these are bugs. They're the expected properties of a demo
whose purpose is *"prove the staged-progression workflow runs end to
end on first install"*. For a performant math agent, retrain with
more data (see *Make it work* below).

## Stage 0 — Bare Llama 3.1 8B

The base model's native grade-school math ability. No fine-tuning,
no retrieval, just pretrained weights + the tutor system prompt.

**Measured:** 0 / 200. **What this answers:** "If I just ran an
off-the-shelf model with no training, what would I get?" On GSM8K
with a non-instruct base: nothing.

### Representative output

```
Q: A classroom has 18 markers and the teacher buys 24 more.
   How many markers are there now?

A: #### 42
   But first, let's set up a question of our own...
   Q: A library has 1,284 books on hand. If the librarian...
```

Common failure: the base model continues the few-shot pattern with
new fictional problems instead of solving the one asked. The parser
grabs the first `####` which happens to be correct by coincidence —
but across 200 samples, this doesn't generalize.

## Stage 1 — + Adapter

Same base model, same prompt, no RAG — plus the LoRA adapter trained
on 500 GSM8K examples via QLoRA (rank 16 / alpha 32 / lr 2e-4 /
3 epochs). Training produces ~100 MB of adapter weights loaded
alongside the base.

**Measured:** 0 / 200. **What this answers:** "How much does
fine-tuning on 500 domain examples help?" At this scale, enough to
change the output format but not enough to reliably solve the
problems. The adapter *does* learn to produce step-by-step
reasoning — but the arithmetic is wrong often enough that no sample
in the 200-question set lands.

### Representative output

```
Q: A classroom has 18 markers and the teacher buys 24 more.
   How many markers are there now?

A: Let x = starting markers.
   Let y = new markers.
   x = 18, y = 24.
   total = x + y = 42.
   #### 48
```

Format is cleaner than E1 (variables + computation steps), but the
final arithmetic is wrong. This is the characteristic failure mode
of an undertrained GSM8K LoRA.

## Stage 2 — + RAG

Same adapter + prompt, plus a 3-document reference RAG (problem-
solving strategy guide + worked examples + formula sheet). Each
query retrieves relevant context and injects it into the prompt.

**Measured:** 0 / 200. **What this answers:** "Does retrieval help
on top of training?" On GSM8K specifically: no — the problem is
arithmetic reasoning, not formula recall. **A null delta is a
legitimate finding** that teaches operators RAG isn't universally
useful. Fix the arithmetic (retrain the adapter) and the ladder
would light up at Stage 1, not Stage 2.

## Make it work

If you want to see the ladder light up, retrain with better
settings:

```bash
# via UI: Training Runs → + Create Training Run
# via CLI: python training/math/train.py --run-id <N>
```

**Scale-up suggestions**, in rough order of effect:

| Dial | Shipped | Try instead |
|---|---|---|
| Training-set size | 500 samples | 5000+ (increase `scripts/prep_math_example_jsonl.py` sample count) |
| Epochs | 3 | 5-8 |
| LoRA rank | 16 | 32 or 64 |
| Base model | Llama 3.1 8B *base* | Llama 3.1 8B **Instruct** (follows format far better) |

The last one — swapping to the Instruct variant — is the single
largest lever on this benchmark. The *base* variant was shipped to
keep the demo artifact-pure (no instruction fine-tuning the operator
didn't do themselves), but a performant demo will use Instruct.

## Why this matters

The staged progression demonstrates two patterns that generalize:

- **Measure before you promote.** Pick a hold-out eval. Measure
  Stage N. Measure Stage N+1. If the delta isn't positive, don't
  ship.
- **Different techniques solve different problems.** Fine-tuning
  teaches format and domain patterns; RAG retrieves reference facts.
  If your problem is arithmetic reasoning (GSM8K), neither of them
  alone is magic. If your problem is factual knowledge lookup, RAG
  is everything.

The shipped math-example demonstrates these patterns on a working
TB installation. Your real agent — your training set, your RAG,
your base — will have its own ladder.

## Reproduce or fork

- **Dataset:** GSM8K ([OpenAI, 2021](https://arxiv.org/abs/2110.14168)),
  MIT-licensed, downloaded via `scripts/download_gsm8k.py` into
  `datasets/math/data/`.
- **Training set:** 500 examples sampled deterministically (seed=42)
  via `scripts/prep_math_example_jsonl.py`.
- **Eval set:** 200 held-out examples; no overlap with the training
  set (assert-checked).
- **Base model:** Llama 3.1 8B (base variant). Requires accepting
  Meta's license on HuggingFace Hub.
- **Adapter training:** QLoRA (4-bit quantization + LoRA rank 16 /
  alpha 32 / lr 2e-4 / 3 epochs). Fits in ~16 GB VRAM on an RTX 3090
  in ~3–4 hours.

Full install walkthrough: [Getting Started]({{ '/getting-started.html' | relative_url }}).
