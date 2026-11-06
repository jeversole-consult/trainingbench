# TB-US-092: Harness fairness + published-benchmark re-baseline

**Status**: Backlog
**Created**: 2026-11-06
**Author**: Jesse Eversole
**Depends on**: TB-US-057 (harness + eval dataset + seed agent), TB-US-065
(auto-registered adapters), TB-US-070 (experiments UI), TB-US-091
(accuracy backfill)
**Commit hash(es)**: <filled in on completion>
**Re-opens**: the math-example research arc, which was closed at
adapter v10 (2026-11-06). This story reopens it under a different
framing — not "squeeze out more performance" but "measure what we
already have fairly, cite published numbers, and let the math-example
story hold up to defense."

## Story

As a TB operator planning to use the math-example arc as a public
pitch surface — including head-to-head comparisons against bare
Llama variants + ChatGPT + Claude on the same held-out GSM8K subset —
I want **the harness to prompt the model fairly, the baseline numbers
to match published GSM8K leaderboards, and all comparisons to carry
citations and documented methodology**, so the pitch stands up to
anyone who looks closely.

## Background: what we found on 2026-11-06

While sorting through why the compare modal's accuracy numbers
"seemed high," three findings surfaced:

### 1. Train/inference prompt-format mismatch (the main issue)

- `training/math/train.py:95` applies the **Llama 3.1 Instruct chat
  template** when formatting training data —
  `<|begin_of_text|><|start_header_id|>user<|end_header_id|>...`.
- `backend/api/harness_runner.py:242-256` (in `_model_fn`) builds
  inference prompts as **plain string concatenation** —
  `"Question: ...\n\nAnswer:"`. The tokenizer's chat template is
  never applied.

This is a classic train/eval format mismatch. The Instruct model is
trained to expect the chat template; raw-string prompts degrade its
performance measurably. **This likely accounts for why the bare
Instruct baseline scored 48.2% on the harness instead of the
published ~80% band.**

More importantly: part of what adapter v10 appears to have "learned"
over 9 trials of PEFT may actually be **how to decode raw-string
prompts** rather than how to do math better. The +17pt lift vs bare
is real against the mismatched baseline but may compress
substantially — or evaporate entirely — against a chat-template-
formatted baseline.

### 2. Dataset identity confirmed

- `backend/harnesses/data/math_eval_200_holdout.jsonl` contains 200
  items with `sample_id` = `gsm8k_holdout_0000..0199` and
  `domain = "grade_school_math_word_problems"`.
