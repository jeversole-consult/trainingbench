# TB-US-021: Add directive-prompt mode for direct SME training-example entry

**Status**: In Progress
**Created**: 2026-10-13
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a Subject Matter Expert using TrainingBench, I want a
**directive-prompt mode** — a way to enter a prompt + correct
answer pair directly into the training-example pipeline
without first going through the RAG query step — so that when
I already know the correct answer and I'm teaching the system
a fact rather than correcting its guess, I can do that in one
step instead of two.

## Background

TB's existing SME workflow (documented in TB-US-020) centers on
a **query-then-rate** loop:

1. SME asks a question via `POST /query`
2. The RAG generates a response
3. SME rates it (`acceptable` or `needs_improvement` + `feedback`)
4. Rating accumulates in `logs/ratings/ratings_<username>.jsonl`
5. `POST /training/sets/from-ratings` turns ratings into a
   training set

This flow works well when the SME wants to **vet or correct
the RAG's answers**. But it has one friction point: when the
SME **already knows the correct answer** and wants to insert
it as a training example without first making the RAG guess
and then correcting it, there is no path. The operator's
2026-10-13 framing: *"an SME can enter a directive prompt,
i.e. this is how this works directive, I'm not asking you,
I'm telling you because I know and you don't."*

Neither stalite3 nor TB has this mode today (verified 2026-10-13
via endpoint audit). It is a legitimate new feature. The core
insight: a directive is a **unary insertion into the training
pipeline** — one Q + one A, no RAG involvement.

## Requirements

### Backend

- [ ] R1: **New endpoint: `POST /training/directive`**. Request
      body:
      ```python
      class DirectiveRequest(BaseModel):
          prompt: str       # The SME's question or instruction
          answer: str       # The correct answer
          tags: Optional[List[str]] = None   # Free-form tags
          model_context: Optional[str] = None  # Which model's
                                               # training this is
                                               # intended for
      ```
      Response: `{"success": true, "entry_id": "<uuid>"}`.
- [ ] R2: **Role gating.** Only `training` users can call this
      endpoint. Non-training users receive HTTP 403.
- [ ] R3: **Storage.** Entries are appended to a per-user
      JSONL log at `logs/directives/directives_<username>.jsonl`.
      Each entry is `{entry_id, timestamp, username, prompt,
      answer, tags, model_context, source: "directive"}`. The
      `source` field distinguishes directive entries from
      regular rating entries when they are later aggregated.
- [ ] R4: **No RAG touch.** The handler does NOT call the RAG
      system, does NOT consult the query log, and does NOT
      write to the ratings log. Directives are a separate
      stream.
- [ ] R5: **Pipeline integration.** Extend
      `POST /training/sets/from-ratings` (or add a new
      `POST /training/sets/from-directives`) to also source
      from the directives log. Implementer's call during
      execution; record the decision in Completion Notes.
      Minimum: directives must be reachable by the training-
      set-building infrastructure. The directive entries
      format into Alpaca shape as `{"instruction": prompt,
      "input": "", "output": answer, "source": "directive",
      ...}`.
- [ ] R6: **Idempotency guard.** If the same prompt + answer
      pair is submitted twice by the same user within a short
      window (e.g., 60 seconds), the second call returns a
      409 Conflict with a reference to the first entry's
      `entry_id`. Prevents accidental double-insertion from
      double-click or network retry.

### UI

- [ ] R7: **Entry point from the chat/query UI.** On the Chat
      tab (or equivalent after TB-US-018 lands), add a
      "Teach the system" (or "Add directive") action — a
      prominent-but-not-dominant button that opens a form
      with two text areas: Prompt and Answer. The form submits
      to `POST /training/directive`. Hidden for non-training
      users.
- [ ] R8: **Confirmation and feedback.** On successful submit,
      the UI shows a toast / inline confirmation ("Directive
      entry recorded") with the `entry_id`. On error (403 or
      409 or 500), the UI surfaces a clear message.
- [ ] R9: **Tagging in the UI.** The form may optionally
      include a tags input (comma-separated) — useful for
      categorizing directives by domain (e.g., "medical",
      "legal"). Nice-to-have; defer to implementer judgment.
- [ ] R10: **Coordination with TB-US-018.** The UI entry
      point lives inside the Chat tab's content, which will
      move into the collapsible left-nav drawer under
      TB-US-018. The directive form is part of the Chat tab
      content, not the drawer; TB-US-018's drawer navigation
      and this story's content additions are independent.

### Operational

- [ ] R11: **Role check for pipeline inclusion.** When
      `/training/sets/from-ratings` (or the extended endpoint)
      pulls from the directives log, directives from
      deactivated users are **excluded**. Matches the pattern
      TB-US-011 established for training-set ownership.
- [ ] R12: **No regression on existing SME flow.** The
      query-rate-from-ratings loop continues to work
      unchanged. Directives are additive.
- [ ] R13: **Cache-bust** on UI files per TB-US-010's
      convention.
- [ ] R14: **No schema changes.** All new state is in flat
      JSONL files on disk, matching the pattern used by the
      existing ratings and query logs.

## Acceptance Criteria

### Core directive flow
- [ ] AC1: A training user calling
      `POST /training/directive` with a valid payload receives
      a 200 response with `{success: true, entry_id}`. The
      entry appears in
      `logs/directives/directives_<username>.jsonl`.
- [ ] AC2: A non-training user calling the endpoint receives
      HTTP 403.
- [ ] AC3: Submitting the same prompt+answer twice within 60
      seconds returns 409 with a reference to the first
      `entry_id` (idempotency guard, R6).
- [ ] AC4: The handler does not read from or write to the
      query log or ratings log — verified by comparing
      filesystem state before/after a directive submission.

