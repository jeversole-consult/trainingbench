# Installing TrainingBench

This document walks through installing TrainingBench from scratch on
a Linux machine with an NVIDIA GPU. Following it end-to-end leaves
you with a running TrainingBench backend, ready to be used to build
and train a chat-based AI agent.

TrainingBench installs are **per-project**. Each project you build on
the platform gets its own directory, its own virtual environment, and
its own runtime artifacts. You can have multiple installs on one
machine; they do not interfere with each other.

This guide does **not** cover building an agent (training adapters,
loading the RAG with content, configuring the chat UI for a domain),
nor deploying an agent operationally. Those are downstream of the
install and are tracked as separate stories.

---

## Supported environment

This install path is documented and intended for:

- **OS**: Linux. Debian/Ubuntu families are the documented example;
  other distros are expected to work with package-manager substitutions.
- **Host**: bare metal or virtual machine.
- **GPU**: one NVIDIA GPU with at least **16 GB of VRAM**. RTX 3090
  (24 GB), RTX 4090 (24 GB), and A6000 (48 GB) are known good shapes.
  Llama 3.1 8B (the default base model for the math training pipeline)
  uses approximately 14-16 GB during QLoRA training.
- **CUDA**: an NVIDIA driver compatible with PyTorch's current wheels.
  At the time of v0.1 this means CUDA 12.x with NVIDIA driver 535 or
  newer. PyTorch ships its own CUDA libraries; you do not need a
  separate CUDA toolkit install.
- **Python**: 3.11, 3.12, or 3.13 — all verified against current
  PyPI wheels for `torch` and `bitsandbytes` as of v0.1. 3.10 will
  likely work. Older versions may have wheel-availability gaps.
- **Disk space**: at least **30 GB** free for the install itself
  (Python packages + one base model checkpoint). Plan for **50 GB or
  more** for active development with several adapters and ingested
  documents.
- **System memory**: 32 GB system RAM is the comfortable minimum.

What has **not** been tested as of v0.1:

- Windows or macOS hosts. Either may work; neither is supported.
- AMD or Intel GPUs. The PEFT/QLoRA paths assume NVIDIA CUDA.
- Multi-GPU configurations. v0.1 targets a single GPU.
- Containerised deployments (Docker, etc.). v0.1 targets a bare-metal
  install.

This section will be updated with concrete "verified on" entries as
real installs are performed (see "What's verified, what isn't" at the
bottom of this document).

### Track A vs Track B — which path is yours?

Not every TrainingBench install needs a GPU. Two paths:

- **Track A — GPU-equipped install.** You can train adapters locally.
  Full workflow available: ingest documents, train PEFT adapters, run
  experiments comparing (prompt, RAG, LLM, adapter) combinations,
  measure accuracy on your eval harness. **Required for TB-US-057
  Phase B's Stage 2 (adapter) measurement and for any real
  fine-tuning work.**
- **Track B — CPU-only install.** Everything except adapter training
  works. You can run inference against your base model (via Ollama
  or an HTTP LLM provider), load content into RAG indices, create and
  release component versions, run experiments against the harness
  (minus adapter stages). Useful for operators who want to explore
  the agent model and measurement workflow without GPU hardware.

The rest of this doc covers Track A (GPU present). For Track B, skip
the CUDA / NVIDIA sections and set `LLM_PROVIDER=ollama` in your
`.env` after installing an Ollama server with the base model pulled.
Everything else works identically.

---

## Step 1: Install system binaries

TrainingBench depends on system packages that are not installed by
pip. On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install -y \
    python3 python3-venv python3-pip \
    git \
    tesseract-ocr \
    poppler-utils \
    build-essential
