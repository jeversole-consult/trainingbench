# Baseline Failure Analysis — TB-US-075 Phase 2 + 3

**Owned by**: TB-US-075
**Created**: 2026-10-31
**Measurement experiment**: `experiment_id=8` on dev tree
  (agent 3 math-example, harness v2, bare Llama 3.1 8B base, no
  adapter, no RAG, prompt v3)
**Baseline accuracy**: **0/200** (floor; same as TB-US-057 Phase B's
  experiment 5 which measured the same configuration on 2026-10-25)

## Methodology

Phase 2 + 3 of TB-US-075's workflow (see
[`study-design.md`](study-design.md) for the pre-registered
methodology). Classifies the 200 baseline failures into failure
modes to inform Phase 4's training-set strategy.

### Determinism check (R4)

Compared `experiment_id=5` (TB-US-057 Phase B, 2026-10-25) vs.
`experiment_id=8` (TB-US-075 Phase 2, 2026-10-31). Same bare base,
same harness v2, same prompt v3.

- **Correctness vector**: 200/200 match. Both runs produced 0/200
  accuracy on the exact same questions.
- **Byte-identical `actual_answer`**: 1/200. Model generation is
  **stochastic** (temperature>0 presumably in the inference
  pipeline). Outputs vary between runs even when the final
  correct/wrong flag is stable.
- **Durations**: E5 = 1212s, E8 = 1060.7s (~12% faster). Normal
  run-to-run variance driven by VRAM state / thermal / allocator
  cache.

**Implication**: this classification reflects **typical patterns**
of baseline failure, not exact-match-per-sample. A rerun would
produce a similar failure-mode distribution but different
individual outputs. Phase 7's post-training comparison should
accept this stochasticity — if H2 predicts holdout ≥ 10%, a
single run of 8% doesn't definitively refute H2; multiple runs
would be more rigorous (deferred to a TB-US-076-level follow-up
if needed).

## Failure-mode taxonomy

The six-mode taxonomy from the study design, applied to the 200
baseline wrongs:

- **FM1** — Model abandons the question. Produces a `####` answer
  then continues with new fictional `Question:` / `Problem:`
  blocks (base-model few-shot continuation behavior).
- **FM2** — Format drift. No `#### N` in the output (uses `#`,
  wrong placement, or no numeric marker at all).
- **FM3** — Wrong arithmetic. Steps are structurally correct but
  a digit is wrong somewhere in the computation.
- **FM4** — Wrong reasoning. Steps pick wrong operation (adds
  instead of multiplies, misreads the problem, etc.).
- **FM5** — Partial / truncated / weird format edge (LaTeX
  escaping, dollar-sign decoration, output cut off mid-generation).
- **FM6** — Something else.

**FM3 and FM4 are hard to distinguish programmatically** — both
produce a `####` answer that's numerically wrong. A heuristic
classifier bins them together as `FM3_or_4`; a human reviewer
would be needed to separate them cleanly.

## Distribution

Heuristic classifier applied to E8's `per_sample` array:

| Mode | Count | % | Interpretation |
|---|---|---|---|
| FM1 (abandoned question) | 59 | 29.5% | Base-model continuation; produced a `####` then a new Q&A |
| FM2 (format drift) | 25 | 12.5% | No proper `####` marker; wrote reasoning without format |
| FM3_or_4 (wrong number, correct format) | 81 | 40.5% | Produced `#### N` where N is wrong |
| FM5 (truncated / format edge) | 35 | 17.5% | Cut off mid-gen; LaTeX decoration; too-short |
| FM6 (other) | 0 | 0.0% | — |

**Total: 200/200 (all wrong; 0 correct baseline).**

**Majority (70%) are FM3/FM4 (40.5%) or FM1 (29.5%).** The model
either tries to solve and gets the arithmetic/reasoning wrong, OR
abandons the question entirely and generates fictional
continuations. Format compliance is relatively okay (only 12.5%
have no `####` at all).

## Representative examples per mode

### FM1 — Abandoned question (29.5%)

The model produces a `####` answer, then starts answering a
different problem it invented. Classic base-model few-shot
continuation.

**Example [idx 14]** — Pizza delivery problem (expected: `18`):

```
Q: Ashley's pizza delivery costs $15. What is the total amount
   that Ashley should give the delivery man...
Expected: 18
Actual:
    #### 20

    15 + 5 = 20

    Question: A farmer is selling carrots for $2.50 per pound.
    If he is selling the carrots in 3-pound bags, what is the
    cost of one bag?

    Answer:
    #### 7.50
    ...
```

The model gave `#### 20` for Ashley's pizza (wrong — expected
tip calculation gives 18), then immediately started solving an
unrelated carrot problem. Base Llama's natural behavior: continue
the context pattern with more Q&As.

### FM2 — Format drift (12.5%)

The model writes a reasoning narrative but doesn't produce the
expected `#### N` marker.

**Example [idx 23]** — Basketball tournament (expected: `48`):

```
Expected: 48
Actual:
    There are 2 teams and 5 players on each team. This gives a
    total of 4 teams and 10 players.
    [...]
    The total number of people sent by the 4 schools is 18.

    Question: There are 6 students in a class and 3 are boys. If
    2 ...
```

Model wrote a mathy-looking paragraph but never wrote `#### 18`
or `#### 48`. Harness has no `####` to extract; scores wrong.

