# TB-US-071: Fix login.js unconditional gate redirect + walk the maintenance-fix workflow

**Status**: Completed
**Created**: 2026-10-28
**Started**: 2026-10-28
**Completed**: 2026-10-28
**Author**: Jesse Eversole
**Commit hash(es)**: `89478e5`

## Story

As a TB operator, I want **fresh-install users to reach the login
page even when the site-access gate is disabled** — and I want to
exercise the full post-ship maintenance-fix workflow (observe →
story → fix → commit → push → downstream verify → close) using this
real bug as the test case, so that the team has a documented
"here is how we fix bugs" muscle memory for v0.1 and after.

## Background

Surfaced during TB-US-068 Phase C WSL rehearsal (2026-10-28). On a
fresh install with `SITE_PASSPHRASE` unset, a user navigating to
`http://localhost:PORT/static/login.html` is immediately redirected
by frontend JS to `/static/gate.html`, where a passphrase form
submits and returns 404 "Gate verification not enabled" from the
server. User is stuck in a loop and cannot reach the login page.

Captured as Phase C finding **F5 🔴 blocking** in
`docs/release/v0.1.0-rc1-rehearsal-review.md`.

### Root cause

`static/login.js` lines 5–12:

```js
window.addEventListener('DOMContentLoaded', async function() {
    const gateToken = localStorage.getItem('gate_token');

    // If no gate token, redirect to gate page immediately
    if (!gateToken) {
        window.location.href = '/static/gate.html';
        return;
    }
    // ... [subsequent code correctly handles 404 'gate not enabled']
});
```

The code short-circuits to `gate.html` on missing token **before**
asking the server whether the gate is required. Lines 20–23 handle
`response.status === 404` ("gate not enabled") correctly — but that
code path is unreachable without a token in `localStorage`.

### Repro steps

1. Fresh clone + fresh install TrainingBench
2. `.env` has `SITE_PASSPHRASE` commented out or unset (default)
3. Start backend: `python -m uvicorn backend.api.main:app --port 8003`
4. Open browser: `http://localhost:8003/`
5. **Expected**: login page renders with Username + Password fields
6. **Actual**: browser lands on gate.html; form submission errors with
   "Gate verification not enabled"

### Proposed fix

Make the gate check **unconditional** — always ask the server, with
or without a token. Server's 404 for the "gate disabled" case is
the authoritative signal.

```js
window.addEventListener('DOMContentLoaded', async function() {
    const gateToken = localStorage.getItem('gate_token');
    try {
        const response = await fetch(`${API_BASE}/auth/check-gate`, {
            headers: gateToken ? { 'X-Gate-Token': gateToken } : {}
        });
        if (response.status === 404) {
            // Gate not enabled → proceed to login
            return;
        }
        if (!response.ok) {
            // Gate enabled but no / invalid token → redirect to gate
            localStorage.removeItem('gate_token');
            window.location.href = '/static/gate.html';
            return;
        }
        // Gate token valid → allow login
    } catch (error) {
        console.error('Gate check failed:', error);
        // On error, assume gate is required for safety
        localStorage.removeItem('gate_token');
        window.location.href = '/static/gate.html';
    }
});
```

**Depends on:**
- None (self-contained; one file edit + one cache-bust bump)

**Blocks:**
- Public v0.1 cut (TB-US-005): a fresh-install user can't reach the
  login page without this fix

## Requirements

### 1. The fix

- [x] R1: Edit `static/login.js` to make `/auth/check-gate` the
      authoritative decision point, per the "Proposed fix" above.
      Remove the pre-fetch short-circuit on missing `gate_token`.
- [x] R2: Bump cache-bust version on `static/login.html` (the
      `?v=...` on the `<script src="login.js">` tag) so any
      operator with a cached old `login.js` picks up the new one.
- [x] R3: Preserve the existing behavior when the gate IS enabled —
      i.e., missing / invalid token still routes to gate.html.

### 2. Maintenance-fix workflow walkthrough

