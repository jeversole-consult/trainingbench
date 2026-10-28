# Agent Architecture + Versioned-Component Management — Design Notes

**Status:** Draft (operator-collaborative; iterate across turns)
**Owned by:** TB-US-044
**Related:** TB-US-043 (Sweet Spot methodology, parallel)
**Created:** 2026-10-16
**Last updated:** 2026-10-16

> **This is a working document.** It will evolve as the
> operator and Claude Code iterate on the open questions
> below. Each design decision is captured as it stabilizes.
> The document is "ready to execute against" when every open
> question has a **Decision:** line and the follow-up
> stories (§11) are drafted.

---

## Table of Contents

1. [What is an agent?](#sec-1)
2. [Agent lifecycle](#sec-2)
3. [Component types owned by an agent](#sec-3)
4. [Versioned-component pattern](#sec-4)
5. [Per-component schema](#sec-5)
6. [Agent entity schema](#sec-6)
7. [Component lifecycle](#sec-7)
8. [Code vs data](#sec-8)
9. [Migration from current TB state](#sec-9)
10. [URL schema implications](#sec-10)
11. [Follow-up stories unlocked](#sec-11)
12. [Open questions for operator decision](#sec-12)
13. [Decision log](#sec-13)
14. [What comes after this architecture is approved](#sec-14)

---

<a id="sec-1"></a>

## 1. What is an agent?

**Working definition** (first draft — operator to refine):

> An **agent** is TrainingBench's top-level organizing
> entity: a named, deployable chat-interface target that
> **owns** a collection of versioned subcomponents (RAG
> corpora, training sets, PEFT adapters, system prompts,
> eval harnesses, query routes) and that has at most one
> current Sweet Spot — a snapshot (per TB-US-043) of a
> specific version of each subcomponent, pinned together
> for deployment.

**What an agent IS:**

- A named identity (`math`, `stalite-concrete`, `cuad`,
  `support-copilot`)
- A boundary of inventory (its RAG, its training sets,
  its adapters, its prompts, its harnesses, its routes)
- A pointer to its current Sweet Spot (which snapshot
  is live)
- A lifecycle entity (created, active, retired)

**What an agent IS NOT:**

- A folder (git-code project is Claude-Code's concept,
  not TB's)
- A deployment target server (that's downstream, Agent
  Release territory)
- A user — agents don't log in; users operate them
- A model — a model is one subcomponent of an agent

**What's shared across agents vs owned per-agent:**

- **Shared:** TB application code, the LLM pool (Ollama
  catalog), base-user accounts, system settings not
  specific to agent behavior
- **Per-agent:** everything specialized — the agent's RAG
  corpus content, its training sets, its trained adapters,
  its system prompt text, its eval harnesses, its query
  routes
- **Boundary question:** can two agents reference the same
  trained adapter? See §9 Q6.

### 1.a. Two-tier architecture (added 2026-10-17)

TB's architecture divides into two tiers, with distinct
scopes and distinct management surfaces:

```
┌─────────────────────────────────────────────┐
│  TB INSTALL                                  │
│                                              │
│  ADMINISTRATIVE TIER (platform-wide)         │
│    👥 Users (accounts)                        │
│    🔑 API Keys (external LLMs)                │
│    ⚙️ System config                           │
│                                              │
│  AGENT TIER (where the work happens)         │
│    🤖 Agent: math                             │
│      ├─ RAG corpora (versioned)              │
│      ├─ Documents (in its RAG)               │
│      ├─ Scraping / Upload                    │
│      ├─ Training sets (versioned)            │
│      ├─ Adapters (versioned)                 │
│      ├─ Prompts, harnesses, routes (versioned)│
│      ├─ Chat / Search / Compare / PowerSearch│
│      ├─ Query log                            │
│      └─ Training runs                        │
│    🤖 Agent: stalite  (own set of all above) │
│    🤖 Agent: cuad     (own set of all above) │
│    ...                                       │
└─────────────────────────────────────────────┘
```

**Operator insight 2026-10-17:** *"agents are at the top of
the food chain except for administrative management like
users and keys."*

**Load-bearing consequences:**

1. **Agents are the primary noun** in TB's architecture.
   The vast majority of what TB does is scoped to an agent
   (11 of 11 drawer items as of this writing). "Agent" is
   not optional context; every productive action runs
   against one.

2. **Administrative tier is small and separate.** Users,
   API keys, system config are the entire set as of today.
   They do NOT belong in the agent-contextualized drawer
   (see §10 for UI implications).

3. **The drawer is a workspace, not a nav bar.** All
   drawer items implicitly operate on a currently-selected
   agent. Switching agents swaps the context of everything
   below the agent-selector. Pattern analog: Slack
   workspace selector, Claude Code project, GitHub repo.

4. **System items get their own surface.** Not in the
   drawer. Candidate placements enumerated in §12 Q11.

**Open — see §12 Q1 for formal-definition decisions, and
§12 Q11 for administrative-surface UX.**

---

<a id="sec-2"></a>

## 2. Agent lifecycle

Candidate states for an agent as an entity (orthogonal to
its components' lifecycle):

| Status | Meaning |
|---|---|
| `active` | Agent is live; experiments and snapshots can be created / promoted |
| `retired` | Agent is no longer being developed; existing snapshots preserved; new experiments blocked |

Simple on purpose. The complexity lives in the component
lifecycle and the Sweet Spot promotion flow (TB-US-043),
not in the agent entity itself.

**Open — see §12 Q2 for whether lifecycle needs more
states (archived, draft, suspended, etc.).**

---

<a id="sec-3"></a>

## 3. Component types owned by an agent

**Six candidate types:**

1. **RAG corpus** (chroma collection + document manifest)
2. **Training set** (JSONL file of curated examples)
3. **PEFT adapter** (trained weights binary + training recipe)
4. **System prompt** (template string with {context} and
   {question} placeholders)
5. **Eval harness** (test prompts + rubric + primary
   metric)
6. **Query routes** (regex-pattern retrieval augmentation
   rules — currently in `AppSettings`)

**Rationale per type:**

| Type | Why agent-owned |
|---|---|
| RAG corpus | Content differs per domain; version matters for reproducibility (what docs were indexed when adapter was trained) |
| Training set | Different for each agent; multiple candidates per agent |
| PEFT adapter | Produced by training against a specific training set + base LLM + hyperparameters |
| System prompt | Varies per agent context ("You are a math tutor…" vs "You are a concrete-mix specialist…") |
| Eval harness | Different test prompts and rubrics per domain |
| Query routes | Agent-specific retrieval behavior (TB-US-044 Q5 confirms this; TB currently has them global) |

**Deliberately NOT agent-owned:**

- **The LLM itself.** LLMs are a shared pool managed by
  Ollama. An agent *references* an LLM by name; it doesn't
  version it. If Meta releases llama3.1:8b-v2 and the
  operator pulls it, that's an external event — TB
  references by Ollama tag.
- **User accounts.** Users operate across agents.
- **Audit logs.** Platform-wide, not agent-scoped.
- **TB application code.** Git-managed externally.

**Open — see §12 Q3 for which component types land in v0.1
vs defer.**

---

<a id="sec-4"></a>

## 4. Versioned-component pattern

Every component type uses the same schema template plus
component-specific columns.

### 4.1 Template

```sql
CREATE TABLE <component>_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,              -- FK → agents.name
    component_name TEXT NOT NULL,          -- stable identity across versions
                                           -- e.g. 'math_corpus', 'gsm8k_corrections'
    version_tag TEXT NOT NULL,             -- 'v1', 'v2-with-textbooks', 'rc1.2'
    content_sha256 TEXT NOT NULL,          -- integrity hash
    description TEXT,                      -- what changed from parent (changelog line)
    parent_version_id INTEGER,             -- lineage; NULL for first version
    status TEXT NOT NULL CHECK (status IN ('draft', 'released', 'deprecated')),
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    released_at TEXT,                      -- stamp when flipped from draft
    deprecated_at TEXT,                    -- stamp when flipped to deprecated
    metadata TEXT,                         -- JSON blob for extensibility
    -- Plus component-specific columns (§5)
    UNIQUE(agent_name, component_name, version_tag),
    FOREIGN KEY (agent_name) REFERENCES agents(name)
);
```

### 4.2 Identity model

An agent can own multiple **components of the same type**
with different `component_name` values:

- `agent='math'`, `component_name='gsm8k_corrections'` is
  one training set
- `agent='math'`, `component_name='math_olympiad_set'` is
  a different training set
- Each has its own version lineage (`v1`, `v2`, …)

**Scope of uniqueness:** `(agent, component_name,
version_tag)` is unique. Across agents, the same
component_name can be reused (`math.gsm8k_corrections.v1`
and `cuad.gsm8k_corrections.v1` are distinct records with
different content).

### 4.3 Content hashing

Every version has a `content_sha256` field computed over
the component's actual content:

| Component | What gets hashed |
|---|---|
| RAG corpus | Manifest JSON (list of {source, chunks_hash}) — not the raw chunks (chroma owns storage) |
| Training set | The JSONL file content |
| PEFT adapter | The adapter directory tarball hash |
| System prompt | The prompt template string (utf-8 bytes) |
| Eval harness | The combined rubric_json + test_prompts_file content |
| Query routes | The JSON serialization (sort_keys=True) |

**Drift detection:** on any read of a `released` version,
TB can recompute the hash and warn if it differs from the
stored one. Catches silent edits.

**Open — see §12 Q4 for hashing scheme decisions.**

---

<a id="sec-5"></a>

## 5. Per-component schema

For each of the six types, the template plus specifics:

### 5.1 RAG corpus — `rag_versions`

```sql
-- Template columns plus:
chroma_collection TEXT NOT NULL,      -- which chroma collection name
documents_manifest TEXT NOT NULL,      -- JSON: list of {source, doc_hash, chunk_count}
total_chunk_count INTEGER,
embedding_model TEXT                   -- e.g. 'all-MiniLM-L6-v2'
```

**Current TB state:** Chroma collections configured in
`database_config.json` (unversioned). Chroma itself stores
the vectors. Migration path: wrap each existing collection
as a `rag_version` row with inferred `v1` version_tag.

### 5.2 Training set — `training_set_versions`

```sql
-- Template columns plus:
file_path TEXT NOT NULL,               -- JSONL on disk; immutable once released
example_count INTEGER NOT NULL,
data_format TEXT,                      -- 'instruction', 'chatml', 'raw'
categories TEXT,                       -- JSON array of tags
```

**Current TB state:** TB has `users.db → training_sets`
table + per-set JSON file. Already has a crude lifecycle
(`status IN ('draft', 'pending', 'applied', 'archived',
'deprecated')`). Migration path: adapt existing rows to the
versioned pattern (today's `training_sets.id = 7` becomes
`training_set_versions.id = N` where `component_name =
<old name>` and `version_tag = 'v1'`).

### 5.3 PEFT adapter — `adapter_versions`

```sql
-- Template columns plus:
adapter_path TEXT NOT NULL,            -- directory under training/adapters/
training_run_id INTEGER,               -- FK → training_runs (which run produced this)
training_set_version_id INTEGER,       -- FK → training_set_versions (what trained it)
base_llm TEXT NOT NULL,                -- 'llama3.1:8b'
hyperparameters TEXT NOT NULL,         -- JSON: {lora_r, lora_alpha, lr, epochs, ...}
training_wall_time_seconds INTEGER,
final_training_loss REAL,
final_eval_loss REAL
```

**Current TB state:** `training_runs` table tracks runs;
adapters live at `training/adapters/<name>/`. Migration
path: each training_run that produced an adapter becomes a
`adapter_version` row linked back to the run.

### 5.4 System prompt — `prompt_versions`

```sql
-- Template columns plus:
prompt_template TEXT NOT NULL,         -- the actual string with {context}, {question}
template_variables TEXT                -- JSON: ['context', 'question', 'date'...] — explicit list
```

**Current TB state:** `AppSettings.rag_prompt` holds ONE
global prompt (unversioned). Migration: current prompt
becomes `prompt_versions` row for a `default` agent (or
promoted to each new agent on creation).

### 5.5 Eval harness — `harness_versions`

```sql
-- Template columns plus:
test_prompts_file TEXT NOT NULL,       -- JSONL on disk
rubric_json TEXT NOT NULL,             -- JSON: scoring criteria
primary_metric TEXT NOT NULL,          -- field in metrics_json that defines ranking
secondary_metrics TEXT                 -- JSON array of other fields to capture
```

**Current TB state:** No eval harness subsystem exists.
Fresh build; no migration.

### 5.6 Query routes — `route_versions`

```sql
-- Template columns plus:
routes_json TEXT NOT NULL              -- JSON: list of {name, patterns, augmentation, position, enabled}
```

**Current TB state:** `AppSettings.query_routes` holds ONE
global list. Migration path matches §5.4 (becomes agent-
owned).

---

<a id="sec-6"></a>

## 6. Agent entity schema

```sql
CREATE TABLE agents (
    name TEXT PRIMARY KEY,                -- 'math', 'stalite-concrete', 'cuad'
    description TEXT,
    status TEXT CHECK (status IN ('active', 'retired')),
    current_snapshot_id INTEGER,          -- FK → snapshots; NULL if no Sweet Spot yet
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    metadata TEXT                         -- JSON blob
);
```

**Naming constraints:** `[a-z][a-z0-9_-]*` — lowercase +
digits + dash/underscore. No spaces; dash-separated for
multi-word (`stalite-concrete`). Enforced at the
`POST /agents` endpoint.

---

<a id="sec-7"></a>

## 7. Component lifecycle

Each versioned component moves through:

| Status | Meaning | Editable? | Usable in snapshots? |
|---|---|---|---|
| `draft` | In-progress; being edited | ✓ Yes | ✗ No |
| `released` | Immutable; frozen content | ✗ No | ✓ Yes |
| `deprecated` | Marked obsolete; hidden from new snapshots | ✗ No | ✗ No (new snapshots); existing snapshots still work |

**Transitions:**

- `draft → released`: operator action; computes hash,
  writes to `released_at`, locks content
- `released → deprecated`: operator action; `deprecated_at`
  stamp; existing snapshots that pin this version continue
  to function
- Backward transitions NOT allowed (released cannot return
  to draft; deprecated cannot return to released)

**Multi-draft semantics:** multiple drafts per
`(agent, component_name)` are allowed. "Draft" is a
scratchpad concept — a version becomes authoritative only
when released.

**Open — see §12 Q7 for lifecycle refinements.**

---

<a id="sec-8"></a>

## 8. Code vs data

| Layer | Versioning | Owner | Example |
|---|---|---|---|
| **TB application code** | git + semver | External: git/GitHub | `backend/api/main.py` |
| **Base LLMs** | External catalog | Ollama (or API provider) | `llama3.1:8b` |
| **Agent artifacts** | Internal versioned-table pattern + content hashes | TB (SQLite + file snapshots) | Everything in §5 |

**Explicit non-decisions for v0.1:**

- No DVC integration (data version control via git-adjacent
  tooling)
- No MLflow / W&B / Comet.ml integration
- No external artifact registry
- No model-weight checksumming beyond adapter files

If any of these become limiting at scale, revisit with a
dedicated story. For a single-operator team with 10-100s
of versioned artifacts, SQLite + content hashes is enough.

---

<a id="sec-9"></a>

## 9. Migration from current TB state

**Starting state (what TB has today):**

| TB component | Current storage | Current versioning |
|---|---|---|
| Users | `users.db → users` | None (identity, not an artifact) |
| Training sets | `users.db → training_sets` + file at `file_path` | Partial (`status` field, no version concept) |
| Training runs | `users.db → training_runs` | None (runs are events, inherently immutable) |
| RAG collections | `database_config.json` + chromadb | None |
| System prompt | `AppSettings.rag_prompt` (single) | Audit log only |
| Query routes | `AppSettings.query_routes` (single) | Audit log only |
| Admin audit | `users.db → admin_audit` | N/A |

**Migration strategy (high level):**

- **Agents table** — new. Create default `agent='default'`
  on first upgrade so legacy records have a home.
- **training_sets** — add a `component_name` and
  `version_tag` columns to the existing table (don't
  rename `training_sets` to `training_set_versions` —
  compat); backfill `component_name = name`, `version_tag =
  'v1'`, `agent_name = 'default'`. Deprecate the loose
  `status` enum in favor of the new 3-state model (or map
  the existing values).
- **RAG** — new `rag_versions` table; migrate each entry
  in `database_config.json` as a row under
  `agent='default', component_name=<id>, version_tag='v1'`.
- **AppSettings prompt + routes** — new `prompt_versions`
  and `route_versions` tables; current values become `v1`
  for `agent='default'`. Keep the AppSettings fields for
  backward compat during a deprecation window.
- **Adapters** — infer from `training_runs` where
  `adapter_name` is set; backfill `adapter_versions` rows.

**Reversibility:** each migration step is reversible via
column-drop + table-drop. Snapshot the pre-migration state
of `users.db` before running the migration.

**Open — see §12 Q8 for migration-timing decisions.**

---

<a id="sec-10"></a>

## 10. URL schema implications

**Current flat endpoints:**

- `GET /training/sets`
- `POST /training/sets`
- `GET /training/sets/{id}`
- `GET /training/runs`

**Candidate nested endpoints:**

- `GET /agents` — list agents
- `POST /agents` — create agent
- `GET /agents/{name}` — agent detail (current snapshot,
  component counts)
- `GET /agents/{name}/training-sets` — list this agent's
  training sets
- `POST /agents/{name}/training-sets` — create new training
  set for agent
- `GET /agents/{name}/training-sets/{id}` — detail
- `GET /agents/{name}/training-sets/{id}/versions` — list
  versions of this training set
- `POST /agents/{name}/training-sets/{id}/versions` —
  create new version
- Analogous paths for `rag-corpora`, `adapters`,
  `prompts`, `harnesses`, `routes`, `experiments`,
  `snapshots`

**Candidate hybrid:** keep the flat `/training/sets` for
backward compatibility (deprecate on a schedule) + add
nested `/agents/{name}/...` surface for new usage.

**My lean:** hybrid — add nested routes; keep flat as
deprecated aliases for 1-2 releases. Reduces disruption to
TB-US-010/017/041 UI already shipped.

**Open — see §12 Q9 for URL schema timing.**

---

<a id="sec-11"></a>

## 11. Follow-up stories unlocked

Once this architecture stabilizes, these stories execute:

1. **TB-US-NN — agents table + CRUD endpoints.** Schema +
   `/agents` endpoints. Admin UI minimal (list in admin
   modal). **Blocking for first versioned agent.**
2. **TB-US-NN — versioned-component schema migration.**
   Add all six `*_versions` tables; add `agent_name` +
   `component_name` + `version_tag` + hash columns to
   `training_sets`; migration script with pre-snapshot.
   **Blocking.**
3. **TB-US-NN — training-set versioning.** Lifecycle flow
   (draft → released → deprecated); content hashing;
   UI additions on training_sets.html. **Blocking for
   first adapter training against a versioned training
   set.**
4. **TB-US-NN — RAG versioning.** Lifecycle + manifest
   hashing; UI additions on manage-databases view.
5. **TB-US-NN — adapter versioning.** Hashing of adapter
   directory; linkage to training_run_id + training_set_version_id.
6. **TB-US-NN — prompt + routes versioning.** Migrate
   `AppSettings` current values to v1; new CRUD endpoints
   `/agents/{name}/prompts/versions`.
7. **TB-US-NN — eval harness subsystem.** New entity;
   schema + CRUD; rubric runner. (Likely overlaps with
   TB-US-043's eval harness work.)
8. **TB-US-NN — URL schema migration.** Nested routes
   added; flat deprecated; admin modal + left-nav updated
   to use agent-aware paths.
9. **TB-US-NN — agent-based admin UI.** List + create /
   retire agents; per-agent dashboard.

**Minimum arc for first versioned agent:** stories 1, 2, 3
(agent entity + schema migration + training-set versioning).
Everything else lands incrementally.

**Coordinator opportunity:** this is clearly a multi-story
arc. Opening a coordinator story (TB-US-NN) when the first
few sub-stories kick off is worth considering (per the
`feedback_coordinator_not_epic` memory).

---

<a id="sec-12"></a>

## 12. Open questions for operator decision

Each question has: context, options, my lean. Mark answered
with **Decision:** line.

### Q1 — Formal agent definition

**Decision (2026-10-16):** Approved.

> *"The agent becomes the top level entity at this time."*

Agent is TB's top-level organizing entity. All artifacts
generated and their versions belong to the agent. §1 as
drafted stands.

---

### Q2 — Agent lifecycle states

**Decision (2026-10-20):** **2 states** — `active` and
`retired`. Keep it minimal for v0.1.

- `active` — agent is live; experiments/snapshots can be
  created and promoted
- `retired` — agent is no longer being developed; existing
  snapshots preserved; new experiments blocked

Richer states (`draft`, `archived`, `suspended`, etc.) can
be added in a future story if the distinction becomes
meaningful. The current `active`/`retired` pair covers the
v0.1 operational needs without introducing state-machine
complexity.

---

### Q3 — Component types in v0.1

**Decision (2026-10-16):** All 6 component types in scope.

Operator statement: *"all artifacts generated and their
versions belong to the agent."*

Execution order of the per-type stories is picked by
follow-up priority, not architectural scope. The design
treats RAG, training set, adapter, prompt, harness, routes
all as agent-owned versioned components.

---

### Q4 — Content hashing scheme

**Decision (2026-10-20):** **SHA-256 only.** Simple,
widely-supported, cryptographically-secure, and sufficient
for drift-detection + integrity verification.

- Standard library (`hashlib.sha256`) — no external deps
- Universal recognition — hash values are self-identifying
  via length (64 hex chars) and operator can verify with
  common CLI tools (`sha256sum`, `shasum -a 256`)
- Fast enough for TB's artifact scale (training sets up to
  a few MB; adapters up to ~500 MB; one-time hash on
  release-to-released transition)
- No multi-hash complexity (BLAKE3 would be faster but adds
  dependency; drift-detection doesn't need the speed)
- No content size / timestamp in the hash (orthogonal
  metadata; captured separately in the version row)

Drift detection: on read of a `released` version, TB can
recompute SHA-256 and warn if it differs from the stored
one.

---

### Q5 — Query routes as agent-owned

**Decision (2026-10-16):** Agent-owned (option A).

Query routes become a per-agent versioned component. The
global `AppSettings.query_routes` becomes `v1` for a
`default` agent on migration, and new agents get their own
versioned routes.

---

### Q6 — Can two agents reference the same adapter?

**Decision (2026-10-16):** No sharing between agents, now
or near-term.

Operator statement: *"we can keep those boundaries with no
shared components between agents. they may be in the
future, but not now and it is not needed."*

Each agent's components are its own. If a trained adapter
proves reusable across agents in the future, that's a
separate story (join table or copy-with-shared-content_sha256
pattern) when the use case materializes. Not now.

Design implication: `agent_name` is NOT NULL on every
versioned-component table. No cross-agent references, no
shared-ownership rows.

---

### Q7 — Component lifecycle refinements

**Decision (2026-10-20):** **3 states** — `draft`,
`released`, `deprecated`. Hold v0.1 complexity down.

**Behavior:**
- `draft` — editable; not usable in snapshots
- `released` — immutable; usable in snapshots; content
  hash locked
- `deprecated` — hidden from new snapshot creation;
  existing snapshots that pin it continue to function
  (preserved for reproducibility)

**No `broken` state in v0.1.** If a released version turns
out to have a bug:
- Mark it `deprecated` to hide from new snapshots
- Release a fix as a new version (`v2`)
- Existing snapshots pinning the buggy version still
  function but are flagged in operator-facing views
- Operator can deliberately re-promote a snapshot that
  uses the fixed version

**No `candidate` state in v0.1.** Multiple drafts for the
same `(agent, component_name)` are already allowed (per
§4.2's identity model); "candidate" is just a convention
operators can use via naming (e.g. `v2-rc1`).

**Transitions remain one-way:**
- `draft → released` (operator action; locks content)
- `released → deprecated` (operator action; soft hide)
- Backward transitions NOT allowed (released cannot return
  to draft; deprecated cannot return to released)

---

### Q8 — Migration timing

**Decision (2026-10-20):** **Option C — Hybrid (schema-
first, data-later).** Minimizes risk at any single step
by separating structural work from data mutations.

**Execution sequence:**

1. **Schema story** (first execution follow-up): add all six
   `*_versions` tables + the `agents` table (per TB-US-048).
   Empty schema; no legacy data touched. Low-risk: pure
   DDL; if migration script fails, nothing is lost.
2. **Per-component data migration stories** (sequential):
   - Training-set versioning (TB has the most existing
     rows; good first real test; backfill into
     `training_set_versions`)
   - Adapter versioning (adapter files + training_run FKs)
   - RAG versioning (chroma collections + manifests)
   - Prompt + routes versioning (`app_settings.json`
     values become `v1`)
   - Eval harness subsystem (fresh build; no legacy
     migration)
3. Each per-component migration gets its own TB-US-NN
   with its own rollback plan and verification steps.

**Why not big-bang (Option A):**
- One failure point for 6+ data migrations is high-stakes
- Harder to roll back selectively if one component
  migration breaks something
- Operators can't test each piece in isolation

**Why not per-component with no schema-first (Option B):**
- Each per-component story would need to add its own
  table — more coupling between stories
- Schema-first lets all follow-ups reference a stable
  layout

**Pre-migration snapshots:** every data-migration story
snapshots `users.db` (or whichever DB the component lives
in) before executing. Preserves rollback path.

---

### Q9 — URL schema migration timing

**Decision (2026-10-20):** **Option B — Soft (keep flat
routes indefinitely as aliases).**

- Nested routes (`/agents/{name}/training-sets`, etc.) are
  added **additively** as the agent entity rolls out
- Flat routes (`/training/sets`, etc.) **remain in place**
  with no deprecation schedule
- Both route families coexist; backend handlers either
  dispatch to the same business logic or the flat route
  implicitly uses the current agent's context

**Why not immediate deprecation (Option A):**
- TB-US-010 / 017 / 041 admin UI + existing script.js code
  depends on flat routes; disrupting them without
  clear operator benefit is cost
- Only one operator team at v0.1 — no multi-tenant
  pressure to tighten URL semantics

**Why not post-migration deprecation (Option C):**
- Even post-migration, flat routes keep working as
  "current-agent-scoped" paths; no reason to break them

**When to revisit:**
- If TB ever gains multiple-concurrent-agent-contexts in
  one tab (not currently planned), flat routes become
  ambiguous and need deprecation
- If a formal API versioning scheme (v1 / v2 / etc.)
  arrives, flat routes could be labeled v1-legacy
- Not v0.1 scope.

**Deployment implication:** no code deletion when nested
routes land. All existing frontend code (user_management.js,
left_nav.js, script.js) continues to call flat routes.
Only new agent-aware code uses the nested form.

---

### Q10 — Where do the versioning primitives live?

**Decision (2026-10-20):** **Option C — Python base class
/ mixin.** SQL stays per-table (6 separate `*_versions`
tables, matching §5); shared logic (hash computation,
status transitions, lineage traversal, etc.) lives in a
Python base manager class that each per-component manager
subclasses.

**Why not Option B (SQL polymorphism):**

- Discriminator-column schemas (`component_versions.type`)
  trade schema clarity for row-level space savings — not a
  win at TB's scale
- Join queries become more complex when the "which type is
  this?" branch has to happen at query time
- Per-table schemas can diverge gracefully as component-
  specific columns multiply (adapter has `hyperparameters`
  JSON; RAG has `chroma_collection`, etc.)

**Why not Option A (pure duplication):**

- Hash computation + state-transition logic + lineage
  queries are inherently shared; duplicating them across
  6 manager classes is bug-prone
- Operator / future-maintainer confusion if `set_released()`
  does subtly different things in different managers

**Implementation outline:**

```python
class VersionedComponentManager:
    """Base class for RAG / training-set / adapter / prompt /
    harness / routes version managers. Shared behavior:
    hash computation, status transitions, lineage, change
    detection."""
    table_name: str  # overridden by subclass
    ...
    def _hash_content(self, content: bytes) -> str: ...
    def set_released(self, version_id: int, actor: str): ...
    def set_deprecated(self, version_id: int, actor: str): ...
    def get_lineage(self, version_id: int) -> List[Dict]: ...

class RAGVersionManager(VersionedComponentManager):
    table_name = "rag_versions"
    # + component-specific methods (manifest_hash, etc.)

class TrainingSetVersionManager(VersionedComponentManager):
    table_name = "training_set_versions"
    # + component-specific methods
```

Each component-specific manager inherits the shared logic,
operates on its own table, and adds component-specific
methods as needed.

---

### Q11 — Administrative-surface UX pattern

**Decision (2026-10-20):** **Option A — top-bar avatar/
account menu**, with role gating + first-run gating per
sub-decisions below. Operator noted: *"take the lean and
I will test it and if I think it needs changes I will
write another story to update it."* Reactive iteration
is accepted path if the shipped UX surfaces friction.

**Position + styling:** top-right of the main-app header;
text chip with chevron (`admin ▼`); no icon — keeps
header chrome clean, operator identity is text content.
Replaces the previous spot where Users/Logout buttons sat
(both cleaned out via TB-US-045 Tweaks 8 + 9).

**Dropdown contents:**

```
┌──────────────────┐
│ admin      │  ← identity cue (username)
│ super            │  ← role indicator
├──────────────────┤
│ 👥 Users         │  ← super-only; opens admin modal (TB-US-017/041)
│ 🔑 API Keys      │  ← super-only; placeholder/disabled at v0.1
│ ⚙️ System Config │  ← super-only; placeholder/disabled at v0.1
└──────────────────┘
```

**Role gating (Q11a):** menu renders for all authenticated
users (identity cue is universal); admin items are
**super-only**. Non-super users see just their username +
role in the dropdown with no actions.

**First-run gating (Q11b):** avatar menu renders only on
authenticated main-app pages (`index.html`,
`training_sets.html`, `training_runs.html`). NOT on
`gate.html`, `login.html`, or `first-change-password.html`.

**Pre-login layering (Q11c):** no design conflict with the
pre-login access gate (Q9a's SITE_PASSPHRASE); avatar
requires auth which happens after both gate and login.

**Interaction (Q11d):** click avatar chip → dropdown opens
below (CSS absolute, right-aligned); closes on
outside-click, Escape, or item-select.

**Logout stays independent** of this menu. Lives at drawer
footer per TB-US-045 Tweak 8. Avatar menu is admin tier
only; Logout is identity-flow action.

### Follow-up story this unlocks

**TB-US-NN — Avatar/account menu component.**

- Add header-right chip + dropdown on 3 main-app HTML
  pages
- Dropdown dispatches to `openUserManagement()` (existing)
  for 👥 Users entry
- Add placeholder entries (disabled styling) for 🔑 API
  Keys + ⚙️ System Config
- Role-filter per Q11a (super sees admin items; others see
  identity only)
- Not applied to `gate.html` / `login.html` /
  `first-change-password.html`
- Cache-bust bumps on all affected static files

**Follow-up stories this interacts with:**

- TB-US-047 §8 story #1 (admin password bootstrap) —
  avatar menu first appears post-forced-change
- Future "API Keys management" story (not yet drafted) —
  enables the 🔑 placeholder
- Future "System Config" story (not yet drafted) —
  enables the ⚙️ placeholder

### Growth path

If the admin tier grows beyond 3-4 items (adding Audit Log
viewer, Install diagnostics, etc.), the dropdown becomes
unwieldy. At that point:

- Introduce `/static/admin.html` dedicated page
- Reduce the dropdown to a single `⚙️ Admin →` link that
  opens the admin page
- Admin page has its own left nav for the various admin
  sub-features

**Not v0.1 scope.** The dropdown-grows-to-admin-page
evolution path is captured here as future design direction;
story to be drafted when the item count justifies it.

### Operator reactive-iteration path

Operator will test the shipped avatar menu and may surface
UX issues (positioning, dropdown behavior, item ordering,
etc.). Per `feedback_ui_changes_organic` memory, small
tweaks land in the TB-US-045 umbrella; larger changes
earn their own stories. Shape:

- Minor polish (icon-vs-text, color, spacing) → TB-US-045
  Tweak NN
- Role-model changes (new user types, different gating) →
  dedicated story
- Content changes (new admin items, reorganization) →
  dedicated story

---

### Q12 — Agent-selector UX (deferred 2026-10-20 to TB-US-048)

**Decision (2026-10-20):** **Deferred to TB-US-048** (Agent
editor — CRUD + admin UI + agent-selector UX).

**Operator rationale (2026-10-20):** *"we can walk Q12, but
without an agent editor there are no agents to edit."* Q12
is coupled UX with the editor it switches between; the
editor concept must exist before the selector UX design is
grounded. Resolved by consolidating all three concerns
(backend CRUD + admin UI + selector) into TB-US-048.

**Preview of resolution** (locked in TB-US-048 R14-R18):

- **Agent-selector location:** top of drawer, immediately
  below `← Close` button. Spans drawer width. Visually
  distinct (background accent, bottom border).
- **Format:** `📂 Current agent: {name} ▼`
- **Interaction:** click → dropdown lists all `active`
  agents + "Manage agents →" link to the admin UI
- **Context switch:** clicking an agent writes
  `tb_current_agent` to localStorage per-browser; drawer
  re-populates agent-scoped items; drawer stays open
- **Multi-tab:** each browser tab tracks its own current
  agent (independent); alternative "sync across tabs"
  rejected for v0.1

Full design + rollout plan in TB-US-048. This TB-US-044
spike closes without resolving Q12 in its own doc; the
resolution lives downstream.

**Pattern note:** matches how Q13 was deferred to TB-US-047
(zero-agent / default-agent handling). Both cases: a
spike-level question properly belonged in a downstream
execution story; TB-US-044 captures the decision via
cross-reference without duplicating the design content.

---

### Q13 — Zero-agent / default-agent handling (resolved 2026-10-18 via TB-US-047)

**Decision (2026-10-18):** Delegated to and resolved by
TB-US-047 (First-run / onboarding architecture spike):

> *Ship ONE example agent (`math-example`) on first install,
> structured as a measurable 3-stage experiment progression
> that teaches the newcomer what each agent component
> contributes. After operator action (rename, create, delete)
> zero agents allowed — drawer shows empty-state UI.*

Supersedes the placeholder-`default` framing originally
proposed in this story. See TB-US-047 §4 for the full
staged-progression design and docs/design/first-run-onboarding.md
§4 for the newcomer journey.

**Implications for TB-US-044 architecture:**

- `agents` table + schema per §3-§6 **still correct**;
  `math-example` is just the first row created on install
- `created_by` for the shipped agent → `admin` (or env-
  override admin username)
- No special-case code for "shipped agents" — they're
  regular agents, just seeded during the install flow
- Zero-agent state is a valid system state (not an error);
  drawer handles it with an empty-state UI

---

<a id="sec-13"></a>

## 13. Decision log

| Date | Decision | Context |
|---|---|---|
| 2026-10-16 | Spike opened (TB-US-044) | Operator design signal — agent + version management is foundational to TB-US-043 Sweet Spot work |
| 2026-10-16 | **Q1 — Agent is TB's top-level entity** | "The agent becomes the top level entity at this time." |
| 2026-10-16 | **Q3 — All 6 component types in v0.1 scope** | "All artifacts generated and their versions belong to the agent." |
| 2026-10-16 | **Q5 — Query routes are agent-owned (not global)** | Routes follow retrieval; retrieval is per-RAG; RAG is per-agent. |
| 2026-10-16 | **Q6 — No cross-agent component sharing (now or near-term)** | "We can keep those boundaries with no shared components between agents. They may be in the future, but not now and it is not needed." |
| 2026-10-17 | **Two-tier architecture captured** | "Agents are at the top of the food chain except for administrative management like users and keys." Agents own all productive work; Users/API keys/system config are the small administrative tier above. See §1.a. |
| 2026-10-17 | **The drawer is an agent-contextualized workspace, not a flat nav list** | 11 of 11 current drawer items are agent-scoped. Future drawer will have an agent-selector + agent-scoped items beneath it. System items (Users, API keys) do NOT belong in the drawer; they get their own administrative surface (see §12 Q11). |
| 2026-10-18 | **Q13 resolved via TB-US-047** | Fresh install ships ONE example agent (`math-example`) structured as a measurable 3-stage experiment progression (bare LLM → +RAG → +adapter) with scored results. Supersedes the placeholder-`default` framing. Zero agents allowed after operator action. See TB-US-047 §4 for full design. |
| 2026-10-20 | **Q2 — Agent lifecycle: 2 states (active / retired)** | Minimal state model for v0.1. `active` = live; experiments/snapshots can be created and promoted. `retired` = no longer being developed; existing snapshots preserved; new experiments blocked. Richer states (draft, archived, suspended) can be added in a future story if the distinction becomes meaningful. |
| 2026-10-20 | **Q4 — Content hashing: SHA-256 only** | Standard library (`hashlib.sha256`), no external deps. Fast enough for TB's artifact scale. Universal CLI recognition for operator verification. No multi-hash (BLAKE3) complexity. Content size + timestamp captured as separate columns in the version row, not folded into the hash. Drift detection via re-hash on read of `released` versions. |
| 2026-10-20 | **Q7 — Component lifecycle: 3 states (draft / released / deprecated)** | Minimal 3-state model for v0.1. `draft` editable; `released` immutable and usable in snapshots; `deprecated` hidden from new snapshots but existing snapshots that pin it continue to function. No `broken` state (deprecate buggy versions + release a fix). No `candidate` state (operators use naming conventions like `v2-rc1` instead). All transitions one-way. |
| 2026-10-20 | **Q10 — Python base class/mixin for versioning primitives** | Option C. SQL stays per-table (6 separate `*_versions` tables). Shared Python base class (`VersionedComponentManager`) carries hash computation, state transitions, lineage traversal. Component-specific manager classes subclass and add their domain-specific methods. Avoids SQL polymorphism complexity + preserves per-component column divergence. |
| 2026-10-20 | **Q11 — Administrative-surface UX: top-bar avatar/account menu (Option A)** | Text chip with chevron (`admin ▼`) in top-right header; opens dropdown with identity cue + super-only admin items (Users / API Keys / System Config). Role-gated: menu renders for all authenticated users but admin items super-only. First-run-gated: not visible on gate.html, login.html, first-change-password.html. Logout stays independent (drawer footer per TB-US-045 Tweak 8). Future growth path to dedicated admin page if items > 3-4. Operator will test post-ship + spawn reactive-iteration story if friction surfaces. |
| 2026-10-20 | **Q12 — Agent-selector UX: deferred to TB-US-048** | Operator insight: "we can walk Q12, but without an agent editor there are no agents to edit." Q12 is coupled UX with the editor; resolved by consolidating backend CRUD + admin UI + selector into TB-US-048. Preview locked: top-of-drawer dropdown ("📂 Current agent: {name} ▼"); multi-tab independence; "Manage agents →" link to admin UI. Full design in TB-US-048 R14-R18. Pattern matches Q13 → TB-US-047 deferral. |
| 2026-10-20 | **Q8 — Migration timing: schema-first-data-later (hybrid Option C)** | Execution sequence: (1) Schema story adds all `*_versions` + `agents` tables (empty); low-risk DDL. (2) Per-component data migration stories follow sequentially (training_sets → adapters → RAG → prompt+routes → eval harness). Each gets its own TB-US-NN with rollback plan + pre-migration DB snapshot. Minimizes risk; enables selective rollback. |
| 2026-10-20 | **Q9 — URL schema: soft (keep flat routes indefinitely as aliases)** | Option B. Nested routes added additively; flat routes `/training/sets` etc. remain functional for existing frontend code (user_management.js, left_nav.js, script.js). Both families coexist. No deprecation schedule. Revisit if multiple-concurrent-agent-contexts in one tab arrives (not planned) or if formal API versioning (v1/v2) is introduced. |
| 2026-10-20 | **All open questions resolved; TB-US-044 spike closes** | 13 questions total (Q1-Q13); 11 decided in-doc; Q12 deferred to TB-US-048; Q13 resolved via TB-US-047. Design content complete. Follow-up stories enumerated in §11; TB-US-048 drafted as first downstream story. |

---

<a id="sec-14"></a>

## 14. What comes after this architecture is approved

Once every question in §12 has a **Decision:** line and
the operator confirms the architecture is ready-to-execute-
against, the follow-up stories in §11 get drafted. The
TB-US-044 story closes with this document as its
deliverable; a coordinator story (TB-US-NN) likely opens
for the agent-execution arc.

TB-US-043 (Sweet Spot methodology) continues in parallel
and references this document for anything component- or
version-related.
