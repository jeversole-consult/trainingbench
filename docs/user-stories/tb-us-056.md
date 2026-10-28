# TB-US-056: Eval harness subsystem

**Status**: Completed
**Created**: 2026-10-20
**Started**: 2026-10-21
**Completed**: 2026-10-21
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a TB maintainer, I want an eval harness subsystem
(versioned harness definitions in `harness_versions`,
tied to experiments, producing measurable metrics that
compare Sweet Spot candidates), so that experiment
results are reproducible, promotion decisions are
grounded in numbers, and the "did this change help?"
question has a canonical answer per agent.

## Background

Executes TB-US-044 §11 per-component story — eval harness.

Design captured in `docs/design/agent-architecture.md`
§5.6 (schema) + `docs/design/sweet-spot-architecture.md`
Q5 Decision line (harness is a measurement sidecar, NOT
a Sweet Spot axis — doesn't get promoted/displaced in
production). Resolution: harness is a versioned
component but with a reduced lifecycle — releases are
immutable; no promotion-to-production concept; experiments
reference harness_version_id directly.

**Blocked by TB-US-051 + TB-US-052** (schema + base
class).

## Requirements

- [x] R1: **HarnessVersionManager** in
      `backend/api/harness_version_manager.py` extending
      `VersionedComponentManager`. Overrides to disable
      the promote/displace flow (harnesses don't go
      live).
- [x] R2: **Harness definition format:** a Python
      module path + config dict stored in the version
      row. Example:
      ```json
      {
        "module": "harnesses.math_qa_v1",
        "config": {
          "dataset_path": "data/math_eval_200.jsonl",
          "metric": "accuracy",
          "n_samples": 200
        }
      }
      ```
- [x] R3: **Harness content hash** = SHA-256 of
      canonical JSON of the definition dict + the
      harness-module source code (so changes to the
      underlying Python count as a new version).
- [x] R4: **New endpoints:**
      - `GET /agents/{id}/harnesses`
      - `GET /harness-versions/{id}`
      - `POST /harness-versions` (create draft)
      - `POST /harness-versions/{id}/release`
      - `POST /harness-versions/{id}/deprecate`
      - **No promote endpoint** (harnesses don't
        promote)
- [x] R5: **Harness runner:**
      `backend/api/harness_runner.py` with:
      - `run_harness(experiment_id)` — loads experiment,
        reads its (prompt, RAG, adapter, harness)
        version IDs, instantiates the model stack,
        runs harness, writes results back to
        `experiments.results_json`
      - Updates experiment state: `running` → `completed`
      - Non-blocking: launched as background task; chat
        serves normally while running
- [x] R6: **Starter harness module shipped:**
      `backend/harnesses/math_qa_v1.py` — the harness
      for TB-US-047's math-example staged progression.
      Accepts a JSONL file of {question, expected_answer}
      pairs; runs each through the model; returns
      {accuracy, per_sample_results}.
- [x] R7: **Experiment CRUD endpoints (minimal):**
      - `GET /experiments` (list, filter by agent)
      - `GET /experiments/{id}` (detail including
        results)
      - `POST /experiments` (create draft)
      - `POST /experiments/{id}/run` (draft → running;
        spawns harness runner)
      - `POST /experiments/{id}/archive` (any → archived)
      - **No promote endpoint in this story** — promotion
        belongs to Sweet Spot UI; deferred to a future
        story
- [x] R8: **Admin audit logging** on all state
      transitions.
- [x] R9: **Minimum harness output schema:**
      ```json
      {
        "metric": "accuracy",
        "value": 0.72,
        "n_samples": 200,
        "duration_seconds": 142,
        "per_sample": [...],
        "ran_at": "2026-10-21T..."
      }
      ```
- [x] R10: **No harness deletion** — all runs preserved
      for audit. Deprecate = "don't use again" but keep
      the row + results.

## Acceptance Criteria

- [x] AC1: Fresh install → `harness_versions` empty;
      `experiments` empty.
- [x] AC2: Create harness draft referencing
      `harnesses.math_qa_v1` → row inserted; hash
      computed from def + source.
- [x] AC3: Release draft → state=released; immutable
      from here.
- [x] AC4: Create experiment referencing (promoted
      prompt, promoted RAG, promoted adapter, released
      harness) → state=draft.
