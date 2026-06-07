---
name: trainingbench
description: Interact with a TrainingBench ML training and RAG platform. Use this skill when the user wants to query the knowledge base, upload or manage documents, check training run status, view system stats, or search the document database. Requires TRAININGBENCH_URL and TRAININGBENCH_TOKEN environment variables.
metadata: {
  "openclaw": {
    "requires": {
      "bins": ["curl", "jq"],
      "env": ["TRAININGBENCH_URL", "TRAININGBENCH_TOKEN"]
    }
  }
}
---

# TrainingBench Skill

## Overview

TrainingBench is an ML training and RAG (Retrieval-Augmented Generation) platform with a REST API. This skill allows you to query its knowledge base, manage documents, and monitor training jobs.

## Configuration

All requests require:
- `TRAININGBENCH_URL` — Base URL for the TrainingBench server, e.g.
  `http://localhost:8000` for a local install or `https://your-host.example`
  for a remote one.
- `TRAININGBENCH_TOKEN` — Session token obtained via login (see Authentication below)

Set these in `~/.openclaw/openclaw.json`:
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

## Authentication

### Login and obtain a session token
```bash
curl -s -X POST "$TRAININGBENCH_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "<username>", "password": "<password>"}' | jq .
```

Response includes `session_token`. Store it as `TRAININGBENCH_TOKEN`.

### Verify current session
```bash
curl -s "$TRAININGBENCH_URL/auth/verify" \
  -H "Authorization: Bearer $TRAININGBENCH_TOKEN" | jq .
```

## Core Workflows

### 1. Query the Knowledge Base (RAG)

Ask a question against the document knowledge base:
```bash
curl -s -X POST "$TRAININGBENCH_URL/query" \
  -H "Authorization: Bearer $TRAININGBENCH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "<user question>", "k": 4}' | jq '{answer: .answer, sources: [.sources[].title]}'
```

- `k` controls how many source documents to retrieve (default: 4)
- Response includes `answer`, `sources`, and `context`

### 2. Search Documents

Search for documents by keyword or semantic similarity:
```bash
curl -s -X POST "$TRAININGBENCH_URL/search" \
  -H "Authorization: Bearer $TRAININGBENCH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "<search term>", "k": 5}' | jq '.[].metadata.source'
```

### 3. List All Documents

```bash
curl -s "$TRAININGBENCH_URL/documents" \
  -H "Authorization: Bearer $TRAININGBENCH_TOKEN" | jq '[.[] | {id: .doc_id, file: .filename, type: .type, folder: .folder}]'
```

### 4. Upload a Document

Upload a file to the knowledge base:
```bash
curl -s -X POST "$TRAININGBENCH_URL/upload" \
  -H "Authorization: Bearer $TRAININGBENCH_TOKEN" \
  -F "file=@/path/to/document.pdf" | jq .
```

Supported formats: PDF, TXT, DOCX, and other text-based files.

### 5. List Folders

```bash
curl -s "$TRAININGBENCH_URL/folders" \
  -H "Authorization: Bearer $TRAININGBENCH_TOKEN" | jq .
```

### 6. System Stats

Get document count, vector store info, and LLM status:
```bash
curl -s "$TRAININGBENCH_URL/stats" | jq .
```

### 7. Available Models

List AI models configured in TrainingBench:
```bash
curl -s "$TRAININGBENCH_URL/models" | jq .
```

### 8. Training Runs

List all training runs and their status:
```bash
curl -s "$TRAININGBENCH_URL/training/runs" \
  -H "Authorization: Bearer $TRAININGBENCH_TOKEN" | jq '[.[] | {id: .id, name: .name, status: .status, model: .base_model}]'
```

Get details for a specific training run:
```bash
curl -s "$TRAININGBENCH_URL/training/runs/<run_id>" \
  -H "Authorization: Bearer $TRAININGBENCH_TOKEN" | jq .
```

Get metrics for a training run:
```bash
curl -s "$TRAININGBENCH_URL/training/runs/<run_id>/metrics" \
  -H "Authorization: Bearer $TRAININGBENCH_TOKEN" | jq .
```

### 9. Training Sets

List available training datasets:
```bash
curl -s "$TRAININGBENCH_URL/training/sets" \
  -H "Authorization: Bearer $TRAININGBENCH_TOKEN" | jq '[.[] | {id: .id, name: .name, status: .status, size: .size}]'
```

### 10. Power Search (External AI)

Query using external AI services (OpenAI, Anthropic, etc.) if configured:
```bash
# First check which services are available
curl -s "$TRAININGBENCH_URL/power-search/services" \
  -H "Authorization: Bearer $TRAININGBENCH_TOKEN" | jq .

# Run a power search
curl -s -X POST "$TRAININGBENCH_URL/power-search" \
  -H "Authorization: Bearer $TRAININGBENCH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "<question>", "service": "<service_name>"}' | jq .
```

## Behavior Rules

- Always check `TRAININGBENCH_TOKEN` is set before making authenticated requests. If missing, prompt the user to log in first.
- When a query returns sources, summarize them clearly and cite the source titles.
- If a `401 Not authenticated` error is received, inform the user their session has expired and offer to log in again.
- For document uploads, confirm the file path exists before attempting the upload.
- When listing training runs, highlight any with `status: running` or `status: failed`.
- Use `jq` to format all responses for readability. If `jq` is unavailable, fall back to raw JSON.
- Never expose the session token in responses to the user.
