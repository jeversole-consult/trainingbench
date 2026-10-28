"""TB-US-052: versioned training sets.

A training-set snapshot is a list of training examples. The canonical
form (what SHA-256 sees) is NDJSON of the examples sorted by
``sample_id``, UTF-8 encoded.

Each row in ``training_set_versions`` records the hash + metadata;
the actual sample payload is stored in a sidecar JSONL file at
``training/datasets/training_set_versions/v{version_id}.jsonl`` so
the DB row stays small. Operators who want to inspect a historical
snapshot read that file.

The manager extends :class:`VersionedComponentManager`; only the
canonicalization + file-write hooks are specialized.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from api.versioned_component import VersionedComponentManager


SNAPSHOTS_DIR = Path(__file__).resolve().parent.parent.parent / "training" / "datasets" / "training_set_versions"


class TrainingSetVersionManager(VersionedComponentManager):
    table_name = "training_set_versions"
    component_type = "training_set"
    promotable = True

    extra_insert_columns = {
        # Written on create_draft; subclass's canonical_bytes picked by
        # VersionedComponentManager from `payload`, and we also stash
        # sample_count in the row itself.
        "sample_count": 0,
    }

    # ------------------------------------------------------------------ #
    # Canonicalization
    # ------------------------------------------------------------------ #

    def canonical_bytes(self, payload: Iterable[Dict]) -> bytes:
        """Return NDJSON bytes with samples sorted by ``sample_id``.

        Each sample dict must have a stable ``sample_id`` (string or
        int). If missing, we fall back to the sample's own JSON for
        ordering — stable but less meaningful. The sort guarantees
        two payloads with the same examples hash to the same digest
        regardless of insertion order.
        """
        samples = list(payload)
        def _key(s):
            return s.get("sample_id") if isinstance(s, dict) else None
        samples.sort(key=lambda s: (_key(s) is None, _key(s), json.dumps(s, sort_keys=True)))
        lines = [json.dumps(s, sort_keys=True, separators=(",", ":")) for s in samples]
        return ("\n".join(lines) + "\n").encode("utf-8")

    # ------------------------------------------------------------------ #
    # Create with sidecar file
    # ------------------------------------------------------------------ #

    def create_draft_with_samples(
        self,
        agent_id: int,
        samples: List[Dict],
        created_by: str,
        parent_version_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Insert a new draft version and write the sidecar JSONL file.

        Thin wrapper over :meth:`create_draft` that also persists the
        sample payload on disk so later readers can retrieve the
        actual training examples.
        """
        samples = list(samples)
        row = self.create_draft(
            agent_id=agent_id,
            payload=samples,
            created_by=created_by,
            parent_version_id=parent_version_id,
            extra={"sample_count": len(samples)},
        )
        self._write_sidecar(row["version_id"], samples)
        return row

    def read_samples(self, version_id: int) -> List[Dict]:
        """Load the sidecar JSONL file for a version."""
        path = self._sidecar_path(version_id)
        if not path.exists():
            return []
        samples: List[Dict] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                samples.append(json.loads(line))
        return samples

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _sidecar_path(self, version_id: int) -> Path:
        return SNAPSHOTS_DIR / f"v{version_id}.jsonl"

    def _write_sidecar(self, version_id: int, samples: List[Dict]) -> None:
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        path = self._sidecar_path(version_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            "\n".join(json.dumps(s, sort_keys=True) for s in samples) + "\n",
            encoding="utf-8",
        )
        tmp.replace(path)
