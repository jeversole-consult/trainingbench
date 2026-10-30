# TB-US-074: Fix train.py logging_dir kwarg incompatibility with transformers 5.x

**Status**: Completed
**Created**: 2026-10-28
**Started**: 2026-10-28
**Completed**: 2026-10-28
**Author**: Jesse Eversole
**Commit hash(es)**: `f9366d5`

## Story

As a TB operator doing a fresh install, I want **the smoke training
pass from INSTALL.md Step 6 to actually run** — not crash immediately
with a `TypeError` from a transformers-library breaking change — so
that the "verify install end-to-end" step the doc promises actually
verifies anything.

## Background

Surfaced during TB-US-072 lab-machine fresh-install acceptance sweep
(2026-10-28), captured in `docs/release/v0.1.0-rc1-rehearsal-review.md`
as finding F9.

Walking INSTALL.md Step 6 (smoke training) end-to-end on a fresh
install hits:

```
TypeError: TrainingArguments.__init__() got an unexpected keyword
argument 'logging_dir'
  File ".../training/math/train.py", line 338, in train
    training_args = TrainingArguments(
```

The subprocess dies 10 seconds after launch. The DB status gets
reconciled to `failed` with the full traceback captured in
`training_runs.notes`.

### Root cause

`training/math/train.py` line 352 passes `logging_dir=str(logs_dir /
"gsm8k")` to `TrainingArguments(…)`. In HuggingFace Transformers
5.x (we have `transformers==5.22.1` pinned), the `logging_dir`
keyword argument was removed. The library now uses `output_dir`
for log artifacts when a logger is configured — and this training
script sets `report_to="none"` already, so no logging dir is
needed at all.

### Repro steps

1. Fresh clone + install (per INSTALL.md Steps 1–5)
2. Download GSM8K: `python scripts/download_gsm8k.py`
3. Run smoke training: `python training/math/train.py
   --max-train-samples 50 --max-eval-samples 25 --epochs 1
   --run-name smoke-test`
4. **Expected**: training loop runs to completion in ~10–15 min,
   produces an adapter at `training/adapters/smoke-test/`
5. **Actual**: `TypeError` on `TrainingArguments.__init__()` within
   10s of launch

### Proposed fix

Remove the `logging_dir=` line from the `TrainingArguments(…)`
constructor call. Since `report_to="none"` is set, no logging
backend writes anything; the kwarg has no effect even on versions
that accept it.

```diff
         optim="paged_adamw_8bit",
-        logging_dir=str(logs_dir / "gsm8k"),
         report_to="none",   # TB-US-066 fix: ...
```

**Depends on:** None (self-contained; one file edit)

**Blocks:**
- TB-US-072 Step 6 smoke verification can't complete until this
  ships
- Any operator fresh install needing to verify training end-to-end

## Requirements

- [x] R1: Remove line 352 (`logging_dir=str(logs_dir / "gsm8k"),`)
      from `training/math/train.py`.
- [x] R2: Preserve the `report_to="none"` line immediately after
      (TB-US-066 fix lineage — the comment references another
      story's fix).
- [x] R3: No other code changes needed. The `logs_dir` variable
      becomes unused; leave the declaration + mkdir for now so
      diff stays minimal and reversible (follow-up story can
      remove the dead variable if operator wants).
- [x] R4: Walk the full maintenance-fix workflow per TB-US-071's
      pattern:
      1. Observe (this finding)
      2. Draft (this story)
      3. Fire (status flip + notification)
      4. Fix (edit)
      5. Commit (TB-US-074: prefix)
      6. Push (origin main)
      7. Downstream verify (git pull on acceptance install; retry
         smoke training; confirm it reaches a training loop)
      8. Close (Completed + notification)
      9. Review-doc update (F9 → ✅ in
         `v0.1.0-rc1-rehearsal-review.md`)

## Acceptance Criteria

- [x] AC1: `training/math/train.py` no longer references
      `logging_dir=` anywhere
- [x] AC2: Smoke training (`python training/math/train.py
      --max-train-samples 50 --max-eval-samples 25 --epochs 1
      --run-name smoke-test-074`) on the TB-US-072 acceptance
      install runs past the `TrainingArguments` constructor without
      TypeError
- [x] AC3: Launching via the API (`POST /training/runs/launch`
      with the same parameters) on the acceptance install reaches
      the training loop (progress logs appear in `training_run_logs`
      table beyond "Training started")
- [x] AC4: Review doc F9 marked ✅ resolved with commit hash
- [x] AC5: Commit log references `TB-US-074`
- [x] AC6: Full 9-phase maintenance-fix workflow executed in order

## Design Notes

- **Why not pin older transformers.** TB is on
  `transformers==5.22.1` because the versioned-component framework
  + `huggingface_hub==2.4.0` dependencies want it. Pinning
  transformers back to a `<5.0` version to accept `logging_dir`
  would cascade compatibility problems. One-line removal is the
  less risky fix.
- **Why not rename `logging_dir` to the modern equivalent.** There
  isn't one — transformers 5.x delegates log paths to the reporter
  backend chosen via `report_to=...`. With `report_to="none"`
  there's no backend to configure, no path to specify.
- **Why keep the dead `logs_dir` variable.** Keeps the diff
  minimal (single-line removal), which is TB's convention for
  surgical fixes. The dead variable survives one minor version;
  a future TB-US can clean it alongside other dead-code pass.
- **Why this story and not just inline in TB-US-072.** Same
  reasoning as TB-US-071: findings that need code fixes get their
  own stories. TB-US-072 is the acceptance sweep; TB-US-074 is the
  fix. Keeps completion criteria atomic.
- **F7a (silent subprocess crash on missing GSM8K) is explicitly
  out of scope here.** F7a is a separate code path (ingress
  validation on `POST /training/runs/launch`) and gets its own
  story if operator decides it's worth fixing. On a fresh install
  following INSTALL.md literally, F7a doesn't bite because Step 6
  tells operator to download GSM8K first.

## Out of Scope

- Removing the now-dead `logs_dir` variable (follow-up code
  cleanup, if operator wants)
- Adding ingress validation to `POST /training/runs/launch` (F7a
  — separate story if drafted)
- Adding an `error_message` column to `training_runs` (F8 — minor
  DX, probably not worth a story)
- Pinning transformers to a specific minor version in
  requirements.txt (separate decision; current float works except
  for this one kwarg)

## Related

- [TB-US-072](tb-us-072.md) — acceptance sweep that surfaced F9
- [TB-US-071](tb-us-071.md) — maintenance-fix workflow template
  this story applies
- [TB-US-065](tb-us-065.md) — training-run tracker (observed
  subprocess crash via its reconciliation path)
- [TB-US-066](tb-us-066.md) — `report_to="none"` fix lineage (the
  comment on the surviving line references this story)
- Files touched:
  - `training/math/train.py` (the fix)
  - `docs/release/v0.1.0-rc1-rehearsal-review.md` (F9 → ✅ resolved)
