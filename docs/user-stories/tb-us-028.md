# TB-US-028: Qualitative handler via OT routing

**Status**: In Progress
**Created**: 2026-10-14
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As the operator of an OT-equipped TrainingBench agent, I want
TB's existing RAG + content-adapter pipeline wired into the OT
router as the **qualitative handler**, and I want a single
unified OT router entry point that classifies every incoming
prompt and dispatches to the appropriate handler, so that the
full OT pipeline (classify → route → handle → log) is reachable
from a single endpoint and the four handlers from TB-US-023
through TB-US-027 compose into a working whole.

## Background

TB already has the qualitative handler capability — the RAG
system plus the content adapter path reached via
`POST /query` (`backend/api/main.py:688`). This story does
not rebuild that; it exposes it through the OT routing path
and makes the OT router the authoritative "ask TB something"
entry point.

This story is the **integration layer** for the whole OT v0.1
arc. After this ships, every handler (TB-US-025, 026, 027)
and the classifier (TB-US-023) is reachable through one
`POST /ot/query` endpoint, with every call captured in the
audit log (TB-US-024).

The existing `POST /query` endpoint stays for backwards
compatibility and so that pre-OT callers (and the stalite3
patterns TB inherited) continue to work. New callers use
`/ot/query`. In a future story the two could merge if desired.

## Requirements

### Router

- [ ] R1: **New endpoint: `POST /ot/query`.** Request body:
      ```python
      class OTQueryRequest(BaseModel):
          prompt: str
          model: Optional[str] = None   # adapter / model override
          k: int = 5                    # RAG retrieval depth (qualitative only)
      ```
      Response:
      ```python
      class OTQueryResponse(BaseModel):
          response: str
          category: str
          handler: str
          entry_id: str                 # from the audit log
          latency_ms: int
      ```
- [ ] R2: **Router flow** (inside the endpoint handler):
      1. Call `ot_audit.start_entry()`.
      2. Call `classify_prompt(prompt)` from TB-US-023;
         `ot_audit.add_classification()`.
      3. Dispatch to the appropriate handler by category:
         - `qualitative` → `handle_qualitative(prompt, model, k, audit_entry)`
         - `quantitative` → `handle_quantitative(prompt, audit_entry)`
         - `lookup` → `handle_lookup(prompt, audit_entry)`
         - `mixed` → `handle_mixed(prompt, audit_entry)`
         Handlers mutate the audit_entry via
         `ot_audit.add_handler()`.
      4. Collect response, call `ot_audit.add_response()`.
      5. Call `ot_audit.finalize()`.
      6. Return `OTQueryResponse`.
- [ ] R3: **Qualitative handler wrapper.** Function
      `handle_qualitative(prompt, model, k, audit_entry) ->
      str` wraps TB's existing RAG query logic (currently
      inline in `POST /query`'s body). The wrapper:
      1. Extracts the core RAG call from the existing
         `/query` handler into a reusable function.
      2. Logs handler details (model used, retrieval
         chunks, latency) to the audit entry.
      3. Returns the RAG-generated response.
- [ ] R4: **Pre-existing `/query` endpoint preserved.** The
      existing endpoint keeps its current behavior. If the
      shared RAG function from R3 is extracted, `/query`
      calls that same function so there's no duplicated
      logic. **No regression on existing callers.**

### Role gating

- [ ] R5: **`/ot/query` requires authentication.** All
      authenticated users (super, training, chat) can call
      it. Rate limiting matches `/query`'s 20/minute. No
      per-category role check in v0.1 (even quantitative /
      lookup are available to any authenticated user).

### Error handling

- [ ] R6: **Handler exceptions are audited and surfaced.**
      If any handler raises, the audit entry is finalized
      with `handler.success = false` and the error message.
      The endpoint returns HTTP 500 with a user-safe error.
- [ ] R7: **Classifier failures.** If `classify_prompt`
      raises (e.g., LLM fallback unreachable), log the
      failure in the audit entry and return HTTP 503. Do
      not fall through to a specific handler.

### No regression

- [ ] R8: **Existing `/query` endpoint unchanged in
      behavior** per R4.
- [ ] R9: **TB-US-010's admin modal functionality**
      unchanged.
- [ ] R10: **All existing training endpoints** unchanged.

### Cache-bust

- [ ] R11: Not applicable — this story is backend-only
      unless the implementer chooses to add a thin UI
      affordance ("Try OT routing" button) which would then
      follow TB-US-010's `?v=` convention.

## Acceptance Criteria

