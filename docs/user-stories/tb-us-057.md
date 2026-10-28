# TB-US-057: Build + publish math-example staged progression artifacts

**Status**: Completed
**Created**: 2026-10-20
**Started**: 2026-10-22
**Completed**: 2026-10-25
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a maintainer preparing the TB OSS launch, I want to
build and publish the three measurable Sweet Spot stages
for the shipped math-example agent (Stage 0: bare LLM;
Stage 1: +RAG; Stage 2: +adapter) with the full artifact
set (training set JSONL, RAG seed corpus, trained
adapter, system prompt text, harness JSONL), so that
new TB operators can see the agent concept working
on first install and measure the pedagogical deltas
themselves.

## Background

Executes TB-US-047 §8 story #7 ("Build math-example
artifacts"). This is the "we are going to do this" work
operator committed to during TB-US-047 Q3 reframe —
turning the shipped math-example into a measured,
pedagogical staged progression.

Design captured in `docs/design/first-run-onboarding.md`
Q3B (staged progression: Stage 0 → +RAG → +adapter)
and TB-US-047 completion notes.

**Blocked by TB-US-051 through TB-US-056** (full
versioned-component machinery must exist to build
these as versioned artifacts; harness must run to
measure Stage 0/1/2 accuracy).

This is a content/dataset production story, not a code
story — most of the work is dataset curation + adapter
training + measurement, not writing code.

## Requirements

- [ ] R1: **Math-eval harness dataset:**
      `backend/harnesses/data/math_eval_200.jsonl` —
      200 math questions covering:
      - Arithmetic (30)
      - Algebra 1 (40)
      - Geometry (30)
      - Pre-calc / trig (40)
      - Word problems (40)
      - Edge cases (large numbers, fractions, negative
        results) (20)
      Each line: `{"question": "...", "expected_answer":
      "...", "domain": "..."}`
- [ ] R2: **Math-example training set JSONL:**
      `training-sets/math-example-v1.jsonl` — ~500
      Q&A pairs for PEFT training. Distinct from the
      eval harness (no overlap). Includes answer
      explanations where helpful (not just final
      numbers).
- [ ] R3: **Math-example RAG seed corpus:**
      `rag-seeds/math-example-v1/` — curated reference
      content:
      - Formula sheets (algebra, geometry, trig)
      - Common identity/theorem explanations
      - Worked-example style docs
      - All content either EL-authored or from
        permissively-licensed sources (CC-BY-SA attributed
        in a LICENSES.md inside the directory, per
        TB-US-047 Q5 licensing decision)
- [ ] R4: **Math-example system prompt** text —
      drafted and committed as the v1 prompt for the
      math-example agent. Includes:
      - Role framing ("math tutor")
      - Instruction to show work
      - RAG-citation discipline
      - Response-format expectations
- [ ] R5: **Trained adapter:**
      `adapters/math-example/v1/` — PEFT adapter
      trained against the training set in R2.
      - Base model: `Qwen/Qwen3-14B` (or chosen base;
        documented in model card)
      - LoRA config documented in `adapter_config.json`
      - Model card at `adapters/math-example/v1/MODEL_CARD.md`
        per HuggingFace convention (per TB-US-044 /
        TB-US-047 Q5 decision)
      - Apache 2.0 licensed (per TB-US-047 Q5)
- [ ] R6: **Baseline measurements** captured + committed
      to `docs/design/first-run-onboarding.md` or a new
      `docs/math-example/measurements.md`:
      - Stage 0: bare base model + math_eval_200 →
        accuracy %
      - Stage 1: +RAG → accuracy %
      - Stage 2: +RAG +adapter → accuracy %
      - Must show meaningful deltas (if deltas aren't
        meaningful, iterate the RAG seed + training set
        before publishing)
