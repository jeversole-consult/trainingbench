# TB-US-024: OT audit log — classification and handler decisions

**Status**: In Progress
**Created**: 2026-10-14
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As the operator or an admin reviewing TrainingBench's OT
pipeline, I want every prompt processed through the OT router
to leave a complete audit entry — the prompt, the
classification decision, the handler used, the response
produced, and all relevant timing and provenance metadata —
so that failures are diagnosable, improvements are targetable,
and the accumulated audit log is a usable data source for v0.2's
trained classifier adapter later.

## Background

Per the OT context doc, the audit log is **the key data source
that enables most future improvements** — not just a diagnostic
trail. It is both:

- **Operational observability** — "why did this prompt get
  routed to the quantitative handler? what did it return?"
- **Training data provenance** — "which classifications were
  correct? which were corrected by SMEs? the labels train the
  v0.2 classifier adapter."

This story builds the audit log interface and the storage
layer. TB-US-023 and TB-US-025 through TB-US-028 all call this
interface to log their decisions. The log must be designed to
support both uses from day one — operational browsing and
machine-readable export.

## Requirements

### Storage

- [ ] R1: **Append-only JSONL files.** One file per month at
      `logs/ot_audit/<YYYY-MM>.jsonl`. Rotation happens
      automatically on month boundary. Files are **never**
      edited after write.
- [ ] R2: **Entry schema.** Each JSONL line is a JSON object:
      ```json
      {
        "entry_id": "uuid4",
        "timestamp": "2026-10-14T15:23:11.428Z",
        "username": "jeversole",
        "user_type": "training",
        "prompt": "...",
        "classification": {
          "category": "quantitative",
          "source": "rule",
          "rule_name": "cost_amount",
          "confidence": null,
          "latency_ms": 1
        },
        "handler": {
          "name": "quantitative",
          "calculator": "math_basic",
          "parameters": {...},
          "latency_ms": 12,
          "success": true,
          "error": null
        },
        "response": "...",
        "total_latency_ms": 15
      }
      ```
      Classification subfields align with TB-US-023's response
      shape. Handler subfields depend on the handler; `name`
      is required, the rest are handler-defined.
- [ ] R3: **Atomic append.** Writes use `open(..., 'a')` with
      `flush` + `fsync` on each line. No batching in v0.1;
      correctness over throughput at TB's current scale.
- [ ] R4: **Directory auto-created** on first write.

### Programmatic interface

- [ ] R5: **Module `backend/api/ot_audit.py`** exposes:
      ```python
      def start_entry(username: str, user_type: str, prompt: str) -> dict
          # returns a mutable dict that handlers populate as they go

      def add_classification(entry: dict, classification: dict) -> None
      def add_handler(entry: dict, handler: dict) -> None
      def add_response(entry: dict, response: str) -> None
      def finalize(entry: dict) -> None
          # computes total_latency_ms, writes to the appropriate month file
      ```
      Non-callers (e.g., TB-US-023 standalone classification
      calls that happen outside a routed request) can call
      `start_entry` + `add_classification` + `finalize`
      directly without the handler fields.

### Admin visibility

- [ ] R6: **`GET /ot/audit` endpoint.** Super-user-only.
      Query params:
      - `limit`: default 100, max 1000
      - `since`: ISO timestamp; default = 24 hours ago
      - `category`: optional filter
      - `username`: optional filter
      - `success`: optional boolean filter
      Response: array of entry objects, newest first.
- [ ] R7: **`GET /ot/audit/export` endpoint.** Super-user-only.
      Streams the raw JSONL of the current month (or all
      months with `?all=true`) as `Content-Type:
      application/jsonl`. Enables bulk export for v0.2
      classifier training.

### UI

- [ ] R8: **Minimal viewer in the admin modal.** Add an
      "OT Audit" tab to the existing user-management modal
      (TB-US-010) or create a sibling. The tab fetches
      `GET /ot/audit` and renders newest-first entries with
      the key fields visible (timestamp, category, handler,
      success); clicking a row expands to show the full
      prompt + response. Simple. No search / filter UI in
      v0.1 beyond what the backend endpoint supports via query
      params.
- [ ] R9: **Super-only visibility.** Non-super users do not
      see the OT Audit tab. Enforcement is backend (403 on
      the endpoint); frontend hide is a UX convenience.

### Operational

- [ ] R10: **Secrets scrubbing.** The audit log never writes
      the full session token, password hash, or any
      `/etc/default/*` env values. Prompt content and response
      content are logged verbatim; everything else is
      metadata.
- [ ] R11: **No regression on existing endpoints.** The audit
      module is additive. Existing endpoints (that have not
      been wired up through the OT router) do not log here.
- [ ] R12: **Cache-bust** on any UI files per TB-US-010's
      convention.

## Acceptance Criteria

