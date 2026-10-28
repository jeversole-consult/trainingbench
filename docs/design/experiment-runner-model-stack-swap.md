# Experiment-runner model-stack swap

**Status:** awaiting operator decision (2026-10-25)
**Problem surface:** TB-US-056 harness runner · TB-US-057 Phase B · TB-US-067 chat-path RAG wiring
**Author:** Jesse Eversole

---

## The problem

Experiments pin a specific `(prompt, RAG, LLM, adapter, harness)`
version combination. Running an experiment should measure that
specific combination. **Today, running an experiment does not
measure the pinned combination.**

The reason is in `backend/api/harness_runner.py`:

```python
def _build_model_fn(experiment: Dict) -> Callable[[str], str]:
    def _model_fn(question: str) -> str:
        result = _main.rag_system.query(question=question, k=4)
        ...
    return _model_fn
```

The `model_fn` closes over the **global `rag_system` singleton** —
constructed at TB startup from `.env` configuration (LLM_PROVIDER,
TB_ACTIVE_ADAPTER). The experiment row's `adapter_version_id`,
`rag_version_id`, and `system_prompt_version_id` fields exist and
are stored correctly, but `_build_model_fn` never reads them.

**Consequence:** on this install, running experiments E1 / E2 / E3
seeded for math-example would produce three measurements against
the same model stack — identical numbers regardless of what the
experiment pins.

## Why it ended up this way

TB-US-053 (RAG versioning) scope-decided to defer chat-path rewiring.
TB-US-056 (eval harness) built on top of what existed and inherited
the limitation. The deferred work was captured in TB-US-067 (chat-path
RAG wiring for versioned agents).

TB-US-067 as drafted focuses on **production chat** — i.e., the
operator-facing `/query` endpoint picking up the per-agent promoted
RAG. It doesn't explicitly address the **harness runner** path,
which has similar needs plus the adapter-swap dimension that `/query`
doesn't currently handle (production chat has always used the fixed
startup-configured adapter).

## What the runner would need

For each experiment, `_build_model_fn` has to construct a model_fn
that reflects the experiment's pinned versions:

1. **Base LLM** — determined by `experiments.llm_identifier` (string
   like `"meta-llama/Meta-Llama-3.1-8B-Instruct"`). Could reuse the
   global rag_system's base model if the identifier matches, or
   load a different base if it doesn't.
2. **Adapter** — if `experiments.adapter_version_id` is non-null,
   load the adapter files from `adapter_versions.files_path` onto
   the base via PEFT. If null, bare base.
3. **System prompt** — if `experiments.system_prompt_version_id` is
   non-null, read `prompt_versions.content` and inject at inference
   time. Could prepend to the user question, or (cleaner) replace
   the RAGSystem's internal prompt template for the duration of the
   call.
4. **RAG** — if `experiments.rag_version_id` is non-null, resolve
   `rag_versions.collection_name` and query the per-version Chroma
   collection. If null, no retrieval (just prompt → model).
5. **Query routes** — the experiment row doesn't currently reference
   routes. Deferred unless the operator asks.

Each of these is independently achievable; **adapter swap is the
most expensive** (loading a 300MB LoRA + merging into a 16GB base
takes a few seconds; keeping multiple adapters warm in memory
multiplies the VRAM cost).

## Three ways to execute

### Option A — Full TB-US-067 as drafted + extension

Execute TB-US-067 to its full scope (production `/query` rewired),
then **extend** `_build_model_fn` to pull from the same per-agent
VectorStore cache + add adapter-swap logic. Both paths share
infrastructure.

- **Pro:** maximum code reuse; one implementation of per-version
  stack construction serves both production and experiments.
- **Pro:** closes TB-US-053's deferred chat-path work completely.
- **Con:** largest scope. Production `/query` changes carry
  regression risk (operator currently uses `/query` for actual chat).
- **Con:** adapter swap for production `/query` is a bigger ask than
  for experiments — in production, every request would need to know
  which adapter to load. Caching has to be aggressive.
- **GPU memory impact:** need to keep multiple adapters cached if we
  want fast per-request swaps. For math-example with just adapter v2,
  trivial. For multi-agent installs with many adapters, could
  pressure VRAM.

