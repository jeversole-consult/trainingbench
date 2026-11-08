# TB-US-099: Port — training_run_tracker extensions to stalite3

**Status**: Completed 2026-11-07 — stalite3 commit `022a2c9`
**Depends on**: TB-US-094, TB-US-096, TB-US-097, TB-US-098
**Blocks**: TB-US-100 (harness_runner needs backfill_accuracy)

## Scope

- [x] Migration `stalite-04-training-run-extensions`: ALTER
      `training_runs` to add `agent_id`, `training_set_version_id`,
      `pid`, `source_experiment_id` columns (all nullable). Tracker
      row in stalite.db; ALTER targets runs_tracker.db per central-
      tracker pattern.
- [x] Append to stalite3's existing `training_run_tracker.py`:
  - `get_active_run()` — single-slot queue source of truth (TB-US-065)
  - `create_launched_run(...)` — insert `status='running'` with
    agent + training-set-version linkage before spawning train.py
  - `set_run_pid(run_id, pid)` (TB-US-065)
  - `startup_reconcile()` — flip stale 'running' rows on boot
  - `cancel_run(run_id, cancelled_by)` — SIGTERM then SIGKILL
  - `backfill_accuracy(run_id, experiment_id, accuracy)` — first-
    wins semantics (TB-US-091)
  - `backfill_accuracy_from_experiments(em, avm)` — one-off
    migration helper
- [x] `get_training_run()` surfaces the 4 new columns with
      defensive `in row.keys()` checks for back-compat.

## Acceptance Criteria

- [x] AC1: Migration idempotent.
- [x] AC2: All 7 new methods present on TrainingRunTracker.
- [x] AC3: Existing training-run flow untouched (create, update,
      list, compare all preserved).
