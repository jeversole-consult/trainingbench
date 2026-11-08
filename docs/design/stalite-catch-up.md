# Stalite catch-up: capability-port design for pre-fork downstreams

**Status**: 2026-11-07 — §3 hypotheses verified against stalite3
commit `adf59f0` (TB-US-090 inspection). Reverse-port candidates in
new §3.4. Memory-based assumptions that didn't survive inspection
in §3.5.
**Earlier status**: 2026-11-06 — initial draft pre-inspection.
**Related**: [`fork-and-customize.md`](fork-and-customize.md),
[`backend-feature-audit.md`](backend-feature-audit.md) (TB side),
[`agent-architecture.md`](agent-architecture.md),
[`sweet-spot-architecture.md`](sweet-spot-architecture.md)
**Motivates**: using stalite's customer-service domain as the next
real-world use case for TB's PEFT training pipeline

## tl;dr

TB forked from a predecessor codebase that is now continuing
independently as stalite. TB's **agent-umbrella architecture** +
**versioned components** + **Sweet Spot methodology** + **experiments
pivot** were added to TB *after* the fork and have never flowed
back. Everything else shared between the two codebases (RAG,
multi-LLM, training, document processing, spreadsheet calculator,
prompt classification*, multi-DB, PowerSearch, Compare) was present
at the fork point and lives on both sides at the **flatter
pre-agent layer**.

*Prompt classification is marked here as a stalite-only feature per
operator report; TB's audit (TB-US-086 §4) found zero backend
matches for it, so this is the exception to the "shared pre-fork
features" pattern.

**This doc catalogs the port surface for the scenario where a
pre-fork downstream wants to adopt TB's post-fork additions** —
either to run TB-style training experiments on its own domain, or
to adopt the Sweet Spot methodology in a disciplined way.

The specific motivating scenario: use **stalite's customer-service
domain** as the first real-world test of TB's PEFT training
pipeline. That training work has been tested on synthetic math
data (math-example research arc, closed 2026-11-06); stalite is
the natural second test because it has real domain data that the
math example lacks.

## 1. Scope + non-goals

**In scope:**

- Capability inventory: what TB has (post-fork) that stalite doesn't
- Port priorities tuned to the "run a TB training experiment on
  stalite" goal — not "port everything TB has ever added"
- Port mechanics per capability: schema migrations, API additions,
  UI patches a downstream would need

**Not in scope:**

- Stalite-specific code review. The author has not inspected
  stalite's codebase at draft time; stalite-side status columns
  below are inferred from the fork-shape memory and operator
  conversation. Mark these as hypotheses, not facts.
- Proprietary stalite content (customer-service prompts, domain
  data, client-specific endpoints). The port surface described
  here is deliberately generic so the doc is useful to any pre-fork
  downstream.
- Decisions about what stalite *should* adopt — that's the
  operator's call. This doc catalogs the port surface; it doesn't
  prescribe the strategy.

## 2. Fork-point anchor

TB's git history records the architectural divergence through a
series of stories that landed after the fork:

| Divergence | TB story | Approximate timing |
|---|---|---|
| Versioning primitives (schema + managers) | TB-US-051, 052 | ~Oct 2026 |
| Agent entity + agent CRUD | TB-US-044, 048 | ~Oct 2026 |
| Sweet Spot methodology (spike + scaffolding) | TB-US-043, 056, 057 | ~Oct 2026 |
| Experiments pivot + harness runner | TB-US-056, 069 | ~Oct 2026 |
| UI overhaul (left-nav drawer + white theme) | TB-US-018, 042 | Oct 2026 |
| Training-run tracker + sticky strip | TB-US-065, 066 | Oct 2026 |
| Experiments UI | TB-US-070 | Nov 2026 |
| Per-component version lifecycle UI | TB-US-087 | Nov 2026 |

Anything in this table is a candidate port target. Features *not*
in this table (RAG, multi-LLM, document processing, etc.) existed
at the fork point and stalite should already have them.

## 3. Capability inventory

Legend for **Stalite status** (verified 2026-11-07 against
stalite3 commit `adf59f0`):

