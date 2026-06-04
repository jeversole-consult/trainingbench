#!/usr/bin/env python3
"""
Session tracking system for monitoring user login/logout events.
Tracks session duration, IP addresses, and user agents.
"""

import sqlite3
from typing import Optional, Dict, List
from datetime import datetime
from pathlib import Path


class SessionTracker:
    """
    Tracks user login and logout events with detailed session information.

    Features:
    - Records login time, IP address, user agent
    - Records logout time and calculates session duration
    - Tracks active sessions
    - Provides session history for users
    - Supports querying by user, date range, and session status
    """

    def __init__(self, db_path: str = "sessions.db"):
        """Initialize session tracker with database."""
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Create sessions table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    user_type TEXT NOT NULL,
                    session_token TEXT NOT NULL,
                    login_time TEXT NOT NULL,
                    logout_time TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    duration_seconds INTEGER,
                    status TEXT DEFAULT 'active',
                    CONSTRAINT status_check CHECK (status IN ('active', 'closed', 'expired'))
                )
            """)

            # Create indexes for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id
                ON sessions(user_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_username
                ON sessions(username)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_status
                ON sessions(status)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_login_time
                ON sessions(login_time)
            """)

            conn.commit()

    def create_session(
        self,
        user_id: int,
        username: str,
        user_type: str,
        session_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict:
        """
        Create a new session record when user logs in.

        Args:
            user_id: User ID
            username: Username
            user_type: User type (super, training, chat)
            session_token: JWT session token
            ip_address: Client IP address
            user_agent: Client user agent string

        Returns:
            Dict with session info
        """
        login_time = datetime.now().isoformat()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO sessions (
                        user_id, username, user_type, session_token,
                        login_time, ip_address, user_agent, status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
                """, (user_id, username, user_type, session_token, login_time, ip_address, user_agent))
                conn.commit()
                session_id = cursor.lastrowid

            return {
                "status": "success",
                "session_id": session_id,
                "user_id": user_id,
                "username": username,
                "login_time": login_time
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def close_session(
        self,
        session_token: str,
        close_type: str = "closed"
    ) -> Dict:
        """
        Close a session when user logs out or token expires.

        Args:
            session_token: JWT session token
            close_type: 'closed' (manual logout) or 'expired' (token expired)

        Returns:
            Dict with close status
        """
        logout_time = datetime.now().isoformat()

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Get the session
                cursor.execute("""
                    SELECT id, login_time, status
                    FROM sessions
                    WHERE session_token = ? AND status = 'active'
                """, (session_token,))

                row = cursor.fetchone()

                if not row:
                    return {
                        "status": "not_found",
                        "message": "Active session not found"
                    }

                session_id = row['id']
                login_time = datetime.fromisoformat(row['login_time'])
                logout_dt = datetime.fromisoformat(logout_time)
                duration_seconds = int((logout_dt - login_time).total_seconds())

                # Update session
                cursor.execute("""
                    UPDATE sessions
                    SET logout_time = ?,
                        duration_seconds = ?,
                        status = ?
                    WHERE id = ?
                """, (logout_time, duration_seconds, close_type, session_id))

                conn.commit()

            return {
                "status": "success",
                "session_id": session_id,
                "duration_seconds": duration_seconds,
                "close_type": close_type
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def get_user_sessions(
        self,
        username: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get session history for a user.

        Args:
            username: Username to query
            status: Filter by status ('active', 'closed', 'expired')
            limit: Maximum number of sessions to return

        Returns:
            List of session records
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                if status:
                    cursor.execute("""
                        SELECT *
                        FROM sessions
                        WHERE username = ? AND status = ?
                        ORDER BY login_time DESC
                        LIMIT ?
                    """, (username, status, limit))
                else:
                    cursor.execute("""
                        SELECT *
                        FROM sessions
                        WHERE username = ?
                        ORDER BY login_time DESC
                        LIMIT ?
                    """, (username, limit))

                sessions = []
                for row in cursor.fetchall():
                    sessions.append({
                        "id": row['id'],
                        "user_id": row['user_id'],
                        "username": row['username'],
                        "user_type": row['user_type'],
                        "login_time": row['login_time'],
                        "logout_time": row['logout_time'],
                        "duration_seconds": row['duration_seconds'],
                        "ip_address": row['ip_address'],
                        "user_agent": row['user_agent'],
                        "status": row['status']
                    })

                return sessions
        except Exception as e:
            print(f"Error getting user sessions: {e}")
            return []

    def get_active_sessions(self) -> List[Dict]:
        """
        Get all currently active sessions.

        Returns:
            List of active session records
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT *
                    FROM sessions
                    WHERE status = 'active'
                    ORDER BY login_time DESC
                """)

                sessions = []
                for row in cursor.fetchall():
                    # Calculate current duration
                    login_time = datetime.fromisoformat(row['login_time'])
                    current_duration = int((datetime.now() - login_time).total_seconds())

                    sessions.append({
                        "id": row['id'],
                        "user_id": row['user_id'],
                        "username": row['username'],
                        "user_type": row['user_type'],
                        "login_time": row['login_time'],
                        "ip_address": row['ip_address'],
                        "user_agent": row['user_agent'],
                        "current_duration_seconds": current_duration,
                        "status": row['status']
                    })

                return sessions
        except Exception as e:
            print(f"Error getting active sessions: {e}")
            return []

    def get_session_stats(self, username: Optional[str] = None) -> Dict:
        """
        Get session statistics.

        Args:
            username: Optional username to filter by

        Returns:
            Dict with session statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if username:
                    # User-specific stats
                    cursor.execute("""
                        SELECT
                            COUNT(*) as total_sessions,
                            SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_sessions,
                            SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed_sessions,
                            SUM(CASE WHEN status = 'expired' THEN 1 ELSE 0 END) as expired_sessions,
                            AVG(duration_seconds) as avg_duration_seconds,
                            MAX(duration_seconds) as max_duration_seconds,
                            MIN(duration_seconds) as min_duration_seconds
                        FROM sessions
                        WHERE username = ?
                    """, (username,))
                else:
                    # Global stats
                    cursor.execute("""
                        SELECT
                            COUNT(*) as total_sessions,
                            SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_sessions,
                            SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed_sessions,
                            SUM(CASE WHEN status = 'expired' THEN 1 ELSE 0 END) as expired_sessions,
                            AVG(duration_seconds) as avg_duration_seconds,
                            MAX(duration_seconds) as max_duration_seconds,
                            MIN(duration_seconds) as min_duration_seconds,
                            COUNT(DISTINCT username) as unique_users
                        FROM sessions
                    """)

                row = cursor.fetchone()

                stats = {
                    "total_sessions": row[0] or 0,
                    "active_sessions": row[1] or 0,
                    "closed_sessions": row[2] or 0,
                    "expired_sessions": row[3] or 0,
                    "avg_duration_seconds": int(row[4]) if row[4] else 0,
                    "max_duration_seconds": row[5] or 0,
                    "min_duration_seconds": row[6] or 0
                }

                if not username:
                    stats["unique_users"] = row[7] or 0

                return stats
        except Exception as e:
            print(f"Error getting session stats: {e}")
            return {}

    def cleanup_old_sessions(self, days: int = 90) -> Dict:
        """
        Delete session records older than specified days.

        Args:
            days: Number of days to keep

        Returns:
            Dict with cleanup status
        """
        try:
            cutoff_date = datetime.now().timestamp() - (days * 86400)
            cutoff_iso = datetime.fromtimestamp(cutoff_date).isoformat()

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM sessions
                    WHERE login_time < ? AND status != 'active'
                """, (cutoff_iso,))
                conn.commit()
                deleted_count = cursor.rowcount

            return {
                "status": "success",
                "deleted_count": deleted_count,
                "days": days
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


# CLI for session management
if __name__ == "__main__":
    import sys

    st = SessionTracker()

    if len(sys.argv) < 2:
        print("Session Tracker CLI")
        print("===================")
        print("\nCommands:")
        print("  python session_tracker.py active")
        print("  python session_tracker.py history <username>")
        print("  python session_tracker.py stats [username]")
        print("  python session_tracker.py cleanup <days>")
        sys.exit(0)

    command = sys.argv[1]

    if command == "active":
        sessions = st.get_active_sessions()
        print(f"\nActive sessions: {len(sessions)}\n")
        for session in sessions:
            duration_min = session['current_duration_seconds'] // 60
            print(f"  {session['username']:15} | {session['user_type']:10} | "
                  f"Duration: {duration_min}m | IP: {session['ip_address']}")

    elif command == "history" and len(sys.argv) >= 3:
        username = sys.argv[2]
        sessions = st.get_user_sessions(username, limit=20)
        print(f"\nSession history for {username}: {len(sessions)} sessions\n")
        for session in sessions:
            duration = session['duration_seconds']
            if duration:
                duration_min = duration // 60
                print(f"  [{session['status']:7}] {session['login_time'][:19]} | "
                      f"Duration: {duration_min}m | IP: {session['ip_address']}")
            else:
                print(f"  [{session['status']:7}] {session['login_time'][:19]} | "
                      f"Active | IP: {session['ip_address']}")

    elif command == "stats":
        username = sys.argv[2] if len(sys.argv) >= 3 else None
        stats = st.get_session_stats(username)
        if username:
            print(f"\nSession stats for {username}:\n")
        else:
            print(f"\nGlobal session stats:\n")
        for key, value in stats.items():
            if 'duration' in key and isinstance(value, int):
                minutes = value // 60
                print(f"  {key}: {value}s ({minutes}m)")
            else:
                print(f"  {key}: {value}")

    elif command == "cleanup" and len(sys.argv) >= 3:
        days = int(sys.argv[2])
        result = st.cleanup_old_sessions(days)
        print(result)

    else:
        print("Invalid command. Run without arguments for help.")
