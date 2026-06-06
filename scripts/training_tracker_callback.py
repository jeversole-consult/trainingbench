#!/usr/bin/env python3
"""
Transformers TrainerCallback for logging training runs to local JSON files.
Automatically tracks metrics, logs, and checkpoints during training.

Standalone version for TrainingBench - no API backend required.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from transformers import TrainerCallback, TrainerState, TrainerControl
from transformers.trainer_utils import PREFIX_CHECKPOINT_DIR


class TrainingTrackerCallback(TrainerCallback):
    """
    Callback for tracking training runs locally via JSON files.

    Logs metrics, training progress, and checkpoints to local files.
    """

    def __init__(
        self,
        run_name: str,
        log_dir: Optional[str] = None
    ):
        """
        Initialize the callback.

        Args:
            run_name: Name of this training run
            log_dir: Directory to save logs (default: experiments/logs/training_runs)
        """
        self.run_name = run_name

        # Set up logging directory
        if log_dir is None:
            # Default to experiments/logs/training_runs
            project_root = Path(__file__).parent.parent
            log_dir = project_root / "experiments" / "logs" / "training_runs"

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create timestamped run directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = self.log_dir / f"{run_name}_{timestamp}"
        self.run_dir.mkdir(parents=True, exist_ok=True)

        # File paths
        self.metrics_file = self.run_dir / "metrics.jsonl"
        self.logs_file = self.run_dir / "logs.jsonl"
        self.checkpoints_file = self.run_dir / "checkpoints.json"
        self.run_info_file = self.run_dir / "run_info.json"

        # Initialize run info
        self.run_info = {
            "run_name": run_name,
            "started_at": datetime.now().isoformat(),
            "status": "running",
            "output_dir": str(self.run_dir)
        }
        self._save_run_info()

        print(f"\n📊 Training Tracker: Logging to {self.run_dir}")

    def _save_run_info(self):
        """Save run info to JSON file."""
        with open(self.run_info_file, 'w') as f:
            json.dump(self.run_info, f, indent=2)

    def _log_message(self, message: str, level: str = "INFO"):
        """Log a message to the logs file."""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "message": message
            }
            with open(self.logs_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"Warning: Failed to log message: {e}")

    def _log_metrics(self, step: int, epoch: float, metrics: dict):
        """Log training metrics to the metrics file."""
        try:
            # Extract metrics
            train_loss = metrics.get('loss', metrics.get('train_loss'))
            eval_loss = metrics.get('eval_loss')
            train_accuracy = metrics.get('train_accuracy')
            eval_accuracy = metrics.get('eval_accuracy')
            learning_rate = metrics.get('learning_rate')

            metric_entry = {
                "timestamp": datetime.now().isoformat(),
                "step": step,
                "epoch": round(epoch, 4) if epoch is not None else None,
                "train_loss": round(train_loss, 6) if train_loss is not None else None,
                "eval_loss": round(eval_loss, 6) if eval_loss is not None else None,
                "train_accuracy": round(train_accuracy, 6) if train_accuracy is not None else None,
                "eval_accuracy": round(eval_accuracy, 6) if eval_accuracy is not None else None,
                "learning_rate": learning_rate
            }

            # Remove None values
            metric_entry = {k: v for k, v in metric_entry.items() if v is not None}

            with open(self.metrics_file, 'a') as f:
                f.write(json.dumps(metric_entry) + '\n')
        except Exception as e:
            print(f"Warning: Failed to log metrics: {e}")

    def _update_status(
        self,
        status: str,
        final_train_loss: Optional[float] = None,
        final_eval_loss: Optional[float] = None,
        final_train_accuracy: Optional[float] = None,
        final_eval_accuracy: Optional[float] = None,
        notes: Optional[str] = None
    ):
        """Update training run status."""
        self.run_info["status"] = status
        self.run_info["updated_at"] = datetime.now().isoformat()

        if final_train_loss is not None:
            self.run_info["final_train_loss"] = round(final_train_loss, 6)
        if final_eval_loss is not None:
            self.run_info["final_eval_loss"] = round(final_eval_loss, 6)
        if final_train_accuracy is not None:
            self.run_info["final_train_accuracy"] = round(final_train_accuracy, 6)
        if final_eval_accuracy is not None:
            self.run_info["final_eval_accuracy"] = round(final_eval_accuracy, 6)
        if notes:
            self.run_info["notes"] = notes

        self._save_run_info()

    def _log_checkpoint(self, checkpoint_path: str, step: int, metrics: dict):
        """Log a checkpoint to the checkpoints file."""
        try:
            # Load existing checkpoints
            if self.checkpoints_file.exists():
                with open(self.checkpoints_file, 'r') as f:
                    checkpoints = json.load(f)
            else:
                checkpoints = []

            # Extract metrics
            train_loss = metrics.get('loss', metrics.get('train_loss'))
            eval_loss = metrics.get('eval_loss')
            train_accuracy = metrics.get('train_accuracy')
            eval_accuracy = metrics.get('eval_accuracy')

            checkpoint_entry = {
                "timestamp": datetime.now().isoformat(),
                "step": step,
                "checkpoint_path": checkpoint_path,
                "train_loss": round(train_loss, 6) if train_loss is not None else None,
                "eval_loss": round(eval_loss, 6) if eval_loss is not None else None,
                "train_accuracy": round(train_accuracy, 6) if train_accuracy is not None else None,
                "eval_accuracy": round(eval_accuracy, 6) if eval_accuracy is not None else None
            }

            # Remove None values
            checkpoint_entry = {k: v for k, v in checkpoint_entry.items() if v is not None}

            checkpoints.append(checkpoint_entry)

            # Save updated checkpoints
            with open(self.checkpoints_file, 'w') as f:
                json.dump(checkpoints, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to log checkpoint: {e}")

    def on_train_begin(self, args, state, control, **kwargs):
        """Called at the beginning of training."""
        self._log_message("Training started", "INFO")

        # Log training configuration
        self.run_info["config"] = {
            "output_dir": args.output_dir,
            "num_train_epochs": args.num_train_epochs,
            "per_device_train_batch_size": args.per_device_train_batch_size,
            "gradient_accumulation_steps": args.gradient_accumulation_steps,
            "learning_rate": args.learning_rate,
            "warmup_steps": args.warmup_steps,
            "logging_steps": args.logging_steps,
            "save_steps": args.save_steps,
            "fp16": args.fp16,
            "optim": args.optim
        }
        self._save_run_info()

    def on_log(self, args, state, control, logs=None, **kwargs):
        """Called after logging."""
        if logs:
            # Log metrics on each logging step
            epoch = logs.get('epoch', state.epoch)
            step = state.global_step

            # Only log if we have actual training metrics
            if 'loss' in logs or 'train_loss' in logs or 'eval_loss' in logs:
                self._log_metrics(step, epoch, logs)

    def on_evaluate(self, args, state, control, metrics=None, **kwargs):
        """Called after evaluation."""
        if metrics:
            epoch = metrics.get('epoch', state.epoch)
            step = state.global_step

            # Log evaluation metrics
            self._log_metrics(step, epoch, metrics)

            # Log evaluation message
            eval_loss = metrics.get('eval_loss', 'N/A')
            self._log_message(
                f"Evaluation at step {step}: eval_loss={eval_loss}",
                "INFO"
            )

    def on_save(self, args, state, control, **kwargs):
        """Called after a checkpoint save."""
        checkpoint_folder = f"{PREFIX_CHECKPOINT_DIR}-{state.global_step}"
        checkpoint_path = os.path.join(args.output_dir, checkpoint_folder)

        # Get latest metrics from state
        metrics = {}
        if hasattr(state, 'log_history') and state.log_history:
            # Get most recent log entry
            for log_entry in reversed(state.log_history):
                if 'loss' in log_entry or 'eval_loss' in log_entry:
                    metrics = log_entry
                    break

        self._log_checkpoint(checkpoint_path, state.global_step, metrics)
        self._log_message(f"Checkpoint saved: {checkpoint_path}", "INFO")

    def on_train_end(self, args, state, control, **kwargs):
        """Called at the end of training."""
        # Extract final metrics from training history
        final_metrics = {}
        if hasattr(state, 'log_history') and state.log_history:
            # Get the last evaluation metrics
            for log_entry in reversed(state.log_history):
                if 'eval_loss' in log_entry:
                    final_metrics = log_entry
                    break

            # If no eval metrics, get last train metrics
            if not final_metrics:
                for log_entry in reversed(state.log_history):
                    if 'loss' in log_entry:
                        final_metrics = log_entry
                        break

        # Record completion time
        self.run_info["completed_at"] = datetime.now().isoformat()

        # Calculate training duration
        started = datetime.fromisoformat(self.run_info["started_at"])
        completed = datetime.fromisoformat(self.run_info["completed_at"])
        duration = (completed - started).total_seconds()
        self.run_info["duration_seconds"] = round(duration, 2)

        # Update status to completed
        self._update_status(
            status="completed",
            final_train_loss=final_metrics.get('loss', final_metrics.get('train_loss')),
            final_eval_loss=final_metrics.get('eval_loss'),
            final_train_accuracy=final_metrics.get('train_accuracy'),
            final_eval_accuracy=final_metrics.get('eval_accuracy'),
            notes="Training completed successfully"
        )

        self._log_message("Training completed successfully", "INFO")
        print(f"\n✓ Training run logged to: {self.run_dir}")
        print(f"   Metrics: {self.metrics_file}")
        print(f"   Logs: {self.logs_file}")
        print(f"   Run info: {self.run_info_file}")

    def on_train_error(self, args, state, control, error=None, **kwargs):
        """Called when training encounters an error."""
        error_msg = f"Training failed: {str(error)}" if error else "Training failed with unknown error"

        self._update_status(
            status="failed",
            notes=error_msg
        )

        self._log_message(error_msg, "ERROR")
        print(f"\n❌ Training run marked as failed: {self.run_dir}")


def load_run_metrics(run_dir: str):
    """
    Load and parse metrics from a training run directory.

    Args:
        run_dir: Path to the training run directory

    Returns:
        Dictionary with run_info, metrics, logs, and checkpoints
    """
    run_dir = Path(run_dir)

    result = {
        "run_info": None,
        "metrics": [],
        "logs": [],
        "checkpoints": []
    }

    # Load run info
    run_info_file = run_dir / "run_info.json"
    if run_info_file.exists():
        with open(run_info_file, 'r') as f:
            result["run_info"] = json.load(f)

    # Load metrics (JSONL format)
    metrics_file = run_dir / "metrics.jsonl"
    if metrics_file.exists():
        with open(metrics_file, 'r') as f:
            for line in f:
                result["metrics"].append(json.loads(line.strip()))

    # Load logs (JSONL format)
    logs_file = run_dir / "logs.jsonl"
    if logs_file.exists():
        with open(logs_file, 'r') as f:
            for line in f:
                result["logs"].append(json.loads(line.strip()))

    # Load checkpoints
    checkpoints_file = run_dir / "checkpoints.json"
    if checkpoints_file.exists():
        with open(checkpoints_file, 'r') as f:
            result["checkpoints"] = json.load(f)

    return result