```

- `python3-venv` is needed for creating isolated environments.
- `tesseract-ocr` provides the `tesseract` binary used by the OCR
  fallback for scanned PDFs.
- `poppler-utils` provides `pdftoppm` and `pdftotext` used during PDF
  processing.
- `build-essential` is needed by some Python packages (notably
  `bitsandbytes`) when prebuilt wheels are not available for your
  platform.

### NVIDIA driver

You need the NVIDIA proprietary driver. On Ubuntu, the most reliable
path is the distro's metapackage:

```bash
sudo apt install -y nvidia-driver-535
sudo reboot
```

After the reboot, verify the driver and the GPU are visible:

```bash
nvidia-smi
```

You should see your GPU listed with a recent driver version. If
`nvidia-smi` errors out, fix the driver before continuing — the rest
of this guide assumes a working CUDA environment.

---

## Step 2: Clone TrainingBench into a project directory

TrainingBench installs are per-project. Pick a directory name that
reflects the project you are building, not just "trainingbench":

```bash
# Replace my-project with whatever name fits your project
git clone https://github.com/<your-org>/trainingbench.git ~/projects/my-project
cd ~/projects/my-project
```

You will run the rest of this guide from inside `~/projects/my-project`
(or whichever directory you picked).

---

## Step 3: Create a virtualenv and install Python dependencies

Inside the project directory:

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

### Step 3a: Match torch to your CUDA driver — important

The default `torch` wheel on PyPI is currently built against CUDA
13.x. If your NVIDIA driver's reported max CUDA version is **12.x**
(see the "CUDA Version" line in `nvidia-smi` output), the default
wheel installs successfully but silently disables GPU support —
`torch.cuda.is_available()` returns False and PEFT training cannot
use the GPU. To avoid this, install `torch` from PyTorch's CUDA
12.8 wheel index *before* running the full requirements install:

```bash
# Run this only if `nvidia-smi` shows CUDA 12.x
pip install torch --index-url https://download.pytorch.org/whl/cu128
```

If `nvidia-smi` shows CUDA 13.x, skip this step — the default torch
wheel will work.

### Step 3b: Install the remaining dependencies

```bash
pip install -r requirements.txt
```

**Heads up — this step is heavy.** It pulls in `transformers`,
`bitsandbytes`, `peft`, `langchain`, `chromadb`,
`sentence-transformers`, `tensorboard`, and their transitive
dependencies. Expect several GB of downloads and 5-15 minutes of
install time on a reasonable network connection.

If `pip install` errors on `torch` or `bitsandbytes` wheels, your
Python is likely older than 3.10 — upgrade to 3.11 / 3.12 / 3.13
and recreate the venv.

### What's in `requirements.txt` vs what gets installed transitively

`requirements.txt` lists TrainingBench's direct dependencies — the
packages the code in the repo imports directly. Each of those pulls
its own dependencies in turn, which is why the actual `pip install`
brings in dozens of packages. The versions in the file are floors
(minimums TrainingBench has been developed against), not pins.

---

## Step 4: Configure the environment

TrainingBench reads configuration from environment variables. Copy
the example file and edit it to match your environment:

```bash
cp .env.example .env
```

Open `.env` in an editor. At minimum, decide on the following:

| Variable | What it controls | Default behavior |
|---|---|---|
| `APP_PORT` | Port the backend listens on | `8000` |
| `DEFAULT_ADMIN_USERNAME` | Username of the seeded super-admin | `admin` |
| `DEFAULT_ADMIN_PASSWORD` | Password of the seeded super-admin | **If unset: auto-generated random 24-char password on first boot, printed to stdout + written to `logs/first-run-admin.txt` (chmod 600). You'll be forced to change it on first login.** |
| `SECRET_KEY` | Cookie/token signing secret | **If unset: auto-generated to `backend/db/.secrets` (chmod 600, gitignored) on first boot.** Only override if you need to pin the value for multi-replica or CI. |
| `PASSWORD_SALT` | Password hash salt | **If unset: auto-generated to `backend/db/.secrets`.** Same note as SECRET_KEY. |
| `DEFAULT_ADMIN_EMAIL` | Email recorded on the seeded admin user | **set to your own address** — the `.env.example` placeholder does not route anywhere |
| `LLM_PROVIDER` | RAG generation backend | `peft` if you will train your own adapter; `ollama` for quick start |
| `OLLAMA_MODEL` | Default Ollama model (if used) | `llama3.1:8b` |
| `OLLAMA_BASE_URL` | Where to reach Ollama | `http://localhost:11434` |
| `SITE_PASSPHRASE` | Optional pre-login gate passphrase | Unset = no gate; set to require passphrase before login page is reachable |
| `TB_SKIP_FIRST_RUN_SEED` | Set to `1` to skip the math-example seeder | Unset = seeder runs on fresh installs |

The full set of available env vars is documented in `.env.example`
with comments explaining each.

**TL;DR:** on a fresh install with just `DEFAULT_ADMIN_EMAIL` set, TB
auto-generates everything cryptographic (admin password, SECRET_KEY,
PASSWORD_SALT) on first boot. You don't have to set them unless you
want to pin the values.

### About the LLM backend choice

