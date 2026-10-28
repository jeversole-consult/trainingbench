"""TB-US-053: versioned RAG indices.

A RAG snapshot is an isolated Chroma collection + a manifest row in
``rag_versions``. Collection naming convention is
``agent{agent_id}_rag_v{version_id}`` so operators can inspect
collections directly and know which version they belong to.

The hash is computed over a canonical manifest of
``{source_path, chunk_count, embedding_model, total_tokens}``
entries — raw chunk bytes are NOT hashed because manifest-level
identity is sufficient for provenance and hashing full embedding
indices is expensive.

Draft collections are mutable: operators can ingest more documents
into a draft. Once released, the collection is treated as locked by
convention (we don't physically lock Chroma — Chroma collections
have no immutability primitive — but ingestion endpoints that go
through this manager check state first).

Promotion requires ``chunk_count > 0`` (R10) to avoid silently
breaking chat by promoting an empty RAG.

See ``docs/design/agent-architecture.md`` §5.2 (schema) + §7
(per-type specialization).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from api.versioned_component import (
    VersionedComponentManager,
    VersionedComponentError,
)


DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


class RAGVersionManager(VersionedComponentManager):
    table_name = "rag_versions"
    component_type = "rag"
    promotable = True

    extra_insert_columns = {
        "collection_name": "",
        "chunk_count": 0,
        "embedding_model": DEFAULT_EMBEDDING_MODEL,
    }

    # ------------------------------------------------------------------ #
    # Canonicalization — manifest-level, per R3
    # ------------------------------------------------------------------ #

    def canonical_bytes(self, payload: List[Dict]) -> bytes:
        """Return newline-delimited canonical manifest bytes.

        ``payload`` is a list of document records; each record must
        have at least ``source_path``, ``chunk_count``, and
        ``total_tokens``. ``embedding_model`` is pulled from the first
        record (or default) to pin the embedding provenance.
        """
        docs = list(payload)
        docs.sort(key=lambda d: d.get("source_path", ""))
        lines = []
        for d in docs:
            manifest_entry = {
                "source_path": d.get("source_path", ""),
                "chunk_count": int(d.get("chunk_count", 0)),
                "embedding_model": d.get("embedding_model", DEFAULT_EMBEDDING_MODEL),
                "total_tokens": int(d.get("total_tokens", 0)),
            }
            lines.append(json.dumps(manifest_entry, sort_keys=True, separators=(",", ":")))
        return ("\n".join(lines) + "\n").encode("utf-8")

    # ------------------------------------------------------------------ #
    # Create — allocates collection name based on version_id
    # ------------------------------------------------------------------ #

    def create_draft_version(
        self,
        agent_id: int,
        created_by: str,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        parent_version_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create an empty draft RAG version.

        Collection name is set to the canonical pattern after insert
        (needs the auto-assigned version_id). The row is inserted
        with an empty manifest; ``ingest_docs`` adds to it.
        """
        # Hash of an empty manifest.
        row = self.create_draft(
            agent_id=agent_id,
            payload=[],
            created_by=created_by,
            parent_version_id=parent_version_id,
            extra={
                "collection_name": "",            # updated below
                "chunk_count": 0,
                "embedding_model": embedding_model,
            },
        )
        collection_name = f"agent{agent_id}_rag_v{row['version_id']}"
        with self._connect() as conn:
            conn.execute(
                f"UPDATE {self.table_name} SET collection_name = ? WHERE version_id = ?",
                (collection_name, row["version_id"]),
            )
            conn.commit()
        return self.get_by_id(row["version_id"])

    # ------------------------------------------------------------------ #
    # Ingest — append documents to a draft
    # ------------------------------------------------------------------ #

    def ingest_docs(self, version_id: int, docs: List[Dict]) -> Dict[str, Any]:
        """Append documents to a draft version's manifest + hash.

        ``docs`` is a list of manifest entries (per :meth:`canonical_bytes`).
        Does NOT write to Chroma — that is wired in TB-US-057 when a real
        seed exists. For now this persists manifest-level provenance only.
        """
        row = self._require_version(version_id)
        if row["state"] != "draft":
            raise VersionedComponentError(
                f"Cannot ingest into a {row['state']} version; create a new draft."
            )

        # Rehydrate current manifest from a stashed JSON column? v0.1
        # keeps manifest-reconstruction simple: callers submit the full
        # desired manifest each time. We recompute hash + chunk_count
        # from the input alone. More sophisticated append semantics
        # land in a follow-up.
        new_hash = self.content_hash(docs)
        new_chunk_count = sum(int(d.get("chunk_count", 0)) for d in docs)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE {self.table_name} SET content_sha256 = ?, chunk_count = ? WHERE version_id = ?",
                (new_hash, new_chunk_count, version_id),
            )
            conn.commit()
        return self.get_by_id(version_id)

    # ------------------------------------------------------------------ #
    # Promote — enforces R10 (chunk_count > 0)
    # ------------------------------------------------------------------ #

    def promote(self, version_id: int, promoted_by: str) -> Dict[str, Any]:  # type: ignore[override]
        row = self._require_version(version_id)
        if int(row.get("chunk_count") or 0) <= 0:
            raise VersionedComponentError(
                f"Cannot promote version {version_id}: chunk_count is 0. "
                "Add documents before promoting (per TB-US-053 R10)."
            )
        return super().promote(version_id, promoted_by=promoted_by)