### Storage + interface
- [ ] AC1: Processing a prompt through the OT router (once
      TB-US-028 lands) results in one line appended to
      `logs/ot_audit/<YYYY-MM>.jsonl` with all required
      fields populated.
- [ ] AC2: A manual call to `start_entry` →
      `add_classification` → `finalize` (no handler) writes
      a valid entry representing a standalone classification.
- [ ] AC3: Month rollover: on the first write of a new month,
      a new file is created at `logs/ot_audit/<new-YYYY-MM>.jsonl`
      without disturbing the previous month's file.
- [ ] AC4: JSONL validation: every line in a given file is
      independently parseable as JSON.

### Endpoints
- [ ] AC5: `GET /ot/audit?limit=10` as a super user returns
      the 10 most recent entries, newest first.
- [ ] AC6: `GET /ot/audit` as a non-super user returns HTTP
      403.
- [ ] AC7: `GET /ot/audit?category=quantitative&limit=50`
      returns up to 50 entries all with category
      "quantitative".
- [ ] AC8: `GET /ot/audit/export` returns the raw JSONL of
      the current month as a streaming response.

### UI
- [ ] AC9: Logging in as super and opening the admin modal
      shows an "OT Audit" tab (or equivalent). Clicking a
      row expands the full prompt/response.
- [ ] AC10: Logging in as training or chat user shows no
      OT Audit tab.

### No-regression
- [ ] AC11: TB-US-010's existing admin modal functionality
      still works (all five original ops).
- [ ] AC12: `GET /query` continues to work unchanged —
      pre-OT handling is unaffected until TB-US-028 wires
      `/query` into the OT router.

## Design Notes

- **Append-only JSONL is right at TB's scale.** No DB
  needed; filesystem is simple, grep-able, exportable. A
  future story could index older months into SQLite for
  faster querying; not needed now.
- **One file per month** avoids both the "tiny file per day"
  overhead and the "one giant file" tail problem. At TB's
  expected prompt volume (hundreds per month at v0.1
  verification scale), monthly files are < 100 MB.
- **Why mutable entry dict passed through handlers.** It is
  the simplest way to let the classifier, the handler, and
  the response-wrapping code each add their piece without
  threading args around. Finalize at the end.
- **Why log prompt + response in full.** The audit log is a
  training-data source. Partial logs are useless for v0.2.
  If PII is a concern in a future deployment, add a redaction
  pass as a separate story.
- **Export endpoint is critical.** The whole point of the
  audit log for v0.2 is to replay / fine-tune on it. Making
  export a first-class endpoint (R7) ensures that path
  exists from day one.
- **No per-user audit logs** (unlike ratings/directives).
  OT routing is a system-level concern; aggregating by month
  is more useful for retrospective analysis than
  per-user-per-day. If a specific user's history is wanted,
  the `?username=` filter covers it.
- **No audit log tombstones.** We never delete entries. If
  bad data (e.g., corrupted logs during a bug) needs to be
  excluded from v0.2 training, filter at export time.
- **TB-US-023's R8 interaction.** TB-US-023 says the
  classifier should "call the audit hook" even if the audit
  log doesn't yet exist. This story ships the hook. When
  TB-US-023 is implemented, the hook calls become real
  writes.

## Out of Scope

- **Audit log retention / archival policy.** Logs accumulate;
  storage review is a separate concern.
- **Search / full-text indexing.** `?category=` and `?username=`
  filters are enough for v0.1 browsing. Full search is a
  follow-up if the operator wants it.
- **Audit log dashboard / analytics.** Counts, charts, "most
  common failed classification" — separate story if useful.
- **PII redaction** of prompt / response content.
- **Multi-tenancy / per-deployment audit scoping.** TB is a
  single-deployment platform today.
- **Encryption at rest** on the JSONL files. OS-level disk
  encryption is the operator's responsibility.
- **Alerting on failed classifications or handler errors.**
  Separate observability story.
- **Trained-classifier-adapter training pipeline.** The
  audit log is the data source; using it to train is
  v0.2's concern.
- **Non-OT endpoint logging.** This story is specifically the
  OT audit log. Existing `/query` logs stay where they are.
- **Branding tweaks.**

## Related

- Parent: [TB-US-022](tb-us-022.md) — OT coordinator.
- Called by: [TB-US-023](tb-us-023.md) — classifier audits
  via this module.
- Called by: [TB-US-025](tb-us-025.md), [TB-US-026](tb-us-026.md),
  [TB-US-027](tb-us-027.md), [TB-US-028](tb-us-028.md) —
  handlers log their execution.
- Consumed by: [TB-US-029](tb-us-029.md) — verification
  example reads from the audit log to produce its report.
- Future: v0.2 classifier adapter training story will
  consume the exported JSONL.
- Admin UI pattern reference: [TB-US-010](tb-us-010.md).
- Context: `docs/ot-context-for-claude-code_1.md` lines
  109–112 (diagnostic clarity), 193 (audit log definition).
