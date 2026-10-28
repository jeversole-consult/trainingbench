"""
Application-level runtime settings, persisted to a JSON file.

Tracks `demo_mode`, `active_database`, `rag_prompt` (user-editable
system prompt template), and `query_routes` (user-configurable
retrieval augmentation rules). The file is the source of truth at
request time; environment variables only seed the file on first run.

TB-US-033: Direct port of stalite3's rag_prompt + query_routes
surface onto TB master. Generic defaults (no Stalite-specific
content).
"""

import json
import os
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional


# Tunable file paths (env-overridable).
SETTINGS_PATH = Path(os.getenv("APP_SETTINGS_PATH", "app_settings.json"))
AUDIT_LOG_PATH = Path(os.getenv("DEMO_MODE_AUDIT_LOG_PATH", "logs/demo_mode_audit.jsonl"))
RAG_PROMPT_AUDIT_LOG_PATH = Path(os.getenv("RAG_PROMPT_AUDIT_LOG_PATH", "logs/rag_prompt_audit.jsonl"))
QUERY_ROUTES_AUDIT_LOG_PATH = Path(os.getenv("QUERY_ROUTES_AUDIT_LOG_PATH", "logs/query_routes_audit.jsonl"))


# TB-US-033: Generic default RAG prompt template. Deployments can override
# via `PUT /settings/rag-prompt`. Required placeholders: {context}, {question}.
DEFAULT_RAG_PROMPT = """Use the following context from technical documents to answer the question. If the context contains relevant information, use it. Otherwise, answer from your training.

Context:
{context}

Question: {question}

Answer:"""

# TB-US-033: Default query routes list. Empty — operators configure per
# deployment via `PUT /settings/query-routes`. Each route detects a
# category of question by regex patterns and augments the similarity-
# search string to bias retrieval toward the matching content category.
DEFAULT_QUERY_ROUTES: List[Dict] = []


class AppSettings:
    """Loads, caches, and persists application-level runtime settings."""

    _lock = Lock()
    _cache: Dict = None

    @classmethod
    def _seed_default(cls) -> Dict:
        """Build the initial settings dict from environment variables."""
        env_demo = os.getenv("DEMO_MODE", "false").lower() == "true"
        return {
            "demo_mode": env_demo,
            "active_database": None,
            "rag_prompt": DEFAULT_RAG_PROMPT,
            "rag_prompt_saved_at": None,
            "rag_prompt_saved_by": None,
            "query_routes": DEFAULT_QUERY_ROUTES,
            "query_routes_saved_at": None,
            "query_routes_saved_by": None,
        }

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

    # TB-US-033: rag_prompt accessors + setter + metadata

    @classmethod
    def rag_prompt(cls) -> str:
        """Return the current RAG prompt template, falling back to the default."""
        value = cls.get().get("rag_prompt")
        if isinstance(value, str) and value:
            return value
        return DEFAULT_RAG_PROMPT

    @classmethod
    def rag_prompt_meta(cls) -> Dict:
        """Return save metadata for the current rag_prompt (saved_at, saved_by)."""
        s = cls.get()
        return {
            "saved_at": s.get("rag_prompt_saved_at"),
            "saved_by": s.get("rag_prompt_saved_by"),
        }

    @classmethod
    def set_rag_prompt(cls, value: str, username: str) -> Dict:
        """Persist a new RAG prompt template and append an audit entry."""
        saved_at = datetime.utcnow().isoformat() + "Z"
        with cls._lock:
            if cls._cache is None:
                cls._cache = cls._load()
            old_value = cls._cache.get("rag_prompt") or DEFAULT_RAG_PROMPT
            cls._cache["rag_prompt"] = value
            cls._cache["rag_prompt_saved_at"] = saved_at
            cls._cache["rag_prompt_saved_by"] = username
            try:
                with SETTINGS_PATH.open("w") as f:
                    json.dump(cls._cache, f, indent=2)
            except OSError as e:
                print(f"app_settings: failed to write settings: {e}")
                raise

        cls._append_rag_prompt_audit(username, old_value, value)
        return {
            "prompt": value,
            "default": DEFAULT_RAG_PROMPT,
            "saved_at": saved_at,
            "saved_by": username,
        }

    # TB-US-033: query_routes accessors + setter + metadata

    @classmethod
    def query_routes(cls) -> List[Dict]:
        """Return the current list of query routes, falling back to defaults."""
        value = cls.get().get("query_routes")
        if isinstance(value, list):
            return value
        return list(DEFAULT_QUERY_ROUTES)

    @classmethod
    def query_routes_meta(cls) -> Dict:
        """Return save metadata for the current query_routes list."""
        s = cls.get()
        return {
            "saved_at": s.get("query_routes_saved_at"),
            "saved_by": s.get("query_routes_saved_by"),
        }

    @classmethod
    def set_query_routes(cls, routes: List[Dict], username: str) -> Dict:
        """Persist a new query routes list and append an audit entry."""
        saved_at = datetime.utcnow().isoformat() + "Z"
        with cls._lock:
            if cls._cache is None:
                cls._cache = cls._load()
            old_routes = cls._cache.get("query_routes") or list(DEFAULT_QUERY_ROUTES)
            cls._cache["query_routes"] = routes
            cls._cache["query_routes_saved_at"] = saved_at
            cls._cache["query_routes_saved_by"] = username
            try:
                with SETTINGS_PATH.open("w") as f:
                    json.dump(cls._cache, f, indent=2)
            except OSError as e:
                print(f"app_settings: failed to write settings: {e}")
                raise

        cls._append_query_routes_audit(username, old_routes, routes)
        return {
            "routes": routes,
            "defaults": list(DEFAULT_QUERY_ROUTES),
            "saved_at": saved_at,
            "saved_by": username,
        }

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

    @staticmethod
    def _append_rag_prompt_audit(username: str, old_value: str, new_value: str) -> None:
        """Append a JSON line to the RAG prompt audit log."""
        RAG_PROMPT_AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "username": username,
            "old_prompt": old_value,
            "new_prompt": new_value,
        }
        try:
            with RAG_PROMPT_AUDIT_LOG_PATH.open("a") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError as e:
            print(f"app_settings: failed to append rag-prompt audit entry: {e}")

    @staticmethod
    def _append_query_routes_audit(username: str, old_routes: List[Dict], new_routes: List[Dict]) -> None:
        """Append a JSON line to the query-routes audit log."""
        QUERY_ROUTES_AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "username": username,
            "old_routes": old_routes,
            "new_routes": new_routes,
        }
        try:
            with QUERY_ROUTES_AUDIT_LOG_PATH.open("a") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError as e:
            print(f"app_settings: failed to append query-routes audit entry: {e}")
