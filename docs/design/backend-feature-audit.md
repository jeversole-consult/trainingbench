# TB Backend Feature Audit (resurface roadmap pre-US-005)

**Status**: 2026-11-05 — audit complete; implementation stories TBD
**Related story**: [TB-US-086](../user-stories/tb-us-086.md)
**Motivates**: TB-US-005 scope decision (public v0.1 cut has been
deliberately held pending this audit)

## tl;dr

TB is substantially richer than the math-example research arc
has made visible. The backend carries forward most capabilities
inherited from the stalite fork, and the UI-overhaul (TB-US-018 +
TB-US-042) left some of those features without UI entry points
even though the backend still works. There is exactly one clear
feature gap (prompt classification) that is net-new work, not
resurface.

**The three Tier-1 UI resurface items** (unblock an honest US-005
pitch) are:

1. **Experiments UI** (TB-US-070 Proposed) — make the Sweet Spot
   methodology visible rather than a chat alert pointing at the API
2. **Version management UI** (per-component promote/release
   buttons) — so operators can see what's promoted without
   touching SQLite
3. **Spreadsheet calculator surface** — currently invisible to
   users even though the backend is wired; a "add a spreadsheet,
   ask it questions" entry would make this a demoable capability

Everything else either already has UI exposure (most of TB's
capability palette is surfaced in the left nav) or is explicitly
scoped for post-launch or deferred as backlog.

## 1. Audit methodology

A **capability** here means a user-recognizable feature (not a
single endpoint or module). The audit reconciles three sources:

- **Backend presence**: grep-verified file paths, endpoints,
  manager modules in `backend/`
- **UI exposure**: HTML tabs in `static/index.html`, dedicated
  pages (`training_sets.html`, `training_runs.html`, etc.),
  JavaScript entry points in `static/*.js`, and the left-nav
  entries in `static/left_nav.js`
- **Story-registry references**: which TB-US-NNN story shipped
  each capability, and which are "Proposed" (not yet implemented)

**Status categories**:

