# TB-SPRINT-001: First-release install path

**Status**: Closed
**Started**: 2026-06-06
**Closed**: 2026-07-09
**Goal**: Get TrainingBench to a documented, per-project install
path that can be verified end-to-end on a real machine, with the
training pipeline driveable from a CLI.

## Scope

| ID | Title | Status |
|---|---|---|
| [TB-US-001](../user-stories/tb-us-001.md) | CLI args, eval, and run tracking for GSM8K training pipeline | Completed |
| [TB-US-002](../user-stories/tb-us-002.md) | First-release install path for TrainingBench | Completed |
| [TB-US-009](../user-stories/tb-us-009.md) | License TrainingBench under Apache-2.0 | Completed |

TB-US-001 and TB-US-002 are tightly coupled: TB-US-002's verification
step (running the smoke train against a freshly installed environment)
also exercises TB-US-001's outstanding AC3 and AC4. Both close together
or neither does.

TB-US-009 was pulled forward from TB-US-005 because the OSS license is
a prerequisite for any public-repo push. It closes independently of
the other two.

## Out of scope

Deliberately deferred to a later sprint:

- **TB-US-003** — Per-user random password salts. Security hardening;
  install path can ship with a documented `PASSWORD_SALT` env var for
  v0.1.
- **TB-US-004** — Training quickstart in README. Depends on TB-US-002
  landing first so the install path it points at exists.
- **TB-US-005** — Cut v0.1 release. Version tag and CHANGELOG entry
  only, now that the license pick has been pulled forward into
  TB-US-009. Last in the sequence; nothing to release until the
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

### What worked

- **Sprint duration honesty.** The sprint ran ~5 weeks, longer than
  originally imagined but shorter than "until v0.1." Framing it as
  "the install half only" kept scope from ballooning as we hit
  install-path surprises.
- **Peer install as verification, not staging.** Standing up an
  actual install from the documented instructions surfaced six
  concrete surprises (Python 3.13 warning was too strict, cu130
  vs cu128 wheels, missing tensorboard, /settings/mode 404, admin
  email placeholder rules, port-conflict handling). All six fed
  back into the install doc in one commit instead of drifting.
- **Pulling TB-US-009 forward** from TB-US-005 was the right call.
  The license commit is a prerequisite for any public push, and
  bundling it with the version-tag cut would have blocked TB-US-005
  on other work.
- **Story-first + tick-boxes** kept acceptance honest. AC3/AC4 on
  TB-US-001 stayed unchecked for weeks even after the code landed,
  which correctly flagged that the smoke path wasn't actually
  verified yet.
- **No-project-references discipline** in commit messages (mostly)
  held. See carry-over below for the one gap.

### What didn't

- **AC3 gap on TB-US-001 wasn't caught at story-writing time.** The
  suggested smoke command didn't include `--eval-steps`, but the
  code required it for any eval to run. This was found during peer
  verification, not story review. Cost: an extra fix commit
  (cadf907) after the story was already "implemented."
- **A single peer-install verification is thinner evidence than the
  story implied.** AC3 says "at least one real or virtual machine"
  which we satisfied, but the original plan was two peer installs
  (see carry-over). One is enough to close, honestly, but two would
  have exercised install-instruction ambiguity harder.
- **Two commit messages leaked a downstream-project name** (commits
  1601885 and 3a98382). This was flagged mid-sprint but the
  msg-filter scrub was not executed — carry-over into TB-US-005 so
  the public push cannot happen with those messages intact.
- **A long-running GPU-hogging process** on the shared host kept
  needing to be evicted for each runtime verification. Not a
  sprint-scope thing to fix, but noting the friction.

### Carry-over

- **Second peer install.** Deferred; not a Sprint 1 blocker. Not
  tied to a new story yet — if the first peer install proves to be
  stable long-term, a second may not be needed for v0.1. Revisit
  before cutting v0.1 (TB-US-005).
- **Scrub downstream-project name leaks from commit messages
  1601885 and 3a98382.** Must happen before the first public push.
  Track as a prerequisite for TB-US-005.
- **The live deployment still hits the /settings/mode 404** until
  the running backend is restarted against `master`. Deploy step,
  not a code fix. Bundle with the next master → live update.
- **Cosmetic UI change** discussed mid-sprint (moving DB stats from
  the top of the admin page to per-database controls in Manage
  Databases). Not yet a story; if picked up, will be TB-US-008 in
  a follow-on sprint.
