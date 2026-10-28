"""TB-US-065: Transformers TrainerCallback that writes directly to the
TrainingBench tracker DB (`training/runs/runs_tracker.db`).

Used when `train.py` is invoked with `--run-id <int>` — the parent TB
server has already created the `training_runs` row and spawned this
subprocess; this callback writes per-step metrics + log lines + status
transitions back to the DB during training.

Design decision: direct SQLite writes (per TB-US-065 R7). Simpler than
piping stdout through a watcher or hitting an HTTP callback. Lock
contention is unlikely at `logging_steps` cadence (default ~every 50
training steps).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from transformers import TrainerCallback


DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "training" / "runs" / "runs_tracker.db"


class TBDBTrainerCallback(TrainerCallback):
    """Writes HF Trainer events to the training_runs* tables for a given run_id."""

    def __init__(self, run_id: int, db_path: Path = DEFAULT_DB_PATH):
        self.run_id = run_id
        self.db_path = str(db_path)
        self._log("Training started")

    # ------------------------------------------------------------------ #
    # SQLite helpers
    # ------------------------------------------------------------------ #

    def _connect(self):
        return sqlite3.connect(self.db_path, timeout=30.0)

    def _log(self, message: str, level: str = "INFO") -> None:
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO training_run_logs (run_id, timestamp, log_level, message) VALUES (?, ?, ?, ?)",
                    (self.run_id, datetime.now().isoformat(), level, message),
                )
                conn.commit()
        except Exception:
            pass  # never crash training on log failure

    # ------------------------------------------------------------------ #
    # Callback hooks
    # ------------------------------------------------------------------ #

    def on_log(self, args, state, control, logs=None, **kwargs):
        """Fires at every `logging_steps` interval from the Trainer."""
        if not logs:
            return
        step = state.global_step
        epoch = state.epoch
        train_loss = logs.get("loss")
        eval_loss = logs.get("eval_loss")
        lr = logs.get("learning_rate")
        timestamp = datetime.now().isoformat()
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO training_run_metrics
                        (run_id, step, epoch, train_loss, eval_loss, learning_rate, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (self.run_id, step, epoch, train_loss, eval_loss, lr, timestamp),
                )
                conn.commit()
        except Exception as e:
            self._log(f"metric write failed: {e}", level="WARN")

        parts = [f"step={step}"]
        if epoch is not None:
            parts.append(f"epoch={epoch:.2f}")
        if train_loss is not None:
            parts.append(f"train_loss={train_loss:.4f}")
        if eval_loss is not None:
            parts.append(f"eval_loss={eval_loss:.4f}")
        if lr is not None:
            parts.append(f"lr={lr:.2e}")
        self._log(" ".join(parts))

    def on_save(self, args, state, control, **kwargs):
        """Fires when the Trainer saves a checkpoint."""
        step = state.global_step
        ckpt_path = f"{args.output_dir}/checkpoint-{step}"
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO training_run_checkpoints
                        (run_id, checkpoint_step, checkpoint_path, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (self.run_id, step, ckpt_path, datetime.now().isoformat()),
                )
                conn.commit()
        except Exception as e:
            self._log(f"checkpoint record failed: {e}", level="WARN")
        self._log(f"checkpoint saved at step {step}: {ckpt_path}")

    def on_train_end(self, args, state, control, **kwargs):
        """Fires at the end of training (success path)."""
        self._log("Training finished (on_train_end callback)")


def mark_run_completed(
    run_id: int,
    duration_seconds: Optional[int],
    final_train_loss: Optional[float] = None,
    final_eval_loss: Optional[float] = None,
    adapter_output_path: Optional[str] = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Called from train.py's main() on successful completion."""
    with sqlite3.connect(str(db_path), timeout=30.0) as conn:
        conn.execute(
            """
            UPDATE training_runs
            SET status = 'completed',
                completed_at = ?,
                duration_seconds = ?,
                final_train_loss = COALESCE(?, final_train_loss),
                final_eval_loss = COALESCE(?, final_eval_loss),
                adapter_output_path = COALESCE(?, adapter_output_path)
            WHERE id = ?
            """,
            (datetime.now().isoformat(), duration_seconds, final_train_loss,
             final_eval_loss, adapter_output_path, run_id),
        )
        conn.commit()


def mark_run_failed(
    run_id: int,
    error_message: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Called from train.py's main() on exception."""
    with sqlite3.connect(str(db_path), timeout=30.0) as conn:
        conn.execute(
            """
            UPDATE training_runs
            SET status = 'failed',
                completed_at = ?,
                notes = CASE WHEN notes IS NULL OR notes = '' THEN ? ELSE notes || char(10) || ? END
            WHERE id = ?
            """,
            (datetime.now().isoformat(), error_message, error_message, run_id),
        )
        conn.commit()


def load_run_config(
    run_id: int,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict:
    """Return the run's config JSON blob as a dict, so train.py can
    override CLI defaults with the launch-time hyperparameters.
    """
    import json
    with sqlite3.connect(str(db_path), timeout=30.0) as conn:
        row = conn.execute(
            "SELECT config, run_name, base_model, agent_id, training_set_version_id, adapter_output_path "
            "FROM training_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
    if row is None:
        raise RuntimeError(f"Run {run_id} not found in {db_path}")
    config = json.loads(row[0] or "{}")
    config["_run_name"] = row[1]
    config["_base_model"] = row[2]
    config["_agent_id"] = row[3]
    config["_training_set_version_id"] = row[4]
    config["_adapter_output_path"] = row[5]
    return config