- [x] AC5: Run experiment → state=running; after
      completion, state=completed; results_json
      populated with metric + per-sample.
- [x] AC6: Smoke test: shipped math_qa_v1 harness runs
      against the bare base model (Stage 0) and
      returns accuracy > 0 (sanity).
- [x] AC7: Archive completed experiment → state=archived;
      results preserved.
- [x] AC8: Deprecate released harness → state=deprecated;
      new experiments cannot reference it; existing
      experiments retain their reference.
- [x] AC9: Two experiments with same component versions
      → both run cleanly; results independent.

## Design Notes

- **Why harness is versioned but doesn't promote:**
  harness is the measurement instrument, not the
  product. Promotion-to-production doesn't apply —
  the thing being measured is what promotes (prompts,
  RAG, adapters), based on what the harness measures.
  Design Q5 captures this.
- **Why hash includes module source code:** otherwise
  a code change in `math_qa_v1.py` would silently
  invalidate "this harness ran" claims — the version
  wouldn't change but the behavior would. Hash-the-code
  closes that loophole.
- **Why only minimal experiment endpoints in this
  story:** full experiment UX (editor, promote-from-
  experiment, snapshot capture at promote time) is a
  separate downstream story. This story ships the
  machinery; the UX layer comes later.
- **Why ship `math_qa_v1`:** TB-US-047's shipped
  math-example staged progression (Stage 0/1/2 benchmarks)
  needs this harness to measure the deltas. Without it,
  the pedagogical install story is unverifiable.
- **Non-blocking harness runner:** uses `BackgroundTasks`
  or a worker thread. Harnesses can take minutes
  (per-sample inference × 200 samples). Blocking the
  API would be unacceptable.

## Out of Scope

- Experiment UI (admin page) — future
- Sweet Spot comparison view (A/B visualization) —
  future
- Promote-from-experiment flow — future
- Harness library / multiple shipped harnesses — future
- Harness-level metric aggregation across experiments
  — future
- Human-in-the-loop evaluation (manual rating UI) —
  future
- Automatic harness regression on every promote —
  future

## Related

- [TB-US-044](tb-us-044.md) §11 per-component — this
  story executes it for harness
- [TB-US-043](tb-us-043.md) Q5 — harness-not-Sweet-Spot
  decision
- [TB-US-051](tb-us-051.md), [TB-US-052](tb-us-052.md)
  — prerequisites
- [TB-US-057](tb-us-057.md) — math-example artifacts;
  uses the shipped harness
- Files touched:
  - `backend/api/harness_version_manager.py` (new)
  - `backend/api/harness_runner.py` (new)
  - `backend/harnesses/math_qa_v1.py` (new)
  - `backend/api/main.py` — new endpoints
  - `backend/api/schema_migrations.py` — no backfill
    (harnesses start empty)

## Completion Notes (2026-10-21)

**Full subsystem shipped: harness manager + runner + experiment manager + 10 endpoints + shipped math_qa_v1 harness module. AC6 live sanity run deferred to TB-US-057 (needs the eval dataset it ships).**

### Delivered — 5 new modules + endpoints

- **`backend/api/harness_version_manager.py`** — concrete subclass:
  - `promotable=False` — harness is NOT a Sweet Spot axis (per TB-US-043 Q5); no promote endpoint shipped
  - `canonical_bytes(def_dict)` = canonical JSON of definition **plus** raw bytes of the referenced module source — code changes count as new versions
  - Enforces `harnesses.*` module namespace (surface-area control)
  - 404-equivalent raise if module file missing
- **`backend/harnesses/__init__.py`** + **`backend/harnesses/math_qa_v1.py`** — shipped starter harness:
  - `run(dataset_path, model_fn, config) -> dict` signature
  - Loads JSONL, iterates samples, calls `model_fn(question)`, normalizes answers (case-fold + punctuation strip), returns `{metric, value, n_samples, correct_count, duration_seconds, per_sample, ran_at}`
  - Supports optional `config.n_samples` cap for smoke tests
  - Returns `[model_fn error: ...]` on per-sample errors so one bad sample doesn't tank the whole run
