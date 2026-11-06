#!/usr/bin/env python3
"""TB-US-085 Trial #9 recovery: launch E37-E39 (E36 already completed).

Same resilient pattern as tb_us_082_run_remaining.py:
- Fresh token at start
- DB polling for state (no HTTP, no token exposure during wait)
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import time
import urllib.request

API = "http://localhost:8002"
AGENT_ID = 3
PROMPT_V = 3
LLM = "meta-llama/Meta-Llama-3.1-8B-Instruct"
HARNESS_HOLDOUT = 5
ADAPTER_V = 10
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


def api_post(path, body, tok):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{API}{path}", data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {tok}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def poll_db(eid, timeout_s=5400):
    start = time.time()
    last = "running"
    while True:
        with sqlite3.connect(TB_DB) as c:
            c.row_factory = sqlite3.Row
            r = c.execute(
                "SELECT state, results_json FROM experiments WHERE experiment_id=?",
                (eid,),
            ).fetchone()
        if r is None:
            time.sleep(5); continue
        s = r["state"]
        if s != last:
            print(f"    E{eid} state: {s}"); last = s
        if s in ("completed", "archived"):
            d = {}
            if r["results_json"]:
                try: d = json.loads(r["results_json"])
                except Exception: pass
            return {"state": s, "n": d.get("n_samples"),
                    "k": d.get("correct_count"), "v": d.get("value")}
        if time.time() - start > timeout_s:
            sys.exit(f"E{eid} timed out")
        time.sleep(30)


def main():
    tok = mint_token()
    with open("/tmp/tb_token.txt", "w") as f:
        f.write(tok)
    print("minted fresh token")
    print()

    runs = [
        "tb-us-085-trial9-eholdout-v10-replicate-2",
        "tb-us-085-trial9-eholdout-v10-replicate-3",
        "tb-us-085-trial9-eholdout-v10-replicate-4",
    ]
    results = []
    for label in runs:
        print(f"\n=== {label} ===")
        row = api_post("/experiments", {
            "agent_id": AGENT_ID, "label": label,
            "harness_version_id": HARNESS_HOLDOUT,
            "system_prompt_version_id": PROMPT_V,
            "llm_identifier": LLM, "adapter_version_id": ADAPTER_V,
        }, tok)
        eid = row["experiment_id"]
        print(f"  Created E{eid}")
        api_post(f"/experiments/{eid}/run", None, tok)
        print(f"  Launched E{eid}")
        r = poll_db(eid)
        summary = f"{r['k']}/{r['n']} = {r['v']*100:.1f}%" if r["v"] is not None else "(no results)"
        print(f"  E{eid} {r['state']}: {summary}")
        results.append((eid, label, r["state"], summary))

    print()
    print("=" * 72)
    print("TB-US-085 Trial #9 recovery — E37-E39 summary")
    print("=" * 72)
    for eid, label, state, summary in results:
        print(f"  E{eid:>3} [{state:>9}]  {summary:>22}  {label}")
    print()
    print(f"E36 (already completed): 126/200 = 63.0%")


if __name__ == "__main__":
    main()
