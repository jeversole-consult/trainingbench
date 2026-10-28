# TB-US-013: Spike — IP and copyright transfer strategy (Jesse → Eversole Learning, LLC)

**Status**: Completed
**Created**: 2026-09-10
**Completed**: 2026-10-12
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As TrainingBench's author, I want a written brief on the IP and
copyright transfer options for TB — moving the copyright holder
from Jesse Eversole (individual) to Eversole Learning, LLC — so
that I can make the transfer decision with clear timing and
mechanics rather than improvising it at release time.

## Background

TrainingBench has been developed under individual authorship.
Under default US copyright law, the copyright belongs to Jesse
Eversole as the individual author. Eversole Learning, LLC was
recently formed with the intent of being the operating entity
behind Jesse's software work — a fact captured on the projmgmt
board as PM-US-006 (which is In Progress; NC SoS response and
downstream tasks like EIN, bank account, operating agreement are
still in flight).

Before TB goes public, the LICENSE file's copyright line has to
attribute the work to *someone*. Doing that assignment cleanly
before first public release is simpler than doing it later —
after release, an ownership change requires either rewriting
history (potentially messy for downstream forks) or a public
assignment notice, and the LICENSE header on every source file
may need to change.

This spike is **business/legal analysis, not code**. Its output
is a brief that recommends a specific path.

## Requirements

- [x] R1: **Document current IP posture.** Addressed as part of
      the general-counsel discussion. Research outcome recorded
      in Completion Notes.
- [x] R2: **Transfer mechanisms.** Resolved — **general counsel
      for EL was engaged** to advise on the mechanism and to
      draft the assignment document (see Completion Notes). The
      "attorney required vs template sufficient" question was
      answered by engaging counsel directly.
- [x] R3: **Timing decision.** Resolved — transfer executed
      **before first public release**, consistent with the
      "recommended default: clean start" framing. Done 2026-10-12.
- [x] R4: **LICENSE authorship line decision.** Resolved — the
      copyright holder of record is now **Eversole Learning, LLC**.
      TB's LICENSE file authorship line should read
      `Copyright (c) 2026 Eversole Learning, LLC` when TB-US-005
      cuts v0.1.
- [x] R5: **Previously-published artifacts.** Addressed in the
      general-counsel discussion. See Completion Notes.
- [x] R6: **PM-US-006 dependency check.** Resolved by the
      execution itself: the LLC was fully constituted (filed
      Articles, issued EIN, signed operating agreement) when the
      assignment was executed. R3 of PM-US-006 (bank account) is
      still deferred and did **not** block the assignment —
      confirmed by actual execution.
- [x] R7: **Deliverable.** **Superseded** — the committed
      deliverable path was `docs/release/ip-transfer-brief.md`
      (a plan artifact). The execution outcome (signed
      assignment via general counsel) supersedes the plan,
      making the brief redundant. The documentation trail lives
      in this story's Completion Notes instead. If a separate
      brief file is ever useful for external reference, it can
      be derived from this story.

## Acceptance Criteria

- [x] AC1: **Superseded** — the deliverable path
      `docs/release/ip-transfer-brief.md` was not produced
      because the execution outcome (signed assignment) replaces
      the planning artifact. See R7 Completion Notes.
- [x] AC2: Resolved — the "recommended path" question was
      answered through general-counsel engagement. The path
      chosen: formal assignment agreement drafted by counsel
      and signed, transferring copyright from Jesse Eversole
      (individual) to Eversole Learning, LLC.
- [x] AC3: Resolved — **a lawyer was involved** (EL's general
      counsel). The template-vs-attorney tradeoff was decided
      in favor of attorney involvement given the direct
      availability of general counsel and the one-shot nature
      of the founding IP assignment.
- [x] AC4: LICENSE authorship line (R4 outcome) is
      `Copyright (c) 2026 Eversole Learning, LLC`. This is
      directly consumable by TB-US-012's playbook when it
      finalizes repo home and license-file content, and by
      TB-US-005 R4 at release-cut time.
- [x] AC5: Confirmed — TB stays on Apache-2.0 (per TB-US-009,
      Shipped); only the copyright holder named in the LICENSE
      changes. No license switch, no re-licensing concern.

## Design Notes

- **Not legal advice.** The spike produces a brief that helps
  the operator decide whether/when to talk to a lawyer, and what
  to ask. Any actual execution (signing an assignment agreement,
  filing anything) is a downstream action, not part of this
  spike.
