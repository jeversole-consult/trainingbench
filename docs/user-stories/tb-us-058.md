# TB-US-058: Shipped math-example seed on first run

**Status**: Proposed
**Created**: 2026-10-20
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As an operator installing TB fresh, I want the shipped
math-example agent to be seeded automatically on first
boot (with its training set, RAG, prompt, adapter if
GPU, harness, and three completed Stage 0/1/2
experiments), so that I can see a working agent
immediately — demonstrating the Sweet Spot concept via
measurable deltas — without configuring anything.

## Background

Executes TB-US-047 §8 story #3 (shipped math-example
seed on first run). Design captured in
`docs/design/first-run-onboarding.md` §5 (first-run
seeder) + §6 (welcome banner conditional prompts).

Pedagogical install goal (TB-US-047 Q3 reframe): the
install itself teaches the agent / Sweet Spot concept
by shipping a working, measured example — not by
asking the operator to read docs first.

**Blocked by TB-US-057** (artifacts must exist) + the
versioned-component machinery (TB-US-051 through
TB-US-056) + TB-US-048 (agent CRUD).

## Requirements

- [ ] R1: **First-run detection:**
      - On startup, check `agents` table for any agent
        with name `math-example`
      - If present: skip seeding (already done or
        operator removed it intentionally — don't fight
        them)
      - If absent AND bundled artifacts present: run
        seeder
      - If absent AND artifacts absent: log + skip
- [ ] R2: **GPU detection:**
      - Detect CUDA availability via torch
      - **Track A (GPU present):** seed all three
        stages including Stage 2 (adapter promoted)
      - **Track B (no GPU):** seed Stages 0 and 1 only;
        Stage 2 draft left with a note "requires GPU"
- [ ] R3: **Seeder actions (idempotent):**
      - Create `math-example` agent via TB-US-048 /agents
        endpoint
      - Load training set JSONL → create training set
        v1, released + promoted
      - Load RAG seed corpus → ingest into Chroma →
        create RAG v1, released + promoted
      - Load prompt text → create prompt v1, released
        + promoted
      - Load adapter files (if Track A) → create adapter
        v1, released + promoted
      - Load harness JSONL → create harness v1, released
      - Create 3 experiments with the measured baselines
        from TB-US-057 R6:
        - Stage 0: `math-example-stage0-bare`,
          state=completed, results = Stage 0 baseline
        - Stage 1: `math-example-stage1-rag`,
          state=completed, results = Stage 1 baseline
        - Stage 2: `math-example-stage2-adapter`,
          state=completed (Track A) or state=draft
          (Track B), results = Stage 2 baseline (Track A)
- [ ] R4: **Progress reporting:** seeder emits startup
      log lines showing progress:
      ```
      [first-run-seeder] agent math-example created (id=2)
      [first-run-seeder] training set v1 loaded (123 samples)
      [first-run-seeder] RAG v1 ingested (45 docs, 234 chunks)
      [first-run-seeder] prompt v1 loaded (420 chars)
      [first-run-seeder] GPU detected; loading adapter v1
      [first-run-seeder] adapter v1 loaded + promoted
      [first-run-seeder] harness v1 loaded
      [first-run-seeder] 3 experiments seeded with baselines
      [first-run-seeder] done in 42s
      ```
      Non-trivial time budget acceptable (seconds, not
      instant) — RAG ingestion dominates.
- [ ] R5: **Default agent handling:**
      - Keep the migration-time `default` agent (TB-US-051)
      - After seeding, make `math-example` the
        currently-selected agent for the first login
        (default-agent-at-first-login config)
      - Operator can switch to `default` or create new
        via TB-US-048
- [ ] R6: **Failure recovery:**
      - If any step fails: log the error, roll back
        partial state (delete the half-created agent +
        components)
      - Mark seeder as "failed" in a flag file so it
        doesn't retry indefinitely; operator can
        delete the flag to retry
- [ ] R7: **Opt-out:**
      - Env var `TB_SKIP_FIRST_RUN_SEED=1` disables
        seeding entirely
      - Documented in INSTALL.md for operators who
        want a clean slate
- [ ] R8: **Admin audit logging** — seeder's actions
      recorded in `admin_audit` with user=`system`
      and action=`first_run_seed`.

## Acceptance Criteria

- [ ] AC1: Fresh install Track A (GPU) → all 3 stages
      seeded; agent list shows `default` +
      `math-example`; math-example is pre-selected on
      first login.
- [ ] AC2: Fresh install Track B (no GPU) → Stages 0
      and 1 seeded; Stage 2 experiment is in state=draft
      with a note; no adapter promoted.
- [ ] AC3: Second startup → seeder is no-op (agent
      already exists).
- [ ] AC4: `TB_SKIP_FIRST_RUN_SEED=1` + fresh install
      → no seeding; only `default` agent in list.
- [ ] AC5: Operator deletes math-example agent (via
      TB-US-048) → next startup does NOT re-seed
      (operator intent respected).
- [ ] AC6: Simulate seeder failure mid-flight →
      rollback leaves no half-created agent; flag file
      prevents retry; operator can clear flag to re-try.
- [ ] AC7: Chat round-trip against math-example agent
      works end-to-end on first login.
- [ ] AC8: Admin audit log shows one `first_run_seed`
      entry.

## Design Notes

- **Why detection-by-name** rather than a separate
  "first run complete" flag: operator deleting the
  agent is a meaningful signal ("I don't want this");
  re-seeding would be hostile. Name check is clean.
- **Why non-trivial seed time is OK:** first-boot is
  a one-time cost. 30-60s of RAG ingestion is a small
  price for a working demo immediately. Startup log
  tells operator what's happening.
- **Default-agent-at-first-login** is a small UX win —
  the operator lands on a working agent, not an empty
  one. Reduces "I logged in, now what?" friction.
- **Rollback-on-failure matters** because a half-seeded
  agent (e.g., prompt set but adapter failed to load)
  would be a confusing broken state. All-or-nothing
  is simpler to reason about.
- **Opt-out exists** for CI, dev loops, and operators
  who want to build from scratch. Documented, not
  hidden.

## Out of Scope

- Multiple shipped agents (just math-example for v0.1)
- Interactive seeder (seeder is non-interactive;
  operator sees results post-login)
- UI for re-running seeder (deletion + flag-clear is
  the manual path)
- Scheduling / lazy-loading of experiments (all
  pre-computed baselines seeded)

## Related

- [TB-US-047](tb-us-047.md) §8 story #3 — this story
  executes it; §5 seeder design + Q3B staged progression
- [TB-US-057](tb-us-057.md) — artifacts; prerequisite
- [TB-US-048](tb-us-048.md) — agent editor; seeder
  uses /agents endpoint
- [TB-US-051](tb-us-051.md) through [TB-US-056](tb-us-056.md)
  — versioned components; prerequisite
- [TB-US-059](tb-us-059.md) — welcome banner; references
  the seeded experiments
- Files touched:
  - `backend/api/first_run_seeder.py` (extended from
    TB-US-057 stub)
  - `backend/api/main.py` — call seeder at startup
    (after migrations, after admin bootstrap)
