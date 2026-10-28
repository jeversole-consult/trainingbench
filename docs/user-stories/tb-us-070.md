# TB-US-070: Experiments UI — active-experiment strip + minimal supervision

**Status**: Proposed
**Created**: 2026-10-25
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a TB operator, I want **the moment I log in** to see
whether an experiment is running and what status it's at
(label, elapsed time, progress) — plus a minimal
supervision view (list, basic detail, archive) — so that
I can start an experiment via the API or a future
launcher, close the browser, come back later, and
immediately understand what's happening on the GPU.

## Background

The visibility gap exposed during TB-US-057 Phase B
execution (2026-10-25). While supervising three
sequential 200-sample experiments against the math-example
agent, the only ways to see progress were:

- `curl -H "Authorization: Bearer $TOKEN" /experiments/{id}` from the shell
- `nvidia-smi` to confirm the GPU was still active

TB-US-066 shipped the equivalent for **training runs** —
sticky top-of-page strip polling `/training/runs?status=running`.
The "View experiments →" button on the math-example card
alerts *"Experiment viewer ships with the next release.
For now, use the API: GET /experiments?agent_id=…"*
(`static/script.js:1202`) — that deferral is this story.

This is **not** a Sweet Spot promotion UI (TB-US-071
territory if that lands). This is just an "is anything
running / what did it do / what did I pin" minimal view
analogous to what TB-US-066 did for training.

**Depends on:**
- TB-US-048 — Agent CRUD (list experiments by agent)
- TB-US-057 Phase A — Experiment manager + seeded math-example
- TB-US-069 — `_build_experiment_stack` writing `_stack` summary
  into `results_json`
- TB-US-066 — Active-run strip pattern + CSS tokens to copy

**Blocks:**
- TB-US-005 — Public v0.1 release cut (nice-to-have, not strict)

## Requirements

### 1. Active-experiment strip (primary feature)

- [ ] R1: **Element** `#tb-active-experiment-strip` injected
      into the header on all pages where TB-US-066's
      `#tb-active-run-strip` is injected (index.html,
      training_sets.html, training_runs.html). Can share
      the same injection point in `left_nav.js` (two
      stacked strips when both run types are active).
- [ ] R2: **Visibility** — hidden by default; appears
      when `GET /experiments?state=running` returns a
      non-empty list. (Requires backend R18.)
- [ ] R3: **Content**:
      ```
      🧪 Experiment running: {label}
         Agent {agent_label} · Elapsed {HH:MM:SS}      [View →]
      ```
      "View" links to `/static/experiments.html#experiment/{id}`.
- [ ] R4: **Polling** — strip polls `GET /experiments?state=running`
      every **10 seconds** when visible. When no active
      experiment, polling continues at the same cadence
      so a newly-started one becomes visible within 10s.
- [ ] R5: **Styling** — amber-accented banner matching
      TB-US-066's active-run strip, with a flask (🧪)
      icon to distinguish it visually from training's
      gear (⚙️). Pulsing border to signal "live".
      Super-only.
- [ ] R6: **State transitions:**
      - State flips to `completed` → strip shows final
        state for 60s with final metric value, then
        disappears
      - State flips to `archived` (error path) → strip
        shows "Archived — see detail for error" for 60s
      - Operator can dismiss the final-state strip via ✕

### 2. Experiments page — list view

- [ ] R7: **New page `static/experiments.html`.** Static
      shell + list + detail view. Rip off `training_runs.html`
      structurally.
- [ ] R8: **List view** of experiments (newest first).
      Columns:
      - Label
      - Agent (via `experiments.agent_id`)
      - State badge: `draft` (grey), `running` (amber),
        `completed` (green), `promoted` (dark green),
        `displaced` (grey), `archived` (red)
      - Pins (compact summary): `adapter v2 · rag v3 · prompt v3`
      - Final metric (when completed): `accuracy=0.47`
      - Started / elapsed (for running) OR duration (for
        completed)
      - Action: `View →` link to detail
- [ ] R9: **Agent filter dropdown** at top of list.
      Default: show all. Operator can filter to one
      agent.
- [ ] R10: **No launch button in v0.1.** Experiments are
      created via API or seeder today; a launch form
      ships in a later story (likely alongside Sweet Spot
      selection UI).
- [ ] R11: **Fix the alert on math-example card**:
      `static/script.js:1202` currently alerts
      "Experiment viewer ships with the next release".
      Rewire the button to `/static/experiments.html?agent_id={id}`.

### 3. Detail view

- [ ] R12: **Routable** via `#experiment/{id}` hash in URL.
      Operator can bookmark + resume after logout.
- [ ] R13: **Panels** (no chart in v0.1):
      - **Header**: label + state badge + started /
        elapsed-or-duration
      - **Pins panel**: adapter version (link to adapter
        version detail), RAG version (link), prompt
        version (link), system prompt (collapsed body),
        base LLM identifier, harness version + config
      - **Live progress panel** (when `running`): sample
        X of N, running accuracy if the harness emits it,
        VRAM headroom. Updates every 5s. (Requires
        backend R19.)
      - **Results panel** (when `completed`): final
        metric value, correct / total, per-sample
        timings if available, `_stack` summary verbatim
        (JSON pretty-printed)
      - **Error panel** (when `archived`): error message +
        traceback snippet
      - **Lineage**: parent experiment link + list of
        children (via `parent_experiment_id`)
      - **Actions**: `Archive` button (super-only; when
        state ∈ {`draft`, `completed`}). Promote /
        displace actions **deferred** to Sweet Spot story.
- [ ] R14: **Polling cadence** — 5s active, 60s otherwise.
      Cancellable `setInterval` cleaned up on navigation.

