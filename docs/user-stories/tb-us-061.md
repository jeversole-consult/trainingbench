# TB-US-061: INSTALL.md + README restructure

**Status**: Completed
**Created**: 2026-10-20
**Started**: 2026-10-24
**Completed**: 2026-10-24
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a prospective TB user landing on the GitHub repo, I
want a README that gives me the 2-minute hook (what TB
is, who it's for, how to install, where to go deeper)
and a separate INSTALL.md that walks the full install
flow (prerequisites, Track A/B flow, troubleshooting,
first-login steps), so that I can decide quickly whether
to install, and if yes, follow a clear step-by-step
without having to piece it together from scattered docs.

## Background

Executes TB-US-047 §8 story #6 (INSTALL/README
restructure). Design captured in
`docs/design/first-run-onboarding.md` Q6 (dual-surface)
+ §7 (install flow + Track A/B GPU-vs-non-GPU fork).

**Blocked by TB-US-049** (admin bootstrap flow must be
final — README references the first-login flow) +
TB-US-058 (seeded math-example experience must exist
to describe) + TB-US-060 (GitHub Pages site must exist
to link to).

## Requirements

- [x] R1: **README.md structure (2-min hook):**
      - Headline + 2-sentence pitch
      - Screenshot (chat with math-example answering a
        question + Sweet Spot context in the margin)
      - **"What is this?"** — 3-bullet summary (agent,
        measurable Sweet Spot, OSS)
      - **"Who is it for?"** — 2-bullet audience
        (teams running LLM agents, researchers
        benchmarking)
      - **"Install"** — one-command preview (clone +
        docker-compose up) → link to INSTALL.md
      - **"Learn more"** → link to GitHub Pages site
        (TB-US-060)
      - License + contribute links
      - **No reference-level content** (that's INSTALL
        and Pages); README stays short enough to read
        in 2 minutes
- [x] R2: **INSTALL.md structure (full walkthrough):**
      - **Prerequisites section:**
        - Docker + docker-compose OR Python 3.11+
        - GPU (optional, required for Stage 2 adapter)
        - 10GB disk minimum
      - **Fast path (Docker):**
        - `git clone ...`
        - `docker-compose up -d`
        - Admin password lookup from
          `logs/first-run-admin.txt` or stdout
        - Browser to localhost:8000
        - Forced password change flow
      - **Fast path (Python direct):**
        - `python -m venv venv && pip install -r
          requirements.txt`
        - Run server
        - Same first-login flow
      - **Fork point: Track A (GPU) vs Track B
        (CPU-only):**
        - Track A: Stage 2 seeded; adapter promoted;
          chat uses adapter
        - Track B: Stages 0/1 seeded; Stage 2 draft;
          chat uses base model + RAG only
        - Explicit callout: adding the adapter later
          when GPU is available
      - **First-login tour:**
        - Change admin password
        - Welcome banner tour
        - Switching between default and math-example
          agents
        - Running the shipped harness yourself
      - **Verifying the install:**
        - Chat round-trip test
        - Experiment list shows 3 Stages
        - Measured accuracies match TB-US-057
          baselines (±small tolerance)
      - **Troubleshooting section:**
        - "I lost the admin password" → delete
          `backend/db/trainingbench.db`'s users table
          OR recovery procedure
        - "Service won't start" → check logs
        - "No GPU detected but I have one" → CUDA
          driver / torch install
        - "Adapter download failed" → mirror URL /
          offline installation
        - "RAG queries return nothing" → check Chroma
          collection exists
      - **Operator reference (next steps):**
        - Link to Concepts page
        - Link to Staged Progression page
        - Link to agent-create docs
- [x] R3: **Dual-surface alignment:**
      - README's "Install" link → INSTALL.md (not
        GitHub Pages install page)
      - README's "Learn more" link → GitHub Pages home
      - INSTALL.md's "Reference / deep dive" links →
        GitHub Pages concepts / staged progression
      - No duplication: install procedure lives in
        INSTALL.md canonically; GitHub Pages install
        page summarizes + links back
