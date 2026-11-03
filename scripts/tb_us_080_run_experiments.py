#!/usr/bin/env python3
"""TB-US-080 Trial #6 Phase 3: run two measurement experiments.

Prerequisites:
- Adapter v8 trained + released + promoted (via run #14 completing)
- Service restarted after training (free VRAM for inference)

Two experiments (reuses E22 from Trial #5 as the bare-Instruct holdout
control — no need to re-measure):
  1. E_in_v8:      adapter v8 + harness v4 (baseline-test) + Instruct
  2. E_holdout_v8: adapter v8 + harness v5 (holdout) + Instruct

Runs are sequential (one experiment at a time; inference holds the
model). Harness runner handles inference in a background task. Poll
until each transitions to 'completed' or 'archived' (= failed).
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
import urllib.error

API = "http://localhost:8002"
TOK = open("/tmp/tb_token.txt").read().strip()
AGENT_ID = 3
PROMPT_V = 3
LLM = "meta-llama/Meta-Llama-3.1-8B-Instruct"
HARNESS_BASELINE = 4
HARNESS_HOLDOUT = 5


def api(path: str, body: dict | None = None, method: str = "POST") -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TOK}",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} on {method} {path}: {e.read().decode()[:600]}")


def resolve_adapter_v8() -> int:
    import sqlite3
    with sqlite3.connect("backend/db/trainingbench.db") as c:
        c.row_factory = sqlite3.Row
        r = c.execute(
            "SELECT version_id, state, files_path FROM adapter_versions "
            "WHERE agent_id=? AND training_set_version_id=? "
            "ORDER BY version_id DESC LIMIT 1",
            (AGENT_ID, 8),
        ).fetchone()
        if not r:
            sys.exit("No adapter_versions row with training_set_version_id=8 found")
        print(f"Found adapter v{r['version_id']} ({r['state']}) at {r['files_path']}")
        return r["version_id"]


def create_experiment(label: str, harness_v: int, adapter_v: int | None) -> int:
    body = {
        "agent_id": AGENT_ID,
        "label": label,
        "harness_version_id": harness_v,
        "system_prompt_version_id": PROMPT_V,
        "llm_identifier": LLM,
        "adapter_version_id": adapter_v,
    }
    row = api("/experiments", body)
    eid = row["experiment_id"]
    print(f"  Created E{eid} '{label}' (adapter={adapter_v}, harness=v{harness_v})")
    return eid


def run_experiment_and_wait(eid: int, timeout_s: int = 5400) -> dict:
    print(f"  Launching E{eid}...")
    api(f"/experiments/{eid}/run", method="POST")
    start = time.time()
    last_state = "running"
    while True:
        row = api(f"/experiments/{eid}", method="GET")
        state = row.get("state", "unknown")
        if state != last_state:
            print(f"    E{eid} state: {state}")
            last_state = state
        if state in ("completed", "archived"):
            return row
        if time.time() - start > timeout_s:
            sys.exit(f"E{eid} timed out after {timeout_s}s (last state: {state})")
        time.sleep(15)


def summarize_result(row: dict) -> str:
    rj = row.get("results_json")
    if isinstance(rj, str):
        try:
            rj = json.loads(rj)
        except Exception:
            return "(no results_json)"
    if not rj:
        return "(no results)"
    n = rj.get("n_samples", "?")
    k = rj.get("correct_count", "?")
    v = rj.get("value", "?")
    try:
        pct = f"{v*100:.1f}%" if isinstance(v, (int, float)) else "?"
    except Exception:
        pct = "?"
    return f"{k}/{n} = {pct}"


def main() -> None:
    adapter_v8 = resolve_adapter_v8()

    experiments = [
        ("tb-us-080-trial6-ein-baseline-test-adapter-v8", HARNESS_BASELINE, adapter_v8),
        ("tb-us-080-trial6-eholdout-adapter-v8",         HARNESS_HOLDOUT,  adapter_v8),
    ]

    results = []
    for label, harness_v, adapter_v in experiments:
        print(f"\n=== {label} ===")
        eid = create_experiment(label, harness_v, adapter_v)
        row = run_experiment_and_wait(eid)
        summary = summarize_result(row)
        print(f"  E{eid} final: {summary}")
        results.append((eid, label, summary, row.get("state")))

    print()
    print("=" * 70)
    print("TB-US-080 Trial #6 measurement summary")
    print("=" * 70)
    for eid, label, summary, state in results:
        print(f"  E{eid:>3} [{state:>9}]  {summary:>22}  {label}")
    print()
    print("Compare vs. bare Instruct holdout (E22, from Trial #5): 86/200 = 43.0%")


if __name__ == "__main__":
    main()
