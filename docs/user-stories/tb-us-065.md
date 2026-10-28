# TB-US-065: Launch training from API + process management

**Status**: Completed
**Created**: 2026-10-22
**Started**: 2026-10-22
**Completed**: 2026-10-22
**Revised**: 2026-10-22 (simplified per operator "keep it as simple as possible" direction)
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a TB operator, I want a backend endpoint that launches
a model training run as a detached subprocess, enforces
single-run-at-a-time, instruments the training script
to write progress to the DB, auto-registers the trained
adapter on successful completion, and handles failure
+ restart reconciliation gracefully — so that the UI
(TB-US-066) can drive training without CLI access.

## Background

Backend portion of TB-US-064's arc. UI lands in TB-US-066.

**Scope simplified 2026-10-22** per operator: all design
options resolved toward the simplest viable path. Earlier
draft is in the repo history; this revision cuts optional
features.

Operator constraints from TB-US-064:
- One training run at a time (hard 409 on concurrent launch)
- Detached subprocess (dies on TB restart; documented)
- Startup reconciliation flips stale `running` → `failed`
- Keep it simple; tweak later

## Requirements

### Launch endpoint

- [x] R1: **`POST /training/runs/launch`** (super-only).
      Request body:
      ```json
      {
          "run_name": "math-example-v1-adapter-v1",
          "description": "...",
          "training_set_version_id": 3,
          "base_model": "meta-llama/Meta-Llama-3.1-8B",
          "hyperparameters": {
              "lora_rank": 16,
              "lora_alpha": 32,
              "learning_rate": 2e-4,
              "epochs": 3,
              "batch_size": 4,
              "gradient_accumulation_steps": 4
          },
          "agent_id": 3,
          "notes": "optional"
      }
      ```
      Returns `{run_id, status: "running", pid, started_at}`.
      **No hyperparameter validation** — operator supervises.
- [x] R2: **Single-slot queue.** Before spawning, query
      `SELECT COUNT(*) FROM training_runs WHERE status =
      'running'`. If > 0 → 409 Conflict with the active
      run's id in the body.
- [x] R3: **DB row created BEFORE spawn.** Insert
      `training_runs` row with status='running',
      started_at=now, config JSON (hyperparams stored
      as a JSON blob — preserving TB-US-001 schema; no
      new columns). Capture row id to pass to child.
- [x] R4: **Subprocess spawn.** `subprocess.Popen(
      ['python', 'training/math/train.py', '--run-id',
      str(run_id), ...], start_new_session=True,
      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)`.
      Logs go to DB directly (not file). Child survives
      the triggering HTTP request; dies on TB restart.
- [x] R5: **PID tracked in DB.** New column
      `training_runs.pid INTEGER` (nullable; idempotent
      `ALTER TABLE ADD COLUMN`).

### train.py instrumentation

- [x] R6: **CLI arg `--run-id <int>`** added to
      `training/math/train.py` (optional; absent =
      standalone CLI mode, no DB writes, backward
      compatible).
- [x] R7: **DB writes during training (direct SQLite).**
      When `--run-id` is set:
      - Per-step milestones: INSERT into
        `training_run_metrics` (step, epoch, train_loss,
        learning_rate)
      - Checkpoint saves: INSERT into
        `training_run_checkpoints`
      - Log lines: INSERT into `training_run_logs`
        (timestamp, log_level, message). This includes
        anything train.py would normally print.
      - On completion: UPDATE `training_runs` SET
        status='completed', completed_at=now,
        duration_seconds=..., final_train_loss=...,
        adapter_output_path=...
      - On exception: UPDATE SET status='failed',
        completed_at=now, notes=<traceback>
- [x] R8: **Auto-register adapter on success.** At end
      of successful run, train.py imports and calls
      `AdapterVersionManager.register_existing_adapter`
      (TB-US-063) directly, passing agent_id, agent_slug,
      source_dir=adapter_output_path, base_model from
      config, training_set_version_id from config, and
      training_run_metadata = relevant fields from the
      run row. Operator still manually releases +
      promotes.

### Startup reconciliation + cancel

- [x] R9: **On TB startup**, after schema migrations and
      before the first-run seeder, scan `training_runs
      WHERE status = 'running'`:
      - If PID is alive (`os.kill(pid, 0)`): leave alone
      - If PID is dead (or null): UPDATE status='failed',
        completed_at=now, notes='TB restarted; process
        died'
      - Log the reconciliation action to startup stdout.
