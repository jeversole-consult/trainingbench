# TB-US-015: TrainingBench public launch — coordinator story

**Status**: In Progress
**Created**: 2026-09-27
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As TrainingBench's author, I want a single coordinator story that
tracks the arc of taking TB from a private research project to a
public open source release, so that the multiple sub-stories the
launch requires have a navigable parent and I always know "where
we are" without scanning the whole backlog.

## Background

TB has been developed as a private local project. A public
release means:

- A public repository (GitHub is the working assumption; final
  decision belongs to TB-US-012).
- A license file with a defensible copyright holder (Apache-2.0
  is chosen per TB-US-009; the copyright authorship line
  depends on TB-US-013).
- Documentation sufficient for an outside researcher to clone,
  install, train an adapter, and reproduce a headline result.
- Community-facing artifacts (README, CONTRIBUTING, CoC,
  SECURITY, issue templates) at the level GitHub scores against
  the Community Standards checklist.
- A `v0.1.0` tag and GitHub Release.

Three **spike stories** were written on 2026-09-10 to resolve
open questions before the release stories execute:

- **[TB-US-012](tb-us-012.md)** — GitHub release mechanics
  (playbook)
- **[TB-US-013](tb-us-013.md)** — IP + copyright transfer brief
- **[TB-US-014](tb-us-014.md)** — OSS compliance checklist
  (license compatibility, DCO/CLA, community docs)

Existing queued work also feeds the launch:

- **TB-US-003** — Per-user random password salts (security fix)
- **TB-US-004** — Training quickstart in README
- **[TB-US-005](tb-us-005.md)** — Cut v0.1 release (the actual
  release story; downstream of the spikes)
- **[TB-US-007](tb-us-007.md)** — Prune unused dependencies

Additional sub-stories will be identified during execution;
this coordinator will be updated as they are written. See
**Known unknowns** below for the current list of anticipated
but not-yet-written work.

## Requirements

Each requirement below is a **phase gate** that references one
or more sub-stories. This coordinator does not execute code
itself; sub-stories carry the actual work. This story completes
when every phase gate is satisfied.

- [ ] **R1: Spikes closed.** All three spike briefs delivered
      and their recommendations adopted:
  - [ ] TB-US-012 — GitHub release playbook exists in
    `docs/release/github-release-playbook.md`
  - [x] TB-US-013 — **Completed 2026-10-12.** The spike's
    recommendation was executed directly: EL's general counsel
    drafted and signed a copyright assignment from Jesse to
    Eversole Learning, LLC. The committed deliverable path
    (`docs/release/ip-transfer-brief.md`) was superseded by
    the signed assignment; the trail lives in TB-US-013's
    Completion Notes. LICENSE authorship line is now
    `Copyright (c) 2026 Eversole Learning, LLC`.
  - [ ] TB-US-014 — OSS compliance checklist exists in
    `docs/release/oss-compliance-checklist.md` with a chosen
    contribution model
- [ ] **R2: Code hardening done.** Everything the spikes flag
      as blocking public release lands:
  - TB-US-003 — Per-user salts (**Deferred 2026-10-14** —
    conditional on PM-US-004 IAM decision; no longer a hard
    launch gate. See TB-US-003 for reactivation condition.)
  - TB-US-007 — Dependencies pruned
  - Any additional hardening surfaced by TB-US-014's license-
    compatibility audit
- [ ] **R3: Documentation ready.** Public-facing docs cleared:
  - TB-US-004 — README quickstart landed
  - Community-facing docs (CONTRIBUTING / CODE_OF_CONDUCT /
    SECURITY / issue + PR templates) — sub-story TBD
  - README-required disclosures (Llama license, hardware,
    dataset provenance) — captured under TB-US-014's checklist
- [ ] **R4: Reproducibility validated.** An outside-of-Jesse
      environment (fresh venv or fresh box) reproduces at least
      one headline TB result end-to-end. Sub-story TBD.
- [ ] **R5: Public release cut.** TB-US-005 executes: repo
      created (per TB-US-012 R1), initial commit pushed, LICENSE
      authorship line correct (per TB-US-013 R4), `v0.1.0` tag
      and GitHub Release published.
- [ ] **R6: Post-release plan on paper.** Where issues go, who
      triages, cadence for follow-up. Sub-story TBD or captured
      inline here.

## Acceptance Criteria

Observable end state of the whole arc, not any single sub-story.

- [ ] **AC1**: A stranger with a modern Linux machine can visit
      the public repo URL, follow the README, and produce a
      trained adapter for at least one domain without asking
      the operator a question.