- **present** — verified present in stalite3
- **absent** — verified absent in stalite3 (port candidate)
- **differs** — present but in a different shape than TB
- **stalite-only (client-specific)** — present but domain-tied;
  should not be ported into TB mainline

### 3.1 Platform core (verified)

| Capability | TB implementation | Stalite3 status | Port direction |
|---|---|---|---|
| RAG query + vector store | `backend/rag/rag_system.py`, `/query` | **present** | — |
| Multi-LLM backbone (HF / Ollama / OpenAI / PEFT / HF-PEFT) | `_init_llm()` in rag_system | **present** (5 providers) | — |
| Multi-DB (ChromaDB collections) | `database_manager.py` + `/databases/*` | **present** | — |
| PowerSearch (fan-out to external LLMs) | `power_search.py`, `/power-search` | **present** (Gemini, ChatGPT, Grok) | — |
| Compare Results (A/B) | `/query` with different pins + Compare tab | **present** | — |
| Document processing (PDF/DOCX/XLSX + OCR) | `document_processor.py` | **present** | — |
| Query routes (regex category-biased retrieval augmentation) | `route_version_manager.py` + app-settings path | **present** (`_maybe_augment_query` in rag_system) | — (TB has versioned variant; stalite's is flatter) |
| Query logger | `query_logger.py` | **present** | — |
| Legacy training-set manager | `training_manager.py` (pre-versioning) | **present** | — (TB keeps the flat path alongside the versioned one) |
| Legacy training-run tracker | `training_run_tracker.py` | **present** | **differs** — TB extended it with agent_id FK + cancel + startup_reconcile + progress_json; stalite's version is pre-extension |
| User management (CRUD + auth) | `user_manager.py` | **present** | **differs** — TB-US-017/041 added CRUD endpoints + admin_audit table; stalite's is pre-v2 |
| Session tracking | `session_tracker.py` | **present** | — |

### 3.1b Capabilities expected to be stalite-only — finding at inspection

The initial draft recorded two "stalite-only" capabilities that
would be reverse-port candidates. Both turned out to be
memory-based assumptions that didn't survive inspection:

- **Prompt classification**: NOT present in stalite3 (grep across
  `backend/` found zero class definitions, zero `classify_*`
  functions, zero `qualitative/quantitative/lookup/mixed`
  references). Stalite3 has `_maybe_augment_query` (regex query
  routing) in `rag_system.py` — the same capability TB has at a
  versioned layer. There is **no distinct four-category classifier
  with specialized handlers** in stalite3. The memory that "stalite
  has prompt classification TB doesn't" and the TB-US-086 audit
  footnote that cited stalite as the source for this are both
  **incorrect** at least for stalite3. TB-US-023 (prompt-classifier
  arc) remains net-new backend work; it is not a reverse-port.
- **Spreadsheet formula extraction**: NOT present in stalite3. The
  memory that "stalite has a generic xlsx formula-extraction
  capability TB doesn't" is **incorrect**. Stalite3 has a
  **client-specific hardcoded calculator** (see §3.4 below), which
  is a different kind of module and should not be ported into
  TB mainline. TB's `SpreadsheetCalculator` (generic xlsx formula
  invocation via openpyxl + pandas) is the capability at the
  "spreadsheet" row, and stalite3 has nothing equivalent.

### 3.2 TB additions (post-fork, verified absent in stalite3)

These are the port candidates for a pre-fork downstream:

