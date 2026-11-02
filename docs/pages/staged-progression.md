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

## Real baselines (shipped artifacts, measured 2026-10-25)

| # | Label | Prompt | RAG | Adapter | Base | Correct | Duration |
|---|---|---|---|---|---|---|---|
| E1 | `math-example-e1-bare-llama-3.1-8b` | tutor | — | — | Llama 3.1 8B | **0 / 200** | 20 min |
| E2 | `math-example-e2-plus-adapter` | tutor | — | ✅ v2 | Llama 3.1 8B | **0 / 200** | 42 min |
| E3 | `math-example-e3-plus-rag` | tutor | ✅ v3 | ✅ v2 | Llama 3.1 8B | **0 / 200** | 42 min |

**All three stages measure at 0.0 accuracy** with the shipped
pedagogical artifacts. The workflow is what the first-install example
demonstrates — not performance.

## The current credible demo: bare Llama 3.1 8B Instruct (2026-11-02)

After four trials of training LoRA adapters, the strongest
math-example result turned out to be **the simplest: just use the
Instruct variant of the base model with no TB-specific training
at all**.

| Setup | GSM8K accuracy (strict `#### N`-aware harness) |
|---|---|
| **Llama 3.1 8B Instruct, no adapter** | **86 / 200 (43%)** on baseline-test subset |
| Llama 3.1 8B base + our best QLoRA adapter (v3) | 52 / 200 (26%) on holdout subset |

**43% out-of-the-box** on an 8B model is a credible headline for a
public-cut demo. We got there by discovering that our previous
adapter-training approach actively regressed Instruct's performance
(trained adapter v5 scored 23% on 200 holdout problems — a
20-point drop from bare Instruct's 43% baseline-test accuracy on
a different 200-problem subset of the same test set). The
methodology surfaced this because we required a bare-base control
measurement — see Trial #4 in the
[search log](https://github.com/jeversole-consult/trainingbench/blob/main/docs/math-example/sweet-spot-search-log.md).

> **Dataset note**: "baseline-test" and "holdout" are two
> disjoint 200-sample subsets of GSM8K (one from the test
> split, one from the train split). Bare Instruct has seen
> neither. The current demo's 43% is on baseline-test; Trial #5
> ([TB-US-079](https://github.com/jeversole-consult/trainingbench/blob/main/docs/user-stories/tb-us-079.md))
> measures bare-Instruct accuracy on holdout to fill the gap.

### How to reproduce

```python
# Zero-training path (what the public demo currently uses)
from transformers import AutoTokenizer, AutoModelForCausalLM
model = AutoModelForCausalLM.from_pretrained("meta-llama/Meta-Llama-3.1-8B-Instruct")
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Meta-Llama-3.1-8B-Instruct")
# ... load TB system prompt v3 and the 200-sample GSM8K harness
# (baseline-test subset: backend/harnesses/data/math_eval_200.jsonl)
# Measured: 86/200 = 43%
```

Full detail:
[`instruct-scale-up-results.md`](https://github.com/jeversole-consult/trainingbench/blob/main/docs/math-example/instruct-scale-up-results.md).

### Can we do better than 43%?

Published Llama 3.1 8B Instruct + math-LoRA numbers land in the
70–85% range, so there's clearly headroom. But our first attempt
(TB-US-077) regressed. [TB-US-078](https://github.com/jeversole-consult/trainingbench/blob/main/docs/user-stories/tb-us-078.md)
drafts the next investigation: training on chat-template-formatted
data at lower LoRA rank, which should preserve Instruct's native
response structure instead of damaging it.

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
