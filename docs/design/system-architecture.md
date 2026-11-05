# TrainingBench — System Architecture

**Target reader**: operator-maintainer, first-time contributor, or
publication reviewer wanting to know "what IS this system" without
reading the full codebase.

**Scope**: components, request flows, state, auth, process boundaries,
and where to look when something breaks. For sub-system specifics see
[`agent-architecture.md`](agent-architecture.md) and
[`sweet-spot-architecture.md`](sweet-spot-architecture.md). For
operational workflows see
[`maintenance-fix-workflow.md`](../training/maintenance-fix-workflow.md)
and [`upgrade-publishing-workflow.md`](../training/upgrade-publishing-workflow.md).

## 1. The system at a glance

```
┌─────────────────────┐             ┌────────────────────────┐
│  Browser            │             │  Research scripts       │
│  (operator, SSH/VPN)│             │  (automation, CLI)      │
└─────────┬───────────┘             └────────────┬────────────┘
          │                                       │
          │ HTTPS + session token                 │ HTTPS + session token (today;
          │ (via /auth/login)                     │  API keys planned)
          │                                       │
          ▼                                       ▼
    ┌────────────────────────────────────────────────────────────┐
    │           FastAPI backend server (port 8002, uvicorn)       │
    │                                                             │
    │  • HTTP API: /auth, /agents, /experiments,                 │
    │    /training/runs/launch, /training-set-versions,          │
    │    /adapter-versions, /query, /admin/*, ...                │
    │  • Auth middleware: verify_super_user / verify_chat / ...  │
    │  • Harness runner (inference) runs as background tasks     │
    │  • ALSO serves the Web UI static files from static/        │
    └───┬──────────────────────────────┬───────────────────┬────┘
        │ spawn (Popen, detached)      │ read/write        │ serve
        ▼                              ▼                   ▼
  ┌─────────────────┐          ┌──────────────────┐  ┌──────────────┐
  │ Training        │          │ SQLite databases │  │ static/*.html │
  │ subprocess      │          │  • users.db       │  │ static/*.js   │
  │ (train.py       │          │  • sessions.db    │  │ static/*.css  │
  │  --run-id N)    │          │  • backend/db/    │  └──────────────┘
  │                 │          │    trainingbench  │
  │ GPU inference,  │          │    .db (versioning│
  │ writes progress │          │    + experiments) │
  │ directly to     │          │  • training/runs/ │
  │ tracker DB      │          │    runs_tracker.db│
  └────┬────────────┘          └──────────────────┘
       │ reads sidecar JSONL
       ▼
  ┌────────────────────┐                          ┌──────────────┐
  │ training-set       │   ◀─── registered via API│ Adapter files │
  │ sidecar files      │                          │ adapters/<agent>/v*/
  │ training/datasets/ │                          │  (LoRA        │
  │   training_set_    │                          │   artifacts)  │
  │   versions/v*.jsonl│                          └──────────────┘
  └────────────────────┘
```

### Components in words

- **Browser (Web UI client).** Runs on the operator's laptop; reaches
  the backend through an SSH tunnel or VPN. Loads static HTML/JS/CSS
  served by the backend. Everything a user clicks hits an HTTP API
  endpoint.
- **Static files (`static/`).** Just files on disk at the backend;
  served as plain static by FastAPI. The Web UI is a thin client —
  it has no state of its own beyond the session token.
- **FastAPI backend server.** The single long-lived process at
  port 8002 (uvicorn). The authoritative service. Handles auth,
  enforces role permissions, orchestrates training launches, runs
  inference, reads/writes all SQLite databases, and serves the Web
  UI files. Everything else talks to this.
- **HTTP API.** The set of endpoints the backend exposes. The Web
  UI and research scripts both use the same API — it is the single
  seam between "outside world" and "TB internals." Grouped by
  concern: `/auth/*`, `/agents/*`, `/training-set-versions/*`,
  `/adapter-versions/*`, `/experiments/*`, `/training/runs/*`,
  `/query`, `/admin/*`.