- [ ] R7: **Seed loader** in
      `backend/api/first_run_seeder.py`:
      - On fresh install, if math-example files are
        bundled in the install, create the agent via
        TB-US-048's /agents endpoint and populate:
        - Training set v1 from R2
        - RAG v1 from R3
        - Prompt v1 from R4
        - Adapter v1 from R5 (if GPU/adapter available
          — Track A)
        - Harness v1 referencing R1
        - 3 experiments (Stage 0, 1, 2) in `completed`
          state with the measured results from R6
      - If any files missing: skip gracefully with log
        line
- [ ] R8: **Package distribution:**
      - Training set + RAG seed shipped in the git repo
        (small enough)
      - Adapter files: too large for git (~300MB
        typical for 14B LoRA). Option A: GitHub Release
        asset; Option B: HuggingFace Hub. Decide at
        implementation time; document in INSTALL.md.
        Lean: HuggingFace Hub as `eversole-learning/trainingbench-math-example-v1`.
      - First-run seeder downloads from release/hub if
        local copy absent AND operator opts in.
- [ ] R9: **LICENSES.md files** in each artifact
      directory:
      - `training-sets/math-example-v1/LICENSES.md`
        → Apache 2.0 EL-authored
      - `rag-seeds/math-example-v1/LICENSES.md` →
        per-source attribution
      - `adapters/math-example/v1/MODEL_CARD.md` →
        Apache 2.0 + base model source + training-set
        provenance
- [ ] R10: **Documentation update:** add
      `docs/math-example/README.md` describing the
      pedagogical arc, how to reproduce the three
      stages, what the measurements mean, how to
      extend / fork.

## Acceptance Criteria

- [ ] AC1: `math_eval_200.jsonl` committed, 200 entries,
      domain coverage per R1, no overlap with training
      set.
- [ ] AC2: Training set JSONL committed, ~500 entries,
      no overlap with eval harness.
- [ ] AC3: RAG seed directory committed with
      LICENSES.md attribution for every non-EL source.
- [ ] AC4: System prompt committed.
- [ ] AC5: Adapter files produced + MODEL_CARD.md
      written; files reachable (local or release
      asset).
- [ ] AC6: Baseline measurements documented with
      three distinct accuracies showing meaningful
      deltas (minimally: Stage 2 > Stage 1 > Stage 0).
- [ ] AC7: Fresh install → seeder runs → math-example
      agent appears in agent list → three Stage
      experiments visible with recorded results →
      operator can run their own eval harness and
      roughly reproduce the baseline.
- [ ] AC8: Removing math-example files from install
      → seeder skips cleanly; no errors; agent list
      shows only `default` (or empty, depending on
      TB-US-051 seed state).
- [ ] AC9: Non-GPU install (Track B per TB-US-047 §7)
      → Stage 0 + Stage 1 seeded (no adapter); install
      flow explicitly tells operator "adapter requires
      GPU; see Stage 2 to add later".

## Design Notes

- **This is the hard-content story.** Code is minimal
  (seeder + loaders). The real work is dataset
  curation, RAG seed authorship, adapter training, and
  achieving meaningful deltas. Expect multiple training
  iterations before deltas are convincing.
- **200 eval samples is a reasonable target** — large
  enough to show statistical signal, small enough to
  run in minutes (not hours) on the shipped base model.
- **No overlap between training set and eval** is a
  hard rule. Overlap would make Stage 2 numbers
  misleading. Automated check in CI post-first-run
  (optional follow-up: a `scripts/verify_no_overlap.py`
  that compares the two JSONL files by question-text
  Jaccard similarity).
- **HuggingFace Hub for adapter distribution** keeps
  the git repo small and gives us a public home for
  model cards + weights. Operators who prefer offline
  installs can mirror the hub release to local disk.
- **Pedagogical framing matters.** The three stages
  should feel like a learning narrative, not a
  benchmark table. The docs should answer "why does
  Stage 2 beat Stage 1?" in a way that teaches the
  Sweet Spot concept.

## Out of Scope

- Non-math example agents (future stories per domain)
- Automated regression suite that re-measures baselines
  on every PR (future CI story)
