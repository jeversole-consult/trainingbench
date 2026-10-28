# TB-US-026: Lookup handler — structured-source queries

**Status**: In Progress
**Created**: 2026-10-14
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As the operator of an OT-equipped TrainingBench agent, I want a
**lookup handler** that routes classified prompts to queries
against structured sources (directory documents, JSON files,
small databases), so that factual retrievals — "who is X," "what
is X's phone number," "where is X" — return exact facts from
the authoritative source rather than LLM-hallucinated guesses.

## Background

Per the OT context doc, lookup is the category for prompts
that need **retrieval of specific factual information from
structured sources**. Example patterns: `"who is..."`,
`"what is X's phone number"`, `"where is..."`.

The design principle is the same as the quantitative handler:
when the right answer lives in a structured source, retrieve
it exactly instead of asking an LLM to approximate it.

v0.1 ships a framework for registering lookup sources + at
least one concrete source wired up to prove the architecture.

## Requirements

### Framework

- [ ] R1: **Lookup source registry.** Module
      `backend/api/handlers/lookup.py` exposes:
      ```python
      LOOKUP_SOURCES: Dict[str, LookupSource] = {}

      def register(name: str) -> Callable:
          # decorator / direct call registers a LookupSource subclass

      class LookupSource(Protocol):
          def extract_entities(self, prompt: str) -> Dict
              # pull entity references from the prompt
          def query(self, entities: Dict) -> List[Dict]
              # return matched records
          def format(self, records: List[Dict], prompt: str) -> str
      ```
- [ ] R2: **Handler entry point.** Function
      `handle_lookup(prompt: str, audit_entry: dict) -> str`
      that:
      1. Selects a lookup source (v0.1 heuristic: try each;
         first with non-empty `extract_entities` wins).
      2. Calls `query(entities)`.
      3. Calls `format(records, prompt)`.
      4. Logs handler details to the audit entry.
      5. Returns the formatted response.
- [ ] R3: **At least one concrete lookup source** registered
      at v0.1: `directory_json` — reads from a configurable
      JSON file at `config/ot/lookup/<source_name>.json` with
      a flat list of records. Example schema:
      ```json
      [
        {"name": "Jesse Eversole", "role": "Founder",
         "email": "operator@example.com", "phone": null},
        {"name": "Ted Corvette", "role": "Collaborator",
         "email": "tedcorvette@gmail.com", "phone": null}
      ]
      ```
      Entity extraction matches names (case-insensitive
      substring) against prompts like
      `"what is Jesse's email"`.
- [ ] R4: **No-match case.** If no lookup source extracts
      entities or no records match, return a clear response:
      `"No matching record found."` Log
      `handler.success = false` with reason.
- [ ] R5: **Error handling.** Exceptions during query (file
      not found, parse error, etc.) are caught, logged in
      the audit entry, and returned to the caller as a
      user-safe error.

### Source management

- [ ] R6: **Config file discovery.** On startup, the handler
      scans `config/ot/lookup/*.json` and registers each as a
      `directory_json` source keyed by filename stem. No
      restart required to add a new source — a file watcher
      (optional in v0.1) or a reload-on-first-miss strategy
      is acceptable. Simplest: load at startup; new files
      require a restart. Reload-at-first-miss is a nice
      follow-up.

### Role gating

- [ ] R7: **No in-handler role check.** OT router (TB-US-028)
      enforces role; any authenticated user whose request
      reaches this handler is allowed to query.

## Acceptance Criteria

- [ ] AC1: Place a directory file at
      `config/ot/lookup/people.json` with the sample schema
      from R3. Calling
      `handle_lookup("what is Jesse's email", audit_entry={})`
      returns `"Jesse Eversole's email is
      operator@example.com."` (or similarly formatted).
      The audit entry has `handler.calculator = "directory_json"`
      (or an equivalent provenance field),
      `handler.success = true`.
- [ ] AC2: Calling with a prompt that no source matches
      returns the "no match" response with
      `handler.success = false`.
- [ ] AC3: A malformed source file (invalid JSON) is logged
      as an error, is skipped at registration time, and does
      not crash the handler for other sources.
- [ ] AC4: Registering a new lookup source via the registry
      pattern works without modifying the handler's dispatch
      code.
- [ ] AC5: `handle_lookup()` is importable and callable from
      the router without going through HTTP.
- [ ] AC6: No LLM is called in any lookup-handler path.
      Confirmed by code inspection.
- [ ] AC7: A lookup against a source with 1,000 records
      returns in <100ms on current hardware (perf not a
      hard requirement; sanity bound).

## Design Notes

- **Why JSON files for v0.1 instead of SQLite / Postgres.**
  Smallest deployable surface. JSON files are editable in a
  text editor, version-controllable, and sufficient for
  TB's current scale. The abstraction (`LookupSource`
  protocol) lets a future `SQLiteSource` or `PostgresSource`
  drop in without changing callers.
- **Entity extraction is the hardest part — but keep it
  simple.** v0.1: case-insensitive substring match against
  record keys. If the prompt mentions a name present in the
  directory, that record wins. Multi-entity extraction is
  v0.2+.
- **Why no HTTP endpoint for direct lookup call.** Same
  reason as the quantitative handler — OT pipeline is
  classify → route → handle. Direct access skips the audit
  and defeats OT's diagnostic clarity.
- **Format is a formatted human-readable string.** As with
  the quantitative handler. Machine-readable records belong
  in a separate (non-OT) retrieval API if ever wanted.
- **File watcher is optional in v0.1.** Scanning `config/ot/
  lookup/*.json` on startup is enough. Reload-at-first-miss
  (on a cache miss, re-scan the directory) is a nice-to-have
  that keeps restart-free source additions working without a
  real watcher.
- **Record schema is flexible.** The JSON file is the source
  of truth; the format callback renders it. If one source has
  `{name, email, phone}` and another has `{title, author,
  isbn}`, both work — each source's format callback produces
  appropriate text.

## Out of Scope

- **Database-backed sources** (SQLite, Postgres,
  Elasticsearch). Abstraction supports them; implementation
  is a later story.
- **Multi-entity queries** (e.g., "what is Jesse's and Ted's
  email"). Falls into the mixed handler (TB-US-027) as a
  decomposition problem.
- **Fuzzy / semantic matching.** v0.1 is substring match.
  Fuzzy / semantic are v0.2+ or belong in the qualitative
  handler.
- **Write operations** (adding records via the lookup
  handler). Lookup is read-only; writes go through a
  dedicated admin surface.
- **PII masking** in responses. Records are returned as-is;
  a redaction layer is a separate concern.
- **Join / cross-source queries.** v0.1 queries one source
  per prompt. Composing results from multiple sources is a
  mixed-handler concern.
- **Direct-invocation HTTP endpoint.**
- **Branding tweaks.**

## Related

- Parent: [TB-US-022](tb-us-022.md) — OT coordinator.
- Called by: [TB-US-028](tb-us-028.md) — OT router.
- Logs to: [TB-US-024](tb-us-024.md) — audit module.
- Verified by: [TB-US-029](tb-us-029.md) — math example
  may include some lookup queries to exercise this handler
  (though math is primarily quantitative — if a lookup
  dimension doesn't fit, the example may defer lookup
  verification to a follow-up).
- Sibling handlers: [TB-US-025](tb-us-025.md) (quantitative),
  [TB-US-027](tb-us-027.md) (mixed),
  [TB-US-028](tb-us-028.md) (qualitative via OT routing).
- Context: `docs/ot-context-for-claude-code_1.md` lines
  33–36 (category description), 85–89 (handler description).
