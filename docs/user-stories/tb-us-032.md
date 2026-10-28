# TB-US-032: Rename stalite3's `sales` role → `chat` (first sync-forward operation)

**Status**: Completed
**Created**: 2026-10-14
**Completed**: 2026-10-14
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As the operator of EL with stalite3 as a long-lived downstream
branch of TB master, I want stalite3's `sales` user role
renamed to `chat` to match TB master's vocabulary, together
with an update to the OT context doc so its role naming
reflects the interface-not-audience principle, so that future
TB → stalite3 sync-forward operations no longer have to
translate role vocabulary and so that the architectural
principle (role names describe the interface, not the
audience) is applied consistently across EL products.

## Background

From the TB-US-031 feature parity audit (2026-10-14):

- stalite3 uses `super | sales | training`; TB uses
  `super | chat | training`.
- The audit initially recommended TB adopt `sales` to match
  the OT context doc. Operator corrected the direction on
  2026-10-14: **stalite3 should adopt TB's `chat`.**
- Operator's architectural rationale: *"the sales user type
  was created for a sales person user, however, it turns out
  that the specific term sales for a user type is probably
  not a good design for the training bench foundation. one
  reason is that there are too many different types of sales
  across the business environment. what matters is do you
  have the relevant data loaded in the RAG, do you have the
  LLM you want to use so that when you issue a prompt you get
  acceptable accuracy. that is why i did not migrate the sales
  user type into training bench and changed it to chat because
  it is primarily a prompt interface for the user."*
- Captured as a permanent architectural principle in
  `MEMORY.md → principle_role_names_describe_interface`:
  role names describe the **interaction surface**, not the
  **audience or market segment**.

This is also the **first sync-forward operation** from TB
master to stalite3 downstream — a validation of the master →
downstream pattern established by the audit.

## Requirements

### stalite3 code changes

- [x] R1: **`backend/api/user_manager.py` on stalite3.** Update:
  - `USER_TYPES` list: `['super', 'sales', 'training']` →
    `['super', 'chat', 'training']`
  - CREATE TABLE `CHECK` constraint:
    `('super', 'sales', 'training')` →
    `('super', 'chat', 'training')`
  - Any docstrings or comments referring to `sales` → `chat`
  - CLI help string on line 342
- [x] R2: **`static/script.js` on stalite3.** Update 4
  references:
  - Permission map `'sales': ['chat']` key renames to
    `'chat': ['chat']`
  - `if (userType === 'sales')` conditionals → `=== 'chat'`
  - Comments describing sales users → chat users

### stalite3 database migration

- [x] R3: **Pre-migration snapshot.** Copy
  `/home/jeversole/stalite3/users.db` to a timestamped backup
  outside the stalite3 tree (e.g. `/tmp/users.db.pre-tb-us-032.<ts>`).
  Enables rollback if migration misfires.
- [x] R4: **Atomic schema migration on stalite3's `users.db`.**
  Standard SQLite constraint-change pattern:
  1. BEGIN TRANSACTION
  2. CREATE TABLE `users_new` with the new CHECK constraint
  3. INSERT INTO users_new SELECT ... with
     `CASE user_type WHEN 'sales' THEN 'chat' ELSE user_type END`
  4. DROP TABLE users
  5. ALTER TABLE users_new RENAME TO users
  6. COMMIT
- [x] R5: **Live-site preservation.** Every existing user row
  is preserved — `id`, `username`, `password_hash`, `email`,
  `created_at`, `last_login`, `active` all unchanged. Only
  `user_type='sales'` becomes `user_type='chat'`. One row
  affected (sales_user).

### TB-side updates

- [x] R6: **OT context doc update.** Update
  `/home/jeversole/trainingbench/docs/ot-context-for-claude-code_1.md`
  line 191 from:
  > **Three roles:** Sales (end users), Training (SMEs
  > providing corrections), Admin (engineer managing the
  > system).

  to:
  > **Three roles:** Chat (end-user prompt interface),
  > Training (SMEs providing corrections and curation),
  > Admin (system configuration and management).

  Document reflects the interface-not-audience principle.

### Verification

