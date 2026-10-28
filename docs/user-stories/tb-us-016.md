# TB-US-016: Create TB user accounts for Ted and Sam; update admin email

**Status**: Completed
**Created**: 2026-10-12
**Completed**: 2026-10-12
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As the operator of TrainingBench and Eversole Learning (EL), I
want two additional user accounts on TB (`tedcorvette`, `sfevers`)
and I want the existing admin account's email corrected from a
non-deliverable placeholder to a real address, so that TB's user
list reflects the actual humans involved in EL work and so that
a future TB stakeholder-notification story has a real,
deliverable-email population to route to.

## Background

TB's current `users.db` has two rows:

- `admin` — `user_type: super`, email `admin@localhost`
  (non-deliverable placeholder; blocks any future notification
  work that would email the admin), last login 2026-10-05.
- `chat_user` — `user_type: chat`, email `operator@example.com`,
  never logged in since creation 2026-07-21.

Separately, the humans actually working on EL (as recorded in
projmgmt's `users.db`) are:
- Jesse (`admin` on projmgmt / this same account on TB)
- Ted (`tedcorvette` on projmgmt — no TB account yet)
- Sam (`sfevers` on projmgmt — no TB account yet)

For TB to parity-match projmgmt's user list and for any
TB-side notification work to route to real inboxes, Ted and Sam
need TB accounts and `admin`'s email needs to be fixed.

This story operates under TB's **current weak auth** (SHA-256 +
global salt — same posture projmgmt had before PM-US-005
created accounts under its weak auth). TB-US-003 (per-user
salts) is already queued and will migrate every account —
including the ones created here — when it lands. Accepted
because the TB users are trusted collaborators, the site is
behind TB's gate passphrase and Cloudflare, and the three
accounts will be re-provisioned by TB-US-003.

## Requirements

