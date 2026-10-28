#!/usr/bin/env python3
"""
User management system for multi-user support.
Handles user authentication, roles, and database operations.
"""

import os
import sqlite3
import hashlib
import secrets
from typing import Optional, Dict, List
from datetime import datetime
from pathlib import Path


# Tunable defaults (env-overridable). Constructor / method arguments still win.
DEFAULT_USERS_DB_PATH = os.getenv("USERS_DB_PATH", "users.db")
DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "changeme")
# admin@localhost is a deliberately generic placeholder so no install
# ships with someone else's address. Set DEFAULT_ADMIN_EMAIL in your
# .env to your own administrative address for this install.
DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@localhost")
# Password hash salt. WARNING: this is a global salt — every password
# in the DB is hashed with the same value. A leaked salt + DB lets an
# attacker build a single rainbow table. Phase-6 follow-up is to move
# to per-user random salts stored alongside the hash.
# TB-US-050: the actual salt value comes from secrets_manager at hash
# time so the auto-generated / env / legacy-preserved value wins.
from api.secrets_manager import get_password_salt as _get_password_salt

# TB-US-049: path for the first-run admin credentials file. Written on
# fresh install when DEFAULT_ADMIN_PASSWORD is unset; deleted on first
# successful password change.
FIRST_RUN_ADMIN_FILE = Path("logs/first-run-admin.txt")


def _write_first_run_admin_file(username: str, password: str) -> None:
    """Write first-run admin credentials to a chmod-600 file atomically."""
    FIRST_RUN_ADMIN_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = FIRST_RUN_ADMIN_FILE.with_suffix(".tmp")
    tmp.write_text(
        f"username: {username}\npassword: {password}\n"
        f"generated_at: {datetime.now().isoformat()}\n"
        "You will be forced to change this password on first login.\n"
        "This file is auto-deleted after your first password change.\n",
        encoding="utf-8",
    )
    tmp.chmod(0o600)
    tmp.replace(FIRST_RUN_ADMIN_FILE)


def _delete_first_run_admin_file() -> None:
    """Remove the first-run admin credentials file if present."""
    try:
        FIRST_RUN_ADMIN_FILE.unlink(missing_ok=True)
    except OSError:
        pass


