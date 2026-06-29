# TB-SPRINT-001: First-release install path

**Status**: Active
**Started**: 2026-06-06
**Closed**: —
**Goal**: Get TrainingBench to a documented, per-project install
path that can be verified end-to-end on a real machine, with the
training pipeline driveable from a CLI.

## Scope

| ID | Title | Status |
|---|---|---|
| [TB-US-001](../user-stories/tb-us-001.md) | CLI args, eval, and run tracking for GSM8K training pipeline | In Progress |
| [TB-US-002](../user-stories/tb-us-002.md) | First-release install path for TrainingBench | Proposed |

The two stories are tightly coupled. TB-US-002's verification step
(running the smoke train against a freshly installed environment)
also exercises TB-US-001's outstanding AC3 and AC4. Both close
together or neither does.

## Out of scope

Deliberately deferred to a later sprint:

- **TB-US-003** — Per-user random password salts. Security hardening;
  install path can ship with a documented `PASSWORD_SALT` env var for
  v0.1.
- **TB-US-004** — Training quickstart in README. Depends on TB-US-002
  landing first so the install path it points at exists.
- **TB-US-005** — Cut v0.1 release. License pick, version tag,
  changelog. Last in the sequence; nothing to release until the
  install path is verified.

Categories of work the sprint explicitly avoids:

- Windows or macOS install paths.
- Docker / container packaging.
- Multi-GPU or distributed training.
- Automated CI for the install path (manual verification is
  acceptable for v0.1).
- Agent construction itself (training adapters for a domain, loading
  RAG content, configuring the chat UI). The install enables this
  work but does not perform it.

## Notes

This is the first sprint exercising the structured methodology
(stories + sprints + git commits) on TrainingBench. Earlier work
that landed in master **before** stories existed — the catch-up
backport of feature code from former research branches, the
research-branch-references scrub of code and history, the
no-hardcoded-values audit, and the user-stories scaffolding itself
— is treated as platform groundwork. It is not retroactively
attached to a story or to this sprint.

The sprint's purpose is narrower than "ship v0.1." It is just the
install half: prove that a new user can stand the platform up on a
fresh machine and reach the point where they could begin building
an agent. Everything past that point is a downstream sprint.

## Review / Retrospective

(Filled in at sprint close.)