- This is a 200-item subset of **GSM8K** (Cobbe et al. 2021,
  https://arxiv.org/abs/2110.14168). It's not TB-authored test data;
  it's a public benchmark subset.
- **Published numbers therefore exist** and must be cited in any
  public comparison.

### 3. Grader is reasonable

- `_extract_predicted_answer` in `math_qa_v1.py` is CoT-aware:
  priority 1 = `#### N` marker, priority 2 = `Final Answer: N` /
  `Answer: N`, priority 3 = last standalone number, fallback = raw
  output.
- `_normalize_answer` strips whitespace, trailing punctuation, `$`,
  `%`, `,` before exact string match on normalized numeric.
- Not the source of the baseline gap. Mentioned here for
  completeness.

## Published reference points (to verify + cite)

These must be verified from primary sources during Phase 3 before
appearing in any public material.

- **Llama 3.1 8B base** on GSM8K: Meta's Llama 3.1 model card
  reports ~50-55% in the 8-shot CoT setting. Citation: Meta Llama 3.1
  model card (https://github.com/meta-llama/llama-models).
- **Llama 3.1 8B Instruct** on GSM8K: Meta's model card reports ~80%+
  in the 0-shot CoT setting. Same citation.
- **GSM8K benchmark itself**: Cobbe et al. 2021, "Training Verifiers
  to Solve Math Word Problems," https://arxiv.org/abs/2110.14168.
- **PEFT on GSM8K**: multiple papers report fine-tuned 7-13B models
  in the 60-75% band — my memory ("approaching the published band")
  called this out but didn't ship a citation. Phase 3 must identify
  2-3 actually-cite-able papers.
- **Comparison scope**: if the pitch references ChatGPT / Claude /
  Gemini performance on GSM8K, those are also published and should
  be cited rather than re-measured. Phase 4 may still re-run them
  through the TB harness for apples-to-apples with the fixed
  methodology.

## Scope

### Phase 1 — Harness fix (code)

- [ ] R1: In `harness_runner._build_experiment_stack._model_fn`,
      detect whether the base model is instruction-tuned. Heuristic:
      the HF tokenizer exposes a non-empty `chat_template` attribute
      AND/OR the model name contains "Instruct" / "chat" / "it".
      Operator may want a config flag to force one mode or the other;
      design it in.
- [ ] R2: When chat-template mode is active, format the inference
      prompt via
      `tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)`.
      Build `messages` from:
      - `system`: the pinned system prompt text (if any) with context
        appended inline
      - `user`: the question
- [ ] R3: Preserve the raw-string path (R2's `else` branch) for base
      (non-Instruct) model backbones. Document which path a run used
      in the experiment's results payload for post-hoc auditing.
- [ ] R4: Expose the chosen mode in the harness runner logs AND in
      the experiment's `_stack` summary so comparison modals surface
      "chat-template" vs. "raw-string" prompting.
- [ ] R5: Consider: should `training/math/train.py` and the harness
      share a single "format for this model" helper? Light
      refactor; reduces future drift.

### Phase 2 — Re-baseline math-example (research)

Pre-registered: bins are 1× / 2× pooled SD of the Trial #7 noise
envelope (±6pt). Multi-seed discipline from TB-US-081: 4 holdout
draws per adapter minimum.

- [ ] R6: Fire 4 holdout experiments with **bare Instruct + fixed
      harness (chat template)**. Record as new experiments against the
      math-example agent with explicit "harness_v2" tag so they
      don't co-mingle with the closed arc's numbers.
- [ ] R7: Fire 4 holdout experiments with **adapter v10 + fixed
      harness**.
- [ ] R8: Fire 4 holdout experiments with **adapter v9 + fixed
      harness**.
- [ ] R9: Produce a before/after table:

      | | Mismatched-harness mean | Fixed-harness mean | Delta |
      |---|---|---|---|
      | Bare Instruct | 48.2% | TBD | TBD |
      | Adapter v9 | 53.75% | TBD | TBD |
      | Adapter v10 | 60.12% | TBD | TBD |

- [ ] R10: Compute the apparent-lift-vs-real-lift decomposition. If
      the fixed-harness bare Instruct scores ~75%+, the adapter's
      gain was mostly format-compensation. If it scores ~60%, the
      adapter also did some actual math learning.

### Phase 3 — Published-benchmark citations

- [ ] R11: Verify Meta Llama 3.1 model-card numbers for 8B base + 8B
      Instruct on GSM8K. Capture exact figures + context (shot count,
      prompt format) with URL.
- [ ] R12: Cite GSM8K paper (Cobbe et al. 2021).
- [ ] R13: Identify 2-3 citable PEFT papers reporting GSM8K results
      for ~7-13B models. Record their methodology (adapter rank,
      dataset size, grader details) alongside their numbers.
- [ ] R14: Add a `docs/math-example/published-benchmarks.md` collecting
      the verified citations + exact-quoted numbers.

### Phase 4 — Head-to-head vs. closed-source LLMs (optional for first cut)

Operator may decide this is Phase 4 or a follow-up story depending
on API budget. Each run against a closed-source LLM costs money.

- [ ] R15: Run the 200-item GSM8K holdout through:
      - OpenAI (ChatGPT via API) with native messages format
      - Anthropic (Claude via API) with native messages format
      - [Optional] Gemini / Grok if operator wants fuller coverage
- [ ] R16: Use the TB harness's existing grader (R3's "chosen mode"
      logging required) so the comparison is apples-to-apples. Note:
      TB's harness runs locally; external-LLM comparisons will need
      a lightweight `backend/harnesses/math_qa_external.py` wrapper
      that calls the API and formats output for the grader.
- [ ] R17: Report numbers with explicit caveats: "This TB harness,
      this subset of GSM8K, this grader; ChatGPT/Claude were not
      prompt-engineered beyond native chat format."

### Phase 5 — Narrative update

- [ ] R18: Update `docs/math-example/sweet-spot-search-log.md` with
      a new "Trial #10: harness fairness fix" entry. Use neutral
      research language per
      `feedback_research_not_ready_to_publish.md`.
- [ ] R19: Update `docs/math-example/methodology.md` to describe the
      harness fairness fix + chat-template requirement.
- [ ] R20: Update `docs/pages/staged-progression.md` with corrected
      numbers + a transparent note that earlier published figures
      from the math-example arc used a mismatched harness. Include a
      short "lessons learned" section about why we caught this.
- [ ] R21: If adapter gain compresses significantly: the math-example
      narrative needs an honest reframe from "look how PEFT improved
      performance" to "look how prompt-format mismatch suppressed
      baseline, and how we caught + corrected it." The first framing
      overclaims; the second is defensible and may be more valuable
      pedagogically.

### Not in scope

- A new training run of adapter v11 on a chat-template-aligned
  pipeline. The point of this story is measurement fairness; new
  training would be TB-US-093+.
- Fixing training-side details (rank, LoRA target modules, hyper-
  params). The arc closed; this story doesn't reopen those questions.
- Non-math domains. Sticks to math-example + GSM8K.
- Stalite catch-up or EEL work. Those are their own threads.

## Pre-registered hypotheses

### H92a — Harness fix lifts the bare Instruct baseline substantially

**Claim**: switching from raw-string to chat-template prompting will
lift bare Instruct's holdout accuracy by at least **10pt** (from
48.2% to ≥58%). Signal: R6's 4-seed mean after the fix lands.

**Why pre-register**: without the lift we lose the explanation for
why bare was so low. If the lift is <5pt, something ELSE is wrong
with the harness (not just prompt format).

### H92b — Most of adapter v10's apparent gain was format-compensation

**Claim**: fixed-harness bare Instruct will land within **5pt** of
adapter v10's current 60.12% number. Signal: R6 vs. R7 means.

**Alternative outcome**: adapter v10 still beats fixed-harness bare
by >10pt. This would argue the adapter did real math-reasoning work
beyond format decoding, and the arc's conclusions survive the
re-baseline.

### H92c — The PEFT story is pedagogically stronger with honest numbers

**Claim**: whichever direction R10 goes, the write-up is more
defensible after this story than it was before. Not a numeric claim
but a framing one.

## Acceptance Criteria

- [ ] AC1: Harness runner applies the chat template on Instruct
      base models by default; can be forced to raw-string mode via
      explicit config flag.
- [ ] AC2: Every experiment's `_stack` summary and the compare modal
      show which prompting mode was used (chat-template vs. raw-string).
- [ ] AC3: 12 new experiments total (4 each for bare Instruct, v9,
      v10) landed with fixed-harness mode; multi-seed statistics
      computed (mean, SD, pooled SD).
- [ ] AC4: Before/after decomposition table published in
      `docs/math-example/rank-sweep-results.md` or a new
      `harness-fairness.md`.
- [ ] AC5: `docs/math-example/published-benchmarks.md` exists with
      verified citations + exact numbers for Llama 3.1 8B base,
      Instruct, and 2-3 PEFT-on-GSM8K reference points.
- [ ] AC6: `sweet-spot-search-log.md` has a Trial #10 entry using
      neutral research language.
- [ ] AC7: `methodology.md` documents the chat-template requirement.
- [ ] AC8: If Phase 4 fires, `docs/math-example/external-llm-comparison.md`
      carries the external-LLM numbers with methodology notes.
- [ ] AC9: `staged-progression.md` carries corrected numbers +
      transparent "earlier figures used mismatched harness" caveat.

## Design Notes

- **Why re-open a closed arc**: arc closure was premised on
  "math-example has served its PEFT demonstration role." That
  premise turns out to have been based on numbers suppressed by a
  harness bug. Re-opening to measure fairly is not scope creep — it's
  due diligence before the math-example arc becomes public material.
- **Why no new training**: the training-side already uses the chat
  template correctly. The bug is inference-side only. A new training
  run isn't needed to validate the fix.
- **Why neutral research language**: per
  `feedback_research_not_ready_to_publish.md`. If R21's outcome
  is "the adapter's gain was mostly format-compensation," that's a
  finding to report honestly, not a failure to spin.
- **Why multi-seed again**: the arc established that single-run
  GSM8K-200 measurements have a ~6pt noise envelope
  (`feedback_research_infrastructure_resilience.md` + Trial #7 memo).
  Any new comparison must be multi-seed to be interpretable.
- **Phase 4 is optional because it costs money**: external LLM API
  calls (ChatGPT, Claude) are per-token. 200 GSM8K questions × some
  token budget × 4 seeds = real dollars. Operator decides when.
- **Relationship to TB-US-091's backfill**: TB-US-091's backfill
  was first-wins. If this story re-measures, operator may want to
  update the comparison-modal source_experiment_id to point at the
  new (fixed-harness) experiment rather than the old (mismatched-
  harness) one. Decision for close-out.

## Related

- [`math_qa_v1.py`](../../backend/harnesses/math_qa_v1.py) — the harness
- [`harness_runner.py`](../../backend/api/harness_runner.py) — the inference path with the bug
- [`training/math/train.py`](../../training/math/train.py) — the training path (correct)
- [TB-US-057](tb-us-057.md) — the math-example arc kickoff
- [TB-US-076](tb-us-076.md) — CoT-aware answer extraction (grader fixes)
- [TB-US-081](tb-us-081.md) — multi-seed discipline + noise envelope
- [TB-US-085](tb-us-085.md) — Trial #9 (closing trial, mismatched-harness numbers)
- [TB-US-091](tb-us-091.md) — accuracy backfill (first-wins semantics)
- GSM8K paper: Cobbe et al. 2021, https://arxiv.org/abs/2110.14168
- Memory files: `feedback_research_not_ready_to_publish.md`,
  `feedback_research_docs_first_class.md`,
  `project_tb_us_068_phase_c_resume.md` (will need update if R10
  changes the arc's closing framing)
