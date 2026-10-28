"""TB-US-054: versioned PEFT adapters.

An adapter snapshot is a directory on disk at
``adapters/{agent_slug}/v{version_id}/`` plus a row in
``adapter_versions`` recording the content hash, base model,
training-set provenance, and training-run metadata.

Hash semantics (per R3):

- ``content_sha256`` = SHA-256 of ``adapter_model.safetensors`` bytes
- ``config_sha256``  = SHA-256 of ``adapter_config.json`` bytes
  (secondary field for additional provenance; adapter_config.json
  changes orthogonally from the model weights — e.g. renaming the
  base model identifier).

Trainer integration (R5) and inference-time hot-swap (R7) are
scope-split out of this story — see completion notes. This module
ships the versioning primitives + a ``register_existing_adapter()``
path so operators (and later TB-US-057's seeder) can add an
already-trained adapter without going through the trainer wiring.

See ``docs/design/agent-architecture.md`` §5.3 (schema) + §7
(per-type specialization).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

from api.versioned_component import (
    VersionedComponentManager,
    VersionedComponentError,
)


ADAPTERS_ROOT = Path(__file__).resolve().parent.parent.parent / "adapters"

ADAPTER_FILE = "adapter_model.safetensors"
CONFIG_FILE = "adapter_config.json"


class AdapterVersionManager(VersionedComponentManager):
    table_name = "adapter_versions"
    component_type = "adapter"
    promotable = True

    extra_insert_columns = {
        "config_sha256": None,
        "training_set_version_id": None,
        "base_model": "",
        "training_run_metadata_json": None,
        "files_path": "",
    }

    # ------------------------------------------------------------------ #
    # Canonicalization
    # ------------------------------------------------------------------ #

    def canonical_bytes(self, payload: Path) -> bytes:
        """Return the raw bytes of ``adapter_model.safetensors``.

        ``payload`` is the path to the adapter directory. The base
        class calls this inside ``content_hash`` which SHA-256s the
        result. Adapter weights are the authoritative "content"; the
        config is hashed separately into ``config_sha256``.
        """
        safetensors_path = Path(payload) / ADAPTER_FILE
        if not safetensors_path.exists():
            raise VersionedComponentError(
                f"Expected {ADAPTER_FILE} at {safetensors_path} — not found"
            )
        return safetensors_path.read_bytes()

    # ------------------------------------------------------------------ #
    # Register existing adapter files
    # ------------------------------------------------------------------ #

    def register_existing_adapter(
        self,
        agent_id: int,
        agent_slug: str,
        source_dir: Path,
        base_model: str,
        created_by: str,
        training_set_version_id: Optional[int] = None,
        training_run_metadata: Optional[Dict] = None,
        parent_version_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Register an on-disk adapter directory as a new draft version.

        Copies ``adapter_model.safetensors`` + ``adapter_config.json``
        (and any other files in the source dir) to the canonical
        location ``adapters/{agent_slug}/v{version_id}/``. Hashes
        both files, writes the row, returns the stored record.
        """
        source_dir = Path(source_dir)
        if not source_dir.is_dir():
            raise VersionedComponentError(
                f"source_dir {source_dir} is not a directory"
            )
        safetensors = source_dir / ADAPTER_FILE
        config = source_dir / CONFIG_FILE
        if not safetensors.exists():
            raise VersionedComponentError(
                f"Missing {ADAPTER_FILE} in {source_dir}"
            )
        if not base_model:
            raise VersionedComponentError("base_model is required")

        # Insert a placeholder row to allocate version_id, then compute
        # the canonical files_path, copy, hash, and update.
        row = self.create_draft(
            agent_id=agent_id,
            payload=source_dir,         # hashes safetensors here
            created_by=created_by,
            parent_version_id=parent_version_id,
            extra={
                "config_sha256": self._hash_file(config) if config.exists() else None,
                "training_set_version_id": training_set_version_id,
                "base_model": base_model,
                "training_run_metadata_json": json.dumps(training_run_metadata or {}, sort_keys=True),
                "files_path": "",       # updated below
            },
        )
        dest_rel = f"adapters/{agent_slug}/v{row['version_id']}"
        dest = ADAPTERS_ROOT / agent_slug / f"v{row['version_id']}"
        dest.mkdir(parents=True, exist_ok=True)
        for f in source_dir.iterdir():
            if f.is_file():
                (dest / f.name).write_bytes(f.read_bytes())
        with self._connect() as conn:
            conn.execute(
                f"UPDATE {self.table_name} SET files_path = ? WHERE version_id = ?",
                (dest_rel, row["version_id"]),
            )
            conn.commit()
        return self.get_by_id(row["version_id"])

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    @staticmethod
    def _hash_file(path: Path) -> Optional[str]:
        if not path.exists():
            return None
        return hashlib.sha256(path.read_bytes()).hexdigest()