### Option B — Smaller precursor: experiment-runner only

Build a per-experiment stack-construction helper **only inside the
harness runner path**. Production `/query` stays unchanged. This
means:

- `_build_model_fn` reads the experiment row, loads the right
  adapter + RAG + prompt into a transient model-fn closure.
- Each harness run constructs its stack from scratch (slow — several
  seconds of adapter loading before the first query). Acceptable
  because harness runs are batched (200 samples per experiment, run
  once in a while, not every chat request).
- No production regression risk — the production chat path is
  untouched.

- **Pro:** smallest scope. Isolated to the harness runner. Operator
  can run E1/E2/E3 with real Stage 0/1/2 numbers.
- **Pro:** no production regression.
- **Con:** duplicates logic that TB-US-067 will eventually need.
  When TB-US-067 lands, we refactor the shared bits.
- **Con:** harness runs are slower (3-5s adapter-load overhead
  per experiment start).

**Would spawn as TB-US-069** per the convention.

### Option C — Hybrid

Do Option B now (unblocks TB-US-057 Phase B measurements), then
when TB-US-067 lands, refactor the shared code. Explicitly commit
to the refactor in TB-US-067's scope.

- **Pro:** operator gets real Stage 0/1/2 numbers immediately for
  TB-US-057 Phase C.
- **Pro:** refactor happens later when the design is more informed
  by actual usage.
- **Con:** two sites of per-version model-stack construction in the
  interim.

## Scope boundary vs TB-US-067

A clean split:

- **TB-US-067:** `/query` endpoint picks up the agent's **promoted**
  RAG from `agent_components`. Simple lookup. No adapter swap in
  production path. The agent's "live" Sweet Spot drives the chat
  experience.
- **TB-US-069 (new, Option B):** harness runner picks up each
  experiment's **pinned** versions. Explicit version IDs on the
  experiment row drive the harness execution.

Different stories, different scopes, minimal overlap.

## Other factors

- **Adapter loading cost.** PEFT's `.from_pretrained` on a LoRA
  adapter against a loaded base model takes a few seconds. Doable
  per-experiment-run, prohibitive per-chat-request without caching.
- **VRAM headroom.** RTX 3090 at 24GB is tight. The base model
  takes ~16GB (4-bit) during QLoRA inference. Each LoRA adapter adds
  ~300MB. Keeping 2-3 adapters loaded simultaneously fits; keeping
  10 doesn't.
- **Harness runs are serial.** Only one experiment runs at a time
  (operator supervises each one). No concurrent VRAM pressure from
  multiple experiments.
- **Honest expectation on E3.** Even with full Options A/B/C
  implemented, RAG on top of GSM8K may show null/negative delta
  (per TB-US-053 scope decision + rag-seeds LICENSES.md note). The
  measurement framework will capture that honestly.

## Decision point

Operator picks:

1. **A — full TB-US-067 scope** (production + experiments share
   infra; biggest regression surface)
2. **B — smallest-possible TB-US-069** (experiment-runner only;
   production untouched; refactor later with TB-US-067)
3. **C — B now, A later** (hybrid; explicit commitment to refactor)
4. Something else

Once chosen, we spawn whichever story and execute. TB-US-057 Phase B
is blocked on this decision because the experiments need the fix to
produce distinct measurements.

## Related

- [TB-US-053](../user-stories/tb-us-053.md) — RAG versioning;
  scope-deferred chat-path wiring that landed here
- [TB-US-056](../user-stories/tb-us-056.md) — Eval harness subsystem;
  built the model_fn pattern this doc proposes extending
- [TB-US-057](../user-stories/tb-us-057.md) — math-example staged
  progression; Phase B unblocking is the near-term motivation
- [TB-US-067](../user-stories/tb-us-067.md) — Chat-path RAG wiring
  for versioned agents; Option A executes this to full scope
- Code references:
  - `backend/api/harness_runner.py` — `_build_model_fn` is the
    target function
  - `backend/api/main.py` — `rag_system` global, initialized at
    startup
  - `backend/rag/rag_system.py` + `backend/rag/vector_store.py` —
    the per-version stack construction would call into these with
    per-experiment overrides
