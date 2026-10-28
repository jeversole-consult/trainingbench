# TB-US-022: Orthogonal Training (OT) — coordinator story

**Status**: In Progress
**Created**: 2026-10-14
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As TrainingBench's author, I want a single coordinator story
that tracks the arc of implementing Orthogonal Training (OT)
v0.1 — the four-category prompt classifier, the four handlers,
the OT-specific audit log, a working verification example, and
the operator workflow for building and deploying a custom
agent — so that the multi-story arc has a navigable parent and
I always know "where we are" on OT without scanning the whole
backlog.

## Background

Orthogonal Training is the framework in which TrainingBench's
training capability operates. OT recognizes that **routing
decisions and content quality are separately trainable
concerns**. Rather than training one model to handle everything,
OT decomposes the system into a **classifier** that routes
each prompt into one of four categories (qualitative,
quantitative, lookup, mixed) and a dedicated **handler** per
category. This gives diagnostic clarity, targeted improvement,
and category-specific accuracy that end-to-end LLM handling
cannot achieve.

The full OT concept is captured in `docs/ot-context-for-claude-code_1.md`.
This story is the parent of the v0.1 implementation arc. v0.2
(trained classifier adapter) and v0.3 (domain-specific
extensions) will have their own coordinators or roll up here
later; this story's scope is **v0.1 only**.

**Scope confirmed by operator on 2026-10-14:**

- Coordinator-up-front (yes — the arc is big enough to earn one)
- v0.1 scope only (rules + LLM-fallback classifier, basic
  handlers, naive mixed)
- Three-role rename (`chat` → `sales`) is deferred as a separate
  story, not blocking
- Verification by concrete example (TB-US-029) proves the
  arc, not by abstract test coverage

## Requirements

Each requirement is a **phase gate** that references one or
more sub-stories. This coordinator does not execute code; the
sub-stories do. This story completes when every phase gate is
satisfied.

- [ ] **R1: Four-category classifier (v0.1).**
  - [ ] [TB-US-023](tb-us-023.md) — rules-based classifier
    with LLM fallback for the four categories (qualitative,
    quantitative, lookup, mixed).
- [ ] **R2: Audit log in place.**
  - [ ] [TB-US-024](tb-us-024.md) — OT-specific audit log
    captures classification + handler + response for every
    prompt processed through the OT router. Admin-visible.
- [ ] **R3: Quantitative handler.**
  - [ ] [TB-US-025](tb-us-025.md) — calculator framework for
    deterministic computation; at least one concrete
    calculator wired up.
- [ ] **R4: Lookup handler.**
  - [ ] [TB-US-026](tb-us-026.md) — queries against
    structured sources (directory documents / structured
    JSON).
- [ ] **R5: Mixed handler (v0.1 naive).**
  - [ ] [TB-US-027](tb-us-027.md) — decomposes a mixed
    prompt into sub-prompts, routes each, composes results.
    v0.1 is naive by design; v0.2+ sophistication is
    deferred.
- [ ] **R6: Qualitative handler wired into OT routing.**
  - [ ] [TB-US-028](tb-us-028.md) — the existing RAG +
    content-adapter path is reachable through the OT router,
    not only through the pre-existing `/query` endpoint.
- [ ] **R7: Verification example runs green.**
  - [ ] [TB-US-029](tb-us-029.md) — a working math-domain
    example exercises all four handlers against a labeled
    query set; the audit log + verification report prove
    correct classification + correct handler per query.
- [ ] **R8: Deploy workflow documented.**
  - [ ] [TB-US-030](tb-us-030.md) — the operator can go from
    an empty TB install to a deployed Agent Release by
    following a single written walkthrough.

## Acceptance Criteria

Whole-arc end state, not any single sub-story.

- [ ] **AC1**: Every sub-story referenced above is
  `Status: Completed`.
- [ ] **AC2**: A prompt submitted through the OT router (as
  defined by TB-US-028) is classified, routed, handled, and
  logged — end-to-end — within one request lifecycle.
- [ ] **AC3**: The OT audit log (TB-US-024) shows a complete
  trail: timestamp, user, prompt, classification, handler,
  response, success. Verified by inspection against a sample
  of prompts covering all four categories.
- [ ] **AC4**: The verification example from TB-US-029
  produces a report (checked-in markdown + optionally a
  dumped JSONL of the audit log) demonstrating correct
  category classification and correct handler execution
  across a labeled query set.
- [ ] **AC5**: An outside collaborator can follow TB-US-030's
  walkthrough and produce an Agent Release without
  consulting the codebase. (Confirmed by Ted or Sam on a
  review pass, or by operator self-review.)
