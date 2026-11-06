# Forking and Customizing TrainingBench

**Who this doc is for**: an engineer or organization considering
adopting TrainingBench for their own use, or a reader wanting
to understand how TB expects to be consumed downstream. If
you're a TB contributor wanting to submit a PR, see
[`CONTRIBUTING.md`](../../CONTRIBUTING.md) instead.

**TL;DR**: TB is an **open-source platform** (Apache-2.0)
designed to be **forked and customized** for your organization's
specific use case. Keep your proprietary customizations in your
private fork; pull TB mainline updates periodically. Contributions
back to TB mainline are welcome but entirely optional.

## 1. What TB is (and isn't)

**TB is**:

- A platform for building AI agents on your own hardware with
  your own data
- Infrastructure: RAG, PEFT adapter training, versioned prompts,
  versioned LoRA adapters, multi-LLM comparison, document
  processing, Sweet Spot experimentation methodology
- Generic — the mainline has no customer-specific code or
  content; everything is designed to be configured or extended
  by downstream users

**TB is NOT**:

- A turnkey agent for any specific domain. The math-example
  demo is a pedagogical illustration, not a production agent.
- A hosted service. You run TB on your own hardware.
- A replacement for your own domain expertise. TB gives you
  the lifecycle tooling; you supply the domain knowledge, data,
  and judgment.

## 2. How TB expects to be used

Three scenarios the TB platform supports:

### Scenario A — Try it

Clone TB, run it locally, kick the tires. Train the math-example
adapter, run the three staged experiments, understand what TB
does and whether it fits your needs. No commitment.

### Scenario B — Fork and customize privately

Most common for commercial or production use:

1. Fork TB (via GitHub or by cloning the repo into your own
   private git host)
2. Build on top of TB in your private fork: add your training
   data, your system prompts, your client/domain-specific
   features, your own branding
3. Pull TB mainline updates into your fork periodically (merge
   or rebase — your choice)
4. Keep your customizations private; the Apache-2.0 license on
   TB does NOT require you to publish your downstream work

This is the pattern TB's maintainer uses internally for client
engagements: TB mainline stays generic; each client gets their
own private fork that holds proprietary content.

### Scenario C — Fork, customize, and contribute back

For generic improvements you discover while customizing (bug
fixes, performance improvements, new generic features, better
documentation), you can submit PRs to TB mainline. See
[`CONTRIBUTING.md`](../../CONTRIBUTING.md). Note that
contributions to mainline carry the Apache-2.0 license; your
private customizations remain separate.

## 3. What belongs in your fork vs. mainline

A rough guide. The judgment call for each specific case is
yours, but these defaults have worked in practice:

