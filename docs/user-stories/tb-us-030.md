# TB-US-030: Build and deploy a custom agent — operator workflow

**Status**: In Progress
**Created**: 2026-10-14
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

**Deliverable**: docs/training/build-and-deploy-agent.md

## Story

As the operator (or a future collaborator) building a custom
agent on TB's OT v0.1 foundation, I want a single written
walkthrough that starts from an empty state and ends with a
deployed Agent Release — covering domain definition, data
curation, calculator / lookup configuration, training (if
desired), verification, release packaging, and deployment —
so that I can produce a working agent without reverse-
engineering the OT architecture from code.

## Background

TB-US-022 through TB-US-029 build the OT architecture and
prove it with the math example. This story is the
**operator-facing manual** — the "now what do I do with it"
walkthrough. It makes the OT pipeline usable by a human
following step-by-step instructions rather than by Claude
Code following code commits.

The walkthrough is **documentation plus minimal tooling.**
Where a step requires a command, the walkthrough gives the
exact command. Where a step requires editing a config file,
the walkthrough shows a before/after example. Where a step
requires reasoning (e.g., "decide what categories your domain
needs"), the walkthrough explains the decision factors.

The deliverable is a single markdown file at
`docs/training/build-and-deploy-agent.md`. Supporting tooling
(templates, scripts) is secondary; the doc is the artifact.

## Requirements

### Deliverable structure

- [ ] R1: **`docs/training/build-and-deploy-agent.md`** with
      the following sections at minimum:
      1. **Overview** — what an "agent" is in TB's model
         (components: base model, adapter, RAG DB, calculators,
         lookup sources, classifier config, system prompts,
         runtime config); what an "Agent Release" is
         (versioned immutable bundle, per OT context doc).
      2. **Prerequisites** — TB installed and running; OT
         router endpoints (TB-US-022 through TB-US-028)
         shipped; the operator has a Training-role account
         and at least one Super-role account.
      3. **Step-by-step walkthrough:**
         - Define the domain and its taxonomy
           (which of the four categories apply; are
           domain-specific categories wanted — if so, defer
           to a v0.3 follow-up)
         - Prepare source data (if applicable: documents for
           the RAG, structured JSON for lookup sources,
           calculator definitions for quantitative)
         - Configure lookup sources at
           `config/ot/lookup/<domain>.json`
         - Configure classifier rules (if domain-specific
           patterns help) at `config/ot/classifier-rules.json`
         - Register calculators (if any; most domains inherit
           math_basic + add their own)
         - (If training a content adapter:) curate training
           set via the SME workflow (TB-US-020) → run training
           (`POST /training/runs`) → export adapter → load
           adapter
         - Verify end-to-end: run a labeled query set
           through `/ot/query`, inspect the OT audit log,
           produce a verification report (follows the
           TB-US-029 pattern)
         - Package the Agent Release
         - Deploy and smoke-test
         - Rollback procedure if needed
      4. **Agent Release packaging** — what gets captured,
         where it lives on disk, how versioning works, how
         to produce the release artifact. v0.1 is manual
         (operator assembles components into a release
         directory + manifest); automation is a later story.
      5. **Troubleshooting** — common failure modes
         (classifier mis-routes, calculator doesn't extract,
         lookup source not found, RAG retrieval returns
         irrelevant chunks, adapter load fails) with
         diagnostic steps using the OT audit log.
      6. **Appendices**:
         - Full example: the math example (TB-US-029) as a
           reference agent
         - Vocabulary (links to the OT context doc)
         - Config file schemas

### Minimal tooling

- [ ] R2: **`scripts/release-agent.py`** (or similar) that
      helps the operator assemble an Agent Release:
      - Takes a release name + version
      - Reads a release manifest (what components, which
        versions)
      - Creates `releases/<name>-<version>/` directory
      - Copies / snapshots the specified components
      - Writes `MANIFEST.md` with metadata (date, versions,
        description)
      - Does NOT make the release live; deployment is a
        separate step
- [ ] R3: **`scripts/verify-agent.py`** (or similar) that
      runs a labeled query set against the OT router and
      produces a verification report — the same pattern
      as TB-US-029's runner, generalized so it works for
      any agent's `labeled-queries.jsonl`.
- [ ] R4: **Templates** at `templates/agent-skeleton/` for
      quick-start:
      - `config/ot/lookup/<domain>.json.example`
      - `config/ot/classifier-rules.json.example`
      - `labeled-queries.jsonl.example`
      - `MANIFEST.md.example`

### Example traced

- [ ] R5: **The math example (TB-US-029) is traced through
      the walkthrough** as a worked example — the operator
      can read the walkthrough's "math agent" subsection and
      see exactly what each step produced in the math case.

### Verification by review

- [ ] R6: **Operator (or another reviewer — Ted or Sam)
      reads the walkthrough front-to-back and attempts to
      produce a toy agent** (not a real deployment, just a
      stub). The reviewer notes any step that was unclear
      or incomplete; those get fixed before the story
      closes.

### No regression

- [ ] R7: **Documentation and tooling only.** No endpoint
      changes, no handler changes, no schema changes. If
      the walkthrough reveals a bug or missing capability in
      TB-US-023 through TB-US-029, open a follow-up story
      rather than widening this one.

## Acceptance Criteria

- [ ] AC1: `docs/training/build-and-deploy-agent.md` exists
      with all sections required by R1 populated with
      substantive content (not placeholders).
- [ ] AC2: `scripts/release-agent.py` exists and produces a
      valid release directory + manifest when given a
      sample input.
- [ ] AC3: `scripts/verify-agent.py` exists and reproduces
      TB-US-029's math verification when pointed at the
      math example's `labeled-queries.jsonl`.
- [ ] AC4: `templates/agent-skeleton/` exists with the four
      files required by R4.
- [ ] AC5: The walkthrough's "math agent" worked-example
      subsection cites TB-US-029 artifacts and is accurate
      against them (nothing out of date, no missing steps).
- [ ] AC6: A reviewer-run (R6) produces a toy agent per the
      walkthrough. Any unclear step is fixed in the doc
      before closure.
- [ ] AC7: `git diff backend/` is clean for this story
      (documentation + scripts only).
- [ ] AC8: `git diff` on the OT story files (TB-US-022
      through TB-US-029) is clean for this story (no
      modifications to upstream story files; this story
      consumes, doesn't change them).

## Design Notes

- **Documentation is the deliverable; tooling is
  supportive.** The walkthrough's job is to make the OT
  stack usable by a human. If the human can produce a
  working agent by reading the doc + copying from
  templates, the story has shipped. If the tooling makes
  that easier, good; if it adds complexity, drop it.
- **"Agent Release" is a manual ceremony at v0.1.** The OT
  context doc describes Agent Releases as immutable
  versioned bundles. v0.1 captures the components into a
  directory with a manifest. Automation (one-command
  release, release signing, release registry, rollback
  automation) is a later arc.
- **Why trace the math example in-place.** Reading a
  "how to" doc that abstracts over every step is harder
  than reading one that walks through a specific concrete
  case. Math (TB-US-029) is that concrete case for the
  walkthrough.
- **Templates aren't magic.** The template files are
  examples with placeholder content. The operator copies,
  renames, edits. No code-generation, no scaffolding
  framework. If future volume justifies something fancier,
  separate story.
- **Troubleshooting section is critical.** First-time
  users hit specific failure modes. Enumerating them with
  diagnostic steps (particularly: how to read the OT
  audit log for root cause) is the single most valuable
  section after the step-by-step walkthrough.
- **Why reviewer verification (R6).** Documentation always
  has unspoken assumptions; the author knows what the
  reader is supposed to know. A reader who doesn't know
  (Ted, Sam, future contributor) will trip over gaps the
  author can't see. One review pass catches most of them.
- **Rollback procedure matters.** An Agent Release that
  deployed something bad needs to be revertible. The
  walkthrough covers the manual rollback mechanics (keep
  the previous release directory; swap the symlink /
  config pointer; restart; verify).

## Out of Scope

- **Agent Release automation** beyond the manual-assembly
  script. One-command release, signed releases, release
  registry — all later stories.
- **Automated rollback** / deployment orchestration.
- **A UI for building / deploying agents.** CLI + manual
  edits are v0.1. UI is a follow-up if demand materializes.
- **Multi-agent coordination** (running several agents
  concurrently with routing between them). v0.1 is one
  agent per TB install.
- **Agent Release registry** (central index of all
  releases across TB installs). Separate concern.
- **Compliance / audit requirements** for agent releases
  (e.g., change-management approval). Separate concern.
- **A/B deployment** (traffic-split between agent
  versions). Separate concern.
- **Model fine-tuning as a step in the walkthrough.** The
  walkthrough references the existing SME + training
  workflow (TB-US-020, 019) but does not re-teach it.
- **Branding tweaks.**

## Related

- Parent: [TB-US-022](tb-us-022.md) — OT coordinator.
- Depends on: [TB-US-023](tb-us-023.md) through
  [TB-US-029](tb-us-029.md). This story can be drafted at
  any time but should not **close** until the upstream
  stories are Completed and TB-US-029's verification report
  exists for the walkthrough to reference.
- Builds on: [TB-US-020](tb-us-020.md) — the SME training
  workflow doc. This story references it for the "curate
  training data" step without duplicating that doc.
- Related: [TB-US-019](tb-us-019.md) — training set
  export is the shape the walkthrough uses for Agent
  Release component packaging.
- Deliverable: `docs/training/build-and-deploy-agent.md`
- Tooling: `scripts/release-agent.py`,
  `scripts/verify-agent.py`, `templates/agent-skeleton/`.
- Context: `docs/ot-context-for-claude-code_1.md` lines
  121–169 (Agent Release concept, research→deployment
  transition).
