"""TB-US-051: versioned-component schema migration.

Creates the versioning + experiments tables in
``backend/db/trainingbench.db``:

- ``agents`` (seeded with ``default`` on first run)
- Six versioned-component tables: ``training_set_versions``,
  ``rag_versions``, ``adapter_versions``, ``prompt_versions``,
  ``route_versions``, ``harness_versions``
- ``agent_components`` — the currently-promoted linkage
- ``experiments`` — per TB-US-043 Q3

Called from ``main.py`` startup after ``secrets_manager.ensure_secrets()``.
Idempotent: ``CREATE TABLE IF NOT EXISTS`` throughout; migration-id
flag table short-circuits re-apply.

See ``docs/design/agent-architecture.md`` §5 (templates) and
``docs/design/sweet-spot-architecture.md`` Q3 for the authoritative
schema specs.

Note on ``query_log``: TB-US-051 R10 called for an
``ALTER TABLE query_log ADD COLUMN experiment_id INTEGER``. TB's
``query_log`` is a JSONL file, not a SQLite table (see
``backend/api/query_logger.py``), so no DDL is possible. Attaching
``experiment_id`` to query-log rows is deferred to TB-US-056
(eval-harness subsystem) where it will be added as an optional
JSON field.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path


log = logging.getLogger(__name__)

VERSIONING_DB_PATH = Path(__file__).resolve().parent.parent / "db" / "trainingbench.db"

MIGRATION_ID = "tb-us-051"
MIGRATION_ID_APPSETTINGS = "tb-us-055-appsettings"


_CREATE_SCHEMA_MIGRATIONS = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_id TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
)
"""

_CREATE_AGENTS = """
CREATE TABLE IF NOT EXISTS agents (
    agent_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    description TEXT,
    state TEXT NOT NULL CHECK(state IN ('active', 'retired')),
    created_at TEXT NOT NULL,
    retired_at TEXT
)
"""

_CREATE_TRAINING_SET_VERSIONS = """
CREATE TABLE IF NOT EXISTS training_set_versions (
    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL,
    content_sha256 TEXT NOT NULL,
    sample_count INTEGER NOT NULL DEFAULT 0,
    state TEXT NOT NULL CHECK(state IN ('draft', 'released', 'deprecated')),
    parent_version_id INTEGER,
    released_at TEXT,
    deprecated_at TEXT,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (parent_version_id) REFERENCES training_set_versions(version_id)
)
"""

_CREATE_RAG_VERSIONS = """
CREATE TABLE IF NOT EXISTS rag_versions (
    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL,
    content_sha256 TEXT NOT NULL,
    collection_name TEXT NOT NULL,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    embedding_model TEXT,
    state TEXT NOT NULL CHECK(state IN ('draft', 'released', 'deprecated')),
    parent_version_id INTEGER,
    released_at TEXT,
    deprecated_at TEXT,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (parent_version_id) REFERENCES rag_versions(version_id)
)
"""

_CREATE_ADAPTER_VERSIONS = """
CREATE TABLE IF NOT EXISTS adapter_versions (
    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL,
    content_sha256 TEXT NOT NULL,
    config_sha256 TEXT,
    training_set_version_id INTEGER,
    base_model TEXT NOT NULL,
    training_run_metadata_json TEXT,
    files_path TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('draft', 'released', 'deprecated')),
    parent_version_id INTEGER,
    released_at TEXT,
    deprecated_at TEXT,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (parent_version_id) REFERENCES adapter_versions(version_id),
    FOREIGN KEY (training_set_version_id) REFERENCES training_set_versions(version_id)
)
"""

_CREATE_PROMPT_VERSIONS = """
CREATE TABLE IF NOT EXISTS prompt_versions (
    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('draft', 'released', 'deprecated')),
    parent_version_id INTEGER,
    released_at TEXT,
    deprecated_at TEXT,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (parent_version_id) REFERENCES prompt_versions(version_id)
)
"""

_CREATE_ROUTE_VERSIONS = """
CREATE TABLE IF NOT EXISTS route_versions (
    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('draft', 'released', 'deprecated')),
    parent_version_id INTEGER,
    released_at TEXT,
    deprecated_at TEXT,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (parent_version_id) REFERENCES route_versions(version_id)
)
"""

_CREATE_HARNESS_VERSIONS = """
CREATE TABLE IF NOT EXISTS harness_versions (
    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL,
    definition_json TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('draft', 'released', 'deprecated')),
    parent_version_id INTEGER,
    released_at TEXT,
    deprecated_at TEXT,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (parent_version_id) REFERENCES harness_versions(version_id)
)
"""

_CREATE_AGENT_COMPONENTS = """
CREATE TABLE IF NOT EXISTS agent_components (
    agent_id INTEGER NOT NULL,
    component_type TEXT NOT NULL CHECK(component_type IN (
        'training_set', 'rag', 'adapter', 'prompt', 'routes', 'harness'
    )),
    version_id INTEGER NOT NULL,
    promoted_at TEXT NOT NULL,
    promoted_by TEXT NOT NULL,
    PRIMARY KEY (agent_id, component_type),
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
)
"""