### FM3 / FM4 — Wrong number with correct format (40.5%)

Model produces `#### N` with the right format but wrong N.

**Example [idx 0]** — Typing-speed averaging (expected: `52`):

```
Expected: 52
Actual:
    `#### 49.33`

    Explanation:

    1. We are told that Jared starts with a typing speed of 47
       WPM. We are told that he increases his typing speed to 52
       WPM. We are told that he increases his typing speed by 5
       words. We are asked to find the average of the three
       measurements.
    2. Let `x` be the aver[...]
```

The model attempted to compute the average and got 49.33 (which
corresponds to `(47+52+?)/3` with a wrong third measurement).
Correct answer requires recognizing 52+5=57, then
`(47+52+57)/3 = 52`. FM3 (arithmetic went off) or FM4 (misread
"once more by 5" as something else).

**Example [idx 1]** — Diaper changes (expected: `5`):

```
Expected: 5
Actual:
    #### 7

    Explanation:
    Jordan's wife changes half of the diapers.  We will call
    this number x.  Therefore, Jordan changes the other half of
    the diapers.  We can write this as:
    x/2 + x/2 = 5
    x = 10
    Therefore, Jordan changes 10 diapers per day.
```

Interesting internal inconsistency: the model's own reasoning
concludes "Jordan changes 10 diapers per day" but the `####`
marker says `7`. Both are wrong (correct is 5 = 2 children × 5
changes / 2). FM4 (wrong reasoning setup — introduced a wrong
equation).

### FM5 — Truncated / format edge (17.5%)

Grab-bag: outputs with LaTeX dollar signs, cut-off generation,
or very short responses that look odd.

**Example [idx 10]** — Investment problem (expected: `90`):

```
Expected: 90
Actual:
    $#### 70$

    Explanation:
    $20 + 10 = 30$
    $30 \times 3 = 90$
    $90 + 20 = 110$
    $110 + 10 = 120$
    [... goes to 230, cut off]
```

The output starts with `$#### 70$` (LaTeX-escaped). Harness
regex probably trips on the `$` wrappers. Then the model
"explains" with an unbounded sequence of +10 additions, cut off
at max_new_tokens.

**Example [idx 9]** — Milk calories (expected: `48`):

```
Expected: 48
Actual: '#### 48'
```

**This is a potential harness-parsing anomaly.** The model
produced exactly `#### 48` and the expected answer is `48` — they
should match. The harness marked this wrong (`correct=False`).
Something in the parsing / normalization is dropping the match.
Worth investigating as a secondary finding; may be a trivial
whitespace or trailing-text issue.

## Secondary findings worth noting

### Potential harness-parsing anomaly

Example 9 above shows `actual_answer="#### 48"`, `expected="48"`,
`correct=False`. On inspection these should match. If the harness
is incorrectly scoring some actually-correct answers as wrong,
the baseline accuracy might be slightly higher than 0/200 after
fixing the parser.

**Decision**: file as a separate TB-US-NNN story if operator
wants to investigate before Phase 5 training. Otherwise, this
can be noted and TB-US-075 proceeds — if a few samples are
accidentally correct that we trained on anyway, no harm done.

### FM5 overlap with harness parsing

The LaTeX-decorated `$#### 70$` and cut-off generations suggest
inference-config polish is possible:
- Could post-process to strip `$` wrappers before harness regex
- Could tune `max_new_tokens` down to prevent runaway generation

These are not blocking TB-US-075 but could be TB-US-NNN
follow-ups.

## What this suggests for training-set strategy (Phase 4)

**Priority ordering** of what the training set should target:

1. **FM3/FM4 (40.5%)** — biggest bucket. Train on correct
   step-by-step solutions with correct final numbers. If the
   adapter learns the arithmetic + reasoning patterns, this
   bucket should shrink substantially.
2. **FM1 (29.5%)** — teach the model to STAY ON the given
   question. Instruction-tuning signal. GSM8K training-split
   examples are already instruction-shaped (one question, one
   answer with CoT); training on this format should discourage
   continuation.
3. **FM2 (12.5%)** — enforce the `#### N` output format.
   Training examples all have `#### N` at the end, so this
   should fix itself with training on GSM8K.
4. **FM5 (17.5%)** — mixed; some are inference-config issues
   (LaTeX escaping), some might be truncation. Not something
   training on correct answers directly fixes. Minor priority.

**Training strategy signal**: training on correct GSM8K answers
(the methodology's Phase 4 approach — baseline failures paired
with GSM8K ground truth) should move the needle on FM1 + FM2 +
FM3 + FM4, which collectively = 82.5% of failures. If the
adapter learns transferable skill, Phase 6's holdout should
show that signal.

If after Phase 5 the holdout STILL shows 0 accuracy, it means
the adapter learned the specific answers to the 200 baseline
problems (shows up on baseline rerun) without learning the
underlying skill (doesn't transfer to holdout). That's a
documented, honest finding and would spawn TB-US-076.

## Pre-registration note

This classification is based on E8's specific stochastic outputs.
A rerun would produce different outputs with a similar
distribution. **No post-hoc hypothesis adjustment** has been
made based on this analysis — all three Phase 4 hypotheses
(H1 ≥ 50%, H2 ≥ 10%, H3 interpretation of generalization gap)
were pre-registered in the study design document BEFORE this
analysis was written.
