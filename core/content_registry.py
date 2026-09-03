from collections.abc import Iterable
from typing import Any


class ContentRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, dict[str, Any]] = {}
    def register(
            self,
            definition: dict[str, Any],
    ) -> None:
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
        for definition in definitions:
            self.register(definition)
    def get(
            self,
            entity_id: str,
    ) -> dict[str, Any]:
        return self._definitions[entity_id]
    