class UserManager:
    """
    Manages users, authentication, and user types/roles.

    User Types:
    - super: Full access to all features
    - chat: Simplified Q&A interface with separate logging
    - training: Q&A with training feedback and session management
    """

    USER_TYPES = ['super', 'chat', 'training']

    def __init__(self, db_path: str = DEFAULT_USERS_DB_PATH):
        """Initialize user manager with database."""
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Create users table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    user_type TEXT NOT NULL,
                    email TEXT,
                    created_at TEXT NOT NULL,
                    last_login TEXT,
                    active INTEGER DEFAULT 1,
                    must_change_password INTEGER NOT NULL DEFAULT 0,
                    CONSTRAINT user_type_check CHECK (user_type IN ('super', 'chat', 'training'))
                )
            """)

            # TB-US-049: add must_change_password to existing installs
            # (safe to run every start; sqlite ALTER TABLE ADD COLUMN is
            # idempotent only via try/except on duplicate column error).
            try:
                cursor.execute(
                    "ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0"
                )
            except sqlite3.OperationalError:
                pass

            # TB-US-059: add welcome_banner_dismissed. Idempotent on repeat.
            try:
                cursor.execute(
                    "ALTER TABLE users ADD COLUMN welcome_banner_dismissed INTEGER NOT NULL DEFAULT 0"
                )
            except sqlite3.OperationalError:
                pass

            # Training sessions table (for future use)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS training_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_name TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    closed_at TEXT,
                    status TEXT DEFAULT 'active',
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    CONSTRAINT status_check CHECK (status IN ('active', 'closed'))
                )
            """)

            # TB-US-017: admin audit log. Every admin action writes one
            # row here before returning its response. Failed attempts also
            # log with success=0 and the error reason in details.
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT,
                    details TEXT,
                    success INTEGER NOT NULL DEFAULT 1
                )
            """)

            conn.commit()

            # Check if any users exist, if not create default super user.
            # TB-US-049: if DEFAULT_ADMIN_PASSWORD env var is unset, generate
            # a random 24-char passphrase, flag must_change_password=1, and
            # write credentials to logs/first-run-admin.txt (chmod 600) so
            # the operator can recover them if stdout was missed.
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                env_password = os.getenv("DEFAULT_ADMIN_PASSWORD")
                if env_password:
                    generated_password = env_password
                    must_change = 0
                else:
                    generated_password = secrets.token_urlsafe(18)
                    must_change = 1

                print("No users found. Creating default super user...")
                self.create_user(
                    username=DEFAULT_ADMIN_USERNAME,
                    password=generated_password,
                    user_type="super",
                    email=DEFAULT_ADMIN_EMAIL,
                    must_change_password=must_change,
                )

                if must_change:
                    banner = (
                        "\n" + "=" * 60 + "\n"
                        "TB-US-049 FIRST-RUN ADMIN CREDENTIALS\n"
                        + "=" * 60 + "\n"
                        f"  username: {DEFAULT_ADMIN_USERNAME}\n"
                        f"  password: {generated_password}\n"
                        "You will be forced to change this password on\n"
                        "first login. Credentials also written to\n"
                        "logs/first-run-admin.txt (chmod 600). That file\n"
                        "is auto-deleted after your first password change.\n"
                        + "=" * 60 + "\n"
                    )
                    print(banner)
                    _write_first_run_admin_file(DEFAULT_ADMIN_USERNAME, generated_password)
                else:
                    print(f"Default super user created: {DEFAULT_ADMIN_USERNAME} / {generated_password}")
                    print("IMPORTANT: Change this password immediately!")

    def _hash_password(self, password: str) -> str:
        """
        Hash a password using SHA-256 with a global salt.

        WARNING: production deployments should switch to bcrypt or argon2
        with per-user random salts. The global salt here is a known
        weakness; configure PASSWORD_SALT env var to at least make the
        salt non-default per deployment.
        """
        return hashlib.sha256(f"{_get_password_salt()}{password}".encode()).hexdigest()

    def create_user(
        self,
        username: str,
        password: str,
        user_type: str,
        email: Optional[str] = None,
        must_change_password: int = 0,
    ) -> Dict:
        """
        Create a new user.

        Args:
            username: Unique username
            password: Plain text password (will be hashed)
            user_type: One of 'super', 'chat', 'training'
            email: Optional email address

        Returns:
            Dict with status and user info or error
        """
        if user_type not in self.USER_TYPES:
            return {
                "status": "error",
                "error": f"Invalid user type. Must be one of: {', '.join(self.USER_TYPES)}"
            }

        password_hash = self._hash_password(password)
        created_at = datetime.now().isoformat()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (username, password_hash, user_type, email, created_at, active, must_change_password)
                    VALUES (?, ?, ?, ?, ?, 1, ?)
                """, (username, password_hash, user_type, email, created_at, int(must_change_password)))
                conn.commit()
                user_id = cursor.lastrowid

            return {
                "status": "success",
                "user_id": user_id,
                "username": username,
                "user_type": user_type
            }
        except sqlite3.IntegrityError:
            return {
                "status": "error",
                "error": f"Username '{username}' already exists"
            }

    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """
        Authenticate a user.

        Args:
            username: Username
            password: Plain text password

        Returns:
            User info dict if authenticated, None otherwise
        """
        password_hash = self._hash_password(password)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, username, user_type, email, created_at, active, must_change_password
                FROM users
                WHERE username = ? AND password_hash = ? AND active = 1
            """, (username, password_hash))

            row = cursor.fetchone()

            if row:
                # Update last login
                cursor.execute("""
                    UPDATE users SET last_login = ? WHERE id = ?
                """, (datetime.now().isoformat(), row['id']))
                conn.commit()

                return {
                    "id": row['id'],
                    "username": row['username'],
                    "user_type": row['user_type'],
                    "email": row['email'],
                    "created_at": row['created_at'],
                    "must_change_password": bool(row['must_change_password']),
                }

            return None

    def get_user(self, username: str) -> Optional[Dict]:
        """
        Get user information by username.

        Args:
            username: Username to look up

        Returns:
            User info dict or None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, username, user_type, email, created_at, last_login, active
                FROM users
                WHERE username = ?
            """, (username,))

            row = cursor.fetchone()

            if row:
                return {
                    "id": row['id'],
                    "username": row['username'],
                    "user_type": row['user_type'],
                    "email": row['email'],
                    "created_at": row['created_at'],
                    "last_login": row['last_login'],
                    "active": bool(row['active'])
                }

            return None

    def list_users(self) -> List[Dict]:
        """
        List all users.

        Returns:
            List of user info dicts
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, username, user_type, email, created_at, last_login, active
                FROM users
                ORDER BY created_at DESC
            """)

            users = []
            for row in cursor.fetchall():
                users.append({
                    "id": row['id'],
                    "username": row['username'],
                    "user_type": row['user_type'],
                    "email": row['email'],
                    "created_at": row['created_at'],
                    "last_login": row['last_login'],
                    "active": bool(row['active'])
                })

            return users

    def update_user_type(self, username: str, new_type: str) -> Dict:
        """
        Update a user's type/role.

        Args:
            username: Username to update
            new_type: New user type

        Returns:
            Status dict
        """
        if new_type not in self.USER_TYPES:
            return {
                "status": "error",
                "error": f"Invalid user type. Must be one of: {', '.join(self.USER_TYPES)}"
            }

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET user_type = ? WHERE username = ?
            """, (new_type, username))
            conn.commit()

            if cursor.rowcount > 0:
                return {"status": "success", "username": username, "new_type": new_type}
            else:
                return {"status": "error", "error": f"User '{username}' not found"}

    def deactivate_user(self, username: str) -> Dict:
        """
        Deactivate a user (soft delete).

        Args:
            username: Username to deactivate

        Returns:
            Status dict
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET active = 0 WHERE username = ?
            """, (username,))
            conn.commit()

            if cursor.rowcount > 0:
                return {"status": "success", "username": username}
            else:
                return {"status": "error", "error": f"User '{username}' not found"}

    def change_password(self, username: str, new_password: str) -> Dict:
        """
        Change a user's password.

        Args:
            username: Username
            new_password: New plain text password

        Returns:
            Status dict
        """
        password_hash = self._hash_password(new_password)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET password_hash = ? WHERE username = ?
            """, (password_hash, username))
            conn.commit()

            if cursor.rowcount > 0:
                return {"status": "success", "username": username}
            else:
                return {"status": "error", "error": f"User '{username}' not found"}

    def welcome_banner_dismissed(self, username: str) -> bool:
        """TB-US-059: return True if the user has dismissed the welcome banner."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT welcome_banner_dismissed FROM users WHERE username = ?",
                (username,),
            )
            row = cursor.fetchone()
            return bool(row[0]) if row else False

    def set_welcome_banner_dismissed(self, username: str, dismissed: bool) -> Dict:
        """TB-US-059: flip the dismissal flag. Idempotent."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET welcome_banner_dismissed = ? WHERE username = ?",
                (1 if dismissed else 0, username),
            )
            conn.commit()
            if cursor.rowcount == 0:
                return {"status": "error", "error": f"User '{username}' not found"}
            return {"status": "success", "username": username, "dismissed": bool(dismissed)}

    def must_change_password(self, username: str) -> bool:
        """TB-US-049: return True if the user is flagged for forced password change."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT must_change_password FROM users WHERE username = ?",
                (username,),
            )
            row = cursor.fetchone()
            return bool(row[0]) if row else False

    def self_change_password(
        self, username: str, current_password: str, new_password: str
    ) -> Dict:
        """TB-US-049: user-initiated password change.

        Verifies the current password, writes the new hash, clears
        must_change_password, and deletes logs/first-run-admin.txt if
        present. Enforces a 10-char minimum on the new password.
        """
        if len(new_password) < 10:
            return {
                "status": "error",
                "error": "New password must be at least 10 characters",
            }

        current_hash = self._hash_password(current_password)
        new_hash = self._hash_password(new_password)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM users WHERE username = ? AND password_hash = ? AND active = 1",
                (username, current_hash),
            )
            if not cursor.fetchone():
                return {"status": "error", "error": "Current password is incorrect"}

            cursor.execute(
                "UPDATE users SET password_hash = ?, must_change_password = 0 WHERE username = ?",
                (new_hash, username),
            )
            conn.commit()

        _delete_first_run_admin_file()
        return {"status": "success", "username": username}

    # TB-US-017: user management v2 additions

    def reactivate_user(self, username: str) -> Dict:
        """Re-enable a previously-deactivated user. Sets active=1.

        Returns status 'error' if the user doesn't exist or is already active.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT active FROM users WHERE username = ?", (username,)
            )
            row = cursor.fetchone()
            if not row:
                return {"status": "error", "error": f"User '{username}' not found"}
            if row[0] == 1:
                return {"status": "error", "error": f"User '{username}' is already active"}

            cursor.execute(
                "UPDATE users SET active = 1 WHERE username = ?", (username,)
            )
            conn.commit()
            return {"status": "success", "username": username}

    def update_email(self, username: str, email: Optional[str]) -> Dict:
        """Update a user's email. Pass None or empty string to clear."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT email FROM users WHERE username = ?", (username,)
            )
            row = cursor.fetchone()
            if not row:
                return {"status": "error", "error": f"User '{username}' not found"}
            old_email = row[0]
            # Normalize empty string → None
            new_email = email if (email and email.strip()) else None
            cursor.execute(
                "UPDATE users SET email = ? WHERE username = ?",
                (new_email, username),
            )
            conn.commit()
            return {
                "status": "success",
                "username": username,
                "old_email": old_email,
                "new_email": new_email,
            }

    def hard_delete_user(self, username: str) -> Dict:
        """Permanently delete a user row from the users table.

        Distinct from deactivate_user (soft delete). Use with caution —
        this removes the row entirely including created_at and
        last_login history.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_type, email, active FROM users WHERE username = ?",
                (username,),
            )
            row = cursor.fetchone()
            if not row:
                return {"status": "error", "error": f"User '{username}' not found"}
            snapshot = {
                "user_type": row[0],
                "email": row[1],
                "active": row[2],
            }
            cursor.execute(
                "DELETE FROM users WHERE username = ?", (username,)
            )
            conn.commit()
            return {
                "status": "success",
                "username": username,
                "deleted_snapshot": snapshot,
            }

    def append_audit(
        self,
        actor: str,
        action: str,
        target: Optional[str] = None,
        details: Optional[Dict] = None,
        success: bool = True,
    ) -> None:
        """Append one row to admin_audit. Best-effort — never raises to caller.

        Args:
            actor: username of the authenticated caller performing the action
            action: short identifier like 'create', 'delete', 'deactivate',
                'activate', 'change_type', 'reset_password', 'update_email',
                'bulk_<action>', etc.
            target: username acted on; None for aggregate/bulk entries
            details: free-form dict (serialized to JSON) — e.g. before/after
                snapshot, bulk parameters, failure reason
            success: True on success; False on failure (with reason in details)
        """
        import json as _json
        timestamp = datetime.utcnow().isoformat() + "Z"
        details_blob = _json.dumps(details) if details is not None else None
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO admin_audit
                       (timestamp, actor, action, target, details, success)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (timestamp, actor, action, target, details_blob, 1 if success else 0),
                )
                conn.commit()
        except Exception as e:
            # Audit logging must never block the main action. Log to stdout.
            print(f"user_manager.append_audit: failed to write audit row ({e})")

    def get_audit_log(self, limit: int = 200) -> List[Dict]:
        """Return admin_audit entries newest-first, up to `limit` rows.

        Each row has `details` deserialized from JSON when present.
        """
        import json as _json
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, timestamp, actor, action, target, details, success
                   FROM admin_audit
                   ORDER BY id DESC
                   LIMIT ?""",
                (limit,),
            )
            rows = cursor.fetchall()
            out = []
            for r in rows:
                entry = dict(r)
                # Parse details JSON if present
                if entry.get("details"):
                    try:
                        entry["details"] = _json.loads(entry["details"])
                    except (ValueError, TypeError):
                        pass  # Leave as string if not valid JSON
                entry["success"] = bool(entry["success"])
                out.append(entry)
            return out