| Capability | TB implementation | Stalite3 status | Priority for "run training on stalite" |
|---|---|---|---|
| **Agent entity** (top-level `agents` table; agent_id FKs everywhere) | `agent_manager.py`, TB-US-051 schema, TB-US-048 CRUD | **absent** | **critical** — all versioning is agent-scoped |
| **Versioning schema** (schema_migrations infra, `*_versions` tables, draft/released/promoted/deprecated states) | `schema_migrations.py`, 5 version managers | **absent** | **critical** |
| **Agent-components mapping** (which prompt/RAG/adapter is promoted for an agent) | `agent_components` table | **absent** | critical for Sweet Spot; optional for one-off training |
| **Training-set versioning** (sidecar JSONL, SHA-256 anchored) | `training_set_version_manager.py`, `/training-set-versions/*` | **absent** (legacy `/training/sets` IS present; versioned layer is not) | **critical** |
| **Adapter versioning** (register, release, promote, promote-displaces-prior) | `adapter_version_manager.py`, auto-registration on run completion (TB-US-065) | **absent** | **critical** |
| **Prompt / RAG / Route / Harness versioning** | 4 more version managers | **absent** | **important** for Sweet Spot; optional for one-off training |
| **Training-run tracker extensions** (agent_id FK, cancel, startup_reconcile, progress_json, source_experiment_id) | `training_run_tracker.py` + schema_migrations TB-US-065/070/091 | **differs** (base `training_run_tracker.py` present; extensions absent) | moderate — can proceed with stalite's existing tracker or port TB's extensions |
| **Experiments pivot** (bind prompt + RAG + LLM + adapter + harness → measurement) | `experiment_manager.py`, TB-US-056 | **absent** | **critical** for Sweet Spot methodology |
| **Harness runner** (background task executes harness module against a stack; chat-template prompt discipline per TB-US-092) | `harness_runner.py`, TB-US-069 stack-building, TB-US-070 progress heartbeat, TB-US-092 chat-template fix | **absent** | **critical** — note: port the TB-US-092 fix with it; don't repeat our mistake |
| **Math-example harness** (GSM8K eval loop; CoT-aware answer extraction) | `backend/harnesses/math_qa_v1.py` | **absent**, domain-irrelevant | low — write a stalite-domain harness instead |
| **UI overhaul** (left-nav drawer, white theme) | `static/left_nav.js`, `static/style.css`, TB-US-018/042 | **absent** — stalite3's `static/` has only `login.js` + `script.js`, no left-nav/agent-mgmt/api-key modules | **low for training, moderate for demo** |
| **Agent management modal** | `agent_management.js`, TB-US-048 | **absent** | moderate — needed once agents exist |
| **Version lifecycle UI** (release / promote / deprecate buttons) | `version_lifecycle.js`, TB-US-087 | **absent** | moderate — needed for operator ergonomics |
| **Training-run strip** (sticky top banner during active run) | `active_run_strip.js`, TB-US-066 | **absent** | low — nice-to-have |
| **Experiments UI** (strip + list + detail) | `active_experiment_strip.js`, `experiments.html`, TB-US-070 | **absent** | moderate — needed once Sweet Spot methodology is in play |
| **API-key mechanism** | `api_key_manager.py`, `/api-keys/*`, TB-US-063 | **absent** (no `api_key_manager.py`, no `/api-keys/*` endpoints) | moderate — needed for research automation |
| **User management v2** (CRUD + audit log) | `user_manager.py`, TB-US-017/041 | **differs** — `user_manager.py` present with basic CRUD but without TB-US-017's admin_audit table or TB-US-041's modal patterns | low |
| **Auto-reload banner** (`/version/build` + client poll) | `version_check.js` + `/version/build` endpoint | **absent** | low — infra polish |

### 3.4 Reverse-port candidates (features stalite3 has that TB doesn't)

One reverse-port candidate surfaced on operator review after the
initial inspection missed its semantic classification:

- **SL-US-010 "Configurable query-routing for category-biased
  retrieval"** — a UI for editing regex-based query-routes that
  bias ChromaDB retrieval toward specific content categories.
  Stalite3 shipped this in June 2026 (committed in stalite3 at
  `b87c623` on 2026-11-07 after sitting uncommitted). TB has had
  the backend (TB-US-040 cache + `_maybe_augment_query`, TB-US-033
  `/settings/query-routes` GET+PUT) since Oct 2026 but never
  built the UI. **Ported into TB as [TB-US-095](../user-stories/tb-us-095.md)**
  (2026-11-07) via a new drawer-admin-dropdown entry + modal
  mirroring stalite3's pattern.

  This is effectively a form of prompt classification — the
  initial inspection concluded "prompt classification is not in
  stalite3" because it searched for the specific TB-US-023
  pattern (4-category classifier with specialized handlers).
  Stalite3's lighter regex-based routing is a different
  implementation of the same category of feature. Memory
  corrected 2026-11-07.

