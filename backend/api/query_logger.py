"""
Query logging system for tracking questions and answers.
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class QueryLogger:
    """Logs all queries and responses to file."""

    def __init__(self, log_dir: str = "logs"):
        """
        Initialize the query logger.

        Args:
            log_dir: Directory to store log files
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Setup file logger for queries
        self.query_log_file = self.log_dir / "queries.jsonl"

        # Setup MASTER log file (captures ALL queries from ALL users)
        self.master_log_file = self.log_dir / "master_query_log.jsonl"

        # Setup standard logger
        self.logger = logging.getLogger("QueryLogger")
        self.logger.setLevel(logging.INFO)

        # File handler for detailed logs
        fh = logging.FileHandler(self.log_dir / "query_activity.log")
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

    def log_query(
        self,
        question: str,
        answer: str,
        sources: List[Dict],
        k: int,
        response_time: float,
        error: Optional[str] = None,
        llm_model: Optional[str] = None,
        database_id: Optional[str] = None,
        username: Optional[str] = None,
        user_type: Optional[str] = None,
        user_id: Optional[int] = None,
        folder: Optional[str] = None,
        rating: Optional[str] = None,
        feedback: Optional[str] = None
    ):
        """
        Log a query and its response to both per-user log and master log.

        Args:
            question: The question asked
            answer: The answer generated
            sources: List of source documents used
            k: Number of chunks retrieved
            response_time: Time taken to generate response (seconds)
            error: Error message if query failed
            llm_model: LLM model used for this query
            database_id: ID of the database used for this query
            username: Username of the person making the query
            user_type: Type of user (super, chat, training)
            user_id: Numeric user ID from database
            folder: Optional folder filter used in query
            rating: Optional rating from training users
            feedback: Optional feedback from training users
        """
        # Generate unique log ID
        log_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        # Per-user log entry (existing format for backward compatibility)
        per_user_log_entry = {
            "timestamp": timestamp,
            "question": question,
            "answer": answer,
            "sources": sources,
            "k": k,
            "response_time": response_time,
            "success": error is None,
            "error": error,
            "llm_model": llm_model,
            "database_id": database_id,
            "username": username,
            "user_type": user_type
        }

        # Master log entry (enhanced format for Phase 2 requirements)
        master_log_entry = {
            "log_id": log_id,
            "timestamp": timestamp,
            "user_info": {
                "username": username,
                "user_type": user_type,
                "user_id": user_id
            } if username else None,
            "database_id": database_id,
            "prompt": {
                "question": question,
                "k": k,
                "model": llm_model,
                "folder": folder
            },
            "response": {
                "answer": answer,
                "sources": sources,
                "response_time": response_time
            },
            "metadata": {
                "llm_model": llm_model,
                "error": error,
                "rating": rating,
                "feedback": feedback,
                "success": error is None
            }
        }

        # Write to per-user log (maintains existing behavior)
        if username:
            # Each user gets their own log file
            log_file = self.log_dir / f"queries_{username}.jsonl"
        else:
            # Fallback to general log file if no username provided
            log_file = self.query_log_file

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(per_user_log_entry, ensure_ascii=False) + "\n")

        # Write to MASTER log (new Phase 2 functionality)
        with open(self.master_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(master_log_entry, ensure_ascii=False) + "\n")

        # Log to standard logger
        user_info = f" [User: {username} ({user_type})]" if username and user_type else ""
        if error:
            self.logger.error(f"Query failed{user_info}: {question[:100]}... Error: {error}")
        else:
            self.logger.info(
                f"Query successful{user_info}: {question[:100]}... "
                f"(k={k}, time={response_time:.2f}s, sources={len(sources)}) [log_id: {log_id}]"
            )

    def get_recent_queries(self, n: int = 10) -> List[Dict]:
        """
        Get the N most recent queries.

        Args:
            n: Number of recent queries to retrieve

        Returns:
            List of query log entries
        """
        if not self.query_log_file.exists():
            return []

        queries = []
        with open(self.query_log_file, "r", encoding="utf-8") as f:
            for line in f:
                queries.append(json.loads(line))

        # Return last N queries
        return queries[-n:]

    def get_all_queries(self) -> List[Dict]:
        """
        Get all logged queries.

        Returns:
            List of all query log entries
        """
        if not self.query_log_file.exists():
            return []

        queries = []
        with open(self.query_log_file, "r", encoding="utf-8") as f:
            for line in f:
                queries.append(json.loads(line))

        return queries

    def get_stats(self, database_id: Optional[str] = None) -> Dict:
        """
        Get statistics about logged queries.

        Args:
            database_id: Optional database ID to filter stats for a specific database

        Returns:
            Dictionary with query statistics
        """
        queries = self.get_all_queries()

        # Filter by database if specified
        if database_id is not None:
            queries = [q for q in queries if q.get("database_id") == database_id]

        if not queries:
            return {
                "total_queries": 0,
                "successful_queries": 0,
                "failed_queries": 0,
                "avg_response_time": 0,
                "total_sources_retrieved": 0
            }

        successful = [q for q in queries if q.get("success", False)]
        failed = [q for q in queries if not q.get("success", True)]

        avg_time = sum(q.get("response_time", 0) for q in successful) / len(successful) if successful else 0
        total_sources = sum(len(q.get("sources", [])) for q in queries)

        return {
            "total_queries": len(queries),
            "successful_queries": len(successful),
            "failed_queries": len(failed),
            "avg_response_time": round(avg_time, 2),
            "total_sources_retrieved": total_sources,
            "log_file": str(self.query_log_file)
        }

    def export_to_csv(self, output_file: str = None) -> str:
        """
        Export queries to CSV format.

        Args:
            output_file: Output CSV file path (defaults to logs/queries.csv)

        Returns:
            Path to the exported CSV file
        """
        import csv

        if output_file is None:
            output_file = self.log_dir / "queries.csv"
        else:
            output_file = Path(output_file)

        queries = self.get_all_queries()

        if not queries:
            return str(output_file)

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["timestamp", "question", "answer", "k", "response_time",
                         "success", "error", "num_sources", "llm_model"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            writer.writeheader()
            for q in queries:
                writer.writerow({
                    "timestamp": q.get("timestamp", ""),
                    "question": q.get("question", ""),
                    "answer": q.get("answer", ""),
                    "k": q.get("k", 0),
                    "response_time": q.get("response_time", 0),
                    "success": q.get("success", True),
                    "error": q.get("error", ""),
                    "num_sources": len(q.get("sources", [])),
                    "llm_model": q.get("llm_model", "")
                })

        return str(output_file)