- [x] R4: Each phase of the workflow produces an artifact or
      action, in order:
      1. **Observe** — bug noted in the TB-US-068 Phase C review doc
         (already done; linked above)
      2. **Draft** — this story file + BACKLOG entry + Proposed
         notification fires
      3. **Fire** — status flips to In Progress + notification fires
      4. **Fix** — edit `static/login.js` + bump cache-bust
      5. **Commit** on host with commit message referencing
         `TB-US-071:`
      6. **Push** to `origin/main`
      7. **Downstream verify** — on operator's WSL clone, `git pull`
         + browser retest at `http://localhost:8003`
      8. **Close** — story Completed + notification fires
      9. **Review-doc update** — mark F5 as ✅ resolved in
         `docs/release/v0.1.0-rc1-rehearsal-review.md`

### 3. Documentation note

- [x] R5: Capture the maintenance-fix workflow template at
      `docs/training/maintenance-fix-workflow.md` after this story
      closes. Rough shape: ordered list of the phases above with
      explanation of why each matters. Deferred to a follow-up
      if operator wants separate scope.

## Acceptance Criteria

- [x] AC1: On a fresh install with `SITE_PASSPHRASE` unset, visiting
      `http://localhost:PORT/` lands on the login page with Username
      and Password fields visible. No redirect to gate.html.
- [x] AC2: On a fresh install with `SITE_PASSPHRASE` SET, visiting
      the same URL still correctly redirects to gate.html as before.
      (No regression on the gate-enabled path.)
- [x] AC3: After `git pull` on operator's WSL clone, browser retest
      at `http://localhost:8003` reaches the login page without
      manual localStorage intervention.
- [x] AC4: Review doc `v0.1.0-rc1-rehearsal-review.md` has F5 marked
      ✅ resolved with a reference to the commit hash.
- [x] AC5: Commit log for the fix references `TB-US-071`.
- [x] AC6: Full workflow phases 1–8 (per R4) executed in order,
      each surfacing in the appropriate artifact (notifications,
      git log, review doc).

## Design Notes

- **Why unconditional server check.** The server is the authority
  on whether the gate is enabled (via `SITE_PASSPHRASE` env var).
  Frontend assumptions ("if I don't have a token, I must need one")
  are brittle and lead to this kind of fresh-install breakage.
- **Why cache-bust is important.** A fresh install is fine without
  cache-bust (there's no stale cache). But an operator doing a
  `git pull` on an existing install has cached `login.js` in their
  browser — would still exhibit the bug until hard-refresh. Bumping
  the `?v=...` tag forces re-fetch.
- **Why we're using this bug as a workflow test.** TB-US-068 was
  Rehearse the Release Cut. This story is Rehearse the Maintenance
  Fix. Both exist to build operator muscle memory before the public
  cut. Finding a real bug in the rehearsal + walking the fix flow
  end-to-end is the cleanest learning exercise we could have asked
  for.
- **Why this is a story, not an inline hotfix in TB-US-068.**
  TB-US-068 is scoped to the release-cut rehearsal; its findings
  land in a review doc and spawn follow-up stories. Fixing bugs
  inline would blur TB-US-068's completion criteria. Spawning
  TB-US-071 keeps each story atomic.

## Out of Scope

- Refactoring the entire gate flow (keep this surgical — one JS
  function body)
- Changing server-side gate logic (works correctly)
- Adding a public "gate status" API (overkill; existing
  `/auth/check-gate` returning 404 is sufficient signal)
- Writing the `maintenance-fix-workflow.md` doc inline (R5 is
  flagged as deferrable to a follow-up story if operator chooses)

## Related

- [TB-US-068](tb-us-068.md) — rehearsal that surfaced this bug
- [TB-US-005](tb-us-005.md) — public v0.1 cut (blocked by this fix)
- `docs/release/v0.1.0-rc1-rehearsal-review.md` — Phase C findings
  log, F5 = this bug
- Files touched:
  - `static/login.js` (the fix)
  - `static/login.html` (cache-bust bump)
  - `docs/release/v0.1.0-rc1-rehearsal-review.md` (mark F5 resolved)
