# TB-US-098: Port — experiments pivot table + `experiment_manager` to stalite3

**Status**: Completed 2026-11-07 — stalite3 commit `8694148`
**Depends on**: TB-US-094, TB-US-096, TB-US-097
**Blocks**: TB-US-099 (training_run_tracker extensions) + TB-US-100
(harness_runner port — needs both 098 and 099 complete)

## Scope

- [x] Add `migrate_experiments_table()` to
      `backend/api/schema_migrations.py`. Migration tracker ID:
      `stalite-03-experiments-table`. CREATE TABLE includes
      `started_at` + `progress_json` columns from day one (TB
      added these via TB-US-070 follow-up migration; stalite3
      ships without the drift).
- [x] Port `backend/api/experiment_manager.py` verbatim from
      TB-US-056 with `DEFAULT_DB_PATH` adjusted to
      `backend/db/stalite.db`. Includes TB-US-070's
      `update_progress()` method.
- [x] Wire migration into main.py boot.

### Not in scope

- `harness_runner.py` — depends on training_run_tracker extensions
  (TB-US-099). Port harness_runner in TB-US-100 once both
  prerequisites are in place.

## Acceptance Criteria

- [x] AC1: `experiments` table exists after boot.
- [x] AC2: `ExperimentManager` imports + queries cleanly.
- [x] AC3: Migration idempotent.
- [x] AC4: stalite3 existing functionality unchanged.
