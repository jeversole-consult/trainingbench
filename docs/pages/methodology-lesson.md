---
title: A PEFT cautionary tale from the TB math-example
description: Nine PEFT trials against Llama 3.1 8B Instruct on GSM8K, an apparent +17pt lift, the harness bug that produced it, and the honest re-baseline that put both trained adapters ~10pt below bare. What this teaches about measuring PEFT.
---

# A PEFT cautionary tale from the TB math-example

**TL;DR**: We ran nine PEFT trials against Llama 3.1 8B Instruct
on a 200-question GSM8K subset. Reported a +17pt lift over bare.
On audit, the inference harness didn't apply the Instruct chat
template while the training pipeline did — the bare baseline was
suppressed by ~37pt, and most of the "lift" was format-decoding
compensation. Fixed the harness, re-measured, and found **both
adapters regress ~10pt below bare on fair measurement**. This
page is the lesson. It's more useful than the +17pt claim would
have been.

## The setup

- **Base model**: Llama 3.1 8B Instruct
- **Benchmark**: GSM8K (Cobbe et al. 2021,
  [arXiv:2110.14168](https://arxiv.org/abs/2110.14168)) — grade-
  school math word problems. A well-studied public benchmark that
  flagship labs have already optimized their models against.
- **Our evaluation subset**: 200 held-out GSM8K items, strictly
  disjoint from training data.
- **Our training**: QLoRA (4-bit quantization + LoRA), ranks
  16-32, attention + MLP target modules, 1-5K training samples
  from GSM8K's train split, 3 epochs, single RTX 3090 (24 GB).
- **Grader**: CoT-aware final-answer extraction + exact-string
  match on normalized numeric. Reasonable; not the source of the
  bug.

## The nine trials and the apparent win

Over three weeks of trials ([`sweet-spot-search-log.md`](https://github.com/jeversole-consult/trainingbench/blob/main/docs/math-example/sweet-spot-search-log.md)),
we iterated through:

- **Trials #1-#3**: baseline-variant experiments on the Llama 3.1
  8B base (not Instruct).
- **Trial #4**: first Instruct attempt — regressed by 20pt. We
  attributed it to a format bug deleting Instruct's native
  `#### N` pattern. (Retroactively: partly true, partly PEFT
  distorting a well-tuned baseline we couldn't see clearly.)
- **Trial #5**: chat-template-formatted training — matched bare
  Instruct. "Format alignment is necessary but not sufficient."
- **Trial #6**: scale training data 5x — no accuracy change.
- **Trial #7**: multi-seed replication established a ~6pt noise
  envelope at n=200.
- **Trial #8**: expanded LoRA target modules to include MLP
  layers — reported as "unlocking reasoning capacity" at +10.75pt
  above bare.
- **Trial #9**: doubled LoRA rank from 16 to 32 at attn+MLP —
  reported +6.38pt more, "approaching the published 60-75% band."

**Reported headline**: adapter v10 at 60.12% vs. bare Instruct's
43% → **+17.1pt lift**. We wrote a mechanism story (LoRA
capacity trap), had a reproduction snippet, had deep-dive docs,
and had multi-seed statistics. Looked clean.

## The bug

The adapter's +17pt lift sounded right. But bare Llama 3.1 8B
Instruct's 43% on our harness was far below Meta's published
~80%+ on GSM8K with chat-template CoT prompting. That gap should
have been a red flag the moment it appeared in Trial #5. We
didn't catch it because:

1. We weren't sanity-checking against published numbers. Multi-
   seed discipline told us our signal was statistically clean —
   but a statistically clean measurement of the wrong thing is
   still wrong.
2. The internal narrative ("format alignment necessary, MLP reach
   is the capability lever") got progressively more sophisticated
   and self-reinforcing. Each trial's finding slotted into the
   growing mechanism story.
3. The gap between "our bare = 43%" and "Meta's bare = 80%+"
   never got audited. We assumed it was our harness grader being
   strict or our subset being harder. Neither was true.

The actual bug: our **training pipeline** applied the Llama 3.1
Instruct chat template to format each sample —
`<|begin_of_text|><|start_header_id|>user<|end_header_id|>...`.
Our **inference harness** built prompts via raw-string
concatenation — `"Question: ...\n\nAnswer:"`. The two formats
look superficially similar but are completely different to the
model. Instruct models trained to answer chat turns do poorly
when asked to continue a conversational-looking text completion.

That's why bare Instruct scored 43% — we were feeding it a prompt
format it wasn't trained to handle. And that's why the PEFT
adapters "improved" — they were getting extra training-time
reward for learning how to decode the raw-string format the
harness would feed them at inference. Their "math capability
gain" was mostly format-decoding compensation.

## The fix and the honest numbers

One code change: make the harness call
`tokenizer.apply_chat_template(messages, add_generation_prompt=True)`
when the tokenizer has a chat template defined. Add `<|eot_id|>`
as an EOS token so generation stops at end-of-turn.

Then re-measure: 4 seeds × 3 conditions = 12 experiments on the
same 200-question holdout.

| Condition | Mean | SD | vs. bare | pooled-SD multiple |
|---|---|---|---|---|
| **Bare Llama 3.1 8B Instruct** | **84.1%** | 1.4pt | — | — |
| + adapter v9 (rank 16, attn+MLP) | 74.4% | 3.2pt | **−9.75pt** | 3.96× (highly significant) |
| + adapter v10 (rank 32, attn+MLP) | 73.6% | 3.0pt | **−10.5pt** | 4.55× (highly significant) |

Bare lifted from 43% to 84.1% — essentially the +37pt the format
fix should produce. Both adapters regress ~10pt. The v10-vs-v9
difference (the "rank sweep helped" conclusion from Trial #9) is
0.24× pooled SD — indistinguishable noise.

**The entire adapter arc was format-decoding compensation.** The
"LoRA capacity trap" story is withdrawn. Adapter v10 is deprecated.

## What this teaches

### 1. Train/eval format mismatch is a silent PEFT failure mode

Fine-tuning a model whose training-time and inference-time
prompt formats differ produces apparent capability gains that
aren't real. The adapter learns to bridge the format gap rather
than to solve the task. Multi-seed discipline doesn't catch it;
your comparison is internally consistent but measures the wrong
thing.

**Check before trusting any PEFT result on an Instruct base:**

- Does your training script call `apply_chat_template`?
- Does your inference / harness call the same chat template with
  `add_generation_prompt=True`?
- Does your bare-model baseline match the model card's published
  number? If it's >10pt below, something is suppressing it. Find
  that before trusting any PEFT improvement over it.

### 2. Multi-seed alone is not enough

Our arc had multi-seed discipline from Trial #7 onward. A ~6pt
noise envelope. 4 draws per adapter. Everything you'd want
statistically. The bug was upstream of the statistics — in the
prompt format itself. The signal was real; its interpretation
was wrong.

Multi-seed tells you the comparison is clean. **Published-baseline
sanity-check tells you the comparison measures what you think.**
You need both.

### 3. PEFT does not earn its keep on flagship home turf

We were competing on a public benchmark the flagship labs had
already optimized against (GSM8K, almost certainly in Llama 3.1's
instruction-tuning corpus directly or indirectly), using a strong
Instruct model whose GSM8K performance Meta had carefully tuned,
with ~0.001% of their compute budget. On fair measurement, we
didn't move the needle. We made it worse.

That's not surprising in hindsight. A well-tuned Instruct model
on a benchmark it's been optimized against has very little
headroom. Modest PEFT (1-5K samples, QLoRA, single GPU) distorts
the pretrained distribution more than it reinforces it.

## When PEFT DOES earn its keep

Our math-example arc shows what NOT to do. Here's the flip side:

| Use PEFT when… | Avoid PEFT when… |
|---|---|
| **Your domain is proprietary / internal / novel.** Customer-service corpora, internal knowledge bases, legal documents, specialized scientific data. Things no flagship lab trained against. | You're competing on a public benchmark flagship models have already optimized (GSM8K, MMLU, HumanEval, HellaSwag, etc.) with 1-5K training samples |
| **Starting from a weaker base** with real capability headroom to fill | Starting from a strong Instruct variant at its natural ceiling for your task |
| **Reasonably-sized domain corpus** (10K-100K+ labeled examples) targeting a specific task | 1-5K examples trying to move a well-tuned Instruct model on a saturated benchmark |
| **Task framings that haven't been optimized at pretraining scale** — your proprietary workflow, your specialized vocabulary | Obvious tasks the pretrained model already handles |

**The TB value proposition this arc illustrates**: an open-source
workbench where you can measure PEFT with the discipline flagship
labs don't openly document. Then point TB at YOUR data — the
corners nobody else has trained against — where PEFT actually
earns its keep.

## How this arc was caught

The audit was triggered by a UI feature we shipped the day the
bug was found: a side-by-side comparison modal showing two
training runs' final metrics. Looking at adapter v10 vs. adapter
v9 side-by-side, we noticed the compare modal had rendered
`—` for accuracy (training-run table didn't carry it). Backfilled
accuracy from the harness experiments into the compare rows —
and the resulting numbers (v10 at 59.5%, v9 at 48.5%) looked
suspiciously high in context. Asked "why are these so high?" —
and the audit followed.

The lesson: **build tooling that surfaces your own numbers back
to you in unfamiliar views.** We'd been looking at the same arc
through the same lens for three weeks. The compare modal was a
new lens; the broken baseline was obvious from it. It wouldn't
have been obvious from any dashboard we'd been looking at.

## Reproducing this analysis yourself

Everything in this arc is open: the harness, the training
pipeline, the experiments, the version-tracked adapters, the
search log. If you want to reproduce (or spot a mistake we
made):

- **Repo**: [github.com/jeversole-consult/trainingbench](https://github.com/jeversole-consult/trainingbench)
- **Harness**: `backend/harnesses/math_qa_v1.py`
- **Runner**: `backend/api/harness_runner.py` (includes the Phase 1
  chat-template fix from commit `b34df33`)
- **Training script**: `training/math/train.py`
- **Search log**: [`docs/math-example/sweet-spot-search-log.md`](https://github.com/jeversole-consult/trainingbench/blob/main/docs/math-example/sweet-spot-search-log.md)
- **Methodology**: [`docs/math-example/methodology.md`](https://github.com/jeversole-consult/trainingbench/blob/main/docs/math-example/methodology.md)
- **The reframe story**: [TB-US-093](https://github.com/jeversole-consult/trainingbench/blob/main/docs/user-stories/tb-us-093.md)
- **The fairness story**: [TB-US-092](https://github.com/jeversole-consult/trainingbench/blob/main/docs/user-stories/tb-us-092.md)
- **Original closing memory** (now historical): [TB-US-085](https://github.com/jeversole-consult/trainingbench/blob/main/docs/user-stories/tb-us-085.md)

If you find something we missed — a different bug, a missed
check, a stronger reframe — open an issue. The arc is the
pedagogical artifact; making it more honest or more useful is
always welcome.

## Related

- [Staged Progression]({{ '/staged-progression.html' | relative_url }})
  — the public demo page updated with these findings
- [Cobbe et al. 2021](https://arxiv.org/abs/2110.14168) — GSM8K
- [Meta Llama 3.1 model card](https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/MODEL_CARD.md)
  — the published numbers your bare baseline should be measured
  against