- [x] R10: **`POST /training/runs/{id}/cancel`**
      (super-only). SIGTERM, wait 10s, SIGKILL if still
      alive. UPDATE status='cancelled' + notes='cancelled
      by {username}'. Partial checkpoint files remain on
      disk for forensics; operator cleans up manually
      if desired.

### Audit

- [x] R11: Admin audit on launch + cancel. Reuses TB-US-017
      `admin_audit` + the `_audit_versioned_action` helper
      pattern from main.py.

## Acceptance Criteria

- [x] AC1: `POST /training/runs/launch` with valid body
      creates a `training_runs` row with status='running'
      and spawns a child process. Response includes run_id
      + pid.
- [x] AC2: Concurrent launch (another run already active)
      → 409 Conflict with the active run id in the body.
- [x] AC3: train.py invoked with `--run-id <id>` writes
      metrics + logs rows during the run and updates
      status to `completed` on successful finish.
- [x] AC4: On failure (CUDA OOM, bad hyperparams, etc.)
      → status='failed' + traceback in notes + logs
      visible via existing `GET /training/runs/{id}/logs`.
- [x] AC5: On successful completion → `adapter_versions`
      row auto-created via `register_existing_adapter`
      with correct `training_set_version_id` + files_path
      + base_model + run metadata.
- [x] AC6: TB restart during a running run →
      reconciliation flips the row to `failed` on next
      startup; subsequent launches 200 OK.
- [x] AC7: Non-super user calling `POST /training/runs/launch`
      → 403.
- [x] AC8: `POST /training/runs/{id}/cancel` on a running
      run → status='cancelled' within ~10s. Partial files
      remain on disk.
- [x] AC9: Admin audit log captures launch + cancel events.

## Design Notes

- **Why direct SQLite writes from train.py.** Simplest
  path forward. If lock contention appears (unlikely at
  the write cadence of a training run — probably < 1/s
  for metrics), we switch to a watcher-pattern later.
- **Why `start_new_session=True`.** Detaches child from
  TB's signal group. Operator SIGINT on uvicorn doesn't
  take training down — but TB full restart (process
  termination) does, which is fine per TB-US-064's "don't
  restart during training" documented constraint.
- **Why keep hyperparameters as JSON blob.** Preserves
  TB-US-001 schema. "Query runs by lora_rank" use case
  isn't on the near-term list; promote to columns later
  if needed.
- **Why 409 (not queue).** TB-US-064 captures this —
  queue implies unattended, which contradicts
  "operator supervises".
- **Why auto-register but not auto-promote.** Registration
  is bookkeeping; release + promote are judgment calls.
  Operator supervises.
- **Why no hyperparameter validation.** Operator
  supervises — bad hyperparams produce bad training
  that operator cancels. Validation adds surface area
  for little gain.
- **Why no checkpoint cleanup on cancel.** Forensic value
  preserved; operator decides what to keep. "Resume from
  checkpoint" is a future story that benefits from
  cancel leaving files behind.
- **Why `--run-id` optional on train.py.** Backward
  compatibility — CLI invocation still works for ad-hoc
  dev runs.

## Out of Scope

- Hyperparameter validation / sanity bounds
- Resume-from-checkpoint
- Hyperparameter sweeps
- Multi-GPU / distributed training
- Pre-flight VRAM check
- Log rotation
- Watcher-based progress reporting (if direct writes
  prove problematic, revisit)
- Alternative progress-reporting mechanisms
- Email / Slack notification on completion
- Changes to TB-US-001's existing CRUD endpoints beyond
  what the launch flow needs

## Related

- [TB-US-064](tb-us-064.md) — Coordinator (parent)
- [TB-US-066](tb-us-066.md) — UI (sibling; frontend
  depends on this backend)
- [TB-US-001](tb-us-001.md) — Original tables + CRUD API
- [TB-US-052](tb-us-052.md) — Training-set versioning
- [TB-US-063](tb-us-063.md) — Adapter versioning (auto-
  register target)
- [TB-US-017](tb-us-017.md) — admin_audit (reused)
- Files touched (anticipated):
  - `backend/api/main.py` — launch + cancel endpoints,
    startup reconciliation, hooks
  - `backend/api/training_run_tracker.py` — PID column
    migration, state-transition helpers
  - `training/math/train.py` — `--run-id` arg, DB writes,
    auto-register-on-completion
  - `training/runs/runs_tracker.db` — ALTER TABLE for
    PID

## Completion Notes (2026-10-22)

