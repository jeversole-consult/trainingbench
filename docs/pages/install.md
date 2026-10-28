---
title: Install
description: Full TrainingBench install walkthrough — prerequisites, GPU vs CPU tracks, first-login flow, troubleshooting.
---

# Install

Full install reference. For a shorter 10-minute version, see
[Getting Started]({{ '/getting-started.html' | relative_url }}).

The authoritative install walkthrough is in the repo at
[`INSTALL.md`](https://github.com/eversole-learning/trainingbench/blob/main/INSTALL.md).
This page summarizes the key steps + decisions; refer to the repo
file for the complete, version-current reference.

## Prerequisites summary

**Supported:**

- **OS:** Linux. Debian/Ubuntu families documented.
- **Python:** 3.11, 3.12, or 3.13
- **GPU (Track A):** NVIDIA with ≥16 GB VRAM. RTX 3090 verified.
- **CUDA:** 12.x via PyTorch's bundled runtime (no system CUDA
  toolkit required)
- **Disk:** 30 GB free (install + base model), 50 GB+ for active
  development
- **RAM:** 32 GB comfortable minimum

**Not supported in v0.1:**

- Windows / macOS hosts
- AMD / Intel GPUs
- Multi-GPU configurations
- Containerized deployments

## Track A vs Track B

- **Track A — GPU-equipped.** Full workflow: adapter training,
  experiments, measurement. Required for the staged-progression
  demonstration's Stage 2.
- **Track B — CPU-only.** Everything except adapter training.
  Useful for exploring the agent model + measurement workflow
  without GPU hardware. Set `LLM_PROVIDER=ollama` and run against
  a locally-installed Ollama server.

## Install steps

1. **Clone + Python venv:**
   ```bash
   git clone https://github.com/eversole-learning/trainingbench
   cd trainingbench
   python3.11 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **CUDA-matched torch** (Track A only — see repo INSTALL.md
   Step 3a for details):
   ```bash
   pip install torch --index-url https://download.pytorch.org/whl/cu128
   ```

3. **Configure `.env`:** copy from `.env.example`; at minimum set
   `DEFAULT_ADMIN_EMAIL`. Everything cryptographic (admin password,
   SECRET_KEY, PASSWORD_SALT) auto-generates on first boot.

4. **Start the backend:**
   ```bash
   python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000
   ```

5. **First login:** `http://localhost:8000`, auth with
   `DEFAULT_ADMIN_USERNAME` + the auto-generated password from the
   stdout banner (or `cat logs/first-run-admin.txt`). Forced
   password change on first login.

## First-boot side effects

On first boot, TB creates:

- `backend/db/.secrets` — auto-generated SECRET_KEY + PASSWORD_SALT
  (chmod 600, gitignored)
- `backend/db/trainingbench.db` — agents + versioning tables +
  seeded `default` agent
- `users.db` — seeded admin user; forced password change on first
  login
- `logs/first-run-admin.txt` — admin credentials file (chmod 600;
  auto-deleted on first password change)
- **Shipped math-example agent** — auto-seeded with training set
  v1, RAG v1, prompt v1, harness v1, and three draft experiments.
  Set `TB_SKIP_FIRST_RUN_SEED=1` to disable.

## First-login tour

Once in, you should see:

- **Top bar:** 🤖 Agent chip showing current agent
- **Chat tab:** 👋 welcome banner with 3 cards (if math-example
  seeded)
- **Hamburger drawer:** nav + agent selector at top + ⚙️ Admin
  group at bottom (super-only)

## Troubleshooting (common issues)

- **`pip install` wheel errors** → use Python 3.11+, recreate venv
- **`torch.cuda.is_available() == False`** → CUDA driver / torch
  version mismatch; see INSTALL.md Step 3a
- **Lost admin password** → `cat logs/first-run-admin.txt` (if first
  change hasn't happened); nuclear option: stop service, `rm users.db`,
  restart
- **Launch endpoint returns 409** → another training run active;
  cancel it first (one-run-at-a-time by design per TB-US-064)
- **math-example not visible in drawer** → check startup log for
  `[seeder] {seeded: True...}`; if `seeded: False, reason: "missing
  artifacts"`, verify `rag-seeds/math-example-v1/`, `training-sets/
  math-example-v1.jsonl`, `backend/harnesses/data/math_eval_200.jsonl`
  all exist

Full troubleshooting table: [INSTALL.md](https://github.com/eversole-learning/trainingbench/blob/main/INSTALL.md#troubleshooting).

## Operational notes

- **One training run at a time.** The design decision in TB-US-064 is
  a hard single-slot queue — launching a second run while one is
  active returns `409 Conflict`.
- **Don't restart TB during training.** Documented constraint. TB
  startup reconciliation flips orphaned `running` rows to `failed`
  with a note.
- **Auto-reap.** Zombie subprocesses are auto-reaped via
  `SIGCHLD → SIG_IGN` (TB-US-065 fix). Not a correctness issue; just
  noted for anyone instrumenting process management elsewhere.

## systemd deployment

For running TB as a system service: see
[INSTALL.md § Optional: run TrainingBench as a systemd service](https://github.com/eversole-learning/trainingbench/blob/main/INSTALL.md).

## Next steps

- **[Getting Started]({{ '/getting-started.html' | relative_url }})** — quick 10-min walkthrough
- **[Concepts]({{ '/concepts.html' | relative_url }})** — vocabulary + architecture
- **[Staged Progression]({{ '/staged-progression.html' | relative_url }})** — math-example
  demonstration
