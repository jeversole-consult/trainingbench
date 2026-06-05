"""
Query logger for collecting RAG training data.
Logs questions, context, and answers for fine-tuning data preparation.
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, List


class QueryLogger:
    """Logs RAG query interactions for training data collection."""

    def __init__(self, log_file: str = "./training/data/query_log.jsonl"):
        """
        Initialize query logger.

        Args:
            log_file: Path to the JSONL log file
        """
        self.log_file = log_file

        # Ensure directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        # Create file if it doesn't exist
        if not os.path.exists(log_file):
            with open(log_file, 'w') as f:
                pass

    def log_interaction(
        self,
        question: str,
        context: List[str],
        answer: str,
        sources: List[Dict] = None,
        rating: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Log a RAG interaction.

        Args:
            question: User's question
            context: Retrieved context chunks
            answer: Generated answer
            sources: Source documents information
            rating: Optional quality rating (1-5)
            metadata: Optional additional metadata
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "context": context if isinstance(context, list) else [context],
            "answer": answer,
            "sources": sources or [],
            "rating": rating,
            "metadata": metadata or {}
        }

        # Append to JSONL file
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def get_logs(self, limit: Optional[int] = None, min_rating: Optional[int] = None) -> List[Dict]:
        """
        Retrieve logged interactions.

        Args:
            limit: Maximum number of logs to return (most recent first)
            min_rating: Minimum rating filter (only return logs with rating >= this)

        Returns:
            List of logged interactions
        """
        if not os.path.exists(self.log_file):
            return []

        logs = []
        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line)

                        # Apply rating filter
                        if min_rating is not None:
                            if entry.get('rating') is None or entry.get('rating') < min_rating:
                                continue

                        logs.append(entry)
                    except json.JSONDecodeError:
                        continue

        # Return most recent first
        logs.reverse()

        # Apply limit
        if limit:
            logs = logs[:limit]

        return logs

    def get_stats(self) -> Dict:
        """
        Get statistics about logged interactions.

        Returns:
            Dictionary with logging statistics
        """
        logs = self.get_logs()

        total_logs = len(logs)
        rated_logs = [log for log in logs if log.get('rating') is not None]

        stats = {
            "total_interactions": total_logs,
            "rated_interactions": len(rated_logs),
            "unrated_interactions": total_logs - len(rated_logs),
            "log_file": self.log_file,
            "log_file_exists": os.path.exists(self.log_file)
        }

        # Add rating distribution if we have rated logs
        if rated_logs:
            rating_counts = {}
            for log in rated_logs:
                rating = log.get('rating')
                rating_counts[rating] = rating_counts.get(rating, 0) + 1

            stats["rating_distribution"] = rating_counts
            stats["average_rating"] = sum(log.get('rating', 0) for log in rated_logs) / len(rated_logs)

        return stats

    def clear_logs(self) -> None:
        """Clear all logged interactions."""
        with open(self.log_file, 'w') as f:
            pass
