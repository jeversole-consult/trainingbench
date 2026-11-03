#!/usr/bin/env python3
"""TB-US-081 Trial #7 Phase 3: multi-seed replicate (Candidate D).

Creates 6 new experiments (3 per adapter: v7 and v8) pinned to the
holdout harness (v5). Each experiment is one stochastic draw via
TB's existing `do_sample=True, temperature=0.7` + no explicit seed.
Combined with existing E21 (v7) and E24 (v8), we get 4 datapoints
per adapter.

Runs sequentially (~45 min each × 6 = ~4.5h total).
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


def create_experiment(label: str, adapter_v: int) -> int:
    body = {
        "agent_id": AGENT_ID,
        "label": label,
        "harness_version_id": HARNESS_HOLDOUT,
        "system_prompt_version_id": PROMPT_V,
        "llm_identifier": LLM,
        "adapter_version_id": adapter_v,
    }
    row = api("/experiments", body)
    eid = row["experiment_id"]
    print(f"  Created E{eid} '{label}' (adapter v{adapter_v})")
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
    pct = f"{v*100:.1f}%" if isinstance(v, (int, float)) else "?"
    return f"{k}/{n} = {pct}"


def main() -> None:
    # 3 new per adapter, alternating v7 and v8 so an early fail
    # surfaces across both arms rather than only on arm 2
    runs = [
        ("tb-us-081-trial7-eholdout-v7-replicate-1", 7),
        ("tb-us-081-trial7-eholdout-v8-replicate-1", 8),
        ("tb-us-081-trial7-eholdout-v7-replicate-2", 7),
        ("tb-us-081-trial7-eholdout-v8-replicate-2", 8),
        ("tb-us-081-trial7-eholdout-v7-replicate-3", 7),
        ("tb-us-081-trial7-eholdout-v8-replicate-3", 8),
    ]

    results = []
    for label, adapter_v in runs:
        print(f"\n=== {label} ===")
        eid = create_experiment(label, adapter_v)
        row = run_experiment_and_wait(eid)
        summary = summarize_result(row)
        print(f"  E{eid} final: {summary}")
        results.append((eid, label, adapter_v, summary, row.get("state")))

    print()
    print("=" * 70)
    print("TB-US-081 Trial #7 multi-seed replicate summary")
    print("=" * 70)
    for eid, label, adapter_v, summary, state in results:
        print(f"  E{eid:>3} [{state:>9}]  v{adapter_v}  {summary:>22}  {label}")
    print()
    print("Baseline draws from prior trials (for completeness):")
    print("  E21  [completed]  v7  89/200 = 44.5%  (Trial #5 original)")
    print("  E24  [completed]  v8  85/200 = 42.5%  (Trial #6 original)")


if __name__ == "__main__":
    main()
