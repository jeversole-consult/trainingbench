# TrainingBench — OpenClaw Integration

This directory contains OpenClaw skills and plugins for integrating with the TrainingBench platform.

## Structure

```
openclaw/
└── skills/
    └── trainingbench/
        └── SKILL.md    # OpenClaw skill for TrainingBench API
```

## Installation

1. Copy or symlink the skill into OpenClaw's skills directory:
   ```bash
   ln -s /path/to/trainingbench/openclaw/skills/trainingbench \
         ~/.openclaw/workspace/skills/trainingbench
   ```

2. Configure credentials in `~/.openclaw/openclaw.json`:
   ```json
   {
     "skills": {
       "entries": {
         "trainingbench": {
           "enabled": true,
           "env": {
             "TRAININGBENCH_URL": "http://localhost:8000",
             "TRAININGBENCH_TOKEN": "<your-session-token>"
           }
         }
       }
     }
   }
   ```

   Replace `TRAININGBENCH_URL` with wherever your TrainingBench server
   is reachable — `http://localhost:8000` for a local install,
   `https://your-host.example` for a remote one.

3. Get your session token by logging in (replace the URL with your
   own and `admin` / `<password>` with credentials that exist in your
   deployment):
   ```bash
   curl -s -X POST http://localhost:8000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "<password>"}' | jq -r .session_token
   ```

## What the Skill Can Do

| Capability | Description |
|---|---|
| RAG Query | Ask questions against the document knowledge base |
| Document Upload | Add new documents to the knowledge base |
| Document Search | Search documents by keyword or semantic similarity |
| Training Runs | Monitor ML training job status and metrics |
| Training Sets | List and manage training datasets |
| System Stats | View platform health and usage |
| Power Search | Query via external AI services (OpenAI, Anthropic, etc.) |