- **"At the right time" is the deliverable.** The user's
  phrasing on 2026-09-10 was "I need to transfer that to the
  newly formed company at the right time." R3 is where the
  brief has to actually answer that.
- **Templates exist.** Copyright assignment agreements between
  an individual and an LLC they own are extremely common (every
  founder does one). Templates from reputable sources
  (Cooley GO, Y Combinator SAFE-adjacent library, state bar
  associations) should be surveyed before recommending "hire a
  lawyer."
- **The LLC's operational readiness is separate from its legal
  existence.** An LLC exists as a legal entity from the date the
  state acknowledges the filing. It can be a party to an
  agreement before it has an EIN or a bank account. R6 confirms
  this concretely for NC.

**Completion Notes (2026-10-12).**

The spike resolved differently than its draft anticipated: rather
than producing a written brief that would then be acted upon
later, the operator engaged **EL's general counsel** directly
for legal advice on the IP assignment, and executed the
assignment in one step.

**What happened:**

1. **General-counsel consultation.** The copyright-assignment
   question was discussed with EL's general counsel, who
   provided legal advice on the mechanism, timing, and
   documentation requirements.
2. **Document drafting.** General counsel drafted the
   assignment document — a formal copyright assignment from
   Jesse Eversole (individual) to Eversole Learning, LLC. Not
   a self-service template; a counsel-drafted agreement
   tailored to the engagement.
3. **Execution.** The assignment document was signed to
   complete the transfer. The copyright of TrainingBench (and
   any related IP covered by the agreement's scope) now
   resides with Eversole Learning, LLC.
4. **Signed copy storage.** Operator-managed external store
   (same pattern as PM-US-006's founding documents — pointer
   in the external company documents index; actual signed copy
   not in this repo).

**Downstream resolutions:**

- **LICENSE authorship line** (R4 / AC4): TB-US-005 R4 and
  TB-US-012's playbook can now use
  `Copyright (c) 2026 Eversole Learning, LLC` as the final
  text — no more TBD.
- **Repo home consistency** (TB-US-012 R1 / PM-US-018 R1):
  copyright holder (LLC) matches corporate owner of the
  GitHub org (LLC). Clean alignment.
- **PM-US-018** (GitHub org setup brief): the operator-managed
  external store is now the authoritative source for the
  signed assignment; PM-US-018 may reference it when drafting
  the IP-related sections of the setup playbook.
- **PM-US-006 R3** (deferred bank account): remains deferred;
  the assignment execution did **not** require a bank account,
  confirming the "fully-constituted entity without a bank
  account is sufficient to execute agreements" posture.

**Why the brief file wasn't written.** The committed deliverable
`docs/release/ip-transfer-brief.md` was a planning artifact
intended to inform a later execution. Since execution happened
directly through counsel, the brief would be a backfill of a
plan that was never followed in that order — the trail that
matters is "general counsel advised, drafted, signed," which
lives here. If a separate externally-referenceable brief is
ever needed (e.g. for an audit or a future collaborator), it
can be derived from these completion notes without loss.

## Out of Scope

- Executing the assignment (signing paperwork). Follow-up story.
- Consulting an actual attorney. That's an action driven by the
  brief's recommendation.
- GitHub release mechanics (TB-US-012).
- License selection (TB-US-009 already Shipped; TB stays on
  Apache-2.0).
- OSS compliance / community norms (TB-US-014).
- Employment / IP-assignment agreements for future contributors
  (that's a company-side concern, not TB-specific).
- Anything about Eversole Learning's own formation status —
  tracked in projmgmt as PM-US-006. R6 only checks whether that
  status blocks this spike's recommendation.

## Related

- Other stories:
  - TB-US-005 — Cut v0.1 release. Downstream; the LICENSE
    authorship line R4 decides feeds directly into release.
  - TB-US-009 — Apache-2.0 licensing (already Shipped). This
    spike doesn't change the license; only the copyright holder
    named in it.
  - TB-US-012 — GitHub release mechanics. R1 (repo home)
    depends on this spike's outcome.
  - TB-US-014 — OSS compliance. LICENSE authorship affects
    CONTRIBUTING and DCO/CLA framing.
- PRs / commits: —
- External:
  - PM-US-006 (Eversole Learning, LLC founding) on the projmgmt
    board — upstream context, not blocking this spike itself.
