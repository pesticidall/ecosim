from collections.abc import Iterable
from typing import Any


class ContentRegistry:
    """Store validated content definitions by their globally unique IDs."""

    def __init__(self) -> None:
        """Create an empty definition registry."""
        self._definitions: dict[str, dict[str, Any]] = {}
    def register(
            self,
            definition: dict[str, Any],
    ) -> None:
        """Register one definition, rejecting an ID already in use."""
        entity_id = definition["id"]
        if entity_id in self._definitions:
            raise ValueError(
                f"Duplicate entity id '{entity_id}'."
            )
        self._definitions[entity_id] = definition
    def register_all(
            self,
            definitions: Iterable[dict[str, Any]],
    ) -> None:
        """Register each definition from an iterable."""
        for definition in definitions:
            self.register(definition)
    def get(
            self,
            entity_id: str,
    ) -> dict[str, Any]:
        """Return the definition registered under an entity ID."""
        return self._definitions[entity_id]
