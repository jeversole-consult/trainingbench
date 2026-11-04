#!/usr/bin/env python3
"""TB-US-082 Trial #8 Phase 4: multi-seed holdout runs for adapter v9.

Prerequisites:
- Adapter v9 trained + released + promoted (via run #15 completing)
- Service state OK (model will load fresh for inference)

4 holdout experiments at n=200, each pinned to adapter v9 +
harness v5 (holdout). Multi-seed from the start per the
"GSM8K at n=200 has ~6pt noise envelope" discipline established
in Trial #7.

Plus 1 baseline-test experiment (adapter v9 + harness v4) for
cross-reference with Trials #5/#6.

Pre-flight remints the session token on each endpoint call to
dodge the 24h expiry issue that hit Trial #7 mid-run.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
import urllib.error

API = "http://localhost:8002"
AGENT_ID = 3
PROMPT_V = 3
LLM = "meta-llama/Meta-Llama-3.1-8B-Instruct"
HARNESS_BASELINE = 4
HARNESS_HOLDOUT = 5
ADAPTER_V = 9  # Trial #8 adapter


def mint_token() -> str:
    """Mint a fresh super-user session token via direct backend call."""
    import subprocess
    out = subprocess.run(
        ["venv/bin/python", "-c",
         "import sys, os; sys.path.insert(0, 'backend');"
         "_s, _e = sys.stdout, sys.stderr;"
         "sys.stdout = sys.stderr = open(os.devnull, 'w');"
         "from api.main import generate_session_token;"
         "sys.stdout, sys.stderr = _s, _e;"
         "print(generate_session_token('admin', 'super', 1))"],
        capture_output=True, text=True, check=True,
    )
    return out.stdout.strip().split("\n")[-1]


def api(path: str, body: dict | None = None, method: str = "POST", tok: str | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {tok}",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        # Re-mint if expired and retry once
        if e.code == 401:
            print(f"  (401 on {method} {path}; re-minting token and retrying)")
            new_tok = mint_token()
            with open("/tmp/tb_token.txt", "w") as f:
                f.write(new_tok)
            req = urllib.request.Request(
                f"{API}{path}", data=data,
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {new_tok}"},
                method=method,
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        sys.exit(f"HTTP {e.code} on {method} {path}: {e.read().decode()[:600]}")


def create_experiment(label: str, harness_v: int, tok: str) -> int:
    body = {
        "agent_id": AGENT_ID,
        "label": label,
        "harness_version_id": harness_v,
        "system_prompt_version_id": PROMPT_V,
        "llm_identifier": LLM,
        "adapter_version_id": ADAPTER_V,
    }
    row = api("/experiments", body, tok=tok)
    eid = row["experiment_id"]
    print(f"  Created E{eid} '{label}' (adapter v{ADAPTER_V}, harness v{harness_v})")
    return eid


def run_experiment_and_wait(eid: int, timeout_s: int = 5400) -> dict:
    tok = open("/tmp/tb_token.txt").read().strip()
    print(f"  Launching E{eid}...")
    api(f"/experiments/{eid}/run", method="POST", tok=tok)
    start = time.time()
    last_state = "running"
    while True:
        tok = open("/tmp/tb_token.txt").read().strip()
        row = api(f"/experiments/{eid}", method="GET", tok=tok)
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
    # Fresh token on start to prevent 24h expiry mid-run
    tok = mint_token()
    with open("/tmp/tb_token.txt", "w") as f:
        f.write(tok)
    print(f"minted fresh session token ({len(tok)} bytes)")
    print()

    # 4 holdout + 1 baseline-test for cross-reference
    runs = [
        ("tb-us-082-trial8-eholdout-v9-replicate-1", HARNESS_HOLDOUT),
        ("tb-us-082-trial8-eholdout-v9-replicate-2", HARNESS_HOLDOUT),
        ("tb-us-082-trial8-eholdout-v9-replicate-3", HARNESS_HOLDOUT),
        ("tb-us-082-trial8-eholdout-v9-replicate-4", HARNESS_HOLDOUT),
        ("tb-us-082-trial8-ein-baseline-test-v9",   HARNESS_BASELINE),
    ]

    results = []
    for label, harness_v in runs:
        print(f"\n=== {label} ===")
        tok = open("/tmp/tb_token.txt").read().strip()
        eid = create_experiment(label, harness_v, tok)
        row = run_experiment_and_wait(eid)
        summary = summarize_result(row)
        print(f"  E{eid} final: {summary}")
        results.append((eid, label, harness_v, summary, row.get("state")))

    print()
    print("=" * 72)
    print("TB-US-082 Trial #8 measurement summary")
    print("=" * 72)
    for eid, label, harness_v, summary, state in results:
        dsname = "holdout" if harness_v == HARNESS_HOLDOUT else "baseline-test"
        print(f"  E{eid:>3} [{state:>9}]  {dsname:<14}  {summary:>22}  {label}")


if __name__ == "__main__":
    main()
