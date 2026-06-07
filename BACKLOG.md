# TrainingBench Backlog

Stories queued for the current sprint and upcoming work. Each story
file lives at `docs/user-stories/tb-us-NNN.md`; this file is an index
of what's in flight, what's queued, and what's shipped.

For the format, see `docs/user-stories/template.md`. For a worked
example, see `docs/user-stories/example.md`.

## Active sprint

| ID | Title | Status |
|---|---|---|
| [TB-US-001](docs/user-stories/tb-us-001.md) | CLI args, eval, and run tracking for GSM8K training pipeline | In Progress |
| [TB-US-002](docs/user-stories/tb-us-002.md) | First-release install path for TrainingBench | Proposed |

## Queued

| ID | Title | Notes |
|---|---|---|
| TB-US-003 | Per-user random password salts | Security fix; replace global salt with per-user random salts and switch hash to bcrypt or argon2. |
| TB-US-004 | Training quickstart in README | Minimum docs a researcher needs to go from clone to "I trained an adapter." Depends on TB-US-002 landing first. |
| TB-US-005 | Cut v0.1 release | License pick, version tag, changelog entry. Last in the sequence. |

## Shipped

(none yet; v0.1 will populate this section)
