#!/usr/bin/env python3
"""
Training Run Tracker for managing and monitoring training experiments.
Provides experiment tracking, metrics logging, and comparison capabilities.
"""

import sqlite3
import json
import shutil
from typing import Optional, Dict, List
from datetime import datetime
from pathlib import Path


class TrainingRunTracker:
    """
    Manages training run experiments with comprehensive tracking.

    Features:
    - Track training runs with full configuration
    - Log metrics and progress during training
    - Store checkpoints and model outputs
    - Compare multiple training runs
    - Link to training sets
    """

    def __init__(self, db_path: str = "training/runs/runs_tracker.db"):
        """
        Initialize training run tracker.

        Args:
            db_path: Path to SQLite database for tracking
        """
        self.db_path = db_path
        self.db_dir = Path(db_path).parent

        # Ensure directory exists
        self.db_dir.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Main training runs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS training_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    training_set_id INTEGER,
                    test_set_id INTEGER,
                    base_model TEXT NOT NULL,
                    adapter_output_path TEXT NOT NULL,

                    -- Training configuration (JSON)
                    config TEXT NOT NULL,

                    -- Timing
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    duration_seconds INTEGER,

                    -- Status tracking
                    status TEXT DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'stopped')),

                    -- Final results
                    final_train_loss REAL,
                    final_eval_loss REAL,
                    final_train_accuracy REAL,
                    final_eval_accuracy REAL,

                    -- Metadata
                    created_by TEXT NOT NULL,
                    gpu_info TEXT,
                    notes TEXT,
                    metadata TEXT
                )
            """)

            # Training run checkpoints
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS training_run_checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    checkpoint_step INTEGER NOT NULL,
                    checkpoint_path TEXT NOT NULL,
                    train_loss REAL,
                    eval_loss REAL,
                    train_accuracy REAL,
                    eval_accuracy REAL,
                    created_at TEXT NOT NULL,

                    FOREIGN KEY (run_id) REFERENCES training_runs(id) ON DELETE CASCADE
                )
            """)

            # Training run logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS training_run_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    log_level TEXT DEFAULT 'INFO',
                    message TEXT NOT NULL,

                    FOREIGN KEY (run_id) REFERENCES training_runs(id) ON DELETE CASCADE
                )
            """)

            # Metrics history for charting
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS training_run_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    step INTEGER NOT NULL,
                    epoch REAL,
                    train_loss REAL,
                    eval_loss REAL,
                    train_accuracy REAL,
                    eval_accuracy REAL,
                    learning_rate REAL,
                    timestamp TEXT NOT NULL,

                    FOREIGN KEY (run_id) REFERENCES training_runs(id) ON DELETE CASCADE
                )
            """)

            conn.commit()
            print("Training run tracker database initialized")

    def create_training_run(
        self,
        run_name: str,
        training_set_id: int,
        base_model: str,
        adapter_output_path: str,
        config: Dict,
        created_by: str,
        description: str = "",
        test_set_id: int = None,
        gpu_info: str = None,
        notes: str = None,
        metadata: Dict = None
    ) -> Dict:
        """
        Create a new training run.

        Args:
            run_name: Unique name for this training run
            training_set_id: ID of training set to use
            base_model: Base model identifier
            adapter_output_path: Path where adapter will be saved
            config: Training configuration dict
            created_by: Username of creator
            description: Description of the run
            test_set_id: Optional test set ID
            gpu_info: GPU information
            notes: Additional notes
            metadata: Additional metadata

        Returns:
            Dict with status and run info
        """
        try:
            # Validate inputs
            if not run_name or not run_name.strip():
                return {"status": "error", "error": "Run name cannot be empty"}

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO training_runs (
                        run_name, description, training_set_id, test_set_id,
                        base_model, adapter_output_path, config,
                        started_at, status, created_by, gpu_info, notes, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?, ?, ?)
                """, (
                    run_name,
                    description,
                    training_set_id,
                    test_set_id,
                    base_model,
                    adapter_output_path,
                    json.dumps(config),
                    datetime.now().isoformat(),
                    created_by,
                    gpu_info,
                    notes,
                    json.dumps(metadata) if metadata else None
                ))

                conn.commit()
                run_id = cursor.lastrowid

            return {
                "status": "success",
                "id": run_id,
                "run_name": run_name,
                "training_set_id": training_set_id
            }

        except sqlite3.IntegrityError:
            return {"status": "error", "error": f"Training run '{run_name}' already exists"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_training_run(self, run_id: int) -> Optional[Dict]:
        """
        Get training run details by ID.

        Args:
            run_id: Training run ID

        Returns:
            Training run info dict or None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM training_runs WHERE id = ?
            """, (run_id,))

            row = cursor.fetchone()

            if row:
                return {
                    "id": row['id'],
                    "run_name": row['run_name'],
                    "description": row['description'],
                    "training_set_id": row['training_set_id'],
                    "test_set_id": row['test_set_id'],
                    "base_model": row['base_model'],
                    "adapter_output_path": row['adapter_output_path'],
                    "config": json.loads(row['config']) if row['config'] else {},
                    "started_at": row['started_at'],
                    "completed_at": row['completed_at'],
                    "duration_seconds": row['duration_seconds'],
                    "status": row['status'],
                    "final_train_loss": row['final_train_loss'],
                    "final_eval_loss": row['final_eval_loss'],
                    "final_train_accuracy": row['final_train_accuracy'],
                    "final_eval_accuracy": row['final_eval_accuracy'],
                    "created_by": row['created_by'],
                    "gpu_info": row['gpu_info'],
                    "notes": row['notes'],
                    "metadata": json.loads(row['metadata']) if row['metadata'] else {}
                }

            return None

    def list_training_runs(
        self,
        status: str = None,
        search: str = None,
        created_by: str = None,
        training_set_id: int = None,
        limit: int = None
    ) -> List[Dict]:
        """
        List all training runs with optional filtering.

        Args:
            status: Filter by status
            search: Search in name and description
            created_by: Filter by creator
            training_set_id: Filter by training set
            limit: Limit number of results

        Returns:
            List of training run dicts
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM training_runs WHERE 1=1"
            params = []

            if status:
                query += " AND status = ?"
                params.append(status)

            if search:
                query += " AND (run_name LIKE ? OR description LIKE ?)"
                search_pattern = f"%{search}%"
                params.extend([search_pattern, search_pattern])

            if created_by:
                query += " AND created_by = ?"
                params.append(created_by)

            if training_set_id:
                query += " AND training_set_id = ?"
                params.append(training_set_id)

            query += " ORDER BY started_at DESC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)

            runs = []
            for row in cursor.fetchall():
                runs.append({
                    "id": row['id'],
                    "run_name": row['run_name'],
                    "description": row['description'],
                    "training_set_id": row['training_set_id'],
                    "status": row['status'],
                    "started_at": row['started_at'],
                    "completed_at": row['completed_at'],
                    "duration_seconds": row['duration_seconds'],
                    "final_train_loss": row['final_train_loss'],
                    "final_eval_loss": row['final_eval_loss'],
                    "created_by": row['created_by']
                })

            return runs

    def update_training_run_status(
        self,
        run_id: int,
        status: str = None,
        completed_at: str = None,
        duration_seconds: int = None,
        final_train_loss: float = None,
        final_eval_loss: float = None,
        final_train_accuracy: float = None,
        final_eval_accuracy: float = None,
        notes: str = None,
        metadata: Dict = None
    ) -> Dict:
        """
        Update training run status and results.

        Args:
            run_id: Training run ID
            status: New status
            completed_at: Completion timestamp
            duration_seconds: Training duration
            final_train_loss: Final training loss
            final_eval_loss: Final evaluation loss
            final_train_accuracy: Final training accuracy
            final_eval_accuracy: Final evaluation accuracy
            notes: Additional notes
            metadata: Additional metadata dict

        Returns:
            Status dict
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                updates = []
                params = []

                if status:
                    updates.append("status = ?")
                    params.append(status)

                if completed_at:
                    updates.append("completed_at = ?")
                    params.append(completed_at)

                if duration_seconds is not None:
                    updates.append("duration_seconds = ?")
                    params.append(duration_seconds)

                if final_train_loss is not None:
                    updates.append("final_train_loss = ?")
                    params.append(final_train_loss)

                if final_eval_loss is not None:
                    updates.append("final_eval_loss = ?")
                    params.append(final_eval_loss)

                if final_train_accuracy is not None:
                    updates.append("final_train_accuracy = ?")
                    params.append(final_train_accuracy)

                if final_eval_accuracy is not None:
                    updates.append("final_eval_accuracy = ?")
                    params.append(final_eval_accuracy)

                if notes is not None:
                    updates.append("notes = ?")
                    params.append(notes)

                if metadata is not None:
                    updates.append("metadata = ?")
                    params.append(json.dumps(metadata))

                if not updates:
                    return {"status": "error", "error": "No fields to update"}

                params.append(run_id)

                query = f"UPDATE training_runs SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                conn.commit()

                if cursor.rowcount > 0:
                    return {"status": "success", "id": run_id}
                else:
                    return {"status": "error", "error": "Training run not found"}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def add_metric(
        self,
        run_id: int,
        step: int,
        epoch: float = None,
        train_loss: float = None,
        eval_loss: float = None,
        train_accuracy: float = None,
        eval_accuracy: float = None,
        learning_rate: float = None
    ) -> Dict:
        """
        Add a metric data point during training.

        Args:
            run_id: Training run ID
            step: Training step number
            epoch: Current epoch (can be fractional)
            train_loss: Training loss at this step
            eval_loss: Evaluation loss at this step
            train_accuracy: Training accuracy at this step
            eval_accuracy: Evaluation accuracy at this step
            learning_rate: Learning rate at this step

        Returns:
            Status dict
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO training_run_metrics (
                        run_id, step, epoch, train_loss, eval_loss,
                        train_accuracy, eval_accuracy, learning_rate, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id, step, epoch, train_loss, eval_loss,
                    train_accuracy, eval_accuracy, learning_rate,
                    datetime.now().isoformat()
                ))

                conn.commit()

            return {"status": "success"}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_metrics(self, run_id: int) -> List[Dict]:
        """
        Get all metrics for a training run.

        Args:
            run_id: Training run ID

        Returns:
            List of metric dicts
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM training_run_metrics
                WHERE run_id = ?
                ORDER BY step ASC
            """, (run_id,))

            metrics = []
            for row in cursor.fetchall():
                metrics.append({
                    "step": row['step'],
                    "epoch": row['epoch'],
                    "train_loss": row['train_loss'],
                    "eval_loss": row['eval_loss'],
                    "train_accuracy": row['train_accuracy'],
                    "eval_accuracy": row['eval_accuracy'],
                    "learning_rate": row['learning_rate'],
                    "timestamp": row['timestamp']
                })

            return metrics

    def add_log(self, run_id: int, message: str, log_level: str = "INFO") -> Dict:
        """
        Add a log entry for a training run.

        Args:
            run_id: Training run ID
            message: Log message
            log_level: Log level (INFO, WARNING, ERROR, etc.)

        Returns:
            Status dict
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO training_run_logs (run_id, timestamp, log_level, message)
                    VALUES (?, ?, ?, ?)
                """, (run_id, datetime.now().isoformat(), log_level, message))

                conn.commit()

            return {"status": "success"}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_logs(self, run_id: int, log_level: str = None, limit: int = None) -> List[Dict]:
        """
        Get logs for a training run.

        Args:
            run_id: Training run ID
            log_level: Filter by log level (INFO, WARNING, ERROR)
            limit: Limit number of log entries (most recent)

        Returns:
            List of log dicts
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = """
                SELECT * FROM training_run_logs
                WHERE run_id = ?
            """
            params = [run_id]

            if log_level:
                query += " AND log_level = ?"
                params.append(log_level)

            query += " ORDER BY timestamp DESC"

            if limit:
                query += f" LIMIT {limit}"

            cursor.execute(query, params)

            logs = []
            for row in cursor.fetchall():
                logs.append({
                    "timestamp": row['timestamp'],
                    "log_level": row['log_level'],
                    "message": row['message']
                })

            return list(reversed(logs))  # Return in chronological order

    def add_checkpoint(
        self,
        run_id: int,
        checkpoint_step: int,
        checkpoint_path: str,
        train_loss: float = None,
        eval_loss: float = None,
        train_accuracy: float = None,
        eval_accuracy: float = None
    ) -> Dict:
        """
        Add a checkpoint record.

        Args:
            run_id: Training run ID
            checkpoint_step: Step number of checkpoint
            checkpoint_path: Path to checkpoint files
            train_loss: Training loss at checkpoint
            eval_loss: Evaluation loss at checkpoint
            train_accuracy: Training accuracy at checkpoint
            eval_accuracy: Evaluation accuracy at checkpoint

        Returns:
            Status dict
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO training_run_checkpoints (
                        run_id, checkpoint_step, checkpoint_path,
                        train_loss, eval_loss, train_accuracy, eval_accuracy,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id, checkpoint_step, checkpoint_path,
                    train_loss, eval_loss, train_accuracy, eval_accuracy,
                    datetime.now().isoformat()
                ))

                conn.commit()

            return {"status": "success"}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_checkpoints(self, run_id: int) -> List[Dict]:
        """
        Get all checkpoints for a training run.

        Args:
            run_id: Training run ID

        Returns:
            List of checkpoint dicts
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM training_run_checkpoints
                WHERE run_id = ?
                ORDER BY checkpoint_step ASC
            """, (run_id,))

            checkpoints = []
            for row in cursor.fetchall():
                checkpoints.append({
                    "checkpoint_step": row['checkpoint_step'],
                    "checkpoint_path": row['checkpoint_path'],
                    "train_loss": row['train_loss'],
                    "eval_loss": row['eval_loss'],
                    "train_accuracy": row['train_accuracy'],
                    "eval_accuracy": row['eval_accuracy'],
                    "created_at": row['created_at']
                })

            return checkpoints

    def delete_training_run(self, run_id: int, delete_files: bool = False) -> Dict:
        """
        Delete a training run.

        Args:
            run_id: Training run ID
            delete_files: Whether to delete adapter files

        Returns:
            Status dict
        """
        try:
            # Get run info
            run = self.get_training_run(run_id)
            if not run:
                return {"status": "error", "error": "Training run not found"}

            # Delete files if requested
            if delete_files:
                adapter_path = Path(run['adapter_output_path'])
                if adapter_path.exists():
                    shutil.rmtree(adapter_path)

            # Delete from database (cascades to metrics, logs, checkpoints)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM training_runs WHERE id = ?", (run_id,))
                conn.commit()

            return {"status": "success", "id": run_id, "run_name": run['run_name']}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def compare_runs(self, run_ids: List[int]) -> Dict:
        """
        Compare multiple training runs.

        Args:
            run_ids: List of training run IDs to compare

        Returns:
            Dict with comparison data
        """
        runs = []
        for run_id in run_ids:
            run = self.get_training_run(run_id)
            if run:
                # Get metrics for comparison
                metrics = self.get_metrics(run_id)
                run['metrics'] = metrics
                runs.append(run)

        return {
            "status": "success",
            "runs": runs,
            "count": len(runs)
        }