The one domain-specific module found during inspection (§3.5
below) is **deliberately client-scoped** and should stay in
stalite's fork per the generic TB platform ↔ private fork pattern
documented in [`fork-and-customize.md`](fork-and-customize.md).

Besides the SL-US-010 UI reverse-port (now completed), TB
mainline is not missing anything else from stalite3.

### 3.5 Client-specific code — deliberately not inspected

Stalite3 has one module (`backend/api/mix_design_handler.py`
and its collaborator `backend/api/formula_calculator.py` with
class `StaliteCalculator`) containing domain-specific logic for
stalite's customer business. Per the TB-public-repo carve-out
(TB-US-090 AC5), these files were **not inspected** during this
spike and their contents are **not reproduced** in this doc.

The pattern they follow is the one `fork-and-customize.md`
recommends: client-specific endpoints and handlers live in the
operator's private fork (`backend/api/your_client_handler.py`
in §5.3 of that doc). Stalite follows this pattern correctly.
No port direction applies.

### 3.6 Reads vs. writes vs. shape differences

Important caveat: **"present pre-fork"** does **not** mean "zero
work to adopt TB's additions." The TB additions reshape pre-fork
data (e.g., every training-set now has an agent_id FK). A port
that lands agents without also wiring agent_id into the existing
pre-fork tables leaves the system in a partial state.

TB's own migration strategy for this problem was the
**hybrid schema-first-data-later** pattern (TB-US-044 §3): add new
tables, back-attribute existing rows to a seeded `default` agent,
let per-component stories (TB-US-052 through TB-US-056) perform
the data migration one surface at a time. A downstream catch-up
would follow the same pattern.

## 4. Port priorities (minimum path to training on stalite)

The question this doc actually answers: **what's the smallest set
of TB additions stalite needs to run one complete PEFT training
experiment on its customer-service data?**

Priorities in execution order:

### Priority 1 — Foundation (must)

1. **Add the `agents` table + agent_manager**. Seed a single
   `stalite` agent (or `customer-service` — operator's call on
   slug). Idempotent migration pattern from TB-US-051.
2. **Add the versioning schema** (schema_migrations infrastructure
   + `training_set_versions` + `adapter_versions` tables with
   agent_id FKs). Seed one draft training-set version from
   stalite's existing training data (if any).
3. **Add training-set-version manager + adapter-version manager**
   (the two version managers needed to version the data going IN
   and the adapter coming OUT of training).
4. **Port TB's PEFT training launch flow** — either the whole
   `training_run_tracker` + `training/math/train.py` subprocess
   pattern, or a minimal variant that writes an adapter directory
   stalite can then register as a draft `adapter_version`.
5. **Build a stalite-domain harness module** (parallel to
   `backend/harnesses/math_qa_v1.py` but for customer-service
   eval). This is domain work the operator does; shape it after
   `math_qa_v1`.

Deliverable of Priority 1: one completed training run on stalite
data → one registered `adapter_version` the operator can smoke-
test by hand. No UI required; API-only is sufficient.

### Priority 2 — Measurement discipline (should)

6. **Add the experiments pivot + harness runner**. Register the
   just-trained adapter as a pin, run the stalite harness against
   it, capture the result.
7. **Port the experiments UI (TB-US-070) OR accept API-only
   supervision**. Operator preference.

Deliverable of Priority 2: before/after accuracy numbers on a
stalite harness. Equivalent to math-example Stage 0 vs. Stage 1.

### Priority 3 — Operator ergonomics (nice-to-have for first-run)

8. **Port the version lifecycle UI (TB-US-087)** so operators can
   promote the winning adapter from the UI instead of a POST.
9. **Port the agent-management modal (TB-US-048)** so stalite
   gains + removes agents from a UI.
10. **Port the training-run strip + experiments strip (TB-US-066,
    TB-US-070)** for visibility during long-running work.

