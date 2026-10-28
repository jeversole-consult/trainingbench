"""TB-US-052: base class for versioned-component managers.

A versioned component is one of the six agent-scoped assets whose
history TB tracks: training set, RAG, adapter, prompt, routes,
harness. Each snapshot gets its own row in ``*_versions``; the
currently-promoted snapshot is also recorded in ``agent_components``.

Design captured in ``docs/design/agent-architecture.md`` §6
(versioning primitives) + §8 (lifecycle). This module provides the
shared primitives so subclasses only have to specify what varies.

Subclass contract (set as class attributes):

- ``table_name``       — the ``*_versions`` table this manager owns
- ``component_type``   — one of ``training_set``, ``rag``,
                          ``adapter``, ``prompt``, ``routes``,
                          ``harness`` (matches
                          ``agent_components.component_type`` enum)
- ``promotable``       — True for all axes; False for harness
                          (harness is a measurement sidecar, not a
                          Sweet Spot axis — per TB-US-043 Q5)

And override as methods:

- ``canonical_bytes(payload)`` — subclass-specific canonicalization
  returning the bytes that get SHA-256-hashed. Subclass decides
  what counts as "the content" (training-set rows, prompt text,
  routes JSON, …).

Everything else — insert draft, state transitions, promotion with
displacement — lives here.

Hashing is SHA-256 only (per TB-US-044 Q4) and is for provenance,
not deduplication: identical content on two creates gets two row
IDs. Operators releasing the same content twice is a legitimate
action (re-labeling, re-dating).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# Default path — subclasses may override via the `db_path` constructor arg.
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "db" / "trainingbench.db"


class VersionedComponentError(RuntimeError):
    """Business-rule violation (bad state transition, missing row, …)."""


class VersionedComponentManager:
    """Base class for versioned-component CRUD + lifecycle.

    Subclasses must set ``table_name`` + ``component_type`` and
    override :meth:`canonical_bytes`. Everything else is inherited.
    """

    # ------------------------------------------------------------------ #
    # Subclass contract
    # ------------------------------------------------------------------ #

    table_name: str = ""            # e.g. 'training_set_versions'
    component_type: str = ""        # e.g. 'training_set'
    promotable: bool = True         # harness overrides to False

    # Columns that an INSERT writes beyond the standard template.
    # Keyed by column name → default value. Subclasses override.
    extra_insert_columns: Dict[str, Any] = {}

    # Columns the standard row has (used for SELECT projection).
    _standard_columns = (
        "version_id",
        "agent_id",
        "content_sha256",
        "state",
        "parent_version_id",
        "released_at",
        "deprecated_at",
        "created_at",
        "created_by",
    )

    # ------------------------------------------------------------------ #

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path

    # ------------------------------------------------------------------ #
    # Required subclass override
    # ------------------------------------------------------------------ #

    def canonical_bytes(self, payload: Any) -> bytes:
        """Return the exact bytes that get hashed.

        Subclasses implement per-type canonicalization: training sets
        sort by sample_id and emit NDJSON; prompts strip trailing
        whitespace and UTF-8-encode; routes canonical-JSON-serialize;
        etc.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    # Hashing (shared)
    # ------------------------------------------------------------------ #

    def content_hash(self, payload: Any) -> str:
        return hashlib.sha256(self.canonical_bytes(payload)).hexdigest()

    # ------------------------------------------------------------------ #
    # CRUD + lifecycle
    # ------------------------------------------------------------------ #

    def create_draft(
        self,
        agent_id: int,
        payload: Any,
        created_by: str,
        parent_version_id: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Insert a new draft version. Returns the created row."""
        now = datetime.now().isoformat()
        content_sha256 = self.content_hash(payload)

        cols = list(self._insert_columns())
        values = [
            agent_id,
            content_sha256,
            "draft",
            parent_version_id,
            None,                               # released_at
            None,                               # deprecated_at
            now,                                # created_at
            created_by,                         # created_by
        ]
        # Append subclass extras in a deterministic order.
        for col in self.extra_insert_columns:
            if extra and col in extra:
                values.append(extra[col])
            else:
                values.append(self.extra_insert_columns[col])

        placeholders = ",".join(["?"] * len(values))
        sql = f"INSERT INTO {self.table_name} ({','.join(cols)}) VALUES ({placeholders})"

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(sql, values)
            version_id = cur.lastrowid
            conn.commit()
        return self.get_by_id(version_id)

    def release(self, version_id: int) -> Dict[str, Any]:
        """draft → released. Idempotent on already-released."""
        row = self._require_version(version_id)
        if row["state"] == "released":
            return row
        if row["state"] != "draft":
            raise VersionedComponentError(
                f"Only draft versions can be released; version {version_id} is {row['state']}"
            )
        now = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                f"UPDATE {self.table_name} SET state = 'released', released_at = ? WHERE version_id = ?",
                (now, version_id),
            )
            conn.commit()
        return self.get_by_id(version_id)

    def deprecate(self, version_id: int) -> Dict[str, Any]:
        """released → deprecated. Blocks on currently-promoted."""
        row = self._require_version(version_id)
        if row["state"] == "deprecated":
            return row
        if row["state"] != "released":
            raise VersionedComponentError(
                f"Only released versions can be deprecated; version {version_id} is {row['state']}"
            )
        if self.promotable and self._is_promoted(row["agent_id"], version_id):
            raise VersionedComponentError(
                f"Cannot deprecate version {version_id}: it is currently promoted. "
                "Promote a different version first."
            )
        now = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                f"UPDATE {self.table_name} SET state = 'deprecated', deprecated_at = ? WHERE version_id = ?",
                (now, version_id),
            )
            conn.commit()
        return self.get_by_id(version_id)

    def promote(self, version_id: int, promoted_by: str) -> Dict[str, Any]:
        """Promote a released version. Auto-displaces the previous promoted."""
        if not self.promotable:
            raise VersionedComponentError(
                f"Component type {self.component_type!r} is not promotable"
            )
        row = self._require_version(version_id)
        if row["state"] != "released":
            raise VersionedComponentError(
                f"Only released versions can be promoted; version {version_id} is {row['state']}"
            )
        agent_id = row["agent_id"]
        now = datetime.now().isoformat()
        with self._connect() as conn:
            # Upsert the agent_components linkage. SQLite doesn't have ON
            # CONFLICT ... DO UPDATE on all versions, so do delete+insert.
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM agent_components WHERE agent_id = ? AND component_type = ?",
                (agent_id, self.component_type),
            )
            cur.execute(
                """
                INSERT INTO agent_components (agent_id, component_type, version_id, promoted_at, promoted_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                (agent_id, self.component_type, version_id, now, promoted_by),
            )
            conn.commit()
        return self.get_by_id(version_id)

    def unpromote(self, agent_id: int) -> None:
        """Clear the currently-promoted linkage for this agent + component."""
        if not self.promotable:
            raise VersionedComponentError(
                f"Component type {self.component_type!r} is not promotable"
            )
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM agent_components WHERE agent_id = ? AND component_type = ?",
                (agent_id, self.component_type),
            )
            conn.commit()

    # ------------------------------------------------------------------ #
    # Reads
    # ------------------------------------------------------------------ #

    def get_by_id(self, version_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                f"SELECT * FROM {self.table_name} WHERE version_id = ?",
                (version_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_versions(self, agent_id: int) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT * FROM {self.table_name} WHERE agent_id = ? ORDER BY version_id",
                (agent_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_promoted(self, agent_id: int) -> Optional[Dict[str, Any]]:
        """Return the currently-promoted version row for this agent, or None."""
        if not self.promotable:
            return None
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT v.* FROM agent_components ac
                JOIN {tbl} v ON v.version_id = ac.version_id
                WHERE ac.agent_id = ? AND ac.component_type = ?
                """.format(tbl=self.table_name),
                (agent_id, self.component_type),
            ).fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _insert_columns(self) -> List[str]:
        """Column list for the standard insert, in order."""
        cols = [
            "agent_id",
            "content_sha256",
            "state",
            "parent_version_id",
            "released_at",
            "deprecated_at",
            "created_at",
            "created_by",
        ]
        cols.extend(self.extra_insert_columns.keys())
        return cols

    def _require_version(self, version_id: int) -> Dict[str, Any]:
        row = self.get_by_id(version_id)
        if row is None:
            raise VersionedComponentError(
                f"Version {version_id} not found in {self.table_name}"
            )
        return row

    def _is_promoted(self, agent_id: int, version_id: int) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT 1 FROM agent_components
                WHERE agent_id = ? AND component_type = ? AND version_id = ?
                """,
                (agent_id, self.component_type, version_id),
            ).fetchone()
        return row is not None