- **Training subprocesses (`train.py`).** Spawned by the backend on
  `POST /training/runs/launch` via `subprocess.Popen(start_new_session=True)`.
  Each is a separate OS process that owns GPU memory during its run.
  Writes progress back to the tracker DB directly (bypasses the API).
  Exits when training completes. See TB-US-065 for the launch flow.
- **Harness runner.** Inference-time code inside the backend. When
  `POST /experiments/{id}/run` fires, the endpoint schedules a
  FastAPI `BackgroundTask` that loads model + adapter and iterates
  the harness's question set. Shares the backend process (not a
  separate subprocess). See TB-US-056, TB-US-069.
- **SQLite databases.** Authoritative state (see §3).
- **Research scripts.** CLI/Python automation — training-set prep,
  experiment orchestration, analysis. Lives in `scripts/`. Talks
  to TB through the same HTTP API as the Web UI does. Not a
  component of the server; a client of it.

## 2. Request flow walkthroughs

### Walkthrough A — "Operator clicks Launch Training in the UI"

1. Browser submits a form at `/training/runs/launch` with `agent_id`,
   `training_set_version_id`, base model, hyperparameters. Sends
   the session token in `Authorization: Bearer ...`.
2. Backend's `verify_super_user` middleware validates the token.
3. Endpoint resolves `training_set_version_id` → sidecar JSONL path
   via `TrainingSetVersionManager.sidecar_path()`. Returns 400 if
   the sidecar is missing.
4. Endpoint writes a new row to `training_runs` (status=`running`,
   with `training_set_version_id`, hyperparameters, timestamps).
5. Endpoint spawns `train.py --run-id <row.id>` as a detached
   subprocess via `Popen(start_new_session=True)`.
6. Endpoint returns the run_id + PID to the browser. The browser
   now knows the training is started; it does NOT wait for completion.
7. The training subprocess reads config from the DB row (hyperparameters,
   base model, training_set_jsonl path), loads the sidecar JSONL,
   loads the base model + applies QLoRA, and starts training.
   `TBDBTrainerCallback` writes per-step metrics to
   `training_run_metrics` as training proceeds.
8. On completion, `train.py`:
   - Updates `training_runs.status = 'completed'`.
   - Auto-registers the adapter via `AdapterVersionManager`
     (writes a row to `adapter_versions` with `training_set_version_id`
     provenance linkage).
   - Exits.
9. The Web UI polls `/training/runs/{id}` for status (TB-US-066
   active-run strip updates live).

### Walkthrough B — "Operator runs an experiment to measure accuracy"

1. Browser submits `POST /experiments/{id}/run` with the experiment
   already created (containing pinned adapter + harness + prompt
   + LLM identifier).
2. Backend validates auth, transitions the experiment state
   draft → running.
3. Endpoint schedules a FastAPI `BackgroundTask` to call
   `_harness_runner.run_experiment(eid)`.
4. Endpoint immediately returns the experiment row to the browser.
5. The background task (same process, separate task):
   - Resolves the pinned stack: `adapter_version_id` → PEFT weights
     from `adapter_versions.files_path`; `rag_version_id` → VectorStore
     (if any); `system_prompt_version_id` → prompt text.
   - Loads the base model into GPU memory (via HF `transformers`
     pipeline).
   - Attaches the adapter via `PeftModel.from_pretrained`.
   - Iterates the harness's question list (e.g.,
     `math_eval_200_holdout.jsonl`), running `pipeline(...)` for
     each question.
   - Writes per-sample outputs + accuracy summary to
     `experiments.results_json`.
   - Transitions state → `completed`.
6. The Web UI's experiment-detail view polls `/experiments/{id}` to
   observe progress. When state flips to `completed`, results are
   rendered.

### Walkthrough C — "A research script runs 6 experiments overnight"

1. Script mints a session token by importing the backend auth helper
   directly (`generate_session_token`). **This is a current
   workaround for the lack of an API-key mechanism.**
2. For each of 6 experiments: script `POST /experiments` (create),
   then `POST /experiments/{id}/run` (launch background task).
