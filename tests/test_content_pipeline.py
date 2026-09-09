import unittest
from pathlib import Path

from core.content_loader import (
    load_entity_definitions_from_directory,
)
from core.content_registry import ContentRegistry

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TestContentPipeline(unittest.TestCase):
    def test_loads_real_redgrass_producer_into_registry(self) -> None:
        producer_directory = (
            PROJECT_ROOT
            / "content"
            / "producers"
        )
        definitions = load_entity_definitions_from_directory(
            producer_directory,
        )
        registry = ContentRegistry()
        registry.register_all(definitions)
        redgrass_definition = registry.get("redgrass")
        self.assertEqual(
            redgrass_definition["entity_type"],
            "producer",
        )
        self.assertEqual(
            redgrass_definition["name"],
            "Redgrass",
        )
        self.assertEqual(
            redgrass_definition["production"],
            [
                {
                    "resource_id": "grass_forage",
                    "amount_per_producer_per_cycle": 0.25
                }
            ]
        )

    def test_load_real_biomass_resource_into_registry(self) -> None:
        resource_directory = (
            PROJECT_ROOT
            / "content"
            / "resources"
        )
        definitions = load_entity_definitions_from_directory(
            resource_directory,
            expected_entity_type="resource",
        )
        registry = ContentRegistry()
        registry.register_all(definitions)
        resource_definition = registry.get("grass_forage")
        self.assertEqual(
            resource_definition["entity_type"],
            "resource",
        )
        self.assertEqual(
            resource_definition["name"],
            "Grass",
        )
        self.assertEqual(
            resource_definition["quantity_type"],
            "biomass",
        )
        self.assertEqual(
            resource_definition["unit"],
            "kg",
        )

if __name__ == "__main__":
    unittest.main()