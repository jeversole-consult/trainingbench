"""TB-US-056: minimal CRUD helpers for the experiments table.

Experiments are the pivot table that ties a (prompt, RAG, LLM,
adapter) stack + a harness to a measurement result. The full UX
layer (compare runs, promote-from-experiment, snapshot capture at
promote time) is a future story. This module provides the primitives
the runner + endpoints need: create, read, state transitions.

State model (per TB-US-043 Q6)::

    draft → running → completed
                       ↘ promoted ↔ displaced
    any → archived
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "db" / "trainingbench.db"


class ExperimentError(RuntimeError):
    """Business-rule violation on experiment lifecycle."""


class ExperimentManager:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path

    # ------------------------------------------------------------------ #
    # Reads
    # ------------------------------------------------------------------ #

    def list_experiments(self, agent_id: Optional[int] = None) -> List[Dict]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            if agent_id is not None:
                rows = conn.execute(
                    "SELECT * FROM experiments WHERE agent_id = ? ORDER BY experiment_id",
                    (agent_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM experiments ORDER BY experiment_id"
                ).fetchall()
        return [dict(r) for r in rows]

    def get_by_id(self, experiment_id: int) -> Optional[Dict]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM experiments WHERE experiment_id = ?",
                (experiment_id,),
            ).fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------ #
    # Writes
    # ------------------------------------------------------------------ #

    def create_experiment(
        self,
        agent_id: int,
        label: str,
        created_by: str,
        system_prompt_version_id: Optional[int] = None,
        rag_version_id: Optional[int] = None,
        llm_identifier: Optional[str] = None,
        adapter_version_id: Optional[int] = None,
        harness_version_id: Optional[int] = None,
        parent_experiment_id: Optional[int] = None,
    ) -> Dict:
        now = datetime.now().isoformat()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO experiments (
                    agent_id, label, state, parent_experiment_id,
                    system_prompt_version_id, rag_version_id, llm_identifier,
                    adapter_version_id, harness_version_id, results_json,
                    created_at, created_by
                ) VALUES (?, ?, 'draft', ?, ?, ?, ?, ?, ?, NULL, ?, ?)
                """,
                (agent_id, label, parent_experiment_id,
                 system_prompt_version_id, rag_version_id, llm_identifier,
                 adapter_version_id, harness_version_id,
                 now, created_by),
            )
            experiment_id = cur.lastrowid
            conn.commit()
        return self.get_by_id(experiment_id)

    def transition_state(self, experiment_id: int, new_state: str, extra: Optional[Dict] = None) -> Dict:
        row = self.get_by_id(experiment_id)
        if row is None:
            raise ExperimentError(f"Experiment {experiment_id} not found")

        valid = {
            "draft":       {"running", "archived"},
            "running":     {"completed", "archived"},
            "completed":   {"promoted", "archived"},
            "promoted":    {"displaced", "archived"},
            "displaced":   {"promoted", "archived"},
            "archived":    set(),
        }
        if new_state not in valid.get(row["state"], set()):
            raise ExperimentError(
                f"Cannot transition experiment {experiment_id} from "
                f"{row['state']!r} to {new_state!r}"
            )

        now = datetime.now().isoformat()
        timestamp_col = {
            "running":   None,
            "completed": "completed_at",
            "promoted":  "promoted_at",
            "displaced": "displaced_at",
            "archived":  "archived_at",
        }.get(new_state)

        sets = ["state = ?"]
        values: List[Any] = [new_state]
        if timestamp_col:
            sets.append(f"{timestamp_col} = ?")
            values.append(now)
        if extra and "results_json" in extra:
            sets.append("results_json = ?")
            values.append(extra["results_json"])
        values.append(experiment_id)

        with self._connect() as conn:
            conn.execute(
                f"UPDATE experiments SET {', '.join(sets)} WHERE experiment_id = ?",
                values,
            )
            conn.commit()
        return self.get_by_id(experiment_id)

    def save_results(self, experiment_id: int, results: Dict) -> Dict:
        """Shortcut used by the harness runner on completion."""
        return self.transition_state(
            experiment_id, "completed",
            extra={"results_json": json.dumps(results, sort_keys=True)},
        )

    # ------------------------------------------------------------------ #

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
