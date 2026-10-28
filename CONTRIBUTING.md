# Contributing to TrainingBench

TrainingBench is **story-driven**: every change — from a one-line
tweak to a multi-week spike — starts as a story in `docs/user-stories/`
and gets tracked in [BACKLOG.md](BACKLOG.md). Those story files ARE
the project's development history; `git log` complements but doesn't
replace them.

## Project state

- **v0.1** is in active development as of 2026-10.
- The maintainer is Eversole Learning, LLC.
- The platform ships under [Apache 2.0](LICENSE).

## How work actually happens here

1. A need surfaces (operator ask, bug, design spike, polish idea).
2. A user story file is created at `docs/user-stories/tb-us-NNN.md`
   following the template at `docs/user-stories/template.md`. Status
   starts as **Proposed**.
3. BACKLOG.md gets a row for the new story.
4. When execution starts, status flips to **In Progress** + a
   notification fires to active operators.
5. When shipped, status flips to **Completed** + another notification
   fires. The story file stays — it becomes permanent documentation.
6. Umbrella stories (`TB-US-045` for small UI tweaks) collect
   related small changes without spawning dozens of story files.
7. Coordinator stories (e.g., `TB-US-064`) organize multi-sub-story
   arcs by linking to their sub-stories.

See the memory files captured during development (in operator's
`~/.claude/projects/.../memory/`) for the finer-grained conventions.

## For external contributors

**TrainingBench is not accepting external PRs at v0.1.** The platform
is being built out by its original maintainer; the architecture is
still shifting rapidly between stories, and merging drive-by
contributions would be disruptive.

If you want to engage:

- **Report issues** in the GitHub issue tracker (once v0.1 ships
  publicly). Flag which story is affected if you can.
- **Suggest stories** by filing an issue titled `[story proposal]
  ...`. Maintainer evaluates against the current arc and either drafts
  a story or defers.
- **Fork and build on it.** The Apache 2.0 license allows forking.
  Please attribute Eversole Learning in any downstream project.

Post-v0.1, this policy will be reviewed. If you want to track that
decision, follow the launch coordinator story at
[`docs/user-stories/tb-us-015.md`](docs/user-stories/tb-us-015.md).

## For the maintainer (process notes)

- Memory files captured in `~/.claude/projects/.../memory/` encode
  durable preferences about story structure, UI patterns, and the
  "experiments are design-gated" rule. These persist across Claude
  Code sessions.
- `backend/db/.secrets` and `logs/first-run-admin.txt` are deliberately
  gitignored. Never commit them.
- Backups: a periodic snapshot via `tar --exclude='.cache' --exclude='*/venv'`
  of `/home/jeversole/` + a sidecar of `/etc/{default,systemd,cloudflared,ssh}`
  is the current cold-restore story.