- [ ] **AC2**: GitHub's Community Standards checklist for the
      repo is 100% green (or every gap is intentional and
      documented in TB-US-014's checklist).
- [ ] **AC3**: `git log --all` on the public repo shows a
      LICENSE file whose copyright line matches the outcome of
      TB-US-013 (Jesse Eversole vs Eversole Learning, LLC —
      whichever the brief recommended).
- [ ] **AC4**: `v0.1.0` tag exists and a GitHub Release page
      exists for it with release notes summarizing what shipped.
- [ ] **AC5**: No secrets have been pushed. Verified either by
      the secrets-scan procedure documented in TB-US-012 R4,
      or by TB-US-012 R2's fresh-history strategy having been
      applied.
- [ ] **AC6**: The projmgmt board shows every referenced sub-
      story as `Status: Completed`, and this story as
      `Status: Completed`.

## Design Notes

- **This is a coordinator story, not an epic.** The projmgmt
  model is intentionally story-only; there is no separate epic
  artifact type. This story does what an epic would do (link
  and track sub-stories) using only ordinary story machinery.
  See `MEMORY.md → feedback_coordinator_not_epic` for the
  rationale.
- **In Progress for months is expected.** This story will
  legitimately sit In Progress from creation (2026-09-27)
  through whenever the launch actually happens. That is honest
  state — the arc is ongoing — not the drift smell that phase-
  split guidance warns about for executing stories.
- **How to add a new sub-story.** When work is identified that
  belongs to the launch:
  1. Write a normal `tb-us-NNN.md` story with tight scope.
  2. Update this coordinator's Requirements section to
     reference it under the correct phase gate (R1–R6).
  3. Update Related with a link.
  4. That's it — no meta-artifact machinery to touch.
- **How completion works.** When a sub-story reaches Completed,
  tick its checkbox under the appropriate R above. When all
  Rs are ticked and the ACs hold, flip this story to Completed.
- **Sub-story authorship independence.** Each sub-story stands
  on its own — its Requirements and ACs describe *its* work,
  not the launch's work. The coordinator doesn't override the
  sub-story's scope. If a sub-story's outcome makes a launch
  R obsolete or irrelevant, update the R here (don't rewrite
  the sub-story).
- **Story split rule for known-unknowns.** Every anticipated
  piece of work below gets its own sub-story before it starts.
  Do not add work items directly into this coordinator's
  Requirements without a corresponding sub-story file.

## Known unknowns — sub-stories to be written

Anticipated work that does not yet have a story file. Each
item below becomes a `TB-US-NNN` at the point work on it
begins. This list is a placeholder; add / edit freely as
scope becomes clearer.

- **Community-facing docs (CONTRIBUTING, CoC, SECURITY, issue
  and PR templates).** Content decisions come from TB-US-014;
  drafting the files is separate work.
- **Reproducibility validation.** Fresh-environment run of at
  least one headline benchmark, transcript captured.
- **Test suite baseline.** Basic sanity tests that a CI job
  can run. Scope TBD — could be smoke tests only for v0.1.
- **Launch announcement plan.** Where to post (HN, LinkedIn,
  arXiv preprint if applicable), when, with what message.
  Marketing-adjacent, not code.
- **Post-release triage cadence** (R6).
- **Domain / landing page** on `eversolelearning.ai` — deferred
  per the branding-freeze preference; may or may not be
  launch-blocking depending on how public a face TB gets.

## Out of Scope

- **Post-launch community management.** Once shipped, ongoing
  issue triage / PR review / release cadence is its own arc.
- **Building marketing surfaces beyond the launch itself.**
  The landing page, brand assets, tagline copy, etc. are all
  branding work and deferred.
- **Fund-raising, grant applications, sponsor conversations.**
  Related to Eversole Learning's business posture, not to TB
  as an OSS release.
- **The Durham Tech proposal arc** (PM-US-012/013/014 on the
  projmgmt board). Independent trajectory per operator
  decision on 2026-09-10 — the proposal may reference TB but
  TB's release does not depend on the proposal's outcome.
- **Roadmap for TB v0.2+.** Anything past v0.1 belongs to a
  future coordinator, not this one.

## Related

Sub-stories referenced by this coordinator:

- [TB-US-003](tb-us-003.md) — Per-user random password
  salts *(**Deferred 2026-10-14** — conditional on PM-US-004.
  Story file created during 2026-09-27 arc-scoped flip.)*
- [TB-US-004](../../BACKLOG.md) — Training quickstart in
  README *(Queued; entry in TB BACKLOG.md — no story file yet)*
- [TB-US-005](tb-us-005.md) — Cut v0.1 release *(Queued)*
- [TB-US-007](tb-us-007.md) — Prune unused dependencies
- [TB-US-009](tb-us-009.md) — Apache-2.0 licensing *(Shipped;
  informs but is not a phase gate)*
- [TB-US-012](tb-us-012.md) — Spike: GitHub release mechanics
- [TB-US-013](tb-us-013.md) — Spike: IP + copyright transfer
- [TB-US-014](tb-us-014.md) — Spike: OSS compliance checklist

Cross-project links:

- **PM-US-004** on projmgmt (Shared IAM foundation) — could
  supersede TB-US-003 if adopted before v0.1 cut. Coordinator
  should re-check R2 when PM-US-004 activates.

External references:

- `docs/release/` — directory where the three spikes' outputs
  land (playbook / brief / checklist).
- `MEMORY.md → feedback_coordinator_not_epic` — rationale
  for using a coordinator story instead of introducing epics.
