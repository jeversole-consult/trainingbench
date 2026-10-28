"""TB-US-048: Agent CRUD on the existing ``agents`` table (TB-US-051 schema).

Agents are the top-level entity in TB's two-tier architecture
(agent management + administrative tier — see TB-US-044 §1.a).

Schema reality check vs the story draft:
TB-US-051 created ``agents`` with ``agent_id INTEGER PRIMARY KEY``
and ``name TEXT UNIQUE NOT NULL``. The story draft (TB-US-048 R1)
assumed ``name`` as PK and called out cascading renames across all
``*_versions`` FK columns. Because the live schema uses ``agent_id``
as the stable PK (and every versioning table FK references
``agent_id``), **rename is a non-destructive UPDATE of the
``name`` field — no cascade is needed**. The versioning tables are
untouched by rename.

Agents are soft-deleted via a ``state`` column (``active`` /
``retired`` — matches TB-US-051 schema). Reactivation is an UPDATE
of ``state`` back to ``active``.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "db" / "trainingbench.db"

# TB-US-044 §6 regex: lowercase slug.
AGENT_NAME_REGEX = re.compile(r"^[a-z][a-z0-9_-]*$")

VALID_STATES = ("active", "retired")


class AgentError(RuntimeError):
    """Business-rule violation (bad transition, bad name, missing row, …)."""


class AgentManager:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path

    # ------------------------------------------------------------------ #
    # Reads
    # ------------------------------------------------------------------ #

    def list_agents(self, include_retired: bool = True) -> List[Dict]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            if include_retired:
                rows = conn.execute(
                    "SELECT * FROM agents ORDER BY agent_id"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM agents WHERE state = 'active' ORDER BY agent_id"
                ).fetchall()
        return [dict(r) for r in rows]

    def get_by_name(self, name: str) -> Optional[Dict]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM agents WHERE name = ?",
                (name,),
            ).fetchone()
        return dict(row) if row else None

    def get_by_id(self, agent_id: int) -> Optional[Dict]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM agents WHERE agent_id = ?",
                (agent_id,),
            ).fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------ #
    # Writes
    # ------------------------------------------------------------------ #

    def create_agent(
        self,
        name: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict:
        self._validate_name(name)
        if self.get_by_name(name):
            raise AgentError(f"Agent name '{name}' already exists")
        now = datetime.now().isoformat()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO agents (name, display_name, description, state, created_at)
                VALUES (?, ?, ?, 'active', ?)
                """,
                (name, display_name or name, description, now),
            )
            agent_id = cur.lastrowid
            conn.commit()
        return self.get_by_id(agent_id)

    def rename_agent(self, old_name: str, new_name: str) -> Dict:
        """Non-destructive rename — stable PK means no FK cascade needed."""
        self._validate_name(new_name)
        row = self.get_by_name(old_name)
        if row is None:
            raise AgentError(f"Agent '{old_name}' not found")
        if old_name == new_name:
            return row
        if self.get_by_name(new_name):
            raise AgentError(f"Agent name '{new_name}' already exists")
        with self._connect() as conn:
            conn.execute(
                "UPDATE agents SET name = ? WHERE agent_id = ?",
                (new_name, row["agent_id"]),
            )
            conn.commit()
        return self.get_by_id(row["agent_id"])

    def update_description(
        self,
        name: str,
        description: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> Dict:
        row = self.get_by_name(name)
        if row is None:
            raise AgentError(f"Agent '{name}' not found")
        sets: List[str] = []
        values: List[Any] = []
        if description is not None:
            sets.append("description = ?")
            values.append(description)
        if display_name is not None:
            sets.append("display_name = ?")
            values.append(display_name)
        if not sets:
            return row
        values.append(row["agent_id"])
        with self._connect() as conn:
            conn.execute(
                f"UPDATE agents SET {', '.join(sets)} WHERE agent_id = ?",
                values,
            )
            conn.commit()
        return self.get_by_id(row["agent_id"])

    def retire_agent(self, name: str) -> Dict:
        """Soft-retire: state → 'retired'. Row and all FKs preserved."""
        row = self.get_by_name(name)
        if row is None:
            raise AgentError(f"Agent '{name}' not found")
        if row["state"] == "retired":
            return row
        now = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                "UPDATE agents SET state = 'retired', retired_at = ? WHERE agent_id = ?",
                (now, row["agent_id"]),
            )
            conn.commit()
        return self.get_by_id(row["agent_id"])

    def reactivate_agent(self, name: str) -> Dict:
        row = self.get_by_name(name)
        if row is None:
            raise AgentError(f"Agent '{name}' not found")
        if row["state"] == "active":
            return row
        with self._connect() as conn:
            conn.execute(
                "UPDATE agents SET state = 'active', retired_at = NULL WHERE agent_id = ?",
                (row["agent_id"],),
            )
            conn.commit()
        return self.get_by_id(row["agent_id"])

    # ------------------------------------------------------------------ #

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @staticmethod
    def _validate_name(name: str) -> None:
        if not name or not AGENT_NAME_REGEX.match(name):
            raise AgentError(
                f"Invalid agent name '{name}': must match {AGENT_NAME_REGEX.pattern} "
                "(lowercase start, lowercase/digits/underscore/hyphen only)"
            )
