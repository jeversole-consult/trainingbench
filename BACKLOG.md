# TrainingBench Backlog

Stories queued for the current sprint and upcoming work. Each story
file lives at `docs/user-stories/tb-us-NNN.md`; each sprint file lives
at `docs/sprints/tb-sprint-NNN.md`. This file is the index of what's
in flight, what's queued, and what's shipped.

For the story format, see `docs/user-stories/template.md`. For a
worked story example, see `docs/user-stories/example.md`. For the
sprint format, see `docs/sprints/template.md`.

## Active sprint

**Current**: none. [TB-SPRINT-001](docs/sprints/tb-sprint-001.md)
closed 2026-07-09; next sprint to be scoped.

## Queued

| ID | Title | Notes |
|---|---|---|
| TB-US-003 | Per-user random password salts | Security fix; replace global salt with per-user random salts and switch hash to bcrypt or argon2. |
| TB-US-004 | Training quickstart in README | Minimum docs a researcher needs to go from clone to "I trained an adapter." Depends on TB-US-002 landing first. |
| TB-US-005 | Cut v0.1 release | License already picked (Apache-2.0, TB-US-009); remaining scope is version tag and CHANGELOG entry. Blocked on the commit-message project-name scrub carried over from Sprint 1. Last in the sequence. |
| [TB-US-007](docs/user-stories/tb-us-007.md) | Prune unused dependencies from requirements.txt | Audit found ≥8 declared-but-not-imported packages (scrapy, selenium, matplotlib, seaborn, sklearn, rouge-score, bert-score, ipywidgets). Depends on TB-US-002 landing first so prune runs against a known-good install. |

## Shipped

Sprint 1 (2026-06-06 → 2026-07-09):

| ID | Title | Closed in |
|---|---|---|
| [TB-US-001](docs/user-stories/tb-us-001.md) | CLI args, eval, and run tracking for GSM8K training pipeline | TB-SPRINT-001 |
| [TB-US-002](docs/user-stories/tb-us-002.md) | First-release install path for TrainingBench | TB-SPRINT-001 |
| [TB-US-009](docs/user-stories/tb-us-009.md) | License TrainingBench under Apache-2.0 | TB-SPRINT-001 |
