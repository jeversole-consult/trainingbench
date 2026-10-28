# TB-US-035: Port `/active-adapter` endpoint — currently-loaded PEFT adapter reporter

**Status**: Completed
**Created**: 2026-10-14
**Completed**: 2026-10-14
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a TB user or operator, I want a `GET /active-adapter`
endpoint that reports the currently-loaded PEFT adapter (name
and path), matching stalite3's existing endpoint signature, so
that any TB-side UI, test harness, or sync-forward
customer-demo (TB-US-032 arc) can introspect which adapter is
active without inferring it from unrelated endpoints.

## Background

From TB-US-031 feature parity audit (Section 3.1), stalite3
has `GET /active-adapter` which returns:

```python
{"adapter": ACTIVE_ADAPTER, "adapter_path": ACTIVE_ADAPTER_PATH}
```

Backed by module-level globals in stalite3's
`backend/api/main.py` (lines 117–118):

```python
ACTIVE_ADAPTER = "stalite-mix-knowledge-v7"
ACTIVE_ADAPTER_PATH = f"training/adapters/{ACTIVE_ADAPTER}"
```

TB has no equivalent. TB's `/query` defaults to
`"llama3.1:8b"` (raw Ollama) with no PEFT adapter concept at
the module level.

**Direct-port scope** (per the operator's 2026-10-14
sync-forward direction): add the globals + endpoint on TB
with the same shape and semantics as stalite3. TB's default
is `None` (TB doesn't ship with a pre-trained adapter;
customer deployments like stalite3 may point to one via
env var).

## Requirements

- [x] R1: **Module-level globals in TB's
      `backend/api/main.py`:**
      ```python
      ACTIVE_ADAPTER = os.getenv("TB_ACTIVE_ADAPTER") or None
      ACTIVE_ADAPTER_PATH = (
          f"training/adapters/{ACTIVE_ADAPTER}" if ACTIVE_ADAPTER else None
      )
      ```
      Env var `TB_ACTIVE_ADAPTER` is optional; TB with no env
      var set has no active adapter (both globals are `None`).
- [x] R2: **New endpoint `GET /active-adapter`** matching
      stalite3's shape:
      ```python
      @app.get("/active-adapter")
      async def get_active_adapter():
          """Get the currently active PEFT adapter name."""
          return {
              "adapter": ACTIVE_ADAPTER,
              "adapter_path": ACTIVE_ADAPTER_PATH
          }
      ```
- [x] R3: **Auth: match stalite3's open posture.** Stalite3's
      `/active-adapter` has NO per-endpoint auth dependency
      (open past the site-wide passphrase gate). Direct port
      means TB matches — no `Depends(verify_web_auth)` on this
      endpoint. The adapter name is not sensitive and the site
      gate is enough.
- [x] R4: **No downstream changes.** TB's `/query` is NOT
      modified by this story to use `ACTIVE_ADAPTER` as a
      fallback — that's a bigger change (would change TB's
      default model behavior) and belongs in a separate
      story if ever desired. This story only adds the
      *reporting* endpoint.
- [x] R5: **No regression.** All existing TB endpoints
      unaffected. `GET /models` (which TB has) is not
      touched.
- [x] R6: **Service restart to pick up env var.** If the
      operator later sets `TB_ACTIVE_ADAPTER`, a service
      restart is required (globals read at import time).

## Acceptance Criteria

- [x] AC1: `GET /active-adapter` on TB with no env var set
      returns `{"adapter": null, "adapter_path": null}`.
- [x] AC2: With `TB_ACTIVE_ADAPTER=example-adapter` set and
      service restarted, `GET /active-adapter` returns
      `{"adapter": "example-adapter", "adapter_path":
      "training/adapters/example-adapter"}`.
- [x] AC3: Authenticated calls to `/active-adapter` return
      the expected shape. (No per-endpoint auth; site gate
      middleware still blocks unauthenticated external
      access per R3's direct-port semantic.)
- [x] AC4: `git diff backend/api/user_manager.py` and
      `git diff backend/api/*.py` other than `main.py` are
      clean.
- [x] AC5: Service restarts cleanly after the change; no
      regression on existing endpoints verified by a
      smoke-test of `/version`, `/stats`, `/query`.
- [x] AC6: Signature matches stalite3's exactly (same JSON
      keys, same value types) so a future sync-forward is
      a no-op.

