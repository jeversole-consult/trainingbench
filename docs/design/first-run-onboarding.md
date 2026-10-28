# First-Run / Onboarding Architecture — Design Notes

**Status:** Draft (operator-collaborative; iterate across turns)
**Owned by:** TB-US-047
**Related:** TB-US-044 (Agent architecture — Q13 folds here)
**Created:** 2026-10-17
**Last updated:** 2026-10-17

> **This is a working document.** It will evolve as the
> operator and Claude Code iterate on the open questions
> below. Each design decision is captured as it stabilizes.
> The document is "ready to execute against" when every open
> question has a **Decision:** line and the follow-up
> stories (§8) are drafted.

---

## Table of Contents

1. [Current fresh-install state](#sec-1)
2. [Problems with the current state](#sec-2)
3. [Admin account bootstrap](#sec-3)
4. [Shipped example agent + staged progression (replaces "default agent" framing)](#sec-4)
5. [First-login UX](#sec-5)
6. [Onboarding checklist](#sec-6)
7. [INSTALL.md + README restructure guidance](#sec-7)
8. [Follow-up stories unlocked](#sec-8)
9. [Open questions for operator decision](#sec-9)
10. [Decision log](#sec-10)
11. [What comes after this design is approved](#sec-11)

---

<a id="sec-1"></a>

## 1. Current fresh-install state

What TB does today when a fresh install starts for the
first time:

### 1.1 What auto-creates

| Artifact | Mechanism | Default |
|---|---|---|
| `users.db` + schema | `UserManager._init_database()` | Empty tables |
| **Admin user** | Auto-created when `users` table is empty | `username=admin, password=changeme, email=admin@localhost, type=super` |
| `sessions.db` + `sessions` table | `SessionTracker._init_database()` on first instantiation | Empty |
| `admin_audit` table (in users.db) | TB-US-017 schema | Empty |
| `app_settings.json` | `AppSettings._seed_default()` | `demo_mode=false, rag_prompt=<default>, query_routes=[], active_database=null` |
| `logs/` directory | On first write | Empty |
| Chroma vector store | `RAGSystem` + `VectorStore` | Empty collection |
| **Default agent** | — | **DOES NOT EXIST** — agent concept lives in TB-US-044 design spike |
| Training sets | — | None |
| PEFT adapters | — | None |

### 1.2 Env vars that govern first-run

| Env var | Purpose | Current default |
|---|---|---|
| `SITE_PASSPHRASE` | Gate passphrase (first auth layer) | `""` (gate disabled) |
| `SECRET_KEY` | Session-token signer | `"default-secret-key-change-this"` |
| `PASSWORD_SALT` | Global password hash salt | `"trainingbench-default-salt-change-this"` |
| `DEFAULT_ADMIN_USERNAME` | Seeded admin username | `"admin"` |
| `DEFAULT_ADMIN_PASSWORD` | Seeded admin password | `"changeme"` |
| `DEFAULT_ADMIN_EMAIL` | Seeded admin email | `"admin@localhost"` |
| `APP_PORT` | Uvicorn port | `8002` |
| `LLM_PROVIDER` | RAG LLM backend | `"peft"` |
| `LLM_MODEL` | LLM model identifier | unset → provider default |

### 1.3 First-boot console output (today)

```
TrainingBench starting on port 8002
Loading embedding model: all-MiniLM-L6-v2
Vector store initialized with collection: documents
Current document count: 0
No users found. Creating default super user...
Default super user created: admin / changeme
IMPORTANT: Change this password immediately!
Training sets database initialized
Training run tracker database initialized
Uvicorn running on http://0.0.0.0:8002
```

### 1.4 First-visit UX

1. Browser → `https://<host>/` → gate page (if `SITE_PASSPHRASE` set) or straight to login.
2. Operator enters passphrase (if gated).
3. Login page: operator must know `admin / changeme` (or env-overridden) to log in.
4. Lands on index.html, Chat tab active (per TB-US-046).
5. Nothing in the RAG, no training sets, no agent concept.
6. No in-app guidance for "what next."
7. The `IMPORTANT: Change this password` log message is only visible to someone reading server logs — invisible to a web-only operator.

---

<a id="sec-2"></a>

## 2. Problems with the current state

**Security problems:**

1. **`admin / changeme` is a known-weak credential.** Any
   GitHub-sourced install that doesn't set env vars has
   identical admin creds to every other install. Trivial
   automated discovery.
2. **`SECRET_KEY` + `PASSWORD_SALT` have hardcoded
   defaults** that are the same across installs. Anyone
   with these can forge session tokens or crack password
   hashes offline.
3. **No in-app enforcement of password change.** Log
   message is invisible to the operator; no login
   interstitial.
4. **No audit of the first login event** separately from
   subsequent ones. All sessions look equivalent.

**UX problems:**

5. **No default agent** (once TB-US-044 lands) — operator
   lands on an empty workspace with no scope to work in.
6. **No "what to do next" guidance.** Operator sees Chat
   tab but has no RAG content, no training set, no
   understanding of where to start.
7. **No setup-done marker.** TB can't tell whether this is
   the operator's first visit (deserve a wizard?) or their
   100th (don't interrupt them).
8. **Help / quickstart is docs-only.** No in-app hints,
   no welcome banner, no checklist.

**Install-doc problems:**

9. **`INSTALL.md` and `README.md` don't walk through the
   actual first-run flow.** No explicit "start the service
   → log in with X → do Y → do Z" sequence.
10. **No onboarding target for the OSS release
    (TB-US-005).** v0.1 ship requires a story where a
    stranger clones, follows the docs, and lands on a
    working TB with their own agent — currently that
    story doesn't exist.

---

<a id="sec-3"></a>

## 3. Admin account bootstrap

### 3.1 The problem

Default admin credentials must be:
- **Secure by default** (no shared `admin / changeme`)
- **Discoverable to the installer** (they need to log in
  somehow)
- **Changed before productive use** (enforced)
- **Compatible with env-driven install** (CI / Docker
  config via env vars should still work)

### 3.2 Proposed design (operator to validate)

**Random-password-on-first-boot pattern:**

1. On service start, UserManager checks if `users` table
   is empty.
2. If yes:
   - Check if `DEFAULT_ADMIN_PASSWORD` env var is set:
     - If set → use it (dev/CI path).
     - If unset → **generate a 24-character cryptographically-
       random passphrase** (e.g., `secrets.token_urlsafe(18)`).
   - Create admin user with:
     - username: `admin` (or env-override)
     - password: that passphrase (hashed)
     - email: env-override or `admin@localhost`
     - **A `must_change_password` flag** (new column on
       users table) set to `true` on auto-created admin.
   - Print the password to stdout prominently (visible
     in `systemctl status` / `docker logs` / terminal):
     ```
     ========================================
     TrainingBench first-run admin credentials:
       username: admin
       password: <generated-passphrase>
     Store this password now. Change it after first login.
     ========================================
     ```
   - Also write it to `logs/first-run-admin.txt` with
     `chmod 600` for recovery if logs are missed. File is
     deleted after first successful password change.
3. On first login as admin:
   - Backend checks `must_change_password` flag.
   - If true, response includes a `must_change_password:
     true` marker.
   - Frontend intercepts, routes to a `/first-change-password.html`
     page that forces password change before any other
     action.
   - After change, flag flips to `false`; file deleted.

**SECRET_KEY and PASSWORD_SALT auto-generation:**

- On first service start, if these env vars are unset,
  TB generates random values (32-byte urlsafe tokens) and
  **writes them to `/etc/trainingbench/.secrets` or
  `backend/db/.secrets`** with `chmod 600`.
- Subsequent starts read from the file.
- Operators can override by setting env vars (precedence:
  env var > file > hardcoded fallback).
- **Hardcoded fallbacks are kept for dev** but every
  default fallback produces a startup warning:
  `WARNING: Using default SECRET_KEY. Set a real one for
  production.`

**Open — see §9 Q1 for admin-bootstrap decisions,
Q2 for SECRET_KEY/SALT handling.**

---

<a id="sec-4"></a>

## 4. Shipped example agent + staged progression

**Reframed 2026-10-18** per operator design signal. The
earlier "auto-create a `default` placeholder agent" framing
is **superseded** by a pedagogy-driven design: TB ships
with ONE example agent that's structured as a measurable
multi-stage progression demonstrating what each agent
component (bare LLM → +RAG → +PEFT adapter) contributes.

> **Operator statement (2026-10-18):** *"the product is of
> little use if you don't have at least one agent to work on.
> the reason for having examples is to provide the newcomer
> with a stepping stone to get to their own agent. ... on
> initial install having one or more examples makes it
> easier for the uninitiated to absorb the concepts at work
> in building and using a chatbot agent."*
>
> Followed by: *"Just a chatbot interface talking to a local
> LLM like llama3B ... that could test the compare function
> of TB bare bones. Then lets say you incrementally add the
> RAG. What is the performance change? ... then what if you
> add a pretrained adapter? what is the performance change.
> we pull this off we will show the user a path to building
> out a specifically trained agent."*

### 4.1 Shipped: ONE example — `math-example`

Fresh install ships with a single example agent named
`math-example`. Rationale:

- **One example minimizes install complexity.**
  Additional domains are future stories.
- **Math is universal exposure.** Nearly all operators
  have seen math problems; low cognitive barrier to
  reading the results.
- **Math lends itself to measurable eval.** Problems have
  definite correct answers; exact-match / regex rubrics
  work; the pedagogy ("here's a %-correct score before vs
  after") is clear.
- **Math has public-domain datasets.** GSM8K (Apache 2.0/
  MIT), MATH (MIT) can ship + redistribute. No legal
  friction.
- **Aligns with TB-US-029** (verification-example story)
  and **TB-US-043 Q10** (first-example choice) — both
  already lean math.

### 4.2 Staged-progression as pedagogy — the design kernel

The shipped `math-example` is NOT just a working agent.
It's **three experiments** with measured results, structured
to teach the newcomer what each component contributes:

```
Stage 0 — Bare chatbot
  ├─ LLM: llama3.1:8b (Ollama local)
  │      OR: api-key'd big public LLM (GPT-4 / Claude /
  │          Gemini) if operator configures API keys
  ├─ RAG: NONE
  ├─ Adapter: NONE
  ├─ System prompt: minimal ("Answer the question.")
  ├─ Test set: public-domain prompts (GSM8K subset,
  │            50-100 problems)
  ├─ Rubric: exact-match on numeric answer
  └─ Measured: baseline score X%

Stage 1 — + RAG
  ├─ Same LLM as Stage 0
  ├─ RAG: math reference corpus (public-domain docs)
  ├─ Adapter: NONE
  ├─ System prompt: RAG-aware ("Use the context when
  │                 relevant. Context: {context}.")
  ├─ Test set: same as Stage 0
  └─ Measured: X + ΔRAG = Y%

Stage 2 — + Pre-trained adapter (PROMOTED Sweet Spot)
  ├─ Same LLM, Same RAG
  ├─ Adapter: trained on shipped math training set
  ├─ Same system prompt as Stage 1
  ├─ Test set: same as Stage 0, 1
  └─ Measured: Y + ΔAdapter = W%
```

**Three experiments. Same eval harness. Measurable deltas.**

### 4.3 Mapping to Sweet Spot vocabulary (TB-US-043)

- Each stage = one **experiment / recipe**
- Each stage's scored result = one **experiment_result** row
- Stage 2 = **current Sweet Spot** (status=`promoted`)
- Stages 0, 1 = **displaced** snapshots (preserved as
  historical pedagogy, not deleted)
- Compare view shows all three side-by-side on first open

### 4.4 The newcomer journey through the shipped stages

1. **Install TB + first-run password change** (per §3).
2. **Login + welcome banner** (per §5) says:
   *"math-example is ready. Try asking it a math question.
   Then open Compare to see how each layer contributes."*
3. **Operator opens Chat** → asks a math question → gets
   an answer from Stage 2 (promoted Sweet Spot).
4. **Operator opens Compare** → sees the three stages
   with scores: X% / Y% / W%, and the deltas ΔRAG and
   ΔAdapter visible.
5. **Operator reads the delta narrative:** *"The RAG added
   15 points. The adapter added 12 more. Both together
   lifted the agent from 31% to 58%."* Real numbers from
   the operator's own benchmark run; not hypothetical.
6. **Operator opens Training Sets** → sees the shipped
   training set that produced the adapter.
7. **Operator opens Training Runs** → sees the shipped
   training run record (reproducible).
8. **Operator opens Databases** → sees the RAG collection
   with the shipped documents indexed.
9. **Operator understands the agent lifecycle viscerally.**
10. **Operator creates their own agent** (`my-cuad`,
    `my-support`, etc.) with the same mental model;
    optionally forks math-example's components as starting
    points.

**The pedagogy succeeds because the install SHOWS rather
than TELLS.** Documentation can describe deltas; the staged
install exhibits them.

### 4.5 Resource / shipping decisions

**Shipped in the git repo (lean, ~10-25 MB):**

| Artifact | Size | Purpose |
|---|---|---|
| Math RAG seed docs (GSM8K rationales, SymPy docs, Wikipedia math) | ~5-10 MB | Rebuilt as a chroma collection on first boot |
| Math training set JSON | ~1-2 MB | Reproducibility: adapter can be re-trained from this |
| Eval harness JSONL (GSM8K subset) + rubric | <1 MB | Scoring instrument |
| System prompts (Stage 0, 1, 2 variants) | <1 KB each | Experiment configurations |
| Experiment metadata records | <1 KB | Stage 0, 1, 2 experiment rows + results |
| First-boot seed script | <1 KB | Rebuilds chroma, seeds experiment rows |

**NOT shipped in git (delivered separately):**

- Pre-trained Stage 2 adapter binary (~100-500 MB) — see
  §4.6.

### 4.6 Pre-trained adapter delivery mechanism

Shipping a 100-500 MB adapter in the git repo bloats
cloning and clashes with the "lean research tool" posture.
Delivery mechanism (decided per Q3C):

**GitHub Release artifact + fallback behavior:**

- Each TB release uploads the pre-trained math adapter as
  a release asset (binary / tarball).
- On first boot, if `agents/math-example/adapter/` is
  empty:
  - TB logs a startup message: *"Pre-trained math adapter
    not present. Visit the welcome banner to download it or
    train your own."*
  - Welcome banner surfaces a button: **"Download
    pre-trained math adapter (120 MB)"**.
  - Clicking it fetches from the release asset URL,
    verifies hash, extracts to `agents/math-example/adapter/`,
    reloads the Stage 2 experiment context.
  - Alternative: operator clicks **"I'll train my own"**
    which opens Training Runs with a pre-configured
    training run against the shipped training set. Operator
    sees Stage 2 become populated after their training
    completes.
- If adapter is present, no banner prompt.

**Fallback — if adapter download fails or operator declines:**

- Compare view clearly indicates **"Stage 2 awaiting
  adapter"** with the two action buttons visible inline.
- Stages 0 and 1 work normally. The newcomer can still see
  the ΔRAG delta.
- Operator can return later to download or train.

**Trade-off accepted:** small bandwidth cost to download
~120 MB on first boot (for operators who want full Stage 2)
in exchange for a lean git repo + optional-first-step UX
+ reproducibility (operator can verify the shipped adapter
by re-training from the shipped training set).

### 4.7 Zero-agents sub-question (Q3D)

Can an operator eventually have zero agents (delete
math-example + all siblings)?

**Decided per Q3D:** **Yes** — zero agents allowed. If the
operator deletes all agents, drawer shows an empty-state
("No agents. Create one to begin.") and agent-scoped drawer
items gray out. Admin surface (Users, API keys, logout)
still works. No forced-minimum. See §9 Q3D.

### 4.8 What this cascades into for other stories

- **TB-US-029 (verification example):** becomes the
  content-source for math-example's shipped artifacts.
  Its deliverables (eval harness + test prompts +
  training set + RAG seeds + Stage 2 adapter) are the
  shipped content. Scope expands slightly.
- **TB-US-030 (operator workflow):** becomes "here's how
  math-example was built; apply this to your own agent."
  Downstream of math-example's existence.
- **TB-US-044 Q13** (zero-agent / default-agent):
  **RESOLVED** — ship math-example (not placeholder);
  zero-agents allowed after operator action. Decision
  mirrored into TB-US-044's log.
- **TB-US-043 Q10** (first-example): confirmed math.
- **New TB-US-NN (to be drafted)** — "Build + publish the
  math-example staged progression as a shipped release
  artifact." Covers: assemble public-domain RAG corpus,
  curate training set, train Stage 2 adapter, run Stage
  0/1/2 benchmarks, record results, publish to GitHub
  Release.

**Open — see §9 Q3B, Q3C, Q3D for the formal Decisions.**

---

<a id="sec-5"></a>

## 5. First-login UX

### 5.1 Proposed layering

Three progressive layers of guidance:

**Layer A — Forced password change** (hard block):

Operator cannot see the main app until they've changed
the auto-generated admin password. Dedicated page:
`/static/first-change-password.html`. Simple form; new
password + confirm. On submit → backend flips
`must_change_password` to `false`, redirects to
`/index.html`.

**Layer B — Welcome banner** (soft nudge, dismissable):

After forced password change, operator lands on index.html.
A banner appears above the main content:

```
┌─────────────────────────────────────────────────┐
│  🎉 Welcome to TrainingBench                     │
│                                                   │
│  Suggested next steps:                            │
│    1. Rename your agent (currently: default)      │
│    2. Upload documents to its RAG                 │
│    3. Start chatting                              │
│                                                   │
│  [Show me the quickstart]  [Dismiss for now]     │
└─────────────────────────────────────────────────┘
```

- Dismissal persisted in localStorage (`tb_welcome_dismissed = true`)
- Reappears if localStorage cleared
- "Show me the quickstart" opens `/static/getting-started.html`

**Layer C — Getting-started page** (reference, always
available):

Dedicated `/static/getting-started.html` with:
- Overview of what TB is
- The onboarding checklist (§6)
- Links to deeper docs (`INSTALL.md`, user-stories, design
  docs via the docs page)
- Accessible from the drawer (⭐ Getting Started item,
  visible until explicitly removed by operator — not just
  dismissed-until-reload)

**Open — see §9 Q4-Q6.**

---

<a id="sec-6"></a>

## 6. Onboarding checklist

### 6.1 Candidate steps (operator to validate)

For a fresh operator landing on TB:

1. **Change admin password** (enforced via forced flow)
2. **Rename the default agent** (optional, deferred OK)
3. **Decide on your base LLM** — leave Ollama default or
   configure OpenAI / Anthropic / etc. via API keys
4. **Add documents to your agent's RAG** (Upload tab,
   Scrape tab, or Databases → import)
5. **Try your first chat** — verify end-to-end answers
   with the default system prompt
6. **Create a training set** from queries that didn't work
   well
7. **Run your first training** (produces a PEFT adapter)
8. **Promote your first Sweet Spot** (per TB-US-043)

### 6.2 Lives in two places

- As a numbered list on `/static/getting-started.html`
  (always-available reference)
- As a short-list in the welcome banner (first 3 items
  only; rest in "Show me the quickstart")

**Open — see §9 Q7.**

---

<a id="sec-7"></a>

## 7. INSTALL.md + README restructure guidance

### 7.1 What they should cover (not drafts of what to write)

**`README.md`** (project root):

- One-paragraph "what is TB" (focused on the chat-agent-
  building value proposition)
- Links to:
  - `INSTALL.md` for setup
  - `docs/README.md` for internal docs
  - `/static/getting-started.html` once installed
- Quickstart section (per TB-US-004) — brief
- Branding: whatever final messaging (deferred-branding
  memory governs)

**`INSTALL.md`**:

- Prereqs (Python, Ollama, disk, GPU optional)
- Install steps (venv, pip, service setup)
- **Required env vars**: just `SITE_PASSPHRASE` and
  nothing else — auto-generated values cover the rest
- First-run instructions:
  - Start the service
  - **Get the first-run admin password from the console
    output or `logs/first-run-admin.txt`**
  - Set `SITE_PASSPHRASE` before starting if the gate is
    wanted
  - Visit `https://<host>/`
  - Enter passphrase, then admin creds
  - Follow the forced password change
  - Welcome banner takes it from there
- Env var reference table (what's required vs auto-
  generated vs operator-overridable)
- Common troubleshooting

**Open — see §9 Q8.**

---

<a id="sec-8"></a>

## 8. Follow-up stories unlocked

Once this spike's design is approved, these follow-up
stories execute:

1. **TB-US-NN — Admin password bootstrap implementation.**
   - Modify `UserManager._init_database` to generate
     random passphrase if `DEFAULT_ADMIN_PASSWORD` unset
   - Add `must_change_password` column to users table
   - Add `/first-change-password.html` page + backend
     endpoint
   - Write first-run creds to `logs/first-run-admin.txt`
     with chmod 600; delete on first password change
   - Blocking for secure OSS release.

2. **TB-US-NN — SECRET_KEY + PASSWORD_SALT auto-generation.**
   - On first start, generate random values if env vars
     unset
   - Persist to `backend/db/.secrets` with chmod 600
   - Startup warnings if hardcoded fallbacks are in use.

3. **TB-US-NN — Shipped math-example seed on first run.**
   - Depends on TB-US-044 execution (agents schema)
   - On first boot: create `math-example` agent, seed RAG
     from shipped docs, seed training set from shipped
     JSON, seed Stage 0/1/2 experiment metadata +
     scored-result rows (reflecting the operator's own
     benchmark runs)
   - Welcome banner surfaces the Stage 2 adapter-download
     prompt
   - This story depends on TB-US-NN-X (adapter build +
     publish, see #7) to produce the artifacts

   *Was: "Default agent on first run" — superseded by
   the staged-progression design.*

4. **TB-US-NN — Welcome banner.**
   - Dismissable banner on index.html for first-time
     users
   - Checklist of next steps
   - localStorage-tracked

5. **TB-US-NN — GitHub Pages site (dual-surface
   companion to README).**
   - Set up Jekyll + chosen theme in `/docs` or
     `gh-pages` branch
   - Author Home page (project overview, screenshots,
     use cases)
   - Author Getting Started page (staged-progression
     story from §4; Q7 checklist; build-your-own-agent
     brief)
   - Configure publishing via GitHub Actions on push to
     main
   - Add drawer entry ⭐ Getting Started in `left_nav.js`
     that opens the Pages URL in a new tab (dismissable
     per-browser)
   - Update welcome banner (TB-US-NN-4) to link to Pages
     URL
   - **NO** in-app `/static/getting-started.html` is
     created
   - **Sequencing:** executes after TB-US-005 public
     repo cut (needs Pages hosting to work).

   *Was: "Getting-started page" (in-app). Reframed to
   external Pages site per Q6 decision.*

6. **TB-US-NN — INSTALL.md + README restructure.**
   - Rewrites per §7 guidance
   - Downstream of all the above (needs the actual flow
     to describe)
   - Prereq for TB-US-005 v0.1 release-cut.

7. **TB-US-NN — Build + publish the math-example staged
   progression artifacts.**
   - Assemble public-domain math RAG corpus (GSM8K
     rationales + SymPy docs + Wikipedia math pages)
   - **Produce ATTRIBUTION.md for RAG sources (per Q11)**
     — each source + its license verbatim
   - Curate the math training set (100-200 SME-vetted
     examples); **include LICENSE.md + MODEL-CARD.md
     under Apache 2.0, © Eversole Learning**
   - Build the eval harness (GSM8K subset, 50-100
     problems, exact-match + rubric)
   - Run Stage 0 benchmark (bare LLM) → record score
   - Run Stage 1 benchmark (+RAG) → record score, measure
     ΔRAG
   - Train the Stage 2 adapter against the training set
   - Run Stage 2 benchmark (+adapter) → record score,
     measure ΔAdapter
   - Package Stage 2 adapter + hash as a GitHub Release
     artifact; **include LICENSE + HuggingFace-standard
     MODEL-CARD.md (per Q11)**
   - Export experiment metadata + scored results as the
     bundle that TB-US-NN-3 (above) seeds on first boot
   - **This is the operator's "we are going to do this"
     work.** Not shipped under TB-US-045 umbrella — it's
     content production, not reactive UI, and has
     dependencies on TB-US-029 (verification example) +
     TB-US-030 (operator workflow)

**Minimum arc for v0.1 release:** stories 1, 3, 4, 6, 7
(secure admin + math-example seed + welcome banner + docs
restructure + staged-progression content). Stories 2, 5
are improvements but not blockers.

**Story 7 is net-new work** that didn't exist before Q3C's
staged-progression resolution. It depends on TB-US-029
and TB-US-030 scope and may absorb significant parts of
both. Worth evaluating whether to formally rework those
stories' scopes once this spike closes.

---

<a id="sec-9"></a>

## 9. Open questions for operator decision

### Q1 — Admin password bootstrap mechanism

**Decision (2026-10-17):** Option A — **random password on
first boot, printed to stdout + written to a chmod-600 file
in `logs/first-run-admin.txt`.**

Mechanics locked:

- `UserManager._init_database()` detects empty users table.
- If `DEFAULT_ADMIN_PASSWORD` env var is unset:
  - Generate 24-char cryptographically-random passphrase
    (`secrets.token_urlsafe(18)`).
  - Create admin user: `username=admin` (or env override),
    hashed password, email env-override or
    `admin@localhost`.
  - Set new `must_change_password=1` flag on the row
    (schema change: add column to users table).
  - Print prominently to stdout:
    ```
    ========================================
    TrainingBench first-run admin credentials:
      username: admin
      password: <generated-passphrase>
    Store this password now. Change it after first login.
    ========================================
    ```
  - Write same credentials to `logs/first-run-admin.txt`
    with `chmod 600`.
  - File is deleted after first successful password change
    (so a long-running install doesn't leak old creds).
- If `DEFAULT_ADMIN_PASSWORD` IS set (dev / CI path): use
  it; do NOT set `must_change_password=1` (operator
  explicitly chose this password).

**Operator note (2026-10-17):** *"this is hard to test for
i will need to go through a download and install, but the
design seems sound."* Testing of the actual flow waits
until the implementation ships (follow-up story #1 in §8)
and the operator does a clean install cycle. The design
decision stands; the test comes with execution.

**Testing surface at execution time:**

- Fresh venv, empty `users.db` deleted, service start →
  stdout has the credentials banner
- `logs/first-run-admin.txt` exists with `chmod 600`
- Can log in with those creds; forced-change page intercepts
- After successful change, flag flips + file deleted
- Env-override path still works (set
  `DEFAULT_ADMIN_PASSWORD=X`, start → login as `admin / X`,
  no forced change)

---

### Q2 — SECRET_KEY and PASSWORD_SALT handling

**Decision (2026-10-17):** Option A — **auto-generate on
first boot, persist to `backend/db/.secrets` (JSON, chmod
600, gitignored).** Startup warning fires if the effective
value matches the hardcoded fallback sentinel string.
Migration mitigation (a) applies to existing installs.

**Resolution order** at startup, highest precedence first:

1. **Env var** (`SECRET_KEY` / `PASSWORD_SALT`) — operator
   explicit override; always wins.
2. **File** (`backend/db/.secrets` — JSON blob) — persisted
   auto-generated values from a previous first-boot.
3. **Hardcoded fallback** — only when both env var is
   unset AND file write fails. Logged as a loud startup
   warning.

**First-run behavior** (fresh install, no env, no file):

- Generate 32-char urlsafe tokens via
  `secrets.token_urlsafe(24)` for both.
- Write `backend/db/.secrets` with `chmod 600`:
  ```json
  {
    "SECRET_KEY": "<generated>",
    "PASSWORD_SALT": "<generated>",
    "generated_at": "<ISO-8601 UTC>"
  }
  ```
- Use the generated values. No warning (secrets are
  proper).

**Existing-install migration — mitigation (a):**

- Detection: `users.db` exists AND no `backend/db/.secrets`
  file AND no env vars.
- Interpretation: this install never had proper secrets;
  currently depending on the hardcoded sentinel values.
- Action: **copy the hardcoded sentinel values into
  `backend/db/.secrets`** (preserves existing password
  hashes + active sessions).
- Startup warning fires because the effective values are
  still the sentinels:
  ```
  ⚠️  SECRET_KEY/PASSWORD_SALT are the hardcoded defaults.
      This install's secrets are known-weak but preserved
      for backward compatibility. To rotate: delete
      backend/db/.secrets, unset the env vars, restart.
      Note: rotation invalidates all sessions AND all
      stored password hashes.
  ```
- Operator rotates deliberately when ready; no forced
  disruption.

**Rotation path** (future, out of this spike's scope):

A follow-up TB-US-NN could add an "Rotate secrets" admin
action that regenerates values + forces re-login for all
users + offers password-reset-link workflow. Not v0.1.

**Related:**

- `TB-US-003` (per-user salts, Deferred): when that lands,
  `PASSWORD_SALT` becomes obsolete entirely (per-user
  salts replace the global salt). This Q2 design is a
  transitional step until TB-US-003 reshapes the hashing
  architecture.

**Testing surface at execution time:**

- Fresh install → `backend/db/.secrets` created, chmod
  600, contains two random-looking strings
- Existing-install migration → `.secrets` created with
  hardcoded values, startup warning visible
- Env override still works (set `SECRET_KEY=X`, restart,
  observe X is used)

---

### Q3 — Shipped example agent on first run (reframed 2026-10-18)

Original Q3 was "do we auto-create a `default` placeholder?"
Reframed by operator insight: ship ONE example agent that
demonstrates component contributions via measurable staged
experiments. Replaces placeholder-driven thinking with
pedagogy-driven thinking. Full design in §4.

---

### Q3B — Example count + which domain

**Decision (2026-10-18):** **One example only — `math-example`**.

- Minimizes install complexity for v0.1
- Math has universal operator exposure (low cognitive
  barrier)
- Math lends itself to measurable eval (definite correct
  answers, simple rubrics)
- Public-domain datasets available (GSM8K Apache 2.0/MIT,
  MATH MIT)
- Aligns with TB-US-029 (verification example) and
  TB-US-043 Q10 (first-example choice)

Additional example domains (CUAD, concrete-mix, support
etc.) deferred to future stories once v0.1 ships.

---

### Q3C — Pre-trained adapter delivery (staged-progression framework)

**Decision (2026-10-18):** **Staged-progression install
+ C3a GitHub Release artifact + C3d fallback.**

Shipped `math-example` structured as three experiments:

- Stage 0 — bare LLM, no RAG, no adapter
- Stage 1 — LLM + RAG (adds ΔRAG delta)
- Stage 2 — LLM + RAG + adapter (promoted Sweet Spot)

All three run against the same public-domain eval harness
with measured scores. Operator sees the deltas side-by-side
in Compare on first open.

**Adapter delivery:**

- Shipped in git: RAG seed docs (~5-10 MB), training set
  JSON, eval harness, system prompts, experiment metadata
- **NOT shipped in git:** pre-trained adapter binary
  (~120 MB)
- **Delivered via:** GitHub Release artifact; TB prompts
  via welcome banner to download or train own
- **Fallback (C3d):** Stage 2 can be left empty; TB works
  at Stages 0 + 1; operator trains their own adapter when
  ready

Trade-off accepted: ~120 MB bandwidth cost on first boot
(for operators who want full Stage 2) in exchange for lean
git repo + optional-first-step UX + reproducibility.

Full §4 captures the staged-progression design.

---

### Q3D — Zero-agents allowed after operator action

**Decision (2026-10-18):** **Yes — zero agents allowed.**

- Fresh install has math-example
- Operator can rename it, delete it, create siblings
- If operator eventually deletes all agents, drawer shows
  empty-state UI ("No agents. Create one to begin.") and
  agent-scoped items gray out
- Admin surface (Users / API keys / Logout) still works
- No forced-minimum; no auto-recreate on empty

The empty-state UI uses the same component the "operator
declined math-example at install" case would use (if that
path exists); one UI serves both.

---

### Q4 — First-login forced password change

**Decision (2026-10-18):** Option A — **hard block via
`must_change_password` flag + dedicated forced-change
page**. Main decision already locked by Q1's `must_change_password`
flag design; Q4 confirms + resolves four sub-decisions below.

**Q4a — Password strength policy on first-change:**
Minimum 10 chars. No complexity rules in this spike;
TB-US-003 (per-user salts, Deferred) will design the full
hashing + strength policy alongside the hashing
architecture rework.

**Q4b — Who gets the `must_change_password` flag:**
Only the auto-generated first admin (B1). Operator-created
users (via the admin modal) have intentional passwords set
by their super-user creator and don't get the flag.

**Q4c — Mid-change interruption:** Deterministic from the
flag model. Flag stays `1` until a successful password
change commits a new hash. Operator abandoning the forced-
change page (close browser, nav away) just means next
login re-triggers the forced flow. Not a decision; a
consequence to confirm.

**Q4d — API/CLI auth exemption:** No bypass (D1). API
clients either (a) use env-set `DEFAULT_ADMIN_PASSWORD`
(which exempts them from the flag entirely per Q1's design)
or (b) script the change-password call as part of their
flow. No frontend-only honoring of the flag; backend
enforces consistently.

**Testing surface at execution time:**

- Fresh install → login as auto-admin → forced-change page
  blocks all other routes
- Attempting to navigate directly to `/static/index.html`
  before changing → redirects to forced-change
- Password < 10 chars → form error, no submission
- Successful change → flag flipped, `logs/first-run-admin.txt`
  deleted, redirect to index.html
- Second login (now with changed password) → no forced-change
  prompt
- API client calling `/auth/login` → gets `must_change_password:
  true` in response; must call change-password endpoint before
  other actions succeed

---

### Q5 — Welcome banner shape

**Decision (2026-10-18):** Option A — **dismissable top
banner above index.html content**, with the full lean
bundle below. Expanded responsibilities from Q3C's
staged-progression reframe: banner also orients the
newcomer to the shipped math-example experiments and
handles the Stage 2 adapter download conditionally.

**Shape:** A — dismissable full-width banner strip above
the main content on index.html.

**Content (3 primary actions max):**

```
┌──────────────────────────────────────────────────────────────────┐
│  🎉 Welcome to TrainingBench                                       │
│                                                                    │
│  Your `math-example` agent is ready. See how each layer           │
│  contributes:                                                      │
│                                                                    │
│  [See how the layers compare →]  [Getting Started →]  [Dismiss]  │
│                                                                    │
│  <conditional, if Stage 2 adapter is missing>                     │
│  💡 Stage 2 (adapter) not yet downloaded.                         │
│    [Download pre-trained adapter (120 MB)]  [I'll train my own]  │
└──────────────────────────────────────────────────────────────────┘
```

**Primary actions:**

- **"See how the layers compare →"** — switches to the
  Compare tab pre-populated with Stage 0/1/2
- **"Getting Started →"** — opens `/static/getting-started.html`
  (Q6 output)
- **"Dismiss"** — hides banner; writes `tb_welcome_dismissed = <ISO
  timestamp>` to localStorage; no reappearance by default

**Conditional secondary (adapter not present):**

- Backend endpoint `/agents/math-example/snapshot/current`
  returns `{adapter_present: false}` → banner shows inline
  download prompt
- **"Download pre-trained adapter (120 MB)"** — fetches the
  GitHub Release asset, verifies hash, extracts to
  `agents/math-example/adapter/`, reloads Compare view
- **"I'll train my own"** — opens Training Runs with a
  pre-configured training run against the shipped training
  set

**Dismiss persistence:** localStorage key
`tb_welcome_dismissed`. Simple; survives page reloads;
clears if operator wipes their browser cache (acceptable —
re-dismissing is a 1-click action).

**Trigger logic:** on `index.html` load, check for
`tb_welcome_dismissed` in localStorage. If absent, show
banner. Backend does not gate this; purely frontend state.

**Reappearance:** none by default. Clearing localStorage
re-shows the banner. A future admin "re-show welcome tour"
button is out of scope here.

**Operator-created non-admin users:** also see the banner
on their first login per-browser (same localStorage check
— per-browser-per-user is fine).

**Testing surface at execution time:**

- Fresh install → login → forced password change → index.html
  loads → banner visible with 3 primary actions
- Click "Compare" → routes to Compare tab (with
  Stage 0/1/2 pre-selected per TB-US-NN-3 seed)
- Click "Dismiss" → banner hides; localStorage key written
- Reload page → banner stays hidden
- Clear localStorage → reload → banner re-appears
- Adapter missing → inline download prompt visible with 2
  action buttons
- Adapter present → inline download prompt not shown

---

### Q6 — Getting-started content surface

**Decision (2026-10-18):** **Dual-surface design** —
README.md (project root) + GitHub Pages site. Not either/or;
both needed, serving different depths of commitment.

**Operator insight (2026-10-18):** *"we have a chicken and
egg problem. we want potential users to examine what they
are getting into before they download. they either do that
with some sort of readme file or they can go to github
pages for initial introduction to the product."*

Resolved by recognizing these aren't alternatives — they're
complementary layers. Every mature OSS project (React,
FastAPI, HuggingFace Transformers, LangChain) uses this
exact pattern.

### Surface responsibilities

| Surface | Audience | Depth | Lives |
|---|---|---|---|
| **README.md** | Everyone landing on GitHub repo (default view) | 2-min skim | Repo root; GitHub auto-renders |
| **GitHub Pages site** | Users who clicked through from README | 10+ min read | Rendered from markdown in `/docs` or `gh-pages` branch |

### README.md v0.1 contents (TB-US-004's work absorbs this)

- One-paragraph TB overview + value proposition
- Screenshot or short GIF of TB in action
- Quickstart snippet (4-5 lines of shell commands)
- 5-8 bullet features
- **Prominent "📖 Full documentation" link to GitHub Pages URL**
- License / badges / contact

### GitHub Pages site v0.1 scope (2 pages)

- **Home** — Project overview, screenshots, use cases
  (more polished than README skim)
- **Getting Started** — The staged-progression story from
  §4; TB-US-047 Q7's checklist; Build-your-own-agent
  briefing; links to design docs

Install content stays in-repo at `INSTALL.md`. Both README
and Pages Home link to it. No install content duplicated
on the Pages site at v0.1.

Future Pages expansions (deferred): dedicated Install page
mirror, Design docs mirror, API reference, FAQ.

### Pages tooling

**Jekyll + chosen theme** (per Q6-a lean). Zero config beyond
theme pick; GitHub Pages native; "just add markdown" workflow.
Overbuild to MkDocs or Docusaurus is premature.

### URL structure

```
<owner>.github.io/trainingbench/
├─ (home)                        → Project overview
└─ /getting-started              → Onboarding (Q6 content)
```

### Cross-references

- **README → Pages:** "📖 Full documentation" button near top
- **Pages header → GitHub repo:** "Code on GitHub" link
- **TB in-app welcome banner (Q5) → Pages Getting Started:**
  `<a target="_blank" href="https://<owner>.github.io/trainingbench/getting-started">`
- **TB in-app drawer item ⭐ Getting Started:** opens same URL
  in new tab; dismissable per-browser via localStorage
  (`tb_getting_started_hidden`)

### In-app role (what TB itself does)

- **No `/static/getting-started.html`** created inside TB —
  content lives externally on GitHub Pages
- Welcome banner "Getting Started →" button → external URL
  in new tab
- Drawer item ⭐ Getting Started → same URL in new tab;
  dismissable (localStorage); page URL still direct-accessible
  after dismissal
- The in-app welcome banner (Q5) still exists as the
  immediate post-install nudge; Pages is where deeper
  reading happens

### Sequencing / timing

Pre-launch sequence:
1. **README.md first** — must exist before public repo goes
   live (TB-US-004's work, Proposed state).
2. **Public repo cut** — TB-US-005 release. README has
   `"📖 Full docs (coming soon)"` placeholder if Pages
   isn't ready yet.
3. **GitHub Pages site shortly after** — Jekyll + Home +
   Getting Started pages ship. README's "Full docs" link
   goes live.

### Testing surface at execution time

- Visit GitHub repo URL → README visible as default view
- README "📖 Full documentation" → opens Pages URL
- Pages Getting Started shows the staged-progression story
  per §4
- Operator installs TB → sees in-app welcome banner (Q5)
- Welcome banner "Getting Started →" → opens Pages URL in
  new tab (preserving the TB workspace)
- Drawer item ⭐ Getting Started → same URL in new tab
- Dismissing drawer item → item hides; URL direct-navigation
  still works

---

### Q7 — Onboarding checklist contents (revised 2026-10-19)

**Decision (2026-10-19):** Phased checklist (3 phases) on
the Pages Getting Started page; read-only numbered items;
locations described in prose (no deep links to in-app
tabs); **Phase 3 forks into two tracks (GPU vs
non-GPU)**; dedicated "What to expect from PEFT training"
section appended.

**Structure:** phased (3 phases: See / Learn / Build).

**Interaction model:** read-only numbered items. No
checkboxes; Pages site is static and can't sync TB state.

**Deep-linking strategy:** describe locations in prose
("Open the Compare tab"), no hardcoded URLs. Portable
across any TB install hostname.

### Content items (12 total)

**Phase 1 — See it work** (your math-example is ready):

1. **Confirm your admin password is set** — should
   already be done via the forced-change page on first
   login; if not, do that first.
2. **Open Compare** — see three experiments side-by-side:
   Stage 0 bare LLM, Stage 1 +RAG, Stage 2 +adapter. Read
   the deltas (ΔRAG and ΔAdapter).
3. **(If Stage 2 shows "adapter not downloaded")** Click
   "Download pre-trained adapter" in the welcome banner —
   gives you the complete 3-stage picture.
4. **Ask your math-example a question** — Chat tab; try
   a math problem; watch it answer.

**Phase 2 — Understand the pieces** (what's inside
math-example):

5. **Open Training Sets** — see the curated math examples
   that produced the Stage 2 adapter. Notice: instruction /
   output format.
6. **Open Databases** — see the chroma collection holding
   the math RAG documents (GSM8K rationales, SymPy docs,
   Wikipedia math pages).
7. **Open Query History** — your Chat questions appear
   here with their routing + scoring.
8. **Read "What to expect from PEFT training"** — the
   section below prepares you for Phase 3 Track A.

**Phase 3 — Make it yours (two tracks):**

**Track A — if you have a GPU** (full lifecycle):

9. **Create your own agent** — in the agent-selector,
   create a new agent (e.g., `my-domain`). Alternatively,
   rename `math-example` to something meaningful.
10. **Add documents to your agent's RAG** — Upload tab
    (file-based) or Scrape tab (web content).
11. **Build a training set** — curate examples specific
    to your domain; from Chat failures that need
    corrections.
12. **Train your first adapter** — Training Runs tab;
    produces your own Stage 2 adapter.
13. **Promote your first Sweet Spot** — once you measure
    the delta your adapter adds, promote the snapshot.
    You've now completed the full lifecycle.

**Track B — if you don't have a GPU** (limited but
functional):

9. **Create your own agent** — same step as Track A.
10. **Add documents to your agent's RAG** — Upload /
    Scrape. Doesn't require GPU.
11. **Try the shipped math-example adapter in your
    agent** (if your domain overlaps enough) — gets you
    Stage 2-equivalent performance without local
    training.
12. **Explore cloud-GPU options** when you're ready to
    train: rent GPU time (~$0.50-$2/hour cloud compute),
    or future training-as-a-service when TB ecosystem
    grows.
13. **Keep iterating on RAG + prompt** — these are the
    axes you CAN tune without a GPU. Updates in TB-US-040
    (RAG prompt / query routes) make this productive.

### "What to expect from PEFT training" section (on Pages
Getting Started, between Phase 2 and Phase 3)

Content candidate:

```
What to expect from PEFT training

Hardware
  - Minimum: Nvidia GPU with 8 GB VRAM (QLoRA at 4-bit)
  - Recommended: GPU with 16+ GB VRAM
  - M-series Mac: 16 GB unified memory (slower but viable)
  - CPU-only: possible but very slow (days vs hours)

Training time (math-example scale, ~200 examples, 3 epochs)
  - Minimum GPU: ~30-60 min
  - Recommended GPU: ~10-20 min
  - M-series Mac: ~20-40 min
  - CPU-only: ~4-10 hours

Dataset preparation
  - 50-200 examples: enough to see a performance delta
  - 500-2000: diminishing returns on small models
  - Quality > quantity

Expected quality trajectories (math-example scale)
  - 50 examples: typically +5-10% over Stage 1
  - 200 examples: +10-20% over Stage 1 (math-example scale)
  - 500+ examples: +15-25% over Stage 1

When PEFT helps
  - Domain-specific tone, structured output
  - Factual grounding on narrow topics
  - Consistent response patterns

When PEFT helps less
  - Broad general knowledge (prefer bigger LLM)
  - Highly creative, open-ended generation
  - Factual lookups (RAG does this better)

If you don't have a GPU
  - Download the pre-trained math-example adapter (free; ~120 MB)
  - Use the shipped adapter for math-adjacent domains
  - Rent GPU time: ~$0.50-$2 per hour (cloud compute)
  - Future: training-as-a-service when TB ecosystem grows
```

### Why two tracks

Non-GPU users are a large potential operator population.
Making them feel welcome and productive protects their
engagement — any user who understands PEFT value is a
win, even if they never train their own adapter.

### Testing surface at execution time

- Operator with GPU reads Phase 3 Track A → trains →
  completes checklist
- Operator without GPU reads Phase 3 Track B → uses
  shipped adapter → completes limited lifecycle
- Both read "What to expect from PEFT training" — set
  expectations correctly for Phase 3 before diving in

---

### Q8 — Install docs structure

**Decision (2026-10-19):** Four sub-decisions resolved.

**Q8a — INSTALL.md as single source of truth; Pages
embeds via Jekyll `include` (preferred) or links to
GitHub (fallback).**

- Install content lives once in `INSTALL.md` at repo root
- Pages Install page uses Jekyll `include` to embed the
  INSTALL.md content, so Pages visitors see it inline
  without clicking to GitHub
- If `include` of a sibling-tree file turns awkward, the
  fallback is a prominent GitHub link ("View INSTALL.md
  on GitHub →") on the Pages Install page
- Single source means no drift between repo and Pages

**Q8b — Quickstart section in README.md** (no separate
QUICKSTART.md).

- README has a prominent "Quickstart" section near the
  top (after the one-paragraph overview)
- 4-5 shell lines: clone / venv / pip install / start
  service / visit URL
- Convention-matching; keeps the GitHub repo view
  immediately actionable for skimmers

**Q8c — INSTALL.md structure (8 sections):**

1. Prerequisites (Python 3.11+, Ollama + base LLM, optional
   GPU, disk requirement)
2. Clone + install (git / venv / pip)
3. First service start (console admin creds output per Q1;
   `logs/first-run-admin.txt` recovery path)
4. First visit — new user flow (gate → login → forced
   password change per Q4 → welcome banner per Q5 →
   math-example ready; optional Stage 2 adapter download
   per Q3C)
5. What's in math-example (1-paragraph pointer to Pages
   Getting Started)
6. Env var reference table (Required / Auto-generated /
   Operator-overridable per Q9 — pending)
7. Troubleshooting (port conflict, Ollama not found, chroma
   indexing fails, adapter download fails, forced-change
   loop issues)
8. Updating TB (git pull + pip install; what state is
   preserved — users.db, agents.db, snapshots — vs reset)

**Q8d — OSS repo files at v0.1:**

| File | Status |
|---|---|
| `README.md` | Required; TB-US-004 drafts; dual-surface hook per Q6 |
| `INSTALL.md` | Required; this spike's §4 covers structure |
| `LICENSE` | Required; Apache 2.0 per TB-US-009 (Shipped) |
| `CONTRIBUTING.md` | Required at v0.1; minimal; "file issues at <URL>; PRs follow this contrib model" |
| `CODE_OF_CONDUCT.md` | Required at v0.1; standard Contributor Covenant |
| `SECURITY.md` | Required at v0.1; minimal; "disclosure: email <address>" |
| `CHANGELOG.md` | NOT required at v0.1; GitHub release notes serve this role |
| `.gitignore` | Already exists; must include `backend/db/.secrets` (per Q2) and `logs/first-run-admin.txt` (per Q1) |

The five "Required at v0.1" files line up with GitHub's
Community Standards checklist (per TB-US-014 OSS compliance
work). TB-US-014's upcoming draft owns the detailed
content of each; this Q8 captures the inclusion decision.

### Testing surface at execution time

- Visit GitHub repo → README visible; Quickstart section
  near the top; 4-5 lines are copy-paste-able
- Click "📖 Full documentation" in README → Pages Home
- Click "📥 Install" on Pages → Pages Install page
  renders INSTALL.md inline (or links to GitHub if the
  fallback is active)
- INSTALL.md § structure walks the operator from clone
  to running TB
- Repo top level has 5 required OSS files (README, INSTALL,
  LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY)

---

### Q9 — Env-var required vs auto-generated

**Decision in progress (2026-10-19).** Three sub-decisions:
Q9a captured below; Q9b (TB_PAGES_URL) and Q9c (audit log
env var consolidation) pending.

**4-tier env var model:**

| Tier | Behavior | Vars |
|---|---|---|
| **1 — Required** | Operator must set; TB refuses to start without | *(none)* |
| **2 — Auto-generated if missing** (Q1 + Q2) | Random values generated on first boot, persisted to on-disk files | `SECRET_KEY`, `PASSWORD_SALT`, admin password |
| **3 — Recommended** | Operator should set based on deployment context; TB warns if unset but still starts | `SITE_PASSPHRASE` |
| **4 — Optional overrides with defaults** | Sensible defaults; operator can override | Everything else |

**Minimum fresh-install env var requirement: ZERO.** TB
works out-of-the-box with no env vars set. The operator
sees the warnings and makes informed choices.

---

### Q9a — SITE_PASSPHRASE unset behavior

**Decision (2026-10-19):** Option A — **unset = open
access + startup warning**. Operator-informed choice;
deployment-context-dependent; TB does not force the
decision.

**Operator insight (2026-10-19):** *"the pre-login access
barrier to protect against bot login attacks works. we do
not know at this time how users are going to deploy TB and
where. it could be in the cloud, but, it could be a VPN.
ultimately it is an installation choice that the user
makes up front and will face the consequences down the
road that is out of our control."*

**Design intent of the gate (captured as TB vocabulary):**

- **Pre-login access barrier against bot login attacks.**
  Lightweight; shared-passphrase-level; not strong auth.
- **Shared within a small team** — one passphrase for the
  whole team; everyone with legitimate access knows it.
- **Checked BEFORE the login page is shown** — hides the
  login endpoint from random internet traffic.
- **Deployment-mode dependent** — matters for public-
  internet installs; less so for LAN / localhost / VPN.
- Not a replacement for per-user login — that's the real
  auth layer behind the gate.

**Startup warning text when unset:**

```
⚠️  Gate disabled (SITE_PASSPHRASE is unset).
    If this install will be reachable from the public
    internet, set SITE_PASSPHRASE in your service
    environment to add a pre-login access barrier against
    bot login attacks. Local / LAN / VPN installs can
    safely leave it disabled.
    See INSTALL.md § "When to enable the gate" for
    deployment-context guidance.
```

**INSTALL.md § 6.1 "When to enable the gate":**

Full-rationale section added in INSTALL.md's env-var-
reference area. Explains the "pre-login access barrier"
concept, when to enable (public-internet reachable), when
you can skip it (localhost / LAN / VPN), how to set it
(systemd Environment directive or `.env` file), and how
to change it later (session invalidation implications).

**Pages Getting Started: brief callout** mirrors the INSTALL
guidance in 3-4 sentences; links to INSTALL.md for full
treatment.

**Vocabulary standardization:**

- User-facing docs: "**pre-login access barrier**" (plus
  "against bot login attacks" when more context is helpful)
- Internal shorthand (design docs, chat): "poor man's
  2FA" is honest + memorable
- Not using: "gate" alone (ambiguous), "shared
  password" (confused with per-user), "SITE_PASSPHRASE"
  (env var name only)

**Why not require it or auto-generate it:**

- Deployment context is operator-known, not TB-knowable:
  public cloud / LAN / VPN / air-gapped are all valid
- Auto-generating defeats the "shared-with-team" semantic
  (operators share the passphrase; a random one has to be
  distributed anyway, might as well let operator choose)
- Requiring it adds install friction for localhost / LAN
  / dev operators who don't need it

**Operator-ownership framing:** this is an installation
choice. TB informs; operator decides; consequences are
operator-owned.

### Testing surface at execution time

- Fresh install with no env vars → start service → console
  shows the warning banner
- Set `SITE_PASSPHRASE=anything` → restart → warning gone;
  gate active; `gate.html` requires passphrase
- Unset `SITE_PASSPHRASE` → restart → warning returns;
  `gate.html` auto-grants (ungated)

---

### Q9b — TB_PAGES_URL env var

**Decision (2026-10-19):** Option B — **add `TB_PAGES_URL`
env var with canonical default**.

The welcome banner (Q5) and drawer item ⭐ Getting Started
(Q6) link out to GitHub Pages URL. Making this an env var
enables:

- Forks of TB that run their own Pages site
- Staging environments pointing at pre-release docs
- Air-gapped operators pointing at an internal mirror

**Default:** canonical GitHub Pages URL (set once the Pages
site goes live; e.g. `https://eversole-learning.github.io/trainingbench/getting-started/`).

**Resolution:** env var > hardcoded default. Welcome banner
+ drawer item use `TB_PAGES_URL` if set, canonical default
otherwise.

**No startup warning if unset** (unlike SITE_PASSPHRASE) —
the default URL is correct for most installs.

---

### Q9c — Audit-log env var consolidation

**Decision (2026-10-19):** Option A — **keep per-subsystem
audit-log env vars**, defer consolidation.

**Operator note (2026-10-19):** *"we definitely need audit
logs"* — infrastructure stays intact.

**Current env vars (preserved):**

- `DEMO_MODE_AUDIT_LOG_PATH` — default: `logs/demo_mode_audit.jsonl`
- `RAG_PROMPT_AUDIT_LOG_PATH` — default: `logs/rag_prompt_audit.jsonl`
- `QUERY_ROUTES_AUDIT_LOG_PATH` — default: `logs/query_routes_audit.jsonl`
- Future: `OT_AUDIT_LOG_PATH` per TB-US-024
- Future: whatever new audit log TB-US-NN-stories add

**Why per-subsystem granularity preserved:**

- Operators debugging specific subsystems can redirect
  one log without affecting others
- Operator-chosen storage paths (fast disk for frequently-
  written logs, slow disk for infrequent) remain
  possible
- Convention already in place from TB-US-033 and TB-US-017

**Future consolidation (deferred):**

If the number of audit-log env vars grows unwieldy (6+)
or if operators request a single-knob control, a future
story adds `LOG_DIR` as a parent default. Per-subsystem
env vars remain as overrides. Not needed at v0.1.

---

### Q10 — Setup-done marker

**Decision (2026-10-19):** Option A — **`must_change_password`
flag alone**. Do not add a separate `setup_complete`
boolean. Progressive markers (Option C) deferred to a
future story if a graduated welcome experience becomes
desired.

**Operator note (2026-10-19):** *"we do not need to
overcomplicate this feature for initial launch."*

**What "setup done" means at v0.1:**

Server-side tracking is needed for exactly one event:
- Password changed from the auto-generated value →
  `must_change_password` flipped to `0`

That flip triggers a real side effect (deletion of
`logs/first-run-admin.txt` per Q1). Everything else is
either operator exploration (not state-tracked) or
localStorage-tracked per-browser (welcome banner
dismissal, getting-started drawer-item hidden flag).

**No `setup_complete` boolean at v0.1.** The
`must_change_password = 0` state IS the setup-done
signal. A separate flag duplicates meaning.

**Admin UI behavior:** Admin surfaces (Users management,
future API keys, etc.) are always available to super users
regardless of setup state. No "features disabled until
setup done" gate.

**Future enhancement path (Option C) remains open:** if TB
ever wants a graduated welcome experience ("welcome →
first agent created → first adapter trained → ..."),
progressive markers become useful. Captured as potential
future work; not drafted as a story yet.

---

### Q11 — Shipped-artifact licensing + attribution infrastructure (added 2026-10-19)

**Decision (2026-10-19):** Three shipped artifacts, each
with explicit licensing + attribution.

**Operator insight (2026-10-19):** *"there is some content
generated by eversole learning (EL) that is copyrighted
for EL. ... this training involves derivative works of any
training sets downloaded from the internet and the work of
training and testing of the PEFT to produce an initial
adapter is a derivative work."*

**License chain:**

```
Public-domain source data (GSM8K Apache 2.0, MATH MIT,
                           SymPy BSD, Wikipedia CC-BY-SA)
    ↓ selected, curated, formatted by EL
Training set file (derivative work; EL ©; Apache 2.0)
    ↓ trained via TB on this set, against specific base LLM
Pre-trained adapter binary (further derivative; EL ©;
                            Apache 2.0; model card)
```

**Per-artifact decisions:**

| Artifact | License on TB redistribution | Attribution requirements |
|---|---|---|
| **RAG seed documents** | Each source's original license (honored verbatim) | ATTRIBUTION.md lists each source + its license |
| **Training set JSONL** | Apache 2.0, © Eversole Learning | Attribution file lists source datasets; model card describes composition |
| **Pre-trained adapter binary** | Apache 2.0, © Eversole Learning | Model card per HuggingFace convention: base LLM, hyperparameters, training-set hash, scored performance |

**Repo structure:**

```
agents/math-example/
├── LICENSE.md                       — Overview + chain of attribution
├── rag/
│   ├── sources/
│   │   ├── gsm8k-rationales.jsonl   (Apache 2.0 — attribution to Cobbe et al. 2021)
│   │   ├── sympy-docs-excerpt.md    (BSD — attribution to SymPy)
│   │   └── wiki-math-pages.md       (CC-BY-SA — attribution to Wikipedia)
│   └── ATTRIBUTION.md               — Each file's license + attribution
├── training-set/
│   ├── math-training-v1.jsonl       (Apache 2.0, © Eversole Learning)
│   └── MODEL-CARD.md                — Composition, size, intent
└── adapter/
    ├── (binary — delivered via GitHub Release artifact)
    ├── LICENSE                      (Apache 2.0, © Eversole Learning)
    └── MODEL-CARD.md                — Base LLM, hyperparameters,
                                       training-set hash, scored performance
```

**Why Apache 2.0 for EL-copyrighted artifacts:**

- Matches TB's own license (TB-US-009 Shipped)
- Permissive: operators can redistribute, modify, use
  commercially
- Attribution requirement preserves EL's authorship
  record
- Standard for ML research artifacts; aligns with
  HuggingFace model-card norms

**Why not more restrictive licensing (NC, SA, custom):**

- Non-commercial clauses discourage adoption by
  commercial operators (who are a major TB audience)
- Share-alike has viral complications
- Custom EL license adds legal review surface for every
  operator
- Permissive Apache 2.0 with required attribution
  balances openness with authorship recognition

**EL copyright claim is standard for ML derivative
artifacts.** HuggingFace model cards and TensorFlow Hub
models routinely claim copyright on trained weights.
Users who redistribute must retain the EL copyright +
attribution — standard Apache 2.0 behavior.

**Implementation details (for the follow-up story):**

- Each artifact's licensing files live at the paths above
- Model cards use HuggingFace-standard format (YAML
  frontmatter + markdown body)
- GitHub Release artifact for the adapter includes a
  `README.md` restating the license
- Pages site's "Downloads" section notes the Apache 2.0
  license + attribution requirement

---

<a id="sec-10"></a>

## 10. Decision log

| Date | Decision | Context |
|---|---|---|
| 2026-10-17 | Spike opened (TB-US-047) | Operator design signal — "the install workflow needs to be ironed out in order to provide guidance to new users." |
| 2026-10-17 | **Q1 — Admin password bootstrap: random on first boot** | Option A. Random 24-char passphrase generated when `users` table is empty and `DEFAULT_ADMIN_PASSWORD` env var is unset. Printed to stdout + written to `logs/first-run-admin.txt` (chmod 600). `must_change_password` flag added to users table; forced-change page handles first login. File deleted on first successful password change. Env-override path preserved for dev/CI. Testing deferred to real install-cycle at execution time. |
| 2026-10-17 | **Q2 — SECRET_KEY + PASSWORD_SALT: auto-generate on first boot, persist to `backend/db/.secrets`** | Option A + migration mitigation (a). File is JSON (chmod 600, gitignored); resolution precedence env > file > hardcoded fallback. On existing-install migration, hardcoded sentinel values are copied into `.secrets` to preserve password hashes + sessions; startup warning fires because effective values still match the sentinels. Rotation workflow deferred to a future admin-action story. Related to TB-US-003 (per-user salts, Deferred) — this is transitional until TB-US-003 reshapes hashing. |
| 2026-10-18 | **Q3 reframed — placeholder `default` superseded by shipped example** | Operator insight: install must SHOW the agent concept, not placeholder it. Three sub-decisions below (Q3B/C/D). Full design in §4. |
| 2026-10-18 | **Q3B — Ship ONE example: math-example** | One domain only for v0.1. Math chosen for universal operator exposure, measurability (definite correct answers), public-domain datasets (GSM8K + MATH), and alignment with TB-US-029 + TB-US-043 Q10. Additional domains (CUAD, concrete-mix, etc.) deferred. |
| 2026-10-18 | **Q3C — Staged-progression install (3 experiments) + adapter via GitHub Release** | math-example structured as 3 measurable experiments: Stage 0 (bare LLM), Stage 1 (+RAG, ΔRAG measured), Stage 2 (+adapter, ΔAdapter measured; promoted Sweet Spot). Compare view shows all three with deltas on first open. Adapter binary ~120 MB NOT in git — shipped as GitHub Release artifact; welcome banner prompts download or train-your-own. Fallback: Stage 2 can remain empty; Stages 0 + 1 work regardless. Lean git repo + opt-in Stage 2 UX + reproducibility (operator can re-train from shipped training set to verify shipped adapter). |
| 2026-10-18 | **Q3D — Zero agents allowed after operator action** | If operator deletes all agents (including math-example), drawer shows empty-state and agent-scoped items gray out. Admin surface still works. No forced-minimum; no auto-recreate. Same empty-state UI serves both "declined math-example" and "deleted all agents" paths. |
| 2026-10-18 | **TB-US-044 Q13 resolved** | TB-US-044's zero-agent/default-agent question is resolved here: ship math-example (not placeholder); zero-agents allowed after operator action. Decision mirrored into TB-US-044's log. |
| 2026-10-18 | **Q4 — Forced password change: hard block (confirmed) + 4 sub-decisions** | Main decision locked by Q1. Sub-decisions: Q4a strength = minimum 10 chars (full policy deferred to TB-US-003); Q4b flag applies only to auto-generated first admin (B1); Q4c mid-change interruption re-triggers forced flow (deterministic from flag); Q4d no API bypass (D1). |
| 2026-10-18 | **Q5 — Welcome banner: dismissable top banner on index.html with 3-action content + conditional adapter prompt** | Shape A; headline + context + 3 primary actions (Compare / Getting Started / Dismiss). Dismiss persistence via localStorage key `tb_welcome_dismissed`. No reappearance by default. Conditional secondary row if Stage 2 adapter missing (download / train-own). Operator-created non-admin users see banner too (per-browser). |
| 2026-10-18 | **Q6 — Dual-surface Getting Started: README.md + GitHub Pages (not either/or)** | Resolves chicken-and-egg: README is 2-min hook (repo default view); Pages is 10+ min deep dive. Pages v0.1 scope = 2 pages (Home + Getting Started). Jekyll + chosen theme. Install stays in-repo at INSTALL.md; both surfaces link to it. TB in-app no longer gets its own getting-started.html — welcome banner + drawer item link out to Pages URL in new tab. Drawer item dismissable per-browser via localStorage (`tb_getting_started_hidden`). Sequencing: README first (TB-US-004); Pages shortly after public repo cut (TB-US-005). |
| 2026-10-19 | **Q7 — Checklist: phased 3 phases, Phase 3 forks into GPU vs non-GPU tracks + PEFT expectations section** | 12-13 items grouped as See (Phase 1, 4 items) / Learn (Phase 2, 4 items including a pointer to "What to expect from PEFT training") / Build (Phase 3, two 5-item tracks). Track A = GPU-equipped operators doing full lifecycle; Track B = non-GPU operators using shipped adapter + bringing their own RAG. Dedicated "What to expect from PEFT training" section on Pages Getting Started between Phase 2 and Phase 3 (hardware, time, dataset prep, quality trajectories, when PEFT helps/doesn't). Prose-described locations, no deep links. Read-only (no interactive checkboxes). |
| 2026-10-19 | **Q11 — Shipped-artifact licensing: Apache 2.0 for EL-derivative artifacts; honor source licenses on RAG sources** | Three artifacts: (1) RAG seed documents — each source's original license honored verbatim; ATTRIBUTION.md lists each source; (2) Training set JSONL — Apache 2.0, © Eversole Learning, with model card for composition; (3) Pre-trained adapter binary — Apache 2.0, © Eversole Learning, HuggingFace-standard model card (base LLM, hyperparameters, training-set hash, scored performance). Repo layout: `agents/math-example/{rag,training-set,adapter}/` with LICENSE + ATTRIBUTION / MODEL-CARD files per artifact. GitHub Release artifact for adapter includes README restating license. |
| 2026-10-19 | **Q8 — Install docs structure: 4 sub-decisions** | Q8a: INSTALL.md single source of truth; Pages embeds via Jekyll include (preferred) or links to GitHub (fallback). Q8b: Quickstart section in README.md (4-5 lines near top); no QUICKSTART.md. Q8c: INSTALL.md 8 sections (prereqs → clone/install → first service start → first visit → math-example pointer → env var reference → troubleshooting → updating). Q8d: 5 required OSS repo files at v0.1 (README, INSTALL, LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY); CHANGELOG deferred. `.gitignore` must include `backend/db/.secrets` + `logs/first-run-admin.txt`. |
| 2026-10-19 | **Q9a — SITE_PASSPHRASE unset = open access + startup warning** | Option A. Operator-informed choice; deployment-context-dependent (public internet vs LAN vs VPN); TB does not force the decision. Vocabulary: "pre-login access barrier against bot login attacks" (user-facing); "poor man's 2FA" (internal shorthand). Startup warning text spells out when to enable; INSTALL.md § 6.1 "When to enable the gate" covers the full rationale. Pages Getting Started gets a brief callout. Not auto-generated (defeats shared-with-team semantic) and not required (adds friction for LAN/VPN/localhost operators who don't need it). |
| 2026-10-19 | **Q9b — Add `TB_PAGES_URL` env var with canonical default** | Option B. Welcome banner (Q5) + drawer item ⭐ Getting Started (Q6) use `TB_PAGES_URL` env var if set, canonical GitHub Pages URL otherwise. Enables forks, staging, and air-gapped mirror operators to retarget the external docs URL without code changes. No warning if unset — default URL is correct for most installs. |
| 2026-10-19 | **Q9c — Keep per-subsystem audit-log env vars; defer consolidation** | Option A. `DEMO_MODE_AUDIT_LOG_PATH`, `RAG_PROMPT_AUDIT_LOG_PATH`, `QUERY_ROUTES_AUDIT_LOG_PATH` + future `OT_AUDIT_LOG_PATH` preserved. Per-subsystem granularity remains valuable for operators debugging specific subsystems or routing logs to different storage. If count grows unwieldy (6+), future story adds `LOG_DIR` as a parent default with per-subsystem overrides. Operator note: *"we definitely need audit logs"* — infrastructure stays intact. |
| 2026-10-19 | **Q10 — `must_change_password` flag alone (no separate setup_complete boolean)** | Option A. Only one event needs server-side tracking: password changed from auto-generated value. Flag flip triggers deletion of `logs/first-run-admin.txt` (per Q1). Everything else is operator exploration (not state-tracked) or localStorage-per-browser (welcome banner dismiss, getting-started drawer-item hide). No "features disabled until setup done" gate on admin UI. Future enhancement path to Option C (progressive markers for graduated welcome experiences) remains open; not drafted at v0.1 per operator direction *"we do not need to overcomplicate this feature for initial launch."* |
| 2026-10-19 | **All 12 open questions resolved; spike ready to close** | TB-US-047 design doc now has Decision lines on Q1-Q11 (12 questions total since Q3B/C/D counted together). Follow-up stories enumerated in §8. Operator approval of the full design pending; this entry marks the design content as complete. |

---

<a id="sec-11"></a>

## 11. What comes after this design is approved

Once every question in §9 has a **Decision:** line and the
operator confirms the design is ready-to-execute-against:

1. Follow-up stories in §8 get drafted.
2. TB-US-044's Q13 Decision line is populated with this
   spike's resolution (§4).
3. TB-US-005's v0.1 release gate is tied to the subset of
   §8 stories identified as blocking (admin bootstrap +
   default agent + welcome banner + docs restructure).
4. TB-US-004's README quickstart draft can proceed with
   the first-run flow nailed down.
