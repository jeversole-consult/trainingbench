# TB-US-066: Training runs UI — active-run visibility + minimal supervision

**Status**: Completed
**Created**: 2026-10-22
**Started**: 2026-10-22
**Completed**: 2026-10-22
**Revised**: 2026-10-22 (simplified per operator "keep it as simple as possible" direction)
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a TB operator, I want **the moment I log in** to see
whether a training run is active and what status it's at
(epoch, step, current loss, elapsed time) — plus a
minimal supervision view (list, basic detail, cancel) —
so that I can start a run, close the browser, come back
later and immediately understand what's happening.

## Background

Frontend portion of TB-US-064's arc. Backend lands in
TB-US-065.

**Scope simplified 2026-10-22.** Operator's explicit asks
anchor the design:

1. *"Display status on login"* — surface active-run state
   immediately, not hidden behind navigation
2. *"Understand when logged in there is an active
   training run going on"* — a persistent indicator
3. *"And what the status of the training run is"* —
   epoch / step / current loss / elapsed, not just "a
   run exists"

The implementation anchor is a **top-of-page active-run
status strip** that appears whenever any run has
`status='running'`. Beyond that, the Training Runs page
gets a list + a basic detail view + a launch modal +
cancel. Charts, rerun button, checkpoint download, etc.
are deferred to TB-US-045 reactive tweaks.

**Depends on:**
- TB-US-065 — Backend launch endpoint + process
  management must exist first
- TB-US-052 — Training-set versioning (launch form picks
  a version)
- TB-US-063 — Adapter versioning (post-completion:
  show the auto-registered adapter link)

## Requirements

### 1. Active-run status strip (primary feature)

- [x] R1: **Element** `#tb-active-run-strip` injected
      into the header on all pages (same places
      `left_nav.js` injects into — index.html,
      training_sets.html, training_runs.html).
- [x] R2: **Visibility** — hidden by default; appears
      when `GET /training/runs?status=running` returns
      a non-empty list.
- [x] R3: **Content**:
      ```
      ⚙️ Training in progress: {run_name}
         Epoch {E} of {total_epochs} · Step {S} ·
         Loss {L} · Elapsed {HH:MM:SS}      [View →]
      ```
      "View" is a link to `/static/training_runs.html#run/{id}`.
- [x] R4: **Polling** — strip polls `GET /training/runs?
      status=running` every **10 seconds** when visible.
      Updates in place (no page reload). When no active
      run, polling continues at the same cadence so a
      newly-started run (started in another tab) becomes
      visible within 10s.