- [ ] **AC6**: v0.1 scope is honored — no v0.2 (trained
  classifier adapter) code paths exist in this coordinator's
  sub-stories. v0.2 is explicitly a future coordinator.

## Design Notes

- **Coordinator story, not an epic.** Per the
  `feedback_coordinator_not_epic` memory, OT is tracked as an
  ordinary coordinator story that links to sub-stories. No
  new artifact type is introduced.
- **Expected In Progress duration: weeks.** This coordinator
  will legitimately sit In Progress through most of the v0.1
  implementation. Per the `feedback_wip_with_claude_code`
  memory, that is honest state for an active arc.
- **Why v0.1 scope only.** The OT context doc separates v0.1
  (rules + LLM fallback), v0.2 (trained classifier adapter),
  and v0.3 (domain extensions). Rolling v0.2 into v0.1 stories
  would create stories that span go/no-go boundaries —
  `feedback_phase_split_stories` says split there.
- **How sub-stories cross-reference.** Each sub-story's
  Related section links back to this coordinator and to any
  sibling sub-stories it depends on. The dependency chain for
  v0.1 is roughly linear:
  `TB-US-024 (audit log) → TB-US-023 (classifier) → TB-US-025/026/027/028 (handlers, parallel) → TB-US-029 (example) → TB-US-030 (deploy workflow).`
  Multiple can be worked in parallel; this is a logical
  ordering, not a strict serial.
- **Role vocabulary mismatch flagged for later.** OT context
  doc names Sales / Training / Admin as the three roles; TB's
  current `users.db` has `super | chat | training`. v0.1
  stories operate on TB's current roles (`chat` plays "sales"
  effectively). A separate story later renames `chat` →
  `sales` across the schema and codebase.
- **Related docs that don't exist yet.** The OT context doc
  references `prompt-taxonomy.md`, `orthogonal-training.md`,
  `architecture.md`, `release-workflow.md`. These are new
  creation; TB-US-023 and TB-US-030 produce the ones that
  land naturally during v0.1. Any remaining get their own
  stories if wanted.
- **Component considerations from the OT context doc:**
  - Each handler is independent — v0.1 sub-stories can land in
    parallel.
  - The audit log (TB-US-024) is the data source for all
    future improvements including v0.2's trained classifier.
    Build it correctly early.
  - Diagnostic clarity (audit log + classification visibility)
    is the key value proposition — any v0.1 story that
    compromises it is wrong.

## Out of Scope

- **v0.2 — trained classifier adapter.** Will have its own
  coordinator (or roll up here if revisit shows a single
  coordinator remains manageable).
- **v0.3 — domain-specific taxonomy extensions.** Future.
- **Agent Release packaging and immutability mechanics**
  beyond what TB-US-030 touches to demonstrate the workflow.
  A full Agent Release ceremony (versioning, rollback,
  manifest validation) is a separate arc.
- **Three-role rename** (`chat` → `sales`). Separate story.
- **End-user UI changes** beyond what's needed to prove the
  OT router works. Full OT-aware UI is a later concern.
- **MFA / rate-limiting / IAM hardening** on OT endpoints.
  Inherited from the broader PM-US-004 arc.
- **Branding tweaks** (per the deferred-branding memory).
- **Projmgmt-side changes.** This is TB-side only.

## Related

Sub-stories (R1–R8):

- [TB-US-023](tb-us-023.md) — Four-category prompt
  classifier (v0.1)
- [TB-US-024](tb-us-024.md) — OT audit log
- [TB-US-025](tb-us-025.md) — Quantitative handler
- [TB-US-026](tb-us-026.md) — Lookup handler
- [TB-US-027](tb-us-027.md) — Mixed handler (v0.1 naive)
- [TB-US-028](tb-us-028.md) — Qualitative handler via OT
  routing
- [TB-US-029](tb-us-029.md) — Verification example (math
  domain)
- [TB-US-030](tb-us-030.md) — Build and deploy a custom
  agent (operator workflow)

Context:

- `docs/ot-context-for-claude-code_1.md` — the canonical OT
  concept document all sub-stories build against.
- [TB-US-015](tb-us-015.md) — Public launch coordinator (the
  pattern this coordinator follows).
- [TB-US-019](tb-us-019.md), [TB-US-020](tb-us-020.md),
  [TB-US-021](tb-us-021.md) — training-enhancement arc
  (parallel; non-blocking).
- `MEMORY.md → feedback_coordinator_not_epic` — governs the
  coordinator pattern.
- `MEMORY.md → feedback_phase_split_stories` — governs the
  v0.1 scope boundary.