3. Script polls experiment state — either by `GET /experiments/{id}`
   (token-authed, expires) or by reading the SQLite `experiments`
   table directly (no auth, no expiry).
4. Experiments run server-side regardless of whether the script is
   alive. If the script dies, in-flight experiments complete and
   writes land in the DB; only orchestration of the NEXT experiment
   is lost.

## 3. Where state lives

| Database | Path | Owns |
|---|---|---|
| `users.db` | `./users.db` | User accounts, password hashes, roles, admin audit log |
| `sessions.db` | `./sessions.db` | Active session tracking (TB-US-034) — when users log in, who's online |
| `trainingbench.db` | `backend/db/trainingbench.db` | **Versioning + experiments core**: `agents`, `training_set_versions`, `adapter_versions`, `rag_versions`, `prompt_versions`, `route_versions`, `harness_versions`, `agent_components` (which version is promoted per agent + component type), `experiments` |
| `runs_tracker.db` | `training/runs/runs_tracker.db` | Training-run lifecycle: `training_runs`, `training_run_metrics` (per-step loss, eval_loss, etc.) |
| `registry.db` | `training/datasets/registry.db` | Legacy training-set-manager registry (partial; superseded by `training_set_versions` in trainingbench.db) |

**File-level state** (not in DBs):
- `training-sets/*.jsonl` — operator-visible prep-script outputs
- `training/datasets/training_set_versions/v{N}.jsonl` — canonical
  sidecar files referenced by DB rows (TB-US-052)
- `adapters/<agent>/v{N}/` — LoRA weights + tokenizer artifacts
  for each adapter version
- `datasets/math/data/` — raw GSM8K (HuggingFace Datasets format)

**Invariant**: the backend is the authoritative writer to all SQLite
databases. Scripts that **read** the DBs directly are a convenience
shortcut (used by analysis scripts, orchestrators polling state).
Scripts that **write** to the DBs directly are a drift risk — the
invariants enforced by the backend (version-component relationships,
promotion state, audit logging) can be broken. Prefer the API for
writes.

## 4. Auth model

### Current (v0.1): session tokens only

- **How a user authenticates**: `POST /auth/login` with username +
  password. Backend hashes the password, compares, and on success
  returns a signed session token (via Python `itsdangerous`,
  `URLSafeTimedSerializer`).
- **How a token is used**: the client sends `Authorization: Bearer
  <token>` on every subsequent request. Backend verifies the
  signature + checks age via `max_age=86400` (24 hours, hardcoded).
- **What's in a token**: `{username, user_type, id}` — the user_type
  is one of `super`, `training`, `chat` (see
  `principle_role_names_describe_interface` memory for role
  semantics).
- **Who can call what**: role-based dependencies on endpoints.
  `verify_super_user` lets only super role through;
  `verify_chat_user` accepts any logged-in role, etc.

### API-key mechanism (correction, 2026-11-05)

**Earlier versions of this doc claimed TB had no API-key
mechanism. That was wrong.** TB ships a full API-key system via
TB-US-063 (closed 2026-10-22):
- `backend/api/api_key_manager.py` — `ApiKeyManager` class, keys
  stored in `users.db` with labels + revocation state
- Endpoints: `POST /api-keys` (create), `GET /api-keys` (list),
  `DELETE /api-keys/{id}` (revoke), `GET /api-keys/_whoami`
- UI: `static/api_key_management.js` modal, super-only, opens
  from the admin dropdown (per `feedback_admin_tier_drawer_footer`
  memory)
- Middleware: `verify_api_key` function (main.py:3347)
  authenticates via `Authorization: ApiKey <key>` header

