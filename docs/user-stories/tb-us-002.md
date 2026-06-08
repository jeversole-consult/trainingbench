# TB-US-002: First-release install instructions for TrainingBench

**Status**: Proposed
**Created**: 2026-06-06
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story


As a new user setting up TrainingBench for a new project,
I need install instructions that take me from `git clone`
to a running, smoke-verified TrainingBench install
on a bare metal or virtual hardware/OS — so that I can use
the platform to build and train a chat based AI agent ready
for deployment.

## Background

TrainingBench currently has no documented install instructions. The
`requirements.txt` lists Python dependencies, but the README does not
walk through venv creation, system binaries (CUDA, tesseract, poppler),
Python version selection, or how to verify the install actually works.
A contributor or a downstream operator cloning the repo today needs 
detailed install instructions to navigate the installation of the many
tools that a TrainingBench installation requires. Installation is a
substantial undertaking. 

Installs are **per-project**. A user managing multiple projects
creates a separate TrainingBench install per project — a new directory
for each, each with its own venv, runtime artifacts, and configuration.
This story documents that per-project install workflow. It does not
cover building the agent itself; that is the work the install enables,
and will be addressed in one or more future stories.

Successful installation satisfies the following:

1. **The first install user** — needs the install to work on a well
   defined machine/OS so they can use the application to build agents.
   
2. **An OSS contributor evaluating the project** — needs the install
   instructions to be honest about prerequisites, dependencies, and
   what's been tested. Generic, with clear "tested on / not tested on"
   boundaries.

## Requirements

- [ ] R1: An install document lives in the repo at a discoverable
      location (`INSTALL.md` at repo root, or a clearly-named section
      in `README.md`). The document is in flowable Markdown and
      readable without rendering.
- [ ] R2: The document specifies the **Python version range** that is
      tested. The current `requirements.txt` is the source of truth
      for direct deps; the document explains how to interpret it and
      what indirect dependencies pip pulls.
- [ ] R3: The document specifies the **system binaries** TrainingBench
      depends on (CUDA + driver for PEFT, tesseract for OCR fallback,
      poppler/`pdftoppm` for PDF rasterisation) with a one-line
      install hint for at least one mainstream Linux distro (Debian/
      Ubuntu via `apt`).
- [ ] R4: The document walks through **venv creation and dependency
      install** as a copy-pasteable sequence. The reader should be
      able to follow it line by line without prior knowledge of
      Python tooling.
- [ ] R5: The document specifies how to **verify the install** —
      starting the backend and seeing it serve, then running the
      smoke-train invocation from TB-US-001. Verification should
      double as the "did it work" check for that story's AC3 and AC4.
- [ ] R6: The document calls out the **first-boot side effects** the
      user will see: default admin user creation (and the env vars
      that override the credentials), the `app_settings.json` getting
      seeded, and the initial empty ChromaDB directory.
- [ ] R7: The document says clearly **what hardware was tested** and
      **what hasn't been**. Honest scope statement, not aspirational.

## Acceptance Criteria

- [ ] AC1: A new user who has Linux, an internet connection, sudo,
      and a supported NVIDIA GPU can follow the install document end
      to end and end up with `uvicorn` serving the TrainingBench
      backend on a configured port, returning the login page in a
      browser.
- [ ] AC2: After the install path is followed, the smoke-train
      invocation from TB-US-001
      (`python training/math/train.py --max-train-samples 50
      --max-eval-samples 25 --epochs 1 --run-name smoke-test`)
      completes successfully and produces a tracker log under the
      install directory.
- [ ] AC3: The install path was actually executed on at least one
      real or virtual machine (not just dry-read), and the user's
      notes on what surprised them are folded back into the doc as
      either fixes or "known issue" callouts.
- [ ] AC4: A `--help` invocation of the major entry points (the
      training script, the uvicorn startup) is included in the install
      doc so the user can confirm their venv is wired correctly
      without committing to a full smoke run.
- [ ] AC5: The install doc names a minimum disk footprint estimate
      (rough order of magnitude — the torch / transformers stack and
      a base Llama 3.1 8B checkpoint is not small) so the user
      sizes their environment realistically.

## Design Notes

- Keep the document **prescriptive**, not encyclopedic. There is one
  blessed path; alternatives can be footnotes or links.
- The supported environment for v0.1 is **single-user Linux with one
  NVIDIA GPU**. Multi-GPU, Windows, macOS, and Docker installation are
  explicitly out of scope. Document the boundary; do not pretend.
- Use the existing `.env.example` (or add one if missing) as the
  config surface the doc points at. Configuration is env-var-driven
  per project policy; the doc should make this obvious.
- Where the user has to make a choice (port number, default admin
  password, LLM_PROVIDER), call it out at the point in the sequence
  where the choice has to be made — not in a separate config
  appendix.
- The verification step is also the smoke verification for
  TB-US-001's outstanding ACs. Land both in the same commit chain.

## Out of Scope

This story stops at "the platform is installed and verified, the user
is ready to build an agent." Everything past that point is downstream
work — likely more than one future story.

- **Agent construction itself.** Training adapters, loading the RAG
  with content, configuring the chat UI for a specific use case, and
  any other work the user does after the install is complete is
  downstream of this story.
- **Operational agent deployment.** Cutting a trained agent over to a
  stable serving configuration, exposing it to end users, and running
  it as a managed service are separate future stories.
- **Automated scaffolding / project-init tooling.** The per-project
  install in this story is the *manual* workflow ("make a directory,
  clone, install, configure"). Tooling that automates project
  creation (e.g. a `trainingbench init` command) belongs in a later
  story.
- **Windows or macOS install.** The test target is Linux. Other
  platforms may work but won't be claimed as supported in v0.1.
- **Docker / container packaging.** Useful but not required for v0.1.
  Belongs in a later story once the bare-metal install is stable.
- **Multi-GPU / distributed training.** Single-GPU QLoRA is the v0.1
  target.
- **Automated CI for the install path.** Manual verification is
  acceptable for v0.1; an automated install smoke test belongs in a
  later story.
- **Password security architecture.** The default admin password is
  noted in the install doc but the broader security work (per-user
  random salts, bcrypt/argon2) is tracked separately as TB-US-003.

## Related

- TB-US-001 — the smoke-train invocation used to verify the install
- `requirements.txt` — the authoritative list of Python deps
- `trainingbench.service` — the systemd template (referenced from the
  install doc as an optional production-launch step)
- `docs/user-stories/template.md` — the story format
- User story methodology: `BACKLOG.md`
