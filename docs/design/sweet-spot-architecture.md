# Sweet Spot Architecture — Design Notes

**Status:** Draft (operator-collaborative; iterate across turns)
**Owned by:** TB-US-043
**Related:** TB-US-044 (Agent architecture + versioned-component management — parallel spike; foundational for the schema details referenced here)
**Created:** 2026-10-15
**Last updated:** 2026-10-16

> **Scope boundary (2026-10-16):** The component /
> versioning architecture (agents table, versioned-
> component schema, RAG/training-set/adapter/prompt/harness/
> route versioning, content hashing, lifecycle) moved to
> TB-US-044. This doc defers to
> `docs/design/agent-architecture.md` for anything in those
> areas. What stays here: Sweet Spot vocabulary (recipe,
> snapshot, Sweet Spot), experimentation methodology,
> before/after comparisons, promotion flow, first-example
> math walkthrough.

> **This is a working document.** It will evolve as the operator
> and Claude Code iterate on the open questions below. Each
> design decision is captured as it stabilizes. The document is
> "ready to execute against" when every open question has a
> **Decision:** line and the follow-up stories (§8) are drafted.

---

## Table of Contents

1. [What is a Sweet Spot?](#sec-1)
2. [Combinatorial space](#sec-2)
3. [Data model](#sec-3)
4. [Tracking surface](#sec-4)
5. [Logging surface](#sec-5)
6. [UI surfaces (named, not designed)](#sec-6)
7. [Naming + categorization](#sec-7)
8. [Follow-up stories unlocked by this design](#sec-8)
9. [Open questions for operator decision](#sec-9)
10. [Out of Scope (for the Sweet Spot architecture, not just this story)](#sec-10)
11. [Decision log](#sec-11)
12. [What comes after this design is approved](#sec-12)

---

<a id="sec-1"></a>

## 1. What is a Sweet Spot?

**Definition (operator-approved 2026-10-15):**

> A **Sweet Spot** is the current winning combination of
> (system prompt, RAG, LLM, PEFT adapter) identified using
> a collection of before/after experiments designed to find
> the highest performance combination of agent components.

**Three load-bearing words:**

- **Current** — the Sweet Spot is live-right-now,
  displaceable. When a better combination emerges, it
  replaces the previous Sweet Spot. The previous one isn't
  deleted; it's displaced (see state model, §4).
- **Collection** — the Sweet Spot emerges from a tournament
  of before/after comparisons, not a single A/B measurement.
  Many experiments feed into "the current winner" status.
- **Highest performance** — the search is purposeful.
  "Performance" is the composite score produced by an eval
  harness (accuracy, latency, quality — operator-defined
  per deployment). Not "any improvement wins"; the search
  seeks the maximum.

**Four axes:**

1. **System prompt** — the template used by RAG at
   generation time (what `AppSettings.rag_prompt` controls
   today; TB-US-033 shipped the surface).
2. **RAG** — which chroma collection is retrieved against.
3. **LLM** — the base model (Ollama name or raw API model
   target).
4. **PEFT adapter** — a fine-tuned adapter on the base LLM,
   or `None` (raw base LLM).

The **eval harness** is *not* a Sweet Spot axis. It's the
measuring instrument — a sidecar used to produce
performance scores against any experiment. Multiple
experiments can be measured by the same harness; one
experiment can be re-measured by a new/better harness.

---

<a id="sec-2"></a>

## 2. Combinatorial space

The experiment space has shape **{system_prompts} ×
{RAG_sets} × {LLMs} × {adapters}**.

A single organization typically has:
- 1-few system prompt variants (phrasings of the agent's
  instructions)
- 1 or a few RAG datasets (their domain corpus)
- 1-3 candidate LLMs under evaluation
- 0..N PEFT adapters (trained on their training sets)

So the combinatorial space per organization is modest in
practice — tens, not thousands. The isolate-one-variable
experimental design (change exactly one axis vs the
baseline) keeps the practical search path small even when
the full product is large.

**Eval harnesses are NOT on the axes** — they're the
measuring instrument. Several experiments can share one
eval harness; one experiment can be re-measured by a new
harness. The eval harness defines what "highest
performance" (per §1) means for a given domain.

TB in v0.1 is **single-operator-team**; multi-tenant is Out
of Scope per TB-US-043.

**Open — see §9 Q2 for how we constrain / enumerate the space.**

---

<a id="sec-3"></a>

## 3. Data model

### 3.1 Existing building blocks (TB today)

| Entity | Table / file | What it is |
|---|---|---|
| User | `users.db → users` | Operator accounts |
| Training set | `users.db → training_sets` + JSON file at `file_path` | Curated set of (instruction, input, output) examples |
| Training run | `users.db → training_runs` (via `training_run_tracker`) | Record of a `training/math/train.py` invocation |
| RAG DB | `database_config.json` + chroma collection | Vector store configuration |
| App settings | `app_settings.json` | `rag_prompt`, `query_routes`, `demo_mode`, `active_database` |
| Audit log | `users.db → admin_audit` | Admin-action trail |
| Session tracker | `users.db → sessions` | User login sessions |
| Training session | `logs/training_sessions/session_<u>.json` | SME curation sessions (TB-US-019) |

### 3.2 What's missing for a Sweet Spot concept

There is **no `experiments` entity** today — the three
axes (RAG, LLM, adapter) exist but their combination into a
testable unit isn't recorded.

**Candidate schema (draft — operator to validate):**

```sql
CREATE TABLE experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,              -- e.g. 'math-llama31-full-stack-v1'
    description TEXT,                -- operator intent
    -- Four axes (the Sweet Spot's configurable surface):
    system_prompt TEXT,              -- rag_prompt variant used
    rag_database_id TEXT,            -- which chroma collection
    base_llm TEXT,                   -- e.g. 'llama3.1:8b'
    adapter_name TEXT,               -- resulting PEFT adapter name; NULL = raw base LLM
    -- Lineage + comparison:
    parent_experiment_id INTEGER,    -- lineage pointer; NULL for root
    compared_to_experiment_id INTEGER, -- the "before" this is a candidate "after" of; NULL for standalone
    -- Training context (how the adapter got built, if any):
    training_set_id INTEGER,         -- FK → training_sets
    training_run_id INTEGER,         -- FK → training_runs
    -- Lifecycle:
    status TEXT CHECK (status IN
        ('draft', 'running', 'completed', 'promoted', 'displaced', 'archived')),
    scope TEXT,                      -- e.g. 'math', 'cuad', 'default' — see Q12
    promoted_at TEXT,                -- stamp when flipped to promoted; NULL otherwise
    promotion_notes TEXT,            -- why this won; "+34% on arithmetic, no regression on lookups"
    displaced_at TEXT,                -- stamp when another experiment superseded this one
    displaced_by_experiment_id INTEGER, -- which experiment superseded it
    -- Audit:
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    metadata TEXT                    -- JSON blob for extensibility
);

CREATE TABLE eval_harnesses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    scope TEXT,                      -- 'math', 'cuad', 'default' — pair with experiments.scope
    rubric_json TEXT,                -- scoring criteria
    test_prompts_file TEXT,          -- path to JSONL of test prompts
    primary_metric TEXT,             -- which field in results defines "performance" ranking
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL
);

CREATE TABLE experiment_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id INTEGER NOT NULL,
    harness_id INTEGER NOT NULL,     -- chosen at measurement time, not config time
    ran_at TEXT NOT NULL,
    metrics_json TEXT,               -- {accuracy: 0.87, mean_latency_ms: 234, ...}
    primary_metric_value REAL,       -- denormalized for sorting/ranking: performance score
    report_file TEXT,                -- path to full eval report
    FOREIGN KEY (experiment_id) REFERENCES experiments(id),
    FOREIGN KEY (harness_id) REFERENCES eval_harnesses(id)
);
```

**Key change from first draft:**

- Dropped `eval_harness_id` from `experiments` — harness is
  chosen at measurement, not configuration. The relationship
  lives on `experiment_results` only (an experiment can be
  measured by multiple harnesses over its life).
- Added `compared_to_experiment_id` — the explicit "before"
  pointer. If experiment A is a tweak intended to compare
  against baseline B, A.compared_to = B.id. Enables the
  comparison report.
- Added `scope` on both experiments and harnesses — see
  Q12. Needed so "current winner" can be queried as
  "promoted experiment in scope X."
- Added `displaced` state + `displaced_at` + `displaced_by`
  — see Q11. Captures tournament tail.
- Added `primary_metric` + `primary_metric_value` — the
  "performance" word in the §1 definition needs a specific
  field on the harness that defines ranking.

**Open — see §9 Q3-Q5 for data-model decisions.**

---

<a id="sec-4"></a>

## 4. Tracking surface

### Per-experiment metadata (candidate):

- **Intent** — what the operator wants to prove / verify
- **Inputs** — training_set, base_llm, rag_db, eval_harness
- **Outputs** — adapter_name, metrics, report
- **Lineage** — parent_experiment_id (if this is a tweak of an earlier one)
- **Status** — lifecycle state (draft → running → completed → promoted or archived)
- **Audit** — who created, who modified, timestamps
- **Notes** — operator's running commentary

### Experiment states (updated per §1 Decision):

| Status | Meaning | Transitions out |
|---|---|---|
| `draft` | Configured; not yet trained | → running (operator starts training) |
| `running` | Training in progress | → completed (training + eval done) |
| `completed` | Trained + at least one eval result captured | → promoted (operator picks as current winner), → archived |
| `promoted` | **Current Sweet Spot** for this scope. At most one per scope. | → displaced (another experiment is promoted in the same scope) |
| `displaced` | Was once the current Sweet Spot; superseded. Kept for history. | → archived |
| `archived` | Historical; hidden from active views. | — |

**Promotion mechanics:**

- When operator flips `completed → promoted` in scope X:
  1. The experiment's `promoted_at` + `promotion_notes` are
     stamped.
  2. If another experiment in scope X is currently
     `promoted`, it is **automatically flipped to
     `displaced`** with `displaced_at` + `displaced_by`
     stamps.
  3. Audit log entry records the handoff.
- Invariant: at most one `promoted` experiment per scope at
  any time. Enforced by the promotion endpoint (database
  CHECK via a partial unique index is a nice-to-have).

**Open — see §9 Q11 for displacement edge cases + Q12 for scope.**

---

<a id="sec-5"></a>

## 5. Logging surface

### Phase-by-phase log map:

| Phase | What's logged | Where |
|---|---|---|
| **Curation** | Training set CRUD + example edits | `users.db → training_sets` + file timestamps + `admin_audit` |
| **Training** | Per-step losses, eval metrics, checkpoints | `training_run_tracker` (existing) |
| **Evaluation** | Per-prompt score + rubric breakdown | `experiment_results` + report file (NEW) |
| **Query / inference** | Per-prompt + which Sweet Spot answered + response | `query_logger` (existing) — **needs `experiment_id` column** |
| **OT classifier decisions** | Per-prompt category + handler chosen | TB-US-024's `logs/ot_audit/` (future) |

### Query traceability requirement:

Given a production query, we should be able to trace back to:
1. Which Sweet Spot answered it
2. Which training_set + adapter + RAG dataset produced that Sweet Spot
3. Which training run produced the adapter
4. Which operator curated the training set

**Design implication:** `query_logger` row needs a nullable
`experiment_id` field. When a request comes in without an
experiment context (raw baseline test), it's null. When
served through a promoted Sweet Spot, it's populated.

**Open — see §9 Q7 for traceability decisions.**

---

<a id="sec-6"></a>

## 6. UI surfaces (named, not designed)

| Surface | What it does | Follow-up story |
|---|---|---|
| **Experiment list** | Table of experiments with status, metrics summary, created_by | New TB-US (schema + UI) |
| **Experiment detail** | Full metadata + metrics + lineage tree + action buttons | Same |
| **Experiment compare** | Side-by-side metrics across 2-N experiments | Same |
| **Eval harness list** | CRUD for test-prompt sets + rubrics | New TB-US |
| **Agent Release list** | Promoted Sweet Spots as deployable packages | TB-US-030 |
| **Audit trail viewer** | Already exists for admin actions (TB-US-017); extend to experiment lifecycle events | Possibly fold into TB-US-017's audit viewer |

**Note:** None of this UI should be built in TB-US-043. Each
surface is a separate downstream story.

---

<a id="sec-7"></a>

## 7. Naming + categorization

**Candidate convention** (operator to validate):

- Experiment name: `<domain>-<base_llm>-<variant>-vN`
  - Example: `math-llama31-with-rag-v2`
  - Example: `cuad-mistral7b-baseline-v1`
- Human-written description required (not optional)
- Parent experiment pointer (optional) for lineage

**Project / hierarchy question:**

Should experiments nest under a "project"? Options:

1. **Flat** — just experiments. Simplest.
2. **2-level** — `project → experiment`. Enables grouping.
3. **3-level** — `project → experiment → run` where `run`
   is a specific execution of an experiment config.

**Open — see §9 Q8 for hierarchy decision.**

---

<a id="sec-8"></a>

## 8. Follow-up stories unlocked by this design

Once this design stabilizes, the Sweet Spot execution arc
breaks into stories like:

1. **TB-US-NN — Experiment schema + CRUD.** Add
   `experiments`, `eval_harnesses`, `experiment_results`
   tables. CRUD endpoints. No UI. **Blocking for first
   experiment.**
2. **TB-US-NN — Eval harness subsystem.** Define rubric
   JSON shape; endpoint to run harness against an experiment;
   writes `experiment_results`. **Blocking for first
   verifiable experiment.**
3. **TB-US-NN — Query logger `experiment_id` column.**
   Add the field; wire into inference path. Non-blocking
   for first experiment but needed before anything is
   "promoted."
4. **TB-US-NN — Experiment UI (list + detail + compare).**
   TB-US-017-style modal or dedicated page.
5. **TB-US-NN — First-example Sweet Spot build.** The
   actual first-experiment story. Likely math-domain to
   align with TB-US-029 verification example.
6. **TB-US-030 (exists)** — Build-and-deploy custom agent
   operator workflow. Downstream of the first Sweet Spot.
7. **TB-US-NN — Promote-to-Agent-Release flow.** UI + API
   for moving a `completed` experiment to `promoted`
   status.
8. **TB-US-NN — Experiment lifecycle audit log.** Capture
   state transitions; may fold into TB-US-017's audit
   subsystem or be its own log.

**Minimum arc for first operational Sweet Spot:** stories
1, 2, 5 (= experiment schema + eval harness + first-example
build). Everything else is nice-to-have.

---

<a id="sec-9"></a>

## 9. Open questions for operator decision

Each question has: context, options, operator's lean (if
captured). Mark answered with **Decision:** line.

### Q1 — Formal definition of Sweet Spot

**Decision (2026-10-15):**

> *"A Sweet Spot is the current winning combination of
> (system prompt, RAG, LLM, PEFT adapter) identified using a
> collection of before/after experiments designed to find the
> highest performance combination of agent components."*

Captured verbatim in §1. Load-bearing words: **current**
(displaceable), **collection** (tournament, not single A/B),
**highest performance** (purposeful search).

**Impact on §4 state model** — the simple `promoted` state
isn't sufficient. See new Q11 (displacement semantics).

**Impact on §2 combinatorial space** — eval harness drops
from the axes list. Four axes: system prompt, RAG, LLM, PEFT
adapter. Eval harness is a measurement sidecar. §2 updated.

---

### Q2 — Combinatorial space enumeration

**Decision (2026-10-20):** **Option A — hand-pick only.**
Each experiment is operator-created. The combinatorial
space exists conceptually but TB does not enumerate or
suggest cells. B/C (enumerated matrix / hybrid search) are
future enhancements if the practical experiment count ever
grows to warrant them.

For v0.1 the experiment count per agent is low (dozens, not
thousands); hand-picking is the right ergonomic default.

---

### Q3 — Is `experiments` a new first-class table?

**Decision (2026-10-20):** **Yes — new `experiments` table**
per TB-US-044 §3.2 and the versioned-component pattern.

Cross-reference: TB-US-044 established the uniform
versioned-component model that `experiments` follows. The
table is agent-owned (`agent_name` FK), carries status
through its own state machine (see Q6), and pins specific
versions of each component via FK columns. Full schema in
§3.2 of this doc.

---

### Q4 — Lineage representation

**Decision (2026-10-20):** **Option A — `parent_experiment_id`
self-referential FK** per the TB-US-044 pattern.

Cross-reference: TB-US-044 adopted self-ref FK for component
version lineage (`parent_version_id`). Experiments follow the
same pattern via `parent_experiment_id`. Simplest; works for
expected scale (dozens of experiments per agent, not
millions). Compare view queries this FK to render lineage
trees.

---

### Q5 — Eval harness: new table or reuse training_sets?

**Decision (2026-10-20):** **Option A — new `harness_versions`
table.** Cross-reference TB-US-044 §5.5 which specified the
dedicated schema (test_prompts_file + rubric_json +
primary_metric). The rubric + scoring criteria don't belong
on training_sets; eval harnesses have their own domain
columns.

---

### Q6 — Experiment state machine

**Decision (2026-10-20):** **6 states** per the design above:
`draft → running → completed → promoted → displaced`; any
state can transition to `archived`. Sub-decisions:

- **Re-promotion of a `displaced` experiment allowed.** If a
  new harness or new scoring reveals that an older
  experiment was actually better, operator can flip the
  current `promoted` to `displaced` and re-promote the
  older one. Both histories preserved.
- **No `running` sub-states.** Single `running` state with
  free-text `metadata.current_phase` is enough for v0.1.
  If graduated progress UX becomes desired, split later.

State model consistent with TB-US-044 §4 experiment state
model.

---

### Q7 — Query traceability — mandatory or optional?

**Decision (2026-10-20):** **Option B — nullable
`experiment_id`** on query log entries.

Baseline / non-Sweet-Spot-served queries record NULL;
queries served by a specific experiment (typically the
current Sweet Spot) record the experiment_id. Keeps schema
permissive without needing a special "no-experiment"
sentinel row.

Follow-up implementation: add `experiment_id` column
(nullable, FK to experiments) to the query_logger schema;
inference path populates it when the current agent has a
`promoted` experiment.

---

### Q8 — Hierarchy level

**Decision (2026-10-20):** **Resolved by TB-US-044 §1.a**
— agents are the top-level organizing entity (not
"projects"). Hierarchy is: `agent → experiments`. No
separate `run` level; a given experiment config has one
run captured in its result rows.

Supersedes earlier "project" framing from this doc's
initial draft. TB vocabulary now uses "agent" throughout
per the two-tier architecture decision.

---

### Q9 — Where does the OT classifier (TB-US-022+) fit?

**Decision (2026-10-20):** **OT configuration lives in
AppSettings (agent-scoped per TB-US-044 Q5); experiments
do NOT configure OT handlers themselves.**

Rationale:

- OT classifier is **routing policy** (which handler fires
  for which prompt type) — not experiment configuration
  (which RAG + LLM + adapter combo). Different lifecycle,
  different owners.
- Agents own their OT routing policy (per TB-US-044's
  Q5 decision that query_routes are agent-owned). OT
  handlers can be enabled/disabled per agent via the
  agent's AppSettings version.
- Experiments **observe** which handler fired via the
  query log (`query_id` + `experiment_id` per Q7) and
  `ot_audit` (TB-US-024). Attribution flows from the OT
  side; the experiment entity stays focused on
  model + data.

OT classifier evolution (per the TB-US-022+ arc) does NOT
force experiment schema changes. OT and experiments are
orthogonal concerns that compose at query time.

---

### Q11 — Displacement semantics

**Decision (2026-10-20):** All 3 leans accepted:

1. **Auto-displacement on promote within same agent.** Only
   one `promoted` experiment per agent at a time. Promoting
   a new experiment within the same agent automatically
   flips the previously-promoted one to `displaced` (with
   stamp fields populated).
2. **Scope = agent** per TB-US-044 §1.a (not NULL /
   "default-scope competition"). Each experiment has an
   agent_name FK; agent is the uniqueness boundary; no
   NULL-scope edge case.
3. **Un-promote allowed.** Operator can demote a current
   `promoted` experiment without promoting a replacement.
   Flips its status to `displaced` with
   `displaced_at = now`, `displaced_by_experiment_id = NULL`
   to indicate manual un-promote (no replacement). The
   agent is then in "no current Sweet Spot" state until
   another experiment is promoted.

Note: Q12 (scope of "current") resolves this fully — scope
is the agent, not a free-text field.

---

### Q12 — Scope of "current"

**Decision (2026-10-20):** **Per agent** per TB-US-044
§1.a + TB-US-048.

Scope collapses to the agent entity (not a free-text tag,
not a "domain" string, not "project"). Each agent has at
most one `promoted` experiment at any time. Uniqueness
enforced at the application layer (promotion endpoint
auto-displaces the previously-promoted experiment for the
same agent).

Schema implication: `experiments` table has `agent_name` FK
(matches the versioned-component pattern from TB-US-044).
No separate `scope` column needed; agent_name IS the scope.

Supersedes the earlier "scope as free-text tag" draft in
this doc's §3.2. Schema updated: `scope` column removed in
favor of relying on `agent_name` which is already present.

---

### Q13 — First-example choice: math or something else?

**Decision (2026-10-20):** **Math** — resolved by TB-US-047
Q3B.

Cross-reference: TB-US-047 Q3B decided the shipped install
example is `math-example`, structured as a 3-stage
progression (bare LLM → +RAG → +adapter). TB-US-043's
first-example question collapses to the same answer. The
math-example on install IS the first operational Sweet Spot
+ its 2 displaced predecessors (Stages 0, 1).

---

### Q14 — Labeling convention for experiments

**Decision (2026-10-20):** **Convention
`{agent}-{llm}-{what-varies}-v{N}` adopted.**

Note: "domain" in the earlier draft resolves to "agent"
per TB-US-044 §1.a (agents at top). Pattern updated.

**Examples (post-reframe):**

- `math-example-llama31-baseline-v1` — Stage 0: bare LLM,
  nothing added
- `math-example-llama31-prompt-only-v1` — adds system
  prompt tweak only
- `math-example-llama31-rag-only-v1` — Stage 1 proxy: adds
  RAG only
- `math-example-llama31-adapter-only-v1` — adds PEFT
  adapter only
- `math-example-llama31-full-stack-v1` — Stage 2: all
  three
- `math-example-llama31-full-stack-v2` — tweaked variant
  of the full stack (new RAG, new training set, etc.)

The pattern is operator-chosen free-text, validated for
basic sanity (`[a-z0-9_-]+`) but not strictly enforced
beyond that. Operators can diverge if a different scheme
better fits their domain; TB does not force the pattern.

Three-stage install uses this pattern for math-example's
Stage 0/1/2 experiment names, per TB-US-047 §4.

---

<a id="sec-10"></a>

## 10. Out of Scope (for the Sweet Spot architecture, not just this story)

- Multi-tenant isolation
- GPU scheduling / distributed training
- Model-weight versioning beyond adapter names
- Checkpoint auto-cleanup / retention
- Experiment branching UI (fork a running experiment)
- Dashboard / BI-style metrics rollups
- A/B testing production traffic (shadow a Sweet Spot
  with another)
- Billing / cost accounting per experiment
- Automated hyperparameter search
- Multi-adapter composition (LoRA-of-LoRAs)
- Branding tweaks (per the deferred-branding memory)

---

<a id="sec-11"></a>

## 11. Decision log

| Date | Decision | Context |
|---|---|---|
| 2026-10-15 | Spike opened (TB-US-043) | Operator deferred first experiment pending design (feedback_experiments_design_gated memory) |
| 2026-10-15 | **Q1 — Sweet Spot defined** | "The current winning combination of (system prompt, RAG, LLM, PEFT adapter) identified using a collection of before/after experiments designed to find the highest performance combination of agent components." Load-bearing: current, collection, highest performance. Eval harness is NOT an axis — measurement sidecar only. |
| 2026-10-20 | **Q2 — Hand-pick experiments (Option A)** | Each experiment operator-created; no matrix enumeration or system-suggested cells. Hand-pick is right default at TB's expected experiment count (dozens per agent, not thousands). B/C deferred as future enhancements if volume justifies. |
| 2026-10-20 | **Q3 — `experiments` is a new first-class table** | Resolved by TB-US-044 §3.2 versioned-component pattern. Table is agent-owned; carries status via state machine (Q6); pins specific component versions via FK columns. |
| 2026-10-20 | **Q4 — Lineage via `parent_experiment_id` self-ref FK** | Resolved by TB-US-044 pattern. Simplest; works at TB's expected scale. Compare view queries this FK to render lineage trees. |
| 2026-10-20 | **Q5 — Eval harness is a new table (`harness_versions`)** | Resolved by TB-US-044 §5.5. Dedicated schema (test_prompts_file + rubric_json + primary_metric). Not a training_sets variant. |
| 2026-10-20 | **Q6 — 6-state experiment lifecycle** | `draft → running → completed → promoted → displaced`; any state can `→ archived`. Re-promotion of a `displaced` experiment allowed. Single `running` state (no sub-states) for v0.1. Consistent with TB-US-044 §4. |
| 2026-10-20 | **Q7 — Nullable `experiment_id` on query log** | Option B. Baseline queries have NULL; Sweet-Spot-served queries record the experiment_id. No sentinel row needed. Follow-up implementation adds the column + populates from the inference path. |
| 2026-10-20 | **Q8 — Hierarchy: agent → experiments (not projects)** | Resolved by TB-US-044 §1.a. Agent is the top-level organizing entity. No separate "project" or "run" level. "Project" vocabulary dropped from this doc; everything uses "agent." |
| 2026-10-20 | **Q9 — OT config lives in AppSettings, not on experiments** | OT classifier is routing policy, not experiment configuration. Agents own their OT routing (per TB-US-044 Q5). Experiments observe which OT handler fired via query_logger + ot_audit; experiment entity stays focused on model + data. |
| 2026-10-20 | **Q11 — Displacement semantics (all 3 leans accepted)** | Auto-displacement on promote within same agent; agent IS the scope (no NULL / default competition); un-promote allowed (displaced_at=now, displaced_by=NULL). |
| 2026-10-20 | **Q12 — Scope = agent (not free-text tag)** | Resolved by TB-US-044 §1.a + TB-US-048. `experiments.agent_name` FK IS the scope; no separate scope column. Schema in §3.2 updated accordingly. |
| 2026-10-20 | **Q13 — First-example: math** | Resolved by TB-US-047 Q3B. The shipped math-example staged progression IS the first operational Sweet Spot (Stage 2) + its two displaced predecessors (Stages 0, 1). |
| 2026-10-20 | **Q14 — Labeling convention `{agent}-{llm}-{what-varies}-v{N}` adopted** | Operator-chosen free-text; validated for basic sanity (`[a-z0-9_-]+`); not strictly enforced. "Domain" in earlier draft resolves to "agent" per TB-US-044. Pattern used for math-example Stage 0/1/2 names. |
| 2026-10-20 | **All open questions resolved; spike closes** | 14 questions total; Q1 decided 2026-10-15; Q2, Q6, Q7, Q11, Q14 decided in-doc 2026-10-20; Q3, Q4, Q5, Q8, Q9, Q12 resolved by cross-reference to TB-US-044; Q13 resolved by cross-reference to TB-US-047. Design content complete. |

---

<a id="sec-12"></a>

## 12. What comes after this design is approved

Once every question in §9 has a **Decision:** line, the
operator confirms the design is ready-to-execute-against,
and the follow-up stories in §8 get drafted. The TB-US-043
story closes with this document as its deliverable; a new
coordinator story (TB-US-NN) opens for the Sweet Spot
execution arc if the follow-ups warrant orchestration.
