# TB-US-068: Private v0.1 release-cut rehearsal

**Status**: In Progress
**Created**: 2026-10-24
**Started**: 2026-10-25
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As the TrainingBench maintainer, I want to **rehearse the full
release-cut process on the private repo first** — committing the
uncommitted work, tagging a release candidate, enabling Pages, and
doing a stranger-eye review — so that when TB-US-005 cuts the real
v0.1 public release, I know every step works and I understand what
each one does. Nothing goes public in this story.

## Background

Several weeks of story work (TB-US-048, TB-US-049, TB-US-050, TB-US-051
through TB-US-056, TB-US-057 Phase A, TB-US-059 through TB-US-066,
TB-US-061, TB-US-063, TB-US-064, …) have landed in the working tree
but have **not been committed to git**. At time of writing there are
36+ files modified or new. Before anything can ship publicly, these
need to be committed, the repo state needs to match what we think it
is, and the release-cut flow needs to be understood end-to-end.

Operator's framing (2026-10-24): *"we need to test the repo process
in private first and we need a test plan for that … we will test in
private then we will see what that delivers. that should be able to
shake things out."*

The rehearsal is explicitly a **learning exercise**, not just a QA
pass. Operator wants to walk the git / release process by doing it,
one small step at a time, before the public cut.

**Depends on:**
- Nothing new. The repo already contains everything we need to
  rehearse against.

**Blocks:**
- TB-US-005 — v0.1 public release cut cannot responsibly happen
  until this rehearsal passes.

## Requirements

### Phase A — Audit what git knows

- [ ] R1: **Run `git status` + `git ls-files` + `git ls-files
      --others --ignored --exclude-standard`.** Operator reads output,
      understands what's tracked vs modified vs ignored.
- [ ] R2: **Confirm sensitive files are gitignored.** Expected
      ignored: `backend/db/.secrets`, `logs/first-run-admin.txt`,
      `hlai-*.tar.gz` backup files, `*.db` runtime databases
      (sessions.db, users.db, trainingbench.db, runs_tracker.db,
      chroma_db), `*/venv/`, `__pycache__/`, `.cache/`. If any of
      these show up in the "tracked" list → stop and fix `.gitignore`
      BEFORE committing anything.
- [ ] R3: **Audit for anything the operator missed.** `git ls-files`
      produces a complete list of files that would be published if
      the repo went public today. Operator scans for anything
      embarrassing, confidential, or operator-specific (hardcoded
      emails other than the gitignored env, test fixtures that
      should have been cleaned, old DB-connected scripts).

### Phase B — Commit the uncommitted work

- [ ] R4: **Group the uncommitted changes into logical commits.**
      Not one giant "snapshot everything" commit. Each commit should
      map to one or two completed stories. Rough grouping:
      - Admin password bootstrap (TB-US-049)
      - Secrets manager (TB-US-050)
      - Versioning schema + 5 component managers (TB-US-051-056)
      - Agent editor + agent-selector (TB-US-048)
      - Admin tier coordinator + API keys (TB-US-062, TB-US-063)
      - Welcome banner (TB-US-059)
      - Training-runs backend + UI (TB-US-065, TB-US-066)
      - Math-example Phase A seeder (TB-US-057 Phase A)
      - Docs: README + INSTALL + CONTRIBUTING (TB-US-061)
      - Docs: Jekyll Pages scaffold (TB-US-060)
      - Reactive UI tweaks umbrella updates (TB-US-045)
- [ ] R5: **Each commit message follows a clear pattern.** Suggested:
      ```
      TB-US-NNN: <short title>

      <2-4 line summary of what shipped in this commit>
      ```
- [ ] R6: **Push to origin** (private remote on GitHub). Verify on
      github.com (private repo view) that each commit is visible.

### Phase C — Fresh-install dress rehearsal

- [ ] R7: **Clone the private repo into a throwaway directory** on
      the same machine (e.g., `~/tb-rehearsal/`). This is NOT a
      different machine; it's the same machine with no pre-existing
      TB state.
- [ ] R8: **Follow INSTALL.md literally**, step by step. If a step
      fails or references something that doesn't exist in the cloned
      repo, STOP and fix the doc or the missing file. Repeat Phase B
      for any fix commits.
- [ ] R9: **Try to reach the Chat tab** at the end. The success
      condition is: fresh clone → followed INSTALL → see the chat tab
      with the welcome banner.
- [ ] R10: **Clean up the throwaway install** after. Remove the
      directory; stop any processes it spawned.

### Phase D — Tag a release candidate

- [ ] R11: **Create a `v0.1.0-rc1` tag** on the latest main commit.
      Message captures what v0.1 contains at a high level.
      ```bash
      git tag -a v0.1.0-rc1 -m "..."
      git push origin v0.1.0-rc1
      ```
- [ ] R12: **Visit `github.com/.../releases`** in a browser.
      Verify the tag shows up. GitHub will prompt to create a
      Release from the tag — walk that flow in the UI. Draft
      release notes. Do NOT publish; save as draft.
- [ ] R13: **Review the release draft:**
      - Does the auto-generated commit summary make sense?
      - Are release notes clear about what's in v0.1 and what's
        deliberately deferred?
      - Any attached files (adapter tarballs, etc.)? v0.1 scope
        decision is **local-only adapter** per TB-US-054, so no
        attachments expected.

### Phase E — Enable Pages privately

- [ ] R14: **Settings → Pages → Source → `main` branch, folder
      `/docs/pages`.** Save.
- [ ] R15: **Watch the GitHub Actions tab.** Both the Pages build
      service AND our CI workflow (`.github/workflows/pages-build.yml`,
      TB-US-060) should run.
