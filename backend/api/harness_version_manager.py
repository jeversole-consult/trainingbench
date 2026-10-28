"""TB-US-056: versioned eval harnesses.

A harness is a Python module + config dict that evaluates an agent's
model stack. Unlike other versioned components, **harnesses are not
promotable** — they are measurement sidecars, not Sweet Spot axes
(per TB-US-043 Q5). Experiments reference a harness_version_id
directly.

Hash semantics (per R3):

- Content hash = SHA-256 of canonical JSON of the definition dict
  **plus** the raw source bytes of the referenced module. The source
  inclusion means a code change in the harness module produces a
  new version — a safeguard against silent behavior drift.

Definition shape::

    {
        "module": "harnesses.math_qa_v1",      # importable module
        "config": {
            "dataset_path": "...",
            "metric": "accuracy",
            "n_samples": 200,
        }
    }

See ``docs/design/agent-architecture.md`` §5.6.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Dict, Optional

from api.versioned_component import (
    VersionedComponentManager,
    VersionedComponentError,
)


# Where harness modules live. Resolved relative to the repo so
# arbitrary importable paths like ``harnesses.math_qa_v1`` map to
# ``backend/harnesses/math_qa_v1.py``.
HARNESS_MODULES_ROOT = Path(__file__).resolve().parent.parent / "harnesses"


class HarnessVersionManager(VersionedComponentManager):
    table_name = "harness_versions"
    component_type = "harness"
    promotable = False     # harness is NOT a Sweet Spot axis

    extra_insert_columns = {
        "definition_json": "{}",
    }

    def canonical_bytes(self, payload: Dict) -> bytes:
        """Hash input: canonical definition JSON + module source bytes.

        ``payload`` must be the full definition dict with ``module`` key.
        """
        if not isinstance(payload, dict) or "module" not in payload:
            raise VersionedComponentError(
                "Harness definition must be a dict with a 'module' key"
            )

        def_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        module_src = self._read_module_source(payload["module"])
        combined = def_bytes + b"\n---module-source---\n" + module_src
        return combined

    def create_draft_definition(
        self,
        agent_id: int,
        definition: Dict,
        created_by: str,
        parent_version_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Convenience: create a draft from a definition dict."""
        # Validate module can be located before writing a row.
        self._read_module_source(definition.get("module", ""))
        return self.create_draft(
            agent_id=agent_id,
            payload=definition,
            created_by=created_by,
            parent_version_id=parent_version_id,
            extra={"definition_json": json.dumps(definition, sort_keys=True)},
        )

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    @staticmethod
    def _read_module_source(module_dotted: str) -> bytes:
        """Return raw bytes of the referenced module's source file.

        ``harnesses.math_qa_v1`` maps to
        ``backend/harnesses/math_qa_v1.py``. Raises
        VersionedComponentError if the file isn't found so hash
        attempts fail fast with a clear message.
        """
        if not module_dotted:
            raise VersionedComponentError("Harness module path is required")
        # Only accept the ``harnesses.*`` namespace for now; broadening
        # to arbitrary modules widens attack surface for later.
        parts = module_dotted.split(".")
        if parts[0] != "harnesses" or len(parts) < 2:
            raise VersionedComponentError(
                f"Harness module must live under 'harnesses.*'; got {module_dotted!r}"
            )
        rel_path = Path(*parts[1:]).with_suffix(".py")
        full_path = HARNESS_MODULES_ROOT / rel_path
        if not full_path.exists():
            raise VersionedComponentError(
                f"Harness module file not found: {full_path}"
            )
        return full_path.read_bytes()
