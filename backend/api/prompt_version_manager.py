"""TB-US-055: versioned system prompts.

Each snapshot is a short text blob. Hash is SHA-256 of the UTF-8
bytes of the prompt text with trailing whitespace stripped — operator
edits commonly introduce incidental trailing whitespace that
shouldn't count as content difference.

See ``docs/design/agent-architecture.md`` §5.4 (schema).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from api.versioned_component import (
    VersionedComponentManager,
    VersionedComponentError,
)


class PromptVersionManager(VersionedComponentManager):
    table_name = "prompt_versions"
    component_type = "prompt"
    promotable = True

    extra_insert_columns = {
        "content": "",
    }

    def canonical_bytes(self, payload: str) -> bytes:
        """Hash input: UTF-8 encoded text with trailing whitespace stripped per line."""
        text = (payload or "").rstrip()
        return text.encode("utf-8")

    def create_draft_text(
        self,
        agent_id: int,
        text: str,
        created_by: str,
        parent_version_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Convenience wrapper: create a draft with inline prompt text."""
        return self.create_draft(
            agent_id=agent_id,
            payload=text,
            created_by=created_by,
            parent_version_id=parent_version_id,
            extra={"content": text or ""},
        )