_CREATE_EXPERIMENTS = """
CREATE TABLE IF NOT EXISTS experiments (
    experiment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL,
    label TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN (
        'draft', 'running', 'completed',
        'promoted', 'displaced', 'archived'
    )),
    parent_experiment_id INTEGER,
    system_prompt_version_id INTEGER,
    rag_version_id INTEGER,
    llm_identifier TEXT,
    adapter_version_id INTEGER,
    harness_version_id INTEGER,
    results_json TEXT,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    completed_at TEXT,
    promoted_at TEXT,
    displaced_at TEXT,
    archived_at TEXT,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (parent_experiment_id) REFERENCES experiments(experiment_id)
)
"""


_ALL_TABLES = [
    _CREATE_SCHEMA_MIGRATIONS,
    _CREATE_AGENTS,
    _CREATE_TRAINING_SET_VERSIONS,
    _CREATE_RAG_VERSIONS,
    _CREATE_ADAPTER_VERSIONS,
    _CREATE_PROMPT_VERSIONS,
    _CREATE_ROUTE_VERSIONS,
    _CREATE_HARNESS_VERSIONS,
    _CREATE_AGENT_COMPONENTS,
    _CREATE_EXPERIMENTS,
]


def apply_versioning_schema(db_path: Path = VERSIONING_DB_PATH) -> dict:
    """Create all versioning tables (idempotent) and seed ``default`` agent.

    Returns a summary dict for logging.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        # Short-circuit if migration already applied — still ensure tables
        # exist in case someone deleted a table out-of-band.
        for ddl in _ALL_TABLES:
            cursor.execute(ddl)

        # Seed the default agent on first run.
        cursor.execute("SELECT COUNT(*) FROM agents")
        agents_count = cursor.fetchone()[0]
        if agents_count == 0:
            cursor.execute(
                """
                INSERT INTO agents (name, display_name, description, state, created_at)
                VALUES (?, ?, ?, 'active', ?)
                """,
                (
                    "default",
                    "Default agent",
                    "Seed agent created by TB-US-051 schema migration. "
                    "Existing data will be back-attributed to this agent "
                    "by per-component migration stories (TB-US-052 through "
                    "TB-US-056).",
                    datetime.now().isoformat(),
                ),
            )

        # Record migration (idempotent via INSERT OR IGNORE).
        cursor.execute(
            "INSERT OR IGNORE INTO schema_migrations (migration_id, applied_at) VALUES (?, ?)",
            (MIGRATION_ID, datetime.now().isoformat()),
        )

        conn.commit()

    seeded_default = agents_count == 0
    return {
        "db_path": str(db_path),
        "migration_id": MIGRATION_ID,
        "seeded_default_agent": seeded_default,
    }


def migrate_appsettings_prompt_and_routes(db_path: Path = VERSIONING_DB_PATH) -> dict:
    """TB-US-055 R8/R9: migrate current AppSettings prompt + routes as v1.

    Idempotent via schema_migrations tracker row.
    Imports AppSettings lazily to keep schema_migrations side-effect-free
    at import time.
    """
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        cur = conn.cursor()
        # Idempotency check
        cur.execute(
            "SELECT 1 FROM schema_migrations WHERE migration_id = ?",
            (MIGRATION_ID_APPSETTINGS,),
        )
        if cur.fetchone():
            return {"migration_id": MIGRATION_ID_APPSETTINGS, "already_applied": True}

        # Lazy import to avoid cycles
        from api.app_settings import AppSettings, DEFAULT_RAG_PROMPT  # noqa
        from api.prompt_version_manager import PromptVersionManager
        from api.route_version_manager import RouteVersionManager

        cur_settings = AppSettings.get()
        prompt_text = cur_settings.get("rag_prompt") or DEFAULT_RAG_PROMPT
        routes = cur_settings.get("query_routes") or []

        prompt_mgr = PromptVersionManager(db_path=db_path)
        route_mgr = RouteVersionManager(db_path=db_path)

        now = datetime.now().isoformat()

        # Prompt v1 — released + promoted for agent 1
        prow = prompt_mgr.create_draft_text(agent_id=1, text=prompt_text, created_by="migration")
        prompt_mgr.release(prow["version_id"])
        prompt_mgr.promote(prow["version_id"], promoted_by="migration")

        # Routes v1 — only migrate if a non-trivial route list is present
        routes_result = None
        if routes:
            rrow = route_mgr.create_draft_routes(agent_id=1, routes=routes, created_by="migration")
            route_mgr.release(rrow["version_id"])
            route_mgr.promote(rrow["version_id"], promoted_by="migration")
            routes_result = rrow["version_id"]

        cur.execute(
            "INSERT INTO schema_migrations (migration_id, applied_at) VALUES (?, ?)",
            (MIGRATION_ID_APPSETTINGS, now),
        )
        conn.commit()

    return {
        "migration_id": MIGRATION_ID_APPSETTINGS,
        "prompt_version_id": prow["version_id"],
        "routes_version_id": routes_result,
        "prompt_chars": len(prompt_text),
        "routes_count": len(routes),
    }