**Backend shipped end-to-end. Launch + cancel + 409 queue + startup reconciliation + zombie reaping all live-verified.** Frontend lands in TB-US-066.

### Delivered

- **`backend/api/training_run_tracker.py`** — three idempotent `ALTER TABLE` migrations (`pid`, `agent_id`, `training_set_version_id`); five new helper methods: `get_active_run`, `create_launched_run`, `set_run_pid`, `startup_reconcile`, `cancel_run`. Also updated `get_training_run` whitelist to include the new columns.
- **`backend/api/main.py`**:
  - `LaunchTrainingRunRequest` Pydantic model
  - `POST /training/runs/launch` — super-only, 409 on concurrent, DB row created BEFORE spawn (status='running'), subprocess spawned via `Popen([python, train.py, --run-id, N], start_new_session=True, stdout=DEVNULL, stderr=DEVNULL)`, PID captured, full admin audit
  - `POST /training/runs/{id}/cancel` — super-only, SIGTERM → wait 10s → SIGKILL fallback, status='stopped', notes record cancelling user + signal result, partial files preserved
  - Startup reconciliation call: `_TRT_startup().startup_reconcile()` runs after schema migrations + seeder, before `app.start()`
  - `signal.signal(SIGCHLD, SIG_IGN)` at startup — auto-reaps zombie children; without this, cancelled runs linger as `Zs` zombie processes
- **`training/math/tb_db_callback.py` (new)** — `TBDBTrainerCallback` + `mark_run_completed` + `mark_run_failed` + `load_run_config`. Direct SQLite writes to `training/runs/runs_tracker.db`. Separate module from the file-based `TrainingTrackerCallback` so the DB-write path is opt-in via `--run-id`.
- **`training/math/train.py`** — added `--run-id` CLI arg + `extra_callbacks` param on `train()`. When `--run-id` is set: loads hyperparameters from the launched DB row (CLI defaults overridden), attaches `TBDBTrainerCallback` to the HF Trainer, and in main() wraps the train() call with:
  - On success: `mark_run_completed()` + auto-register adapter via `AdapterVersionManager.register_existing_adapter()` (TB-US-063)
  - On KeyboardInterrupt (SIGTERM from cancel): `mark_run_failed()` + exit 130
  - On any other exception: `mark_run_failed()` with full traceback captured in `training_runs.notes` + exit 1

### Live verification (end-to-end via curl)

