# UI Acceptance Checklist Template

**Reusable template for TrainingBench release-cut acceptance passes.**
First used: TB-US-072 for v0.1.0-rc1 (2026-10-28). Expected re-use at
every subsequent release.

## How to use this template

1. Copy to `docs/release/<version>-ui-acceptance-review.md`
2. Fill in the Rehearsal environment section with your specifics
3. Walk every item in the checklists below
4. Mark each ✅ pass / 🔴 blocking / 🟡 should-fix / 🟢 nice-to-have
5. Follow TB-US-068 AC8 pattern: each 🔴 gets its own story draft;
   each 🟡 lands in TB-US-045 reactive umbrella (if small) or a
   follow-up story (if structural); 🟢s go to review doc with a
   "defer unless trivial" note

## Rehearsal environment

| Field | Value |
|---|---|
| Date | <YYYY-MM-DD> |
| Operator | <name> |
| Target version | v<X.Y.Z-rcN> or v<X.Y.Z> |
| Clone source | git@github.com:<org>/<repo>.git |
| HEAD commit | <sha> |
| Lab machine | <hostname, OS, driver, GPU, Python> |
| Throwaway dir | <path> |
| APP_PORT used | <port> (choose to avoid live service collision) |
| Access method | Direct browser / SSH tunnel / Cloudflare tunnel |

## Phase 1 — Fresh install reaches a running backend

Verify the install path from clone through `uvicorn running`.

- [ ] Clone succeeded; `git log --oneline -N` shows expected commits
- [ ] Clone directory structure matches dev tree (`openclaw/`,
      `docs/user/`, etc. match current state — no orphan dirs)
- [ ] System binaries pre-check (`python3-venv`, `git`, `curl`,
      `tesseract-ocr`, `poppler-utils`, `build-essential`) satisfied
      via `apt install -y` (list unchanged ones)
- [ ] `python3 -m venv venv` succeeds
- [ ] `pip install --upgrade pip` succeeds
- [ ] (GPU machine) `pip install torch --index-url
      https://download.pytorch.org/whl/cu128` succeeds if NVIDIA
      driver reports CUDA 12.x
- [ ] `pip install -r requirements.txt` completes without errors;
      no package-version warnings that look structural
- [ ] `python -c "import torch; print(torch.cuda.is_available())"` →
      True on GPU install, acceptable on CPU-only install
- [ ] `cp .env.example .env`
- [ ] `.env` has `APP_PORT=<chosen>` and `DEFAULT_ADMIN_EMAIL`
      set
- [ ] `set -a; source .env; set +a` before uvicorn (per F1
      INSTALL.md gap)
- [ ] `python -m uvicorn backend.api.main:app --host 0.0.0.0
      --port "$APP_PORT"` starts cleanly
- [ ] All first-boot banners present in stdout:
      - `[secrets]`
      - `[schema]` for TB-US-051
      - `[schema]` for TB-US-055-appsettings
      - `[seeder]` with seeded agent + experiments
      - `INFO: Uvicorn running on http://0.0.0.0:<PORT>`
- [ ] Admin credentials visible in `logs/first-run-admin.txt`
      (DO NOT rely on stdout banner — may land after Uvicorn URL
      per F2)

## Phase 2 — Auth + first-run flows

- [ ] Browser (or curl): root URL redirects to `/static/login.html`
      (not `/static/gate.html` — regression check for TB-US-071)
- [ ] Login with `admin` + auto-generated password succeeds
- [ ] Forced-change-password page accepts a new password
- [ ] `logs/first-run-admin.txt` auto-deletes after change
- [ ] Re-login with new password succeeds; `must_change_password`
      is now false
- [ ] Welcome banner dismiss endpoint works + persists across
      re-login

## Phase 3 — Top bar + drawer nav

- [ ] Top-bar agent chip visible, shows current agent (default
      or math-example after first-run seed)
- [ ] Hamburger drawer opens + closes (click outside, Esc,
      close button)
- [ ] Agent selector widget lists both seeded agents
- [ ] Switching agent via selector persists across pages
- [ ] All drawer nav entries render: Chat / Upload / Documents /
      Databases / Training Sets / Training Runs
- [ ] Admin group (super-only) renders at bottom: Users + API
      Keys
- [ ] Non-super users (if created) do NOT see admin group

## Phase 4 — Nav pages (visual + endpoint check)

For each page: load with browser (or curl `/static/<page>.html`),
check for JS errors in dev tools console, verify basic rendering.

- [ ] Chat tab — welcome banner (if math-example seeded) + input
      box + "View experiments →" button
- [ ] Upload tab — file selector + upload state
- [ ] Documents tab — empty state on fresh / list on populated
- [ ] Databases tab — RAG manifests + detail
- [ ] Training Sets tab — training-set versions + detail
- [ ] Training Runs tab — list view + `+ Start new run` button
      (super-only) + launch modal

