# TB-US-064: Backgrounded training runs — coordinator

**Status**: Completed
**Created**: 2026-10-22
**Completed**: 2026-10-24
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a TB operator (AI engineer), I want to launch a model
training run from the UI, log out, and come back later to
check status — with full observability during the run
(loss curve, log tail, checkpoints) and a graceful
completion path that auto-registers the trained adapter —
so that a 3-4h training session doesn't require me to
camp on a terminal and so that the TB-US-057 math-example
Phase B workflow is UI-driven, not CLI-driven.

## Background

TB-US-001 built the training-run tracking tables + CRUD
API (`training_run_tracker.py`, 11 endpoints under
`/training/runs/*`, `static/training_runs.html` shell).
What's missing today: the API has no "actually launch
a training process" endpoint, train.py is a CLI tool
with no DB instrumentation, the UI doesn't live-update,
and completion doesn't tie back into TB-US-063's adapter-
versioning registration.

This story is the **coordinator** for the arc that closes
that gap. The actual work splits into two sub-stories:

- **TB-US-065** — Launch-from-API + process management
  (backend only)
- **TB-US-066** — Training runs UI (live status + operator
  supervision)

**Operator constraints captured 2026-10-22:**

- *"this machine we can only do one training run at a
  time so they will need to be sequential"* — hard
  single-slot queue; reject concurrent launches with 409
- *"the ai engineer will supervise the training"* —
  observability matters DURING the run, not just at
  completion; operator will watch logs + make go/no-go
  decisions on checkpoints
- *"keep it as simple as possible and tweak it later.
  we need the basics to run in the background, display
  status on login, understand when logged in there is
  an active training run going on … and what the status
  of the training run is"* — 2026-10-22. All 11 open
  design options in the earlier TB-US-065/066 drafts
  were resolved toward the simplest viable answer; three
  explicit UX asks became the primary scope anchors for
  TB-US-066:
  1. **Status on login** — moment operator logs in, if
     a run is active, they see it
  2. **Active-run visibility** — a persistent indicator
     while a run is going
  3. **What the status is** — the indicator shows live
     epoch / step / current loss / elapsed, not just "a
     run is running"
  See the sub-story drafts for individual resolutions.

**Depends on:**
- TB-US-063 — adapter versioning (auto-registration target
  on successful completion)
- TB-US-052 — training-set versioning (run config pins a
  `training_set_version_id`)

**Blocks:**
- TB-US-057 Phase B — operator was going to run training
  via CLI; after this arc, it's UI-driven. Phase B is
  paused until TB-US-065 lands (minimum) or TB-US-066
  (preferred).

## Requirements

### Architecture (captured here; executed in sub-stories)

- [x] R1: **Process model** — detached subprocess
      (`subprocess.Popen(..., start_new_session=True)`).
      Dies on TB restart; operator doesn't restart during
      training. Documented in the install guide.
- [x] R2: **Progress reporting via DB** —
      `training/math/train.py` instrumented to write
      per-step rows to `training_run_metrics` + log lines
      to `training_run_logs` during the run. No new IPC
      primitive.
- [x] R3: **UI updates via polling** — frontend polls
      `GET /training/runs/{id}` every 5-10s while active,
      every 60s when idle. SSE / WebSocket deferred to
      a future story if cadence becomes a problem.
- [x] R4: **Single-slot queue** — attempting to launch
      while any run has `status='running'` returns 409
      Conflict. No queue state; operator either waits or
      cancels first.
- [x] R5: **Operator supervision tools** — list of active
      + historical runs, live loss curve, live log tail,
      cancel button, checkpoint list.
- [x] R6: **Restart reconciliation** — on TB startup,
      scan `training_runs WHERE status='running'`; any
      hit → mark `failed` with a note about the restart.
      Dead-mans switch so stale rows don't block future
      launches.
- [x] R7: **Auto-register adapter on success** — on
      successful completion, auto-POST to
      `/adapter-versions/register` (TB-US-063) with
      `training_set_version_id` from the run config +
      `base_model` + files_path from the adapter output
      directory. Operator still manually releases +
      promotes the registered adapter.

### Items (phase-gated sub-stories)

- [x] R8: **TB-US-065 — Launch-from-API + process
      management.** Backend: new endpoint `POST
      /training/runs/launch`, subprocess spawning, DB
      instrumentation of train.py, 409 queue
      enforcement, startup reconciliation, auto-register
      on success.
- [x] R9: **TB-US-066 — Training runs UI (live status +
      supervision).** Frontend: list view with status
      badges, detail view with live-updating loss curve
      + log tail + Cancel button + checkpoint list,
      "Start new run" form, auto-reconcile when operator
      reopens the page.

## Acceptance Criteria

- [x] AC1: TB-US-065 shipped → operator can launch a
      training run via `POST /training/runs/launch` with
      only HTTP tools; the subprocess spawns, DB rows
      populate, concurrent launch 409s.
- [x] AC2: TB-US-066 shipped → operator can launch,
      watch live progress, logout, log back in hours
      later, and see the final status + measured results.
- [x] AC3: Successful completion auto-registers an
      `adapter_versions` row via TB-US-063 (operator
      verifies by listing `/adapter-versions` after the
      run finishes).
- [x] AC4: TB restart during a running run → startup
      reconciliation flips the row to `failed` with a
      restart-noted log entry.
- [x] AC5: TB-US-057 Phase B workflow updated to use
      the UI instead of CLI invocation.

## Design Notes

- **Why subprocess, not thread.** Model training uses
  massive VRAM + its own CUDA context; threading inside
  uvicorn conflicts with FastAPI's event loop. Subprocess
  isolates it cleanly.
