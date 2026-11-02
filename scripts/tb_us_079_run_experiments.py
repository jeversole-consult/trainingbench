#!/usr/bin/env python3
"""TB-US-079 Phase 3: create + run three measurement experiments.

Prerequisites (verify before running):
- Adapter v7 trained + auto-registered (via run #13 completing)
- Service restarted after training (free VRAM for inference)

Three experiments:
  1. E_in_v7:         adapter v7 + harness v4 (baseline-test) + Instruct
  2. E_holdout_v7:    adapter v7 + harness v5 (holdout) + Instruct
  3. E_bare_holdout:  no adapter + harness v5 (holdout) + Instruct

The third fills the gap discovered during TB-US-079 prep: E19 (TB-US-077)
was mis-labeled as "holdout" when it actually used harness v4
(baseline-test). This gives us the clean apples-to-apples comparison
for H5b against bare Instruct on the actual holdout set.

Runs are sequential (one experiment at a time; inference loads/holds
the model). After each experiment transitions to running, the harness
runner handles inference in a background task. We poll until the
state becomes 'completed' or 'archived' (= failed).
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
import urllib.error
from typing import Any

API = "http://localhost:8002"
TOK = open("/tmp/tb_token.txt").read().strip()
AGENT_ID = 3
PROMPT_V = 3
LLM = "meta-llama/Meta-Llama-3.1-8B-Instruct"
HARNESS_BASELINE = 4   # math_eval_200.jsonl
HARNESS_HOLDOUT = 5    # math_eval_200_holdout.jsonl


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


def resolve_adapter_v7() -> int:
    """Find the most recent adapter_version_id trained from training_set=7."""
    import sqlite3
    with sqlite3.connect("backend/db/trainingbench.db") as c:
        c.row_factory = sqlite3.Row
        r = c.execute(
            "SELECT version_id, state, files_path FROM adapter_versions "
            "WHERE agent_id=? AND training_set_version_id=? AND files_path LIKE 'adapters/math-example/%' "
            "ORDER BY version_id DESC LIMIT 1",
            (AGENT_ID, 7),
        ).fetchone()
        if not r:
            sys.exit("No adapter_versions row with training_set_version_id=7 found")
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


def run_experiment_and_wait(eid: int, timeout_s: int = 3600) -> dict:
    """Transition experiment to running + poll until completed/archived."""
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
    adapter_v7 = resolve_adapter_v7()

    experiments = [
        ("tb-us-079-trial5-ein-baseline-test-adapter-v7", HARNESS_BASELINE, adapter_v7),
        ("tb-us-079-trial5-eholdout-adapter-v7",         HARNESS_HOLDOUT,  adapter_v7),
        ("tb-us-079-bare-instruct-holdout",              HARNESS_HOLDOUT,  None),
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
    print("TB-US-079 Trial #5 measurement summary")
    print("=" * 70)
    for eid, label, summary, state in results:
        print(f"  E{eid:>3} [{state:>9}]  {summary:>22}  {label}")


if __name__ == "__main__":
    main()