### 4. Backend prerequisites

- [ ] R15: **`started_at` column** added to `experiments`
      table (nullable). `transition_state(…, "running")`
      writes it; existing rows stay NULL. Timestamp
      exposed via `GET /experiments/{id}`.
- [ ] R16: **Elapsed time derivation** — strip + list
      derive `now - started_at` for `running` rows.
      Completed rows show `completed_at - started_at`.
- [ ] R17: **`GET /experiments?state=X` filter.** Add
      `state` query parameter (reuses existing endpoint).
      Validates against the state enum; invalid → 400.
      Default (no param) = all states.
- [ ] R18: **Progress heartbeat (optional).** Harness
      runner writes `progress_json` (new nullable column)
      every N samples (default N=5) with
      `{current_sample: int, total_samples: int,
      running_correct: int, last_updated: str}`. Enables
      R13's "sample X of N" display. If not feasible to
      ship in the same story, drop and show only elapsed.
- [ ] R19: **Audit log entry** per archive from UI
      (reuse `experiment.archive`).

### 5. Cross-cutting

- [ ] R20: **Super-only gating** on archive button + the
      strip (hide for non-super users).
- [ ] R21: **Cache-bust** bump on all touched static
      files + register new JS in all pages.
- [ ] R22: **Drawer entry** — add "Experiments" link to
      the drawer under the agent group (not admin).

## Acceptance Criteria

### Active-experiment strip
- [ ] AC1: Super user, no running experiment → strip
      hidden on all pages.
- [ ] AC2: `POST /experiments/{id}/run` → within 10s,
      strip appears on current page with label + elapsed.
- [ ] AC3: Strip's elapsed-time counter advances on each
      10s poll.
- [ ] AC4: Navigate to another page while experiment
      running → strip visible on that page.
- [ ] AC5: Logout + log back in with experiment running
      → strip visible immediately.
- [ ] AC6: Experiment completes → strip shows "Completed
      — accuracy=X" for 60s; then disappears.
- [ ] AC7: Non-super user → strip hidden.
- [ ] AC8: Training run active AND experiment active →
      both strips stacked, no visual clash.

### Experiments page
- [ ] AC9: Drawer entry opens list view, newest-first.
- [ ] AC10: Agent filter narrows the list to one agent.
- [ ] AC11: State badges reflect live DB (10s poll).
- [ ] AC12: Clicking a row opens detail with pins +
      results populated.
- [ ] AC13: Math-example card's "View experiments →"
      button navigates to `experiments.html?agent_id=X`
      (not the deferred-alert).

### Detail view
- [ ] AC14: `#experiment/{id}` is bookmarkable + resumable
      across sessions.
- [ ] AC15: While running, live progress panel updates
      every ~5s with sample X of N (if R18 ships) or
      elapsed-only (fallback).
- [ ] AC16: On completion → results panel shows metric
      value + `_stack` summary.
- [ ] AC17: On archive → error panel shows message +
      traceback.
- [ ] AC18: Lineage panel shows parent + children links
      for chained experiments.
- [ ] AC19: Archive button appears for super-only,
      disabled for already-archived rows.

### No regression
- [ ] AC20: TB-US-066 training-run strip still works
      alongside the new experiment strip.
- [ ] AC21: Drawer, modal, nav behavior unchanged
      elsewhere.
- [ ] AC22: `GET /experiments` without `state` filter
      returns all rows (back-compat).

## Design Notes

- **Why mirror TB-US-066's strip pattern.** Operator's
  explicit ask that triggered this story was "is the
  status reported on the website UI?" — the TB-US-066
  strip is the proven answer for training; applying
  it 1:1 for experiments keeps the mental model
  consistent and lets us reuse the CSS tokens.
- **Why super-only.** Non-super users can't launch
  experiments and don't need to see them. If chat users
  later need visibility (e.g., "the agent you're talking
  to is being evaluated"), that's a separate story.
- **Why no launch button in v0.1.** Launching an
  experiment is a design decision (which adapter?
  which RAG? which prompt?) — per the "Experiment
  creation is design-gated" principle, operator should
  make those pins thoughtfully, which argues for a
  purpose-built launcher later (Sweet Spot story) rather
  than a quick form here.
- **Why `started_at` is new instead of reusing
  `created_at`.** `created_at` is when the draft was
  recorded; `started_at` is when the harness kicked off.
  For a draft that sits for days before running, elapsed
  computed from `created_at` would be misleading.
- **Why progress heartbeat is optional.** First version
  can ship with elapsed-only. Operator can decide at
  review time whether sample-level progress is worth the
  harness-runner changes. The strip's primary value is
  "something IS running" — details are secondary.
- **Why no chart.** Same reason as TB-US-066: keep it
  as simple as possible; chart lands as a TB-US-045
  reactive tweak if operator asks.
- **How this relates to TB-US-067 and future Sweet
  Spot work.** TB-US-067 is backend plumbing (chat-path
  RAG wiring). The Sweet Spot promotion UI is a future
  story that would add promote / displace actions +
  the Sweet Spot combo picker. This story (TB-US-070)
  is strictly "see what's happening"; it does not
  implement promotion.

## Followups / Explicit Deferrals

- **Promote / displace actions in detail view** → Sweet Spot story
- **Launch form** → Sweet Spot story (or dedicated TB-US)
- **Chart of per-sample timings** → TB-US-045 reactive tweak
- **Per-sample streaming log** → defer unless harness emits one
- **Experiment comparison view** (side-by-side E1/E2/E3) →
  separate story once two or more experiment arcs exist in
  the wild
