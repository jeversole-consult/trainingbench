"""TB-US-092 Phase 2 — fixed-harness re-baseline runner.

Fires experiments sequentially against the math-example agent,
one subprocess per experiment so CUDA state is pristine every
time. Avoids the memory-fragmentation slowdown observed when all
12 experiments ran in a single long-lived Python process
(VRAM fragmented from ~16 GB to ~21 GB after one model reload,
causing #53 to pace 33× slower than #52).

Two modes:
  (default)        — parent: create experiment rows + spawn workers
  --exp <id>       — worker: run exactly one experiment then exit
                     (releases CUDA + model on process exit)

All conditions pin:
    agent_id=3 (math-example)
    system_prompt_version_id=3 (promoted)
    harness_version_id=5 (released, GSM8K-200 holdout)
    llm_identifier=None (defaults to meta-llama/Meta-Llama-3.1-8B-Instruct)

Per-experiment exceptions are caught + logged; batch continues.
Progress + final summary written to logs/tb_us_092_phase2.log.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from api.experiment_manager import ExperimentManager  # noqa: E402

AGENT_ID = 3
PROMPT_V_ID = 3
HARNESS_V_ID = 5

CONDITIONS = [
    # label_prefix, adapter_version_id
    ("tb-us-092-stopfix-bare-instruct", None),
    ("tb-us-092-stopfix-v9", 9),
    ("tb-us-092-stopfix-v10", 10),
]
SEEDS_PER_CONDITION = 4

LOG_PATH = REPO_ROOT / "logs" / "tb_us_092_phase2.log"
VENV_PYTHON = str(REPO_ROOT / "venv" / "bin" / "python")


def _log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as f:
        f.write(line + "\n")


def _worker(experiment_id: int) -> int:
    """Run exactly one experiment in this (fresh) Python process.
    Imports harness_runner lazily so model-load happens here, inside
    the subprocess, not in the parent. Process exit returns full
    CUDA state to the OS — the whole point of subprocess isolation.
    """
    from api.experiment_manager import ExperimentManager  # noqa: F811
    from api.harness_runner import run_experiment

    em = ExperimentManager()
    em.transition_state(experiment_id, "running")
    try:
        row = run_experiment(experiment_id)
    except Exception as e:
        # Experiment is already flipped to archived inside run_experiment
        # on exception. Print the trace so the parent sees it.
        print(f"WORKER ERROR on #{experiment_id}: {e}", flush=True)
        traceback.print_exc()
        return 1
    # Print a tight summary the parent can grep from the stdout.
    results = {}
    if row and row.get("results_json"):
        try:
            results = json.loads(row["results_json"])
        except Exception:
            pass
    print(
        f"WORKER_DONE experiment_id={experiment_id} "
        f"state={row.get('state') if row else '?'} "
        f"metric={results.get('metric','?')} value={results.get('value','?')}",
        flush=True,
    )
    return 0


def _parent() -> None:
    em = ExperimentManager()
    _log("=== TB-US-092 Phase 2 subprocess runner start ===")

    # Pre-register experiments as draft rows.
    plan = []
    for prefix, adapter_vid in CONDITIONS:
        for seed in range(1, SEEDS_PER_CONDITION + 1):
            label = f"{prefix}-seed{seed}"
            row = em.create_experiment(
                agent_id=AGENT_ID,
                label=label,
                created_by="tb_us_092_phase2_runner",
                system_prompt_version_id=PROMPT_V_ID,
                rag_version_id=None,
                llm_identifier=None,
                adapter_version_id=adapter_vid,
                harness_version_id=HARNESS_V_ID,
            )
            plan.append((row["experiment_id"], label))
            _log(f"created experiment #{row['experiment_id']} label={label} adapter={adapter_vid}")

    _log(f"plan: {len(plan)} experiments queued; one subprocess per experiment")

    summary = {"completed": 0, "archived": 0, "errors": []}
    for exp_id, label in plan:
        _log(f"--- spawning worker for #{exp_id} ({label})")
        t0 = time.time()
        # Spawn a fresh Python process. All CUDA allocations get
        # fully released when this subprocess exits.
        cmd = [VENV_PYTHON, str(Path(__file__).resolve()), "--exp", str(exp_id)]
        try:
            # Inherit stdout/stderr so HF warnings still land in
            # the top-level stdout log; worker also prints a
            # WORKER_DONE summary line we can parse.
            result = subprocess.run(
                cmd,
                cwd=str(REPO_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
            elapsed = int(time.time() - t0)
            # Parse the summary line from worker stdout.
            summary_line = next(
                (ln for ln in reversed(result.stdout.splitlines())
                 if ln.startswith("WORKER_DONE") or ln.startswith("WORKER ERROR")),
                None,
            )
            if result.returncode == 0:
                summary["completed"] += 1
                _log(f"OK #{exp_id} {label} elapsed={elapsed}s | {summary_line or 'no summary line'}")
            else:
                summary["archived"] += 1
                _log(f"FAIL #{exp_id} {label} elapsed={elapsed}s rc={result.returncode} | {summary_line or 'no summary line'}")
                summary["errors"].append({"experiment_id": exp_id, "label": label, "rc": result.returncode})
        except Exception as e:
            elapsed = int(time.time() - t0)
            summary["errors"].append({"experiment_id": exp_id, "label": label, "error": str(e)})
            _log(f"ERROR spawning #{exp_id} {label} elapsed={elapsed}s: {e}")

    _log("=== TB-US-092 Phase 2 subprocess runner complete ===")
    _log(f"summary: completed={summary['completed']} failed={summary['archived']} errors={len(summary['errors'])}")
    for err in summary["errors"]:
        _log(f"  error on #{err['experiment_id']} ({err['label']}): {err.get('error') or ('rc=' + str(err.get('rc')))}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exp", type=int, help="Worker mode: run this experiment then exit")
    args = parser.parse_args()
    if args.exp is not None:
        sys.exit(_worker(args.exp))
    _parent()


if __name__ == "__main__":
    main()
