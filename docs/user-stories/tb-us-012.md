# TB-US-012: Spike — GitHub release mechanics for TrainingBench

**Status**: In Progress
**Created**: 2026-09-10
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As TrainingBench's author, I want a written playbook covering the
mechanics of taking TB from a private local repo to a public
GitHub repo, so that the actual v0.1 release (TB-US-005) executes
against a known plan rather than a series of improvised choices
made under time pressure.

## Background

TrainingBench has been developed as a private local project.
TB-US-005 ("Cut v0.1 release") is queued and reads its scope as
"version tag and CHANGELOG entry" — but that assumes the release
mechanics are already figured out, which they aren't. This spike
converts the unknown-unknowns of "how do we actually put this on
GitHub" into a written playbook.

Deliberately narrow: this spike is only the **mechanics** of the
release. Two adjacent concerns are handled by their own spikes:

- **IP and copyright transfer** — Jesse (individual) to Eversole
  Learning, LLC — is TB-US-013's problem. That decision drives
  the LICENSE file authorship line that this spike would
  otherwise have to guess at.
- **OSS compliance and community norms** — CONTRIBUTING, DCO vs
  CLA, license compatibility with dependencies and Llama weights
  — is TB-US-014's problem.

This spike, TB-US-013, and TB-US-014 are all inputs to TB-US-005.

## Requirements

Deliverable-in-writing. Each requirement is a decision the
playbook must resolve, not a code change.

- [ ] R1: **Repo home decision.** Personal GitHub account
      (`github.com/jeversole/trainingbench` or similar) vs a new
      organization (`github.com/eversole-learning/trainingbench`).
      Depends on TB-US-013 outcome for the copyright holder.
- [ ] R2: **Git history strategy.** Squash to a clean initial
      public commit vs preserve full history from the private
      repo. Trade off "clean provenance-free start" vs
      "authorship record intact." Note any commits containing
      information that should not be public regardless of choice.
- [ ] R3: **`.gitignore` audit.** Enumerate what's already
      ignored, what needs to be added before the first public
      commit (venv, `__pycache__/`, `data/`, model weights,
      `.env`, notebooks with output cells, logs). Produce a
      before/after list.
- [ ] R4: **Secrets scan.** Pick a tool (gitleaks, trufflehog,
      git-secrets, GitHub push-protection) and document the
      pre-push procedure. If findings surface historical secrets,
      document the mitigation (rotate + BFG history rewrite vs
      squash-to-fresh-history per R2).
- [ ] R5: **CI decision for v0.1.** GitHub Actions or nothing at
      first? If yes, which jobs (lint, unit tests, security scan,
      docs build)? Keep the initial matrix minimal.
- [ ] R6: **Release / tag mechanics.** How SemVer tags map to
      GitHub Releases, where CHANGELOG lives and how it's
      maintained, how the first tag (`v0.1.0`) gets cut and
      published.
- [ ] R7: **Repo hygiene defaults.** Branch-protection rules on
      `main` (require PR, require CI green, require sign-off?),
      default branch name, merge strategy (squash vs merge vs
      rebase), issue/PR templates.
- [ ] R8: **Deliverable.** Playbook lands as
      `docs/release/github-release-playbook.md`. Every R1–R7
      decision has a concrete answer (not TBD).

## Acceptance Criteria

- [ ] AC1: `docs/release/github-release-playbook.md` exists.
- [ ] AC2: Every requirement above is answered with a specific
      decision, not left as a range of options.
- [ ] AC3: The playbook, TB-US-013's IP brief, and TB-US-014's
      compliance checklist are together sufficient input for
      TB-US-005 to execute without further research.

## Design Notes

- **Spike, not implementation.** No `git push` happens here.
  The output is a written plan that a follow-up story (or a
  re-scoped TB-US-005) actually executes.
- **Sequencing hint.** R1 (repo home) waits on TB-US-013's
  copyright-holder recommendation. Most other requirements can
  be drafted independently.
- **Squash vs preserve history (R2).** If TB's history contains
  secrets, exploratory dead ends, or personally-identifying
  content that shouldn't be public, squash is the safer path.
  If history is clean, preserving it gives future contributors
  useful provenance.

## Out of Scope

- Actually creating the GitHub repo or pushing code. Belongs to
  the story that executes the playbook (likely a re-scoped
  TB-US-005).
- IP / copyright decisions (TB-US-013).
- License selection or OSS compliance (TB-US-014).
- Writing the CONTRIBUTING, README, or other content files
  themselves — the playbook may reference where they should live
  but doesn't produce them.
- Post-release community management (issue triage cadence, PR
  review SLAs, etc.).

## Related

- Other stories:
  - TB-US-005 — Cut v0.1 release. Downstream; this spike's
    output is required input.
  - TB-US-013 — IP and copyright transfer spike. R1 blocks on
    its recommendation.
  - TB-US-014 — GitHub compliance / OSS norms spike. Parallel.
  - TB-US-009 — Apache-2.0 licensing (already Shipped). LICENSE
    file exists; this spike only decides the authorship line and
    where the file lives in the public repo.
- PRs / commits: —
- External: GitHub docs on repository setup and release
  management.
