# TB-US-078: Wire `training_set_versions` JSONL into `train.py` — prerequisite for correct Trial #5

**Status**: Completed
**Created**: 2026-11-02 (originally as Trial #5 story)
**Rescoped**: 2026-11-02 — original Trial #5 scope moved to TB-US-079 after architectural discovery
**Completed**: 2026-11-02
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on closure commit>

## Story

As a TB maintainer executing the Instruct-PEFT research arc, I
want **`train.py` to actually read its training examples from
the registered `training_set_version.file_path` JSONL** — the
provenance record the registry claims to be — so that Trial #5
(and every future trial) tests the hypothesis we think it's
testing, not a surrogate.

Prerequisite for TB-US-079 (Trial #5 — chat-template-formatted
training on Instruct). Captured as its own story because the
discovery is substantive enough to publish, and the fix needs
clean validation independent of Trial #5's research hypothesis.

## Background — the discovery

During TB-US-078 Phase 2 preparation (which was originally
Trial #5 under the old scope), inspection of `train.py` revealed
a **training-pipeline wiring gap** that had been in place since
TB-US-065 shipped (2026-10-22):

**Design intent (per TB-US-052/063/065):**
- `training_set_versions` registry owns a JSONL file per
  version (`training-sets/*.jsonl`)
- `/training/runs/launch` records `training_set_version_id` on
  the run; `train.py` reads that version's data as training input
- `adapter_versions.training_set_version_id` closes the
  provenance loop

**Actual implementation (train.py `prepare_dataset`, lines 82–160):**
- Unconditionally calls `load_from_disk("datasets/math/data")`
  — the raw full-size GSM8K HuggingFace Datasets directory
- Takes `train_data.select(range(max_train_samples))` — the first
  N rows after HF's default-seeded shuffle
- Ignores the launch request's `training_set_version_id` for
  data-input purposes; the ID is **stored on the adapter row
  (`register_existing_adapter` call at train.py:680) as pure
  provenance decoration**, never consulted for the actual training
  data bytes

**Consequence for prior trials TB-US-075/076/077:** every trial
nominally used a different `training_set_version` (v4, v5, v6
with distinct seeds), but all three trials actually trained on
essentially the same slice (`GSM8K.train[0:N]`) of raw GSM8K.
Scientifically, this means prior trials still produced valid
comparisons on hyperparameters (rank, epochs, lr, base model) at
constant data, but the "data" axis in our search was never
being varied as advertised.

**Related format bug (fixed as part of this story's cutover):**
`format_training_example` at train.py:47-79 splits GSM8K answers
on `####` and emits `...reasoning... Final Answer: {final_answer}`.
GSM8K's native `#### N` marker is deleted. On the Instruct base,
this overwrote Instruct's native `####`-at-end answer-confirmation
behavior and contributed to Trial #4's regression (TB-US-077 F13
analysis). The JSONL path lets each training set version carry its
own fully-formed `text` field, bypassing the hardcoded template
entirely.

## Scope

Clean cutover (no backward-compat dispatch — per the
`feedback_no_backcompat_research_mode` memory, the old codepath
wasn't driving behavior as designed, so nothing is lost by
deleting it).

- **`training/math/train.py`** — rewrite `prepare_dataset()`:
  - Takes a `training_set_jsonl` path (required)
  - Reads JSONL via `datasets.load_dataset("json", data_files=...)`
    OR plain `json.loads` loop
  - Uses the `text` field verbatim for tokenization — no
    reformatting, no `####`-stripping, no system-prompt
    hardcoding
  - Metadata columns (`question`, `answer`, `sample_id`) are
    carried through for traceability but not used in tokenization
  - Delete `format_training_example`
  - Delete the `datasets/math/data` default fallback

- **Eval dataset** — eval uses the GSM8K `test` split (unchanged),
  but each eval record is formatted via the same
  `tokenizer.apply_chat_template()` call so the eval-loss metric
  is comparable to training loss. This handling lives inside
  `prepare_dataset` and is distinct from the training set's
  `text` field (training-set-version JSONL is for training only;
  eval is a fixed reference set).

- **`backend/api/main.py` `/training/runs/launch`** — resolve
  `training_set_version.file_path` from the registry at launch
  time, validate the file exists, pass the absolute path to
  `train.py` as `--training-set-jsonl`.

- **`training/math/train.py` CLI** — new required arg
  `--training-set-jsonl`. If not provided and `--run-id` is set,
  the TB launch config carries it via `_training_set_jsonl` key.

## Pre-registered hypotheses

Infrastructure story, not a research trial, but the smoke-run
validates:

### H78a — JSONL path works end-to-end

**Claim**: a training run launched via `/training/runs/launch`
with `training_set_version_id=<v7>` successfully reads from the
JSONL file, trains an adapter, and auto-registers it with the
correct `training_set_version_id` linkage.

**Measurable signal**: smoke-run (10 samples, 1 epoch, Instruct
base) completes without error; `adapter_versions` row's
`training_set_version_id = 7`; adapter files written to disk;
training logs confirm "loaded N rows from <jsonl path>".

### H78b — `text` field is used verbatim (no re-formatting)

**Claim**: the tokenized training input exactly matches the
`text` field of the JSONL row, with no stripping or substitution.

**Measurable signal**: a tokenize-and-detokenize round-trip of
sample #0 reproduces the original `text` field (modulo known BPE
unicode edge cases). Logged by train.py at startup for the first
training example.

### H78c — Smoke adapter output has native `#### N` structure

**Claim**: an adapter trained from a chat-template-formatted
training set (v7) produces outputs that end with `#### N`, not
`Final Answer: N` as adapter v5 did.

**Measurable signal**: run a tiny inference check (3 holdout
questions) after smoke-run completes; count outputs ending with
`#### N`. ≥2/3 passes H78c.

## Requirements

### Phase 1 — Code changes

- [ ] R1: `train.py prepare_dataset` rewrite — JSONL input + `text`
      field verbatim; eval still GSM8K `test` with chat template
- [ ] R2: `train.py` CLI — new `--training-set-jsonl` arg; validate
      file exists at parse time
- [ ] R3: Delete `format_training_example` and the
      `datasets/math/data` default fallback (clean cutover)
- [ ] R4: `main.py /training/runs/launch` — resolve
      `training_set_version.file_path`, pass as CLI arg; 400 if
      the file is missing

### Phase 2 — Documentation (written alongside code, not after)

- [ ] R5: `docs/math-example/architectural-finding-training-set-wiring.md`
      (new) — the deep dive on what was found, how, why prior
      trials still produced interpretable results, what changed
- [ ] R6: `docs/math-example/sweet-spot-search-log.md` — new
      "Research-process finding (2026-11-02)" entry inserted
      between Trial #4 and the planning entry for Trial #5
- [ ] R7: `docs/math-example/methodology.md` — new "Known
      research-process limitations discovered during execution"
      section referencing the architectural finding
- [ ] R8: `docs/math-example/study-design.md` — correct Trial #5
      pre-registration to reflect that prior trials used
      first-N-of-GSM8K (not the registered training set)

### Phase 3 — Validation smoke-run

- [ ] R9: Register `training_set_versions.v7` via API (file:
      `training-sets/math-example-v7-chat-template.jsonl`,
      already built by `scripts/prep_math_v7_chat_template.py`)
- [ ] R10: Release + promote v7
- [ ] R11: Launch training run: Instruct base, v7 training set,
      `max_train_samples=10`, `epochs=1`, `lora_r=16` — only
      goal is to prove end-to-end pipeline, not research
- [ ] R12: Verify H78a, H78b, H78c
- [ ] R13: If smoke-run fails: iterate on train.py until it passes
      before closing TB-US-078

### Phase 4 — Close

- [ ] R14: Commit + push + flip TB-US-078 → Completed in
      BACKLOG.md + fire closure notification
- [ ] R15: Flip TB-US-079 (Trial #5) → unblocked / ready-to-fire

## Acceptance Criteria

- [ ] AC1: `train.py` reads training data from the JSONL path,
      not `load_from_disk`
- [ ] AC2: `format_training_example` and the `datasets/math/data`
      default fallback are deleted
- [ ] AC3: `/training/runs/launch` validates the training set's
      file exists and passes it to train.py
- [ ] AC4: Smoke-run completes end-to-end
- [ ] AC5: H78a (pipeline works), H78b (text verbatim), H78c
      (native `####`) all have recorded outcomes
- [ ] AC6: Architectural finding deep dive exists
- [ ] AC7: methodology / study-design / search-log all updated
      with the finding
- [ ] AC8: TB-US-079 unblocked and ready to fire as Trial #5

## Design Notes

- **Why not keep the old codepath as a fallback.** No current
  training run needs it; keeping it introduces a hidden mode
  switch that complicates reproducibility documentation. If a
  future story genuinely needs raw-GSM8K-via-HF, it can be
  re-introduced then with explicit framing.
- **Why the eval dataset stays raw GSM8K `test`.** Eval is a
  reference measurement, not a research variable. Chat-template
  formatting is applied so eval-loss and train-loss are
  computed on comparable sequences, but the eval dataset itself
  doesn't become a `training_set_version` row.
- **Why smoke-run uses 10 samples / 1 epoch.** The point is
  pipeline validation (H78a-c), not performance measurement.
  Trial #5 is the performance measurement, and TB-US-079 owns it.
- **"text field verbatim" discipline.** The JSONL prep script
  (`scripts/prep_math_v7_chat_template.py`) is where format
  decisions live. train.py's job is to tokenize what it's given,
  not to re-format. This separation lets future trials try
  different formatting approaches by changing only the prep
  script.

## Out of Scope

- Trial #5 itself (TB-US-079)
- Retroactive re-training of v4/v5/v6 adapters under correct
  wiring (not valuable — those trials' key findings don't change
  under the correct wiring; documented in the architectural
  finding doc)
- Migration of existing `training-sets/*.jsonl` files from v4/v5/v6
  to be "trainable" under the new wiring (not needed — v4/v5/v6
  wasn't actually training on those files; they're historical
  provenance artifacts only)
- Retraining the GSM8K eval set as a separate `training_set_version`
  — eval is a reference, not a variable

## Related

- [TB-US-077](tb-us-077.md) — Trial #4; produced the F13 analysis
  that led to Trial #5 preparation + the architectural discovery
- [TB-US-065](tb-us-065.md) — the training-run API that introduced
  the wiring gap being fixed here
- [TB-US-052](tb-us-052.md), [TB-US-063](tb-us-063.md) — the
  versioning primitives whose wiring this story completes
- [TB-US-079](tb-us-079.md) — Trial #5 proper (unblocked by this)
- `docs/math-example/architectural-finding-training-set-wiring.md`
  (new, R5)
- Files touched:
  - `training/math/train.py` (R1, R2, R3)
  - `backend/api/main.py` (R4)
  - `backend/api/training_set_version_manager.py` (public
    `sidecar_path` accessor for R4)
  - `docs/math-example/architectural-finding-training-set-wiring.md` (R5, new)
  - `docs/math-example/sweet-spot-search-log.md` (R6)
  - `docs/math-example/methodology.md` (R7)
  - `docs/math-example/study-design.md` (R8)
  - `BACKLOG.md` (R14)

## Completion Notes (2026-11-02)

### Smoke-run (R9–R12) results

- **R9**: `training_set_versions.v7` registered via API from
  `training-sets/math-example-v7-chat-template.jsonl` (1000
  samples, seed=46, chat-template-formatted, disjoint from
  holdout). `content_sha256 = 13adefc8…` Sidecar JSONL written
  at `training/datasets/training_set_versions/v7.jsonl` (2.1 MB).
- **R10**: v7 released + promoted (both API calls returned 200).
- **R11**: smoke training run #12 launched via
  `/training/runs/launch` with `training_set_version_id=7`,
  `max_train_samples=10`, `epochs=1`, Instruct base, rank 16.
  Launch endpoint resolved sidecar path and stored
  `_training_set_jsonl` in the run config.
- Training completed in 12.6 seconds (model load + 3 optimizer
  steps + save). Train losses: 2.36 → 2.87 → 2.44. Eval loss:
  2.25. Adapter auto-registered as `adapter_versions.v6` with
  `training_set_version_id = 7` provenance linkage (correct).

### Hypothesis outcomes

- **H78a — pipeline works end-to-end**: ✅ PASS
  - `_training_set_jsonl` in run #12 config:
    `/home/jeversole/trainingbench/training/datasets/training_set_versions/v7.jsonl`
  - Run status: `completed`
  - 3 training steps logged in `training_run_metrics`
  - Adapter v6 auto-registered with `training_set_version_id=7`
  - Files written: `adapter_config.json`,
    `adapter_model.safetensors`, `tokenizer.json`,
    `training_args.bin`, `README.md`

- **H78b — `text` field used verbatim**: ✅ PASS (by code
  inspection)
  - `prepare_dataset()` has one tokenization path:
    `tokenizer(examples["text"], …)`. The `_load_training_set_jsonl`
    loader requires every row carry a `text` field (sys.exit if
    missing). No re-formatting codepath exists after
    `format_training_example` was deleted.

- **H78c — adapter LOADS + GENERATES + has native `####`**: ✅
  PASS by inspection (with smoke-scale caveat)
  - 3 holdout questions generated through PeftModel-loaded
    smoke adapter + bare Instruct base
  - Q0 output ended with `#### $43` (native structure, unit
    prefix) — see interpretation note below
  - Q1 output ended with `#### 28` (native structure, bare)
  - Q2 output truncated at max_new_tokens=256 before reaching
    marker
  - **Zero** outputs contained `Final Answer:` (the adapter v5
    regression pattern)
  - Caveat: smoke-scale training (10 samples × 1 epoch) is
    insufficient to meaningfully shift output distribution; the
    `####-at-end` observations likely reflect bare Instruct's
    native behavior more than training signal. Trial #5
    (TB-US-079) is where the training-signal effect becomes
    measurable.

### Observed quirk — `#### $N` unit-prefixed outputs

Instruct sometimes emits `#### $43` (or `#### 42%`) rather than
bare `#### 43` for money/percentage answers. The strict harness
regex `####\s*([-+]?\d[\d,.]*)` MISSES these matches, but the
patched harness's priority-3 trailing-number fallback catches
them, so accuracy scoring is correct. H5a interpretation for
Trial #5 updated to pre-register that `#### $N` counts as
native-structure-preserved. See TB-US-079's H5a notes.

### Acceptance criteria status

- ✅ AC1: `train.py` reads training data from JSONL
- ✅ AC2: `format_training_example` + `datasets/math/data`
  default fallback deleted
- ✅ AC3: `/training/runs/launch` validates + passes JSONL path
- ✅ AC4: Smoke-run completed end-to-end
- ✅ AC5: H78a / H78b / H78c outcomes recorded
- ✅ AC6: Architectural finding deep dive exists
- ✅ AC7: methodology / study-design / search-log all updated
- ✅ AC8: TB-US-079 unblocked (ready to fire at operator's call)
