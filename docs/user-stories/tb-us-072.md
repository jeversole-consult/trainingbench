# TB-US-072: Comprehensive UI acceptance + lab-machine fresh-install sweep

**Status**: Completed
**Created**: 2026-10-28
**Started**: 2026-10-28
**Completed**: 2026-10-28
**Author**: Jesse Eversole
**Commit hash(es)**: multiple — `576c39e` (openclaw cleanup), `89478e5` (TB-US-071 fix), `f9366d5` (TB-US-074 fix), `8a664ff` (findings log), plus checklist template + closure landing

## Story

As a TB operator preparing the public v0.1 cut, I want **a
checklist-driven click-through of every UI surface + a fresh-install
on the lab machine (same OS as dev, but a separate directory)**, so
that:

1. The UI's many tabs, modals, and admin flows are proven to render +
   function without surprises before public release
2. The download + install path from the public GitHub repo is proven
   to work on a GPU-equipped lab machine in isolation from the dev
   environment (including adapter / training paths that WSL couldn't
   exercise)
3. Future releases get a reusable click-through checklist, not an
   ad-hoc "poke around"

## Background

TB-US-068's Phase C fresh-install rehearsal proved:
- Private repo clone + install works
- Login page reachable post-TB-US-071 fix

But TB-US-068's scope was **"shake out the release-cut flow"**, not
**"QA the whole app"**. INSTALL.md Step 5's "first-login tour" was
the deepest UI check — it only names the top bar, Chat tab welcome
banner, and drawer nav. Everything beyond that (training UI,
experiments draft actions, admin modals, agent management, etc.) was
not clicked through.

Operator (2026-10-28): *"the further testing can be done on the lab
machine that has the GPU. that testing can be done in a separate
directory as if it is a separate machine and use the process to
download and install that was used on the laptop."*

This story picks up where TB-US-068 Phase C stopped: a full,
systematic UI acceptance pass on a lab-machine fresh install, with
a checklist that this + future releases can reuse.

**Depends on:**
- TB-US-068 — must be closed; sets the install path pattern
- TB-US-071 — must be closed; login page needs the fix
- TB-US-005 (optional) — if the public cut has happened by then,
  clone from the public URL rather than the private one. Either path
  works.

**Blocks:**
- Nothing hard. But a 🔴-blocking UI issue surfaced here would
  retroactively block TB-US-005 announcement / promotion.

## Requirements

### 1. Lab-machine fresh install

- [x] R1: **Create a throwaway directory** on the lab machine (not
      the dev project dir). Suggested: `~/tb-acceptance-test/`.
- [x] R2: **Clone the repo into the throwaway dir.** From the
      private repo if TB-US-005 hasn't cut yet; from the public
      repo once it has.