TrainingBench can use either a PEFT-trained adapter (your own
fine-tuned model) or Ollama (a separately-installed local model
server) for RAG generation. For a first install with no trained
adapter yet, set `LLM_PROVIDER=ollama` and make sure Ollama is
running with the configured model pulled:

```bash
# Only needed if you set LLM_PROVIDER=ollama
ollama pull llama3.1:8b
```

If you set `LLM_PROVIDER=peft` without a trained adapter, the backend
will start but RAG queries return a "LLM not configured" fallback
message. Training your first adapter is a separate task — see
TB-US-001 and the training pipeline at `training/math/`.

---

## Step 5: Start the backend

From the project directory, with the venv active:

```bash
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port $APP_PORT
```

### First-boot side effects

On the first boot, the server creates side-effect state that was not
in the repo. Watch stdout — several startup banners confirm each step:

- **`backend/db/.secrets`** (chmod 600, gitignored) with auto-generated
  SECRET_KEY and PASSWORD_SALT. Log line: `[secrets] generated and
  wrote .../backend/db/.secrets`
- **`backend/db/trainingbench.db`** with the agents + versioning
  tables + seeded `default` agent. Log line: `[schema] {...
  seeded_default_agent: True}`
- **`users.db`** seeded with a super-admin. If you did NOT set
  `DEFAULT_ADMIN_PASSWORD`, you'll see a prominent banner with the
  auto-generated password + instructions. Credentials also written to
  `logs/first-run-admin.txt` (chmod 600) — this file is auto-deleted
  after you change your password.
- **`sessions.db`** for login/logout session tracking
- **`app_settings.json`** for runtime-modifiable configuration
- **Legacy `chroma_db/`** created as an empty vector store (legacy
  singleton; new agents get their own versioned collections)
- **`logs/`** for query and audit logs
- **math-example agent + 3 draft experiments** auto-seeded if the
  `rag-seeds/`, `training-sets/`, and `backend/harnesses/data/`
  artifacts are present. Log line: `[seeder] {... seeded: True,
  agent_id: N, ...}`. Set `TB_SKIP_FIRST_RUN_SEED=1` to disable.

All DB paths are env-overridable (see `.env.example`). The defaults
put everything inside the project directory so multiple installs on
one machine do not collide.

### Confirm the server is up

Visit `http://localhost:<APP_PORT>` in a browser. You should see the
TrainingBench login page.

**If you set `DEFAULT_ADMIN_PASSWORD` in `.env`:** log in with those
credentials. You're immediately in the Chat tab.

**If you did NOT set it (auto-generated path):**

1. Get the auto-generated password from either the stdout banner or
   `cat logs/first-run-admin.txt`
2. Log in with `DEFAULT_ADMIN_USERNAME` + that password
3. You'll be forced to the password-change page — set a new password
   (minimum 10 characters). The `logs/first-run-admin.txt` file is
   deleted automatically on successful change.
4. You land in the Chat tab with the welcome banner visible.

### First-login tour

What you should see once you're in:

- **Top bar:** 🤖 Agent chip showing current agent (`default` by
  default; switch to `math-example` via the drawer selector)
- **Chat tab:** 👋 welcome banner with three cards (if math-example
  seeded) or "Create an agent" (if not)
- **Hamburger drawer:** nav for Chat / Upload / Documents / Databases
  / Training Sets / Training Runs + agent selector at top + ADMIN
  group at bottom (super-only; Users + API Keys inside)

---

## Step 6: Verify the install end-to-end

The previous step proved the backend can start. This step proves the
training pipeline is wired correctly all the way through to your GPU.

### Confirm the CLI entry points are wired

In a fresh terminal (with the venv activated), run the `--help`
commands for the two major entry points:

```bash
# Training pipeline CLI
python training/math/train.py --help

# Backend (uvicorn's own help)
python -m uvicorn --help
```

Both commands should print help text without errors. If either fails
with `ImportError`, the venv is not activated, or `pip install` did
not complete cleanly.

### Download the GSM8K dataset

The math training script trains against the GSM8K math word-problem
dataset. Download it once into the expected location:

```bash
python scripts/download_gsm8k.py
```

### Run the smoke training pass

This is a tiny training run — just enough to confirm the GPU loads
the base model and the training loop ticks over. It is **not** a real
fine-tune:

```bash
python training/math/train.py \
    --max-train-samples 50 \
    --max-eval-samples 25 \
    --epochs 1 \
    --run-name smoke-test
```

What you should see:

