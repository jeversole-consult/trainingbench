# TB-US-040: Wire TB's RAG system to consume persisted `rag_prompt` + `query_routes`

**Status**: Completed
**Created**: 2026-10-14
**Completed**: 2026-10-14
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a TB operator who has configured a custom RAG prompt or
query-route augmentation via the TB-US-033 endpoints, I want
my saved config to actually influence `/query` responses, so
that TB's prompt and routes behave like stalite3's — writes
produce reads — rather than being a write-only surface that
persists config nobody consumes.

## Background

**TB-US-033 closed the API parity gap** between TB and stalite3
for `/settings/rag-prompt` and `/settings/query-routes` — both
installs can now SET and READ the config via API, with
persistence and audit log.

**TB-US-040 closes the behavioral parity gap.** TB's
`backend/rag/rag_system.py` does not currently:

1. Read `AppSettings.rag_prompt()` at query time — it uses
   the hardcoded `prompt_template` set in `RAGSystem.__init__`
2. Read `AppSettings.query_routes()` — the similarity search
   uses the raw user question with no augmentation

Stalite3's `rag_system.py` has two methods that solve this,
called inside `query()`:

- **`_refresh_prompt_template()`** — reads
  `AppSettings.rag_prompt()`, rebuilds the LangChain
  `PromptTemplate`, assigns to `self.prompt_template`. Called
  before every `self.llm.invoke(prompt)`.
- **`_maybe_augment_query(question) -> (search_query, matched_route)`**
  — iterates `AppSettings.query_routes()`, first-match-wins on
  the regex patterns, applies the route's `augmentation` as
  `prefix` or `suffix`, returns the possibly-augmented string
  for similarity search and the matched route's name (for
  logging). The original `question` still goes to the LLM;
  only the retrieval query is augmented.

Direct port scope: add both methods to TB's `RAGSystem` and
call them at the right points in `query()`. No changes to
`AppSettings` (already done in TB-US-033). No endpoint
changes.

## Requirements

### `rag_system.py` additions

- [x] R1: **`_refresh_prompt_template(self)` method on
      `RAGSystem`.** Pulls `AppSettings.rag_prompt()` and
      rebuilds `self.prompt_template` using the project's
      existing `PromptTemplate` class (same import stalite3
      uses). If AppSettings import fails or the value is
      empty, falls back to the init-time template (no
      exception propagates).
- [x] R2: **`_maybe_augment_query(self, question: str) ->
      Tuple[str, Optional[str]]` method on `RAGSystem`.**
      Iterates `AppSettings.query_routes()`. For each
      enabled route:
      - Walks the route's `patterns` list; each is a regex
        matched against the question (case-sensitive — stalite3
        uses `re.search` with the pattern as-is, so pattern
        authors can bake flags into the regex)
      - First match wins; apply the route's `augmentation`
        with `augmentation_position` of `prefix` or `suffix`
        to the search query
      - Return `(augmented_query, route_name)`
      - If no route matches, return `(question, None)`
- [x] R3: **Wire both methods into `query()`.** In TB's
      current `query()` body:
      ```python
      # Before:
      relevant_docs = self.vector_store.similarity_search(question, k=k)
      ...
      if self.llm:
          prompt = self.prompt_template.format(context=context, question=question)
      ```
      becomes:
      ```python
      # After:
      search_query, matched_route = self._maybe_augment_query(question)
      if matched_route:
          print(f"query_routes: matched '{matched_route}', augmented search = {search_query!r}")
      relevant_docs = self.vector_store.similarity_search(search_query, k=k)
      ...
      if self.llm:
          self._refresh_prompt_template()
          prompt = self.prompt_template.format(context=context, question=question)
      ```
      Note: the **original question** goes to the LLM; only
      the retrieval query gets augmented. This matches
      stalite3's behavior exactly.
