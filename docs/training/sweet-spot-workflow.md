# Sweet Spot Workflow

How to find a performant combination of (base model, training set,
adapter, RAG, prompt) for your own agent using the TrainingBench
staged-progression pattern.

**Audience:** operators who have a working TB install and want to
build their own agent, not just explore the shipped math-example.

**Prerequisite:** TB-US-057's math-example walkthrough gives you
the pattern on a known-pedagogical artifact set. Read
[`sweet-spot-exploration.md`](../math-example/sweet-spot-exploration.md)
first if you haven't.

## What a "sweet spot" is

A **Sweet Spot** is the current winning combination of pinned
component versions for an agent, chosen via a tournament of
before/after experiments against a shared hold-out eval. The
pattern is:

- Start with a bare base (Stage 0)
- Add training (Stage 1) → does it beat Stage 0?
- Add retrieval (Stage 2) → does it beat Stage 1?
- Keep what helps; drop what doesn't
- The current winner is the Sweet Spot; it stays Sweet until a
  challenger experiment beats it on the hold-out eval

The staged progression is one specific path. In practice sweet-spot
tournaments can run in any order (RAG-first, prompt-first, etc.) —
what matters is *every* promotion decision is backed by a measured
delta on a shared eval.

## Workflow

### 1. Define your agent

Via the Agent Management modal (TB-US-048) or the API:
`POST /agents` with `{"name": "my-agent"}`. Agents are the top-of-
food-chain scope; every component you build gets pinned to one
agent.

### 2. Build a training set

A JSONL file with the shape your training pipeline expects.
`training/math/train.py` uses `{"question": ..., "answer": ...}` for
instruction tuning. Register it:
`POST /agents/{id}/training-sets` with a path to the file. The
server computes a SHA-256 content hash and gives it a version ID.

Release it when you're ready to train against it:
`POST /training-set-versions/{v}/release`.

### 3. Build a hold-out eval harness

A JSONL file with `{"question": ..., "ground_truth": ...}` plus a
Python module that scores a model's answer. Register as a harness
version: `POST /agents/{id}/harness-versions`.

**Critical:** the eval and training sets must not overlap. The
math-example seeder asserts this at creation time; replicate that
for your own agent.

### 4. Pick a base model

Register as part of each experiment's `llm_identifier` field. The
model file lives wherever the TB server can `AutoModelForCausalLM.
from_pretrained(id)` — HuggingFace Hub, a local path, etc.

### 5. Run Stage 0 — base-only baseline

Create a draft experiment pinning only the base + prompt + harness
(adapter=None, rag=None). Run it:

```bash
POST /experiments  { ...pins... }      # returns experiment_id
POST /experiments/{experiment_id}/run  # launches via BackgroundTasks
```

Supervise via `GET /experiments/{id}` polling + the training-runs
UI (TB-US-066) + `nvidia-smi`. **This is your Stage 0 number.**

### 6. Train an adapter

Via the Training Runs UI (TB-US-066) or `POST /training/runs/launch`.
Pick:
- Agent (your agent)
- Training-set version (released; from step 2)
- Base model (same as Stage 0)
- Hyperparameters (defaults in `training/math/README.md` as a
  starting point; see *Dials to turn* below)

On successful completion the adapter auto-registers as
`adapter_versions.v{N}` (TB-US-063 / TB-US-065 R9). Release and
promote it:

```bash
POST /adapter-versions/{N}/release
POST /adapter-versions/{N}/promote
```

### 7. Run Stage 1 — base + adapter

Create a second experiment identical to Stage 0 but with
`adapter_version_id` pinned to the version from step 6. Run it.
**This is your Stage 1 number.**

### 8. Build a RAG manifest (optional)

If your problem is factual-recall-shaped (not purely reasoning-
shaped), build a reference corpus and register it:
`POST /agents/{id}/rag-versions`.

### 9. Run Stage 2 — base + adapter + RAG

Create a third experiment identical to Stage 1 but with
`rag_version_id` also pinned. Run it. **This is your Stage 2
number.**

### 10. Decide

- If Stage 1 > Stage 0: adapter helps. Keep it in the Sweet Spot.
- If Stage 2 > Stage 1: RAG helps. Keep it.
- If a stage doesn't improve: a null delta is a legitimate finding.
  Don't ship what doesn't earn its place.

The current winner is the Sweet Spot. Record it. Future candidates
(new training sets, new RAG manifests, new prompts) run as fresh
experiments pinned against the winning base combination — if a
challenger beats the Sweet Spot on the eval, it displaces.

## Dials to turn

If a stage doesn't improve, the most common fixes:

| Problem | Try |
|---|---|
| Adapter doesn't beat base | More training data; higher LoRA rank; more epochs; swap to Instruct-variant base |
| Base is already Instruct and adapter still doesn't help | Your training set is too small / off-distribution from the eval |
| RAG doesn't help on top of adapter | Your problem is probably reasoning, not knowledge. Null delta is honest |
| All three stages near zero | Grader is likely stricter than reality. Verify a few outputs by hand before concluding "nothing works" |
| Hard to tell if changes help | Shrink your eval first (n=20) for fast iteration; scale up to n=200+ once you have a signal |

## Operational notes

### Service state between runs

TrainingBench's harness runner reuses the server process. Between
experiments:
- Python model refs get released by `_free_stack()`
- PyTorch's CUDA caching allocator retains the VRAM pool
- Next experiment's stack reuses the pool

Result: ~16 GB stays allocated after the first run. The *next* run
is fine (stack replaces stack in cache). But if you want to measure
Stage 0 against a *fresh* VRAM state (uncached), restart the
service: `sudo systemctl restart trainingbench.service`.

### Serialized GPU

Only one experiment at a time per GPU. The TB server enforces this
implicitly (one process, one BackgroundTask slot). If you need
parallel experiment runs, you need multiple GPUs or a job queue
(not yet shipped).

### Audit trail

Every experiment transition writes to `admin_audit` via
`_audit_versioned_action` (TB-US-017). You can post-hoc reconstruct
"who ran what when and did it succeed" from that table.

### Persisted artifacts

- Experiment DB rows live in `backend/db/trainingbench.db` →
  `experiments` table, with `results_json` containing the full
  per-sample output.
- Adapter files live in `adapters/{agent-name}/v{N}/` per
  TB-US-063.
- Training-set / RAG / prompt / harness manifests live in their
  respective `*_versions` tables with content hashes.

Everything is reproducible from these rows if you keep the DB.

## When to call something a Sweet Spot

- Measured on a hold-out eval (shared across experiments)
- Beats the previous Sweet Spot by a margin that's larger than
  your run-to-run noise (run the same experiment twice and record
  the delta; your noise floor is roughly that number)
- All component versions pinned via version IDs (no "latest" refs)
- Audit log shows the promotion decision and who made it

Below those bars, you have a candidate, not a Sweet Spot.

## References

- Design kernel: `docs/design/sweet-spot-architecture.md` (TB-US-043)
- Agent architecture: `docs/design/agent-architecture.md` (TB-US-044)
- Worked walkthrough on math-example:
  `docs/math-example/sweet-spot-exploration.md`
- Component-version APIs: TB-US-052 (training sets), TB-US-053
  (RAG), TB-US-055 (prompts), TB-US-056 (harnesses), TB-US-063
  (adapters)
- Experiment lifecycle: TB-US-057 Phase A, TB-US-069
- Training launcher: TB-US-065 (backend), TB-US-066 (UI)
