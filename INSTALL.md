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
- **Python**: 3.11 or 3.12 strongly recommended. 3.10 will likely
  work. 3.13 may have wheel-availability issues for `torch` and
  `bitsandbytes` — use 3.11 or 3.12 if you are starting fresh.
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
pip install -r requirements.txt
```

**Heads up — this step is heavy.** `pip install -r requirements.txt`
pulls in `torch`, `transformers`, `bitsandbytes`, `peft`, `langchain`,
`chromadb`, `sentence-transformers`, and their transitive
dependencies. Expect several GB of downloads and 5-15 minutes of
install time on a reasonable network connection.

If you see wheel errors for `torch` or `bitsandbytes`, your Python
version is likely too new (3.13) or your CUDA driver is too old.
Recreate the venv with `python3.11 -m venv venv` or `python3.12 -m
venv venv` and re-run pip.

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

| Variable | What it controls | Sensible first value |
|---|---|---|
| `APP_PORT` | Port the backend listens on | `8000` |
| `WEB_USERNAME` | Default admin username | `admin` |
| `WEB_PASSWORD` | Default admin password | **choose your own** — do not leave as `changeme` |
| `SECRET_KEY` | Cookie/token signing secret | **choose your own** — random 32+ byte string |
| `PASSWORD_SALT` | Password hash salt | **choose your own** — random string per deployment |
| `DEFAULT_ADMIN_EMAIL` | Email recorded on the seeded admin user | **set to your own address** — the `.env.example` placeholder does not route anywhere |
| `LLM_PROVIDER` | RAG generation backend | `peft` if you will train your own adapter; `ollama` for quick start |
| `OLLAMA_MODEL` | Default Ollama model (if used) | `llama3.1:8b` |
| `OLLAMA_BASE_URL` | Where to reach Ollama | `http://localhost:11434` |

The full set of available env vars is documented in `.env.example`
with comments explaining each.

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
in the repo:

- **`users.db`** is created and seeded with a default admin user
  (`WEB_USERNAME` / `WEB_PASSWORD` from your `.env`). A startup line
  is printed reminding you to change the password.
- **`sessions.db`** is created for login/logout session tracking.
- **`app_settings.json`** is created, holding runtime-modifiable
  configuration like `demo_mode` and `active_database`.
- **`chroma_db/`** is created as an empty vector store.
- **`logs/`** is created for query and audit logs.

All of these paths are env-overridable (see `.env.example`). The
defaults put everything inside the project directory so multiple
installs on one machine do not collide.

### Confirm the server is up

Visit `http://localhost:<APP_PORT>` in a browser. You should see the
TrainingBench login page. Log in with the admin credentials from your
`.env`.

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
| `pip install` errors on `torch` or `bitsandbytes` wheels | Python version too new (3.13) or driver too old | Recreate venv with Python 3.11 or 3.12; verify `nvidia-smi` works |
| `nvidia-smi` does not list a GPU | NVIDIA driver not installed correctly | Reinstall the driver; reboot |
| Backend starts but training fails with "CUDA out of memory" | GPU has less than ~16 GB VRAM | Use a smaller `--max-length`, fewer `--max-train-samples`, or pick a smaller base model via `--model` |
| Login page returns 404 in browser | Wrong host/port, or backend not running | Confirm `APP_PORT` matches the port you typed; check terminal for tracebacks |
| Admin login fails | `.env` not loaded, or password mismatch | Confirm `WEB_PASSWORD` in `.env` matches what you type |
| Smoke train hangs at "Loading base model" | First-time HuggingFace download | Wait — it is downloading approximately 16 GB |

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
