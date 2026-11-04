# TB-US-083: System architecture documentation

**Status**: Completed
**Created**: 2026-11-03
**Started**: 2026-11-04
**Completed**: 2026-11-04
**Author**: Jesse Eversole
**Depends on**: Nothing (pure documentation; can land anytime)
**Commit hash(es)**: <filled in on closure commit>

## Story

As a TB operator-maintainer who occasionally has to debug an
unfamiliar part of the system, I want **a single short document
that lays out TB's component architecture** — what the pieces
are, how they fit together, where state lives, how auth works,
and where to look when something misbehaves — so that future-me
or any new contributor can orient in minutes rather than hours.

Surfaced during TB-US-081 conversation (2026-11-03) when operator
noted: "TB is more than just a web UI. it has a backend server.
the web ui talks to the backend server using an API. if that is
the architecture then it needs to be cleanly documented so that
the user understands what these components are, how they fit
together, and how they are maintained."

## Background — why this is missing today

Existing docs are either:
- **Sub-system design docs** (`docs/design/agent-architecture.md`,
  `docs/design/sweet-spot-architecture.md`) — deep but scoped to
  one area
- **Operational workflow docs** (`docs/training/maintenance-fix-
  workflow.md`, `docs/training/upgrade-publishing-workflow.md`) —
  describe tasks, not components
- **Research methodology** (`docs/math-example/methodology.md`,
  `docs/math-example/study-design.md`) — describe how we do
  science, not how the platform works

**Nothing** sits at the top level and answers the question
"what IS TrainingBench and how do its pieces fit?" A reader
currently has to clone the repo and read 50 files to build
that picture.

## Scope

Produce **one short architecture doc** at
`docs/design/system-architecture.md`. Target length 2-4 pages
(short enough to be read in one sitting; long enough to be
useful).

### Required contents

1. **System at a glance** — one component diagram (ASCII box
   diagram) + 1 paragraph per component describing what it
   owns, who talks to it, where it runs.

   Components to describe:
   - Browser (Web UI client)
   - Static files (`static/`) — served by backend
   - FastAPI backend server (port 8002, uvicorn)
   - The HTTP API (endpoint groups: auth, agents, training sets,
     adapters, experiments, training runs, admin)
   - Training subprocesses (`train.py`, GPU inference)
   - Harness runner (inference-time, inside backend)
   - SQLite databases (per-concern breakdown)
   - Research scripts (automation layer, separate from operator UI)

2. **Request flow walkthroughs** — at least 2 end-to-end
   traces of common operations:
   - "User clicks 'launch training' in the UI" → browser →
     POST `/training/runs/launch` → auth check → create DB row
     → spawn subprocess → return run_id → subprocess writes
     metrics back → auto-register adapter on completion
   - "User runs an experiment" → browser → POST `/experiments/{id}/run` →
     background task → harness runner loads model+adapter →
     iterates 200 samples → writes `per_sample` to `results_json` →
     state → `completed`
   - Optional 3rd: "A research script fires 6 experiments" —
     shows the automation-vs-browser distinction

3. **Where state lives** — table listing each SQLite database,
   its path, and which concern it owns:
   - `users.db` — user accounts, roles, audit log
   - `sessions.db` — active sessions (TB-US-034)
   - `backend/db/trainingbench.db` — versioning
     (training_set_versions, adapter_versions, rag_versions,
     prompt_versions, harness_versions, agent_components,
     experiments)
   - `training/runs/runs_tracker.db` — training_runs +
     training_run_metrics (TB-US-052/065)
   - `training/datasets/registry.db` — training-set-manager
     registry (legacy, partial)
   - Local file state: `training-sets/*.jsonl`,
     `training/datasets/training_set_versions/v*.jsonl`
     (sidecars), `adapters/<agent>/v*` (LoRA artifacts)

   Key invariant: the backend is the authoritative writer.
   Scripts that bypass the API to read DBs directly are
   read-only shortcuts; direct DB writes from scripts are a
   drift risk.

