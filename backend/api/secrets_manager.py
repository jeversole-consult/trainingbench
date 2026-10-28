"""TB-US-050: auto-generated SECRET_KEY + PASSWORD_SALT.

On first boot the pair is generated and persisted to
``backend/db/.secrets`` (JSON, chmod 600, gitignored). Subsequent
boots read from that file. Env-var overrides (``SECRET_KEY`` and
``PASSWORD_SALT``) always win so dev/CI setups can inject their own.

**Lockout avoidance.** PASSWORD_SALT regeneration is destructive —
all existing password hashes become invalid. When no secrets file
exists AND the users table already has rows, we preserve the legacy
hardcoded salt so existing credentials keep working. Fresh installs
(empty users table) get a freshly generated salt.
"""

from __future__ import annotations

import json
import os
import secrets as _secrets
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


SECRETS_FILE = Path(__file__).resolve().parent.parent / "db" / ".secrets"

# Legacy hardcoded salt. Pre-TB-US-050 TB installs used this exact
# string as the PASSWORD_SALT default, so any existing user password
# hash was computed with it. Preserved so upgrades don't lock anyone
# out.
LEGACY_PASSWORD_SALT = "trainingbench-default-salt-change-this"

# Where UserManager stores accounts. secrets_manager peeks at it to
# decide whether a fresh salt is safe to generate.
USERS_DB_PATH = os.getenv("USERS_DB_PATH", "users.db")


_cache: Optional[Dict[str, str]] = None


def _read_file() -> Optional[Dict[str, str]]:
    if not SECRETS_FILE.exists():
        return None
    try:
        return json.loads(SECRETS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_file(secrets_dict: Dict[str, str]) -> None:
    """Atomic write: temp file + chmod 600 + rename."""
    SECRETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = SECRETS_FILE.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(secrets_dict, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    tmp.chmod(0o600)
    tmp.replace(SECRETS_FILE)


def _users_table_has_rows() -> bool:
    """Return True if the users table exists and has at least one row."""
    try:
        with sqlite3.connect(USERS_DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM sqlite_master "
                "WHERE type='table' AND name='users'"
            )
            if cur.fetchone()[0] == 0:
                return False
            cur.execute("SELECT COUNT(*) FROM users")
            return cur.fetchone()[0] > 0
    except sqlite3.Error:
        return False


def ensure_secrets() -> Dict[str, str]:
    """Load existing secrets or generate+persist on first boot.

    Returns the dict so callers can introspect, but normal use is
    via :func:`get_secret_key` / :func:`get_password_salt`.
    """
    global _cache
    if _cache is not None:
        return _cache

    existing = _read_file()
    if existing and "SECRET_KEY" in existing and "PASSWORD_SALT" in existing:
        _cache = existing
        print(f"[secrets] loaded from {SECRETS_FILE}")
        return _cache

    # Generate what's missing. SECRET_KEY is always safe to generate
    # (invalidates sessions on rotation). PASSWORD_SALT is destructive
    # on existing installs; preserve legacy value in that case.
    new_secret_key = _secrets.token_urlsafe(32)
    if _users_table_has_rows():
        new_password_salt = LEGACY_PASSWORD_SALT
        salt_source = "legacy-preserved"
    else:
        new_password_salt = _secrets.token_urlsafe(32)
        salt_source = "generated-fresh"

    payload = {
        "SECRET_KEY": new_secret_key,
        "PASSWORD_SALT": new_password_salt,
        "created_at": datetime.now().isoformat(),
    }
    _write_file(payload)
    _cache = payload
    print(f"[secrets] generated and wrote {SECRETS_FILE} (salt={salt_source})")
    return _cache


def get_secret_key() -> str:
    """Return SECRET_KEY (env wins over file)."""
    env_val = os.getenv("SECRET_KEY")
    if env_val:
        return env_val
    return ensure_secrets()["SECRET_KEY"]


def get_password_salt() -> str:
    """Return PASSWORD_SALT (env wins over file)."""
    env_val = os.getenv("PASSWORD_SALT")
    if env_val:
        return env_val
    return ensure_secrets()["PASSWORD_SALT"]
