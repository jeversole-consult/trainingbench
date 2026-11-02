# Architectural Finding — `training_set_versions` was never wired into `train.py`

**Discovered**: 2026-11-02 during TB-US-078 Phase 2 preparation
**Fixed**: TB-US-078 (same day)
**Published for**: future reproducibility; publication honesty;
  reader needs this context to interpret trial-to-trial comparisons
  across TB-US-075 through TB-US-077

## tl;dr

The `training_set_versions` registry (TB-US-052) stored per-version
sidecar JSONL files on disk and exposed them as the "authoritative
training data" via API. The adapter_versions table's
`training_set_version_id` field claims to answer *"exactly what
data was this adapter trained on?"*

In reality, `training/math/train.py` **never read those JSONL
files**. From its ship date (TB-US-065, 2026-10-22) through this
finding, the trainer unconditionally called
`load_from_disk("datasets/math/data")` — the raw full-size GSM8K
HuggingFace Datasets directory — and selected the first N rows
after HF's default shuffle. The `training_set_version_id` on each
adapter row was *provenance decoration*, not a data-input pointer.

Fixed in TB-US-078 via a clean cutover (no backward-compat shim).
Training now reads the sidecar JSONL and uses each row's `text`
field verbatim.

## How the gap existed

**Design intent, per TB-US-052 / TB-US-063 / TB-US-065:**

```
                   ┌──────────────────────────┐
POST /training/    │                          │
      runs/launch  │   training_runs row      │
     ──────────────▶   .training_set_version_id──┐
                   │                          │ │
                   └──────────────────────────┘ │
                                                ▼
                   ┌──────────────────────────┐
                   │  training_set_versions   │
                   │        row               │
                   │  .files_path (JSONL on   │
                   │               disk)      │
                   └────────────┬─────────────┘
                                │ read samples
                                ▼
                   ┌──────────────────────────┐
                   │  train.py                │  <- intended path
                   │  prepare_dataset()       │
                   │  → trains on these rows  │
                   └──────────────────────────┘
```

**What actually happened:**

```
                   ┌──────────────────────────┐
POST /training/    │  training_runs row       │
      runs/launch  │  .training_set_version_id = v6
     ──────────────▶   (recorded; never read for data)
                   └──────────────────────────┘
                               │
                               │  spawned subprocess with --run-id
                               ▼
                   ┌──────────────────────────┐
                   │  train.py                │
                   │  prepare_dataset(        │
                   │    dataset_path =        │
                   │    "datasets/math/data"  │  <-- hardcoded default
                   │  )                       │
                   │  = load_from_disk(…)     │
                   │  = raw GSM8K             │
                   │  = train_data.select(    │
                   │      range(N))           │  <-- first N of GSM8K.train
                   └──────────────────────────┘
                               │
                               │ auto-register adapter
                               ▼
                   ┌──────────────────────────┐
                   │  adapter_versions row    │
                   │  .training_set_version_id = v6
                   │   (metadata; untrue      │
                   │    as a data-input      │
                   │    claim)                │
                   └──────────────────────────┘
```

The `training_set_version_id` round-tripped through the system as
a cross-reference string but never selected any bytes.

## How the discovery happened

TB-US-078 began as "Trial #5: train on chat-template-formatted
data on Instruct." The prep script
`scripts/prep_math_v7_chat_template.py` was written to:

1. Load the Instruct tokenizer and verify its `chat_template`
   attribute is non-empty.
2. Load GSM8K, shuffle with seed=46, pick 1000 unique questions
   strictly disjoint from the holdout set.
