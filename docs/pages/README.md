# docs/pages/

TB-US-060 Jekyll scaffold for the TrainingBench GitHub Pages site.

## What this is

The content TrainingBench's public documentation site renders from.
Five Markdown pages (Home, Getting Started, Staged Progression,
Concepts, Install) + a shared `_layouts/default.html` + `_config.yml`.

GitHub Pages renders Jekyll natively — once Pages is enabled on this
repo pointing at this folder, the site builds on every push to main
and serves at the configured URL.

## Enabling GitHub Pages (operator step)

Once the repo is public (post TB-US-005):

1. Go to **Settings → Pages** on the GitHub repo
2. **Source:** Deploy from a branch
3. **Branch:** `main`
4. **Folder:** `/docs/pages`
5. Save. GitHub builds the site; URL appears in a few minutes.

Optional: configure a custom domain in the same panel (CNAME file
goes next to `_config.yml`).

## Updating `_config.yml` for the deployed URL

If the Pages site is served at a subpath (e.g.,
`eversole-learning.github.io/trainingbench/`), edit
`_config.yml`:

```yaml
baseurl: "/trainingbench"
```

If served at the root (custom domain), leave `baseurl: ""`.

## CI build check

`.github/workflows/pages-build.yml` builds the site on every PR
touching `docs/pages/` and fails the check if anything breaks.
Pre-merge safety net; doesn't deploy — Pages' own build service
handles that.

## Local preview (optional)

Requires Ruby 3.x + bundler. From this directory:

```bash
gem install jekyll bundler kramdown kramdown-parser-gfm rouge
jekyll serve
```

Then open `http://localhost:4000`.

## Content ownership + updates

- **Home (`index.md`)** — stable hero + three feature cards
- **Getting Started (`getting-started.md`)** — 10-minute install
  walkthrough; keep aligned with repo `INSTALL.md`
- **Staged Progression (`staged-progression.md`)** — math-example
  demonstration; **currently uses placeholder measurement numbers
  pending TB-US-057 Phase B completion**. Update with real
  numbers once operator-run measurements land.
- **Concepts (`concepts.md`)** — vocabulary ref. Update as new
  concepts land (currently stable through TB-US-064).
- **Install (`install.md`)** — summary of repo INSTALL.md. Keep
  them in sync.
