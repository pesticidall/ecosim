from pathlib import Path
from typing import Any

REQUIRED_IDENTITY_FIELDS = (
    "entity_type",
    "id",
    "name",
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