## Phase 5 — Admin modals

- [ ] Users modal — list + Actions dropdown + Edit modal
- [ ] API Keys modal — list + create + revoke + raw-key-once
      display
- [ ] Agent management modal — create / rename / retire /
      reactivate

## Phase 6 — Training supervision

- [ ] Active-run strip hidden on fresh install (no runs active)
- [ ] Launch training via `POST /training/runs/launch` with
      correctly-nested `hyperparameters` (per F10 lesson):
      ```json
      {
        "run_name": "...",
        "training_set_version_id": N,
        "base_model": "...",
        "hyperparameters": {
          "max_train_samples": 50,
          "max_eval_samples": 25,
          "epochs": 1
        }
      }
      ```
- [ ] Active-run strip appears within 10s with live progress
- [ ] Strip shows epoch / step / loss / elapsed, updating
- [ ] Navigate to another page; strip still visible
- [ ] Logout + log back in; strip visible immediately
- [ ] Run completes; strip shows "Completed" for ~60s then auto-hides
- [ ] Strip can be dismissed via ✕
- [ ] Detail view shows adapter link post-completion
- [ ] Adapter auto-registered as `adapter_versions.vN` via
      TB-US-063 flow

## Phase 7 — Experiment runs (GPU required)

Pre-reqs:
- Trained + promoted an adapter (Phase 6)
- Experiments E2/E3 updated to pin that adapter_version_id

- [ ] Seeded math-example experiments visible via API
      (`GET /experiments?agent_id=<math-example>`)
- [ ] E1 (bare) runs to completion; results JSON contains
      `metric`, `value`, `_stack` (with `adapter: None`)
- [ ] E2 (+adapter) runs to completion; `_stack` has `adapter:
      <path>`
- [ ] E3 (+adapter+rag) runs to completion; `_stack` has both
      adapter + rag_collection
- [ ] Each experiment persists `per_sample` array
- [ ] Three experiments ran sequentially without GPU contention
- [ ] (If appropriate) VRAM freed between runs via
      `trainingbench.service` restart

## Phase 8 — Smoke-test the full install

For GPU machines:
- [ ] `python scripts/download_gsm8k.py` succeeds
- [ ] `python training/math/train.py --max-train-samples 50
      --max-eval-samples 25 --epochs 1 --run-name smoke`
      reaches a training loop + completes
- [ ] Smoke-training adapter files land in
      `training/adapters/smoke/final/`

For CPU-only machines (Track B):
- [ ] Training skipped by design; backend + UI are the only check

## Phase 9 — Cleanup (R10 equivalent)

- [ ] Kill the backend (Ctrl+C or `pkill -f "uvicorn.*<port>"`)
- [ ] `rm -rf <throwaway-dir>`
- [ ] Verify port freed: `ss -tlnp | grep :<port>` returns nothing
- [ ] Verify live service (if any) unaffected

## Phase 10 — Deliverables

- [ ] Findings documented in
      `docs/release/<version>-ui-acceptance-review.md`
- [ ] Each 🔴 has a story draft
- [ ] Each 🟡 landed in TB-US-045 (if small) or a follow-up story
- [ ] BACKLOG updated with any spawned stories
- [ ] Operator attests confidence in release shape for public cut

## Severity scale (reminder)

- 🔴 **Blocking**: must fix before public cut; prevents a doc
  follower from reaching a working install OR materially
  misrepresents behavior
- 🟡 **Should-fix**: fix before public cut if easy; otherwise
  follow-up story
- 🟢 **Nice-to-have**: defer unless trivial

## Appendix — known-good reference findings

Findings surfaced during the first execution of this checklist
(TB-US-072 for v0.1.0-rc1):

- **F1**: INSTALL.md Step 5 shell-env gap (`$APP_PORT` export)
- **F2**: Credentials banner appears AFTER "Uvicorn running"
  line — operators easily miss it; `logs/first-run-admin.txt`
  is the reliable source
- **F5**: 🔴 login.js unconditional gate redirect — fixed
  in TB-US-071 (`89478e5`)
- **F6**: 🟡 seeded experiments have `adapter_version_id=None`
  despite "plus-adapter" labels
- **F7a/F7b**: launch endpoint doesn't validate GSM8K presence;
  errors reconcile only via list query
- **F8**: no structured `error_message` column
- **F9**: 🔴 train.py logging_dir kwarg — fixed in
  TB-US-074 (`f9366d5`)
- **F10**: API-shape clarity — hyperparameters must be nested;
  unknown top-level fields silently dropped (Pydantic default)
- **F11**: `training_runs.final_train_loss` / `final_eval_loss`
  not denormalized post-completion

Any of these may re-surface in future rehearsals; checklist
items are structured to catch them.
