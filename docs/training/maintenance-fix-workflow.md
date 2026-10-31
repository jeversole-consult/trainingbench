# Maintenance Fix Workflow

How to ship a bug fix to TrainingBench post-release. This is the
operational pattern for anyone — maintainer or contributor — who
has to fix something after v0.1 is public.

**Companion doc**: [`upgrade-publishing-workflow.md`](upgrade-publishing-workflow.md)
for feature releases + version cuts. This doc is specifically for
single-issue surgical fixes.

**Audience**: TrainingBench maintainers + contributors shipping
fixes. Not for end users operating a TB install.

## When to use this doc

Use this workflow when **all of these** are true:

- A bug exists on `main` (or a tagged release) that needs
  correcting
- The fix fits in one logical commit (one file to a handful of
  files, one clear "what broke + how we fixed it")
- No new feature capability is being added
- SemVer impact is **patch bump** (e.g., `v0.1.0 → v0.1.1`)

If the change adds a new feature, that's a feature arc with its
own story. If the fix is sprawling or needs multiple
coordinated commits across subsystems, consider splitting it OR
treating it as a mini-release.

For bigger shipping concerns (RC cycles, release notes, Pages
publishing), read [`upgrade-publishing-workflow.md`](upgrade-publishing-workflow.md).

## The 9-phase workflow