- [x] R1: **Create user `tedcorvette` on TB.**
  - `username`: `tedcorvette`
  - `email`: `tedcorvette@gmail.com`
  - `user_type`: `super` (see Design Notes for the reasoning;
    cheap to change later via `UserManager.update_user_type`)
  - `active`: `1`
  - `password`: URL-safe generated passphrase using the
    same `word-word-word-word-NN` pattern from PM-US-005
    (~39 bits entropy; higher than the 12-char pattern used
    for Ted's projmgmt reset)
- [x] R2: **Create user `sfevers` on TB.** Same shape as R1
  with `username: sfevers`, `email: sfevers@gmail.com`,
  independent generated passphrase.
- [x] R3: **Update `admin` email** from `admin@localhost`
  to `operator@example.com`. Direct SQL `UPDATE` (TB's
  `UserManager` does not expose an email-update method; adding
  one is out of scope).
- [x] R4: **Password delivery.** Both new passphrases handed
  off out-of-band to Ted and Sam. Not recorded in the story
  file or anywhere version-controlled.
- [x] R5: **No regression on `admin`.** The admin
  account's `password_hash`, `user_type`, `active`, and
  `last_login` are unchanged — only `email` moves.
- [x] R6: **`chat_user` left as-is.** Not deleted, not
  deactivated, not renamed. See Design Notes.
- [x] R7: **Login verification.** After creation, both new
  accounts authenticate successfully via
  `UserManager.authenticate()` with the generated password.

## Acceptance Criteria

- [x] AC1: TB's `users.db` contains four active rows after
      this story: `admin` (updated email), `chat_user`
      (unchanged), `tedcorvette`, `sfevers`. All four
      `active=1`.
- [x] AC2: `admin.email = 'operator@example.com'` in
      the DB.
- [x] AC3: `tedcorvette.email = 'tedcorvette@gmail.com'` and
      `sfevers.email = 'sfevers@gmail.com'`.
- [x] AC4: `tedcorvette.user_type = 'super'` and
      `sfevers.user_type = 'super'` (unless operator redirects
      post-execution).
- [x] AC5: `UserManager.authenticate('tedcorvette', <generated>)`
      and `UserManager.authenticate('sfevers', <generated>)`
      both return a user record (not `None`), proving the hash
      stored matches the password.
- [x] AC6: `admin.last_login` is unchanged (no auth
      attempt as part of this story's execution).
- [x] AC7: `UserManager.authenticate('admin', <existing-password>)`
      still succeeds (admin not regressed) — verified by
      inspecting that `password_hash` for admin is unchanged
      pre/post execution.

## Design Notes

- **Why `user_type: super` for Ted and Sam.** TB has three
  roles: `super` (admin), `training` (owns training sets per
  TB-US-011), and `chat` (chat interface only). The humans
  getting accounts here are the same humans who have full
  access on projmgmt (where there is no role system). Super
  matches that parity. If future TB work indicates they should
  have narrower access (e.g. `training` only), the role can be
  changed in one call: `UserManager().update_user_type(username, 'training')`.
  No DB migration needed; the user_type field is just updated.
- **Why `chat_user` stays.** Four reasons:
  1. It's not harming anything (one DB row, no login activity).
  2. The `email` column has no uniqueness constraint, so
     setting admin's email to `operator@example.com` does
     not conflict with `chat_user` carrying the same address.
  3. If TB has (or will have) a chat interface pathway that
     relies on a dedicated chat-role account, keeping the row
     avoids regressing that pathway.
  4. "Deleting a user to tidy up" is exactly the pattern the
     stories-are-documentation principle argues against —
     when in doubt, keep the artifact, flag the decision.
     If a future story determines `chat_user` is dead weight,
     it can be deactivated (`active=0`) under that story's
     scope.
- **Why direct SQL for the email update.** TB's `UserManager`
  exposes `create_user`, `authenticate`, `change_password`,
  `update_user_type`, but **not** `update_email`. Adding a
  method for a one-time admin-email fix is a disproportionate
  change. Using a bounded SQL `UPDATE users SET email = ?
  WHERE username = ?` is simpler and the right scope for this
  story. If an email-update capability becomes a repeat need,
  that's a separate story to add the method properly.
- **Password hashing — current state is weak.** Same posture
  as projmgmt before PM-US-004. TB-US-003 migrates when it
  lands. Accepted here because the stakeholders are trusted,
  the site has a passphrase gate, and TB sits behind
  Cloudflare.
- **Passphrase pattern.** `word-word-word-word-NN` matches the
  pattern established by PM-US-005's `scripts/create_users.py`.
  Entropy is ~39 bits (vs ~18 bits for the 12-char pattern I
  used on Ted's projmgmt reset) — appropriate for a first-
  issue password that may sit for a while before TB-US-003
  rotates it.
- **No companion script committed.** PM-US-005 built
  `scripts/create_users.py` with a wordlist. For TB this
  story runs the equivalent inline from the venv Python
  (two users is below the threshold for a committed script).
  If TB-US-NNN adds a bulk-user-management need later, a
  committed script becomes worthwhile.
- **chat_user and admin now share email.** After R3,
  `admin.email` and `chat_user.email` both equal
  `operator@example.com`. This is intentional (both are
  effectively "Jesse" accounts) and harmless (no uniqueness
  constraint, no notification routing dedup logic exists on
  TB today).

**Completion Notes (2026-10-12).**

Executed inline via TB's venv Python from TB's working
directory (so the relative `users.db` resolved correctly).
Default `PASSWORD_SALT` was in effect (no override in TB's
systemd unit), consistent with how the pre-existing accounts
were hashed.

**Changes applied:**

1. `tedcorvette` created — `id=3`, `user_type=super`,
   `email=tedcorvette@gmail.com`, `active=1`. Generated
   passphrase (not recorded in version control; handed off
   out-of-band).
2. `sfevers` created — `id=4`, `user_type=super`,
   `email=sfevers@gmail.com`, `active=1`. Generated
   passphrase (not recorded in version control; handed off
   out-of-band).
3. `admin` email updated — `admin@localhost` →
   `operator@example.com`. Direct SQL `UPDATE`;
   1 row changed.
4. `chat_user` left as-is, as planned.

**Verification results:**

- `UserManager.authenticate('tedcorvette', <generated>)` →
  returns user record (AC5).
- `UserManager.authenticate('sfevers', <generated>)` →
  returns user record (AC5).
- `admin.password_hash` byte-for-byte identical
  pre/post (AC7 — admin not regressed on auth).
- `admin.last_login` unchanged at 2026-10-05 (AC6 —
  no auth was performed as part of this story's execution).
- `admin.email` = `operator@example.com` (AC2).
- `tedcorvette.email` = `tedcorvette@gmail.com` and
  `sfevers.email` = `sfevers@gmail.com` (AC3).
- `tedcorvette.user_type` = `super` and
  `sfevers.user_type` = `super` (AC4).
- `users.db` final state: 4 active rows (admin,
  chat_user, tedcorvette, sfevers) — AC1.

**Password-handoff tracking (R4):**

Both generated passphrases exist only in this session's chat
transcript and (ephemerally) on the operator's screen. They
must be delivered to Ted and Sam via a separate channel
(SMS, in-person, encrypted email, etc.) before this story's
value is realized operationally. The passwords are not
written to any file in either repo.

**Downstream unblocks:**

- A future TB-side stakeholder-notification story now has a
  real recipient population to route to (three deliverable
  Gmail addresses on `admin`, `tedcorvette`, and
  `sfevers`). That story remains unwritten pending the
  earlier design-decision picks (stakeholder source, subject
  format, scope).
- TB-US-003 (per-user salts) will rehash all four of these
  accounts when it executes, invalidating the current
  SHA-256 hashes and the password-reset path at that time.

**Background correction:** story's Background originally
cited `admin`'s last login as 2026-07-20; actual DB
value at execution was 2026-10-05. Corrected in-place in the
Background section before closure.

## Out of Scope

- **Building a TB user-management UI.** Separate story if
  wanted; this story runs via Python / SQL directly.
- **Deleting or renaming `chat_user`.** Left alone per
  Design Notes.
- **Fixing TB's weak hashing** (SHA-256 + global salt). That
  is TB-US-003, already queued.
- **Enabling MFA, rate limiting, or password reset flow** on
  TB. Not relevant to this story; part of a future IAM arc
  (projmgmt-side PM-US-004 may supersede).
- **Role changes for Ted or Sam.** Default is `super`; a
  change is a one-line call under a different story.
- **TB stakeholder-notification implementation.** This story
  is the *user-list prerequisite* for a notification story;
  the notification story itself remains unwritten pending the
  operator's picks on scope / subject format / stakeholder
  source (recorded earlier in session).
- **Deleting the non-deliverable `admin@localhost` as a
  pattern elsewhere.** This story fixes one row.

## Related

- [TB-US-003](tb-us-003.md) — Per-user password salts. Will
  rehash all accounts including the three touched here.
- [TB-US-010](tb-us-010.md) — In-app user management UI
  (Shipped). This story works around that UI by going through
  `UserManager` + SQL directly (R3's email update isn't
  exposed in the UI).
- [TB-US-011](tb-us-011.md) — Ownership-based training-set
  access for training-role users (Shipped). Informs the role
  model that R1/R2 operate against.
- **PM-US-005** on projmgmt (Completed) — the direct analog
  of this story on the projmgmt side; same user set, same
  weak-auth-plus-future-migration pattern, same OOB password
  delivery.
- **PM-US-017** on projmgmt (Completed) — the stakeholder
  notification implementation on projmgmt. A TB-side notification
  story remains to be written and will consume the users
  created here.
- `backend/api/user_manager.py` — `UserManager.create_user()`
  (R1, R2), direct `UPDATE` for email (R3), `authenticate()`
  (R7, AC5, AC7).
- TB's `users.db` schema — `email` is **not** unique;
  `username` **is** unique; `user_type` is constrained to
  `super | training | chat`.