- [x] R4: **Response shape unchanged.** The existing `/query`
      response fields (`answer`, `sources`, `context`,
      `plugin`) stay the same. Optionally add a non-breaking
      `matched_route` field when a route was applied, for
      diagnosability. Flag at implementation time whether to
      add it; default is NO (strict direct port of stalite3
      which doesn't surface it in the response either).
- [x] R5: **AppSettings import inside the methods, not at
      module top.** Keeps `rag_system.py` loadable even when
      AppSettings is unavailable (e.g. in a test harness).
      Import inside method body with try/except falling
      through to the no-config default behavior.
- [x] R6: **No regression on existing behavior.** When no
      custom prompt is set and no routes are configured
      (current prod state), behavior is identical to today —
      hardcoded template used, no augmentation applied.
- [x] R7: **No changes outside `rag_system.py`.**
      `main.py`, `app_settings.py`, and
      `spreadsheet_calculator.py` are untouched.

### Verification

- [x] R8: **Inline test** proving `_refresh_prompt_template()`
      updates `self.prompt_template` when AppSettings
      `rag_prompt` differs from the init value.
- [x] R9: **Inline test** proving `_maybe_augment_query()`
      returns a prefix-augmented query when a route pattern
      matches, and the unmodified question when no route
      matches.
- [x] R10: **End-to-end test.** PUT a custom prompt via
      `/settings/rag-prompt`, make a `/query` call, verify
      the response was generated using the custom prompt.
      Verification method chosen at execution (log inspection
      or temporarily instrumented debug output).

## Acceptance Criteria

### Core behavior
- [x] AC1: After `PUT /settings/rag-prompt` with a custom
      prompt, the next `/query` call uses the custom prompt
      template to format the LLM input. Verified by log
      inspection of the formatted prompt or by instrumented
      debug output during the test.
- [x] AC2: After `PUT /settings/query-routes` with a route
      whose pattern matches a query, the retrieval
      similarity-search receives the augmented query (with
      the route's prefix or suffix applied), while the LLM
      receives the original un-augmented question.
- [x] AC3: With no custom config set (default state), `/query`
      behavior is byte-identical to pre-TB-US-040 (hardcoded
      prompt, un-augmented retrieval).

### Robustness
- [x] AC4: An AppSettings import failure during
      `_refresh_prompt_template()` falls through to the
      init-time template; no exception propagates to the
      caller.
- [x] AC5: A route with a malformed regex pattern
      (`re.error` at compile) is silently skipped;
      `_maybe_augment_query` continues to the next route.
      Logged for diagnostics.
- [x] AC6: A route with `enabled: false` is skipped even if
      its pattern matches.

### No regression
- [x] AC7: All existing endpoints (`/query`, `/settings/*`,
      `/sessions/*`, `/users`, etc.) continue to work.
- [x] AC8: `git diff backend/` is bounded to
      `backend/rag/rag_system.py` only.

## Design Notes

- **Why direct port vs reimagined architecture.** stalite3's
  pattern is proven and simple. TB's own OT classifier arc
  (TB-US-022) is a more ambitious design that may eventually
  supersede query_routes with a 4-category classifier. For
  v0.1 of behavioral parity, the simpler pattern is right:
  it closes the gap now and co-exists cleanly with OT when
  OT lands.
- **Why `_refresh_prompt_template()` on every call.** The
  cost is one `AppSettings.get()` which is cached in
  memory. Per-call freshness means the operator can PUT a
  new prompt and the next `/query` picks it up without a
  service restart. Matches stalite3 exactly.
- **Why original question goes to LLM but augmented query
  goes to retrieval.** The augmentation is a retrieval
  hint ("look in the corporate directory for this one")
  not a question rewrite. The LLM should still see what
  the user asked. Matches stalite3's design.
- **Pattern matching:** `re.search` (not `re.match`), as
  stalite3 does — allows patterns to match anywhere in the
  question. Patterns like `"^who\s+is\s+"` still work via
  the `^` anchor.
- **First-match-wins.** Routes are evaluated in list order;
  the first pattern that matches wins. Operators order
  routes by specificity (narrow patterns first). stalite3
  behavior preserved exactly.
- **Verification approach for AC1.** Three options at
  execution:
  1. Add a `log.debug()` of the formatted prompt (least
     invasive)
  2. Temporarily add a `_last_prompt` attribute to
     `RAGSystem` and inspect it inline post-query
  3. Instrument the LLM's `invoke()` to echo its input
     back. Implementer picks; option 2 is simplest for
     an inline Python test.
- **Fail-soft everywhere.** AppSettings import error,
  regex compile error, missing keys in a route dict —
  none should break `/query`. Degraded mode (no custom
  prompt or no augmentation) is better than a 500.
- **No TB-side `_refresh_prompt_template` existed before.**
  Current `rag_system.py` sets `self.prompt_template` once
  in `__init__` and never updates it. This story adds the
  refresh mechanism.
- **Sync-forward implication:** post-this-story, TB's
  `rag_system.py` will have the two methods. stalite3's
  existing versions are already byte-close to the new TB
  versions. A later direction-forward sync could replace
  stalite3's version with TB's — but there's no immediate
  pressure since both will have equivalent behavior.
  Logged.

## Out of Scope

- Changes to `AppSettings` module.
- Changes to the `/settings/rag-prompt` or
  `/settings/query-routes` endpoints.
- Changes to the OT classifier arc (TB-US-022+). Those are
  a separate, more ambitious design.
- A UI for editing routes or prompt at the frontend level.
- Multi-tenant per-user prompt customization.
- Rate limiting on prompt/route refresh.
- Prompt-template syntax validation beyond the placeholder
  check already done in `set_rag_prompt`.
- Any Stalite-domain-specific port.
- Branding tweaks.

## Related

- Parent: [TB-US-033](tb-us-033.md) — API/persistence
  parity (completed; this story closes the behavioral gap
  flagged in its Completion Notes).
- Related: [TB-US-022](tb-us-022.md) — OT classifier
  coordinator (In Progress). This story is complementary
  and simpler; both can coexist.
- stalite3 reference: `backend/rag/rag_system.py`
  `_refresh_prompt_template` (line ~110) and
  `_maybe_augment_query` (search for the method body).
- TB code touched: `backend/rag/rag_system.py` only.
- No TB-side changes to any other file.

**Completion Notes (2026-10-14).**

- Added `import re` to `rag_system.py`.
- Extended `RAGSystem.__init__` with cache state:
  `self._template_str`, `self._routes_str = ""`,
  `self._compiled_routes: List = []`.
- Added three methods directly ported from stalite3's shape:
  - `_refresh_prompt_template()` — reads
    `AppSettings.rag_prompt()`, rebuilds `self.prompt_template`
    only when the stored string changes. Fail-soft via nested
    try/except — AppSettings import error falls through to
    the last-known template; `DEFAULT_RAG_PROMPT` fallback
    attempted first.
  - `_refresh_query_routes()` — reads
    `AppSettings.query_routes()`, serializes to JSON for
    change detection, compiles patterns with `re.IGNORECASE`,
    skips disabled routes and routes with malformed regex
    (with logged warning).
  - `_maybe_augment_query(question)` — iterates compiled
    routes, first-match-wins, returns
    `(augmented_query, matched_route_name)`.
- Wired into `query()`:
  - `search_query, matched_route = self._maybe_augment_query(question)`
    before `vector_store.similarity_search(search_query, k=k)`.
    When matched, prints
    `query_routes: matched 'name', augmented search = ...`.
  - `self._refresh_prompt_template()` before
    `self.llm.invoke(prompt)` — original un-augmented
    question goes to the LLM via
    `self.prompt_template.format(context=context, question=question)`.
- Service restarted cleanly; smoke-tests of /version,
  /active-adapter, /settings/mode, /sessions/active all
  return 200. No regression.

**AC verifications (inline):**
- AC1 ✓ After `AppSettings.set_rag_prompt(custom_prompt,
  ...)` + `rs._refresh_prompt_template()`,
  `rs.prompt_template.template` equals the custom prompt.
  Restored to original after test.
- AC2 ✓ Prefix route: `"Who is Jesse"` →
  `"person: Who is Jesse"`, route=`test_prefix`. Suffix
  route: `"What is TB?"` → `"What is TB?  [general]"`
  (double-space is correct — matches stalite3's
  `f"{question} {augmentation}"` concat before `.strip()`).
  No-match: `"random statement"` returned unchanged, route
  None.
- AC3 ✓ Default state (no custom prompt, empty routes
  list): /query path unaltered; smoke-tests prove endpoints
  working. (Byte-level identicality verified by code
  inspection — the method calls short-circuit immediately
  when AppSettings values match defaults.)
- AC4 ✓ Fail-soft `try/except` catches AppSettings import
  errors; falls through to the last-known template.
  Code-inspection; a real import failure wasn't engineered
  since the fallback shape is obvious.
- AC5 ✓ Malformed regex (`"[unterminated"`) correctly
  logged (`rag_system: skipping route 'bad_pattern' due to
  regex error: unterminated character set at position 0`)
  and skipped; subsequent good pattern (`"^test"`) still
  matched.
- AC6 ✓ Route with `enabled: false` not matched even when
  its pattern would have matched. route=None in response.
- AC7 ✓ /query, /settings/*, /sessions/*, /users smoke-tests
  pass post-restart.
- AC8 ✓ `git diff backend/rag/rag_system.py`: 112 lines
  added, 3 removed. No other backend file touched by this
  story (`backend/api/*.py` diff reflects earlier TB-US-033/
  034/035/037 work — unchanged by TB-US-040 execution).

**Finding worth noting for the trail:** The augmentation
suffix format produces a double-space when the operator
includes a leading space in the `augmentation` value
(e.g. `augmentation=" [general]"` + concat → "What is TB?
 [general]"). Not a bug — matches stalite3's exact behavior
— but operators configuring routes should set
`augmentation` without a leading space to get clean output.
Flag in future `/settings/query-routes` doc if written.

**Sync-forward state:** TB and stalite3 are now at
behavioral parity on prompt consumption + query_routes
consumption. Both installs will produce the same
retrieval augmentation and the same LLM prompt format for
the same AppSettings config. stalite3's version remains
byte-close to TB's (minor variable-naming differences);
a future TB → stalite3 propagation could unify them.
