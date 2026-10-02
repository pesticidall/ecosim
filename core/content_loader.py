import json
from pathlib import Path
from typing import Any

from core.content_validator import validate_entity_definition


def load_json_file(file_path: Path) -> dict[str, Any]:
    """Load one JSON file and require an object at its top level."""
    with file_path.open("r", encoding="utf-8") as file:
        loaded_data = json.load(file)
        if not isinstance(loaded_data, dict):
            raise TypeError(
                f"Top-level JSON value in '{file_path}' must be an object."
            )
        return loaded_data

def load_entity_definition(
    file_path: Path,
) -> dict[str, Any]:
    """Load and validate one content entity definition."""
    definition = load_json_file(file_path)
    validate_entity_definition(definition, file_path)
    return definition


def load_entity_definitions_from_directory(
        directory_path: Path,
        expected_entity_type: str | None = None,
) -> list[dict[str, Any]]:
    """Load a directory of definitions and enforce its entity type."""
    if not directory_path.exists():
        raise FileNotFoundError(
            f"Content directory '{directory_path}' does not exist."
        )
    file_paths = sorted(
        directory_path.rglob("*.json"),
        key=lambda file_path: (
            file_path.relative_to(directory_path).as_posix()
        ),
    )
    definitions: list[dict[str, Any]] = []
    for file_path in file_paths:
        definition = load_entity_definition(file_path)
        if (
            expected_entity_type is not None
            and definition["entity_type"] != expected_entity_type
        ):
            actual_entity_type = definition["entity_type"]
            raise ValueError(
                f"Definition '{file_path}' has entity type "
                f"'{actual_entity_type}', but this directory expects "
                f"'{expected_entity_type}'."
            )
        definitions.append(definition)

    return definitions