**What the earlier doc was reacting to**: during the research
arc, scripts minted session tokens directly from the backend
Python module (`generate_session_token`) and hit the 24h expiry
mid-campaign (surfaced in TB-US-081 Trial #7). That workaround
**ignored the already-shipped API-key system** — scripts should
use API keys for automation, not session tokens.

The `feedback_research_infrastructure_resilience` memory is
still correct about the principle (research automation needs
long-lived credentials) but its proposed solution ("file a TB
story to add API keys") duplicates work that was already done.
Correct resolution: update research scripts to use API keys.

Discovered during TB-US-086 backend audit.

### Other identity notes

- **No password-recovery flow** in v0.1; operator resets by editing
  `users.db` directly.
- **Gate token** (separate concept) — some installs have a public
  "gate" (access-code) before the login page. Issued by
  `generate_gate_token`, separate from session tokens.
- **IAM foundation** — PM-US-004 drafts a long-term IAM design
  (CF Access, MFA, rate limiting). Independent of this doc.

## 5. Process boundaries

| Process | Count | What it owns | Lifetime |
|---|---|---|---|
| FastAPI server (uvicorn) | 1 | HTTP API, static file serving, harness-runner background tasks | Long-lived (systemd `trainingbench.service`) |
| Training subprocess (`train.py --run-id N`) | 0–1 at a time | One training run: QLoRA training on GPU; writes to tracker DB | 10 min to 4+ hours per run |
| Browser | 0+ | Web UI session | Interactive, session-length |
| Research scripts | 0+ | Automation orchestration | Minutes to multi-hour |

**Why training is a subprocess, not inline**: GPU-bound workloads
can hog Python's GIL and block the API server. Spawning a separate
process gives the training VRAM and compute isolation; the backend
stays responsive. `SIGCHLD → SIG_IGN` installed at server startup
auto-reaps completed training subprocesses so they don't become
zombies.

**Why harness runs inline (in the backend process)**: inference is
much shorter than training (minutes vs. hours), and FastAPI's
`BackgroundTasks` already runs it outside the request/response path.
Loading a model + adapter costs ~30-60 sec but PyTorch's CUDA
allocator caches freed memory, so a second experiment pinning the
same adapter reuses the warm allocator without a reload.

**Why one training subprocess at a time**: single-GPU host. The
`/training/runs/launch` endpoint enforces single-slot via
`get_active_run()` → 409 if another is running. For multi-GPU
installs, this would need lifting.

## 6. Debug / observe entry points

| Question | Where to look |
|---|---|
| Is the backend running? | `systemctl status trainingbench.service` |
| Backend errors / HTTP request log | `journalctl -u trainingbench.service -f` |
| Is a training run active? | `ps -ef \| grep train.py` or `GET /training/runs?status=running` |
| Training progress | `training_run_metrics` table in `runs_tracker.db` (step, epoch, train_loss, eval_loss) |
| Training completion status | `training_runs.status` ("running" / "completed" / "failed") |
| Experiment progress / results | `experiments.state` + `experiments.results_json` in `trainingbench.db` |
| Current promoted version per agent | `agent_components` table (`agent_id, component_type, version_id, promoted_at`) |
| Live GPU state | `nvidia-smi --query-gpu=memory.used,memory.free,utilization.gpu --format=csv` |
| Live VRAM held by TB | `nvidia-smi` — TB's FastAPI process is the one holding the inference model's memory between experiments |
| User sessions | `sessions.db` (TB-US-034 session_tracker) |
| Admin audit log | `admin_audit` table in `users.db` (TB-US-017) |
| Adapter files on disk | `adapters/<agent>/v{N}/adapter_model.safetensors` |
| Training-set sidecars | `training/datasets/training_set_versions/v{N}.jsonl` |

**Research-arc specific**: the methodology docs
(`docs/math-example/methodology.md`,
`docs/math-example/sweet-spot-search-log.md`) are the source of
truth for the math-example research campaign. Experiments
E1–E35+ map to the trial narrative there.

---

## Appendix — things deliberately NOT in this doc

- **Deployment / install guide** — lives in README.md + release
  docs.
- **API endpoint reference** — the backend exposes an OpenAPI
  spec at `GET /openapi.json`; a formal reference would be a
  separate story.
- **Database migration strategy** — lives in individual
  version-manager modules + the `schema_migrations` table.
- **Security audit / threat model** — the auth-model gap (no
  API keys) should be fixed before this is worth doing.
- **Multi-tenancy / scaling** — TB is single-operator per install;
  no plans to change in v0.1.