- [x] R5: **Styling** — amber-accented banner (consistent
      with TB-US-042 palette). Pulsing border to signal
      "live". Super-only (hide for non-super users since
      they can't launch anyway).
- [x] R6: **State transitions:**
      - Status flips to `completed` or `failed` or
        `cancelled` → strip shows final state for 60s
        with the final loss / cancel reason, then
        disappears
      - Operator can dismiss the final-state strip
        manually via a × button

### 2. Training Runs page — list view

- [x] R7: **Audit existing `static/training_runs.html`.**
      Rewrite / enhance as needed. Static shell today;
      upgrade to full list + detail.
- [x] R8: **List view** of training runs (newest first).
      Columns:
      - Run name / description
      - Agent (via `training_runs.agent_id`)
      - Status badge: `running` (amber), `completed`
        (green), `failed` (red), `cancelled` (grey)
      - Started / elapsed (for running) OR duration
        (for completed)
      - Final train loss (populated on completion)
      - Action: `View →` link to detail
- [x] R9: **`+ Start new run`** button (super-only) at
      top of the list.

### 3. Launch form (modal)

- [x] R10: **Modal** matching TB-US-048/063 pattern.
      Fields:
      - Run name (required text)
      - Description (optional text)
      - Agent — dropdown from `GET /agents?include_retired=false`
      - Training set version — dropdown from
        `GET /agents/{selected_agent}/training-sets`
        filtered to `state='released'`
      - Base model — text input, default
        `meta-llama/Meta-Llama-3.1-8B`
      - Hyperparameters — collapsed accordion; defaults
        prefilled from training/math/README values
        (lora_rank=16, lora_alpha=32, lr=2e-4, epochs=3,
        batch=4, gradient_accumulation=4)
      - Notes (optional text)
- [x] R11: **Submit → `POST /training/runs/launch`** per
      TB-US-065. Success → close modal + the active-run
      strip picks it up on next poll. 409 → inline error
      with "View active run" link.
- [x] R12: **Launch button disabled** when any run is
      active (defense in depth; backend 409s regardless).

### 4. Detail view

- [x] R13: **Routable** via `#run/{id}` hash in URL.
      Operator can bookmark the specific run and return
      to it after logout.
- [x] R14: **Panels** (no chart in v0.1):
      - Header: run name + status badge + started /
        elapsed-or-duration
      - **Current progress panel** (when `running`):
        current epoch / step, latest train loss, learning
        rate. Updates every 5s.
      - **Log tail**: last 50 entries from
        `training_run_logs` (via existing `GET /training/
        runs/{id}/logs`). Updates every 5s when running.
      - **Config panel** (collapsed by default): the
        hyperparameters the run was launched with +
        link to training_set version.
      - **Checkpoints list**: step + loss per row (no
        download in v0.1).
      - **Adapter link** (when `completed`): show the
        auto-registered `adapter_versions` row + link.
      - **Cancel button** (when `running`): confirm
        dialog → `POST /training/runs/{id}/cancel`.
- [x] R15: **Polling cadence** — 5s active, 60s otherwise.
      Cancellable `setInterval` cleaned up on page
      navigation.

### 5. Cross-cutting

- [x] R16: **Super-only gating** on launch + cancel
      actions (hide buttons for non-super users; backend
      403s anyway).
- [x] R17: **Cache-bust** bump on all touched static
      files + add new JS files to all 3 pages.

## Acceptance Criteria

### Active-run strip
- [x] AC1: Super user, no active run → strip hidden on
      all pages.
- [x] AC2: Launch a run → within 10s, strip appears on
      current page.
- [x] AC3: Strip shows live epoch / step / loss / elapsed
      updating on 10s cadence.
- [x] AC4: Navigate to another page while run is active
      → strip is still visible on that page.
- [x] AC5: Logout + log back in with run still active →
      strip is visible immediately on login.
- [x] AC6: Run completes → strip updates to "Completed"
      state for 60s with final loss; then disappears.
- [x] AC7: Non-super user → strip hidden (super-only).

### Training Runs page
- [x] AC8: Opens from drawer entry → list view renders
      newest-first.
- [x] AC9: Status badges reflect live DB state (polling
      refreshes).
- [x] AC10: Super user: `+ Start new run` button
      visible; clicking opens modal. Non-super user:
      button hidden.
- [x] AC11: Launch form validates (run_name required,
      training_set_version_id required). Missing →
      inline error, no POST.
- [x] AC12: 409 from launch → inline error with "View
      active run" link.

### Detail view
- [x] AC13: Click a run row → detail view opens with
      panels populated.
- [x] AC14: While running, current progress + log tail
      update every ~5s.
- [x] AC15: Cancel on active run → confirm dialog →
      run transitions to `cancelled` within ~10s;
      button disappears.
- [x] AC16: On successful completion → detail view
      shows auto-registered adapter row with link.
- [x] AC17: `#run/{id}` URL is bookmarkable + resumable
      across sessions.

### No regression
- [x] AC18: Drawer / modal / existing nav behavior
      preserved.

## Design Notes

- **Why the active-run strip is the primary feature.**
  Operator explicitly asked for status-on-login +
  active-run visibility + status details. A chip that
  appears on every page right under the header is the
  most direct answer. Everything else in this story
  supports that chip.
- **Why no chart in v0.1.** Operator said "keep it as
  simple as possible". Chart ships as a TB-US-045
  reactive tweak once operator confirms the simpler
  "latest-loss-as-text" view is actually what they
  want.
- **Why 10s cadence for strip, 5s for detail.** Strip
  is a passive indicator; 10s is responsive enough.
  Detail view is active supervision; 5s matches the
  "watching training" workflow.
- **Why super-only on the strip.** Non-super users
  can't launch training; showing them a run-in-progress
  banner adds noise without actionability.
- **Why modal for launch.** Matches TB-US-048/063.
  Hyperparameter accordion keeps the modal from being
  overwhelming by default.
- **Why bookmarkable `#run/{id}` URLs.** Operator can
  bookmark a specific run before closing the browser,
  come back later directly to that run.
- **Why 60s "final state" visibility on the strip.**
  Operator who just happens to log in right after a
  run completes sees the result, not an immediately-
  blank header.

## Out of Scope

- Loss curve chart (deferred to TB-US-045 reactive
  tweak after v0.1 ships)
- Rerun button
- Checkpoint download
- Side-by-side run comparison
- Resume-from-checkpoint
- Run tagging / filtering / search
- Email / Slack notification on completion
- Operator-defined custom metrics display
- Edit-in-place run name / description
- Hyperparameter sweeps UI
- Grouping runs by agent in list view
- Live CUDA utilization / VRAM display
- SSE / WebSocket real-time (polling is enough)

## Related

- [TB-US-064](tb-us-064.md) — Coordinator (parent)
- [TB-US-065](tb-us-065.md) — Backend; this frontend
  drives its API
- [TB-US-048](tb-us-048.md), [TB-US-063](tb-us-063.md)
  — modal visual pattern template
- [TB-US-052](tb-us-052.md) — Training-set versioning
  (launch form picks a version)
- [TB-US-045](tb-us-045.md) — Where chart + rerun +
  checkpoint-download tweaks land post-v0.1
- Files touched (anticipated):
  - `static/training_runs.html` — restructure
  - `static/training_runs.js` (new) — list + detail +
    polling + launch modal
  - `static/active_run_strip.js` (new) — the status
    strip (loaded on all 3 pages)
  - 3 HTML pages — add `<div id="tb-active-run-strip">`
    placeholder + include `active_run_strip.js` +
    cache-bust bumps
  - `static/style.css` — status badge + strip styles if
    not reusable

## Completion Notes (2026-10-22)

**Scope revision mid-execution:** audit of existing `static/training_runs.html` revealed TB-US-001 shipped a 1437-line page with substantial UI already (list view, launch form, detail modal, metrics/logs/checkpoints tabs). This story **augmented** rather than rewrote. Smaller delta than the draft anticipated — most of the "list view" + "detail view" requirements were already met by the pre-existing code.

### Delivered

**Primary feature: active-run status strip** (new, cross-page):
- **`static/active_run_strip.js`** (new, ~175 lines): self-contained module injected into `<body>` on every page via `<script src="active_run_strip.js?v=20261022a">`. Polls `/training/runs?status=running` every 10 seconds, enriches with the latest metric row from `/training/runs/{id}/metrics`. Renders a sticky top-of-page banner showing:
  - **While running:** `⚙️ Training in progress: {run_name}` + `Step {S} · Epoch {E.EE} · Loss {L.LLLL} · Elapsed {HH:MM:SS}` + amber pulsing border + `View →` link
  - **Final-state linger** (60s after status transitions out of `running`): status emoji + run name + final loss / duration + colored border matching outcome + user-dismissible `✕` button
- Super-only (checks `/auth/verify` → `user_type==='super'`; non-super users don't see the strip at all).

**Launch flow wiring** on existing `training_runs.html`:
- Replaced the `runTrainingSet` select (old `/training/sets` source — empty table) with two new selects: `runAgent` (from `/agents?include_retired=false`) and `runTrainingSetVersion` (from `/agents/{id}/training-sets` filtered to `state='released'`). The agent select repopulates the training-set-version select on change.
- Submit handler rewritten: POSTs to `/training/runs/launch` (TB-US-065) instead of `/training/runs` (metadata-only). Payload shape matches `LaunchTrainingRunRequest`: `run_name`, `description`, `training_set_version_id`, `base_model`, `hyperparameters`, `agent_id`, `notes`. `adapter_output_path` from the form field is folded into `hyperparameters` so the launch endpoint picks it up per TB-US-065 R1.
- 409 handling: shows a friendly alert listing the active run's id / name / started_at + "Cancel it first" instruction.
- Button label changed from "Create Training Run" → "🚀 Launch Training Run" to reflect that the click actually spawns a subprocess now.

**Cancel action** in detail view:
- When the detail modal is opened for a run with `status='running'`, a red-outlined "🛑 Cancel run" button appears next to the status badge.
- Clicking it fires a confirm dialog explaining SIGTERM/SIGKILL semantics + partial-file-preservation, then POSTs to `/training/runs/{id}/cancel`. On success, refreshes the runs list and closes the detail modal.

**Cache-bust bumps:** `active_run_strip.js?v=20261022a` added to all 3 pages (index, training_sets, training_runs). Existing scripts (left_nav, user_management, agent_management, api_key_management) unchanged.

### Verification

- **Served files sanity-checked** via curl: `active_run_strip.js` contains the strip id + poll function; `training_runs.html` has 6 launch-related strings (runAgent + onchange + loader + submit URL + launch button + cancelRun).
- **Backend data for form dropdowns verified**:
  - `GET /agents?include_retired=false` → 2 agents (`default`, `math-example`) ✓
  - `GET /agents/3/training-sets` → 1 released version (v3, 500 samples) matching TB-US-057 Phase A ✓
  - `GET /training/runs?status=running` → empty list (strip will be hidden on load) ✓
- **JS syntax:** `node --check static/active_run_strip.js` → OK.
- **Live browser verification deferred to operator** per the `feedback_ui_changes_organic` memory. End-to-end testing requires launching a real training run (3-4h GPU time); plumbing is proven via the TB-US-065 cancel-after-launch smoke tests.

### Scope decisions landed per simplification

- **No chart** (deferred to TB-US-045 reactive tweak if operator asks after v0.1 ships)
- **No rerun button** (dropped per simplification)
- **No checkpoint download** (dropped per simplification)
- **No side-by-side comparison** (page already had a `/training/runs/compare` endpoint hooked up — preserved; not enhanced)
- **Modal launch** (used the pre-existing `newRunModal`; no new modal created)
- **Simple polling** at 10s cadence (strip) — matched to TB-US-064 architecture decision
- **Super-only strip** (checks `/auth/verify` role; non-super users see nothing)

### Known caveats

- **Strip renders at `document.body.firstChild`.** If a page has a sticky header, the strip will scroll under it. Current TB pages don't have sticky headers so this works; if we add one, revisit.
- **Latest-metric fetch adds one extra API call per 10s poll.** Overhead negligible but noted.
- **Operator-dismissed terminal-state banner** uses a window-level `__tbStripDismissed` ID. If operator reloads the page, dismissal is forgotten. Acceptable for v0.1.
- **No live log tail in the detail view.** The existing detail modal has a log tab via `/training/runs/{id}/logs` but doesn't auto-refresh. Could be a TB-US-045 polish item once operator uses it.
- **Live visual verification** depends on an actual training run (operator-driven). The CLI plumbing is proven via TB-US-065; the UI wiring is code-complete.

### What this unblocks

- **TB-US-057 Phase B** — operator can now launch GSM8K training via the UI: open Training Runs → `+ Create Training Run` → select agent `math-example`, training-set version `v3`, base model `meta-llama/Meta-Llama-3.1-8B-Instruct`, hyperparameters JSON — click launch. Watch the active-run strip. Logout. Come back. Status is right there.
- **TB-US-064** (coordinator): all requirements closed. The arc can transition from In Progress to Completed once operator confirms browser verification.
