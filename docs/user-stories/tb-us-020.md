# TB-US-020: Document the SME training workflow in TrainingBench

**Status**: In Progress
**Created**: 2026-10-13
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

**Deliverable**: docs/training/sme-workflow.md

## Story

As the operator and future training users of TrainingBench, I
want a clear written walkthrough of how a Subject Matter Expert
(SME) interacts with TB to produce fine-tuning training data —
starting from login, through querying and rating, into
training-set construction, through a training run, to a
deployed adapter — so that collaborators (Ted, Sam, future
hires) can understand the end-to-end flow without reverse-
engineering it from the code, and so that the arc of training-
capability enhancements (TB-US-019+) has a shared reference for
what the current baseline is.

## Background

TB has a complete SME-interactive-training surface today, but
there is no written walkthrough that assembles it into a
coherent workflow. The pieces exist in isolation across:

- `POST /query` — the RAG entry point
- `POST /rate-response` — SME evaluation of RAG answers
- `logs/ratings/ratings_<username>.jsonl` — per-user ratings log
- `logs/queries/*` — the RAG query log
- `POST /training/sets/from-ratings` — convert ratings to a
  training set
- `POST /training/sets/from-query-log` — convert queries to a
  training set
- `POST /training/runs` + checkpoints + metrics endpoints — the
  actual training execution
- The `training` user_type gating on key endpoints

A new collaborator — e.g., Ted or Sam, once TB-US-017 ships and
their training-role accounts can be created — currently has to
piece this together from the codebase. This story closes that
gap with a concrete doc.

This is the first of several anticipated training-capability
enhancements (per operator framing on 2026-10-13: "there will be
many enhancements to the training capability of training
bench"). Future enhancements include:

- **TB-US-019** (In Progress) — session workflow + training set
  export
- **TB-US-021** (also drafted 2026-10-13) — directive-prompt
  mode: direct SME entry of a prompt + correct answer, bypassing
  the RAG query step
- Further enhancements to be identified

The documentation produced by this story describes the **current
baseline**, with explicit notes about what TB-US-019 and
TB-US-021 will add once shipped.

## Requirements

- [ ] R1: **Deliverable: `docs/training/sme-workflow.md`.** A
      single markdown doc, structured as a walkthrough. Target
      length: moderate — long enough to be a real explanation
      (several thousand words), short enough that a reader can
      finish it in one sitting.
- [ ] R2: **Section: "The SME's role."** What a Subject Matter
      Expert is in TB's model, why their input matters (ground
      truth for fine-tuning), what access and privileges they
      have (`training` user_type, ownership-based training-set
      access per TB-US-011), and how they differ from `super`
      (admin) and `chat` (query-only) users.
- [ ] R3: **Section: "Step-by-step workflow."** A linear
      walkthrough:
      1. Login (gate passphrase + credentials)
      2. Navigate to the chat/query interface
      3. Enter a prompt via `POST /query`
      4. Receive the RAG-generated response
      5. Evaluate the response — `POST /rate-response` with
         rating ∈ {`acceptable`, `needs_improvement`}
         - If `acceptable`: Q and A are logged as a positive
           example (A becomes the training "output")
         - If `needs_improvement`: `feedback` field required;
           the SME provides the correct answer; Q + feedback
           becomes the training example
      6. Repeat 3–5 across many prompts
      7. Convert accumulated ratings into a training set via
         `POST /training/sets/from-ratings`
      8. Review the resulting training set in the Training Sets
         UI; edit or clone as needed
      9. Trigger a training run via `POST /training/runs`
      10. Monitor the run (metrics, logs, checkpoints endpoints)
      11. On completion, use the resulting adapter via
          `/query?model=peft:<adapter-name>`
- [ ] R4: **Section: "Correction-via-feedback: the hidden
      teaching mechanism."** Explain explicitly that the
      `needs_improvement` + `feedback` combination is a
      correction mechanism, not just a complaint — the
      feedback text becomes the "correct answer" in the
      training example. Many SMEs may not realize this
      without being told.
- [ ] R5: **Section: "Where the data lives."** Enumerate the
      filesystem artifacts: query log location, ratings log
      location, training sets registry, training runs,
      checkpoints directory, adapter directory. One paragraph
      per artifact; path-and-purpose only (not implementation
      detail).
- [ ] R6: **Section: "Role gating."** Which endpoints require
      `training` role, which require `super`, which are open to
      any authenticated user. A table is appropriate.
- [ ] R7: **Section: "Anticipated enhancements."** Short notes
      on what the arc will add:
      - TB-US-019: session workflow (interactive curation
        tracking) and training set export (download as JSONL
        in Alpaca / ChatML / raw formats)
      - TB-US-021: directive-prompt mode (direct Q+A entry,
        bypassing the RAG step for cases where the SME wants to
        teach the system a fact rather than correct an answer)
      - Flagged: more enhancements anticipated; this section
        gets updated as stories ship.