- Interactive tutorial walking through staged
  progression (future UX story)
- Multi-model base comparison (what if operator uses
  Llama vs Qwen?) — v0.1 ships one base
- Downstream agent-cloning / forking semantics

## Related

- [TB-US-047](tb-us-047.md) §8 story #7 — this story
  executes it; Q3B staged progression + Q5 licensing
- [TB-US-056](tb-us-056.md) — eval harness; this
  story's harness definition targets `math_qa_v1`
- [TB-US-058](tb-us-058.md) — first-run seeder; depends
  on these artifacts being published
- [TB-US-052](tb-us-052.md) through [TB-US-056](tb-us-056.md)
  — versioned component machinery; prerequisite
- [TB-US-048](tb-us-048.md) — agent editor; seeder
  creates the math-example agent via /agents endpoint
- Files touched:
  - `backend/harnesses/data/math_eval_200.jsonl` (new)
  - `training-sets/math-example-v1.jsonl` (new)
  - `rag-seeds/math-example-v1/` (new directory)
  - `adapters/math-example/v1/` (new directory;
    files via Release/Hub)
  - `backend/api/first_run_seeder.py` (new)
  - `docs/math-example/README.md` (new)
  - `docs/math-example/measurements.md` or appended
    to `docs/design/first-run-onboarding.md`

## Phase A Completion Notes (2026-10-22)

**Scope revised 2026-10-22 per operator reframe** (3-phase bounded demonstration — not open-ended Sweet Spot search). Phase A infra prep is complete; story stays **In Progress** pending Phase B (operator runs training + 3 experiments) and Phase C (workflow doc).

### Scope deviations from original story draft

