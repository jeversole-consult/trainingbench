# TB-US-023: Four-category prompt classifier (v0.1)

**Status**: In Progress
**Created**: 2026-10-14
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As the operator of a TrainingBench agent, I want every
incoming prompt classified into one of four categories —
**qualitative**, **quantitative**, **lookup**, **mixed** —
before any handler runs, so that the OT router can send each
prompt to the appropriate handler and so that classification
decisions are visible, auditable, and improvable.

## Background

Classification is the first step in the OT pipeline (per
`docs/ot-context-for-claude-code_1.md`). v0.1 uses:

- **Rules-based classification** for obvious cases
  (e.g. `"how much"` → quantitative, `"who is"` → lookup).
- **LLM fallback** for anything that doesn't match a rule.
  The fallback is a small, fast model (Llama 3.2 3B, Qwen 2.5
  3B, or similar) with a system prompt that returns one of
  the four categories.
- **Classification runs before any content generation**, so
  routing cost is a classifier call, not a full RAG query.

The classifier is a prerequisite for every other handler story
in the OT arc (TB-US-025 through TB-US-028). v0.2 (TB-US-???)
will later replace the rules + LLM path with a trained
classifier adapter; v0.1 keeps the simpler form.

## Requirements

### Core classification

- [ ] R1: **`POST /ot/classify` endpoint.** Request body:
      ```python
      class ClassifyRequest(BaseModel):
          prompt: str
          user_context: Optional[Dict] = None  # future-proofing
      ```
      Response:
      ```python
      class ClassifyResponse(BaseModel):
          category: Literal["qualitative", "quantitative", "lookup", "mixed"]
          source: Literal["rule", "llm"]          # which path matched
          rule_name: Optional[str] = None         # name of the matched rule, if any
          confidence: Optional[float] = None      # LLM confidence if available
          latency_ms: int
      ```
- [ ] R2: **Rules-based first pass.** A configurable set of
      pattern-matching rules runs first. Each rule has: a name,
      a pattern (regex or substring match), and a target
      category. First match wins. Rules live in a config file
      (`config/ot/classifier-rules.json` or similar — path
      finalized at execution) so operators can tune without a
      code change.
- [ ] R3: **LLM fallback.** When no rule matches, call a small
      local LLM (via the same Ollama path TB already uses in
      the RAG). The system prompt instructs the model to
      return exactly one of the four category tokens. Parse
      the response; if the model returns anything other than
      a valid category token, default to `qualitative` and
      log the parse failure.
- [ ] R4: **Model configurability.** The LLM fallback model
      name is read from an env var `OT_CLASSIFIER_MODEL`
      (default: `llama3.2:3b` or whichever small model TB has
      pulled). Default documented.
- [ ] R5: **Latency measurement.** Return `latency_ms` in the
      response. Target: rules path < 1ms, LLM fallback < 500ms
      on the current hardware. Not a hard requirement; a
      Design Notes guideline for the operator to monitor.
- [ ] R6: **Thread-safe / request-safe.** Multiple concurrent
      requests do not share classifier state in ways that
      cause miscategorization. Rules are read-only; LLM calls
      are stateless.
- [ ] R7: **Pydantic models** live near existing TB models in
      `backend/api/main.py`.

### Auditability

