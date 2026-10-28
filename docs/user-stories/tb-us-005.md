# TB-US-005: Cut v0.1 release

**Status**: Proposed
**Created**: 2026-09-27
**Reclassified**: 2026-10-14 (In Progress → Proposed; paired with TB-US-004)
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

> **Stub** — requirements will tighten when picked up.
>
> **Reclassified Proposed 2026-10-14** — paired with TB-US-004
> (README quickstart). Launch arc dormant since OT and sync-
> forward took priority. Reactivate as a pair when the operator
> decides to push toward v0.1 cut.

## Story

As TrainingBench's author, I want to cut `v0.1.0` as a public
GitHub Release, so that TB has a citable version anchor and
downstream work (community feedback, sub-releases, papers
referencing "TB v0.1") has an unambiguous reference point.

## Background

This story is the actual **release execution**. It runs the plan
that the three spikes (TB-US-012, TB-US-013, TB-US-014) produce,
against the codebase that the hardening and documentation
stories have prepared.

Upstream dependencies (must be Completed before this story
starts real work):

- **TB-US-012** — GitHub release playbook (repo home, history
  strategy, secrets scan, CI baseline)
- **TB-US-013** — IP transfer brief (LICENSE authorship line
  decision)
- **TB-US-014** — OSS compliance checklist (community docs,
  contribution model)
- **TB-US-007** — Dependencies pruned
- **TB-US-004** — README quickstart landed
- **TB-US-003** — Password hashing hardened (or superseded)

Once those are in place, this story is largely mechanical:
create the repo (or set the private repo public), run the
secrets scan, apply the LICENSE authorship line, land the
community docs, push, tag `v0.1.0`, publish a GitHub Release
with notes.

## Requirements (draft — will tighten when picked up)

- [ ] R1: All upstream stories (listed above) are Completed.
      Verified by inspecting each of their story files.
- [ ] R2: GitHub repo exists at the URL chosen in TB-US-012 R1,
      with visibility set to Public.
- [ ] R3: Local repo prepared according to TB-US-012 R2's
      history strategy (squash-to-clean vs preserve). Secrets
      scan per TB-US-012 R4 comes back clean.
- [ ] R4: `LICENSE` file authorship line matches TB-US-013 R4's
      recommendation. Every source file's copyright header (if
      any) aligns.
- [ ] R5: Community docs from TB-US-014 R4 are landed:
      `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`,
      and any issue/PR templates that made the cut.
- [ ] R6: `CHANGELOG.md` initial entry for `v0.1.0` written —
      short list of what shipped.
- [ ] R7: `git push` to the public remote succeeds. Branch
      protection rules on `main` per TB-US-012 R7 applied.
- [ ] R8: `git tag v0.1.0`, pushed to remote.
- [ ] R9: GitHub Release page for `v0.1.0` created with release
      notes summarizing shipped scope and linking to the README.

## Acceptance Criteria (draft)

- [ ] AC1: A stranger visits the public URL, sees the repo,
      clones it, and can execute the README quickstart to
      produce a trained adapter — matches TB-US-015 AC1.
- [ ] AC2: `v0.1.0` tag exists on the public remote.
- [ ] AC3: GitHub Release page for `v0.1.0` is published and
      linked from the repo's Releases sidebar.
- [ ] AC4: GitHub Community Standards checklist is 100% green
      (or every gap is intentional and documented per TB-US-014).
- [ ] AC5: No secrets are present in the pushed history —
      verified per TB-US-012's secrets-scan procedure.

## Design Notes (draft)

- **This story is orchestration, not design.** All the hard
  decisions are made in the upstream spikes and hardening
  stories. If a decision has to be made *during* this story's
  execution, that's a signal an upstream story wasn't complete.
- **CHANGELOG for v0.1 is short.** Everything is "initial
  release." Keep the entry brief; details live in the README
  and in the individual story files.
- **Release notes should link to the README quickstart** —
  that's the strongest onramp for someone landing on the
  release page.

## Out of Scope

- Announcement / marketing plan (HN post, LinkedIn, arXiv, etc.)
  — that's a separate launch story (see TB-US-015 Known
  unknowns).
- Post-release community management (issue triage cadence, PR
  review, roadmap).
- v0.2 planning.

## Related

- [TB-US-015](tb-us-015.md) — launch coordinator; R5 phase gate.
- [TB-US-012](tb-us-012.md), [TB-US-013](tb-us-013.md),
  [TB-US-014](tb-us-014.md) — upstream spikes.
- [TB-US-007](tb-us-007.md) — dependency prune (upstream).
- [TB-US-004](tb-us-004.md) — README quickstart (upstream).
- [TB-US-003](tb-us-003.md) — password hashing hardening
  (upstream or superseded by PM-US-004).
- [TB-US-009](tb-us-009.md) — Apache-2.0 licensing (Shipped;
  informational).