### Priority 4 — Full Sweet Spot adoption (post-first-run)

11. **Add the remaining version managers** (prompt, RAG, route,
    harness) so stalite can pin and compare full stacks, not just
    adapters.
12. **Port the agent-components mapping** so stalite has a true
    Sweet Spot ("current promoted stack for this agent").

### What to skip

- **Math-example harness + seed agent.** Domain-irrelevant for
  stalite. Write a stalite harness instead.
- **The UI overhaul** (TB-US-018/042). Visual polish, not
  training-blocking. Port only if stalite wants a visual refresh
  on its own schedule.
- **PowerSearch / Compare tabs.** Already present pre-fork.
- **API-key mechanism.** Only if stalite has a research-
  automation use case that currently relies on session tokens.
  Not training-blocking.

## 5. Port mechanics per capability

For each priority-1 and priority-2 capability, this section lists
what the actual port touches. Use this as a shopping list when
drafting a stalite-side story.

### 5.1 `agents` table + agent_manager

- **Schema**: `CREATE TABLE agents (agent_id INTEGER PK, name TEXT
  UNIQUE, display_name TEXT, description TEXT, state TEXT CHECK IN
  ('active', 'retired'), created_at TEXT)`. Idempotent via
  schema_migrations tracker.
- **Seeding**: on first-run, insert `agents` row for stalite's
  primary agent slug.
- **Manager module**: port `backend/api/agent_manager.py` verbatim
  — `AgentManager` class, CRUD methods, slug regex, soft-delete
  via state column.
- **Endpoints**: port `GET/POST /agents`, `GET /agents/{name}`,
  `PUT /agents/{name}`, `DELETE /agents/{name}` from `main.py`.
- **Migration**: `MIGRATION_ID = "stalite-01-agents"` in
  schema_migrations.
- **Reference**: TB-US-044 (architecture spike), TB-US-048 (CRUD).

### 5.2 Versioning schema + schema_migrations infra

- **Port `backend/api/schema_migrations.py`** verbatim. Rename
  the `MIGRATION_ID` constants to a stalite namespace to avoid
  confusion with TB's migration tracker if the DB ever gets copied.
- **Schema** — add the `*_versions` tables needed for priority 1:
  `training_set_versions` and `adapter_versions` (defer
  `prompt_versions`, `rag_versions`, `route_versions`,
  `harness_versions` to priority 4).
- **Columns pattern** (shared across all `*_versions` tables):
  `version_id` PK, `agent_id` FK, `state` CHECK IN ('draft',
  'released', 'promoted', 'deprecated'), `created_at`,
  `created_by`, promoted/deprecated timestamps, content hashes
  (`content_sha256` where applicable), `training_run_metadata_json`
  (adapters only), `training_set_version_id` FK (adapters only),
  `parent_version_id` FK (all).
- **Reference**: TB-US-051 (schema), TB-US-052 (training-set
  version manager), TB-US-053 (adapter version manager).

### 5.3 Training-set version manager

- **Port `backend/api/training_set_version_manager.py`** verbatim.
  Depends on: the versioning schema being in place.
- **Endpoints**: `GET /agents/{agent_id}/training-sets`,
  `POST /training-set-versions`, `GET
  /training-set-versions/{id}`, `POST
  /training-set-versions/{id}/{release,promote,deprecate}`.
- **Sidecar JSONL**: create `training/datasets/training_set_versions/v*.jsonl`
  under stalite's filesystem layout.
- **Data migration**: back-attribute any existing stalite training
  data to `v1` of the primary agent's training-set versioning.

### 5.4 Adapter version manager

- **Port `backend/api/adapter_version_manager.py`** verbatim.
- **Endpoints**: `GET /agents/{agent_id}/adapter-versions`,
  `POST /adapter-versions/register`,
  `POST /adapter-versions/{id}/{release,promote,deprecate}`.
- **Adapter storage**: on registration, hash
  `adapter_model.safetensors` → `content_sha256`; hash
  `adapter_config.json` → `config_sha256`. Copy files to
  `adapters/{agent_slug}/v{version_id}/` under stalite's layout.