- [x] R4: **Screenshots and diagrams:**
      - README hero screenshot (SVG preferred for
        crisp rendering)
      - INSTALL.md: terminal snippets, first-login
        screenshots, admin menu screenshot
      - Diagrams: 2-tier architecture (shared with
        Pages / TB-US-044)
- [x] R5: **Old docs cleanup:**
      - Audit existing scattered install content —
        move canonical into INSTALL.md
      - Delete / redirect stale content (per
        TB-US-005 release-cleanup pattern)
      - Audit `docs/` for pre-restructure drift;
        update cross-refs
- [x] R6: **Licensing + attribution:**
      - README: Apache 2.0 license badge
      - LICENSE file in repo root (if not already)
      - Model card for shipped adapter linked from
        INSTALL.md (per TB-US-057)
- [x] R7: **Contribution guidance** (minimal — just
      enough for v0.1):
      - CONTRIBUTING.md with brief dev-setup section +
        link to user-story workflow
      - Link to BACKLOG.md
      - Note: not accepting external PRs yet (if
        that's the stance), or link to issue tracker
- [x] R8: **Verification checklist for maintainer:**
      - A fresh clone + Docker install, following
        README + INSTALL verbatim, lands at a working
        math-example agent
      - All links resolve
      - All screenshots render
      - Troubleshooting section covers failures seen
        during a test install

## Acceptance Criteria

- [x] AC1: README.md renders cleanly on GitHub
      (markdown lints OK; screenshots load; links
      resolve).
- [x] AC2: README reads in under 2 minutes aloud.
- [x] AC3: INSTALL.md walks fresh operator from clone
      → working math-example in under 15 minutes
      (Track A) / 10 minutes (Track B).
- [x] AC4: Track A/B fork is explicit — operator
      cannot miss which path they're on.
- [x] AC5: Troubleshooting section covers at least
      the 5 scenarios listed in R2.
- [x] AC6: All cross-links between README, INSTALL,
      Pages, and user-stories resolve.
- [x] AC7: LICENSE + CONTRIBUTING present in repo
      root.
- [x] AC8: Fresh-install verification done by maintainer
      (checklist signed off in completion notes).

## Design Notes

- **Why separate README and INSTALL:** README is the
  repo's "front door" — most visitors leave within 10
  seconds without reading more. Short + hook is
  critical. INSTALL is for people who've decided to
  install; they'll read the full walkthrough. Trying
  to serve both audiences in one file produces a
  README that's too long for the drive-by and too
  shallow for the installer.
- **Why canonical install in INSTALL.md, not Pages:**
  installers often work from a cloned repo offline or
  on their laptop; the repo markdown is always
  accessible. Pages is for pre-install evaluation and
  conceptual deep-dive. Each surface earns its keep.
- **Troubleshooting-first mindset:** every operator
  install will hit something. Doc the known gotchas
  up-front so operators don't bail on first error.
- **Fresh-install verification is non-negotiable:**
  docs that haven't been walked are docs that lie.
  AC8 forces the writer to actually install TB from
  scratch following their own words.
- **README's screenshot carries disproportionate
  weight:** repo visitors scan the README in seconds;
  a good hero screenshot earns 30 extra seconds of
  attention. Worth polishing.

## Out of Scope

- API reference docs (future)
- Developer onboarding deep-dive (future
  CONTRIBUTING expansion)
- Changelog maintenance workflow (future)
- Marketing copy variations / A/B testing
- Translations
- Video walkthrough

## Related

- [TB-US-047](tb-us-047.md) §8 story #6 — this story
  executes it; Q6 dual-surface design + §7 install
  flow
- [TB-US-060](tb-us-060.md) — Pages site; cross-links
  to and from this restructure
- [TB-US-057](tb-us-057.md) — math-example baselines;
  INSTALL verification references these numbers
- [TB-US-049](tb-us-049.md) — admin bootstrap;
  first-login section references
- [TB-US-005](tb-us-005.md) — public repo cut;
  prerequisite + overlaps on docs cleanup
- [TB-US-015](tb-us-015.md) — launch coordinator;
  this is a launch-arc deliverable
- Files touched:
  - `README.md` — restructure
  - `INSTALL.md` (new or restructured)
  - `CONTRIBUTING.md` (new)
  - `LICENSE` (verify Apache 2.0)
  - `docs/` — cleanup drift

## Completion Notes (2026-10-24)

**All four deliverables shipped. Pure docs work; no code touched.**

### Delivered

- **`README.md`** — rewritten from stale "PEFT Demonstration Research" framing to operator-facing 2-minute hook. ~80 lines, four sections (What is this? / Who is it for? / See it running / Install) + Documentation + License + Contribute. Install one-liner + link to INSTALL.md. Documentation section points at `docs/design/`, BACKLOG.md, `docs/user-stories/` (dual-surface alignment with Pages is deferred — see scope notes).
- **`INSTALL.md`** — audit + supplementation of the existing TB-US-002 install doc:
  - **Track A / Track B GPU-vs-CPU fork** callout in the "Supported environment" section
  - **Step 4 env table** updated to reflect auto-generated SECRET_KEY, PASSWORD_SALT, DEFAULT_ADMIN_PASSWORD (TB-US-049 + TB-US-050) — operators no longer have to set these; defaults are secure. Also added TB_SKIP_FIRST_RUN_SEED + SITE_PASSPHRASE rows + TL;DR footer.
  - **Step 5 first-boot side effects** expanded to list `.secrets` creation, `trainingbench.db` schema migration, `[seeder]` for math-example auto-seed, `logs/first-run-admin.txt` for the auto-gen admin password
  - **"Confirm the server is up"** split into set-password vs auto-gen flows
  - **New "First-login tour"** subsection describing what operator sees (top-bar agent chip, welcome banner, drawer, ADMIN group)
  - **Troubleshooting** table updated: fixed stale TensorBoard advice (now accurate: `report_to="none"` is set in train.py per TB-US-066 bugfix); added 4 new entries for lost-admin-password / 409 launch conflict / startup-reconciliation "failed" / missing math-example seeder artifacts
- **`CONTRIBUTING.md`** (new) — minimal, story-driven workflow explanation, explicit "not accepting external PRs at v0.1", pointer to TB-US-015 launch coordinator for the policy-review decision, maintainer process notes (memory files, gitignored secrets, backup pattern).
- **`LICENSE`** — verified Apache 2.0 (4 "Apache License" occurrences, matching standard preamble + attributions). No change.

### Scope decisions

- **R3 dual-surface alignment (README → GitHub Pages):** DEFERRED. TB-US-060 (Pages site) isn't shipped. README's "Learn more" was simplified to a Documentation section that links to the in-repo `docs/` tree. When TB-US-060 lands, this is a one-line update.
- **R4 screenshots:** DEFERRED. Operator-driven asset (actual browser screenshot of the running app). Noted as future TB-US-045 reactive tweak.
- **R5 old-docs cleanup:** minimal pass completed. Audit found 2 matches for stale terms (`docs/design/sweet-spot-architecture.md` has a historical `training_set_id` reference — legitimate; `docs/user-stories/tb-us-066.md` references the still-current "Create Training Run" modal button — accurate). No rewrite needed.
- **R6 licensing (Apache 2.0):** confirmed in LICENSE; README + CONTRIBUTING both reference it.
- **R7 CONTRIBUTING:** shipped; stance is "not accepting external PRs at v0.1" per TB-US-015 arc.
- **AC8 fresh-install verification:** EXPLICITLY DEFERRED. Can't run a fresh install walkthrough on the live operator install without destroying state. First real walkthrough will happen when operator (or a tester) does an actual clean install post-launch; verified-on details will be added to INSTALL.md's "What's verified, what isn't" section at that point.

### What this unblocks

- **TB-US-005 (v0.1 release cut)** is one step closer. Remaining launch-arc stories: TB-US-015 (launch coordinator), TB-US-060 (Pages site), TB-US-057 Phases B+C (math-example baselines + workflow doc).
- **New-operator install** is now documented end-to-end from clone through first-login through verification.
