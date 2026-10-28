# TB-US-067: Chat-path RAG wiring for versioned agents

**Status**: Proposed
**Created**: 2026-10-22
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a TB operator, I want the `/query` chat endpoint to
use an agent's promoted RAG version (from
`agent_components`) rather than the legacy singleton
Chroma collection — so that TB-US-057 experiment E3
(adapter + RAG) can actually route through the versioned
RAG and so that per-agent RAG isolation becomes real at
inference time.

## Background

TB-US-053 (RAG versioning) shipped the versioning
machinery but **deferred the chat-path rewiring** —
operators create / release / promote RAG versions, but
`/query` still routes against the legacy singleton
`documents` Chroma collection.

TB-US-057 Phase B experiment E3 (adapter + RAG) depends
on the chat path actually using the promoted RAG for
the math-example agent. Without this story, E3 either
(a) requires manual inference-time prompt injection by
the operator or (b) can't be measured through the harness
runner.

**Depends on:**
- TB-US-053 — RAG versioning machinery (shipped)
- TB-US-052 — Training-set versioning (schema prereq;
  shipped)

**Blocks:**
- TB-US-057 Phase B experiment E3

## Requirements

- [ ] R1: **Per-request agent selection.** `/query`
      endpoint (and ingest endpoints that currently
      target the singleton collection) read the current
      agent from the request:
      - Request body may include `agent_name` or
        `agent_id`
      - Request header `X-TB-Agent-Name` as alternative
      - Fallback: `sessionStorage.tb_current_agent` is
        passed by the frontend
      - If none provided: fallback to the legacy
        singleton collection (backward compatibility)
- [ ] R2: **Promoted RAG lookup.** For the resolved
      agent, query `agent_components WHERE agent_id = ?
      AND component_type = 'rag'`. If a promoted row
      exists, use the collection `rag_versions.collection_name`
      for retrieval. Else fall back to legacy singleton.
- [ ] R3: **Chroma client cache.** A single-process cache
      of VectorStore instances keyed by collection_name
      so we don't rebuild embedding model + Chroma
      connection on every request. LRU with sane bound
      (10 collections).
- [ ] R4: **Chat response includes provenance.** When
      answering, include `rag_version_id` + `collection_name`
      used in the response metadata so the harness runner
      can record which RAG served the query.
- [ ] R5: **Ingest endpoints also agent-scoped.** The
      existing `/upload`, `/scrape`, crawl endpoints now
      target the resolved agent's draft RAG version
      (auto-create a draft if none exists). Released
      RAG versions remain read-only.
- [ ] R6: **No regression** on queries without agent
      context — legacy singleton continues to serve.
- [ ] R7: **Admin audit** on cross-agent writes (ingesting
      into a different agent than the drawer's current).

## Acceptance Criteria

- [ ] AC1: `POST /query` with `agent_name: "math-example"`
      → response uses math-example's promoted RAG
      collection (verified via `rag_version_id` field in
      the response).
- [ ] AC2: `POST /query` with no agent context → legacy
      singleton collection served; no regression.
- [ ] AC3: `POST /upload` with `agent_name: "math-example"`
      → doc lands in math-example's draft RAG version
      (collection `agent{N}_rag_v{M}`); auto-creates
      draft if none exists.
- [ ] AC4: Attempt to ingest into an agent with no draft
      and all RAG versions released → auto-create new
      draft (not error).
- [ ] AC5: Attempt to ingest into a released RAG version
      directly → 400 "released; create new draft" (same
      behavior as `POST /rag-versions/{id}/ingest`).
- [ ] AC6: Chroma client cache: second request to same
      agent reuses the cached VectorStore (verify via
      log instrumentation; no "loading embedding model"
      line on repeat).
- [ ] AC7: Smoke test: `math_qa_v1` harness pointed at
      math-example agent's promoted RAG returns results
      different from the no-RAG baseline.

## Design Notes

- **Why delayed until now.** TB-US-053 scope-decision
  called this out as deferred — the risk of silently
  breaking the live chat flow outweighed the benefit
  of rewiring on an empty RAG. Now that TB-US-057 Phase
  A has real content and Phase B wants to measure E3,
  the integration is justified.
- **Why resolve agent from multiple sources.** Different
  caller contexts: UI chat sends sessionStorage;
  harness runner sends via request body; CLI tools can
  use the header. All resolve to the same lookup
  mechanism.
- **Why fall back to the singleton.** Backward
  compatibility with any script or test that hits
  `/query` without agent context. Deprecate the
  singleton in a future cleanup story.
- **Why LRU cache the VectorStore.** Loading embedding
  model + Chroma client is slow (~2s). At 5-10 agents
  per install, caching the full set is cheap.
- **Why not force agent on every request.** Breaking
  change for existing callers. The soft migration
  (default to singleton if unspecified) lets us ship
  without a flag day.

## Out of Scope

- Deprecating / deleting the legacy singleton
  collection (future cleanup story)
- Per-request RAG version override (always uses the
  agent's promoted version; experimenters who want to
  pin a specific RAG version use the experiment flow
  via `experiments.rag_version_id`)
- Cross-agent RAG sharing (future)
- Collection cleanup / garbage collection for retired
  agents (future)
- Changing the embedding model per agent (future;
  v0.1 single embedding model globally)

## Related

- [TB-US-053](tb-us-053.md) — RAG versioning;
  deferred the chat-path wiring this story completes
- [TB-US-057](tb-us-057.md) Phase B — E3 depends on
  this story
- [TB-US-052](tb-us-052.md) — Training-set versioning
  (schema prereq)
- [TB-US-048](tb-us-048.md) — agent-selector widget
  (sessionStorage source for request context)
- Files touched (anticipated):
  - `backend/api/main.py` — `/query` + ingest endpoints
    get agent-resolution + per-agent VectorStore lookup
  - `backend/rag/vector_store.py` — may need an LRU
    cache helper
  - `backend/api/rag_version_manager.py` — add
    `ensure_draft_for_ingest(agent_id)` helper
  - `backend/rag/rag_system.py` — accept per-request
    VectorStore override
  - `static/script.js` — pass `agent_name` in chat
    requests from the UI
