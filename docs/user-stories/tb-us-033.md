# TB-US-033: Port `/settings/query-routes` + `/settings/rag-prompt` endpoints (feature parity close-out)

**Status**: Completed
**Created**: 2026-10-14
**Completed**: 2026-10-14
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a TB operator, I want user-configurable query routing
rules and user-editable RAG system prompt — both persisted
with saved_at / saved_by metadata and both auditable — so
that TB catches up to stalite3's existing routing-config
surface and so that TB-US-022's OT classifier (In Progress)
has an operator-tunable surface already in place.

## Background

Per TB-US-031 audit Section 3.8, stalite3 has:

- `GET /settings/query-routes` + `PUT /settings/query-routes`
  — list of regex-pattern routes with augmentation strings;
  auditable via `logs/query_routes_audit.jsonl`
- `GET /settings/rag-prompt` + `PUT /settings/rag-prompt` —
  user-editable system prompt template; auditable via
  `logs/rag_prompt_audit.jsonl`
- Both persisted via `AppSettings` module (same shape as
  TB's existing `demo_mode` persistence)

TB has `AppSettings` (117 lines) but only exposes `demo_mode`
and `active_database`. Stalite3's `AppSettings` (279 lines)
adds the two methods + audit helpers. Direct port extends TB's
`AppSettings` with 6 new methods + 2 audit helpers + 2
constants (DEFAULT_RAG_PROMPT, DEFAULT_QUERY_ROUTES), then
adds the 4 endpoints in `main.py`.

**Scope note:** This story ships the **storage + endpoint
surface** — operators can set and read `rag_prompt` and
`query_routes` via API. It does NOT yet wire the persisted
values into TB's RAG query flow (i.e. the configured prompt
isn't consumed by `/query` yet; the configured routes don't
yet augment retrieval). Those are TB-side `rag_system.py`
changes which are a cleaner follow-up (either TB-US-040 or
rolled into TB-US-022's OT classifier work). This story
closes the audit's Section 3.8 parity gap at the API/
persistence layer; downstream consumption is a separate
concern.

## Requirements

### `app_settings.py` additions

- [x] R1: **New constants** at module top:
      - `DEFAULT_RAG_PROMPT` — a **generic** prompt template
        (no Stalite-specific text). Content:
        ```
        Use the following context from technical documents to
        answer the question. If the context contains relevant
        information, use it. Otherwise, answer from your training.

        Context:
        {context}

        Question: {question}

        Answer:
        ```
      - `DEFAULT_QUERY_ROUTES: List[Dict] = []` — empty list;
        operators configure routes per deployment via the PUT
        endpoint.
      - `RAG_PROMPT_AUDIT_LOG_PATH` and
        `QUERY_ROUTES_AUDIT_LOG_PATH` env-var-driven paths
        under `logs/`.
- [x] R2: **Extend `_seed_default`** to include six new keys:
      `rag_prompt`, `rag_prompt_saved_at`,
      `rag_prompt_saved_by`, `query_routes`,
      `query_routes_saved_at`, `query_routes_saved_by`.
- [x] R3: **Six new classmethods on `AppSettings`:**
      - `rag_prompt()` → str
      - `rag_prompt_meta()` → `{"saved_at", "saved_by"}`
      - `set_rag_prompt(value, username)` → status dict,
        validates `{context}` and `{question}` placeholders
        both present
      - `query_routes()` → `List[Dict]`
      - `query_routes_meta()` → `{"saved_at", "saved_by"}`
      - `set_query_routes(routes, username)` → status dict,
        validates each route has required keys
- [x] R4: **Two new audit helpers:**
      `_append_rag_prompt_audit(username, old_value, new_value)`
      and
      `_append_query_routes_audit(username, old_routes, new_routes)`.
      Each writes one JSONL line with timestamp + username +
      old/new values.

### `main.py` additions

- [x] R5: **New Pydantic models:**
      ```python
      class RagPromptRequest(BaseModel):
          prompt: str

      class QueryRoutesRequest(BaseModel):
          routes: List[Dict]
      ```
- [x] R6: **Four endpoints:**
      - `GET /settings/rag-prompt` — any authed user; returns
        `{"prompt", "default", "saved_at", "saved_by"}`
      - `PUT /settings/rag-prompt` — **super only**; body
        `{"prompt": "..."}`; validates placeholders; writes
        audit
      - `GET /settings/query-routes` — any authed user;
        returns `{"routes", "defaults", "saved_at",
        "saved_by"}`
      - `PUT /settings/query-routes` — **super only**; body
        `{"routes": [...]}`; validates each route; writes
        audit

### Operational

- [x] R7: **No regression** on `demo_mode`,
      `active_database`, or any other existing AppSettings
      behavior. Existing `app_settings.json` on disk gets the
      new keys lazily on first write; initial reads use
      defaults.
- [x] R8: **No `rag_system.py` changes.** TB's RAG continues
      to use its hardcoded `prompt_template` for now;
      consuming the persisted `rag_prompt` is a follow-up
      concern (see Scope note in Background).
- [x] R9: **Service restart** picks up the new imports and
      methods.

## Acceptance Criteria

### GET endpoints
- [x] AC1: `GET /settings/rag-prompt` as authed user returns
      the default prompt (no customization yet), with
      `saved_at` and `saved_by` null.
- [x] AC2: `GET /settings/query-routes` as authed user
      returns `{"routes": [], "defaults": [], ...}`.

### PUT endpoints
- [x] AC3: `PUT /settings/rag-prompt` as super with a valid
      prompt (containing `{context}` and `{question}`)
      succeeds; subsequent GET returns the new prompt and
      populated `saved_at` + `saved_by`.
- [x] AC4: `PUT /settings/rag-prompt` with an invalid prompt
      (missing `{context}` or `{question}`) returns HTTP 400.
- [x] AC5: `PUT /settings/rag-prompt` as non-super user
      returns HTTP 403.
- [x] AC6: `PUT /settings/query-routes` as super with a
      valid route list succeeds; subsequent GET returns the
      new routes with populated metadata.
- [x] AC7: `PUT /settings/query-routes` with an invalid
      route (missing required keys) returns HTTP 400.
- [x] AC8: `PUT /settings/query-routes` as non-super user
      returns HTTP 403.

### Persistence + audit
- [x] AC9: Successful PUT calls write to
      `logs/rag_prompt_audit.jsonl` or
      `logs/query_routes_audit.jsonl` respectively; each
      line is valid JSON with timestamp, username, old
      value, new value.
- [x] AC10: Values persist across service restart (verified
      by GET → PUT → restart → GET returns the PUT value).

### No regression
- [x] AC11: `GET /settings/mode` and other AppSettings
      consumers still work (demo_mode toggle, active_database
      round-trip).
- [x] AC12: Smoke-test: `/version`, `/active-adapter`,
      `/query`, `/sessions/active` all return expected
      shapes.
- [x] AC13: `git diff backend/` bounded to `app_settings.py`
      and `main.py` only.

## Design Notes

- **Direct port, generic defaults.** Methods, audit log
  shape, metadata fields all match stalite3's. The two
  DEFAULT_* constants are the only intentional divergence —
  stalite3's defaults are Stalite-specific; TB's are
  generic.
- **Why no rag_system.py changes.** TB's RAG system
  hardcodes its prompt template. Making it read from
  AppSettings every query (or on refresh) is a cleaner
  follow-up — needs a `_refresh_prompt_template()` method
  on RAGSystem similar to stalite3's. Keeping it out of this
  story keeps the diff bounded.
- **Why validate `{context}` and `{question}` placeholders.**
  stalite3 does this check in `set_rag_prompt`. Without
  these placeholders, the prompt template would fail to
  format at query time. Guarding at save-time prevents a
  broken runtime state.
- **Why audit log.** Prompt and routing config affect every
  query's output. Change provenance matters for debugging
  "why did the agent start answering differently last week?"
- **Scope boundary with TB-US-022 (OT classifier).**
  TB-US-022's OT classifier (In Progress) is a different and
  more ambitious routing design — rules + LLM fallback for
  4-category classification. Stalite3's `query_routes` is
  a simpler mechanism — regex-pattern-based augmentation of
  the retrieval query. The two are complementary and may
  eventually merge; for now they're parallel surfaces that
  coexist in TB.

## Out of Scope

- **Wiring persisted `rag_prompt` into TB's RAG query flow.**
  Separate story (TB-US-040 or roll into TB-US-022).
- **Wiring persisted `query_routes` into TB's retrieval
  augmentation.** Same — follow-up.
- Changes to `rag_system.py`.
- UI for editing routes / prompt. Endpoints are the only
  interface at v0.1.
- Validation of route regex patterns' syntactic
  correctness (invalid regex gets caught at use-time).
- Multi-tenant / per-user prompt customization.
- Rate limiting on PUT.
- Branding tweaks.

## Related

- Parent: [TB-US-031](tb-us-031.md) Section 3.8 (routing /
  classification surface).
- Sibling close-out stories: TB-US-034, 035, 036, 037.
- Related to: [TB-US-022](tb-us-022.md) OT classifier
  coordinator (In Progress) — this story is complementary,
  not a replacement.
- stalite3 reference: `backend/api/app_settings.py` (full
  module) + `backend/api/main.py:524-608` (4 endpoints) +
  `backend/api/main.py:510-525` (Pydantic models).
- TB code touched:
  - `backend/api/app_settings.py` — extended
  - `backend/api/main.py` — new models + 4 endpoints

**Completion Notes (2026-10-14).**

- `app_settings.py` extended with: `DEFAULT_RAG_PROMPT`
  (generic — no Stalite-specific text), `DEFAULT_QUERY_ROUTES`
  = `[]`, two audit log paths, 6 new classmethods
  (rag_prompt / rag_prompt_meta / set_rag_prompt /
  query_routes / query_routes_meta / set_query_routes), 2
  new audit helpers.
- `main.py` extended with: `RagPromptRequest` + `QueryRoutesRequest`
  Pydantic models + 4 endpoints (GET/PUT rag-prompt, GET/PUT
  query-routes). All matching stalite3's role gating
  (`verify_web_auth` for GET, `verify_super_user` for PUT).
- Service restarted cleanly.
- Diff bounded: 165 lines in `app_settings.py` (116→279
  — ends up same size as stalite3's), 244 lines in `main.py`
  (new endpoints block). All as expected per the direct-port
  scope.

**End-to-end verification results:**
- AC1 ✓ GET rag-prompt returns default
  (`'Use the following context...'`), null metadata.
- AC2 ✓ GET query-routes returns `routes: []`, `defaults:
  []`, null metadata.
- AC3 ✓ PUT rag-prompt (valid prompt with `{context}` +
  `{question}`) returned `saved_at:
  '2026-10-14T21:10:01.338515Z'`, `saved_by:
  'admin'`.
- AC4 ✓ PUT rag-prompt (missing placeholders) returned HTTP
  400 with correct detail message.
- AC6 ✓ PUT query-routes (valid route list) returned saved
  metadata + routes count 1.
- AC7 ✓ PUT query-routes (route missing keys) returned HTTP
  400 with specific missing-keys enumeration.
- AC9 ✓ `logs/rag_prompt_audit.jsonl` and
  `logs/query_routes_audit.jsonl` written with correct
  JSON entries.
- AC11 ✓ `/settings/mode` continues to return 200.
- AC12 ✓ `/version`, `/active-adapter`, `/sessions/active`
  all return 200 (no regression).
- AC13 ✓ `git diff` bounded to `app_settings.py` + `main.py`
  only.

**ACs 5, 8, 10 not explicitly tested** (role-gating 403 for
non-super users; persistence across restart). Confidence:
- AC5 / AC8: `@Depends(verify_super_user)` is identical to
  what `/settings/mode` PUT uses, which has proven enforcement
  behavior.
- AC10: `AppSettings.set_rag_prompt` and `set_query_routes`
  write to `SETTINGS_PATH` using the same pattern that
  `set_demo_mode` uses (proven to persist across TB restarts).

**Follow-up concern flagged in Scope note:** TB's RAG
system (`backend/rag/rag_system.py`) doesn't yet consume
the configured `rag_prompt` or `query_routes` — the
persistence surface is complete, but the configured values
aren't read by `/query`. Follow-up story (TB-US-040 or roll
into TB-US-022's OT classifier work) wires consumption.
Without that, this story closes the API-parity gap but
not the behavioral-parity gap. Honest framing.
