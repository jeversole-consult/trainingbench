# Upgrade Publishing Workflow

How to cut a feature release of TrainingBench. This is the
operational pattern for publishing a feature-upgrade release
(minor or major), with the private-rehearsal pattern that
precedes the public cut.

**Companion doc**: [`maintenance-fix-workflow.md`](maintenance-fix-workflow.md)
for single-issue bug fixes between releases. This doc is
specifically for release cuts.

**Audience**: TrainingBench maintainers responsible for shipping
versioned releases. Not for contributors fixing individual bugs.

## When to use this doc

Use this workflow when **any** of these is true:

- A multi-story feature arc has completed and you want to cut a
  new version
- The accumulated changes on `main` since the last tag warrant
  a release
- You're cutting the first public release
- You're cutting a release-candidate (RC) before a public cut

For single-issue bug fixes between releases, use the
[maintenance-fix workflow](maintenance-fix-workflow.md) instead.

## Pre-release checklist

Before cutting anything, walk this checklist. Any ❌ item either
blocks the release or spawns a follow-up fix.

- [ ] All stories in the arc are **Completed** on BACKLOG
- [ ] `main` HEAD matches what you intend to tag
- [ ] Working tree is clean (`git status` → nothing uncommitted)
- [ ] `origin/main` is in sync with local `main` (no unpushed
      commits, no untracked remotes to reconcile)
- [ ] All known-blocking bugs are either fixed or formally
      scope-deferred with story-level documentation
- [ ] All operator-personal information (emails, usernames,
      hostnames) has been redacted from file content (TB-US-068
      Phase A pattern)
- [ ] Any new user-facing docs reference the right version
      numbers
- [ ] The install path has been walked literally by someone
      who's not the author (acceptance pass; see TB-US-072)

## The private-rehearsal pattern

The private rehearsal is a dress rehearsal of the whole
release-cut flow, done against a private repo first so mistakes
don't become public git history.

**This is TB-US-068's whole structure.** Running the pattern:

### Phase A — Audit what git knows

Before committing or tagging anything, see what the repo
actually contains:

- `git status` — what's modified, what's untracked
- `git ls-files` — what's tracked (would ship if the repo
  went public today)
- `git ls-files --others --ignored --exclude-standard` — what's
  gitignored (should include DBs, secrets, caches, large
  model binaries)

Audit for:
- Sensitive files in the tracked list (`.env`, `*.db`, secret
  keys, operator-personal docs)
- Stale directories from older arcs (e.g., TB-US-068 found
  `openclaw/` and `docs/user/`)
- PII in commit history vs. content — redaction can address
  content but not git author/committer fields

Fix sensitive-file leaks BEFORE committing anything.

### Phase B — Commit the uncommitted work

Group the arc's uncommitted work into **logical commits** —
one commit per logical unit, each with a story-prefixed
message. Not one giant snapshot.

TB-US-068's 5-commit grouping (as a reference):
1. `chore: expand .gitignore + env scaffold + deps`
2. `feat(backend): versioned components + agents + first-run`
3. `feat(ui): drawer nav + admin modals + first-run + training strip`
4. `feat: math-example first-install artifacts (TB-US-057)`
5. `docs: README + INSTALL + CONTRIBUTING + Jekyll Pages +
    full story history`

Each commit message body lists the stories it touches so
`git log --grep=TB-US-NNN` later locates every related
commit.

Push to `origin/main`.

### Phase C — Fresh-install dress rehearsal

Clone the just-pushed repo into a **throwaway directory** on
the same machine (or a different machine for extra rigor).
Walk the INSTALL doc **literally** from scratch:

- `git clone` into the throwaway dir
- Set up a fresh venv
- Install dependencies
- Configure `.env` (use a different APP_PORT to avoid
  collision with any live service)
- Start the backend
- Walk the first-run flow (auto-generated password, forced
  change, Chat tab)
- Smoke-test any training/experiment paths

**Any step that fails** — stop and either fix the doc or fix
the code. Repeat Phase B for any fix commits before continuing.

Cleanup afterward: kill the backend, remove the throwaway dir,
verify the port is freed, confirm no live service was
affected.

TB-US-072's `docs/release/ui-acceptance-checklist-template.md`
is the reusable template for this phase.

### Phase D — Tag a release candidate

Standard semver convention:

- `vX.Y.Z-rc1`, `vX.Y.Z-rc2`, ... for release candidates
- `vX.Y.Z` for the actual cut