- [ ] R16: **Visit the Pages URL** (GitHub shows it on the Settings
      → Pages panel). Private repos' Pages are visible only to
      authenticated collaborators. Confirm all 5 pages render + nav
      works + amber styling applies.
- [ ] R17: **If Pages build fails:** iterate on `docs/pages/` fixes;
      re-push; verify the workflow passes.

### Phase F — Stranger-eye review

- [ ] R18: **Read the README from scratch** as if operator had never
      seen the project. Does it answer "what is this?" / "who is it
      for?" / "how do I install?" in two minutes?
- [ ] R19: **Read INSTALL.md top to bottom.** Would a stranger
      following this doc end up with a working install? Note any
      step that assumes operator-local state (file paths that only
      exist on this machine, model-weight downloads that require
      HuggingFace token the install doesn't mention, etc.).
- [ ] R20: **Visit the Pages site** and click through all 5 pages.
      Note any cross-links that 404, prose that references stories
      operator hasn't drafted yet, or placeholder values that need
      updating.
- [ ] R21: **Note findings in a review doc** at
      `docs/release/v0.1.0-rc1-rehearsal-review.md`. This becomes
      the input to the real cut (TB-US-005).

### Phase G — Decide

- [ ] R22: **Operator reviews Phase F findings** + decides whether
      to iterate (go back to Phase B with fixes) or proceed to
      TB-US-005 for the actual public cut.
- [ ] R23: **If proceeding to TB-US-005:** remove `-rc1` suffix in a
      new rehearsal + repeat Phases D-F for `v0.1.0-rc2` only if
      Phase F surfaces substantive fixes. Otherwise jump directly to
      TB-US-005.

## Acceptance Criteria

- [ ] AC1: Phase A audit complete; no sensitive files appear in
      `git ls-files` output; `.gitignore` adjustments (if any) are
      committed first.
- [ ] AC2: Phase B commits land cleanly. `git log` shows the arc
      of work from TB-US-048 forward in logical groups.
- [ ] AC3: Phase C fresh-install walkthrough reaches the Chat tab.
      Every INSTALL.md step either worked as-written or was fixed +
      re-committed.
- [ ] AC4: `v0.1.0-rc1` tag exists on origin. GitHub Releases shows
      a draft release built from that tag.
- [ ] AC5: Pages site builds (private visibility) + renders
      correctly in a browser. All 5 pages reachable; nav works;
      amber styling applies; no broken links on internal pages.
- [ ] AC6: Review document at
      `docs/release/v0.1.0-rc1-rehearsal-review.md` captures Phase F
      findings.
- [ ] AC7: Operator feels they understand the release-cut flow well
      enough to execute TB-US-005 confidently (soft criterion;
      operator attests).
- [ ] AC8: Any issues found during the rehearsal that need separate
      fixes get their own story drafted (not shoved into TB-US-005).

## Design Notes

- **Why private first.** Mistakes on a private repo are invisible;
  mistakes on a public repo stay in `git log` forever. Any
  secret-leak into git becomes a `git filter-repo` recovery exercise.
  Any premature "v1.0" tag that embarrasses us stays searchable.
- **Why rehearse the whole flow, not just audit the repo.** The
  release-cut process has steps the operator hasn't personally
  walked before: creating tags, drafting releases, enabling Pages,
  configuring GitHub Actions. Doing it against a private repo
  teaches each step with real feedback.
- **Why group commits by story, not one big snapshot.** Future
  readers (including operator next week) will `git log` for
  "when did TB-US-049 ship?" and get a clean per-story answer.
  One mega-commit erases that signal.
- **Why "rc1" suffix.** Standard semver convention. `v0.1.0-rc1`
  signals "release candidate 1 for v0.1.0" — not yet the real cut.
  If rehearsal surfaces fixes, next tag is `v0.1.0-rc2`. When
  confident, the real cut drops the suffix: `v0.1.0`.
- **Why no attached release assets.** TB-US-054 scope decision was
  "adapter: local-only for v0.1." Keeping the release lightweight
  simplifies the rehearsal.
- **Why operator does the stranger-eye review, not Claude.** Claude
  wrote most of the docs. Only the operator can evaluate them with
  fresh eyes.
- **This story does not commit the uncommitted work on operator's
  behalf.** Phase B is the operator's exercise — Claude can suggest
  commit groupings and messages, but operator runs `git add` + `git
  commit` + `git push` to internalize the flow.

## Out of Scope

- The actual public release cut (TB-US-005)
- Repo-visibility flip from private → public
- Branding decisions (per the `feedback_branding_deferred` memory)
- HuggingFace Hub adapter distribution (TB-US-054 scope decision
  deferred this)
- PyPI / Docker / npm distribution channels
- Announcement / marketing
- v0.1.0 release-notes copyediting (first-pass drafts are fine for
  the rehearsal; polish in TB-US-005)
- Custom-domain configuration for Pages
- Running the rehearsal on a different machine (same machine,
  throwaway directory, is the Phase C design)

## Related

- [TB-US-005](tb-us-005.md) — v0.1 public release cut (blocked by
  this story)
- [TB-US-015](tb-us-015.md) — public launch coordinator
- [TB-US-060](tb-us-060.md) — Pages scaffold tested here
- [TB-US-061](tb-us-061.md) — README/INSTALL tested here
- [TB-US-049](tb-us-049.md) through [TB-US-066](tb-us-066.md) —
  the uncommitted work this rehearsal commits
- Files touched (during execution):
  - All currently-modified repo files (per Phase B)
  - `docs/release/v0.1.0-rc1-rehearsal-review.md` (new, Phase F)
  - Possibly `.gitignore` tweaks (Phase A, if any sensitive files
    aren't ignored)