- [ ] AC1: `POST /ot/query` with `{"prompt": "what is 2 + 2"}`
      returns `{"category": "quantitative", "handler":
      "quantitative", "response": "4", ...}` with a
      populated `entry_id` and `latency_ms`.
- [ ] AC2: `POST /ot/query` with
      `{"prompt": "explain how PEFT works"}` returns
      `{"category": "qualitative", "handler": "qualitative",
      "response": "...", ...}` where the response is the
      RAG-generated answer (matches the behavior of a
      direct `/query` call with the same prompt).
- [ ] AC3: `POST /ot/query` with
      `{"prompt": "what is Jesse's email"}` returns
      `{"category": "lookup", "handler": "lookup", ...}`
      with the exact fact from the configured lookup source.
- [ ] AC4: `POST /ot/query` with a compound prompt returns
      `{"category": "mixed", "handler": "mixed", ...}` with
      a composed response. The audit entry has
      `handler.sub_entries` populated.
- [ ] AC5: Every call to `/ot/query` writes exactly one
      line to the current month's OT audit JSONL file. The
      `entry_id` in the response matches the entry.
- [ ] AC6: The pre-existing `/query` endpoint continues to
      work and returns the same shape it returned before this
      story. Verified by hitting it with a known prompt
      pre- and post-deploy.
- [ ] AC7: A quantitative-handler error (e.g., no
      calculator matches) returns an HTTP 200 with the
      handler's error response in `response` and
      `handler.success = false` in the audit entry — the
      user gets a message, not a 500.
- [ ] AC8: A classifier failure (LLM fallback unreachable
      with no rule match) returns HTTP 503 and logs the
      failure in the audit entry.
- [ ] AC9: Non-authenticated calls to `/ot/query` return
      HTTP 401.

## Design Notes

- **Why a new endpoint rather than modifying `/query`.** The
  existing `/query` has implicit assumptions baked into it
  (always RAG, always LLM, always qualitative in OT terms).
  Modifying it to detect classification would risk breaking
  callers. `/ot/query` is the new canonical path. `/query`
  can be deprecated and merged later if desired.
- **Shared RAG function extraction (R3).** The current
  `/query` handler has ~100 lines of model-swap and RAG
  logic inline. Extracting that into a `_run_rag_query()`
  function (or similar) lets both endpoints call it. This
  is defensible refactor-while-adding-feature — the
  function is renamed/relocated but its behavior is identical.
- **The qualitative handler is a wrapper, not a rewrite.**
  TB's RAG path is already production-tested. The handler
  story is minimal: wrap it, log it, return it.
- **No per-category role gating at v0.1.** All
  authenticated users get all handlers. If a future
  deployment wants (for example) only training users to
  reach the quantitative calculators, that's a separate
  story — v0.1 keeps the role surface flat.
- **Why return `entry_id` in the response.** It gives
  callers a stable identifier to reference the audit entry
  later (e.g., "the response to prompt X was wrong — look
  at entry_id Y"). Cheap to include; useful downstream.
- **Why rate-limit like `/query`.** The OT router can
  trigger an LLM call for classification + another LLM call
  if qualitative. Keeping the limit at 20/minute matches
  the existing contract and prevents a surprise spike in
  model inference load.
- **No streaming responses at v0.1.** All handlers return
  complete responses. Streaming is a future concern.

## Out of Scope

- **Merging / deprecating `/query`.** Separate story if
  wanted after the OT router has been in use for a while.
- **UI integration** — adding an OT-aware chat panel to
  TB's static pages. The existing chat UI continues to call
  `/query`; a future UI story can switch to `/ot/query`.
- **Model override / adapter selection logic beyond R1.**
  `/query` already handles PEFT-adapter model names; the
  qualitative wrapper inherits that.
- **Caching responses by prompt hash.** None.
- **Multi-model fan-out** (ask the same prompt of several
  models). Separate concern.
- **Streaming responses.**
- **Per-user response personalization.**
- **Branding tweaks.**

## Related

- Parent: [TB-US-022](tb-us-022.md) — OT coordinator.
- Depends on: [TB-US-023](tb-us-023.md) (classifier),
  [TB-US-024](tb-us-024.md) (audit log),
  [TB-US-025](tb-us-025.md) (quantitative),
  [TB-US-026](tb-us-026.md) (lookup),
  [TB-US-027](tb-us-027.md) (mixed).
- Verified by: [TB-US-029](tb-us-029.md) — the math example
  calls `/ot/query` and verifies classification + handler
  behavior against a labeled query set.
- Context: `docs/ot-context-for-claude-code_1.md` lines
  69–96 (handler architecture); existing TB code
  `backend/api/main.py:688` (`POST /query`).