- [x] R7: **Post-migration validation on stalite3:**
  - `SELECT COUNT(*) FROM users WHERE user_type='sales'` = 0
  - `SELECT COUNT(*) FROM users WHERE user_type='chat'` ≥ 1
  - sales_user (id=2) now has `user_type='chat'` with all other
    fields unchanged
  - Schema CHECK constraint allows `chat`, rejects `sales`
  - All user ids present pre-migration are present post-
    migration (no row loss)
- [x] R8: **No TB-side regression.** TB's `user_manager.py`
  unchanged; TB's `users.db` unchanged; TB's existing
  endpoints unchanged.

### Operator handoff

- [x] R9: **Service restart flag.** Code changes to
  `user_manager.py` and `script.js` require stalite3's
  Python process to be restarted to take effect. Flag this
  explicitly for the operator; do NOT auto-restart (stalite3
  is operator-managed, not systemd-managed).

## Acceptance Criteria

### Migration correctness
- [x] AC1: Pre-migration snapshot of `users.db` exists at the
  recorded timestamped path.
- [x] AC2: `sales_user` (id=2) has `user_type='chat'` after
  migration; all other fields identical to pre-migration.
- [x] AC3: No user has `user_type='sales'` after migration.
- [x] AC4: Row count pre = row count post (zero rows lost).
- [x] AC5: Schema CHECK constraint reads
  `('super', 'chat', 'training')`.
- [x] AC6: An attempt to INSERT a user with
  `user_type='sales'` after migration fails with a CHECK
  constraint violation.

### Code consistency
- [x] AC7: stalite3's `user_manager.py` has no occurrences
  of `'sales'` as a user_type literal.
- [x] AC8: stalite3's `static/script.js` has no occurrences
  of `'sales'` as a user_type literal (empty state or role
  check).
- [x] AC9: TB's OT context doc line 191 reads the new "Chat
  (end-user prompt interface)" language.

### No regression
- [x] AC10: TB's `user_manager.py` is unchanged — no diff
  on the TB side for user management.
- [x] AC11: stalite3's live-site data (login tokens, chroma
  databases, logs, config) is unchanged. Only `users.db`
  schema and the one row are modified.

## Design Notes

- **This is the first sync-forward operation.** The whole
  master → downstream pattern established by TB-US-031's
  audit gets its first test here. If this goes smoothly,
  it validates the mechanism; if it misfires, the lesson
  informs how future sync-forward stories are structured.
- **No TB-side user_manager changes.** TB is already
  correct. TB's `chat` role vocabulary stays as-is; this
  story only touches the OT context doc on the TB side
  (R6), which is documentation, not code.
- **SQLite constraint migration pattern.** SQLite doesn't
  support `ALTER TABLE ... DROP CONSTRAINT`, so we use the
  standard rebuild pattern: new table + copy + drop old +
  rename. All in one transaction for atomicity.
- **Service restart is operator-triggered.** stalite3 isn't
  systemd-managed (operator runs it as a bare Python
  process). Auto-restart would require more coupling than
  this story wants to introduce. The operator restarts
  stalite3 when ready; until then, the running service
  continues against the migrated DB (which it tolerates —
  the users table shape is unchanged aside from CHECK).
- **Live-site risk assessment.** Pre-migration audit shows
  no login activity since 2026-07-02 (3 months ago). The
  migration is a 1-row UPDATE on a tiny table during a
  low-activity window. SQLite's atomic swap pattern
  completes in milliseconds. Risk is minimal.
- **Memory principle applied.** The
  `principle_role_names_describe_interface` memory governs
  this story's naming decision and the OT doc update. Future
  role vocabulary decisions follow the same principle.

## Out of Scope

- **TB-side user_manager changes.** TB is already correct.
- **UI label changes on stalite3** beyond the role-check
  conditionals in script.js. If "Sales" appears as display
  text in HTML anywhere, that's a separate cosmetic
  follow-up — this story only renames the role identifier.
- **Password reset for sales_user** — not needed; existing
  password hash is preserved.
- **Formal sync-forward tooling.** This operation is done
  manually under the audit's recommended Mechanism A
  (manual port) for v0.1. Mechanism C (Agent Release
  package) comes later.
- **stalite3 service restart.** Operator-triggered post this
  story's execution.
