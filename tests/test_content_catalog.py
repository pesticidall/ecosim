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

    def test_loads_leaves_as_biomass_resource(self) -> None:
        registry = build_content_registry(PROJECT_ROOT / "content")

        leaf_definition = registry.get("leaves_browse")

        self.assertEqual(leaf_definition["entity_type"], "resource")
        self.assertEqual(leaf_definition["name"], "Leaves")
        self.assertEqual(leaf_definition["quantity_type"], "biomass")
        self.assertEqual(leaf_definition["unit"], "kg")

    def test_loads_sandpaper_raisin_as_leaf_producer(self) -> None:
        registry = build_content_registry(PROJECT_ROOT / "content")

        producer_definition = registry.get("sandpaper_raisin")

        self.assertEqual(producer_definition["entity_type"], "producer")
        self.assertEqual(producer_definition["name"], "Sandpaper Raisin")
        self.assertEqual(
            producer_definition["production"],
            [
                {
                    "resource_id": "leaves_browse",
                    "amount_per_producer_per_cycle": 0.5,
                }
            ],
        )

    def test_loads_springbok_as_mixed_feeder(self) -> None:
        registry = build_content_registry(PROJECT_ROOT / "content")
        animal_definition = registry.get("springbok")

        self.assertEqual(animal_definition["name"], "Springbok")
        self.assertEqual(animal_definition["diet_type"], "herbivore")
        self.assertEqual(
            animal_definition["food_requirement_per_animal_per_cycle"],
            2.0,
        )
        self.assertEqual(
            animal_definition["birth_rate_per_animal_per_cycle"],
            0.1,
        )
        self.assertEqual(
            animal_definition["diet"],
            [
                {"resource_id": "grass_forage", "preference": 1.0},
                {"resource_id": "leaves_browse", "preference": 0.5},
            ],
        )

    def test_loads_bushbuck_as_leaf_browser(self) -> None:
        registry = build_content_registry(PROJECT_ROOT / "content")
        animal_definition = registry.get("bushbuck")

        self.assertEqual(animal_definition["entity_type"], "animal")
        self.assertEqual(animal_definition["name"], "Bushbuck")
        self.assertEqual(animal_definition["diet_type"], "herbivore")
        self.assertEqual(
            animal_definition["food_requirement_per_animal_per_cycle"],
            2.0,
        )
        self.assertEqual(
            animal_definition["birth_rate_per_animal_per_cycle"],
            0.1,
        )
        self.assertEqual(
            animal_definition["diet"],
            [{"resource_id": "leaves_browse", "preference": 1.0}],
        )
if __name__ == "__main__":
    unittest.main()