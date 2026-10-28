# TB-US-004: Training quickstart in README

**Status**: Proposed
**Created**: 2026-09-27
**Reclassified**: 2026-10-14 (In Progress → Proposed; paired with TB-US-005)
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

> **Stub** — requirements will tighten when picked up.
>
> **Reclassified Proposed 2026-10-14** — honest status cleanup
> during a cleanup round. TB-US-004 and TB-US-005 are a tightly-
> coupled launch-arc pair; neither has been actively worked
> since the 2026-09-27 arc-scoped WIP flip. Parked together.
> Reactivate as a pair when the operator decides to push the
> launch arc toward v0.1 cut.

## Story

As a researcher who just cloned TrainingBench for the first time,
I want the README to include a **training quickstart** — the
smallest sequence of commands that goes from "fresh clone" to "I
trained an adapter and saw a before/after metric" — so that I can
evaluate whether TB is worth investing more of my time in before
reading a 30-page install guide.

## Background

TrainingBench's existing install path (TB-US-002, Shipped) gets
someone from clone to a running backend. That is not the same as
gets them from clone to *trained an adapter*. For a research
project, "train an adapter" is the actual demonstration; anything
before that is preamble. A stranger evaluating TB in five minutes
needs to see that demonstration in the README, not chase it
through separate docs.

TB has one training entrypoint that TB-US-001 (Shipped) hardened:
`python training/math/train.py` with configurable sample counts,
epochs, and a smoke-test invocation. The quickstart likely
inherits from that same invocation — small samples, one epoch,
a named run — and shows what the output looks like.

The launch coordinator (TB-US-015 AC1) requires that a stranger
can clone the public repo and produce a trained adapter without
asking the operator a question. This story is the doc surface
that makes AC1 achievable.

## Requirements (draft — will tighten when picked up)

- [ ] R1: README `Quickstart` section added, sitting above the
      more detailed `Installation` and `Usage` sections. Lives
      at the top of the file, right after the tagline.
- [ ] R2: The section is copy-pasteable — every command a user
      needs to run is in a fenced code block, in order, with no
      "and then..." prose gaps. Includes: clone, venv create,
      install, download prerequisites (if any), run the smoke
      training command, view the output.
- [ ] R3: The smoke training command completes in under 5
      minutes on a typical modern laptop or matches the smoke
      target from TB-US-001. If longer, the quickstart says so
      up front.
- [ ] R4: The section shows expected output (a short excerpt,
      not the full log) so the reader knows what "success"
      looks like.
- [ ] R5: The section mentions hardware requirements at least
      in one line (GPU present or CPU-only, RAM, disk). Detailed
      requirements can link to `INSTALL.md` for more.
- [ ] R6: Verified against a fresh clone — reviewer follows the
      quickstart on a clean checkout, exactly as written, and
      it works end-to-end.

## Acceptance Criteria (draft)

- [ ] AC1: A reader who does not already know TrainingBench can
      go from URL to "trained an adapter" using only the README
      quickstart, without consulting any other file.
- [ ] AC2: The quickstart completes in the time the section
      promises (whatever number is chosen — 5 min, 15 min, etc.).
- [ ] AC3: A fresh-clone verification pass has been executed
      and the commit message notes when and where.

## Design Notes (draft)

- **Above the fold matters.** The section is worth more if it
  is the first substantive thing in the README, not buried
  under a 500-word narrative.
- **Copy-paste discipline.** Every command in one code block
  chain, exactly executable. No `<placeholder>` values unless
  they're documented in the same block.
- **Sample size matters for the "5 minutes" claim.** The smoke
  training run should use small enough sample counts that even
  a modest machine can complete it; the fine-tuning is a demo,
  not a real experiment.

## Out of Scope

- Rewriting the entire README. Only the Quickstart section is
  in scope; adjacent sections are touched only as needed to
  avoid contradicting the quickstart.
- Producing a video walkthrough. Not this story.
- Explaining PEFT / LoRA / QLoRA in depth. Point the curious
  reader at published resources; the quickstart is about
  getting hands on the tool, not teaching the underlying method.
- Multi-domain quickstart (all five TB domains). One domain is
  enough for a first taste; the others get their own docs.
- Windows-specific quickstart. Assume Linux/macOS for v0.1.

## Related

- [TB-US-015](tb-us-015.md) — launch coordinator; R3 phase gate.
- [TB-US-001](tb-us-001.md) — the smoke training command this
  quickstart inherits from.
- [TB-US-002](tb-us-002.md) — install path; the quickstart
  starts where TB-US-002 leaves off.
- `README.md` — file being modified.
- `INSTALL.md` — sibling doc for detailed install; quickstart
  points to it for full detail.