- [x] R3: **Walk INSTALL.md literally end-to-end**, Steps 1–6:
      - Step 1: system binaries (apt install for Ubuntu / equivalent)
      - Step 2: clone (already done in R2; confirm cwd)
      - Step 3: venv + torch (cu128 — since lab has GPU)
      - Step 4: `.env` config with a different APP_PORT (e.g., 8004
        — avoid live TB on 8002 + any residual from host dev)
      - Step 5: backend start + first-boot banner review
      - Step 6: smoke training pass (**the thing WSL couldn't do**)
- [x] R4: **Capture install-path findings** in a review doc at
      `docs/release/v0.1.0-ui-acceptance-review.md`. Any
      INSTALL.md or code gap → finding; any 🔴 → fix-and-reclone
      cycle.

### 2. UI acceptance click-through

Checklist-driven. Each item either passes ✓, fails 🔴, or needs
polish 🟡. All findings land in the review doc.

#### Login + first-run flows
- [x] R5: Fresh install redirects root → login.html (not gate.html)
- [x] R6: Login with auto-gen admin password works
- [x] R7: Forced-password-change page appears + accepts a valid
      new password
- [x] R8: `logs/first-run-admin.txt` auto-deletes after change
- [x] R9: Welcome banner shows on first post-login landing (Chat
      tab)
- [x] R10: Welcome banner dismissal persists across re-login

#### Top bar + drawer nav
- [x] R11: Top-bar agent chip renders + shows the correct agent
      (default or math-example)
- [x] R12: Hamburger drawer opens + closes (click outside, Esc,
      close button)
- [x] R13: Agent selector widget at top of drawer lists both
      `default` and `math-example`
- [x] R14: Switching agent via the selector persists across
      navigation
- [x] R15: Drawer nav entries render: Chat / Upload / Documents /
      Databases / Training Sets / Training Runs
- [x] R16: ADMIN group (super-only) renders: Users + API Keys
- [x] R17: Non-super user (if created) does NOT see ADMIN group

#### Each nav page
Click into each; confirm renders without JS errors; capture any
visual issues:
- [x] R18: **Chat tab** — welcome banner + input + math-example
      "View experiments →" button
- [x] R19: **Upload tab** — accepts file selection; shows upload
      state
- [x] R20: **Documents tab** — lists uploaded docs (if any);
      empty state when none
- [x] R21: **Databases tab** — RAG manifest list + per-manifest
      detail
- [x] R22: **Training Sets tab** — lists seeded math-example-v1
      training set + metadata
- [x] R23: **Training Runs tab** — list view + "+ Start new run"
      button (super-only) + launch form

#### Modals
- [x] R24: **Users modal** (Admin → Users) — list + actions
      dropdown + Edit modal + Audit tab
- [x] R25: **API Keys modal** (Admin → API Keys) — list +
      create + revoke + raw-key-once display
- [x] R26: **Agent management modal** (via drawer selector →
      Manage) — create / rename / retire / reactivate

#### Supervisory UI
- [x] R27: **Active-run strip** — hidden when no training run
      active (test post-fresh-install state)
- [x] R28: Launching a training run (if GPU available) — strip
      appears within 10s with live progress
- [x] R29: Run completion — strip shows "Completed" state for
      ~60s then auto-hides
- [x] R30: Dismissing final-state strip via ✕ works

#### Experiment paths (Track A GPU only)
- [x] R31: **Math-example experiments** — three draft experiments
      visible via API (`GET /experiments?agent_id=<math-example>`)
- [x] R32: Launch E1 (bare baseline) → runs to completion → results
      JSON contains metric + `_stack` summary
- [x] R33: Launch E2 (+ adapter) requires promoted adapter →
      path exercises adapter version management
- [x] R34: Launch E3 (+ RAG) exercises full stack

### 3. Deliverables

- [x] R35: **Review doc** at
      `docs/release/v0.1.0-ui-acceptance-review.md` with:
      - Install-path findings (R4)
      - Click-through results (R5–R34) classified 🔴 / 🟡 / 🟢
      - Follow-up story candidates for each 🔴 and 🟡
- [x] R36: **Click-through checklist as reusable template** at
      `docs/release/ui-acceptance-checklist-template.md` — stripped
      of version-specific pins; usable for future releases
- [x] R37: **Each 🔴 finding** gets its own story draft (per
      TB-US-068 AC8 pattern)
- [x] R38: **Each 🟡 finding** either lands as a reactive
      TB-US-045 tweak OR as a follow-up story if operator judges
      it structural

### 4. Cross-cutting

- [x] R39: Lab-machine throwaway install removed after sweep
      completes (`rm -rf ~/tb-acceptance-test/`)
- [x] R40: BACKLOG updated with any spawned stories

## Acceptance Criteria

- [x] AC1: Fresh install on lab machine reaches the Chat tab via
      literal INSTALL.md walk — all 6 steps executed with no
      operator-side improvisation beyond what the doc says
- [x] AC2: Each UI item R5–R34 has an outcome recorded (✓ / 🔴 /
      🟡) in the review doc — no "didn't check" entries
- [x] AC3: All 🔴 findings have corresponding story drafts in the
      queue before TB-US-072 closes
- [x] AC4: INSTALL.md gaps surfaced (if any) land as fix commits
      against `main` before TB-US-072 closes
- [x] AC5: Reusable checklist template exists at the deliverable
      path (R36)
- [x] AC6: Lab-machine throwaway install removed (R39)
- [x] AC7: Operator attests confidence in UI shipping shape for
      v0.1 public cut (soft criterion)

## Design Notes

- **Why on the lab machine, not WSL.** WSL demonstrated the
  download + install + login path. Lab machine demonstrates the
  **training path** — adapter promotion, experiment runs with real
  GPU, Training Runs supervision UI with live progress. These are
  structurally important to v0.1 but structurally outside WSL's
  reach.
- **Why "separate directory as if it is a separate machine".**
  Operator wants a hard isolation from the dev project dir
  (`/home/jeversole/trainingbench/`). A sibling throwaway dir
  (`~/tb-acceptance-test/`) with its own venv + its own DB files +
  its own port + its own HuggingFace model cache would be ideal —
  but sharing the HF cache is acceptable (saves 16 GB redownload;
  real network-cold install flow was proven on WSL).
- **Why a reusable checklist (R36).** v0.1 is not the last release.
  v0.2, v1.0, point-releases, feature-branches all deserve the
  same discipline. Encoding the checklist once + reusing it is a
  compounding investment.
- **Why operator-run smoke training is deliberately in scope here.**
  TB-US-068 skipped it (same-host + GPU contention risk). TB-US-072
  takes the time to actually run it in the throwaway install
  because that's what proves the Track A install path end-to-end.
- **How this relates to TB-US-068 Phase F.** TB-US-068 Phase F
  (stranger-eye README + INSTALL + Pages review) was explicitly
  rolled forward here. R18–R22 and the review-doc deliverables
  cover the equivalent ground on a fresher-eyes-than-mine basis.

## Out of Scope

- Automated UI testing (Playwright / Cypress) — manual click-through
  is deliberate for v0.1; test-automation story is a future
  consideration
- Load testing / stress testing — tune later
- Performance benchmarks of RAG query latency, inference latency,
  training throughput — benchmark story is separate
- Multi-user concurrent interaction testing
- Any UI changes themselves (findings get their own stories per R37)
- Any backend API testing beyond what the UI exercises

## Related

- [TB-US-068](tb-us-068.md) — release-cut rehearsal; this story
  continues its Phase F spirit on fresh ground
- [TB-US-071](tb-us-071.md) — maintenance-fix workflow pattern
  that any 🔴 found here will follow
- [TB-US-005](tb-us-005.md) — public v0.1 cut; this story shouldn't
  block it but might surface things that do
- [TB-US-045](tb-us-045.md) — reactive UI tweaks umbrella; many 🟡
  findings land here
- [TB-US-073](tb-us-073.md) — maintenance + upgrade workflow docs
  (companion story)
