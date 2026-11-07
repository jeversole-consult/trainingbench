"""TB-US-092 Phase 2 — fixed-harness re-baseline runner.

Fires 12 experiments sequentially against the math-example agent:
    4 × bare Instruct (no adapter)
    4 × adapter v9
    4 × adapter v10

All three conditions pin:
    agent_id=3 (math-example)
    system_prompt_version_id=3 (promoted)
    harness_version_id=5 (released, GSM8K-200 holdout)
    llm_identifier=None (defaults to meta-llama/Meta-Llama-3.1-8B-Instruct)

The TB-US-092 Phase 1 harness fix is live, so these experiments run
with chat-template prompting by default (tokenizer.chat_template is
non-null for Llama 3.1 Instruct).

Serial execution — the GPU can only run one at a time. Each run is
~29 min; the batch should complete in ~6 hours.

Per-experiment exceptions are caught + logged; the batch continues.
Progress + final summary written to logs/tb_us_092_phase2.log.
"""
from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from api.experiment_manager import ExperimentManager
from api.harness_runner import run_experiment

AGENT_ID = 3
PROMPT_V_ID = 3
HARNESS_V_ID = 5

CONDITIONS = [
    # label_prefix, adapter_version_id
    # "stopfix" distinguishes this cohort from the aborted earlier one
    # (experiments #40-#51) which ran before the stop-token-ids fix
    # was applied to the pipeline. #40 completed at 85% under the
    # slow generator; #41 was archived mid-flight; #42-#51 were
    # deleted as drafts. All current-cohort runs use stop_token_ids.
    ("tb-us-092-stopfix-bare-instruct", None),
    ("tb-us-092-stopfix-v9", 9),
    ("tb-us-092-stopfix-v10", 10),
]
SEEDS_PER_CONDITION = 4

LOG_PATH = REPO_ROOT / "logs" / "tb_us_092_phase2.log"


def _log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as f:
        f.write(line + "\n")


def main() -> None:
    em = ExperimentManager()
    _log("=== TB-US-092 Phase 2 runner start ===")

    # Pre-register all 12 experiments as draft rows so we have a stable
    # plan visible in the UI before any GPU time is spent.
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

    _log(f"plan: {len(plan)} experiments queued")

    # Execute sequentially. For each experiment, flip state to running
    # (so progress_json polling + strip visibility fire), then invoke
    # the harness runner synchronously. The runner saves results +
    # transitions state to completed/archived on its own.
    summary = {"completed": 0, "archived": 0, "errors": []}
    for exp_id, label in plan:
        _log(f"--- starting experiment #{exp_id} ({label})")
        t0 = time.time()
        try:
            em.transition_state(exp_id, "running")
            result = run_experiment(exp_id)
            elapsed = int(time.time() - t0)
            metric = "?"
            value = None
            if result and result.get("results_json"):
                import json as _json
                try:
                    payload = _json.loads(result["results_json"])
                    metric = payload.get("metric", "?")
                    value = payload.get("value")
                except Exception:
                    pass
            if result and result.get("state") == "completed":
                summary["completed"] += 1
                _log(f"OK #{exp_id} {label} elapsed={elapsed}s metric={metric} value={value}")
            else:
                summary["archived"] += 1
                _log(f"ARCHIVED #{exp_id} {label} elapsed={elapsed}s state={result.get('state') if result else 'unknown'}")
        except Exception as e:
            elapsed = int(time.time() - t0)
            summary["errors"].append({"experiment_id": exp_id, "label": label, "error": str(e)})
            _log(f"ERROR #{exp_id} {label} elapsed={elapsed}s: {e}")
            _log(traceback.format_exc())
            # Best-effort flip to archived so the UI reflects reality.
            try:
                em.transition_state(exp_id, "archived")
            except Exception:
                pass

    _log("=== TB-US-092 Phase 2 runner complete ===")
    _log(f"summary: completed={summary['completed']} archived={summary['archived']} errors={len(summary['errors'])}")
    for err in summary["errors"]:
        _log(f"  error on #{err['experiment_id']} ({err['label']}): {err['error']}")


if __name__ == "__main__":
    main()
