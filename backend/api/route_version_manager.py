"""TB-US-055: versioned query routes.

Each snapshot is a list of route rules (currently used for prefix /
suffix augmentation of chat queries — see TB-US-040). Hash is
SHA-256 of canonical JSON (sorted keys, no whitespace) so two
semantically identical configs with reordered keys hash the same.

See ``docs/design/agent-architecture.md`` §5.5 (schema).
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from api.versioned_component import (
    VersionedComponentManager,
    VersionedComponentError,
)


class RouteVersionManager(VersionedComponentManager):
    table_name = "route_versions"
    component_type = "routes"
    promotable = True

    extra_insert_columns = {
        "content": "[]",
    }

    def canonical_bytes(self, payload: List[Dict]) -> bytes:
        """Hash input: canonical JSON (sort_keys, no whitespace)."""
        return json.dumps(payload or [], sort_keys=True, separators=(",", ":")).encode("utf-8")

    def create_draft_routes(
        self,
        agent_id: int,
        routes: List[Dict],
        created_by: str,
        parent_version_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Convenience wrapper: create a draft with inline routes list."""
        canonical = json.dumps(routes or [], sort_keys=True, separators=(",", ":"))
        return self.create_draft(
            agent_id=agent_id,
            payload=routes or [],
            created_by=created_by,
            parent_version_id=parent_version_id,
            extra={"content": canonical},
        )
