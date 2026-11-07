# TB-US-093: Reframe the math-example demo (conditional on TB-US-092 H92b)

**Status**: Completed 2026-11-07
**Shipped**: 2026-11-07
**Created**: 2026-11-07
**Confirmed by**: TB-US-092 Phase 2 cohort #64-#75 (4 seeds × 3
conditions = 12 experiments, 0 failures) — bare Instruct 84.1%
(SD 1.4pt), adapter v9 74.4% (SD 3.2pt, −9.75pt at 3.96× pooled
SD), adapter v10 73.6% (SD 3.0pt, −10.5pt at 4.55× pooled SD).
v10 vs v9: 0.24× pooled SD (indistinguishable). Both adapters
strongly hurt the model's GSM8K performance on fair measurement.
**Author**: Jesse Eversole
**Depends on**: TB-US-092 Phase 2 (re-baseline experiments) + Phase 3
(citations). Must NOT fire before both are complete.
**Blocks**: any public-facing math-example material (TB-US-005
public v0.1 cut, Pages site updates, pitch collateral).
**Commit hash(es)**: <filled in on completion>

## Story

As a TB operator who built a math-example pedagogical demo around a
"+17pt lift from PEFT on GSM8K" narrative, I want to **honestly
reframe the demo after TB-US-092 revealed the measurement was
format-decoding compensation rather than math capability gain** — so
that no public artifact overclaims and the pedagogical value of the
arc stands up to scrutiny.

The reframe may actually produce a **stronger** pedagogical story:
"we fine-tuned, saw +17pt vs bare, discovered our measurement was
unfair (train/eval format mismatch), re-measured honestly, found
the adapter was hurting performance, and changed what we tell
people" is a more defensible research-methodology story than the
original "+17pt" claim.

**Framing (operator direction, 2026-11-07)**: the demo is a
**disciplined negative result against the flagship labs' home
turf, run on a single GPU**. Specifically:

- GSM8K is a well-known public benchmark. Meta, OpenAI, Anthropic,
  and others have trained their flagship models against it
  (directly or through curated math corpora derived from it).
  Llama 3.1 8B Instruct's ~84% score is the result of a
  large-compute, large-data, carefully-tuned pipeline we did not
  replicate.
- We ran disciplined PEFT (QLoRA, rank 16-32, attn+MLP, 1-5K
  training samples) on a single RTX 3090 — effectively competing
  on the flagship labs' home turf with ~0.001% of their compute
  budget.
- **We did not move the needle, and in fact degraded by ~10pt.**
  On a benchmark the flagship labs have already heavily optimized
  for, starting from a model that already carries that
  optimization, modest PEFT buys nothing.
- The methodology lesson — train/eval format mismatch produces
  apparent gain that isn't real — generalizes beyond this demo
  and is the first thing every PEFT practitioner should check.

**The message to TB users is NOT "PEFT doesn't work."** It is:

- **"PEFT earns its keep where flagship models haven't already
  optimized."** That's proprietary domain data, internal knowledge
  bases, customer-service corpora, novel-task domains — things no
  Meta/OpenAI/Anthropic team ever trained against. Not public
  benchmarks already thoroughly saturated by frontier training.
- **"When you run PEFT, measure with discipline."** Format
  alignment, multi-seed, documented grader, published-benchmark
  comparison when available. Otherwise you convince yourself of
  gains that aren't there.

## Scope

### 1. Unpromote adapter v10 (component lifecycle)

- [x] R1: Via UI (TB-US-087 version-lifecycle buttons) or API, call
      `POST /adapter-versions/10/deprecate` on the math-example
      agent's adapter v10. State transitions from `promoted` to
      `deprecated`. The agent then has NO promoted adapter until
      operator pins one (if any).
- [x] R2: Record the decision in an audit entry (automatic via
      `_audit_versioned_action` on the endpoint).
- [x] R3: Decide whether adapter v9 gets re-promoted or the agent
      stays adapter-less. **Current evidence**: fixed-harness bare
      Instruct ≈ 85% is already in the published band;
      re-promoting any of our adapters would need its own evidence
      that it beats bare on the fixed harness. Default: leave the
      agent adapter-less, let bare Instruct carry the demo.

### 2. Reframe public-facing docs

- [x] R4: `docs/pages/staged-progression.md` — rewrite Trial-by-trial
      narrative to match fixed-harness numbers. The core table
      becomes:

      | Setup | GSM8K-200 holdout (fixed harness, chat template) |
      |---|---|
      | Llama 3.1 8B Instruct + chat template | ~TBD% (from TB-US-092 R6) |
      | + adapter v10 (prior demo) | ~TBD% (from TB-US-092 R7) |
      | + adapter v9 | ~TBD% (from TB-US-092 R8) |

      Framing: "earlier figures used a harness that did not apply
      the chat template on Instruct variants; those figures
      suppressed the baseline. The fixed-harness measurement is the
      new source of truth." Cite Meta's Llama 3.1 model card number
      alongside.

