"""
Database manager for handling multiple RAG databases.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


# Tunable defaults (env-overridable). Constructor arguments still win.
DEFAULT_DATABASE_CONFIG_FILE = os.getenv("DATABASE_CONFIG_FILE", "database_config.json")


class DatabaseManager:
    """Manages multiple RAG database configurations."""

    def __init__(self, config_file: str = DEFAULT_DATABASE_CONFIG_FILE):
        """
        Initialize the database manager.

        Args:
            config_file: Path to the database configuration file
        """
        self.config_file = Path(config_file)
        self.databases = self._load_config()

        # Prefer the persisted active-database choice from app_settings; fall
        # back to whichever db is marked is_default if no persisted choice.
        try:
            from api.app_settings import AppSettings
            persisted = AppSettings.active_database()
        except Exception:
            persisted = None
        if persisted and persisted in self.databases:
            self.active_database = persisted
        else:
            self.active_database = self._get_default_database()

    def _load_config(self) -> Dict[str, Dict]:
        """Load database configurations from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading database config: {e}")
                return self._create_default_config()
        else:
            return self._create_default_config()

    def _create_default_config(self) -> Dict[str, Dict]:
        """Create default database configuration."""
        default_config = {
            "default": {
                "name": "Default Database",
                "path": "./chroma_db",
                "description": "Main RAG database",
                "created_at": datetime.now().isoformat(),
                "is_default": True
            }
        }
        self._save_config(default_config)
        return default_config

    def _save_config(self, config: Dict[str, Dict]) -> None:
        """Save database configurations to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving database config: {e}")

    def _get_default_database(self) -> str:
        """Get the default database ID."""
        for db_id, db_info in self.databases.items():
            if db_info.get('is_default', False):
                return db_id
        # If no default, return first one
        return list(self.databases.keys())[0] if self.databases else "default"

    def list_databases(self) -> List[Dict]:
        """
        List all available databases.

        Returns:
            List of database configurations
        """
        result = []
        for db_id, db_info in self.databases.items():
            # Get document count and chunk count if database exists
            db_path = Path(db_info['path'])
            chunk_count = 0
            doc_count = 0
            webpage_count = 0
            uploaded_count = 0

            if db_path.exists():
                # Try to get counts from ChromaDB
                try:
                    import chromadb
                    client = chromadb.PersistentClient(path=str(db_path))
                    collections = client.list_collections()
                    if collections:
                        # Get total chunks
                        chunk_count = collections[0].count()

                        # Get unique document count and counts by type
                        results = collections[0].get()
                        if results.get('metadatas'):
                            unique_webpages = set()
                            unique_uploads = set()

                            for metadata in results['metadatas']:
                                source = metadata.get('source', 'unknown')
                                doc_id = metadata.get('doc_id')

                                # Differentiate between web pages and uploaded documents
                                # Web pages start with http:// or https://
                                # Uploaded documents are filenames or have doc_id
                                if source.startswith('http://') or source.startswith('https://'):
                                    # This is a web page - count by URL
                                    unique_webpages.add(source)
                                elif doc_id:
                                    # Uploaded document with doc_id
                                    unique_uploads.add(doc_id)
                                else:
                                    # Old uploaded document without doc_id - count by source
                                    unique_uploads.add(source)

                            # Total document count
                            doc_count = len(unique_webpages) + len(unique_uploads)
                            webpage_count = len(unique_webpages)
                            uploaded_count = len(unique_uploads)

                except Exception:
                    pass

            result.append({
                "id": db_id,
                "name": db_info['name'],
                "path": db_info['path'],
                "description": db_info.get('description', ''),
                "created_at": db_info.get('created_at', ''),
                "is_default": db_info.get('is_default', False),
                "is_active": db_id == self.active_database,
                "document_count": doc_count,
                "chunk_count": chunk_count,
                "webpage_count": webpage_count,
                "uploaded_count": uploaded_count
            })

        return result

    def create_database(
        self,
        db_id: str,
        name: str,
        description: str = "",
        set_as_default: bool = False
    ) -> Dict:
        """
        Create a new database configuration.

        Args:
            db_id: Unique identifier for the database
            name: Display name for the database
            description: Optional description
            set_as_default: Whether to set as default database

        Returns:
            Dictionary with creation status
        """
        if db_id in self.databases:
            return {
                "status": "error",
                "error": f"Database '{db_id}' already exists"
            }

        # Sanitize db_id for filesystem
        safe_id = "".join(c for c in db_id if c.isalnum() or c in "-_").lower()
        db_path = f"./chroma_db_{safe_id}"

        # Create directory
        os.makedirs(db_path, exist_ok=True)

        # If setting as default, unset other defaults
        if set_as_default:
            for db_info in self.databases.values():
                db_info['is_default'] = False

        # Add to configuration
        self.databases[db_id] = {
            "name": name,
            "path": db_path,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "is_default": set_as_default
        }

        self._save_config(self.databases)

        return {
            "status": "success",
            "db_id": db_id,
            "name": name,
            "path": db_path
        }

    def delete_database(self, db_id: str, delete_files: bool = False) -> Dict:
        """
        Delete a database configuration.

        Args:
            db_id: Database ID to delete
            delete_files: Whether to delete the actual database files

        Returns:
            Dictionary with deletion status
        """
        if db_id not in self.databases:
            return {
                "status": "error",
                "error": f"Database '{db_id}' not found"
            }

        if self.databases[db_id].get('is_default', False):
            return {
                "status": "error",
                "error": "Cannot delete the default database"
            }

        db_path = self.databases[db_id]['path']

        # Remove from configuration
        del self.databases[db_id]
        self._save_config(self.databases)

        # Optionally delete files
        if delete_files:
            import shutil
            try:
                if os.path.exists(db_path):
                    shutil.rmtree(db_path)
            except Exception as e:
                return {
                    "status": "warning",
                    "message": f"Database removed from config but files couldn't be deleted: {e}"
                }

        return {
            "status": "success",
            "db_id": db_id
        }

    def set_active_database(self, db_id: str) -> Dict:
        """
        Set the active database for queries.

        Args:
            db_id: Database ID to activate

        Returns:
            Dictionary with status
        """
        if db_id not in self.databases:
            return {
                "status": "error",
                "error": f"Database '{db_id}' not found"
            }

        self.active_database = db_id

        # Persist so the choice survives restart.
        try:
            from api.app_settings import AppSettings
            AppSettings.set_active_database(db_id)
        except Exception as e:
            print(f"DatabaseManager: failed to persist active_database: {e}")

        return {
            "status": "success",
            "active_database": db_id,
            "name": self.databases[db_id]['name']
        }

    def get_active_database(self) -> Dict:
        """
        Get information about the currently active database.

        Returns:
            Dictionary with active database info
        """
        if self.active_database not in self.databases:
            self.active_database = self._get_default_database()

        db_info = self.databases[self.active_database]
        return {
            "id": self.active_database,
            "name": db_info['name'],
            "path": db_info['path'],
            "description": db_info.get('description', '')
        }

    def get_database_path(self, db_id: Optional[str] = None) -> str:
        """
        Get the path for a specific database or the active one.

        Args:
            db_id: Database ID (if None, returns active database path)

        Returns:
            Path to the database directory
        """
        if db_id is None:
            db_id = self.active_database

        if db_id not in self.databases:
            raise ValueError(f"Database '{db_id}' not found")

        return self.databases[db_id]['path']

    def duplicate_database(
        self,
        source_db_id: str,
        new_db_id: str,
        new_name: str,
        description: str = ""
    ) -> Dict:
        """
        Duplicate an existing database (copy all files and create new config).

        Args:
            source_db_id: ID of the database to duplicate
            new_db_id: Unique identifier for the new database
            new_name: Display name for the new database
            description: Optional description

        Returns:
            Dictionary with duplication status
        """
        # Validate source database exists
        if source_db_id not in self.databases:
            return {
                "status": "error",
                "error": f"Source database '{source_db_id}' not found"
            }

        # Check if new ID already exists
        if new_db_id in self.databases:
            return {
                "status": "error",
                "error": f"Database '{new_db_id}' already exists"
            }

        # Get source database path
        source_path = Path(self.databases[source_db_id]['path'])

        # Validate source path exists
        if not source_path.exists():
            return {
                "status": "error",
                "error": f"Source database directory '{source_path}' does not exist"
            }

        # Create new database path
        safe_id = "".join(c for c in new_db_id if c.isalnum() or c in "-_").lower()
        new_db_path = Path(f"./chroma_db_{safe_id}")

        # Copy database files
        try:
            import shutil
            shutil.copytree(source_path, new_db_path)
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to copy database files: {str(e)}"
            }

        # Add to configuration
        self.databases[new_db_id] = {
            "name": new_name,
            "path": str(new_db_path),
            "description": description or f"Copy of {self.databases[source_db_id]['name']}",
            "created_at": datetime.now().isoformat(),
            "is_default": False,
            "duplicated_from": source_db_id
        }

        self._save_config(self.databases)

        return {
            "status": "success",
            "db_id": new_db_id,
            "name": new_name,
            "path": str(new_db_path),
            "source_db_id": source_db_id
        }
