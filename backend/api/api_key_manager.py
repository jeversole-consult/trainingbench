"""TB-US-063: per-user API keys with hash-at-rest storage.

Replaces the single shared ``ADMIN_API_KEY`` env-var pattern with a
proper per-key record: each key is a row in the ``api_keys`` table
with a human-readable label, SHA-256 hashed secret, prefix for
display, creator attribution, and a revocation state.

Key format: ``tbk_<32-char urlsafe-base64>`` (36 chars total). The
``tbk_`` prefix lets log scrubbers detect leaked keys. The raw key
is returned exactly once at create time and NEVER retrievable
thereafter — only its hash and prefix persist.

Co-located in ``users.db`` with the users table so the admin
surfaces stay together.
"""

from __future__ import annotations

import hashlib
import os
import secrets as _secrets
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional


KEY_PREFIX = "tbk_"
PREFIX_DISPLAY_LEN = 12   # tbk_ + 8 chars of body


class ApiKeyError(RuntimeError):
    """Business-rule violation on API-key lifecycle."""


class ApiKeyManager:
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path
        self._init_table()

    def _init_table(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    label TEXT NOT NULL,
                    key_hash TEXT NOT NULL UNIQUE,
                    key_prefix TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    last_used_at TEXT,
                    revoked_at TEXT
                )
            """)
            conn.commit()

    # ------------------------------------------------------------------ #
    # Hashing
    # ------------------------------------------------------------------ #

    @staticmethod
    def _hash(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @staticmethod
    def _generate_raw_key() -> str:
        return KEY_PREFIX + _secrets.token_urlsafe(24)

    # ------------------------------------------------------------------ #
    # CRUD
    # ------------------------------------------------------------------ #

    def create_key(self, label: str, created_by: str) -> Dict[str, Any]:
        """Create a new API key. Returns row dict WITH raw key — once only."""
        if not label or not label.strip():
            raise ApiKeyError("label is required")
        raw_key = self._generate_raw_key()
        key_hash = self._hash(raw_key)
        key_prefix = raw_key[:PREFIX_DISPLAY_LEN]
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO api_keys (label, key_hash, key_prefix, created_at, created_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                (label.strip(), key_hash, key_prefix, now, created_by),
            )
            key_id = cur.lastrowid
            conn.commit()
        return {
            "id": key_id,
            "label": label.strip(),
            "key_prefix": key_prefix,
            "created_at": now,
            "created_by": created_by,
            "last_used_at": None,
            "revoked_at": None,
            "raw_key": raw_key,     # one-time field; never retrievable again
        }

    def list_keys(self, include_revoked: bool = True) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if include_revoked:
                rows = conn.execute(
                    "SELECT id, label, key_prefix, created_at, created_by, "
                    "last_used_at, revoked_at FROM api_keys ORDER BY id DESC"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, label, key_prefix, created_at, created_by, "
                    "last_used_at, revoked_at FROM api_keys "
                    "WHERE revoked_at IS NULL ORDER BY id DESC"
                ).fetchall()
        return [dict(r) for r in rows]

    def get_by_id(self, key_id: int) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT id, label, key_prefix, created_at, created_by, "
                "last_used_at, revoked_at FROM api_keys WHERE id = ?",
                (key_id,),
            ).fetchone()
        return dict(row) if row else None

    def revoke(self, key_id: int) -> Dict:
        row = self.get_by_id(key_id)
        if row is None:
            raise ApiKeyError(f"API key {key_id} not found")
        if row["revoked_at"]:
            return row  # already revoked, idempotent
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE api_keys SET revoked_at = ? WHERE id = ?",
                (now, key_id),
            )
            conn.commit()
        return self.get_by_id(key_id)

    # ------------------------------------------------------------------ #
    # Authentication path
    # ------------------------------------------------------------------ #

    def verify(self, raw_key: str) -> Optional[Dict]:
        """Return key row if raw_key matches an active key, else None.

        Updates ``last_used_at`` on match. Case-sensitive. Does NOT
        return the key_hash to callers.
        """
        if not raw_key or not raw_key.startswith(KEY_PREFIX):
            return None
        key_hash = self._hash(raw_key)
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT id, label, key_prefix, created_at, created_by, "
                "last_used_at, revoked_at FROM api_keys "
                "WHERE key_hash = ? AND revoked_at IS NULL",
                (key_hash,),
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                "UPDATE api_keys SET last_used_at = ? WHERE id = ?",
                (now, row["id"]),
            )
            conn.commit()
        return dict(row)
