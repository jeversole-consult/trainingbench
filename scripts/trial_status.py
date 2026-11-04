#!/usr/bin/env python3
"""TB research-arc status reporter.

Read-only script that prints the current state of training runs +
experiments for a given trial, intended to be safely allowlisted for
automation / wake-up polling. Uses only Python stdlib (sqlite3, json,
argparse, pathlib, re).

Usage:
    python3 trial_status.py                      # all TB-US-* experiments
    python3 trial_status.py --trial 082          # only TB-US-082's experiments
    python3 trial_status.py --training-only      # training runs only
    python3 trial_status.py --trial 082 --training   # both

This script does NOT write to any database, does NOT call any HTTP
endpoint, does NOT spawn subprocesses, and does NOT import any TB
backend module. Safe to allowlist via:

    "Bash(/home/jeversole/trainingbench/venv/bin/python
         /home/jeversole/trainingbench/scripts/trial_status.py *)"

(Single-line in actual settings.json; split here for readability.)
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

TB_ROOT = Path(__file__).resolve().parent.parent
TB_DB = TB_ROOT / "backend" / "db" / "trainingbench.db"
RUNS_DB = TB_ROOT / "training" / "runs" / "runs_tracker.db"


def _fmt_acc(rj_str: str | None) -> str:
    """Decode an experiment's results_json and return a '{k}/{n} = {pct}%' string."""
    if not rj_str:
        return "—"
    try:
        d = json.loads(rj_str)
    except Exception:
        return "(unparseable)"
    v = d.get("value")
    n = d.get("n_samples")
    k = d.get("correct_count")
    if v is None or n is None or k is None:
        return "—"
    try:
        return f"{k}/{n} = {v*100:.1f}%"
    except Exception:
        return "—"


def print_experiments(trial_filter: str | None) -> None:
    label_prefix = f"tb-us-{trial_filter}" if trial_filter else "tb-us-"
    with sqlite3.connect(f"file:{TB_DB}?mode=ro", uri=True) as c:
        c.row_factory = sqlite3.Row
        rows = list(
            c.execute(
                "SELECT experiment_id, state, label, results_json, "
                "created_at, completed_at "
                "FROM experiments WHERE label LIKE ? "
                "ORDER BY experiment_id",
                (label_prefix + "%",),
            )
        )
    if not rows:
        print(f"(no experiments matching '{label_prefix}*')")
        return
    print(f"=== Experiments matching '{label_prefix}*' ({len(rows)}) ===")
    for r in rows:
        acc = _fmt_acc(r["results_json"])
        print(
            f"E{r['experiment_id']:>3} [{r['state']:>9}]  {acc:<20}  "
            f"{r['label']}"
        )


def print_training_runs() -> None:
    if not RUNS_DB.exists():
        print("(no runs_tracker.db yet)")
        return
    with sqlite3.connect(f"file:{RUNS_DB}?mode=ro", uri=True) as c:
        c.row_factory = sqlite3.Row
        rows = list(
            c.execute(
                "SELECT id, run_name, status, duration_seconds, "
                "started_at, completed_at "
                "FROM training_runs WHERE status IN ('running', 'completed') "
                "ORDER BY id DESC LIMIT 5"
            )
        )
    print(f"=== Training runs (5 most recent) ===")
    for r in rows:
        dur = f"{r['duration_seconds']}s" if r["duration_seconds"] else "—"
        print(f"run{r['id']:>3} [{r['status']:>9}]  dur={dur:<8}  {r['run_name']}")

    # Also show latest metric point for any 'running' run
    with sqlite3.connect(f"file:{RUNS_DB}?mode=ro", uri=True) as c:
        c.row_factory = sqlite3.Row
        active = c.execute(
            "SELECT id FROM training_runs WHERE status='running' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if active:
            metric = c.execute(
                "SELECT step, epoch, train_loss, eval_loss "
                "FROM training_run_metrics WHERE run_id=? "
                "ORDER BY step DESC LIMIT 1",
                (active["id"],),
            ).fetchone()
            if metric:
                print(
                    f"  latest metric for run{active['id']}: "
                    f"step={metric['step']} epoch={metric['epoch']:.2f} "
                    f"train_loss={metric['train_loss']} "
                    f"eval_loss={metric['eval_loss']}"
                )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--trial",
        type=str,
        default=None,
        help="Filter to experiments matching 'tb-us-<trial>*' "
        "(e.g., '082' for Trial #8). Default: all TB-US-* experiments.",
    )
    ap.add_argument(
        "--training-only",
        action="store_true",
        help="Show training runs only (skip experiments).",
    )
    ap.add_argument(
        "--training",
        action="store_true",
        help="Also show training runs (default: experiments only).",
    )
    args = ap.parse_args()

    if not TB_DB.exists():
        print(f"ERROR: TB DB not found at {TB_DB}", file=sys.stderr)
        return 1

    if not args.training_only:
        print_experiments(args.trial)
        print()

    if args.training or args.training_only:
        print_training_runs()

    return 0


if __name__ == "__main__":
    sys.exit(main())