# CLI for user management
if __name__ == "__main__":
    import sys

    um = UserManager()

    if len(sys.argv) < 2:
        print("User Management CLI")
        print("===================")
        print("\nCommands:")
        print("  python user_manager.py list")
        print("  python user_manager.py create <username> <password> <type>")
        print("  python user_manager.py changetype <username> <new_type>")
        print("  python user_manager.py changepass <username> <new_password>")
        print("  python user_manager.py deactivate <username>")
        print("\nUser types: super, chat, training")
        sys.exit(0)

    command = sys.argv[1]

    if command == "list":
        users = um.list_users()
        print(f"\nTotal users: {len(users)}\n")
        for user in users:
            status = "ACTIVE" if user['active'] else "INACTIVE"
            print(f"  [{status}] {user['username']:15} | Type: {user['user_type']:10} | Created: {user['created_at'][:10]}")

    elif command == "create" and len(sys.argv) >= 5:
        username, password, user_type = sys.argv[2], sys.argv[3], sys.argv[4]
        result = um.create_user(username, password, user_type)
        print(result)

    elif command == "changetype" and len(sys.argv) >= 4:
        username, new_type = sys.argv[2], sys.argv[3]
        result = um.update_user_type(username, new_type)
        print(result)

    elif command == "changepass" and len(sys.argv) >= 4:
        username, new_password = sys.argv[2], sys.argv[3]
        result = um.change_password(username, new_password)
        print(result)

    elif command == "deactivate" and len(sys.argv) >= 3:
        username = sys.argv[2]
        result = um.deactivate_user(username)
        print(result)

    else:
        print("Invalid command. Run without arguments for help.")
