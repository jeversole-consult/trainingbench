# TB-US-003: Per-user random password salts

**Status**: Deferred
**Created**: 2026-09-27
**Deferred**: 2026-10-14
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

> **Stub** — requirements will tighten when picked up.
>
> **Deferred 2026-10-14** per operator decision. See **Reactivation
> condition** below. Previously listed under TB-US-015 launch
> coordinator R2 (code hardening); now conditional on the
> PM-US-004 IAM decision rather than a hard launch gate.

## Story

As a TrainingBench user (present or future), I want each of my
passwords to be hashed with a per-user random salt using a
modern password-hashing scheme, so that a database compromise
does not enable rainbow-table attacks against every user at
once and my credential is resistant to offline brute force even
if the store leaks.

## Background

TrainingBench today uses **SHA-256 with a single global salt**
for password hashing (`backend/api/user_manager.py`, `_hash_password`).
That scheme is known-weak against modern attacker capability:
SHA-256 is designed to be fast (billions of hashes/sec on GPU),
and a global salt means one leaked hash-set is attacked with a
single rainbow table rather than per-user work.

Modern practice: **argon2id** (or bcrypt as a widely-supported
fallback) with a fresh random salt per user. Both are
deliberately slow, memory-hard (argon2), and produce hashes
that already include the salt inline.

Called out in TB-US-004's IAM discussion as blocking pre-launch;
also cross-referenced by projmgmt PM-US-004 as one of the
weaknesses the shared IAM foundation would fix. If PM-US-004
lands before TB-US-003 activates, this story may be superseded
by adoption of the shared IAM instead of a TB-local fix.

## Requirements (draft — will tighten when picked up)

- [ ] R1: Replace SHA-256 + global salt in `user_manager.py`
      with argon2id (preferred) or bcrypt. Add the dependency
      to `requirements.txt` and note it in TB-US-007's audit.
- [ ] R2: Existing user hashes migrate on next successful
      login: verify with old scheme; on success, re-hash with
      new scheme and update the row. Zero-downtime, no forced
      password reset.
- [ ] R3: Global salt env var (if any) is removed from the
      hashing path. May remain temporarily as legacy for
      migration verification.
- [ ] R4: Password verification uses constant-time comparison
      via the library's `verify()` method rather than string
      equality.
- [ ] R5: Unit tests cover: new-user creation (fresh hash),
      legacy-hash login (migrates in place), password change
      (uses new scheme), wrong-password rejection.

## Acceptance Criteria (draft)

- [ ] AC1: Every hash in `users.db` after N logins is in the
      argon2id (or bcrypt) format — verified by inspecting
      `password_hash` column and confirming it starts with the
      library's prefix (`$argon2id$` or `$2b$`).
- [ ] AC2: A user whose hash was originally SHA-256 can still
      log in after the code change; on that login, their hash
      is updated in place.
- [ ] AC3: No SHA-256 hex digests remain in `users.db` after
      every active user has logged in at least once
      post-migration.

## Design Notes (draft)

- **Library choice.** `argon2-cffi` for argon2id (modern
  default). `passlib` if a broader multi-scheme wrapper is
  wanted. Bcrypt via `bcrypt` package as a well-known fallback.
- **Migration lens.** In-place rehash on successful login is
  the least-disruptive path — no forced reset, no user-visible
  action. Users who don't log in for a long time will keep
  their old hash until they do; that's acceptable.
- **Interaction with PM-US-004.** If the shared IAM foundation
  ships before this story executes, adopt the shared identity
  layer instead of doing a TB-local fix. This story would then
  be Retired (superseded), not Completed.

## Out of Scope

- Cross-project SSO (that's PM-US-004).
- MFA (also PM-US-004).
- Rate limiting login attempts (TrainingBench already has
  `LoginTracker`; not part of this story).
- Password-reset flow. Separate story if wanted.

## Related

- [TB-US-015](tb-us-015.md) — launch coordinator; R2 phase gate
  (updated 2026-10-14 to mark this story as conditional, not
  blocking).
- **PM-US-004** on projmgmt — could supersede this story if
  adopted first. See Reactivation condition.
- `backend/api/user_manager.py` — the file being modified when
  reactivated.

## Reactivation condition (added 2026-10-14)

TB-US-003 is **Deferred** rather than Retired because there is
still a plausible scenario where it needs to execute. Specifically:

- **Reactivate** if PM-US-004 (shared IAM foundation across
  projmgmt + TB) lands with a decision that **does not replace
  TB's local auth** — e.g., PM-US-004 adopts a federation
  pattern that leaves TB's existing `users.db` + hashing in
  place. In that case, TB's weak-hashing issue is still real
  and TB-US-003 needs to run.
- **Retire** (move to Withdrawn status in a future cleanup) if
  PM-US-004 lands with Cloudflare Access (the audit's working
  recommendation) or any other mechanism that fully replaces
  TB's local login path — the TB-local hashing becomes dead
  code.
- **Hold as Deferred** indefinitely while PM-US-004 remains in
  Backlog. No urgency to decide; the attack posture that TB-US-003
  addresses (weak hashing on `users.db`) is unchanged by the
  deferral — just not being actively fixed by TB directly.

**Operational posture during deferral:** stalite3 users and TB
users continue to log in using SHA-256 + global salt. The
`login_tracker` rate limit on `/auth/login` provides defense
against online brute force (5 failures / 15-min IP lockout).
Offline attack posture (if `users.db` leaks) is unchanged.
Known-weak and documented.

**Completion Notes (deferral — 2026-10-14).**

- Status flipped `In Progress` → `Deferred` per operator decision.
- Previously held `In Progress` by the 2026-09-27 arc-scoped WIP
  flip (TB-US-015 launch arc activation); the flip was honest
  about intent but TB-US-003 was never actually worked.
- TB-US-015 R2 phase gate updated to reflect the conditional
  posture.
- No code or user-facing changes result from this deferral.
  stalite3 and TB continue to run with the known-weak hashing
  pending the PM-US-004 decision.