3. Apply `tokenizer.apply_chat_template()` with the TB system
   prompt v3 + user question + assistant answer (preserving
   GSM8K's native `#### N` marker).
4. Emit a JSONL with the pre-formatted `text` field per row.

Script ran successfully. Spot-checked sample #0: looked correct.

Before launching training, verified train.py would consume the
new JSONL by reading `prepare_dataset`. Discovery:

- Line 91: `dataset = load_from_disk(str(dataset_path))` — the
  entry point. Argument came from `--dataset-path` CLI arg
  (default: `datasets/math/data`).
- Line 47-79: `format_training_example` — a hardcoded chat-template
  formatter that re-emits every GSM8K record as its own string
  with `Final Answer: N` at the end (stripping GSM8K's native
  `#### N`).
- No reference anywhere in train.py to `training_set_version_id`,
  `training-sets/`, or the sidecar directory
  `training/datasets/training_set_versions/`.

Searched backend for the launch endpoint's handling of
`training_set_version_id`:

- `backend/api/main.py:/training/runs/launch`: stored it on the
  `training_runs` row's `training_set_version_id` column + passed
  it to `create_launched_run`. Did **not** resolve it to a file
  path for the subprocess.
- train.py:680 (`register_existing_adapter`): read
  `tb_run_config.get("_training_set_version_id")` and set it on
  the auto-registered adapter row. Pure provenance pass-through.

Conclusion: a wiring gap had persisted since TB-US-065 shipped.

## Why prior trials still produced interpretable results

Important for publication honesty. The architectural gap did NOT
invalidate TB-US-075–077's trial comparisons; it reframed them.

**What was constant across TB-US-075/076/077 trials:**

- Training data: first N rows of raw GSM8K.train (where N =
  `max_train_samples`), after HF's default-seeded shuffle
- Hardcoded chat-template-with-`Final Answer:` format via
  `format_training_example`

**What actually varied across trials:**

| Trial | Base | Rank | Epochs | LR | N | What changed vs. prior |
|---|---|---|---|---|---|---|
| #1 (US-075) | Base | 32 | 5 | 2e-4 | 200 | first adapter |
| #2 (US-076) | Base | 32 | 5 | 2e-4 | 200 | same adapter + patched harness |
| #3 (US-076) | Base | 16 | 10 | 2e-4 | 300 | ↑ epochs, ↓ rank, ↑ N |
| #4 (US-077) | Instruct | 32 | 5 | 2e-4 | 500 | base swap + ↑ N |

Trial-to-trial comparisons were therefore comparisons at approximately
constant training data on a varying hyperparameter axis. That's a
scientifically valid comparison — it just means the "training set
version" axis in the search log, which looked like a data-variation
axis, was actually a provenance-decoration axis.

**Specifically for Trial #4's regression finding:**

TB-US-077's conclusion — adapter v5 regressed Instruct from 43%
to 23% — stands. The mechanism (format mismatch via `Final
Answer:` deleting Instruct's native `####`-at-end confirmation)
is correctly identified. The architectural gap is adjacent, not
causally upstream: a correct wiring + the same hardcoded template
would have produced the same regression.

## Why the format bug was adjacent (not identical) to the wiring bug

Two bugs lived in `train.py`:

**Bug 1 — Wiring gap**: `prepare_dataset` reads raw GSM8K, not
the registered training set.

**Bug 2 — Format strip**: `format_training_example` splits GSM8K
answers on `####` and emits `...reasoning...\n\nFinal Answer: N`,
discarding the native `####` marker.

Bug 2 is independent of Bug 1 — Bug 2 would still have corrupted
Instruct's native structure even if Bug 1 hadn't existed. But
Bug 1 shaped how we would have fixed Bug 2:

- Under Bug 1 (wiring broken), fixing Bug 2 required patching
  `format_training_example`'s hardcoded template.
- Under Bug 1-fixed (TB-US-078 wiring correct), fixing Bug 2
  moves OUT of train.py entirely: the per-version prep script
  owns the format. train.py uses `text` verbatim.

The cleaner separation is a design win from the fix. Future trials
can experiment with different formatting approaches purely by
changing the prep script — train.py doesn't care.

## The fix (TB-US-078)

Clean cutover (no dispatch logic — per
`feedback_no_backcompat_research_mode`, the old codepath wasn't
driving behavior as designed, so nothing is lost by deleting it).

**`training/math/train.py` changes:**

- `prepare_dataset(training_set_jsonl, eval_dataset_hf_dir, …)`:
  loads from JSONL, uses `text` field verbatim. Eval set is still
  GSM8K `test`, chat-template-formatted inline so eval-loss is
  comparable to training-loss.
- `_load_training_set_jsonl(path)`: reads the sidecar JSONL,
  validates every row has `text`, returns HF Dataset.
- Deleted: `format_training_example`, the raw-GSM8K default,
  `--subset`, `use_full_dataset`.
- New CLI arg: `--training-set-jsonl` (required unless `--run-id`
  supplies via TB launch config).

**`backend/api/main.py` changes:**

- `/training/runs/launch`: resolves `training_set_version_id` →
  `training_set_version_manager.sidecar_path(version_id)` →
  validates file exists → passes as `_training_set_jsonl` in the
  launch config.
- 400 error if `training_set_version_id` is missing or the sidecar
  file is missing.

**`backend/api/training_set_version_manager.py` changes:**

- Added public `sidecar_path(version_id)` wrapper around the
  internal `_sidecar_path`.

## Implications for future reproducibility

Going forward:

1. Every trial's **actual training data** is faithfully recorded
   in the sidecar JSONL at
   `training/datasets/training_set_versions/v{N}.jsonl`.
2. `adapter_versions.training_set_version_id` now closes the
   provenance loop as designed.
3. Prep-script changes propagate directly to training (via a new
   training_set_version row + a re-registration call), so the
   "data" axis of our research search is now genuinely variable.
4. For published results, reproducibility becomes:
   - Grab `training_set_versions.v{N}` sidecar
   - Grab train.py at the commit hash from `training_runs.config`
   - Grab the adapter from `adapter_versions.{M}.files_path`
   - Re-run on comparable hardware → within stochastic variance,
     identical adapter

**Not re-training v4/v5/v6 adapters under correct wiring.** The
trial comparisons remain scientifically interpretable at
approximately-constant-data. The findings (harness bug in Trial
#1, overfit in Trial #3, Instruct regression in Trial #4) do not
change under the correct wiring. Trial #5 and all subsequent
trials run under the correct wiring.

## Related documents

- `docs/user-stories/tb-us-078.md` — the fix
- `docs/user-stories/tb-us-079.md` — Trial #5 under correct wiring
- `docs/math-example/methodology.md` — research protocol
- `docs/math-example/study-design.md` — per-trial pre-registrations
- `docs/math-example/sweet-spot-search-log.md` — chronological
  trial record
- `docs/math-example/instruct-scale-up-results.md` — Trial #4
  deep dive (F13 analysis)
