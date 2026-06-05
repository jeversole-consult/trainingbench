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
DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@localhost")
# Password hash salt. WARNING: this is a global salt — every password
# in the DB is hashed with the same value. A leaked salt + DB lets an
# attacker build a single rainbow table. Phase-6 follow-up is to move
# to per-user random salts stored alongside the hash.
PASSWORD_SALT = os.getenv("PASSWORD_SALT", "trainingbench-default-salt-change-this")


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
                    CONSTRAINT user_type_check CHECK (user_type IN ('super', 'chat', 'training'))
                )
            """)

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

            conn.commit()

            # Check if any users exist, if not create default super user
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                print("No users found. Creating default super user...")
                self.create_user(
                    username=DEFAULT_ADMIN_USERNAME,
                    password=DEFAULT_ADMIN_PASSWORD,
                    user_type="super",
                    email=DEFAULT_ADMIN_EMAIL,
                )
                print(f"Default super user created: {DEFAULT_ADMIN_USERNAME} / {DEFAULT_ADMIN_PASSWORD}")
                print("IMPORTANT: Change this password immediately!")

    def _hash_password(self, password: str) -> str:
        """
        Hash a password using SHA-256 with a global salt.

        WARNING: production deployments should switch to bcrypt or argon2
        with per-user random salts. The global salt here is a known
        weakness; configure PASSWORD_SALT env var to at least make the
        salt non-default per deployment.
        """
        return hashlib.sha256(f"{PASSWORD_SALT}{password}".encode()).hexdigest()

    def create_user(
        self,
        username: str,
        password: str,
        user_type: str,
        email: Optional[str] = None
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
                    INSERT INTO users (username, password_hash, user_type, email, created_at, active)
                    VALUES (?, ?, ?, ?, ?, 1)
                """, (username, password_hash, user_type, email, created_at))
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
                SELECT id, username, user_type, email, created_at, active
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
                    "created_at": row['created_at']
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