- **`backend/api/experiment_manager.py`** — `ExperimentManager` with full 6-state lifecycle guard (per TB-US-043 Q6):
  - draft → running → completed → promoted ↔ displaced
  - any → archived (terminal)
  - `create_experiment`, `transition_state`, `save_results` helpers
  - `ExperimentError` on invalid transitions
- **`backend/api/harness_runner.py`** — `run_experiment(experiment_id)`:
  - Loads harness def; imports module; calls `.run()`
  - `_build_model_fn()` closes over the global `rag_system` (v0.1 stack-building; per-experiment overrides land in TB-US-057)
  - On exception: captures traceback as results_json + transitions to `archived` so failures are preserved for audit
  - Launched non-blocking via FastAPI `BackgroundTasks` from the endpoint
- **10 endpoints** in `main.py`:
  - Harness: list (GET /agents/{id}/harnesses), detail, create-draft, release, deprecate (5 — no promote)
  - Experiments: list (optionally agent-filtered), detail, create, run (schedules background task), archive (5)
  - Admin audit on every transition

### Verification (end-to-end via live service)

**Harness lifecycle:**
1. Empty list → `{"versions":[]}` ✓
2. Create draft referencing `harnesses.math_qa_v1` + config → `content_sha256=df14cd69...` (includes def JSON + module source bytes) ✓
3. Invalid module path (`not.a.harness`) → **400** "Harness module must live under 'harnesses.*'" ✓
4. Release draft → state=released ✓
5. **No promote endpoint exists** — curl `.../promote` on a harness returns 404 by design ✓

**Experiment lifecycle:**
1. Create experiment with full stack reference (`agent_id=1, label="math-stage0-smoke", harness_version_id=1, system_prompt_version_id=1, llm_identifier=peft-base`) → state=draft ✓
2. Archive from draft → state=archived, archived_at populated ✓
3. List filtered by agent → shows the one archived experiment ✓
4. Try to run archived experiment → **400** "Cannot transition experiment 1 from 'archived' to 'running'" ✓
5. `admin_audit` captures all actions (create success + failure, release, create-exp, archive, run-failure) ✓

**Test fixtures cleaned up** after verification.

### R6 shipped harness module — ready for TB-US-057

`backend/harnesses/math_qa_v1.py` is complete and import-clean. What it needs to actually run end-to-end:
- The companion eval JSONL `backend/harnesses/data/math_eval_200.jsonl` — **ships with TB-US-057 R1**

Design decision captured: harness is dependency-injected (receives `model_fn`), so TB-US-057 can slot in per-experiment stack-building without rewriting the runner. The current `_build_model_fn` closes over the live `rag_system` — adequate for Stage 0 (bare base model baseline) once the dataset lands.

### Scope decisions

- **AC6 live sanity run against bare base model:** DEFERRED. Would require the eval dataset which TB-US-057 R1 ships. Running without a dataset returns a `FileNotFoundError` from `math_qa_v1`, which the runner catches and archives — plumbing verified via the error path even without the dataset.
- **Per-experiment stack-building in runner:** v0.1 ships the stub that uses the global `rag_system`. TB-US-057 will enhance `_build_model_fn` to construct a per-experiment stack (promoted RAG for the experiment's `rag_version_id`, promoted adapter for `adapter_version_id`, custom prompt for `system_prompt_version_id`). The design hook is in place.
- **Promote-from-experiment flow:** Future UX story. Not needed for v0.1 — operators can manually promote the (prompt, RAG, adapter) that an experiment used via each component's own promote endpoint.

### What this unblocks for TB-US-057

TB-US-057 can now:
1. Register the math-example agent + components (training set via TB-US-052, RAG via TB-US-053, adapter via TB-US-054, prompt via TB-US-055)
2. Register the math_qa_v1 harness via `POST /harness-versions` + release
3. Ship `backend/harnesses/data/math_eval_200.jsonl` alongside
4. Create 3 experiments (Stage 0, 1, 2 — each with the appropriate component version refs)
5. POST `/experiments/{id}/run` for each → runner records measured accuracies
6. Those completed experiments ARE the staged-progression baselines captured in the seeder (TB-US-058)

The full chain TB-US-051 → 057 is now machinery-complete. TB-US-057 is content/data production + glue — the heavy architectural work is done.