- [x] R5: The arc's 9-trial narrative stays — but gets a new
      concluding section: "Trial #10: the measurement correction."
      Walks a reader through how the mismatch was discovered (first
      noticed via an unexpectedly low baseline vs. published, then
      verified in the harness code), what it tells us about PEFT
      more generally (format-decoding compensation is a real risk
      on under-specified harnesses), and what it means for TB's
      claim about this demo (we don't claim improvement; we claim
      a well-measured null result with a useful methodology lesson).

- [x] R6: Update `docs/math-example/sweet-spot-search-log.md`:
      - Add Trial #10 entry per TB-US-092 R18
      - Mark Trials #4-#9 conclusions with "see Trial #10 — these
        numbers used the mismatched harness" footnotes
      - DO NOT delete or edit the original trial narratives.
        Everything is history.

- [x] R7: Update `docs/math-example/methodology.md` with the
      chat-template requirement from TB-US-092 R19 (may already be
      done by that story — coordinate with its R19 at fire time).

- [x] R8: Update the math-example card in the welcome banner
      (`static/script.js:1137+`) — the "📊 See the staged
      progression" card. Current copy references "Stage 0 → 1 → 2
      accuracy deltas." Revise to reflect the honest finding.

- [x] R9: Public README / repo description if the math-example lift
      is referenced there. Audit via grep.

### 3. Update the compare modal's source-experiment links

- [x] R10: TB-US-091 backfill wrote first-wins source_experiment_id
      on training runs #15 and #16 (adapter v9 and v10), pointing
      at pre-fix experiments. Operator should decide: do the
      compare-modal rows also link the fixed-harness experiments
      (#45+ and #49+), or stay pointing at the originals for
      historical traceability? Default: **leave as-is**, with a
      new note in the compare modal explaining that the linked
      experiments used the mismatched harness.

### 4. Pedagogical artifacts

- [x] R11: Draft a new section in `docs/pages/staged-progression.md`
      titled something like "What this arc actually teaches."
      Topics:
      - Train/eval format mismatch is a common PEFT failure mode
      - Format-decoding compensation shows up as apparent
        capability gain
      - Multi-seed discipline (TB-US-081) didn't catch this —
        single-seed measurement would have been just as wrong
      - **The adapter made the model worse on fair measurement.**
        Not because fine-tuning is bad — because we were competing
        on the flagship labs' home turf, on a benchmark their
        models had already been trained against, with ~0.001% of
        their compute. There was no headroom to gain.
      - How TB-US-092's audit was triggered (compare modal exposed
        suspicious numbers → asked "why so high" → found bug)

- [x] R11a: Add a dedicated **"When PEFT DOES earn its keep"**
      subsection (new since operator framing 2026-11-07). The
      message TB wants to send to users: don't repeat our mistake
      of benchmarking against a public dataset flagship LLMs have
      already crushed. Apply PEFT to:
      - **Proprietary domain data** flagship labs never saw
        (customer-service corpora, legal documents, internal
        knowledge bases, specialized scientific domains)
      - **Novel task framings** that haven't been optimized at
        pretraining scale
      - **Weaker base models** that have real capability headroom
        the adapter can fill
      - **Much larger training sets** (10K-100K+, not 1-5K) when
        competing on well-studied benchmarks
      This is the actionable take-away for TB users considering
      PEFT: use TB to improve on things the big labs haven't
      already optimized. The math-example arc shows what NOT to
      do, and points at what to do instead.

- [x] R12: Draft a short write-up suitable for the TB public site
      at `docs/pages/methodology-lesson.md` — "A PEFT cautionary
      tale from the TB math-example." Lead with the
      disciplined-negative-result-on-flagship-home-turf framing;
      close with the "where PEFT DOES earn its keep" signpost.
      Probably 2-3 pages. This becomes a drawable artifact — a
      shareable research vignette that is more valuable as a
      pedagogical piece than the original +17pt claim would have
      been.

### 5. Close the research arc (really this time)

- [x] R13: Update `project_tb_us_068_phase_c_resume.md` project
      memory — final numbers, closed, honest closing framing.
- [x] R14: BACKLOG.md — mark TB-US-005 (public v0.1 cut) as still
      Proposed. The math-example arc is now ready for public
      exposure under the reframe; TB-US-005 can pull the trigger.

### Not in scope

- A new training run of adapter v11 trying to beat fixed-harness
  bare Instruct. That's a separate research story if the operator
  wants to chase it. Possible but likely large — would need
  fundamentally different approach (e.g., much more training data,
  different base, RL from AI feedback, etc.) since bare Instruct is
  already ≈ published-leaderboard performance on GSM8K.
- Deleting any trial history. All narrative stays as record.
- Changing stalite-side plans. This is math-example scope only.
- Legal / brand-risk review of the reframe. If the arc has already
  been shared externally (e.g., operator mentioned a post), the
  reframe strategy should include a public correction, but that's
  operator's call and separate from this story's code+docs work.

## Pre-registered hypotheses

### H93a — Reframed narrative is defensible

**Claim**: after this story ships, the math-example demo reads as
a methodology lesson rather than a performance claim, and no
public artifact overclaims. **Signal**: operator reads the
updated docs and agrees. No numeric claim.

