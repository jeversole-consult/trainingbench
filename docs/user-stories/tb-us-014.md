# TB-US-014: Spike — GitHub compliance and OSS norms for TrainingBench

**Status**: In Progress
**Created**: 2026-09-10
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As TrainingBench's author, I want a written checklist covering
license compatibility, GitHub's community-standards surface, and
the contribution-model decisions TB needs before public release,
so that v0.1 lands with the correct community-facing artifacts
already in place rather than being retrofitted after the fact.

## Background

Apache-2.0 licensing is already decided and shipped (TB-US-009).
This spike is **not** license selection; it's everything that
sits alongside the license: dependency compatibility, model-weight
compatibility (TB fine-tunes Llama models — Meta's license has
conditions), the contribution model (DCO vs CLA vs neither), and
the standard community-facing docs GitHub scores repos on.

Adding these files after release is possible but expensive: they
change the experience of the very first outside contributors and
set precedent. Cheaper to decide before v0.1 than after.

This spike, TB-US-012 (mechanics), and TB-US-013 (IP) are the
three inputs to TB-US-005 (Cut v0.1 release).

## Requirements

- [ ] R1: **License compatibility audit — dependencies.** Walk
      TB's declared dependencies (`requirements.txt`, informed by
      TB-US-007's audit) and identify each package's license.
      Flag any GPL / AGPL / SSPL packages that would restrict
      TB's Apache-2.0 outbound licensing or require reciprocal
      licensing.
- [ ] R2: **License compatibility — Llama model weights.** TB
      fine-tunes Llama models. Meta's Llama 3 Community License
      has commercial-use conditions and attribution requirements.
      Confirm: does releasing TB's *code* (not the fine-tuned
      weights themselves) satisfy the Llama license? What does
      the README need to disclose? Does distributing *adapters*
      (LoRA / QLoRA weights) trigger anything different from
      distributing full fine-tuned weights?
- [ ] R3: **Contribution model decision.** Choose one of:
      - **DCO** (Developer Certificate of Origin — commit
        sign-off, no separate agreement). Low friction, common
        for modern OSS.
      - **CLA** (Contributor License Agreement — separate
        signed doc per contributor). Higher friction; useful if
        a company plans to relicense later.
      - **Neither** — accept contributions with implicit
        Apache-2.0 inbound. Lowest friction; least legal cover.
      Recommend one with reasoning.
- [ ] R4: **Community-facing docs list.** Decide which of these
      exist at v0.1 and their minimum content:
      - `CONTRIBUTING.md` (how to file issues, how to submit
        PRs, dev-environment setup pointer)
      - `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1 or
        similar boilerplate)
      - `SECURITY.md` (how to report vulnerabilities, response
        expectations)
      - `SUPPORT.md` (where to ask questions)
      - Issue templates (`.github/ISSUE_TEMPLATE/*.md`) — bug
        report, feature request
      - PR template (`.github/pull_request_template.md`)
- [ ] R5: **GitHub community-profile checklist.** GitHub scores
      each repo on a "Community Standards" health check
      (Description, README, CoC, Contributing, License, Issue
      templates, PR template). List the items TB needs to hit
      before v0.1 and any that are OK to defer.
- [ ] R6: **Third-party integrations decision.** Which
      integrations enable at launch (Dependabot for dep updates,
      CodeQL for security scanning, secret-scanning if not
      already on)? Cost is small; err on the side of enabling
      unless there's a reason not to.
- [ ] R7: **README-required disclosures.** Compile the list of
      things the README must explicitly say (Llama license
      attribution, hardware requirements, dataset licensing for
      any bundled or referenced datasets, model provenance).
- [ ] R8: **Deliverable.** Checklist lands as
      `docs/release/oss-compliance-checklist.md`. Each R1–R7
      item is resolved with a specific answer.

## Acceptance Criteria

- [ ] AC1: `docs/release/oss-compliance-checklist.md` exists.
- [ ] AC2: License compatibility (R1 + R2) has been
      **verified**, not assumed. Any incompatible dependency is
      called out by name.
- [ ] AC3: A single contribution model (R3) is chosen with
      documented reasoning.
- [ ] AC4: The community-facing docs list (R4) states which
      files exist at v0.1 vs are deferred.
- [ ] AC5: The checklist and TB-US-012's playbook together are
      sufficient for TB-US-005 to execute the release without
      further compliance research.

## Design Notes

- **License is not up for debate.** Apache-2.0 shipped in
  TB-US-009. This spike works within that constraint; it does
  not reopen it.
- **Llama license is the highest-risk unknown.** Meta's terms
  have moved multiple times. R2 must be answered against the
  current published license, with the URL and date-checked cited
  in the checklist.
- **DCO vs CLA lean.** DCO is the modern default for solo /
  small-team OSS projects. CLAs make sense when a company
  expects to relicense (e.g. dual-license commercial + OSS).
  Absent that intent, DCO is the recommendation to beat.
- **Cheap-to-include, expensive-to-omit.** The community docs
  (R4) each take minutes to draft from templates. Skipping any
  of them and adding later signals "afterthought" to the first
  outside contributor.

## Out of Scope

- Writing the CONTRIBUTING / CoC / SECURITY / README files
  themselves. That's implementation, downstream of this spike.
  Templates and required content are decided here; drafting
  happens in a follow-up.
- GitHub release mechanics (TB-US-012).
- IP / copyright transfer (TB-US-013).
- License selection (TB-US-009 — done).
- Post-release community management (issue triage, PR review
  cadence, roadmap publication).
- Marketing, launch announcement, HN post, arXiv preprint —
  those are release-day and post-release concerns, not
  compliance.

## Related

- Other stories:
  - TB-US-005 — Cut v0.1 release. Downstream; this spike's
    output is required input.
  - TB-US-007 — Dependency prune (Queued). Its audit feeds R1.
  - TB-US-009 — Apache-2.0 licensing (Shipped). Constraint,
    not variable.
  - TB-US-012 — GitHub release mechanics. Parallel spike.
  - TB-US-013 — IP transfer. Affects LICENSE authorship and
    contributor-agreement framing.
- PRs / commits: —
- External:
  - Meta Llama Community License (URL + date-checked, per R2)
  - Contributor Covenant (`https://www.contributor-covenant.org/`)
  - GitHub Community Standards docs
