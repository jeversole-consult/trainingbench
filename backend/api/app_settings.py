"""
Application-level runtime settings, persisted to a JSON file.

Currently tracks `demo_mode`. The file is the source of truth at request time;
the `DEMO_MODE` environment variable only seeds the file on first run.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, Optional


SETTINGS_PATH = Path("app_settings.json")
AUDIT_LOG_PATH = Path("logs") / "demo_mode_audit.jsonl"


class AppSettings:
    """Loads, caches, and persists application-level runtime settings."""

    _lock = Lock()
    _cache: Dict = None

    @classmethod
    def _seed_default(cls) -> Dict:
        """Build the initial settings dict from environment variables."""
        env_demo = os.getenv("DEMO_MODE", "false").lower() == "true"
        return {"demo_mode": env_demo, "active_database": None}

    @classmethod
    def _load(cls) -> Dict:
        """Read settings from disk, seeding the file on first run."""
        if SETTINGS_PATH.exists():
            try:
                with SETTINGS_PATH.open("r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                print(f"app_settings: failed to read {SETTINGS_PATH}: {e}; re-seeding from env")

        defaults = cls._seed_default()
        try:
            with SETTINGS_PATH.open("w") as f:
                json.dump(defaults, f, indent=2)
        except OSError as e:
            print(f"app_settings: failed to write seed file: {e}")
        return defaults

    @classmethod
    def get(cls) -> Dict:
        """Return current settings, loading from disk on first call."""
        with cls._lock:
            if cls._cache is None:
                cls._cache = cls._load()
            return dict(cls._cache)

    @classmethod
    def demo_mode(cls) -> bool:
        """Convenience accessor for the demo_mode flag."""
        return bool(cls.get().get("demo_mode", False))

    @classmethod
    def set_demo_mode(cls, value: bool, username: str) -> Dict:
        """Persist a new demo_mode value and append an audit entry."""
        with cls._lock:
            if cls._cache is None:
                cls._cache = cls._load()
            old_value = bool(cls._cache.get("demo_mode", False))
            new_value = bool(value)
            cls._cache["demo_mode"] = new_value
            try:
                with SETTINGS_PATH.open("w") as f:
                    json.dump(cls._cache, f, indent=2)
            except OSError as e:
                print(f"app_settings: failed to write settings: {e}")
                raise

        cls._append_audit(username, old_value, new_value)
        return {"demo_mode": new_value, "previous": old_value}

    @classmethod
    def active_database(cls) -> Optional[str]:
        """Return the persisted active database id, or None if never set."""
        value = cls.get().get("active_database")
        return value if isinstance(value, str) and value else None

    @classmethod
    def set_active_database(cls, db_id: Optional[str]) -> None:
        """Persist the active database id. Pass None to clear."""
        with cls._lock:
            if cls._cache is None:
                cls._cache = cls._load()
            cls._cache["active_database"] = db_id
            try:
                with SETTINGS_PATH.open("w") as f:
                    json.dump(cls._cache, f, indent=2)
            except OSError as e:
                print(f"app_settings: failed to persist active_database: {e}")
                raise

    @staticmethod
    def _append_audit(username: str, old_value: bool, new_value: bool) -> None:
        """Append a JSON line to the demo-mode audit log."""
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "username": username,
            "from": "demo" if old_value else "live",
            "to": "demo" if new_value else "live",
        }
        try:
            with AUDIT_LOG_PATH.open("a") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError as e:
            print(f"app_settings: failed to append audit entry: {e}")
