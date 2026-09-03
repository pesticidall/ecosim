import json
from pathlib import Path
from typing import Any

from core.content_validator import validate_entity_definition


def load_json_file(file_path: Path) -> dict[str, Any]:
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
    definition = load_json_file(file_path)
    validate_entity_definition(definition, file_path)
    return definition


def load_entity_definitions_from_directory(
        directory_path: Path,
) -> list[dict[str, Any]]:
    if not directory_path.exists():
        raise FileNotFoundError(
            f"Content directory '{directory_path}' does not exist."
        )
    file_paths = sorted(directory_path.glob("*.json"))

    return [
        load_entity_definition(file_path)
        for file_path in file_paths
    ]