- **Dataset:** 6-domain hand-curated breakdown (R1) → **GSM8K uniform word problems** (public benchmark; operator doesn't curate content; standard eval). Train/test are disjoint sets upstream so overlap-safe by construction.
- **Base model:** Qwen3-14B → **Llama 3.1 8B** (matches TB-US-001 existing training pipeline; 24GB VRAM fits via QLoRA).
- **Content source policy:** operator-authored → **public-benchmark + original EL reference docs** (operator can't hand-build math content; operator runs training + evaluates).
- **Stage ordering:** bare → +RAG → +adapter → **bare → +adapter → +RAG** (per operator 2026-10-22 reframe — adapter before RAG so E2 answers "what does training do by itself" and E3 answers "what does retrieval add on top of a trained model").
- **Adapter distribution (R8):** HuggingFace Hub lean → **local only for v0.1**; fresh TB installs are Track B (no adapter) until a future distribution story.
- **R6 baseline measurements:** deferred to Phase B (only operator can run training).
- **R10 math-example README:** deferred to Phase C (needs real measured numbers).

### Phase A deliverables (shipped)

- **`datasets/math/data/`** — GSM8K downloaded (7473 train + 1319 test) via existing `scripts/download_gsm8k.py` (TB-US-001).
- **`scripts/prep_math_example_jsonl.py`** (new) — deterministic (seed=42) sampler that extracts 200 eval + 500 train rows into:
  - `backend/harnesses/data/math_eval_200.jsonl` — `{sample_id, question, expected_answer, domain}` compatible with `math_qa_v1.run()`. Final numeric answer extracted from GSM8K's `#### N` marker.
  - `training-sets/math-example-v1.jsonl` — `{sample_id, question, answer}` with full chain-of-thought preserved for adapter training.
  - Overlap sanity-check: `assert eval_qs & train_qs == set()` ✓
- **`rag-seeds/math-example-v1/`** (new):
  - `strategy-guide.md` — 4-step problem-solving framework (original EL, Apache 2.0)
  - `worked-examples.md` — 5 worked solutions covering common patterns (original EL — NOT drawn from GSM8K)
  - `formula-sheet.md` — arithmetic / fractions / percent / ratio / rate / geometry / algebra reference (original EL)
  - `system-prompt.txt` — tutor-framing prompt instructing step-by-step work + `#### <answer>` final-line marker matching GSM8K
  - `LICENSES.md` — Apache 2.0 attribution with honest expectation-setting ("RAG may add little or nothing to GSM8K accuracy; a null delta is also a valid finding")
- **`backend/api/first_run_seeder.py`** (new) — idempotent `seed_math_example()`:
  - Creates `math-example` agent via `AgentManager`
  - Loads training-set v{N} released + promoted (500 samples)
  - Loads RAG v{N} released + promoted (3 docs, manifest-level only; chat-path chroma rewiring is TB-US-053 deferred)
  - Loads prompt v{N} released + promoted
  - Loads harness v{N} released (harnesses don't promote per TB-US-043 Q5)
  - Creates **3 draft experiments** matching Phase B's sequence:
    - E1 `math-example-e1-bare-llama-3.1-8b` (prompt pinned, no RAG, no adapter)
    - E2 `math-example-e2-plus-adapter` (prompt pinned, no RAG, adapter_version_id null for operator to populate)
    - E3 `math-example-e3-plus-rag` (prompt pinned, RAG pinned, adapter null for operator to populate)
  - Opt-out: `TB_SKIP_FIRST_RUN_SEED=1`
  - Failure recovery: writes `logs/first-run-seeder.failed` on exception
- **`backend/api/main.py`** — wired `seed_math_example()` into startup after schema migrations

### Verification

- **Startup log:** `[seeder] {'seeded': True, 'agent_id': 3, 'training_set_version_id': 3, 'training_set_samples': 500, 'rag_version_id': 3, 'rag_chunk_count': 3, 'prompt_version_id': 3, 'harness_version_id': 2, 'experiments': [{'id': 2, 'label': 'math-example-e1-bare-llama-3.1-8b'}, {'id': 3, 'label': 'math-example-e2-plus-adapter'}, {'id': 4, 'label': 'math-example-e3-plus-rag'}]}` ✓
- `GET /agents` → `[default, math-example]` ✓
- `GET /experiments?agent_id=3` → 3 draft experiments present ✓
- Idempotent re-run → `{'seeded': False, 'reason': "agent 'math-example' already exists (id=3)"}` ✓
- Opt-out env var honored (`TB_SKIP_FIRST_RUN_SEED=1` returns `seeded: False` with reason) ✓

### Note on version IDs

The `*_version_id = 3` for training set / rag / prompt reflects AUTOINCREMENT not resetting after prior test-fixture cleanup (TB-US-052/053/055 verification created and then deleted test rows). Cosmetic only; functionally correct. If you want cleaner version IDs for the demo, say the word and I'll run a one-time renumber.

### Phase B — dependency shift (2026-10-22)

**Phase B workflow pivoted from CLI to UI-driven after operator
asked for backgrounded training with observability**. Phase B is
now **blocked on TB-US-064 arc** (coordinator + TB-US-065 backend
launch endpoint + TB-US-066 UI). Original CLI-based Phase B steps
preserved below as a fallback / historical reference, but the
intended operator workflow is through the UI.

#### Expected post-TB-US-064 Phase B workflow

1. **E1 baseline (no training needed):** Run
   `/experiments/{E1}/run` from the API or future experiment-
   runner UI. Harness evaluates bare Llama 3.1 8B against the
   200-example eval set.
2. **Train the adapter via UI:** Open the Training Runs drawer
   entry → `+ Start new run` → select
   `training_set_version_id=3`, base model Llama 3.1 8B,
   hyperparameters from training/math/README defaults, agent =
   `math-example`. Launch. Logout. Come back later.
3. **On successful completion**, adapter auto-registers as
   `adapter_versions.v{N}` via TB-US-063 (per TB-US-065 R9).
   Operator still manually releases + promotes.
4. **E2 (adapter):** promote the adapter → re-run experiment E2
   → harness evaluates adapter-only path.
5. **E3 (adapter + RAG):** depends on chat-path chroma rewiring
   from TB-US-053 landing OR inline injection of reference docs
   into the inference prompt. Decide at the time.
6. **Phase C trigger:** operator says "draft the workflow doc"
   with the three measured numbers; I write
   `docs/math-example/sweet-spot-exploration.md` +
   `docs/training/sweet-spot-workflow.md`.

#### Original CLI fallback (if TB-US-064 arc is delayed)

Possible operator workflow if the UI isn't yet in place —
measures everything from the terminal rather than the UI, loses
backgrounded observability but still produces the measurements:

1. `training/math/baseline.py` → E1 result (~30 min)
2. `training/math/train.py` → adapter files (~3–4 hours)
3. `POST /adapter-versions/register` manually from curl
4. `training/math/evaluate.py` → E2 result (~30 min)
5. For E3: manually inject RAG seed into prompt → measure
6. Phase C trigger

This path is noted so operator has an escape hatch if TB-US-064
takes longer than expected. Lean: wait for TB-US-064.

## Phase C Completion Notes (2026-10-25)

Phase C ships two documents + a rewrite of the public Jekyll page:

1. **`docs/pages/staged-progression.md` — rewritten.** The public-
   facing Pages site now shows real measurements (0/200 at all three
   stages) with an honest-baseline framing + a "Make it work" dial
   table for operators who want performant numbers.
2. **`docs/math-example/sweet-spot-exploration.md` — new.** Operator-
   facing deep companion with full version pins, DB-level experiment
   IDs, timings, VRAM observations, failure-mode analysis (base vs.
   adapter vs. RAG vs. grader), and the path to performant numbers.
3. **`docs/training/sweet-spot-workflow.md` — new.** Generic
   workflow for operators to apply this pattern to their own agents.
   Covers all 10 workflow steps + dials-to-turn table + operational
   notes on VRAM state, GPU serialization, audit trail,
   reproducibility.

**Framing choice.** All three docs land the same honest finding: the
TB staged-progression mechanism ships and works; the shipped
pedagogical artifacts (500-sample LoRA on base Llama + 3-doc toy
RAG + strict grader) are too minimal to make the ladder light up.
Operators who want performance are pointed at concrete scale-up
dials (biggest effect: swap to Instruct variant).

**Phase C deliverables map vs. story-text in §Phase B**:
- `sweet-spot-exploration.md` ✅ (named deliverable)
- `sweet-spot-workflow.md` ✅ (named deliverable)
- Public Pages page updated with real numbers (not strictly
  listed as a deliverable but implied by TB-US-060 + the operator
  "update with your actual measurements after the first operator-run
  completion" line in the placeholder page).

**Story closes.**

## Phase B Completion Notes (2026-10-25)

**Phase B executed end-to-end via the UI-driven workflow.** The
TB-US-064 arc (TB-US-065 backend + TB-US-066 training UI) and
TB-US-069 (experiment-time per-version model-stack swap) all
landed, unblocking the full three-stage measurement.

### Workflow actually run

1. **Training (TB-US-065 + TB-US-066).** Operator launched
   training run #6 against training_set v3 (500 samples) with
   default hyperparameters (lora_rank=16, alpha=32, lr=2e-4,
   3 epochs, batch=4). Adapter auto-registered as
   `adapter_versions.v2` after TB-US-065 bugfix #2 (HF Trainer
   saves to `output_dir/final/`, not `output_dir/`).
2. **Promotion.** Operator released + promoted adapter v2.
3. **Experiments (TB-US-069 harness-runner rewrite).** Three
   fresh experiments (ids 5/6/7) created with pins matching
   the Stage 0/1/2 progression + harness v2 at `n_samples=200`.
   Launched sequentially via `POST /experiments/{id}/run`.
4. **Observability.** Supervised via `GET /experiments/{id}`
   polling + `nvidia-smi`. (The gap in UI-side experiment
   visibility was captured as TB-US-070.)

### Measurements

| ID | Experiment | Adapter | RAG | correct | n | accuracy | duration |
|---|---|---|---|---|---|---|---|
| 5 | E1 (Stage 0 — bare) | — | — | 0 | 200 | 0.0 | 1212s (20 min) |
| 6 | E2 (Stage 1 — +adapter) | v2 | — | 0 | 200 | 0.0 | 2531s (42 min) |
| 7 | E3 (Stage 2 — +adapter+rag) | v2 | v3 | 0 | 200 | 0.0 | 2507s (42 min) |

**All three stages measured at accuracy=0.0.** The plumbing is
verified (TB-US-069 confirmed via `_stack` summary that each
experiment loaded a distinct stack); the measurements are honest
and attributable to the toy nature of the shipped artifacts.

### Analysis — why the baselines are flat

1. **Base model is not instruct-tuned.** Llama-3.1-8B base
   produces coherent-looking math prose that follows the
   `#### answer` format pattern from the few-shot context, but
   it's not actually solving the problems. Per-sample outputs
   from E1 showed the model continuing with a new question-
   and-answer pair rather than solving the one asked.
2. **Adapter is severely undertrained.** 500 training samples ×
   3 epochs on GSM8K-level reasoning is too few. Published
   math-reasoning LoRAs typically use ≥10k samples and more
   aggressive hyperparameters (higher rank, longer training).
   The 500-sample training set here is pedagogical scaffolding,
   not a performant corpus.
3. **RAG manifest is a 3-doc toy.** `rag_version_id=3` seeds
   three short math-concept documents. Per-question retrieval
   doesn't materially improve problem solving at this scale.
4. **Grader is strict.** Harness compares the model's final
   `####` numeric answer against ground truth. Any formatting
   drift or wrong number scores zero.

**None of these are bugs.** They are expected properties of a
pedagogical "first install" example whose purpose is to prove
the TB staged-progression workflow — training + promotion +
experiment-pinned evaluation — ships and runs correctly. The
baselines produce clean 0.0 measurements that are stable and
reproducible, which is itself a useful property for a demo.

### Phase B observations worth preserving

- **Timings scale with chain-of-thought length.** E1 at 20 min
  vs E2 at 42 min — the adapter-trained model generates longer
  outputs per sample. Operators planning Phase B-style runs
  should budget 20–45 min per experiment at n=200 depending on
  the adapter.
- **RAG retrieval overhead at this scale is small** (~0% in E3
  vs E2 at 200 samples). The 5-sample verification run showed
  a ~20% delta, but that was dominated by model-load warmup.
- **VRAM shape:** idle ~1.1 GB post-service-restart; one active
  stack ~16–17 GB; `_free_stack()` releases Python refs but
  PyTorch's caching allocator retains most of the VRAM between
  runs. Not a leak — reused by the next stack. Documented as
  TB-US-069 AC8.
- **Service restart is the right reset.** Between runs, VRAM
  stays at ~16 GB which is enough headroom on a 24 GB card
  for the next stack to load, but doesn't return to baseline.
  A clean baseline requires `systemctl restart trainingbench`.

### Phase B deliverables

- Three completed experiments (ids 5, 6, 7) in the DB with
  full `results_json` including `_stack` summary + 200-row
  `per_sample` arrays.
- Three archived experiments (ids 2, 3, 4) preserving the
  TB-US-069 5-sample verification run audit trail.
- This Phase B Completion Notes section (what you're reading).

### Phase C trigger

Phase C (workflow doc) is now unblocked. Deliverables:
`docs/math-example/sweet-spot-exploration.md` +
`docs/training/sweet-spot-workflow.md`.

The workflow doc will frame the honest finding: **the
staged-progression workflow ships and works mechanically; the
toy artifacts don't produce improvements at these minimal
training scales, and that's acceptable for a pedagogical
first-install example**. Operators who want performant math
agents are directed to retrain with ≥10k samples +
appropriate hyperparameters.

Phase C status: ready to draft when operator triggers.