- **Surfaced** — backend works + UI entry point reaches it
- **Partial** — backend works + UI reachable via a workaround or
  incomplete view (e.g., Chat uses the calculator transparently
  but doesn't advertise it)
- **Dormant** — backend works + no UI entry point post-overhaul
- **Missing** — no backend implementation (true feature gap)

**US-005 relevance** (does the launch pitch depend on this?):

- **Pitch-critical** — the capability is core to how TB would be
  described in a social-media / Pages announcement
- **Pitch-adjacent** — valuable but not load-bearing on the pitch
- **Post-launch** — can land after US-005
- **N/A** — administrative / infrastructure

**Effort estimate**:

- **Minor** — connect existing endpoint to a new UI button (hours)
- **Moderate** — new UI tab or dedicated page + wire-up (~1 day)
- **Major** — needs backend work too (multiple days)

## 2. Capability-by-capability inventory

### Chat / RAG surface (user-facing core)

| Capability | Backend | UI | Status | US-005 | Effort |
|---|---|---|---|---|---|
| **RAG query** (chat) | `backend/rag/rag_system.py`, `/query` endpoint | `#chat-tab` in index.html + `script.js` | **Surfaced** | Pitch-critical | — |
| **Document processing** (PDF/DOCX/XLSX + OCR) | `backend/document_processor.py` (pypdf, pdfplumber, pdf2image, python-docx, openpyxl, pytesseract) | `#upload-tab` + `/upload` endpoint | **Surfaced** | Pitch-critical | — |
| **Web scraping** (single URL, multiple URLs, crawl) | `/scrape`, `/scrape-multiple-urls`, `/crawl-website` | `#scrape-tab` | **Surfaced** | Pitch-adjacent | — |
| **Semantic search** (vector) | `/search` endpoint + vector_store | `#search-tab` | **Surfaced** | Pitch-adjacent | — |
| **Document management** (list, delete, folders) | `/documents`, `/folders` CRUD | `#manage-tab` | **Surfaced** | N/A | — |
| **Query history** | `/sessions/my-history`, query_logger | `#history-tab` | **Surfaced** | N/A | — |

### Multi-LLM surface

| Capability | Backend | UI | Status | US-005 | Effort |
|---|---|---|---|---|---|
| **Multi-LLM backbone** (HuggingFace + Ollama + OpenAI providers at `rag_system.py` level; selectable per-experiment via `llm_identifier`) | `backend/rag/rag_system.py` `_init_llm()`, `/models` endpoint for Ollama listing | Model selector in Compare tab + `/models` consumed by UI | **Surfaced** (model picker in Compare); backbone powers every chat | Pitch-critical | — |
| **PowerSearch** (fan out same prompt to Gemini + ChatGPT + Grok via external API keys) | `backend/api/power_search.py`, `/power-search`, `/power-search/services` | `#powersearch-tab` | **Surfaced** | Pitch-critical | — |
| **Compare Results** (A/B two-config: DB-1×Model-1 vs. DB-2×Model-2, same question) | `/query` with different pins | `#compare-tab` | **Surfaced** | Pitch-critical | — |

### Multi-DB surface

| Capability | Backend | UI | Status | US-005 | Effort |
|---|---|---|---|---|---|
| **Multi-DB (ChromaDB collections)** — create, delete, switch active, duplicate | `backend/api/database_manager.py`, `/databases` CRUD + `/databases/switch` + `/databases/active` + `/databases/duplicate` | `#databases-tab` | **Surfaced** | Pitch-critical | — |

### Training + experimentation surface

| Capability | Backend | UI | Status | US-005 | Effort |
|---|---|---|---|---|---|
| **Training-set versioning** (sidecar JSONL, SHA-256-anchored, agent-scoped) | `backend/api/training_set_version_manager.py`, `/training-set-versions/*` | `training_sets.html` dedicated page | **Surfaced** | Pitch-critical | — |
| **Training-set export + mining** (export; from-query-log; from-ratings) | `/training/sets/*/export`, `/training/sets/from-query-log`, `/training/sets/from-ratings` | Surfaced via training_sets.html | **Surfaced** | Pitch-adjacent | — |
| **PEFT adapter training** (launch, cancel, metrics, logs, checkpoints, comparison) | `backend/api/training_run_tracker.py`, `training/math/train.py` subprocess, `/training/runs/*` | `training_runs.html` + `active_run_strip.js` sticky banner | **Surfaced** | Pitch-critical | — |
| **Sweet Spot experiments** (CRUD + background runner, per-experiment pinning of adapter/prompt/RAG/LLM/harness) | `backend/api/experiment_manager.py`, `backend/api/harness_runner.py`, `/experiments/*` + `/experiments/{id}/run` | **NONE** — `script.js:1202` shows alert "Experiment viewer ships with the next release. For now, use the API" | **Dormant** | **Pitch-critical** | **Moderate** (TB-US-070 Proposed) |
| **Agent + versioned components** (agents, prompts, RAG, adapters, routes, harnesses — each with draft/released/deprecated + promotion state) | 5 version managers (prompt, rag, adapter, route, harness) + agent_manager + agent_components table | Agent-management modal exists (`agent_management.js`, opens from left-nav admin area); version lifecycle buttons (release/promote) for individual components are **not surfaced** in the UI | **Partial** (agent picker surfaced; component-version lifecycle dormant) | **Pitch-critical** | **Moderate** (per-component promote/release UI) |

### Specialized handlers

| Capability | Backend | UI | Status | US-005 | Effort |
|---|---|---|---|---|---|
| **Spreadsheet calculator** (xlsx formulas invoked transparently during `/query` when the RAGSystem's `calculator` hook fires) | `backend/api/spreadsheet_calculator.py` (openpyxl + pandas; formula invocation for structured spreadsheets) | **None user-facing** — wired silently into Chat; no "upload spreadsheet and ask it questions" flow surfaces this | **Partial / Dormant** | Pitch-adjacent | **Minor** (UI entry: tell operators the feature exists) |
| **Prompt classification** (four-category classifier: qualitative/quantitative/lookup/mixed) | **None** (zero grep matches; TB-US-023 Proposed) | None | **Missing** | Post-launch (TB-US-023 arc, including TB-US-022-030) | **Major** (net-new backend + UI; multi-story arc) |
| **Spreadsheet formula EXTRACTION** (parse an xlsx, auto-discover what formulas it contains) | Indeterminate — operator mentioned this was done in stalite, but TB's `document_processor.py` reads xlsx into pandas DataFrames, which is not the same as formula extraction | None | **Missing or dormant — needs code inspection** | Post-launch | **Moderate-to-major** |

### Infrastructure / admin surface

| Capability | Backend | UI | Status | US-005 | Effort |
|---|---|---|---|---|---|
| **User management** (CRUD, roles, audit log) | `backend/api/user_manager.py` + `users.db` + audit_log; TB-US-017/041 | `user_management.js` modal, opens from admin dropdown | **Surfaced** | N/A | — |
| **API keys** (operator credentials for automation; `Authorization: ApiKey <key>` or similar) | `backend/api/api_key_manager.py`, `/api-keys` CRUD + `/api-keys/_whoami`; TB-US-063 completed | `api_key_management.js` modal, opens from admin dropdown | **Surfaced** | N/A (fixes the research-infrastructure-resilience gap I'd previously claimed existed!) | — |
| **Sessions tracking** (active sessions, history, per-user, stats) | `backend/api/session_tracker.py`, `/sessions/*` endpoints | Query History tab + via user modal | **Surfaced** | N/A | — |
| **Query routes + persisted RAG prompt** (regex-pattern route augmentation at RAG query time) | `/settings/query-routes`, `/settings/rag-prompt`, AppSettings module | **Dormant or partial** — settings endpoints exist, UI exposure unclear | **Partial** (needs verification) | Post-launch | **Minor-to-moderate** |

## 3. Prioritized resurface roadmap for US-005

### Tier 1 — unblocks an honest US-005 pitch

| # | Capability | Follow-up story | Effort |
|---|---|---|---|
| 1 | Experiments UI (list, create, run, view results, archive) | TB-US-070 (already drafted, Proposed) | Moderate |
| 2 | Per-component version lifecycle UI (release / promote / deprecate buttons for prompts, RAG, adapters, routes, harnesses) | **TB-US-NNN (to draft)** | Moderate |
| 3 | Spreadsheet calculator surface (a user-visible way to see this feature exists; could be as simple as a doc / tooltip / tab) | **TB-US-NNN (to draft)** | Minor |

**Why these three**: without the Experiments UI the Sweet Spot methodology is invisible (reduces pitch to "we trained an adapter," not "we ran a disciplined research campaign"). Without version-lifecycle UI operators can't manage their own components post-training. Spreadsheet calculator surface is the smallest "and we also do structured-data math" demo flag.

### Tier 2 — post-US-005

- **Methodology-UI** (TB-US-084 Backlog) — cohorts, pre-registration forms, trial pages, noise-envelope widgets
- **Prompt classification** (TB-US-023 Proposed) — net-new backend work; whole OT arc (TB-US-022 through TB-US-030) if operator wants the full four-handler architecture
- **Explicit-seed harness runner** — reproducibility improvement; not launch-critical but helpful for any future publication

### Tier 3 — backlog / scoped out

- **Spreadsheet formula extraction** (narrow use case; operator should confirm whether stalite's extraction is really needed in TB)
- **Advanced query routes UI** (works via API today; UI could wait)

## 4. Backend gaps that are net-new work (not resurface)

Only one confirmed:

- **Prompt classification** (zero grep matches across backend/ and static/)

Everything else the operator listed as a stalite capability (RAG, multi-LLM, multi-DB, external-LLM API plugins, document processing, spreadsheet calculator) is already present in TB's backend — it's a UI-exposure question, not a port question.

## 5. Open design questions

1. **Spreadsheet formula EXTRACTION** — does stalite's version parse an arbitrary xlsx and auto-discover formulas, or is it closer to TB's current invocation pattern? **Operator decision needed** before allocating effort.
2. **Version-lifecycle UI shape** — should release/promote live on each component's individual page/modal, or in a unified "promotion workflow" view that shows all five component types at once? Either direction is defensible; this is a UX call.
3. **Experiments UI scope** — TB-US-070 Proposed draft is from Oct 2026. Does it match the methodology we developed during TB-US-075-082 (cohorts, multi-seed, noise-envelope awareness), or does it need re-scoping with TB-US-084's methodology-UI findings? Overlap is significant; the two stories should cross-reference before either fires.
4. **PowerSearch feature pitch** — does the US-005 launch pitch lead with PowerSearch (multi-LLM comparison) or with the trained-adapter story? Different audience framing; probably both, but ordering matters.
5. **API-key UI / docs for external automation users** — the capability is complete (TB-US-063) but is it documented for ML researchers who'd use TB from scripts? May need a short "programmatic access" doc page.

## 6. What this audit does NOT cover

- Individual code review of each module (surface presence + purpose only).
- Pixel work or mockups — audit identifies what to resurface; implementation stories handle how.
- Stalite-specific implementation details (operator confirmed stalite is proprietary reference, not a copy target).
- Front-end tooling / build-system changes.

## 7. Correction to a prior claim in TB-US-083

The system-architecture doc (TB-US-083, committed `4ba47e3`) states
in §4 Auth model:

> **Known gap**: no API-key mechanism for automation. Research
> scripts currently mint session tokens directly from the backend
> Python module — a hack that inherits the 24h expiry.

**This is wrong.** TB has a complete API-key mechanism
(TB-US-063, closed 2026-10-22) — backend at
`backend/api/api_key_manager.py` + endpoints at `/api-keys/*` +
UI at `static/api_key_management.js` accessed via the admin
dropdown. The 24h token-expiry pain we hit during the research
arc could have been avoided by using an API key. Follow-up
patch to TB-US-083 architecture doc recommended.

## Links

- TB-US-005 (Proposed; held pending this audit) — public v0.1 cut
- TB-US-070 (Proposed) — Experiments UI
- TB-US-084 (Backlog) — Research methodology UI design spike
- TB-US-083 (Completed) — System architecture doc (needs API-key
  correction)
- TB-US-023 (Proposed) — Four-category prompt classifier
- TB-US-022 through TB-US-030 (Queued) — Orthogonal Training arc
- TB-US-063 (Completed) — API keys mechanism
- TB-US-018 + TB-US-042 (Completed) — UI overhaul that left
  some features dormant
