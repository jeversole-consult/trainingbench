---
title: Home
description: TrainingBench — measure what training does to your LLM.
---

<div class="hero">
    <h1>Measure what training does to your LLM.</h1>
    <p class="pitch">
        Open-source workbench for AI agents. Build an agent from
        five swappable components, run experiments to measure what
        each change does to accuracy, and converge on your own Sweet
        Spot — all on consumer GPUs with your data staying local.
    </p>
    <div class="cta-row">
        <a href="{{ '/install.html' | relative_url }}" class="cta primary">Install TrainingBench →</a>
        <a href="{{ '/staged-progression.html' | relative_url }}" class="cta secondary">See it in action</a>
    </div>
</div>

## What TrainingBench gives you

<div class="feature-grid">
    <div class="feature-card">
        <h3>📊 Staged progression</h3>
        <p>Measure how retrieval, fine-tuning, and prompt engineering
        each contribute to agent accuracy. The shipped math-example
        agent runs the three-stage demonstration out of the box.</p>
        <p><a href="{{ '/staged-progression.html' | relative_url }}">See the three stages →</a></p>
    </div>
    <div class="feature-card">
        <h3>🤖 Explore an agent</h3>
        <p>Each agent owns its own versioned RAG, training set,
        adapter, prompt, and query routes. Promote a new version
        in; compare it to what was there before.</p>
        <p><a href="{{ '/concepts.html' | relative_url }}">Agent model →</a></p>
    </div>
    <div class="feature-card">
        <h3>🚀 Start your own</h3>
        <p>Create a new agent for your domain. Ingest documents.
        Train an adapter. Measure. Iterate. Your data, your GPU,
        your model weights.</p>
        <p><a href="{{ '/getting-started.html' | relative_url }}">Getting started →</a></p>
    </div>
</div>

## Who it's for

- **AI engineers running agents in production** who want a defensible
  answer to *"is my new adapter actually better than the one it
  replaced?"*
- **Researchers + educators** who want a reproducible platform for
  teaching how retrieval, fine-tuning, and prompt engineering compose.
- **Operators + hobbyists** who want to run an LLM-powered knowledge
  system locally without recurring cloud bills.

## What's inside

TrainingBench is a self-hosted FastAPI backend + a web UI that treats
AI agents as **first-class versioned entities**. Each agent is composed
of six component types — RAG index, training set, PEFT adapter, system
prompt, query routes, eval harness — and every component is versioned
with a three-state lifecycle (draft → released → deprecated). An
experiment pins a specific combination of versions, runs it against
the eval harness, and records a measured accuracy. The combination
you promote into production is your current **Sweet Spot**.

The platform ships with the plumbing for all of that + a working
math-example agent that teaches the workflow by demonstration.

## Ready to run?

- **Install:** [full walkthrough]({{ '/install.html' | relative_url }}) covering prerequisites,
  GPU vs CPU-only tracks, first-login flow, and troubleshooting.
- **Try the math-example:** [staged progression]({{ '/staged-progression.html' | relative_url }})
  walks through the three-stage demonstration.
- **Learn the concepts:** [agent model + Sweet Spot vocabulary]({{ '/concepts.html' | relative_url }}).