### H93b — The reframe is pedagogically richer

**Claim**: the story "we discovered our measurement was unfair and
corrected" is more valuable to TB's external audiences (ML
researchers, educators) than the original "+17pt" story would have
been. **Signal**: subjective, but testable via asking an external
reader. May prove false.

## Acceptance Criteria

- [x] AC1: Adapter v10 is deprecated (component state =
      `deprecated`) on the math-example agent.
- [x] AC2: `docs/pages/staged-progression.md` reflects fixed-harness
      numbers everywhere.
- [x] AC3: `sweet-spot-search-log.md` has Trial #10 entry + "see
      Trial #10" footnotes on Trials #4-#9.
- [x] AC4: Welcome-banner math-example card copy matches the new
      framing.
- [x] AC5: No file in the repo references "+17pt" or "60.12%" as
      a current-demo number (both become historical — the arc
      narrative keeps them, but current-state language stops using
      them). grep check.
- [x] AC6: `project_tb_us_068_phase_c_resume.md` project memory is
      updated with final numbers + closed status.
- [x] AC7: BACKLOG.md reflects the arc's reframed closure.
- [x] AC8: (Conditional on R12) If the methodology-lesson doc was
      drafted, it's cross-referenced from the staged-progression
      page and linked in the welcome banner.

## Design Notes

- **Why pre-stage this draft instead of wait**: the operator
  stepped out during TB-US-092's 6-hour re-baseline batch. When
  they come back, they'll either (a) see the hypothesis confirmed
  and want to move quickly on reframing, or (b) see the hypothesis
  disconfirmed and this story becomes a no-op they can discard.
  Drafting at pre-stage time costs 20 minutes; drafting
  post-completion while the operator is reading the results costs
  their attention at the worst moment.
- **Why not delete the arc narrative**: the trials happened. The
  mechanisms we described were real (format rigidity, capacity
  trap, multi-seed noise envelope) — only the "adapter beats bare"
  claim is withdrawn. The narrative, with its honest correction,
  is the point.
- **Why adapter-less math-example as the default**: bare Llama 3.1
  8B Instruct ≈ 85% on GSM8K-200 (per TB-US-092 #40) is already
  within the published band. Shipping an adapter that performs
  worse on fair measurement is harder to defend than simply
  shipping the base. The demo becomes "here's how to use TB with
  a bare Instruct model" — which is actually the first thing a
  new operator needs to learn anyway.
- **Why the reframe may be stronger pedagogy**: "we were wrong,
  caught it, corrected, and tell you how" is a research-maturity
  story. The original +17pt story was one more PEFT demo in a
  crowded field. The reframed story is memorable *because* it
  surfaces a failure mode that other PEFT demos quietly avoid
  disclosing.
- **Why the "flagship home turf" framing matters** (operator
  2026-11-07): the reframe isn't just "we were wrong." It's "we
  competed on the hardest possible turf — a public benchmark the
  flagship labs have already optimized for, starting from one of
  their best Instruct models, on a single consumer GPU — and
  honestly reported that we didn't win." That framing:
  - Names the structural disadvantage so the negative result
    isn't mistaken for "PEFT is broken"
  - Points users toward the condition where PEFT DOES work (their
    own data, their own domain, their own unexplored corners)
  - Lets TB occupy a defensible pedagogical niche: the
    open-source workbench that teaches you what the flagship labs
    don't openly disclose about PEFT limits
- **Finalized numbers for R4/R20** (from TB-US-092 Phase 2
  cohort #64-#75, completed 2026-11-07 11:51 UTC):

      | Setup | GSM8K-200 holdout (fixed harness) |
      |---|---|
      | Llama 3.1 8B Instruct (bare) | 84.1% mean (SD 1.4pt, 4 draws) |
      | + adapter v9 (rank 16 attn+MLP QLoRA) | 74.4% mean (SD 3.2pt) → −9.75pt (3.96× pooled SD) |
      | + adapter v10 (rank 32 attn+MLP QLoRA) | 73.6% mean (SD 3.0pt) → −10.5pt (4.55× pooled SD) |
      | v10 vs v9 | 0.24× pooled SD (indistinguishable noise) |

  Both adapters strongly regress; v9 vs v10 difference is
  indistinguishable. The "rank 32 sweep" of Trial #9 was noise.

## Related

- [TB-US-092](tb-us-092.md) — the harness fairness fix + re-baseline
  that motivates this story
- [TB-US-087](tb-us-087.md) — version-lifecycle UI (R1 will use
  this)
- [TB-US-091](tb-us-091.md) — accuracy backfill (R10 interacts
  with this)
- [TB-US-089](tb-us-089.md) — math-example retrospective (Backlog;
  this story's content probably supersedes most of TB-US-089's
  scope — consolidate or sequence)
- [TB-US-005](tb-us-005.md) — public v0.1 cut (unblocked after this
  story if the operator decides public release is still the right
  move given the reframe)
- Memory: `feedback_research_not_ready_to_publish.md`,
  `project_tb_us_068_phase_c_resume.md`
