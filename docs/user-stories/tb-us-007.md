# TB-US-007: Prune unused dependencies from requirements.txt

**Status**: Proposed
**Created**: 2026-06-29
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a user installing TrainingBench on a fresh machine, I want
`requirements.txt` to declare only the packages the code actually
imports — so the install downloads less, finishes faster, and the
dependency surface I have to trust is smaller.

## Background

A quick first-pass audit of `requirements.txt` against tracked
imports turned up multiple packages that are declared but never
imported anywhere in `backend/`, `scripts/`, or `training/`:

| Declared package | Tracked imports found |
|---|---|
| `scrapy` | 0 |
| `selenium` | 0 |
| `scikit-learn` (`import sklearn`) | 0 |
| `matplotlib` | 0 |
| `seaborn` | 0 |
| `rouge-score` | 0 |
| `bert-score` | 0 |
| `ipywidgets` | 0 |
| `jupyter` | 0 direct imports (may be a CLI the user invokes) |

These declarations cost the user real install time and disk: `scrapy`
alone pulls Twisted and a tree of native dependencies; the
`jupyter`/`ipywidgets` pair pulls dozens of transitive packages
including a full IPython stack. For a first-release install path
that is supposed to be lean, this is dead weight.

The audit is a *first pass*. Some of these may turn out to be used
indirectly (e.g. via `setup.py` extras, Jupyter notebooks in
`research/`, or as run-time CLI tools called from documentation).
The story's actual work is doing the audit carefully and removing
only what's truly unused.

## Requirements

- [ ] R1: Every package listed in `requirements.txt` is verified
      against tracked code (`backend/`, `scripts/`, `training/`,
      `static/` — wherever Python imports could happen). The
      verification considers both direct imports (`import X`,
      `from X import ...`) and the package's import-name mapping
      where it differs from its PyPI name (e.g. `scikit-learn` is
      imported as `sklearn`, `beautifulsoup4` is imported as `bs4`).
- [ ] R2: Packages with zero tracked imports are removed from
      `requirements.txt`, unless they are intentionally optional
      (a comment in the file explains why they stay).
- [ ] R3: For each removed package, a one-line note in the commit
      message explains why removal is safe ("not imported anywhere"
      or "redundant with X").
- [ ] R4: After the prune, a fresh install (`python3 -m venv venv;
      pip install -r requirements.txt`) completes successfully on a
      clean machine.
- [ ] R5: After the prune, `python -c "import backend.api.main"`
      succeeds without ImportError. The backend smoke-starts
      (`uvicorn backend.api.main:app --port <free>`) and serves
      the login page.
- [ ] R6: After the prune, the smoke training invocation from
      TB-US-001 still works:
      `python training/math/train.py --max-train-samples 50
      --max-eval-samples 25 --epochs 1 --run-name smoke-test`.

## Acceptance Criteria

- [ ] AC1: `requirements.txt` at HEAD has no declared package that
      lacks at least one tracked import (with intentional exceptions
      annotated with a comment).
- [ ] AC2: An install on a freshly created venv on this machine,
      using the pruned `requirements.txt`, results in a working
      backend that serves the login page.
- [ ] AC3: The smoke-train invocation from TB-US-001 completes a
      train+eval loop using only the pruned dependency set.
- [ ] AC4: The size difference between the pre-prune and
      post-prune `venv/` is recorded in the commit message, so a
      future maintainer can see the cost-savings benefit.

## Design Notes

- The audit should look at *what is imported in tracked code*, not
  at *what the package documentation says it does*. The fact that
  `matplotlib` is a great library does not justify shipping it if
  no tracked file imports it.
- Some declared packages may be used by Jupyter notebooks or
  research scripts kept outside `backend/`/`scripts/`/`training/`.
  If such usage is the reason a package stays, that gets a
  comment in `requirements.txt`.
- This story does **not** repack `requirements.txt` into
  core/dev/optional groups (e.g. `requirements-dev.txt`). That is
  a larger restructure and belongs in a separate story.
- This story does **not** introduce version-pinning policy
  (e.g. switching `>=` floors to exact pins). Also separate.
- A successful prune may reveal that the install footprint shrinks
  enough to revise the "30 GB minimum, 50 GB comfortable" estimate
  in `INSTALL.md`. If so, update the doc as part of this story.

## Out of Scope

- **Replacing libraries.** This story removes unused declarations;
  it does not swap `chromadb` for a different vector store or
  `langchain` for something else.
- **Splitting requirements into groups** (core / dev / optional /
  training-only / scraping-only). Useful, larger, separate story.
- **Version-pinning policy.** The current `>=` floors are kept as
  they are; pinning to exact versions for reproducibility is a
  separate concern.
- **Removing packages that are *unused right now* but were
  introduced for an in-flight feature.** If a maintainer notes
  that a package is reserved for upcoming work in a near-term
  story, it stays with a comment.
- **Auditing `pyproject.toml` or `setup.py`.** Neither file exists
  in TrainingBench yet; if and when they do, that's a separate
  audit.

## Related

- TB-US-002 — the install path that this story makes faster and
  smaller. Sequence: complete TB-US-002 first (so we have a known-
  good install baseline), then run this audit against that
  baseline.
- TB-US-001 — its smoke-train invocation is the AC3 verification
  for this story.
- `requirements.txt` — the file being pruned.
- `INSTALL.md` — may need its disk-footprint estimate revised
  after the prune.