- [ ] R8: **Every classification call logs to the OT audit
      stream** (via TB-US-024's logging interface). The log
      entry carries: prompt, category, source (rule/llm),
      rule_name (if applicable), latency_ms, user. If
      TB-US-024 is not yet shipped when this story is
      implemented, this requirement conditionally defers to a
      follow-up linking commit; the classifier works without
      the audit log but **should not silently skip the audit
      hook** — the hook call is present, the implementation
      may be a no-op stub until TB-US-024 lands.

### Role gating

- [ ] R9: **Classification endpoint is authenticated.** Any
      authenticated user can call `/ot/classify`. Rate limiting
      follows TB's existing `/query` 20/minute pattern.

### Internal programmatic API

- [ ] R10: **Internal function `classify_prompt(prompt: str)
      -> ClassifyResponse`** callable from other OT handlers
      and the OT router (TB-US-028) without going through
      HTTP. The HTTP endpoint is a thin wrapper around this
      function.

## Acceptance Criteria

- [ ] AC1: `POST /ot/classify` with a prompt like
      `"How much does X cost?"` returns
      `{category: "quantitative", source: "rule", ...}`.
- [ ] AC2: `POST /ot/classify` with a prompt like
      `"Who is the CEO of X?"` returns
      `{category: "lookup", source: "rule", ...}`.
- [ ] AC3: `POST /ot/classify` with an ambiguous prompt that
      no rule matches returns a `source: "llm"` response with
      a valid category.
- [ ] AC4: Editing the rules file and restarting the service
      (or whatever hot-reload mechanism is chosen) results in
      the new rules taking effect without a code change.
- [ ] AC5: Classifier returns `qualitative` as the safe
      default if the LLM fallback returns a malformed response.
      The parse failure is logged.
- [ ] AC6: `latency_ms` is populated and plausible for both
      the rules path (fast) and the LLM path (slower).
- [ ] AC7: Calling `classify_prompt()` directly (not via
      HTTP) returns the same type of response object. Verified
      by inline test or by another handler story's
      integration.
- [ ] AC8: Pydantic models validate: a request with
      `prompt: null` or missing is a 422; a response always
      has exactly one of the four category literals.

## Design Notes

- **Rules go first for cost and speed.** The LLM fallback
  costs ~100–500ms. Rules cost ~0ms. Pushing obvious cases
  to rules reduces total system latency and reduces load on
  the small LLM.
- **Rule file shape.**
  ```json
  [
    {"name": "cost_amount",     "pattern": "(?i)how much",   "category": "quantitative"},
    {"name": "person_lookup",   "pattern": "(?i)who is",     "category": "lookup"},
    {"name": "explain_pattern", "pattern": "(?i)^explain\\b", "category": "qualitative"},
    ...
  ]
  ```
  Regexes are powerful but risky; keep rules **conservative**
  — a rule should match only when the category is unambiguous.
  Ambiguous cases should fall through to the LLM.
- **LLM system prompt.** A short, prescriptive instruction:
  > You are a prompt classifier. Read the user's prompt and
  > respond with exactly one word: qualitative, quantitative,
  > lookup, or mixed. No other output.
  >
  > qualitative = reasoning, interpretation, synthesis
  > quantitative = calculation using formulas or deterministic math
  > lookup = retrieval of specific factual information
  > mixed = combines two or more of the above
- **Why default to qualitative on parse failure.** Qualitative
  is the handler most likely to produce a useful fallback
  response — it has the RAG. A misclassified prompt that
  routes to RAG + LLM will at least generate something
  plausible, whereas a misclassified prompt that routes to a
  calculator will fail outright.
- **Classifier is NOT the router.** The classifier returns a
  category; a separate component (TB-US-028's router) uses
  the category to dispatch to a handler. Keeping these
  separate makes v0.2's classifier-adapter swap easier.
- **Why `source` in the response.** Operator will want to
  know whether classification came from a rule (fast,
  explainable) or from the LLM (opaque, needs tuning). The
  `source` field surfaces this without needing to inspect
  the audit log.
- **Caching NOT in v0.1.** No prompt-hash → category cache.
  Classifier is already fast on the rules path and we don't
  want to introduce cache invalidation complexity for v0.1.
- **Model choice.** Llama 3.2 3B is a strong default for the
  fallback. Qwen 2.5 3B is a reasonable alternative. Both
  run on consumer hardware. Larger models would be overkill;
  smaller models (<1B) are too noisy at classification.

## Out of Scope

- **v0.2 — trained classifier adapter.** Replaces this
  rules + LLM scheme with a PEFT-trained adapter. Separate
  story.
- **Audit log implementation** itself — this story *calls*
  the audit log interface (R8); building that interface is
  TB-US-024.
- **Routing / dispatch** to the appropriate handler.
  Classification returns a category; dispatch is TB-US-028.
- **Mixed-handler decomposition logic.** The classifier
  identifies something as mixed; TB-US-027 decomposes it.
- **Per-domain classification tuning** (e.g., medical-domain
  rules vs legal-domain rules). v0.3+ concern.
- **UI for editing classification rules.** Rules file is
  edited directly; UI is a follow-up if operators tune
  frequently.
- **A/B classifier comparison.** Future story.
- **Multi-language classification.** English-only in v0.1.
- **Branding tweaks** (per the deferred-branding memory).

## Related

- Parent: [TB-US-022](tb-us-022.md) — OT coordinator.
- Depends-on: [TB-US-024](tb-us-024.md) — audit log
  interface (R8 soft-depends; see Design Notes).
- Downstream: [TB-US-028](tb-us-028.md) — OT router that
  consumes classifications.
- Context: `docs/ot-context-for-claude-code_1.md` — the four
  categories (lines 23–42).
- Reference impl patterns in TB's existing `/query` handler
  (`backend/api/main.py:688`) for the Ollama small-LLM call
  shape.
