# TrainingBench

**An open workbench for building and measuring AI agents on your own hardware.**

Build an agent out of five swappable components (RAG index, training set,
PEFT adapter, system prompt, query routes), run experiments to measure
what each change actually does to accuracy, and converge on your own
Sweet Spot — all on consumer GPUs, with your own data staying local.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

---

## What is this?

- **Agent-first.** Everything in TrainingBench lives under an **agent**:
  its RAG, its training set, its adapter, its prompt, its experiments.
  Multiple agents in one install.
- **Versioned, promotable components.** Every component has versions
  with a 3-state lifecycle (draft → released → deprecated). Promote a
  version into production (your current "Sweet Spot") with one click;
  swap it out with another to compare.
- **Measurable.** A pluggable eval harness turns "did this change help?"
  into a number. Experiments pin a specific `(prompt, RAG, LLM,
  adapter)` combination and record a measured result.
- **Self-hosted.** Your data, your GPU, your model weights. No cloud
  dependency, no telemetry, no model-API bills.

## Who is it for?

- **AI engineers running agents in production** who want a defensible
  answer to *"is my new adapter actually better than the one it
  replaced?"*
- **Researchers + educators** who want a reproducible platform for
  teaching how retrieval, fine-tuning, and prompt engineering compose.

## See it running

TrainingBench ships with a **math-example agent** out of the box: a
Llama 3.1 8B base, a 500-example GSM8K training set, a small reference
RAG, and a system prompt — all pre-configured. Run three experiments
(bare base → +adapter → +adapter+RAG) to see each stage's measured
accuracy on a 200-question hold-out eval. The code and the measurements
teach the workflow.

See [`docs/math-example/README.md`](docs/math-example/README.md) *(ships
with TB-US-057 Phase C)* for the staged-progression narrative.

## Install

```bash
git clone https://github.com/eversole-learning/trainingbench
cd trainingbench
./install.sh
```

Full walkthrough with prerequisites, GPU vs CPU tracks, first-login
flow, and troubleshooting: **[INSTALL.md](INSTALL.md)**.

**Hardware:** one NVIDIA GPU with ≥16 GB VRAM (RTX 3090 verified).
CPU-only installs (Track B) work for everything except adapter training.

## Documentation

- **[INSTALL.md](INSTALL.md)** — install walkthrough
- **[`docs/design/`](docs/design/)** — architecture + Sweet Spot + agent model
- **[BACKLOG.md](BACKLOG.md)** — in-flight stories + what's shipped
- **[`docs/user-stories/`](docs/user-stories/)** — every story that
  shaped the current state (TrainingBench's development history is
  stored as the stories themselves)

## License

[Apache 2.0](LICENSE). © Eversole Learning, LLC.

## Contribute

TrainingBench's development is story-driven — see
[CONTRIBUTING.md](CONTRIBUTING.md) for how stories work and how to
engage.