# CLI for training run management
if __name__ == "__main__":
    import sys

    tracker = TrainingRunTracker()

    if len(sys.argv) < 2:
        print("Training Run Tracker CLI")
        print("========================")
        print("\nCommands:")
        print("  python training_run_tracker.py list")
        print("  python training_run_tracker.py info <id>")
        print("  python training_run_tracker.py delete <id>")
        sys.exit(0)

    command = sys.argv[1]

    if command == "list":
        runs = tracker.list_training_runs()
        print(f"\nTotal training runs: {len(runs)}\n")
        for run in runs:
            duration = f"{run['duration_seconds']}s" if run['duration_seconds'] else "N/A"
            loss = f"{run['final_eval_loss']:.4f}" if run['final_eval_loss'] else "N/A"
            print(f"  [{run['status'].upper():10}] ID: {run['id']:3} | {run['run_name']:30} | Loss: {loss:8} | Duration: {duration:8} | By: {run['created_by']}")

    elif command == "info" and len(sys.argv) >= 3:
        run_id = int(sys.argv[2])
        run = tracker.get_training_run(run_id)
        if run:
            print(f"\nTraining Run Details:")
            print(f"  ID: {run['id']}")
            print(f"  Name: {run['run_name']}")
            print(f"  Description: {run['description']}")
            print(f"  Status: {run['status']}")
            print(f"  Training Set ID: {run['training_set_id']}")
            print(f"  Base Model: {run['base_model']}")
            print(f"  Started: {run['started_at']}")
            print(f"  Duration: {run['duration_seconds']}s" if run['duration_seconds'] else "  Duration: Running...")
            print(f"  Final Eval Loss: {run['final_eval_loss']}" if run['final_eval_loss'] else "  Final Eval Loss: N/A")
            print(f"  Adapter Path: {run['adapter_output_path']}")
        else:
            print(f"Training run {run_id} not found")

    elif command == "delete" and len(sys.argv) >= 3:
        run_id = int(sys.argv[2])
        result = tracker.delete_training_run(run_id)
        print(result)

    else:
        print("Invalid command. Run without arguments for help.")
