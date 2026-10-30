# TB-US-073: Maintenance + upgrade publishing workflow documentation

**Status**: Proposed
**Created**: 2026-10-28
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a TB maintainer (or anyone else who later contributes to the
project), I want **go-to documentation on how to publish a bug fix
or feature upgrade** — the workflow, the artifacts, the git flow,
the version bump decision — so that neither I nor a future
contributor has to reconstruct the pattern from story files or
chat transcripts every time something ships.

## Background

TB-US-071 walked the bug-fix workflow end-to-end as a dual-purpose
story: fix a real bug + demonstrate the maintenance pattern. The
story's R5 flagged a deliverable: *"Capture the maintenance-fix
workflow template at `docs/training/maintenance-fix-workflow.md`
after this story closes."* — explicitly deferred to a follow-up.

Operator (2026-10-28): *"we fixed a bug and showed how that
workflow is going to work. may want to write some additional
documentation around that than just the story so that when either
a bug fix or upgrade is published they have go to documentation."*

Two parallel workflows to document:
1. **Maintenance fix** — a bug surfaces post-release; fix lands as
   a point commit + patch tag increment. Scope: narrow, surgical.
2. **Feature upgrade** — a new feature arc completes; releases roll
   up as a minor-version increment with release notes, maybe RCs.
   Scope: broader, multi-story.

Both share plumbing (git, GitHub Releases, Pages, SemVer) but
differ in cadence and ceremony.

**Depends on:**
- TB-US-068 (closed) + TB-US-071 (closed) — the worked examples
  the docs reference

**Blocks:**
- Nothing hard. A new contributor onboarding without these docs
  can still find their way via the story files, but friction is
  higher.

## Requirements

### 1. Maintenance-fix workflow doc

- [ ] R1: **Deliverable**: `docs/training/maintenance-fix-workflow.md`
      — the "when a bug is reported post-release, here is how to
      ship a fix" doc.
- [ ] R2: **Structure**:
      1. **When to use** — maintenance fix vs. feature work vs.
         upgrade
      2. **The 9-phase workflow** (observe → draft → fire → fix →
         commit → push → downstream verify → close → review-doc
         update), with per-phase guidance:
         - What artifact gets produced
         - What signals the phase is done
         - Common pitfalls
      3. **SemVer impact** — bug fix = patch bump (0.1.0 → 0.1.1)
      4. **Commit message convention** — `TB-US-NNN:` prefix,
         what belongs in the body
      5. **Cache-bust discipline** — frontend changes need `?v=...`
         bump on referenced static files
      6. **Downstream verification pattern** — operator does
         `git pull` + browser retest on throwaway install
      7. **When a fix needs to backport to a stable branch** —
         future consideration; v0.1 is single-branch
- [ ] R3: **Worked example**: reference TB-US-071 as the canonical
      walked-through example. Include commit hash + story links.

### 2. Upgrade-publishing workflow doc

- [ ] R4: **Deliverable**: `docs/training/upgrade-publishing-workflow.md`
      — the "when a feature arc completes, here is how to publish
      the upgrade" doc.
- [ ] R5: **Structure**:
      1. **When to use** — upgrade vs. maintenance fix vs. major
         release
      2. **Pre-release checklist**:
         - All stories in the arc are Completed in BACKLOG
         - CHANGELOG section drafted (if we have one)
         - Known-issues list reviewed
         - Deprecations announced
      3. **Private rehearsal pattern** — same as TB-US-068; walk
         clone + install on throwaway dir; find + fix anything
         surprising before public visibility
      4. **Tagging convention**:
         - `vX.Y.Z-rc1`, `rc2`, ... for release candidates
         - `vX.Y.Z` for the actual cut
         - When to bump X vs. Y vs. Z (SemVer)
      5. **GitHub Release flow**:
         - Draft release from tag
         - Release notes template
         - Attachments (not expected for TB adapter-local
           distribution)
         - Publish decision
      6. **Pages publishing** — if docs changed, how they refresh
      7. **Post-release**: update version strings in-repo if any,
         merge any late fixes
- [ ] R6: **Worked example**: reference TB-US-068 as the canonical
      private-rehearsal example. Describe how TB-US-005 (public
      cut) extends it.

### 3. Cross-cutting

- [ ] R7: Both docs cross-reference each other at the top so a
      maintainer landing on one knows the other exists
- [ ] R8: Both docs link to `CONTRIBUTING.md` for the broader
      story-driven development context
- [ ] R9: Add index entries at `docs/README.md` pointing to both
      new docs

## Acceptance Criteria

- [ ] AC1: `docs/training/maintenance-fix-workflow.md` exists with
      the 9-phase workflow documented
- [ ] AC2: `docs/training/upgrade-publishing-workflow.md` exists
      with the release-cut flow documented
- [ ] AC3: Each doc includes at least one worked example referencing
      a real completed TB-US story (TB-US-071 and TB-US-068
      respectively)
- [ ] AC4: Both docs link to CONTRIBUTING.md and to each other
- [ ] AC5: `docs/README.md` has entries for both
- [ ] AC6: A new contributor reading just these two docs could
      execute a bug fix or a point release without needing to
      ask the maintainer "what's the process"

## Design Notes

- **Why two docs, not one.** Maintenance (fix a bug) and upgrade
  (ship a feature) have different cadences, different ceremony,
  and get searched for by different mental models. Separation
  reduces cognitive load at the moment someone needs the doc.
- **Why not fold these into INSTALL.md or README.md.** INSTALL and
  README are for *users* of TB (operators standing up an install).
  These two docs are for *maintainers of TB itself* (people
  changing the code). Different audience, different directory
  (`docs/training/` → arguably rename to `docs/maintainers/`
  if the audience distinction matters more than the current
  "training" ambiguity).
- **Why 9 phases, not more or fewer.** The TB-US-071 walkthrough
  landed on 9 phases organically. Writing them down formalizes
  the pattern. If a future workflow adds/removes a phase, this
  doc is where it lives.
- **Why reference stories rather than inline the full flow.** The
  story files ARE the project's development history
  (CONTRIBUTING.md pattern). Having the doc link to TB-US-071 lets
  readers see the real artifacts (story file + commit + review doc
  update) rather than a sanitized retelling.
- **Why no CHANGELOG / release-notes template yet.** TB doesn't
  have a CHANGELOG today. If TB-US-005 or a successor adopts one,
  this doc should be updated. For now, link to GitHub Releases
  draft-notes as the equivalent.

## Out of Scope

- Writing an actual CHANGELOG (separate story if operator decides
  to adopt that convention)
- Backport-to-stable-branch workflow (TB is single-branch for v0.1)
- Hotfix-under-pressure runbook (fast-path version of maintenance
  for genuine incidents; can be a future story once v0.1 has real
  users with real incident response needs)
- Build / publish of a package (PyPI, Docker) — v0.1 scope is
  source-only distribution

## Related

- [TB-US-068](tb-us-068.md) — worked example for the upgrade
  workflow (private rehearsal arm)
- [TB-US-071](tb-us-071.md) — worked example for the maintenance
  workflow + R5 which flagged this doc as a deliverable
- [TB-US-061](tb-us-061.md) — CONTRIBUTING.md shipped the broader
  story-driven development context; this story extends it
  maintainer-side
- [TB-US-072](tb-us-072.md) — companion story (comprehensive UI
  acceptance pass)
- [TB-US-005](tb-us-005.md) — public v0.1 cut; may use the upgrade
  doc as a reference during the cut itself