| Category | Where it goes | Notes |
|---|---|---|
| Your training data (text, Q&A pairs, labeled examples) | **Your fork** | Always private. Register as a `training_set_version`; the sidecar JSONL lives in your fork's `training/datasets/training_set_versions/`. |
| Your RAG documents (uploaded, scraped) | **Your fork + your ChromaDB** | Sit in your Chroma database, not in code. But seed scripts that populate them live in your fork. |
| Your LoRA adapters (trained model weights) | **Your fork** | Live in `adapters/<your-agent>/v*`. Bytes, not code. |
| Agent-specific system prompts | **Your fork** | Register as `prompt_version`s. Keep domain-specific wording / vocabulary private. |
| Query routes (regex patterns for your domain) | **Your fork** | Register as `route_version`s. |
| UI branding (logo, colors, product name, legal footer) | **Your fork** | Modify `static/*.html` + `static/*.css`. Diverges from mainline but easy to merge. |
| Client-specific harnesses (your domain's eval set) | **Your fork** | Register as `harness_version`s pointing at your own JSONL. |
| Client-specific endpoint (e.g., HCP CV scorer) | **Your fork** | Add a new module in `backend/api/` + an endpoint in your fork's `main.py`. Keep the generic routing/registry patterns from TB. |
| Bug fixes in TB generic code | **Mainline PR welcome** | If the bug is in TB-shipped code, upstream benefits. |
| New generic features (e.g., support for a new LLM provider) | **Mainline PR welcome** | Discuss first via issue. |
| Performance improvements | **Mainline PR welcome** | |
| New documentation | **Mainline PR welcome if generic** | Your client-specific docs stay in your fork. |

The pattern: **anything that references your specific domain
or clients stays in your fork; anything generic that other TB
users would benefit from can flow up to mainline**.

## 4. Practical guide to starting your fork

### Starting out

```bash
# Fork via GitHub UI first, then:
git clone https://github.com/YOUR-ORG/trainingbench.git your-trainingbench
cd your-trainingbench
git remote add upstream https://github.com/jeversole-consult/trainingbench.git
# Follow README.md install instructions to get TB running locally
```

### Keeping your fork aligned with TB mainline

Monthly or when TB cuts a release:

```bash
git fetch upstream main
git merge upstream/main   # or `rebase upstream/main` if your team prefers linear history
# Resolve conflicts (most will be in docs, config defaults,
# or UI branding — never in model weights or training data
# which live outside the repo)
# Run the smoke test: install, log in, train a small adapter,
# run one experiment
```

### Where to put your customizations

Suggested but not required:

- **Your agent artifacts**: `adapters/<agent-name>/v*/`, `training/datasets/training_set_versions/v*.jsonl` — TB already writes to these paths
- **Your UI branding**: modify `static/index.html` + CSS directly; those merge cleanly from upstream in most cases
- **Your client-specific endpoints**: new file in `backend/api/` (e.g., `backend/api/your_client_handler.py`), wire it into `main.py` under a clearly-named section
- **Your seed data / default config**: a `client_config/` directory in your fork is a reasonable convention. Not shipped by TB mainline.
- **Your environment**: `.env` or `config.local.json` — already gitignored in TB

### Avoiding merge conflicts over time

The most conflict-prone spots:

- `static/index.html` + CSS if TB changes UI layout (e.g., left-nav drawer; TB-US-018 did this)
- `backend/api/main.py` endpoint section (large file; many additions by TB)
- `BACKLOG.md` (TB's project-tracking file; you probably don't want this file in your fork anyway)
- `_config.yml` for the Pages site (if you're not publishing Pages, you can delete this safely)

Strategies:

- **Fence your client-specific code into its own files** rather than inline-editing shared TB files when possible
- **Use env vars for config** — TB reads many defaults from env (`PEFT_ADAPTER_PATH`, `OLLAMA_MODEL`, `TB_SPREADSHEET_PATH`, etc.); overriding them in your deployment doesn't touch code
- **Delete, don't scrub, docs you don't need**: if TB ships math-example docs you don't want, just delete those files in your fork

## 5. License clarity

- **TB mainline**: Apache License 2.0 (see [`LICENSE`](../../LICENSE))
- **Your private fork**: your customizations are yours; you are
  NOT required to open-source them. The Apache-2.0 license
  permits proprietary derivative works.
- **If you contribute code back to TB mainline**: your
  contribution is licensed under Apache-2.0. See
  [`CONTRIBUTING.md`](../../CONTRIBUTING.md) for details.
- **Trademark**: "TrainingBench" and "TB" are informal project
  names, not registered trademarks (as of this writing). Your
  fork can keep the TB name internally; for public-facing
  branding use your organization's name instead.
- **Attribution**: Apache-2.0 requires preserving the LICENSE
  file + copyright notices in derivative works. Keep the
  `LICENSE` file in your fork.

## 6. Common pitfalls

**Modifying TB's shared schema vs. extending it.**
TB's databases (users, sessions, trainingbench.db, runs_tracker)
have schemas that evolve with TB releases. If you add tables for
your client-specific data, add them with distinct names (e.g.,
`your_client_queries`) rather than extending TB's tables. Your
tables won't conflict with upstream migrations.

**Overwriting defaults vs. layering.**
If TB ships a default system prompt and you want a different
one, don't edit the TB file — create a new prompt_version via
the API and promote it. The Sweet Spot methodology handles
this cleanly.

**Pulling upstream without testing.**
TB mainline may ship changes that interact with your
customizations. Run your deployment's smoke tests after every
upstream merge, before deploying to production.

**Mixing your fork's content with TB's git history.**
Don't force-push your fork's history over TB's; keep them
separable so you can always diff "what's TB" vs. "what's mine."

**Treating the math-example as production.**
The math-example demo is pedagogical. If your use case is math
reasoning in production, start with it as a reference but build
your own agent (your own training data, your own domain prompts).

## 7. Related docs

- [`CONTRIBUTING.md`](../../CONTRIBUTING.md) — if you want to
  contribute to TB mainline
- [`system-architecture.md`](system-architecture.md) — TB's
  internals; useful if you're adding new capabilities to your
  fork
- [`agent-architecture.md`](agent-architecture.md) — the
  versioned-component model
- [`sweet-spot-architecture.md`](sweet-spot-architecture.md) —
  the experimentation methodology
- [`maintenance-fix-workflow.md`](../training/maintenance-fix-workflow.md)
  + [`upgrade-publishing-workflow.md`](../training/upgrade-publishing-workflow.md)
  — operational patterns you can adopt or adapt in your fork