- [ ] R8: **Section: "Open issues and gotchas."** Known
      friction points the SME should be aware of:
      - Current weak password hashing (SHA-256 + global salt;
        TB-US-003 will migrate)
      - Single-user training-session file writes are safe only
        because TB runs single-process (flagged in TB-US-019)
      - Each adapter load takes ~60 seconds (per existing code
        comments)
      - Rate limiting on `/query` (20/minute)
- [ ] R9: **Section: "Glossary."** Short definitions for
      jargon that appears in the doc:
      - **SME** (Subject Matter Expert)
      - **PEFT**, **LoRA**, **QLoRA**
      - **Training set** vs **training run** vs **adapter**
      - **Alpaca format**, **ChatML format**
      - **Query log**, **ratings log**
- [ ] R10: **Verification via a fresh read.** Verifier (the
      operator or another reader) reads the doc front-to-back
      and can describe the workflow without rereferring to
      the codebase.

## Acceptance Criteria

- [ ] AC1: `docs/training/sme-workflow.md` exists.
- [ ] AC2: Each of the 8 sections required (R2–R9) is present
      with substantive content (not placeholders).
- [ ] AC3: The step-by-step workflow (R3) is accurate against
      the current codebase — every endpoint, log location, and
      role requirement mentioned is correct as of the doc's
      Last-updated date.
- [ ] AC4: The "Anticipated enhancements" section (R7) lists
      TB-US-019 and TB-US-021 and notes they are In Progress.
- [ ] AC5: The glossary (R9) covers every acronym and jargon
      term that appears in the body.
- [ ] AC6: A reader can navigate from "I'm a new training user,
      what do I do?" to the first query action without needing
      to open the codebase or ask the operator.

## Design Notes

- **Pure documentation story.** No code changes. No endpoint
  additions, no schema changes, no UI touches. The deliverable
  is a markdown file.
- **Audience.** The doc targets a reader who is somewhat
  technically literate but has not read TB's codebase.
  Collaborators like Ted and Sam are the primary audience; the
  operator is the secondary reviewer.
- **"The hidden teaching mechanism" matters.** Many SMEs will
  not realize that typing a correction into the `feedback` box
  during a `needs_improvement` rating actually turns into
  training data. Calling this out explicitly (R4) is a
  value-add; without it, SMEs may skip the feedback field or
  use it for complaints instead of corrections.
- **Snapshot vs living doc.** This story produces a snapshot.
  The "Anticipated enhancements" section acknowledges that
  future stories will update the doc. A separate story
  (post-TB-US-019 or post-TB-US-021 execution) refreshes the
  doc to describe the newly-shipped flows.
- **Tone.** Prefer plain prose over imperative lists where
  possible. The SME role is a human role; the doc should feel
  like onboarding, not an API reference.
- **Include a diagram if useful.** A simple ASCII flow
  (`login → query → rate → from-ratings → run → adapter`) at
  the top of the step-by-step section helps readers orient.
  Not required.
- **No code snippets beyond endpoint names.** The doc should
  describe *what happens* at each step, not teach the reader
  the HTTP shape of each call. A separate API reference (if
  ever wanted) would be a different doc.

## Out of Scope

- Any **new feature** for the SME workflow. Documenting the
  existing capability only.
- **Updating the doc after TB-US-019 or TB-US-021 ships.**
  Separate follow-up stories update the doc. This story
  captures the current baseline.
- **Marketing-facing copy** about TB's training capability.
  This doc is operator-and-collaborator-facing.
- **A standalone operator runbook** (how to deploy TB, how to
  troubleshoot a stuck training run). Separate concern.
- **UI documentation** (how to click specific buttons). The
  doc describes the workflow conceptually; where UI exists,
  it's named (e.g., "the Chat tab"), but screenshot-level
  detail is out of scope.
- **Branding-adjacent copy** (per the deferred-branding
  memory on the projmgmt side; same spirit applies).
- **Translation** to other languages.
- **Replacing TB's existing README or INSTALL docs.** This
  is a new doc at a dedicated path, not a rewrite.

## Related

- [TB-US-011](tb-us-011.md) — Ownership-based training-set
  access for training-role users (Shipped). Reference for R2.
- [TB-US-017](tb-us-017.md) — User management v2 (In
  Progress). Reference for how a training user is created
  once that story ships.
- [TB-US-019](tb-us-019.md) — Session workflow + export (In
  Progress). Reference in R7 as an anticipated enhancement;
  doc may be refreshed post-execution.
- [TB-US-021](tb-us-021.md) — Directive-prompt mode (In
  Progress). Also referenced in R7.
- `backend/api/main.py` — the endpoints referenced in R3.
- `docs/training/sme-workflow.md` — the deliverable.
- `MEMORY.md → workflow_projmgmt_pilot` — reminder that this
  is TB-side work; projmgmt pilot rule does not apply.