- **Auto-registration hook** (TB-US-065): when a training run
  completes successfully, call
  `adapter_version_manager.register_existing_adapter(...)` from
  the training completion callback. This is what makes "trained
  adapter appears as a draft version" work automatically.

### 5.5 PEFT training launch flow

Three sub-options; operator picks:

- **Option A — port TB's whole flow.** `training_run_tracker.py`
  + `training/math/train.py` subprocess pattern + `/training/runs`
  endpoints + `active_run_strip.js`. Highest fidelity; most work.
- **Option B — port only `training_run_tracker` + a stalite-
  specific train script.** Keep stalite's existing training path
  if any; just add the tracker so runs are DB-recorded and the
  adapter can be auto-registered on completion.
- **Option C — zero port; wrap stalite's existing path in a thin
  script that writes to the new `adapter_versions` table on
  completion.** Minimum viable but loses the launch / cancel /
  progress visibility.

Recommended: **Option B** for a first-run experiment. Option A
if operator wants the full TB training-ops surface on stalite.

### 5.6 Stalite-domain harness module

New code; not a port.

- Write `backend/harnesses/stalite_customer_service_v1.py` with
  `run(dataset_path, model_fn, config)` returning `{metric,
  value, n_samples, correct_count?, duration_seconds, per_sample,
  ran_at}`. Model after `backend/harnesses/math_qa_v1.py`.
- Operator decides the metric: exact-match accuracy? semantic
  similarity? judge-model rating? Matters for what "training
  worked" means.
- Register the harness via `harness_version_manager` (optional
  for priority 1; required for priority 4's full Sweet Spot).

### 5.7 Experiments pivot + harness runner

- **Port `backend/api/experiment_manager.py`** verbatim.
  Depends on: agents, versioning schema, agent_components (optional
  for simple experiments).
- **Port `backend/api/harness_runner.py`** verbatim. The
  progress-heartbeat path (TB-US-070 R18) injects a `progress_cb`
  into the harness config; keep that or skip for simpler port.
- **Schema**: add `experiments` table (TB-US-056 definition).
  Includes `started_at` + `progress_json` columns (TB-US-070
  additions).
- **Endpoints**: `POST /experiments`, `POST
  /experiments/{id}/run`, `POST /experiments/{id}/archive`,
  `GET /experiments`, `GET /experiments/{id}`.
- **Background execution**: TB uses FastAPI's `BackgroundTasks`.
  Preserve the pattern unless stalite is on a different framework.

### 5.8 Experiments UI (priority 3)

- **Port `static/experiments.html`** + `static/active_experiment_strip.js`.
  Both files are self-contained; adjust path assumptions
  (`/static/experiments.html` must match stalite's static mount).
- Depends on: the backend endpoints from §5.7 being live.

## 6. Open design questions

(Operator-answerable at port-planning time. Kept short since the
operator declined the "open questions" scope for this doc.)

- Does stalite want one `agents` row ("stalite") or
  many (per sub-domain)?
- What eval metric does the stalite harness optimize?
- Which of §5.5's three training-launch options?

## 7. What this doc does not cover

- **Stalite's actual code** — status columns in §3 are
  hypotheses. A follow-up spike story with inspection of stalite's
  repo would turn them into facts.
- **Operational logistics** — who runs the training, on what
  hardware, over what wall-clock. Stalite is proprietary to the
  operator; those decisions live outside this doc.
- **Cost / scheduling** — no estimates by hour or week; this is a
  capability-port design, not a project plan.

## 8. Related

- [`fork-and-customize.md`](fork-and-customize.md) — the general
  "how to adopt TB downstream" guide; this doc is the specific
  "pre-fork downstream catching up to post-fork additions"
  variant.
- [`backend-feature-audit.md`](backend-feature-audit.md) — the
  authoritative inventory of TB's current capability palette;
  this doc's §3 is derived from it.
- [`agent-architecture.md`](agent-architecture.md),
  [`sweet-spot-architecture.md`](sweet-spot-architecture.md) — the
  designs being ported.
