#!/usr/bin/env python3
"""
Training Set Manager for organizing and managing training datasets.
Provides a file manager-like interface for training data.
"""

import os
import sqlite3
import json
import shutil
from typing import Optional, Dict, List
from datetime import datetime
from pathlib import Path


# Tunable defaults (env-overridable). Constructor arguments still win.
DEFAULT_TRAINING_REGISTRY_DB_PATH = os.getenv(
    "TRAINING_REGISTRY_DB_PATH", "training/datasets/registry.db"
)
DEFAULT_TRAINING_BASE_DIR = os.getenv(
    "TRAINING_BASE_DIR", "training/datasets"
)


class TrainingSetManager:
    """
    Manages training datasets with database tracking and file storage.

    Features:
    - Create, read, update, delete training sets
    - Organize datasets by status (active/archived)
    - Track metadata (creator, dates, example count)
    - Search and filter capabilities
    - Integration with query logs and training ratings
    """

    def __init__(
        self,
        db_path: str = DEFAULT_TRAINING_REGISTRY_DB_PATH,
        base_dir: str = DEFAULT_TRAINING_BASE_DIR,
    ):
        """
        Initialize training set manager.

        Args:
            db_path: Path to SQLite database for metadata
            base_dir: Base directory for training dataset files
        """
        self.db_path = db_path
        self.base_dir = Path(base_dir)
        self.active_dir = self.base_dir / "active"
        self.archived_dir = self.base_dir / "archived"

        # Ensure directories exist
        self.active_dir.mkdir(parents=True, exist_ok=True)
        self.archived_dir.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Create training_sets table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS training_sets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    file_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    modified_at TEXT,
                    modified_by TEXT,
                    example_count INTEGER DEFAULT 0,
                    data_format TEXT DEFAULT 'instruction',
                    categories TEXT,
                    tags TEXT,
                    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'pending', 'applied', 'archived', 'deprecated')),
                    adapter_name TEXT,
                    training_run_id INTEGER,
                    locked_at TEXT,
                    metadata TEXT
                )
            """)

            conn.commit()
            print("Training sets database initialized")

    def create_training_set(
        self,
        name: str,
        data: List[Dict],
        created_by: str,
        description: str = "",
        categories: List[str] = None,
        tags: List[str] = None,
        data_format: str = "instruction",
        metadata: Dict = None
    ) -> Dict:
        """
        Create a new training set.

        Args:
            name: Unique name for the training set
            data: List of training examples
            created_by: Username of creator
            description: Description of the training set
            categories: List of categories
            tags: List of tags
            data_format: Format of the data (instruction, completion, chat)
            metadata: Additional metadata

        Returns:
            Dict with status and training set info
        """
        try:
            # Validate name
            if not name or not name.strip():
                return {"status": "error", "error": "Name cannot be empty"}

            # Sanitize filename
            safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name.replace(' ', '_').lower()

            # Create file path
            file_path = self.active_dir / f"{safe_name}.json"

            # Check if file already exists
            if file_path.exists():
                return {"status": "error", "error": f"Training set '{name}' already exists"}

            # Write data to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Insert into database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO training_sets (
                        name, description, file_path, created_at, created_by,
                        example_count, data_format, categories, tags, status, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?)
                """, (
                    name,
                    description,
                    str(file_path),
                    datetime.now().isoformat(),
                    created_by,
                    len(data),
                    data_format,
                    json.dumps(categories) if categories else None,
                    json.dumps(tags) if tags else None,
                    json.dumps(metadata) if metadata else None
                ))

                conn.commit()
                training_set_id = cursor.lastrowid

            return {
                "status": "success",
                "id": training_set_id,
                "name": name,
                "file_path": str(file_path),
                "example_count": len(data)
            }

        except sqlite3.IntegrityError as e:
            return {"status": "error", "error": f"Training set '{name}' already exists"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_training_set(self, training_set_id: int) -> Optional[Dict]:
        """
        Get training set details by ID.

        Args:
            training_set_id: ID of the training set

        Returns:
            Training set info dict or None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM training_sets WHERE id = ?
            """, (training_set_id,))

            row = cursor.fetchone()

            if row:
                return {
                    "id": row['id'],
                    "name": row['name'],
                    "description": row['description'],
                    "file_path": row['file_path'],
                    "created_at": row['created_at'],
                    "created_by": row['created_by'],
                    "modified_at": row['modified_at'],
                    "modified_by": row['modified_by'],
                    "example_count": row['example_count'],
                    "data_format": row['data_format'],
                    "categories": json.loads(row['categories']) if row['categories'] else [],
                    "tags": json.loads(row['tags']) if row['tags'] else [],
                    "status": row['status'],
                    "adapter_name": row['adapter_name'],
                    "training_run_id": row['training_run_id'],
                    "locked_at": row['locked_at'],
                    "metadata": json.loads(row['metadata']) if row['metadata'] else {}
                }

            return None

    def list_training_sets(
        self,
        status: str = None,
        search: str = None,
        created_by: str = None,
        limit: int = None
    ) -> List[Dict]:
        """
        List all training sets with optional filtering.

        Args:
            status: Filter by status (active, archived, deprecated)
            search: Search in name and description
            created_by: Filter by creator
            limit: Limit number of results

        Returns:
            List of training set dicts
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM training_sets WHERE 1=1"
            params = []

            if status:
                query += " AND status = ?"
                params.append(status)

            if search:
                query += " AND (name LIKE ? OR description LIKE ?)"
                search_pattern = f"%{search}%"
                params.extend([search_pattern, search_pattern])

            if created_by:
                query += " AND created_by = ?"
                params.append(created_by)

            query += " ORDER BY created_at DESC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)

            training_sets = []
            for row in cursor.fetchall():
                training_sets.append({
                    "id": row['id'],
                    "name": row['name'],
                    "description": row['description'],
                    "created_at": row['created_at'],
                    "created_by": row['created_by'],
                    "example_count": row['example_count'],
                    "data_format": row['data_format'],
                    "status": row['status'],
                    "adapter_name": row['adapter_name'],
                    "training_run_id": row['training_run_id'],
                    "locked_at": row['locked_at'],
                    "categories": json.loads(row['categories']) if row['categories'] else [],
                    "tags": json.loads(row['tags']) if row['tags'] else [],
                    "metadata": json.loads(row['metadata']) if row['metadata'] else {}
                })

            return training_sets

    def update_training_set(
        self,
        training_set_id: int,
        modified_by: str,
        name: str = None,
        description: str = None,
        categories: List[str] = None,
        tags: List[str] = None,
        status: str = None
    ) -> Dict:
        """
        Update training set metadata.

        Args:
            training_set_id: ID of training set to update
            modified_by: Username of modifier
            name: New name (optional)
            description: New description (optional)
            categories: New categories (optional)
            tags: New tags (optional)
            status: New status (optional)

        Returns:
            Status dict
        """
        try:
            # Get training set to check if it's locked
            training_set = self.get_training_set(training_set_id)
            if not training_set:
                return {"status": "error", "error": "Training set not found"}

            # Prevent editing locked training sets (pending, applied, archived, deprecated)
            if training_set['status'] in ['pending', 'applied'] and status not in ['archived', 'deprecated']:
                return {
                    "status": "error",
                    "error": f"Training set is locked (status: {training_set['status']}). Only draft training sets can be edited."
                }

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Build update query dynamically
                updates = ["modified_at = ?", "modified_by = ?"]
                params = [datetime.now().isoformat(), modified_by]

                if name is not None:
                    updates.append("name = ?")
                    params.append(name)

                if description is not None:
                    updates.append("description = ?")
                    params.append(description)

                if categories is not None:
                    updates.append("categories = ?")
                    params.append(json.dumps(categories))

                if tags is not None:
                    updates.append("tags = ?")
                    params.append(json.dumps(tags))

                if status is not None:
                    if status not in ['draft', 'pending', 'applied', 'archived', 'deprecated']:
                        return {"status": "error", "error": "Invalid status"}
                    updates.append("status = ?")
                    params.append(status)

                    # Move file if status changed
                    training_set = self.get_training_set(training_set_id)
                    if training_set:
                        old_path = Path(training_set['file_path'])
                        if status == 'archived' and old_path.parent == self.active_dir:
                            new_path = self.archived_dir / old_path.name
                            shutil.move(str(old_path), str(new_path))
                            updates.append("file_path = ?")
                            params.append(str(new_path))
                        elif status == 'active' and old_path.parent == self.archived_dir:
                            new_path = self.active_dir / old_path.name
                            shutil.move(str(old_path), str(new_path))
                            updates.append("file_path = ?")
                            params.append(str(new_path))

                params.append(training_set_id)

                query = f"UPDATE training_sets SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                conn.commit()

                if cursor.rowcount > 0:
                    return {"status": "success", "id": training_set_id}
                else:
                    return {"status": "error", "error": "Training set not found"}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def delete_training_set(self, training_set_id: int, delete_file: bool = True) -> Dict:
        """
        Delete a training set.

        Args:
            training_set_id: ID of training set to delete
            delete_file: Whether to delete the actual file

        Returns:
            Status dict
        """
        try:
            # Get training set info
            training_set = self.get_training_set(training_set_id)
            if not training_set:
                return {"status": "error", "error": "Training set not found"}

            # Delete file if requested
            if delete_file:
                file_path = Path(training_set['file_path'])
                if file_path.exists():
                    file_path.unlink()

            # Delete from database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM training_sets WHERE id = ?", (training_set_id,))
                conn.commit()

            return {"status": "success", "id": training_set_id, "name": training_set['name']}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_training_data(self, training_set_id: int) -> Optional[List[Dict]]:
        """
        Load the actual training data from file.

        Args:
            training_set_id: ID of training set

        Returns:
            List of training examples or None
        """
        training_set = self.get_training_set(training_set_id)
        if not training_set:
            return None

        file_path = Path(training_set['file_path'])
        if not file_path.exists():
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def add_example_to_set(
        self,
        training_set_id: int,
        example: Dict,
        modified_by: str
    ) -> Dict:
        """
        Add a single example to a draft training set.
        Only works on training sets with status='draft'.

        Args:
            training_set_id: ID of training set
            example: Training example dict (instruction, input, output)
            modified_by: Username of modifier

        Returns:
            Status dict
        """
        try:
            # Get training set
            training_set = self.get_training_set(training_set_id)
            if not training_set:
                return {"status": "error", "error": "Training set not found"}

            # Check if training set is editable
            if training_set['status'] != 'draft':
                return {
                    "status": "error",
                    "error": f"Training set is locked (status: {training_set['status']}). Only draft training sets can be edited."
                }

            # Load current data
            data = self.get_training_data(training_set_id)
            if data is None:
                data = []

            # Add new example
            data.append(example)

            # Save updated data
            file_path = Path(training_set['file_path'])
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Update metadata in database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE training_sets
                    SET example_count = ?, modified_at = ?, modified_by = ?
                    WHERE id = ?
                """, (len(data), datetime.now().isoformat(), modified_by, training_set_id))
                conn.commit()

            return {
                "status": "success",
                "id": training_set_id,
                "example_count": len(data)
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def lock_training_set(
        self,
        training_set_id: int,
        locked_by: str
    ) -> Dict:
        """
        Lock a training set by changing status from 'draft' to 'pending'.
        This is called when a training user completes their training session.

        Args:
            training_set_id: ID of training set to lock
            locked_by: Username who locked it

        Returns:
            Status dict
        """
        try:
            # Get training set
            training_set = self.get_training_set(training_set_id)
            if not training_set:
                return {"status": "error", "error": "Training set not found"}

            # Check current status
            if training_set['status'] != 'draft':
                return {
                    "status": "error",
                    "error": f"Cannot lock training set with status '{training_set['status']}'. Only draft training sets can be locked."
                }

            # Update status to pending and set locked_at timestamp
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE training_sets
                    SET status = 'pending', locked_at = ?, modified_at = ?, modified_by = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), datetime.now().isoformat(), locked_by, training_set_id))
                conn.commit()

            return {
                "status": "success",
                "id": training_set_id,
                "new_status": "pending",
                "locked_at": datetime.now().isoformat()
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def mark_as_applied(
        self,
        training_set_id: int,
        adapter_name: str,
        training_run_id: int = None
    ) -> Dict:
        """
        Mark a training set as 'applied' after an adapter has been trained from it.
        Links the training set to the adapter that was produced.

        Args:
            training_set_id: ID of training set
            adapter_name: Name of the adapter that was produced
            training_run_id: Optional training run ID

        Returns:
            Status dict
        """
        try:
            # Get training set
            training_set = self.get_training_set(training_set_id)
            if not training_set:
                return {"status": "error", "error": "Training set not found"}

            # Check current status - should be 'pending'
            if training_set['status'] != 'pending':
                return {
                    "status": "error",
                    "error": f"Cannot mark training set as applied. Expected status 'pending', got '{training_set['status']}'."
                }

            # Update status to applied and link adapter
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE training_sets
                    SET status = 'applied', adapter_name = ?, training_run_id = ?, modified_at = ?
                    WHERE id = ?
                """, (adapter_name, training_run_id, datetime.now().isoformat(), training_set_id))
                conn.commit()

            return {
                "status": "success",
                "id": training_set_id,
                "new_status": "applied",
                "adapter_name": adapter_name,
                "training_run_id": training_run_id
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def clone_training_set(
        self,
        training_set_id: int,
        new_name: str,
        created_by: str,
        description: str = None
    ) -> Dict:
        """
        Clone an existing training set.

        Args:
            training_set_id: ID of training set to clone
            new_name: Name for the cloned set
            created_by: Username of creator
            description: Optional new description

        Returns:
            Status dict with new training set info
        """
        # Get original training set
        original = self.get_training_set(training_set_id)
        if not original:
            return {"status": "error", "error": "Training set not found"}

        # Load data
        data = self.get_training_data(training_set_id)
        if data is None:
            return {"status": "error", "error": "Could not load training data"}

        # Create clone
        return self.create_training_set(
            name=new_name,
            data=data,
            created_by=created_by,
            description=description or f"Clone of {original['name']}",
            categories=original['categories'],
            tags=original['tags'],
            data_format=original['data_format']
        )

    def create_from_query_log(
        self,
        name: str,
        created_by: str,
        log_file: str = "logs/master_query_log.jsonl",
        filters: Dict = None,
        description: str = "",
        tags: List[str] = None,
        categories: List[str] = None
    ) -> Dict:
        """
        Create a training set from query log entries.

        Args:
            name: Name for the training set
            created_by: Username of creator
            log_file: Path to query log file (default: master log)
            filters: Filter criteria (e.g., user_type, date_range, success_only)
            description: Description of the training set
            tags: List of tags
            categories: List of categories

        Returns:
            Status dict with training set info
        """
        try:
            log_path = Path(log_file)
            if not log_path.exists():
                return {"status": "error", "error": f"Log file not found: {log_file}"}

            # Set default filters
            if filters is None:
                filters = {}

            # Read and filter log entries
            training_examples = []
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line)

                        # Apply filters
                        if filters.get('success_only', True) and not entry.get('metadata', {}).get('success', True):
                            continue

                        if filters.get('user_type') and entry.get('user_info', {}).get('user_type') != filters['user_type']:
                            continue

                        if filters.get('username') and entry.get('user_info', {}).get('username') != filters['username']:
                            continue

                        if filters.get('database_id') and entry.get('database_id') != filters['database_id']:
                            continue

                        # Convert to training example format
                        question = entry.get('prompt', {}).get('question', '')
                        answer = entry.get('response', {}).get('answer', '')

                        if question and answer:
                            training_examples.append({
                                "instruction": question,
                                "input": "",
                                "output": answer
                            })

                        # Limit number of examples
                        if filters.get('max_examples') and len(training_examples) >= filters['max_examples']:
                            break

                    except json.JSONDecodeError:
                        continue

            if not training_examples:
                return {"status": "error", "error": "No matching log entries found"}

            # Create metadata with filter info
            metadata = {
                "source": "query_log",
                "log_file": log_file,
                "filters": filters,
                "created_from_logs": True
            }

            # Create training set
            return self.create_training_set(
                name=name,
                data=training_examples,
                created_by=created_by,
                description=description or f"Training set from query logs ({len(training_examples)} examples)",
                categories=categories,
                tags=tags or ["query_log"],
                data_format="instruction",
                metadata=metadata
            )

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def create_from_ratings(
        self,
        name: str,
        created_by: str,
        rating_filter: str = "acceptable",
        username: str = None,
        description: str = "",
        tags: List[str] = None,
        categories: List[str] = None
    ) -> Dict:
        """
        Create a training set from training user ratings.

        Args:
            name: Name for the training set
            created_by: Username of creator
            rating_filter: Filter by rating type ('acceptable', 'needs_improvement', or 'all')
            username: Filter by specific training user (optional)
            description: Description of the training set
            tags: List of tags
            categories: List of categories

        Returns:
            Status dict with training set info
        """
        try:
            ratings_dir = Path("logs/ratings")
            if not ratings_dir.exists():
                return {"status": "error", "error": "Ratings directory not found"}

            # Collect rating files
            if username:
                rating_files = [ratings_dir / f"ratings_{username}.jsonl"]
            else:
                rating_files = list(ratings_dir.glob("ratings_*.jsonl"))

            if not rating_files:
                return {"status": "error", "error": "No rating files found"}

            # Read and filter ratings
            training_examples = []
            for rating_file in rating_files:
                if not rating_file.exists():
                    continue

                with open(rating_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            entry = json.loads(line)

                            # Apply rating filter
                            rating = entry.get('rating', '')
                            if rating_filter != 'all':
                                if rating != rating_filter:
                                    continue

                            # Get content (which should be the Q&A pair)
                            content = entry.get('content', '')
                            if not content:
                                continue

                            # Try to parse content as JSON (it might be a full response)
                            try:
                                content_obj = json.loads(content) if isinstance(content, str) else content
                                question = content_obj.get('question', '')
                                answer = content_obj.get('answer', '')
                            except:
                                # If not JSON, skip
                                continue

                            if question and answer:
                                example = {
                                    "instruction": question,
                                    "input": "",
                                    "output": answer
                                }

                                # Add feedback if present and rating is needs_improvement
                                if rating == 'needs_improvement' and entry.get('feedback'):
                                    example['feedback'] = entry['feedback']

                                training_examples.append(example)

                        except json.JSONDecodeError:
                            continue

            if not training_examples:
                return {"status": "error", "error": f"No {rating_filter} ratings found"}

            # Create metadata
            metadata = {
                "source": "training_ratings",
                "rating_filter": rating_filter,
                "username_filter": username,
                "created_from_ratings": True
            }

            # Create training set
            return self.create_training_set(
                name=name,
                data=training_examples,
                created_by=created_by,
                description=description or f"Training set from {rating_filter} ratings ({len(training_examples)} examples)",
                categories=categories,
                tags=tags or ["ratings", rating_filter],
                data_format="instruction",
                metadata=metadata
            )

        except Exception as e:
            return {"status": "error", "error": str(e)}


# CLI for training set management
if __name__ == "__main__":
    import sys

    manager = TrainingSetManager()

    if len(sys.argv) < 2:
        print("Training Set Manager CLI")
        print("========================")
        print("\nCommands:")
        print("  python training_manager.py list")
        print("  python training_manager.py info <id>")
        print("  python training_manager.py delete <id>")
        sys.exit(0)

    command = sys.argv[1]

    if command == "list":
        training_sets = manager.list_training_sets()
        print(f"\nTotal training sets: {len(training_sets)}\n")
        for ts in training_sets:
            print(f"  [{ts['status'].upper():10}] ID: {ts['id']:3} | {ts['name']:30} | Examples: {ts['example_count']:4} | By: {ts['created_by']}")

    elif command == "info" and len(sys.argv) >= 3:
        ts_id = int(sys.argv[2])
        ts = manager.get_training_set(ts_id)
        if ts:
            print(f"\nTraining Set Details:")
            print(f"  ID: {ts['id']}")
            print(f"  Name: {ts['name']}")
            print(f"  Description: {ts['description']}")
            print(f"  Status: {ts['status']}")
            print(f"  Examples: {ts['example_count']}")
            print(f"  Created: {ts['created_at']} by {ts['created_by']}")
            print(f"  File: {ts['file_path']}")
        else:
            print(f"Training set {ts_id} not found")

    elif command == "delete" and len(sys.argv) >= 3:
        ts_id = int(sys.argv[2])
        result = manager.delete_training_set(ts_id)
        print(result)

    else:
        print("Invalid command. Run without arguments for help.")