Each phase has an artifact (what you produce), a done-signal
(how you know you're ready to move on), and common pitfalls.
The whole chain traces from "we saw a bug" to "the fix is live
and verified downstream".

### Phase 1 — Observe

Someone noticed something wrong. Capture the specifics before
losing context.

- **Artifact**: an entry in a review doc, a note on an open
  story, or a direct report (comment, issue, Slack message)
  with:
  - Reproduction steps
  - Expected behavior
  - Actual behavior
  - Where it was surfaced (which test, which install, which
    commit)
- **Done-signal**: a future reader could re-produce the bug
  from the write-up alone, without additional conversation
- **Pitfall**: skipping this and jumping to a fix. Without an
  observation record, future-you can't tell whether the fix
  actually addressed the right thing.

**Example**: TB-US-071's bug was observed during TB-US-068
Phase C WSL rehearsal and captured as finding F5 in
`docs/release/v0.1.0-rc1-rehearsal-review.md` *before* any
fix was proposed.

### Phase 2 — Draft

Write a story file for the fix. This is where the bug becomes
tracked work.

- **Artifact**: `docs/user-stories/tb-us-NNN.md` with:
  - Status `Proposed`
  - Clear reproduction steps (copy from Phase 1)
  - Root cause (specific file + line reference if known)
  - Proposed fix shape (surgical diff, not a rewrite plan)
  - Dependencies / blocks (usually "self-contained")
  - Requirements list + acceptance criteria
  - A BACKLOG.md row referencing the story
- **Done-signal**: story file + BACKLOG row land uncommitted
  on local tree; notification pipeline fires for the Proposed
  state
- **Pitfall**: drafting a fix without pinning the root cause.
  "The login page is broken" is not a draft; "login.js line 9
  short-circuits to gate.html when `gate_token` is missing"
  is.

### Phase 3 — Fire

Flip the story from `Proposed` → `In Progress`. Signals to any
other maintainer that work is now active on this.

- **Artifact**: status update in the story file + Started date
  added; notification fires to active users
- **Done-signal**: anyone looking at BACKLOG or the story file
  sees it as In Progress
- **Pitfall**: fixing something without firing first. Then the
  notification pipeline either doesn't send, or sends
  mis-sequenced events (Completed before In Progress).

### Phase 4 — Fix

Edit the code. Keep it surgical.

- **Artifact**: minimal diff that addresses the root cause from
  Phase 2's draft. One file or a small set.
- **Done-signal**: `git diff` shows only intentional changes;
  no stray reformatting or scope creep
- **Pitfall**: fixing adjacent code "while you're there". Each
  additional change weakens the attribution ("did the fix work,
  or did the other change help?"). Note secondary issues, draft
  separate stories.

**Also apply**: if the fix touches a frontend static file that
browsers may cache, bump the `?v=...` cache-bust tag on
whatever HTML files reference it. See TB-US-071 for an example
(`static/login.html` bumped alongside `static/login.js`).

### Phase 5 — Commit

Land the fix on `main` with a story-prefixed commit message.

- **Artifact**: commit with:
  - **First line**: `TB-US-NNN: <short title>` (prefix lets
    `git log --grep="TB-US-NNN"` find every related commit
    later)
  - **Body**: what broke, how we fixed it, where it was
    surfaced, any related story references
  - Trailing `Co-Authored-By:` line if Claude Code helped
- **Done-signal**: `git log --oneline -1` shows the new HEAD
  with the TB-US prefix
- **Pitfall**: committing just the code fix and leaving the
  story-file state edits (ticks on Rs/ACs) for a separate
  commit later. **Land the story file's close-state ticks in
  the same commit as the fix** so a `git show <sha>` tells the
  whole story. TB-US-071 split this across two commits by
  mistake; TB-US-074 corrected it.

### Phase 6 — Push

Make the fix visible on the remote.

- **Artifact**: `git push origin main` succeeds
- **Done-signal**: `git log origin/main` includes the new SHA
- **Pitfall**: pushing to a stale remote (someone else pushed
  while you were working). If push rejects, pull + reconcile
  before trying again. Avoid force push on `main`.

### Phase 7 — Downstream verify

Prove the fix works downstream — not just on the machine that
produced the commit. The "downstream" could be a throwaway
clone, a separate install, or a different machine.

- **Artifact**: evidence that the fix works on a tree pulled
  from `origin/main`:
  - `git pull` on the downstream tree
  - Rerun whatever reproduced the original bug (Phase 1)
  - Confirm it no longer reproduces
- **Done-signal**: the exact reproduction steps from Phase 1
  no longer trigger the bug on a freshly-pulled downstream tree
- **Pitfall**: declaring victory based only on the author's
  local tree where the fix was authored. Code can work there
  for environmental reasons unrelated to the fix.

**Example**: TB-US-071's fix was pulled on the WSL rehearsal
tree + the login page rendered directly in the browser
without manual localStorage intervention. That was the
downstream verification — the fix worked on a tree that
wasn't the author's.

### Phase 8 — Close

Mark the story Completed. Fires the final notification.

- **Artifact**:
  - Story file: status `Completed`, Completed date added,
    commit hash recorded, Rs + ACs ticked
  - BACKLOG.md row updated with the completion summary
  - Notification pipeline fires for the Completed state
- **Done-signal**: BACKLOG shows the story as Completed with
  the commit reference; anyone can click through to the story
  file for the fix details
- **Pitfall**: closing before Phase 7. If the fix doesn't
  verify downstream, closing is premature — reopen or draft
  a follow-up.

### Phase 9 — Review-doc update

If the bug was captured in a review doc (release rehearsal,
acceptance sweep, etc.), update that doc to mark the finding
as ✅ resolved with the commit hash.

- **Artifact**: review doc edit changing the finding line from
  🔴/🟡 open to ✅ resolved, with a reference like `fixed in
  commit 89478e5 as TB-US-071`
- **Done-signal**: a reader of the review doc immediately sees
  the finding is addressed; they can click through to the
  commit for details
- **Pitfall**: skipping this. Later readers of the review doc
  will think the finding is still open and waste cycles
  investigating.

## SemVer impact

Maintenance fixes almost always warrant a **patch bump**:

| Change | SemVer | Example |
|---|---|---|
| Bug fix, no behavior change | PATCH | `v0.1.0 → v0.1.1` |
| Breaking fix (changes API) | MINOR for `0.x`; MAJOR for `1.x+` | `v0.1.0 → v0.2.0` |
| Fix that adds a tiny new flag | MINOR | `v0.1.0 → v0.2.0` |

If uncertain, patch is the safe default. If the fix changes
public API shape (not just internals), bump a minor level.

Release-cut mechanics (tagging, GitHub Release draft, Pages
rebuild) live in [`upgrade-publishing-workflow.md`](upgrade-publishing-workflow.md).

## Commit message convention

```
TB-US-NNN: <imperative title, under 70 chars>

<2-5 line body: what broke, how we fixed it, where it was surfaced>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

- **Imperative mood** in the title (`fix`, `remove`, `add`),
  not past tense
- **Reference the story** so grep works
- **Body explains WHY**, since `git diff` shows WHAT
- **Co-Authored-By** when Claude Code did substantive work

## Cache-bust discipline (frontend fixes)

Browsers cache static files aggressively by URL. A fix to
`static/login.js` won't reach an operator with the old file
cached unless the file's URL changes.

TB uses a `?v=YYYYMMDDx` query string on `<script>` tags in HTML
files. Bump the suffix when the referenced file changes:

```diff
- <script src="login.js?v=20261021a"></script>
+ <script src="login.js?v=20261028a"></script>
```

Any HTML file that references the changed JS file needs this
bump — grep for the filename to find them.

## Downstream verification pattern

Downstream verification is the second-to-last phase for a
reason: it's where fixes actually prove themselves.

The pattern:

1. Find or create a tree that didn't have the fix locally
2. `git pull origin main`
3. Run the reproduction steps from Phase 1
4. Confirm the bug no longer reproduces
5. Document the reproduction attempt + outcome

Downstream can be:

- A throwaway clone on the same machine
- A different machine (WSL, lab machine, teammate's laptop)
- A fresh `git clone` into a new directory
- A deployed instance pulled from origin

What matters: the tree being verified against **wasn't the
one where the fix was authored**. A fix that works only on the
authoring tree isn't verified — environmental state could be
masking the bug.

## When a fix needs to backport to a stable branch

**v0.1 scope**: TB is single-branch (`main`). Backports are
out of scope.

**Future (post-v1.0)**: if TB adopts a stable-branch model,
this doc will need an "Also push to stable" phase. Draft that
as a dedicated story when it's time.

## Worked examples

Two bugs went through this exact workflow during the TB-US-068
private release-cut rehearsal:

### Worked example 1 — TB-US-071 (login.js gate-redirect)

**Observed**: TB-US-068 Phase C WSL rehearsal; browser landed
at gate.html with "Gate verification not enabled" instead of
reaching the login page.
**Draft**: `docs/user-stories/tb-us-071.md`, status Proposed.
**Fire**: status → In Progress; notification pipeline fired.
**Fix**: `static/login.js` — removed the pre-fetch
short-circuit; `/auth/check-gate` is now the authoritative
decision point. Cache-bust bumped on `static/login.html`.
**Commit**: `89478e5 TB-US-071: fix login.js unconditional
gate redirect`.
**Push**: landed on `origin/main`.
**Downstream verify**: `git pull` on operator's WSL rehearsal
clone + browser retest; login page loaded directly, no manual
localStorage intervention needed.
**Close**: TB-US-071 → Completed with commit hash `89478e5`.
**Review-doc update**: F5 marked ✅ resolved in
`docs/release/v0.1.0-rc1-rehearsal-review.md`.

### Worked example 2 — TB-US-074 (train.py logging_dir kwarg)

**Observed**: TB-US-072 lab-machine acceptance sweep; smoke
training subprocess died with `TypeError: TrainingArguments.
__init__() got an unexpected keyword argument 'logging_dir'`.
**Draft**: `docs/user-stories/tb-us-074.md`, status Proposed.
**Fire**: status → In Progress; notification pipeline fired.
**Fix**: `training/math/train.py` — one-line removal of
`logging_dir=str(logs_dir / "gsm8k")` from the
`TrainingArguments(...)` constructor. `report_to="none"` is
already set, so no logging backend writes anywhere.
**Commit**: `f9366d5 TB-US-074: remove logging_dir kwarg
incompatible with transformers 5.x`.
**Push**: landed on `origin/main`.
**Downstream verify**: `git pull` on the acceptance install
tree; retried the smoke training launch; subprocess reached
the training loop, hit `logging_steps=50` boundaries,
completed in 20s with the correctly-nested hyperparameters
API shape, adapter files written to disk, adapter
auto-registered as `adapter_versions.v1`.
**Close**: TB-US-074 → Completed with commit hash `f9366d5`.
**Review-doc update**: F9 marked ✅ resolved in the review doc.

### What the two walks shared

- Same 9 phases, same artifact at each
- Both fit in a single-file surgical fix
- Both verified downstream before closure
- Both landed as `TB-US-NNN:`-prefixed commits
- Both updated the review doc that originally surfaced the bug

### What they differed on (and the lesson)

TB-US-071 split story-file close-state edits across two
commits (fix commit vs. closure commit). TB-US-074 landed the
story-file ticks in the same commit as the code fix. **The
TB-US-074 approach is preferred.**

## References

- Story-driven development principles: `CONTRIBUTING.md`
- Companion doc: [`upgrade-publishing-workflow.md`](upgrade-publishing-workflow.md)
- Worked example stories: `docs/user-stories/tb-us-071.md`,
  `docs/user-stories/tb-us-074.md`
- Review docs that surfaced the two example bugs:
  `docs/release/v0.1.0-rc1-rehearsal-review.md`
