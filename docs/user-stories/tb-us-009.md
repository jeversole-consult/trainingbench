# TB-US-009: License TrainingBench under Apache-2.0

**Status**: Completed
**Created**: 2026-07-06
**Author**: Jesse Eversole
**Commit hash(es)**: b22c381

## Story

As a user or downstream developer considering TrainingBench for their
own work, I want a clearly documented open-source license at the root
of the repository, so that I can tell at a glance whether I'm allowed
to use, modify, and redistribute the code, and under what terms.

## Background

Prior to this story, the repository had no `LICENSE` file and the
`README.md` `## License` section said "License TBD based on dataset
requirements and publication plans." That is a blocker for any public
push: GitHub treats a repo without a license as all-rights-reserved,
and downstream users have no legal basis to use, modify, or
redistribute the code.

Apache-2.0 is the chosen license because TrainingBench is a research
platform meant to be forked and extended: a permissive license lowers
the barrier for downstream adoption, and Apache-2.0's explicit patent
grant is meaningful for a project that may eventually integrate model
weights, training techniques, or algorithms that touch patent-covered
territory. MIT was considered and rejected because it lacks the
patent grant; AGPL-3.0 was considered and rejected because it would
force downstream network services to publish their modifications,
which conflicts with the "platform for others to build on" intent.

Two existing license references in the codebase are for **datasets or
model artifacts**, not for the TrainingBench code itself:

- `README.md` line 62: `License: CC-BY 4.0` — refers to the CUAD
  legal-contract dataset from Hugging Face.
- `README.md` line 102 and `datasets/math/README.md` line 13: MIT —
  refers to the GSM8K math dataset from Hugging Face.

The story must not delete or contradict these references; it must
disambiguate them so a reader can see they describe upstream data,
not the platform.

TB-US-005 in the backlog reserves "license pick" as part of the v0.1
release cut. This story pulls that piece forward independently because
the OSS license is a prerequisite for the peer-install verification
already in flight, not a release-cut concern.

## Requirements

- [x] R1: An `Apache-2.0` `LICENSE` file exists at the repository
      root, containing the canonical Apache-2.0 license text from
      `https://www.apache.org/licenses/LICENSE-2.0.txt`, unmodified.
- [x] R2: A `NOTICE` file exists at the repository root, naming the
      project, the copyright holder, and the year, and pointing at
      `LICENSE` for the full text. The NOTICE also explains that
      third-party dependencies installed via pip carry their own
      licenses (this project does not bundle their source in-tree).
- [x] R3: `README.md` `## License` section is updated to name
      Apache-2.0 explicitly, link to `LICENSE`, and remove the "TBD"
      phrasing.
- [x] R4: `README.md` disambiguates the existing CC-BY 4.0 and MIT
      references so a reader can see they describe upstream datasets,
      not the TrainingBench code.
- [x] R5: `BACKLOG.md` and `docs/sprints/tb-sprint-001.md` reflect
      that TB-US-009 is in scope for the active sprint. TB-US-005's
      description in `BACKLOG.md` is updated to note that the license
      choice is already made, so the v0.1 cut only needs the version
      tag and changelog entry.

## Acceptance Criteria

- [x] AC1: `git ls-files LICENSE NOTICE` returns both files at HEAD.
- [x] AC2: `diff <(curl -sS https://www.apache.org/licenses/LICENSE-2.0.txt) LICENSE`
      returns no differences (byte-for-byte canonical text).
- [x] AC3: `grep -n "License TBD" README.md` returns zero matches.
      `grep -n "Apache-2.0" README.md` returns at least one match in
      the `## License` section.
- [x] AC4: A reader looking only at the repository root can identify
      the project's license from `LICENSE` alone, without having to
      read `README.md`.

## Design Notes

- The `LICENSE` file uses the canonical Apache Software Foundation
  text without modification. Do not personalize the boilerplate
  copyright block inside the license text itself — that block is
  part of the license and describes the license's own terms. The
  project-specific copyright line belongs in `NOTICE`.
- The `NOTICE` file is short by design. Apache-2.0 requires NOTICE
  attributions to be preserved by downstream redistributors; keeping
  it minimal reduces the burden on forks. Third-party dependency
  attributions live with their respective packages via pip, so we
  do not enumerate them here.
- Per-file SPDX-License-Identifier headers are **not** added in this
  story. They are optional under Apache-2.0 and would touch every
  source file; that scope is a separate concern.
- Copyright year is `2026` (project creation year per `README.md`).
  When source files are meaningfully modified in later years, the
  convention is to update to a range (e.g. `2026-2028`), but that
  is a maintenance concern, not part of this story.

## Out of Scope

- **Per-file SPDX headers.** Optional under Apache-2.0; would touch
  every source file. Separate story if we ever want them.
- **Contributor License Agreement (CLA) / DCO setup.** Signoff and
  contribution mechanics belong to a repository-governance story,
  not a licensing story.
- **CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md.** Standard OSS
  governance files; useful, larger, separate.
- **Third-party dependency license audit.** A downstream release
  concern (are we depending on anything license-incompatible with
  Apache-2.0?). Should happen before v0.1 cut but is not this
  story's work.
- **Dataset licensing review.** The CC-BY 4.0 (CUAD) and MIT (GSM8K)
  references stay as they are; a full review of every dataset the
  platform might touch belongs with the training pipeline docs.

## Related

- TB-US-005 — "Cut v0.1 release." Originally bundled the license
  choice; TB-US-009 pulls that piece forward so TB-US-005's remaining
  scope narrows to version tag and changelog.
- TB-US-002 — First-release install path. TB-US-009 unblocks the
  public-repo push that a verified install path implicitly assumes.
- `LICENSE`, `NOTICE`, `README.md` — the files this story touches.