### Pipeline integration
- [ ] AC5: After submitting 3 directive entries,
      `POST /training/sets/from-ratings` (or the equivalent
      path chosen per R5) includes those 3 entries in the
      resulting training set. The output rows carry a
      `source: "directive"` marker so the training set
      preserves the provenance of each example.
- [ ] AC6: A directive entry from a deactivated user is
      skipped by the training-set builder (R11).

### UI
- [ ] AC7: Logging in as a training user and navigating to
      the Chat tab shows the "Teach the system" / "Add
      directive" action.
- [ ] AC8: Submitting the directive form with valid data
      shows a success confirmation and the entry appears in
      the backing log.
- [ ] AC9: The action is hidden for non-training users (and
      calling the endpoint directly still 403s — the UI hide
      is a convenience, the backend is the enforcement).

### No regression
- [ ] AC10: The existing query-rate flow continues to work
      end-to-end (query → rate acceptable → from-ratings
      includes the entry).
- [ ] AC11: `git diff backend/api/user_manager.py` is clean
      (no changes to user management for this story).
- [ ] AC12: Rate limiting on `/query` is unchanged.

## Design Notes

- **Why a separate log file.** Directives are semantically
  distinct from ratings — they have no RAG context, no
  message_id correlating back to a chat exchange. Mixing them
  into `ratings_<username>.jsonl` would require awkward
  nullable fields and would mask the provenance distinction
  that matters for training-data lineage ("was this a
  correction or a direct insertion?"). A separate stream is
  cleaner.
- **Why not just insert directly into a training set.** An
  alternative design is to skip the directives log entirely
  and insert into a training set directly on
  `/training/directive`. Rejected because:
  - The current pattern is "accumulate entries, batch into
    training set" — matches ratings and query log flow
  - The SME doesn't know yet which training set a directive
    belongs to; the from-ratings step is where that choice
    happens
  - The directives log preserves the raw record even if the
    SME later changes their mind about which set to build
- **Why the idempotency guard (R6).** SMEs will double-click
  the Submit button. The guard prevents accidental duplicates
  from polluting the training set. A 60-second window is
  generous enough to cover network retries and double-clicks,
  tight enough that intentional re-entry (updated phrasing,
  for example) still works.
- **Tags (R9) are useful, not required.** For domain
  categorization (medical / legal / math / etc. — matching
  TB's benchmark domains), tags help filter during from-
  ratings. If the implementer leaves tags out of v1, follow
  up when a tag-filter use case emerges.
- **"Model context" field (R1).** Optional field for when a
  directive is specifically about teaching a particular model
  variant (e.g., "this instruction is for llama3.1 fine-
  tuning only"). Many directives will be model-agnostic;
  the field defaults to null.
- **Interaction with TB-US-019's session workflow.**
  Directives entered within an active training session
  should ideally associate with that session. Simplest
  v1 approach: don't associate — directives are stand-alone
  log entries. If the operator wants session-attribution for
  directives later, that's a follow-up.
- **No markdown processing on prompt / answer.** Store the
  raw text. If a future training-set format requires
  stripping or converting markdown, that happens at the
  training-set-build step, not here.
- **Rate limiting on `/training/directive`.** Not applied in
  v1. Training users are trusted and small in number. If
  automated-insertion abuse becomes a concern, add
  slowapi-style rate limiting consistent with the `/query`
  endpoint's 20/minute.

## Out of Scope

- **Editing or deleting a submitted directive.** v1 is append-
  only. If a mistake is entered, a new entry can override
  (effectively — in the training set build step, newer
  entries can supersede older ones). Edit / delete UI is a
  follow-up if needed.
- **Bulk directive import** (upload a JSONL file of directives
  at once). Separate story. For now, directives are entered
  one at a time via the UI.
- **Associating directives with a specific training session**
  (TB-US-019). Flagged in Design Notes; not implemented
  here.
- **Full audit log of directive entries** (who entered what,
  when, with what IP). The per-user JSONL log already
  provides most of this at a basic level. A richer audit
  story would wrap this + ratings + sessions into a unified
  admin viewer — separate from this story.
- **A directive-specific analytics UI** (e.g., "how many
  directives has Ted submitted this week"). Follow-up if
  wanted.
- **Model-training integration beyond from-ratings.** The
  pipeline stops at training-set construction. The downstream
  training run is unchanged.
- **Multi-worker file-locking** on the directives log.
  Current TB execution is single-process; flagged for a
  future hardening story.
- **Branding tweaks** (per the deferred-branding memory).

## Related

- [TB-US-011](tb-us-011.md) — Shipped ownership-based access
  for training-role users. R11 role-check pattern inherited.
- [TB-US-019](tb-us-019.md) — Session workflow + export (In
  Progress). Directives may optionally associate with
  sessions in a future story; not in this story's scope.
- [TB-US-020](tb-us-020.md) — SME workflow documentation (In
  Progress). Should be updated post-this-story's-execution
  to describe the directive mode (via a doc-refresh follow-
  up, not inside TB-US-020).
- [TB-US-018](tb-us-018.md) — UI refresh (In Progress). The
  directive-entry form lives inside the Chat tab content;
  TB-US-018's drawer navigation and this story's content
  additions are independent (R10).
- [TB-US-010](tb-us-010.md) — Shared JS include pattern for
  role-gated UI; applicable for R7's "hide for non-training"
  behavior.
- `backend/api/main.py` — new endpoint lands here; new
  `DirectiveRequest` Pydantic model near existing training
  domain models.
- `static/index.html` (Chat tab content) — new form added
  here.
- `logs/directives/directives_<username>.jsonl` — new log
  file path.
- `MEMORY.md → workflow_projmgmt_pilot` — TB-side work,
  projmgmt pilot rule does not apply.
