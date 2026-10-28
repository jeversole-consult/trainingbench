---
title: Concepts
description: TrainingBench's agent model + Sweet Spot vocabulary + two-tier architecture.
---

# Concepts

Reference for the vocabulary used throughout TrainingBench. Each term
has a precise meaning; the shipped UI uses them consistently.

## Agent

The **top-of-food-chain** entity. Everything functional in TrainingBench
is scoped to a specific agent: its RAG, its training set, its adapter,
its prompt, its experiments.

Multiple agents can live in one install. Each gets its own slug name
(e.g., `math-example`, `legal-contract-review`). Switching the drawer's
agent-selector re-contexts all agent-scoped UI without reload.

An agent has a lifecycle: `active` → `retired` (soft-delete; data
preserved, agent read-only, reactivation possible).

Covered in [TB-US-044](https://github.com/eversole-learning/trainingbench/blob/main/docs/user-stories/tb-us-044.md).

## Versioned component

Each agent is composed of six **component types**, each versioned
independently:

| Component | What it is | How it's versioned |
|---|---|---|
| **Training set** | List of training examples (prompt → correct answer) | NDJSON sorted by sample_id, SHA-256 hashed |
| **RAG index** | Chroma collection of document chunks + embeddings | Manifest hash (source paths + chunk counts + embedding model) |
| **PEFT adapter** | LoRA weights trained on the training set | SHA-256 of `adapter_model.safetensors` |
| **System prompt** | Instruction text for the model | SHA-256 of UTF-8 bytes (trailing-ws stripped) |
| **Query routes** | Prompt-augmentation rules (prefix / suffix patterns) | SHA-256 of canonical JSON |
| **Eval harness** | Python module that measures accuracy on a dataset | SHA-256 of definition JSON + module source |

### Three-state lifecycle

Every version is in exactly one state:

- **`draft`** — mutable; operator is building it. Not yet usable in
  production.
- **`released`** — immutable; ready to use. Can be promoted into
  production or compared against other released versions.
- **`deprecated`** — immutable; no longer recommended. Preserved for
  history and reproducibility.

Transitions: `draft → released → deprecated`. One-way; no reverse.

Covered in [TB-US-043](https://github.com/eversole-learning/trainingbench/blob/main/docs/user-stories/tb-us-043.md).

## Sweet Spot

The **currently-promoted combination** of (system prompt, RAG, LLM,
adapter) for an agent. There's always exactly one Sweet Spot per
agent at any time (or zero if nothing is promoted yet). It's not a
magic optimum — it's just what operator has decided is "good enough
to be live right now."

Three related concepts:

- **Recipe** — the current, mutable configuration you're editing.
  Think "what I'm working on at my desk."
- **Snapshot** — an immutable capture of a recipe at a specific
  moment. Produced by releasing component versions.
- **Sweet Spot** — the snapshot currently promoted to production.
  Replaced by promoting a different snapshot.

### Four Sweet Spot axes

A promotion sets which released version plays each role:

- `system_prompt_version_id` — which prompt is live
- `rag_version_id` — which RAG index is live
- `llm_identifier` — which base model (string field, not a FK —
  external to TB's version space)
- `adapter_version_id` — which LoRA adapter is live (nullable;
  Stage 0 = bare base model = no adapter)

Note the eval harness is **not** a Sweet Spot axis — it's a
measurement sidecar, not a production component. (See
[TB-US-043 Q5](https://github.com/eversole-learning/trainingbench/blob/main/docs/user-stories/tb-us-043.md).)

## Experiment

A measured comparison. Pins a specific `(prompt, RAG, LLM, adapter,
harness)` tuple and records a result:

```json
{
  "experiment_id": 4,
  "agent_id": 2,
  "label": "math-example-e2-plus-adapter",
  "state": "completed",
  "system_prompt_version_id": 3,
  "rag_version_id": null,
  "llm_identifier": "meta-llama/Meta-Llama-3.1-8B",
  "adapter_version_id": 1,
  "harness_version_id": 1,
  "results_json": { "metric": "accuracy", "value": 0.62, "n_samples": 200, ... }
}
```

### Six-state lifecycle

```
draft → running → completed → promoted ↔ displaced
                 ↘ archived
```

- **`draft`** — created, not yet executed
- **`running`** — harness is executing
- **`completed`** — harness finished, results recorded
- **`promoted`** — its component combination became the current Sweet
  Spot
- **`displaced`** — was promoted; a newer experiment took its place
  (re-promotable)
- **`archived`** — explicitly set aside; preserved for history

## Two-tier architecture

TrainingBench separates **agent management** from **administrative
functions**:

- **Agent tier** — everything scoped to a specific agent. The main
  drawer nav + the agent-selector widget.
- **Administrative tier** — install-wide concerns: users, API keys,
  system config, audit viewers. Lives in the drawer-footer **⚙️
  Admin** dropdown above Logout. Super-user only.

The drawer agent-selector doesn't affect the admin tier. Admin items
are not agent-scoped.

Covered in [TB-US-062](https://github.com/eversole-learning/trainingbench/blob/main/docs/user-stories/tb-us-062.md).

## Harness

A Python module + config dict that measures an agent's model stack
against a dataset. Shipped harnesses expose:

```python
def run(dataset_path: str, model_fn: Callable[[str], str], config: dict) -> dict:
    """Returns {metric, value, n_samples, duration_seconds, per_sample, ...}"""
```

The harness is dependency-injected with a `model_fn` built by the
harness runner, which pins the experiment's component versions.
Hashing includes both the config dict AND the module source — a code
change to the harness module itself produces a new harness version.

Shipped: `harnesses.math_qa_v1` for GSM8K-style math word problems.

Covered in [TB-US-056](https://github.com/eversole-learning/trainingbench/blob/main/docs/user-stories/tb-us-056.md).

## See also

- [Staged Progression]({{ '/staged-progression.html' | relative_url }}) — the three-stage
  math-example demonstration putting all of these concepts together
- [Getting Started]({{ '/getting-started.html' | relative_url }}) — install + first-login
  walkthrough
- [GitHub repository](https://github.com/eversole-learning/trainingbench) —
  source code + full user-story history