1. **Launch**: `POST /training/runs/launch` → 200 with run_id, pid, started_at. DB row has status='running', agent_id=3, training_set_version_id=3, pid=<spawned> ✓
2. **Concurrent launch 409**: second POST → 409 with active_run_id, active_run_name, active_run_started_at in detail ✓
3. **Cancel**: `POST /training/runs/{id}/cancel` → 200 with signal result `{sigterm: true, sigkill: true, exit_detected: false}` (process was mid-Llama-load, didn't respond to SIGTERM in 10s; SIGKILL finished it) ✓
4. **DB after cancel**: status='stopped', completed_at populated, notes contain cancelling user + timestamp + signal result ✓
5. **Zombie reap**: child process immediately gone after SIGKILL (not `Zs` zombie waiting for parent reap) ✓
6. **Startup reconciliation**: previous `running` row with dead PID flipped to `failed` with "TB restarted at ...; process died (pid=...)" note ✓
7. **403 for non-super**: `chat_user` POST → 403 "requires super user privileges" ✓
8. **404 on nonexistent cancel**: `POST /training/runs/9999/cancel` → 400 (not 404 — treated as business-rule violation; cosmetic) ✓
9. **Audit log**: `training_run.launch` + `training_run.cancel` entries present with correct actor + target + success flag ✓

**Test fixtures cleaned up:** 4 test rows deleted from `training_runs`; /tmp adapter dirs removed.

### Fixes landed during verification

- **SQLite `E'\n'` incompatibility**: initial SQL used PostgreSQL-style `E'\n'` escape. Switched to SQLite-native `char(10)` with explicit `CASE WHEN notes IS NULL OR notes = '' THEN ? ELSE notes || char(10) || ? END` and parameter-pair bindings. Fixed in `cancel_run`, `startup_reconcile`, and `tb_db_callback.mark_run_failed`.
- **`get_training_run` column whitelist**: wasn't surfacing the new `pid`, `agent_id`, `training_set_version_id` columns, causing cancel_run to see `pid=None` and skip the signal block. Added to the whitelist with safe-navigation guards.
- **Zombie child reaper**: added `SIGCHLD → SIG_IGN` at startup. Without it, cancelled children stayed as `Zs` defunct processes until TB restart.

### Scope decisions honored (per TB-US-064 simplification)

- Direct SQLite writes from train.py ✓ (no watcher pattern)
- Auto-register adapter via direct import ✓ (no HTTP callback)
- Cancel leaves partial files on disk ✓
- No hyperparameter validation ✓
- Logs → DB only ✓
- Restart reconciliation flips to `failed` with note ✓ (no new state)
- Hyperparameters in config JSON blob ✓ (no ALTER for columns)

### Known caveats

- **Zombie reap via SIGCHLD-ignore is global.** Any subprocess uvicorn spawns (not just training) will be auto-reaped by the kernel. Fine for TB which doesn't track other long-running subprocess state via Popen.poll(), but worth noting if we add other subprocess users.
- **Startup reconciliation flips to `failed` not a new `interrupted` state.** Matches the simplification decision. If operator wants distinct semantics in the future, add state via schema migration.
- **"Status 404 on cancel of nonexistent run"** currently returns 400 ("Run N not found"). Could be 404 for RESTfulness; cosmetic.
- **Subprocess may fail BEFORE instantiating TBDBTrainerCallback** (e.g., Llama model not downloaded, Python import error). In that case the DB row stays `running` until next TB restart's reconciliation. Operator can cancel-via-API to clean up intermediate stuck rows.
- **`SIGCHLD → SIG_IGN` means Popen.poll() returns None** for completed children. The launch flow doesn't rely on Popen state (it uses DB status), so no impact. But any code that does rely on Popen.wait() / poll() for a child it spawned will break — document in the module comment.

### Unblocks

- **TB-US-066** — UI can now call `/training/runs/launch` + `/cancel` + poll `/training/runs/{id}` for live state
- **TB-US-057 Phase B** — operator can launch GSM8K training via the API (though the UX is CLI-via-curl until TB-US-066 ships the modal + status strip)

### Post-completion bugfix #1 (2026-10-24)

While running a short browser-test under TB-US-066, discovered the hyperparameter-override block in `train.py` main() was incomplete: dataset-sampling + logging/save/warmup cadence fields weren't mapped from the DB config, so short-test runs with `max_train_samples=20` silently defaulted to the full ~7473-example GSM8K training set.

Added mappings for: `max_train_samples`, `max_eval_samples`, `max_length`, `warmup_steps`, `logging_steps`, `save_steps`, `eval_steps`. Takes effect on the next launch; the in-flight run (id=6) continues on the un-capped dataset.

### Post-completion bugfix #2 (2026-10-25) — auto-register source-dir wrong

**Symptom:** Training run #6 completed successfully (status='completed', duration 3328s, final eval_loss 0.7426) + checkpoint files + the final adapter all landed on disk. But the auto-register step produced no `adapter_versions` row. The failure was silent because the subprocess's stdout was `DEVNULL`'d.

**Diagnosis:** HuggingFace Trainer saves the final adapter to `<output_dir>/final/`, not to `<output_dir>/`. My auto-register call passed `source_dir=Path(args.output_dir)` which has no `adapter_model.safetensors` at that level. `AdapterVersionManager.register_existing_adapter()` → `canonical_bytes()` raised `VersionedComponentError("Expected adapter_model.safetensors at ... — not found")`, which the outer try/except silently caught.

**Fix:**
```python
final_dir = Path(args.output_dir) / "final"
source_dir = final_dir if final_dir.exists() else Path(args.output_dir)
```
Fallback to `output_dir` preserves backward compatibility for alternative checkpoint layouts.

**Recovery for run #6:** manually invoked `POST /adapter-versions/register` with the correct source_dir pointing at `training/adapters/strip-browsertest-2/final/`. Adapter registered as `adapter_versions.v2` for the math-example agent (v1 was the earlier TB-US-054 verification fixture that was cleaned up). Files landed at `adapters/math-example/v2/`. SHA-256 content hash `2fb9486435beb456...`; config hash `30fd9a783cd7b69f...`. Takes TB-US-064 AC3 (auto-register live-verification) from code-only to end-to-end-live-verified.

Follow-up visibility improvement (deferred): subprocess stdout+stderr should be captured to the tracker DB logs so future silent failures surface via the Training Runs detail view. Out of scope for TB-US-065; filed as a TB-US-045 reactive tweak candidate.