```bash
git tag -a v0.1.0-rc1 -m "<multi-line summary of what's in it>"
git push origin v0.1.0-rc1
```

The tag message should capture **what's in the release at a
high level**: major features shipped, deliberate deferrals,
known caveats. Future readers browsing GitHub Releases will
see this message as the default release note body.

### Phase E — Enable Pages privately

If the release includes Jekyll Pages content (as v0.1 does
per TB-US-060):

- Repo Settings → Pages → Source: `Deploy from a branch`,
  branch `main`, folder `/docs/pages`
- Save → GitHub Actions runs the Pages build
- Visit the Pages URL (visible only to authenticated
  collaborators on a private repo)
- Click through all pages; confirm layout + nav + styling
  work

If the Pages build fails, iterate on `docs/pages/` content +
re-push; the CI workflow re-runs automatically.

### Phase F — Stranger-eye review

Someone (ideally not the primary author) reads the docs from
scratch, as if they'd never seen the project:

- README: answers "what is this?" / "who is it for?" / "how
  do I install?" in two minutes?
- INSTALL: would a stranger reach a working install by
  following literally?
- Pages site: do cross-links resolve? Are prose + numbers
  current?
- Any references to specific user accounts, hostnames,
  internal URLs that leaked past Phase A redaction?

Notes land in a review doc at
`docs/release/<version>-rehearsal-review.md` (see TB-US-068's
example at
`docs/release/v0.1.0-rc1-rehearsal-review.md`). Classify
findings by severity:

- 🔴 Blocking (must fix before cut)
- 🟡 Should-fix (fix if easy; else follow-up story)
- 🟢 Nice-to-have (defer unless trivial)

### Phase G — Decide

Based on the Phase F review:

- **If 🔴 blockers**: fix them (using the
  [maintenance-fix workflow](maintenance-fix-workflow.md)),
  then cut `rc2`, repeat Phases D–F
- **If 🟡/🟢 only**: proceed to public cut OR document the
  fixes as follow-up stories and proceed anyway (operator
  judgment)
- **If accumulating fixes without closure**: time-box — set a
  decision deadline and stick with it

## The public cut

Once the private rehearsal passes:

### Promote the tag

Either reuse the last `rcN` tag or create a new tag without
the `-rcN` suffix:

```bash
# Option A: just push rc1 as-is (if rc1 passed Phase G cleanly)
git push origin v0.1.0-rc1

# Option B: new tag at the same commit for the "official" cut
git tag -a v0.1.0 <sha-of-rc1-commit> -m "<release notes>"
git push origin v0.1.0
```

Convention: for v0.1 shipping as an early-access release, Option
A is fine — the `-rc1` suffix signals the release's maturity
honestly. For later versions aiming at stability, Option B
produces a clean `vX.Y.Z` tag.

### Draft and publish the GitHub Release

- Repo → Releases → `Draft a new release`
- Choose the tag
- Title: `TrainingBench v0.1.0` (or `v0.1.0-rc1`)
- Body: start from the tag message; expand with:
  - **What's new** (features shipped)
  - **What's deliberately deferred**
  - **Known issues** (if any)
  - **Install path**: link to INSTALL.md
- Attached assets: v0.1 scope is adapter-local
  (TB-US-054 decision), so no model/weight attachments
  expected
- Publish

### Enable Pages publicly

- Repo Settings → Pages: already enabled from Phase E
- Flip repo visibility `Private` → `Public` (Settings →
  General → Danger Zone → Change repository visibility)
- Pages URL now resolves without authentication
- Spot-check the Pages site from an incognito window to
  confirm public visibility

### Post-release

- Announce (if applicable): internal channels, external
  announcement, social
- Monitor Issues / Discussions for operator-reported bugs
- Any surfaced bug → use the
  [maintenance-fix workflow](maintenance-fix-workflow.md)

## Tagging convention

### Semantic versioning for TB

| Change type | Pre-1.0 | Post-1.0 |
|---|---|---|
| Breaking change | Minor bump (`0.1.0 → 0.2.0`) | Major bump (`1.0.0 → 2.0.0`) |
| New feature, backward compatible | Minor | Minor |
| Bug fix, backward compatible | Patch | Patch |

Pre-1.0 (where we are) treats minor as the breaking boundary.
This matches the SemVer spec's "under rapid development" phase.

### RC vs. final