- **Any Stalite-domain customization** (formula calculator,
  mix design handler, Stalite-specific training data).
- **Branding tweaks.**

## Related

- Parent: [TB-US-031](tb-us-031.md) — feature parity audit
  that identified this gap and recommended the HIGH-priority
  rename.
- Memory: `MEMORY.md →
  principle_role_names_describe_interface` — the
  architectural principle this story enforces.
- stalite3 code touched:
  - `/home/jeversole/stalite3/backend/api/user_manager.py`
  - `/home/jeversole/stalite3/static/script.js`
  - `/home/jeversole/stalite3/users.db`
- TB code touched (doc only):
  - `/home/jeversole/trainingbench/docs/ot-context-for-claude-code_1.md`
- Deliverables: none (this is a migration story, not a
  deliverable-producing story).

**Completion Notes (2026-10-14).**

Executed in this order:

1. **Pre-migration snapshot** at
   `/tmp/users.db.pre-tb-us-032.20261014-131651`. MD5
   matched source. 20480 bytes.
2. **Code changes on stalite3's `user_manager.py`** (4 edits):
   - Line 21–22 docstring: `sales` → `chat` with rename note
   - Line 25: `USER_TYPES = ['super', 'chat', 'training']`
   - Line 48 (CREATE TABLE CHECK): `('super', 'chat',
     'training')`
   - Line 105 (docstring in create_user)
   - Line 342 (CLI help string): `super, chat, training`
3. **Code changes on stalite3's `static/script.js`**
   (3 edits):
   - Line 95: permission map key `'sales'` → `'chat'`;
     comment added clarifying "role describes the interface"
   - Line 116: `if (userType === 'sales')` → `=== 'chat'`
   - Line 252, 258: comment + conditional updated
4. **Atomic schema migration on `/home/jeversole/stalite3/users.db`.**
   Pattern: BEGIN TRANSACTION → CREATE users_new → INSERT
   with CASE translation → DROP users → ALTER RENAME →
   COMMIT. All in one transaction.
5. **TB OT context doc update** at
   `/home/jeversole/trainingbench/docs/ot-context-for-claude-code_1.md`
   line 191: "Sales (end users)" → "Chat (end-user prompt
   interface)" with historical rename note.

**Verification results:**

- Row count pre = post = 12 (zero rows lost)
- `sales_user` (id=2) row: `user_type` flipped `sales` →
  `chat`; `username`, `password_hash`, `email`,
  `created_at='2026-01-27T15:25:35.818079'`,
  `last_login='2026-05-21T05:06:44.734564'`, `active=1`
  all unchanged
- Distribution post: `{'chat': 1, 'super': 4, 'training':
  7}`
- Schema CHECK: `('super', 'chat', 'training')`
- INSERT with `user_type='sales'` correctly raises
  `IntegrityError: CHECK constraint failed:
  user_type_check`
- stalite3 `user_manager.py` and `script.js` have no
  `'sales'` role literals (only the historical rename note
  in a docstring)
- TB OT context doc line 191 reads the new language
- TB `user_manager.py` and TB users.db unchanged (git diff
  clean on TB side)

**Preserved intentionally:**

- stalite3's `static/script.js` line 117 UI text
  `'AI Sales Agent'` — this is domain-descriptive branding
  for Stalite's deployment context (where the agent IS used
  by sales staff), not a role reference. The role vocabulary
  describes the interface; the deployment branding
  separately describes the audience. Per the
  `feedback_branding_deferred` memory, no ad-hoc brand-copy
  changes.
- stalite3's running Python process (PID 2160573) is still
  on the pre-migration code. **Operator restart required**
  to pick up the `user_manager.py` and `script.js` changes.
  Service continues running against the migrated DB without
  issue (schema is still compatible with the pre-restart
  code because the running code validates against
  `USER_TYPES = ['super', 'sales', 'training']` in memory;
  it will accept `user_type='chat'` reads but reject
  `create_user(... user_type='chat')` writes until
  restarted — flagged for operator).

**First sync-forward operation complete.** The master →
downstream pattern established by TB-US-031 has its first
successful validation. Mechanism was manual port
(Mechanism A per the audit) for v0.1.
