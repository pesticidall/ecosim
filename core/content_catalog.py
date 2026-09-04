from pathlib import Path

from core.content_loader import (
    load_entity_definitions_from_directory,
)
from core.content_registry import ContentRegistry

CONTENT_DIRECTORIES = (
    ("animals", "animal"),
    ("producers", "producer"),
    ("regions", "region"),
    ("resources", "resource"),
    ("weather", "weather"),
)
def build_content_registry(
    content_root: Path,
) -> ContentRegistry:
    registry = ContentRegistry()
    for directory_name, expected_entity_type in CONTENT_DIRECTORIES:
        directory_path = content_root / directory_name
        definitions = load_entity_definitions_from_directory(
            directory_path,
            expected_entity_type=expected_entity_type,
        )
        registry.register_all(definitions)
    return registry