Use `-rcN` suffix for release candidates. Reserve the plain
`vX.Y.Z` tag for releases that actually passed a Phase F
review clean. Don't apply the plain tag retroactively — if
`rc1` passed, push `rc1` publicly; if `rc1` had blockers and
needed `rc2`, publish `rc2` or the subsequent plain tag.

### Alpha / beta tags

- `vX.Y.Z-alphaN` — experimental, incomplete; expect breakage
- `vX.Y.Z-betaN` — feature-complete but still rough
- `vX.Y.Z-rcN` — ready for public, pending final rehearsal
- `vX.Y.Z` — released

Pre-v0.1 we skipped alpha/beta and jumped straight to `rc1`
because v0.1 is already an "early access" release.

## Pages publishing details

TB-US-060 shipped a Jekyll Pages scaffold at `docs/pages/`.
When any content under there changes and gets committed to
`main`:

- `.github/workflows/pages-build.yml` fires on push
- GitHub's Pages build pipeline also fires
- Both must succeed for the site to update

If either fails, check:
- Workflow logs on GitHub Actions tab
- `_config.yml` syntax
- Any new `.md` files have valid frontmatter

## Worked example — TB-US-068 (private rehearsal for v0.1)

The private-rehearsal pattern was walked end-to-end for
v0.1.0-rc1:

**Phase A (audit)**:
- `git status` showed 23 modified + 60+ untracked files
- Operator PII found in 14 docs — redacted
  (`admin_41727` → `admin`, personal email → placeholder)
- Stray `openclaw/` + `docs/sync/` dirs identified; removed
- Branch renamed `master` → `main`
- GitHub repo `jeversole-consult/trainingbench` created
- SSH key setup + routed via `~/.ssh/config`
- Remote `origin` added via SSH

**Phase B (commit)**:
- 5 commits + 1 openclaw cleanup commit
  (`049fc3f`, `697e650`, `fe52418`, `5a8135f`, `31d6a8a`,
  `576c39e`)
- Each commit grouped by logical area, referencing the stories
  touched in its message body
- All pushed to `origin/main`

**Phase C (fresh-install rehearsal)**:
- Clone into `~/tb-rehearsal/trainingbench/` on same host
- Walked INSTALL Steps 2–5 literally; discovered F1 (env
  export gap) + F2 (password-banner surfacing timing)
- `curl`-based R9 verification; UI index served correctly
- R10 cleanup: removed the throwaway dir
- Additional WSL pass surfaced F5 (🔴 login.js gate-redirect)
  → fixed as TB-US-071 using the maintenance-fix workflow

**Phase D (tag)**:
- `v0.1.0-rc1` tag created with multi-line release-notes
  body
- Pushed to origin

**Phase E/F/G (rolled forward)**:
- Pages enablement + stranger-eye review deferred to the
  TB-US-005 public cut
- TB-US-072 picked up the UI acceptance work on the lab
  machine (comprehensive click-through) — found F9
  (🔴 train.py logging_dir) → fixed as TB-US-074 using the
  maintenance-fix workflow
- Phase G decision made: proceed to TB-US-005 for public
  cut; not iterating as `rc2`

**Key learnings**:
- Group commits by logical area, not by single story
- The private rehearsal catches bugs that would be
  embarrassing in public history
- Phase C's fresh-install walk is where INSTALL.md
  shortcomings become visible
- Operator-run acceptance (not the primary author) is the
  highest-signal step

## Checklist for the actual cut day

Day-of release:

- [ ] All Phase A audit items green
- [ ] All Phase F review-doc findings addressed or
      scope-deferred with story-level documentation
- [ ] Tag pushed to `origin`
- [ ] GitHub Release draft published
- [ ] Repo visibility flipped to Public (if applicable)
- [ ] Pages site visible without authentication (if
      applicable)
- [ ] Announcement made (if planned)
- [ ] Post-release monitoring enabled

## References

- Story-driven development principles: `CONTRIBUTING.md`
- Companion doc:
  [`maintenance-fix-workflow.md`](maintenance-fix-workflow.md)
- Worked example: TB-US-068 (private release-cut rehearsal
  for v0.1.0-rc1)
- Review doc from TB-US-068:
  `docs/release/v0.1.0-rc1-rehearsal-review.md`
- Reusable UI acceptance checklist from TB-US-072:
  `docs/release/ui-acceptance-checklist-template.md`
- Pages scaffold: TB-US-060
- README/INSTALL/CONTRIBUTING: TB-US-061