4. **Auth model** — current state + known gap:
   - Session tokens: issued at `/auth/login`, signed via
     `itsdangerous`, hardcoded 24h `max_age`, enforced in
     `verify_session_token`. Expected pattern: interactive
     browser user.
   - Role types: super, chat, training (see
     `principle_role_names_describe_interface` memory for
     nuance).
   - **Known gap**: no API-key mechanism for automation. Research
     scripts currently mint session tokens directly from the
     backend module — a hack that inherits the 24h expiry.
     Possible follow-up story (not required for this doc) would
     add an API-key credential type for automation.

5. **Process boundaries** — concrete answer to "what's in which
   OS process":
   - **1 FastAPI server process** (uvicorn, port 8002) — serves
     the API, serves static files, runs harness-runner background
     tasks for experiments. Long-lived.
   - **N training subprocesses** — spawned by `/training/runs/
     launch` via `subprocess.Popen(start_new_session=True)`. Each
     runs `train.py --run-id N`. Detached; writes directly to
     tracker DB. GPU memory owned by the subprocess during its
     lifetime.
   - **Browser** — remote; runs on operator's laptop.
   - Why the separation matters: training can be CPU/GPU-heavy
     without blocking API; `SIGCHLD → SIG_IGN` auto-reaps
     completed training subprocesses (TB-US-065).

6. **Debug / observe entry points** — "where do I look when X":
   - API-level errors → systemd journal (`journalctl -u
     trainingbench.service`)
   - Training progress → `training_run_metrics` table in
     `runs_tracker.db`
   - Experiment results + per-sample → `experiments.results_json`
     in `trainingbench.db`
   - Current demo state → `agent_components` table (which
     version of each component is promoted per agent)
   - Live training → `nvidia-smi` + `ps -ef | grep train.py`
   - Training completion → `training_runs.status` ("completed"
     / "failed")

### Not in scope

- IAM-foundation design (that's PM-US-004's scope — pre-existing
  separate story)
- API-key mechanism code changes (future TB-US-NNN; doc just
  acknowledges the gap)
- Multi-tenancy or scale concerns (TB is single-operator per
  install; call it out and move on)
- Database migration strategy (lives in individual version-manager
  docs)
- Specific API endpoint reference (that's for API docs / OpenAPI
  spec, a separate concern)

## Deliverables

- [ ] R1: `docs/design/system-architecture.md` — the primary
      doc (2-4 pages)
- [ ] R2: Cross-link from `docs/README.md` — add a
      "Start here" top-of-page pointer to the new architecture
      doc so new readers find it first
- [ ] R3: Cross-link from `CONTRIBUTING.md` — "read this before
      your first PR" mention
- [ ] R4: The doc includes ASCII component diagram (readable in
      a terminal; no reliance on graphics tools)

## Acceptance Criteria

- [ ] AC1: Architecture doc exists at
      `docs/design/system-architecture.md`, 2-4 pages
- [ ] AC2: All 6 required content sections present (system
      overview, request flows, state locations, auth, process
      boundaries, debug entry points)
- [ ] AC3: At least 2 end-to-end request-flow walkthroughs,
      each tracing an operation across the major components
- [ ] AC4: Table listing all SQLite databases with path + owned
      concern
- [ ] AC5: `docs/README.md` cross-links to the architecture doc
      at the top of its "Start here" section
- [ ] AC6: `CONTRIBUTING.md` points to the architecture doc
- [ ] AC7: A reader with no prior TB knowledge can describe,
      after reading only this doc, the five main components
      and how a training-launch request flows through them
      (self-check; no formal reviewer required for v0.1)

## Design Notes

- **Why 2-4 pages, not longer**: anything longer than ~4 pages
  stops getting re-read. The goal is an entry doc, not a
  reference manual. More-specific details belong in the
  sub-system design docs (which this doc should link to).
