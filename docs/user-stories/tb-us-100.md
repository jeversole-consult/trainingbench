# TB-US-100: Port — harness_runner + admin_audit prereq to stalite3

**Status**: Completed 2026-11-07 — stalite3 commit `f2f5621`
**Depends on**: TB-US-098 (experiments pivot), TB-US-099 (backfill_accuracy)
**Blocks**: endpoint-wiring port stories; actual experiment runs
on stalite3

## Scope

- [x] Migration `stalite-05-admin-audit`: creates `admin_audit`
      table in stalite3's users.db (minimal subset of TB-US-017;
      full user-management v2 CRUD deferred). Tracker in stalite.db.
- [x] Append `UserManager.append_audit()` — best-effort audit
      write. Ported verbatim from TB-US-017.
- [x] Port `backend/api/harness_runner.py` verbatim. Includes:
      - TB-US-092 Phase 1 chat-template fix (detects Instruct
        variants via tokenizer.chat_template; applies
        apply_chat_template with add_generation_prompt=True)
      - TB-US-092 stop-token-ids fix (<|eot_id|> + eos) for
        performance
      - TB-US-091 backfill hook post-save_results
      - TB-US-070 progress-heartbeat callback (progress_json)
      - Stack summary carries `prompting_mode` + `source` for
        auditability on the compare modal

## Acceptance Criteria

- [x] AC1: Migration idempotent; audit table created in users.db.
- [x] AC2: `append_audit()` writes to admin_audit successfully.
- [x] AC3: `harness_runner.run_experiment` + `_build_experiment_stack`
      import cleanly.
- [x] AC4: Full boot chain applies all 5 stalite migrations
      without error.

## Not in scope

- `/experiments/{id}/run` endpoint wire-up
- Harness module files (`backend/harnesses/*`)
- Subprocess-per-experiment runner pattern (defer until operator
  wants actual stalite experiments)
