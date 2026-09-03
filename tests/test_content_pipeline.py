import unittest
from pathlib import Path

from core.content_loader import (
    load_entity_definitions_from_directory,
)
from core.content_registry import ContentRegistry

PROJECT_ROOT = Path(__file__).resolve().parents[1]

class TestContentPipeline(unittest.TestCase):
    def test_loads_real_grass_producer_into_registry(self) -> None:
        producer_directory = (
            PROJECT_ROOT
            / "content"
            / "producers"
        )
        definitions = load_entity_definitions_from_directory(
            producer_directory
        )
        registry = ContentRegistry()
        registry.register_all(definitions)
        grass_definition = registry.get("grass")
        self.assertEqual(
            grass_definition["entity_type"],
            "producer",
        )
        self.assertEqual(
            grass_definition["name"],
            "Grass",
        )
if __name__ == "__main__":
    unittest.main()