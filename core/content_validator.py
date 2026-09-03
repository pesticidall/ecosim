import re
from pathlib import Path
from typing import Any

REQUIRED_IDENTITY_FIELDS = (
    "entity_type",
    "id",
    "name",
)
SUPPORTED_ENTITY_TYPES = frozenset(
    {
        "animal",
        "producer",
        "region",
        "resource",
        "weather"
    }
)
ENTITY_ID_PATTERN = re.compile(
    r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*"
)

def validate_entity_definition(
        definition: dict[str, Any],
        source_path: Path,
) -> None:
    missing_fields = [
        field
        for field in REQUIRED_IDENTITY_FIELDS
        if field not in definition
    ]
    if missing_fields:
        field_list = ", ".join(missing_fields)
        raise ValueError(
            f"Definition '{source_path}' is missing required "
            f"field(s): {field_list}."
        )
    for field in REQUIRED_IDENTITY_FIELDS:
        field_value = definition[field]
        if not isinstance(field_value, str):
            raise TypeError(
                f"Field '{field}' in definition '{source_path}' "
                f"must be a string."
            )
        if not field_value.strip():
            raise ValueError(
                f"Field '{field}' in definition '{source_path}' "
                f"must not be empty."
            )
    entity_type = definition["entity_type"]
    if entity_type not in SUPPORTED_ENTITY_TYPES:
        raise ValueError(
            f"Definition '{source_path}' has unsupported "
            f"entity type '{entity_type}'."
        )
    entity_id = definition["id"]
    if ENTITY_ID_PATTERN.fullmatch(entity_id) is None:
        raise ValueError(
            f"Field 'id' in definition '{source_path}' "
            f"must use lowercase snake_case."
        )