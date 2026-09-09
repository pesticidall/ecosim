import unittest
from pathlib import Path

from core.content_catalog import build_content_registry

PROJECT_ROOT = Path(__file__).resolve().parents[1]

class TestContentCatalog(unittest.TestCase):
    def test_builds_registry_from_all_content_directories(self) -> None:
        content_root = PROJECT_ROOT / "content"
        registry = build_content_registry(content_root)
        redgrass_definition = registry.get("redgrass")
        forage_definition = registry.get("grass_forage")
        hare_definition = registry.get("scrub_hare")
        weather_definition = registry.get("seasonal_rain")
        region_definition = registry.get("redgrass_savanna")
        self.assertEqual(
            redgrass_definition["entity_type"],
            "producer",
        )
        self.assertEqual(
            forage_definition["entity_type"],
            "resource",
        )
        self.assertEqual(
            hare_definition["entity_type"],
            "animal",
        )
        self.assertEqual(
            hare_definition["name"],
            "Scrub Hare",
        )
        self.assertEqual(
            weather_definition["entity_type"],
            "weather",
        )
        self.assertEqual(
            weather_definition["name"],
            "Seasonal Rain",
        )
        self.assertEqual(
            region_definition["entity_type"],
            "region",
        )
        self.assertEqual(
            region_definition["name"],
            "Redgrass Savanna",
        )

if __name__ == "__main__":
    unittest.main()