#!/usr/bin/env python3
"""TB-US-082 Trial #8: resume remaining experiments after orchestrator kill.

E31 (holdout replicate 1) completed at 50.0%. Still need:
- E32, E33, E34 — holdout replicates 2-4
- E35 — baseline-test (adapter v9 × harness v4)

Resilience improvements over tb_us_082_run_experiments.py:
1. Fresh token minted at start (not stale from prior session)
2. Polling uses DIRECT SQLite reads, not HTTP — avoids the 24h
   token issue during the long-wait phase (where prior runs
   got killed by harness runtime)
3. Only API calls are the per-experiment create + launch
   (2 calls per experiment × 4 experiments = 8 total API calls;
   each < 1 second)
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
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
ADAPTER_V = 9
TB_DB = "backend/db/trainingbench.db"


def mint_token() -> str:
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


def api_post(path: str, body: dict | None, tok: str) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{API}{path}", data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {tok}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def poll_experiment_state_via_db(eid: int, timeout_s: int = 5400) -> dict:
    """Poll experiment state by reading SQLite directly. Avoids all HTTP
    + token issues during long-wait phase.
    """
    start = time.time()
    last_state = "running"
    while True:
        with sqlite3.connect(TB_DB) as c:
            c.row_factory = sqlite3.Row
            r = c.execute(
                "SELECT state, results_json FROM experiments WHERE experiment_id=?",
                (eid,),
            ).fetchone()
        if r is None:
            time.sleep(5)
            continue
        state = r["state"]
        if state != last_state:
            print(f"    E{eid} state: {state}")
            last_state = state
        if state in ("completed", "archived"):
            # Parse results if present
            d = {}
            if r["results_json"]:
                try:
                    d = json.loads(r["results_json"])
                except Exception:
                    pass
            return {"state": state, "n": d.get("n_samples"),
                    "k": d.get("correct_count"), "v": d.get("value")}
        if time.time() - start > timeout_s:
            sys.exit(f"E{eid} timed out after {timeout_s}s (last state: {state})")
        time.sleep(30)


def create_and_run(label: str, harness_v: int, tok: str) -> int:
    row = api_post("/experiments", {
        "agent_id": AGENT_ID,
        "label": label,
        "harness_version_id": harness_v,
        "system_prompt_version_id": PROMPT_V,
        "llm_identifier": LLM,
        "adapter_version_id": ADAPTER_V,
    }, tok)
    eid = row["experiment_id"]
    print(f"  Created E{eid} '{label}' (adapter v{ADAPTER_V}, harness v{harness_v})")
    api_post(f"/experiments/{eid}/run", None, tok)
    print(f"  Launched E{eid}")
    return eid


def main() -> None:
    tok = mint_token()
    with open("/tmp/tb_token.txt", "w") as f:
        f.write(tok)
    print(f"minted fresh session token")
    print()

    runs = [
        ("tb-us-082-trial8-eholdout-v9-replicate-2", HARNESS_HOLDOUT),
        ("tb-us-082-trial8-eholdout-v9-replicate-3", HARNESS_HOLDOUT),
        ("tb-us-082-trial8-eholdout-v9-replicate-4", HARNESS_HOLDOUT),
        ("tb-us-082-trial8-ein-baseline-test-v9",   HARNESS_BASELINE),
    ]

    results = []
    for label, harness_v in runs:
        print(f"\n=== {label} ===")
        eid = create_and_run(label, harness_v, tok)
        r = poll_experiment_state_via_db(eid)
        summary = f"{r['k']}/{r['n']} = {r['v']*100:.1f}%" if r["v"] is not None else "(no results)"
        print(f"  E{eid} {r['state']}: {summary}")
        results.append((eid, label, harness_v, r["state"], summary))

    print()
    print("=" * 72)
    print("TB-US-082 Trial #8 — remaining experiments summary")
    print("=" * 72)
    for eid, label, harness_v, state, summary in results:
        dsname = "holdout" if harness_v == HARNESS_HOLDOUT else "baseline-test"
        print(f"  E{eid:>3} [{state:>9}]  {dsname:<14}  {summary:>22}  {label}")
    print()
    print(f"E31 (replicate-1, already completed): 100/200 = 50.0% holdout")


if __name__ == "__main__":
    main()