- The base model (Llama 3.1 8B by default) downloads from HuggingFace
  on the first run. This is approximately 16 GB and may take a while.
- `nvidia-smi` in another terminal shows GPU memory in use.
- Training progress prints every `--logging-steps` (default 50).
- The run completes and prints a "Next steps" message.
- A tracker log appears in the configured log directory.

If the smoke run completes, the install is verified. Your environment
can train PEFT adapters on this hardware.

---

## Optional: run TrainingBench as a systemd service

For ongoing use you may want TrainingBench to start on boot rather
than under an interactive shell. A `systemd` template lives in the
repo at `trainingbench.service`. Copy it, edit the placeholders for
your user and install path, then enable it:

```bash
sudo cp trainingbench.service /etc/systemd/system/trainingbench.service
sudo $EDITOR /etc/systemd/system/trainingbench.service   # fill placeholders
sudo systemctl daemon-reload
sudo systemctl enable --now trainingbench
sudo systemctl status trainingbench
```

This is optional. Nothing else in TrainingBench depends on running
under systemd.

---

## Troubleshooting

| Symptom | Likely cause | What to try |
|---|---|---|
| `pip install` errors on `torch` or `bitsandbytes` wheels | Python older than 3.10, or no matching wheel for your platform | Use Python 3.11/3.12/3.13 and recreate the venv |
| `torch.cuda.is_available()` is False after install | Default cu130 torch wheel pulled, but driver only supports CUDA 12.x | See Step 3a — reinstall torch from the cu128 index |
| `nvidia-smi` does not list a GPU | NVIDIA driver not installed correctly | Reinstall the driver; reboot |
| Backend starts but training fails with "CUDA out of memory" | GPU has less than ~16 GB VRAM, or other processes are holding VRAM | Use a smaller `--max-length`, fewer `--max-train-samples`, pick a smaller base model via `--model`, or stop other GPU processes (`nvidia-smi --query-compute-apps=pid,used_memory --format=csv`) |
| Trainer fails with "TensorBoardCallback requires tensorboard to be installed" | HF Trainer default includes a TensorBoard callback | Already handled: `train.py` sets `report_to="none"`. If you hit this with a fresh branch, either upgrade or install `pip install tensorboard` |
| Login page returns 404 in browser | Wrong host/port, or backend not running | Confirm `APP_PORT` matches the port you typed; check terminal for tracebacks |
| Admin login fails + no `DEFAULT_ADMIN_PASSWORD` in .env | Auto-generated password: check for it | `cat logs/first-run-admin.txt` (file auto-deleted after first password change) OR scroll back on service stdout for the credentials banner |
| Admin login fails + password set in .env | `.env` not loaded, or password mismatch | Confirm `DEFAULT_ADMIN_PASSWORD` in `.env` matches what you type. (`.env` must be in the project root and the backend must have been started from there.) |
| Lost admin password entirely | `logs/first-run-admin.txt` deleted after first change; no recovery UI yet | Nuclear option: stop service, `rm users.db`, restart — new auto-generated admin, lose other user accounts. Future-proof: back up `users.db` after setting things up |
| Smoke train hangs at "Loading base model" | First-time HuggingFace download | Wait — it is downloading approximately 16 GB |
| Launch endpoint returns 409 Conflict | Another training run is still active | Visit Training Runs page, cancel the active run, retry. One run at a time by design (TB-US-064) |
| Training run shows "failed" immediately with "TB restarted" | Service restarted while this run was active | Expected behavior — TB-US-065 startup reconciliation marks orphaned subprocesses as failed. Launch a new run |
| math-example agent not visible in drawer selector | Seeder didn't run, or operator deleted it | Check startup log for `[seeder] {seeded: True...}`. If `seeded: False, reason: "missing artifacts"`, verify `rag-seeds/math-example-v1/`, `training-sets/math-example-v1.jsonl`, `backend/harnesses/data/math_eval_200.jsonl` all exist |

---

## What's verified, what isn't

As of v0.1, this install path is documented based on TrainingBench's
known dependencies and the architecture decisions in master. It has
**not** yet been executed end-to-end on a specific machine.

The first successful run of this install path on a real machine
should result in this section being updated with:

- The actual OS / kernel / GPU / driver / Python versions used
- Anything in the install that surprised the user
- Any "known issue" callouts that should travel with the doc

If you are the first to run this install all the way through, you are
contributing to v0.1 verification — please open a PR with your
verified-on details and any corrections.