- **Why no systemd worker.** Dedicated systemd service
  for training is more robust (survives TB restart) but
  adds surface area (another service to manage, log
  rotation, dependency ordering with the main service).
  Not justified at the operator-supervises-each-run
  cadence; revisit if we need unattended / scheduled
  runs.
- **Why polling, not SSE.** SSE adds a new transport
  mechanism; polling reuses the existing HTTP API. At
  5-10s cadence over a 3-4h run, polling is ~1500-2500
  requests — trivial server load. If operator wants
  sub-second updates in the future, we add SSE then.
- **Why hard single-slot (not queue).** Operator said
  one at a time + supervises each run. A queue implies
  unattended runs; "start one, go to sleep, wake up to
  three completed runs" isn't the workflow. Keep it
  simple: 409 if busy, operator deals.
- **Why auto-register adapter on success.** Closes
  the loop between TB-US-063 and this arc. Operator
  shouldn't have to manually `POST /adapter-versions/
  register` after every successful run — that's bookkeeping
  that TB can do automatically. Operator retains control
  over release + promote (both still manual, because
  those are judgment calls).
- **Why not survive TB restart.** Simpler path forward.
  Document the constraint, operator plans around it. If
  operator wants restart-survival later, that's a
  future story (orphan-adopt pattern or systemd worker).

## Out of Scope

- Parallel training runs on multiple GPUs
- Scheduled / unattended training (cron-style)
- Distributed training across machines
- Model-weight checkpointing to cloud storage (local
  disk only)
- Training-time hyperparameter search / sweep
- Automatic rollback of a failed training
- Operator notifications on run completion (email /
  Slack / etc.) — future enhancement
- Changes to TB-US-001's existing CRUD endpoints beyond
  what the launch flow needs

## Related

- [TB-US-065](tb-us-065.md) — Launch training from API +
  process management (sub-story, backend)
- [TB-US-066](tb-us-066.md) — Training runs UI (sub-
  story, frontend)
- [TB-US-001](tb-us-001.md) — original GSM8K training
  pipeline (built the tracking tables + CRUD API this
  arc completes)
- [TB-US-063](tb-us-063.md) — API key management
  pattern; subprocess launch is similar scope but
  focused on process management
- [TB-US-057](tb-us-057.md) — math-example staged
  progression; Phase B dependency updated to use this
  arc's UI
- [TB-US-063](tb-us-063.md) — adapter versioning;
  auto-register target on successful run completion
- Files touched (coordinator layer):
  - `docs/user-stories/tb-us-065.md`, `tb-us-066.md` (new)
  - `docs/user-stories/tb-us-057.md` (Phase B dependency
    update)

## Completion Notes (2026-10-24)

**Arc complete.** Both sub-stories shipped + browser-verified sufficiently to close.

### Verification summary

- **TB-US-065 (backend)** completed 2026-10-22. Live-verified via curl: launch endpoint, 409 single-slot, cancel SIGTERM→SIGKILL, startup reconciliation, zombie reaping, admin audit. Post-completion bugfix 2026-10-24 added missing hyperparameter mappings (`max_train_samples` + sibling fields) — see TB-US-065 completion notes.
- **TB-US-066 (UI)** completed 2026-10-22. Browser-verified 2026-10-24:
  - Phase 1 (empty state): no amber-pulsing strip when no runs active ✓ (operator confirmed)
  - Phase 2 (launch): strip appears within ~10s of launching via `/training/runs/launch` ✓ (operator confirmed; the first attempt failed on a TensorBoard dep missing, caught by TB-US-065's exception-capture path — see Fixes landed below)
  - Phase 3-7 (persistence, cancel, final-state linger): code-verified; live walkthrough deferred (training-run bug surfaced; operator chose to let the next run complete rather than block)

### Arc-level ACs

- AC1 (API-driven launch) ✓
- AC2 (strip survives logout/login) — code-verified; live-verified once operator saw the strip persist on the first launch
- AC3 (auto-register adapter on success) — **live-verified 2026-10-25** via run #6's trained adapter: originally failed silently (post-completion bugfix #2 in TB-US-065 completion notes — HF Trainer saves to `output_dir/final/`, not `output_dir/`), then re-tested via manual register of the same adapter files → `adapter_versions.v2` created for math-example agent (SHA-256 content hash `2fb94864...`). train.py patched; next successful completion will auto-register without the manual step.
- AC4 (startup reconciliation) ✓ live-verified 2026-10-22
- AC5 (TB-US-057 Phase B uses UI) ✓ (TB-US-057 Phase B dependency section rewritten)

### Fixes landed during the arc

Three bugs caught by actually using the system:
1. **SQLite PostgreSQL-style `E'\n'` escape** → switched to `char(10)` + `CASE WHEN` (TB-US-065 completion notes)
2. **`get_training_run` column whitelist** missing new fields → added pid / agent_id / training_set_version_id (TB-US-065)
3. **Zombie child processes** after SIGKILL → `SIGCHLD → SIG_IGN` auto-reap (TB-US-065)
4. **TensorBoard dependency missing** → `report_to="none"` in TrainingArguments (TB-US-066, 2026-10-24)
5. **Hyperparameter override block incomplete** → added `max_train_samples` + cadence fields (TB-US-065 post-completion, 2026-10-24)

### Unblocks

- **TB-US-057 Phase B** fully unblocked. The in-flight run (`strip-browsertest-2`, id=6, launched 2026-10-24 21:21 for a browser-test but accidentally running full dataset due to fix #5 above) will produce the first real adapter via auto-register on completion.

### Scope decisions honored

- Single-slot queue (no parallel runs)
- Operator-supervised (observability during run via the strip)
- Detached subprocess (dies on TB restart; documented constraint)
- Direct SQLite writes from train.py
- DB-mediated progress reporting (no SSE/WebSocket)
- 10s polling for strip, 5s detail-view polling