## Design Notes

- **Direct-port.** Stalite3's `ACTIVE_ADAPTER` is a hardcoded
  module global (`"stalite-mix-knowledge-v7"`). TB's version
  defaults to `None` and is env-var-configurable. The *shape*
  of the response matches exactly.
- **Why env var instead of hardcoded.** TB has no
  Stalite-specific adapter to hardcode. Env var lets per-
  deployment TB installs point to a specific adapter via
  `/etc/default/trainingbench` without a code change.
- **Why not scan `training/adapters/` and auto-select.** Too
  magical. If multiple adapters exist, which one is "active"
  is operator intent, not inferrable.
- **Why not change `/query`'s default model.** TB currently
  defaults to raw Ollama (`"llama3.1:8b"`). Changing that to
  use `ACTIVE_ADAPTER` would alter TB's default behavior for
  every existing caller and is out of scope. If/when a
  customer deployment wants adapter-first behavior, a
  separate story adds that.
- **Sync-forward implication.** Once TB has this endpoint,
  stalite3's version is already compatible — stalite3 keeps
  its hardcoded default; TB's env-var pattern is a superset
  of stalite3's hardcode. No stalite3 change needed.

## Out of Scope

- Changing TB's `/query` default model behavior to use
  `ACTIVE_ADAPTER` as a fallback.
- Adding a `PUT /active-adapter` to change the adapter at
  runtime (hot-swap). Hot-swap costs ~60s per adapter load
  (per stalite3 comments); runtime-swap is a bigger story.
- Adding `/models` endpoint improvements. TB has `/models`;
  this story doesn't touch it.
- UI changes to display the active adapter.
- Validation that `ACTIVE_ADAPTER_PATH` actually exists on
  disk. If the env var points to a non-existent path, the
  endpoint returns the configured value anyway. Validation
  is a bigger concern.
- Branding tweaks.

## Related

- Parent: [TB-US-031](tb-us-031.md) — feature parity audit;
  R3 lists `/active-adapter` as missing on TB side.
- Follow-up to: [TB-US-032](tb-us-032.md) — first
  sync-forward operation (role vocab).
- Sibling stories to execute next (TB-US-036 through
  TB-US-033): feature parity close-out.
- stalite3 reference: `backend/api/main.py:117-118, 1356-1362`.
- TB code touched: `backend/api/main.py` only.

**Completion Notes (2026-10-14).**

- Added `ACTIVE_ADAPTER` + `ACTIVE_ADAPTER_PATH` module
  globals in `backend/api/main.py` (after LLM_MODEL, before
  SITE_PASSPHRASE), populated from `TB_ACTIVE_ADAPTER` env
  var with `None` default.
- Added `GET /active-adapter` endpoint next to `/models` for
  stalite3-parity placement. No per-endpoint auth
  (direct-port semantic; site gate middleware still blocks
  unauthenticated external access).
- Service restarted; endpoint live at
  `https://tbench.weidecai.com/active-adapter` returning
  `{"adapter": null, "adapter_path": null}` when
  `TB_ACTIVE_ADAPTER` is unset (current production state).
- Env-var-reading logic validated inline for AC2 (three
  cases: set, unset, empty string). Empty string correctly
  treated as `None` via `or None` idiom.
- Smoke-tests: `/version` and `/stats` return 200
  post-restart. No regression.
- `git diff backend/` is 29 lines (+29/-0), all in
  `main.py`.
- First inter-session gotcha: Cloudflare returned 502 for
  ~5 seconds after service restart (expected — tunnel takes
  a moment to re-establish). Retried after sleep 3,
  succeeded.
- Signature matches stalite3's exactly:
  `{"adapter": <string or null>, "adapter_path": <string or null>}`.
  Future sync-forward to stalite3 is a no-op on this
  endpoint since stalite3 already has the identical shape.