- **Why ASCII diagram, not graphical**: lives in git, versions
  cleanly, readable in any terminal or markdown viewer. If we
  ever want fancy rendering later, Mermaid is a drop-in option
  without changing the content.
- **Why include the auth-model gap acknowledgment**: honest
  documentation surfaces known limitations. The 24h session-token
  issue just caused a mid-research-run interruption; a doc that
  pretends the system has clean automation support would be
  misleading.
- **Why this story is pure-docs, not docs+code**: scope control.
  Adding API-key support is substantive backend work; this story
  is "describe what IS so future readers can orient." If API
  keys get added later, that story can add a section to this
  doc.

## Related

- Prior docs this one indexes against:
  - `docs/design/agent-architecture.md` (TB-US-044 spike output)
  - `docs/design/sweet-spot-architecture.md` (TB-US-043 output)
  - `docs/training/maintenance-fix-workflow.md` (TB-US-073)
  - `docs/training/upgrade-publishing-workflow.md` (TB-US-073)
  - `docs/math-example/methodology.md` (research protocol)
- Future stories this doc could seed:
  - API-key credential type for automation
  - Configurable `SESSION_MAX_AGE_SECONDS`
  - OpenAPI spec for the backend
  - IAM foundation (PM-US-004) — already exists as backlog

## Out of Scope

- API endpoint reference (OpenAPI / Swagger)
- Database schema reference (sits in migration files + manager
  classes)
- Deployment / install docs (those exist elsewhere)
- Performance tuning
- Security audit (API-key mechanism is a prerequisite for a
  proper audit)

## Completion Notes (2026-11-04)

Drafted during the Trial #8 experiment-wait window.

### Deliverables

- **`docs/design/system-architecture.md`** — new 3-page
  orientation doc. Six required sections present:
  1. System at a glance — ASCII component diagram + 1-paragraph
     component descriptions
  2. Request flow walkthroughs — three end-to-end traces
     (training launch, experiment run, research-script orchestration)
  3. Where state lives — table of 5 SQLite databases + file-level
     state
  4. Auth model — current session-token mechanism + known API-key
     gap + role vocabulary
  5. Process boundaries — 4-row table of processes with
     lifetime + ownership + why-the-boundary rationale
  6. Debug / observe entry points — 13-row table mapping
     "where do I look when X" to its answer
  7. (Bonus) Appendix listing what's deliberately NOT in the doc
- **`docs/README.md`** — new "Start here" section at the top
  pointing at the architecture doc; design-docs list now leads
  with it.
- **`CONTRIBUTING.md`** — new "Understand the system first"
  pre-step before the work-flow section.

### Scope validation

- Target length 2-4 pages: ~3 pages rendered ✓
- All 6 required content sections present ✓
- ≥2 request-flow walkthroughs (actually 3) ✓
- SQLite database table ✓
- `docs/README.md` cross-link at top ✓
- `CONTRIBUTING.md` cross-link ✓
- ASCII component diagram (readable in terminal) ✓

### Acceptance criteria status

- ✅ AC1: Architecture doc exists at correct path, 3 pages
- ✅ AC2: All 6 required content sections present
- ✅ AC3: 3 request-flow walkthroughs present
- ✅ AC4: SQLite database table with path + owned concern
- ✅ AC5: `docs/README.md` "Start here" section cross-links
- ✅ AC6: `CONTRIBUTING.md` points at the architecture doc
- ⏸️ AC7 (self-check: reader can describe 5 main components +
  training-launch flow after reading): deferred to operator
  review — can validate by reading the doc fresh

### Not done (per out-of-scope)

- API-key credential mechanism (acknowledged as gap in §4; not
  implemented in code; future TB-US-NNN if operator wants)
- Configurable `SESSION_MAX_AGE_SECONDS` (same reasoning)
- OpenAPI endpoint reference (separate concern)
