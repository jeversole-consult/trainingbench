# TB-US-047: Spike — First-run / onboarding architecture

**Status**: Completed
**Created**: 2026-10-17
**Completed**: 2026-10-19
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

**Deliverable**: `docs/design/first-run-onboarding.md`

## Story

As the operator of TrainingBench AND as a stranger who's
about to install TB from GitHub, I want a formal design for
what a fresh install produces, how a new user bootstraps
their admin credentials securely, whether a default agent
is auto-created, and how first-login nudges the operator
toward productive next steps — so that someone unfamiliar
with TB can go from `git clone` to "logged in with my own
agent, documents loaded, first query running" without
having to read source code or guess defaults.

## Background

Operator design signal on 2026-10-17 after the two-tier
architecture decision landed in TB-US-044:

> *"i download a clean copy of training bench from github.
> what is the initial state of a fresh training bench
> install? does it have a default agent? what is the default
> admin account so that a user can stand up their own
> version of training bench and move from the default to
> their own agents. this workflow needs to be ironed out in
> order to provide guidance to new users to get started
> with the application."*

**Current fresh-install state problems** (documented in-full
in the deliverable's §2):

- Default admin credentials are `admin / changeme` (or env-
  configurable) — insecure for public OSS install
- `PASSWORD_SALT` and `SECRET_KEY` have hardcoded defaults —
  same security issue
- No agent concept exists (TB-US-044 design spike in flight)
- No in-app guidance for new users
- No "setup complete" state marker
- Changing password requires knowing the admin modal exists;
  nothing surfaces it on first login

**Scope relationship with other stories:**

- **TB-US-044** — Q13 (zero-agent / default-agent handling)
  folds into this story and gets its Decision line here.
- **TB-US-003** — Deferred security story for per-user salts.
  Adjacent to "fix default admin password weakness" but
  this spike doesn't execute hashing changes.
- **TB-US-004** — Proposed README quickstart. This spike's
  output informs what the quickstart tells the operator.
- **TB-US-005** — v0.1 release-cut. Having an acceptable
  first-run experience is a release gate.

## Requirements

### Deliverable

- [x] R1: **Design document at
      `docs/design/first-run-onboarding.md`** with the full
      first-run architecture captured. Not a code
      deliverable.
- [x] R2: **Current-state section** — what exists today on
      a fresh install (env vars, auto-created artifacts,
      startup log output, what the operator sees).
- [x] R3: **Problem enumeration** — what's wrong with the
      current state (security defaults, discovery, missing
      guidance, no setup-done marker).
- [x] R4: **Admin bootstrap design** — how a fresh TB
      install produces a secure admin account that the
      installer can actually use. Candidate: random
      password + first-login forced change.
- [x] R5: **Agent bootstrap design** — resolves TB-US-044
      Q13 (default agent on first run?). Captures the
      Decision line.
- [x] R6: **First-login UX design** — wizard, banner, or
      page-based onboarding; what fires once and dismisses;
      what persists.
- [x] R7: **Onboarding checklist** — the operator-facing
      "do these N things first" list and where it lives
      (in-app page vs README vs welcome banner).
- [x] R8: **Install-flow doc guidance** — what `INSTALL.md`
      and `README.md` need to say to match the new design.
      Not the actual docs — guidance on what they should
      cover.
- [x] R9: **Follow-up stories enumeration** — the TB-US-NN
      stories this spike unlocks (admin bootstrap
      implementation, default-agent creation on first run,
      first-login banner, getting-started page, etc.).
- [x] R10: **Open questions for operator decision** —
      pattern matches TB-US-043 and TB-US-044 (each
      question has context, options, my lean, Decision
      line).

### Process

- [x] R11: **Iterative, operator-collaborative drafting.**
      Same pattern as TB-US-043 and TB-US-044. Doc evolves
      across turns.
- [x] R12: **No code changes in this spike.** Deliverable
      is the doc. Execution waits for follow-up stories in
      R9.
- [x] R13: **TOC + anchors** matching the TB-US-043/044
      design doc pattern (`<a id="sec-N"></a>` + numbered
      TOC links).
- [x] R14: **Coordinate with TB-US-044** — any decision
      that touches the agent architecture (specifically
      default-agent handling) is mirrored into TB-US-044's
      Q13 Decision line + decision log.

## Acceptance Criteria

- [x] AC1: `docs/design/first-run-onboarding.md` exists
      with every section from R2-R10 populated to the
      operator's satisfaction.
- [x] AC2: At least one open question has an explicit
      operator **Decision:** line.
- [x] AC3: TB-US-044's Q13 Decision line is populated,
      referencing this story's resolution.
- [x] AC4: At least 3 follow-up stories identified (R9)
      with one-line scopes, covering: admin bootstrap
      implementation, default-agent creation on first run,
      first-login UX.
- [x] AC5: Operator confirms "the design is ready to
      execute against."
- [x] AC6: No code changes in this story (`git diff
      backend/` is empty).

## Design Notes

- **Spike shape, not coordinator.** Design-only; a single
  deliverable (the doc). Implementation lives in follow-up
  stories.
- **Why its own spike vs folding into TB-US-044.** First-
  run touches both tiers (admin bootstrap + agent bootstrap
  + onboarding UX), while TB-US-044 is specifically the
  agent-model spike. Giving first-run its own home keeps
  TB-US-044 focused and gives the install flow enough
  design space to breathe.
- **Why collaborative drafting.** Install experience is
  the first impression TB makes on a new user. Operator
  judgment on password-security tradeoffs, in-app vs doc
  guidance, auto-created-vs-explicit setup — all deserve
  operator input, not just my leans.
- **Install-time secrets.** The spike should capture how
  TB handles `SITE_PASSPHRASE`, `SECRET_KEY`,
  `PASSWORD_SALT`, `DEFAULT_ADMIN_*` env vars — which
  should be required, which auto-generated, which
  explicitly set.

## Out of Scope

- Implementing any part of the design (follow-up stories).
- Changes to TB-US-044's agent-model core (this spike
  consumes its decisions; doesn't modify them).
- Multi-tenant / multi-install coordination.
- Automated password-rotation / scheduled security audits.
- Email verification on first-user setup (would require
  SMTP config; defer).
- Billing / licensing flows (not relevant to OSS install).
- UI design beyond "where the surface lives" (actual pixel
  mockups out of scope).
- Branding tweaks (per deferred-branding memory).

## Related

- [TB-US-043](tb-us-043.md) — Sweet Spot methodology spike.
  First-run doesn't directly affect Sweet Spot design but
  the default agent is a Sweet Spot candidate.
- [TB-US-044](tb-us-044.md) — Agent architecture spike.
  **Q13 (zero-agent / default-agent handling) folds into
  this story**; this story's resolution of agent bootstrap
  populates TB-US-044's Q13 Decision.
- [TB-US-003](tb-us-003.md) — Per-user salts (Deferred).
  Adjacent to the admin-password-security concern this
  spike will raise.
- [TB-US-004](tb-us-004.md) — README quickstart (Proposed).
  Downstream of this spike.
- [TB-US-005](tb-us-005.md) — v0.1 release-cut (Proposed).
  Having an acceptable first-run flow is a gate.
- `MEMORY.md → feedback_coordinator_not_epic` — governs
  whether a coordinator spawns from this spike's follow-ups.
- `backend/api/user_manager.py` — current `_init_database`
  logic that creates the default admin user.
- `backend/api/main.py` — current env var consumption
  (SECRET_KEY, SITE_PASSPHRASE, DEFAULT_ADMIN_*).
- `INSTALL.md` — current install doc at the project root.
- Deliverable: `docs/design/first-run-onboarding.md`.

**Completion Notes (2026-10-19).**

**Design spike closed with all 12 open questions resolved.**

**Deliverable:** `docs/design/first-run-onboarding.md`
(~1500 lines) — comprehensive design covering first-run
flow, admin bootstrap, example-agent architecture, UX
layers, licensing, and 7 follow-up stories.

**Decisions reached (12 total across Q1-Q11):**

- **Q1** — Admin password: random on first boot; printed
  to stdout + chmod-600 file in `logs/`; `must_change_password`
  flag + forced-change page; env override preserved
- **Q2** — SECRET_KEY + PASSWORD_SALT: auto-generate on
  first boot; persist to `backend/db/.secrets` (JSON,
  chmod 600, gitignored); env > file > hardcoded
  precedence; existing-install migration copies
  hardcoded sentinels to file with warning
- **Q3 reframed** — Install ships ONE example agent
  (`math-example`) with a **measurable 3-stage
  progression** (bare LLM → +RAG → +adapter);
  pedagogy-driven; measured deltas visible in Compare on
  first open; replaces placeholder-"default" framing
- **Q3B** — One example at v0.1 (math); other domains
  deferred
- **Q3C** — Staged progression + GitHub Release artifact
  for the adapter + fallback behavior if adapter missing
- **Q3D** — Zero agents allowed after operator action
- **Q4** — Forced password change: hard block; minimum
  10 chars; only auto-generated admin flagged; no API
  bypass; mid-change interruption safely re-triggers
- **Q5** — Welcome banner: dismissable top banner;
  3 primary actions (Compare / Getting Started /
  Dismiss) + conditional Stage 2 adapter prompt;
  localStorage dismiss
- **Q6** — Dual-surface Getting Started: README.md + GitHub
  Pages site (not either/or); Jekyll + chosen theme; v0.1
  Pages scope = 2 pages (Home + Getting Started); no
  in-app `/static/getting-started.html`
- **Q7** — Phased checklist with Phase 3 forking into
  Track A (GPU) and Track B (non-GPU) + dedicated "What
  to expect from PEFT training" section
- **Q8** — INSTALL.md single source of truth with 8
  sections; Quickstart in README; 5 required OSS repo
  files at v0.1
- **Q9a** — SITE_PASSPHRASE unset = open access +
  startup warning; "pre-login access barrier against bot
  login attacks" vocabulary locked
- **Q9b** — `TB_PAGES_URL` env var with canonical default
- **Q9c** — Per-subsystem audit-log env vars preserved;
  consolidation deferred
- **Q10** — `must_change_password` flag alone as
  setup-done marker; no separate `setup_complete`
  boolean
- **Q11** — Shipped-artifact licensing: Apache 2.0 for
  EL-derivative artifacts (training set + adapter);
  honor source licenses on RAG seed documents;
  attribution + model-card files

**TB-US-044 Q13 resolved via this spike.** Cross-reference
captured in both docs.

**7 follow-up stories enumerated in deliverable §8:**

1. Admin password bootstrap implementation (blocking for
   secure OSS release)
2. SECRET_KEY + PASSWORD_SALT auto-generation
3. Shipped math-example seed on first run
4. Welcome banner implementation
5. GitHub Pages site setup (Jekyll + Home + Getting
   Started)
6. INSTALL.md + README restructure
7. Build + publish math-example staged progression
   artifacts (depends on TB-US-029 verification example
   + TB-US-030 operator workflow; produces licensing
   files per Q11)

**Minimum arc for v0.1 release:** stories 1, 3, 4, 6, 7.

**No code changes in this story.** Pure design spike.

**AC verifications:**

- AC1 ✓ Deliverable exists at
  `docs/design/first-run-onboarding.md` with all required
  sections (R2-R10) populated
- AC2 ✓ 12 open questions have explicit **Decision:**
  lines captured
- AC3 ✓ TB-US-044 Q13 Decision line populated with
  cross-reference to this spike
- AC4 ✓ 7 follow-up stories identified with one-line
  scopes (exceeds the "at least 3" bar)
- AC5 ✓ Operator confirmed ready-to-execute-against via
  "close TB-US-047"
- AC6 ✓ `git diff backend/` for this story: empty

**Downstream:**

- Each of the 7 follow-up stories is now draftable.
  Operator picks ordering + which to execute first.
- TB-US-005 (v0.1 release) gets 5 of these as release
  gates (minimum arc).
- TB-US-029, TB-US-030, TB-US-044 all have scope
  interactions captured in §4.8 of the deliverable;
  may need minor rework once their execution begins.
- TB-US-003 (per-user salts, Deferred) remains deferred;
  this spike's Q2 handles the transitional global-salt
  state until TB-US-003 is ready to reshape the hashing
  architecture.
