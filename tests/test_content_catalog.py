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
        self.assertEqual(
            region_definition["habitat_ids"],
            [
                "open_grassland",
                "acacia_scrub",
                "rocky_outcrop",
            ],
        )

    def test_loads_b_habitats_with_distinct_conditions(self) -> None:
        registry = build_content_registry(
            PROJECT_ROOT / "content"
        )

        open_conditions = registry.get("open_grassland")[
            "conditions"
        ]
        scrub_conditions = registry.get("acacia_scrub")[
            "conditions"
        ]
        rocky_conditions = registry.get("rocky_outcrop")[
            "conditions"
        ]

        self.assertGreater(
            open_conditions["openness"],
            scrub_conditions["openness"],
        )
        self.assertGreater(
            scrub_conditions["vegetation_density"],
            rocky_conditions["vegetation_density"],
        )
        self.assertGreater(
            rocky_conditions["shelter_availability"],
            open_conditions["shelter_availability"],
        )
        self.assertGreater(
            rocky_conditions["terrain_ruggedness"],
            scrub_conditions["terrain_ruggedness"],
        )

    def test_loads_b_weather_with_distinct_effects(self) -> None:
        registry = build_content_registry(
            PROJECT_ROOT / "content"
        )
        expected_effects = {
            "clear": (1.0, 1.0, 1.0, 1.0),
            "seasonal_rain": (1.25, 0.85, 0.9, 0.8),
            "heavy_rain": (1.1, 0.65, 0.8, 0.65),
            "mist": (1.0, 0.75, 0.98, 0.9),
            "heavy_fog": (1.0, 0.45, 0.95, 0.75),
            "strong_wind": (1.0, 0.95, 0.9, 1.0),
        }

        for weather_id, expected in expected_effects.items():
            with self.subTest(weather_id=weather_id):
                weather_definition = registry.get(weather_id)
                movement_modifiers = weather_definition[
                    "movement_modifiers"
                ]

                self.assertEqual(
                    (
                        weather_definition[
                            "producer_production_multiplier"
                        ],
                        weather_definition[
                            "visibility_modifier"
                        ],
                        movement_modifiers["terrestrial"],
                        movement_modifiers["flight"],
                    ),
                    expected,
                )

        self.assertEqual(
            registry.get("strong_wind")[
                "flight_capability_modifiers"
            ],
            {
                "short_burst": 0.65,
                "powered": 0.75,
                "soaring": 0.9,
            },
        )

    def test_loads_real_taxonomic_definition(self) -> None:
        registry = build_content_registry(
            PROJECT_ROOT / "content"
        )

        mammalia_definition = registry.get("mammalia")

        self.assertEqual(
            mammalia_definition["entity_type"],
            "taxon",
        )
        self.assertEqual(
            mammalia_definition["name"],
            "Mammalia",
        )
        self.assertEqual(
            mammalia_definition["rank"],
            "class",
        )
        self.assertEqual(
            mammalia_definition["parent_taxon_id"],
            "chordata",
        )

    def test_loads_real_trait_definition(self) -> None:
        registry = build_content_registry(
            PROJECT_ROOT / "content"
        )

        trait_definition = registry.get(
            "powerful_hindlimbs"
        )

        self.assertEqual(
            trait_definition["entity_type"],
            "trait",
        )
        self.assertEqual(
            trait_definition["name"],
            "Powerful Hind Limbs",
        )
        self.assertTrue(
            trait_definition["description"].strip()
        )

    def test_loads_real_trait_tags(self) -> None:
        registry = build_content_registry(
            PROJECT_ROOT / "content"
        )

        trait_definition = registry.get(
            "powerful_hindlimbs"
        )

        self.assertEqual(
            trait_definition["tags"],
            [
                "locomotion",
                "escape",
                "defense",
            ],
        )
        self.assertEqual(
            trait_definition["effects"],
            [
                {
                    "target": "escape_mobility",
                    "modifier": 1.15,
                },
                {
                    "target": "counterattack_power",
                    "modifier": 1.1,
                },
            ],
        )

    def test_rejects_catalog_with_missing_parent_taxon(self) -> None:
        from unittest.mock import patch

        def load_test_definitions(
            directory_path: Path,
            expected_entity_type: str | None = None,
        ) -> list[dict]:
            if expected_entity_type == "taxon":
                return [
                    {
                        "entity_type": "taxon",
                        "id": "animalia",
                        "name": "Animalia",
                        "rank": "kingdom",
                        "parent_taxon_id": None,
                    },
                    {
                        "entity_type": "taxon",
                        "id": "mammalia",
                        "name": "Mammalia",
                        "rank": "class",
                        "parent_taxon_id": "chordata",
                    },
                ]
            return []

        with (
            patch(
                "core.content_catalog."
                "load_entity_definitions_from_directory",
                side_effect=load_test_definitions,
            ),
            self.assertRaisesRegex(
                ValueError,
                r"Taxon 'mammalia' references missing parent taxon 'chordata'.",
            ),
        ):
            build_content_registry(Path("content"))

    def test_rejects_taxon_with_unknown_default_trait(self) -> None:
        from unittest.mock import patch

        def load_test_definitions(
            directory_path: Path,
            expected_entity_type: str | None = None,
        ) -> list[dict]:
            if expected_entity_type == "taxon":
                return [
                    {
                        "entity_type": "taxon",
                        "id": "mammalia",
                        "name": "Mammalia",
                        "rank": "class",
                        "parent_taxon_id": None,
                        "default_trait_ids": [
                            "endothermic",
                        ],
                    },
                ]
            if expected_entity_type == "trait":
                return [
                    {
                        "entity_type": "trait",
                        "id": "powerful_hindlimbs",
                        "name": "Powerful Hind Limbs",
                        "description": "Strong rear limbs.",
                    },
                ]
            return []

        with (
            patch(
                "core.content_catalog."
                "load_entity_definitions_from_directory",
                side_effect=load_test_definitions,
            ),
            self.assertRaisesRegex(
                ValueError,
                r"Taxon 'mammalia' references unknown default trait 'endothermic'.",
            ),
        ):
            build_content_registry(Path("content"))

    def test_rejects_animal_with_unknown_added_trait(self) -> None:
        from unittest.mock import patch

        def load_test_definitions(
            directory_path: Path,
            expected_entity_type: str | None = None,
        ) -> list[dict]:
            if expected_entity_type == "taxon":
                return [
                    {
                        "entity_type": "taxon",
                        "id": "animalia",
                        "name": "Animalia",
                        "rank": "kingdom",
                        "parent_taxon_id": None,
                    },
                ]
            if expected_entity_type == "trait":
                return [
                    {
                        "entity_type": "trait",
                        "id": "powerful_hindlimbs",
                        "name": "Powerful Hind Limbs",
                        "description": "Strong rear limbs.",
                    },
                ]
            if expected_entity_type == "animal":
                return [
                    {
                        "entity_type": "animal",
                        "id": "scrub_hare",
                        "name": "Scrub Hare",
                        "taxon_id": "animalia",
                        "trait_ids": [
                            "cryptic_coloration",
                        ],
                    },
                ]
            return []

        with (
            patch(
                "core.content_catalog."
                "load_entity_definitions_from_directory",
                side_effect=load_test_definitions,
            ),
            self.assertRaisesRegex(
                ValueError,
                r"Animal 'scrub_hare' references unknown added trait 'cryptic_coloration'.",
            ),
        ):
            build_content_registry(Path("content"))

    def test_accepts_animal_with_known_added_trait(self) -> None:
        from unittest.mock import patch

        def load_test_definitions(
            directory_path: Path,
            expected_entity_type: str | None = None,
        ) -> list[dict]:
            if expected_entity_type == "taxon":
                return [
                    {
                        "entity_type": "taxon",
                        "id": "animalia",
                        "name": "Animalia",
                        "rank": "kingdom",
                        "parent_taxon_id": None,
                    },
                ]
            if expected_entity_type == "trait":
                return [
                    {
                        "entity_type": "trait",
                        "id": "powerful_hindlimbs",
                        "name": "Powerful Hind Limbs",
                        "description": "Strong rear limbs.",
                    },
                ]
            if expected_entity_type == "animal":
                return [
                    {
                        "entity_type": "animal",
                        "id": "scrub_hare",
                        "name": "Scrub Hare",
                        "taxon_id": "animalia",
                        "trait_ids": [
                            "powerful_hindlimbs",
                        ],
                    },
                ]
            return []

        with patch(
            "core.content_catalog."
            "load_entity_definitions_from_directory",
            side_effect=load_test_definitions,
        ):
            registry = build_content_registry(Path("content"))

        self.assertEqual(
            registry.get("scrub_hare")["trait_ids"],
            ["powerful_hindlimbs"],
        )

    def test_rejects_animal_with_unknown_taxon(self) -> None:
        from unittest.mock import patch

        def load_test_definitions(
            directory_path: Path,
            expected_entity_type: str | None = None,
        ) -> list[dict]:
            if expected_entity_type == "taxon":
                return [
                    {
                        "entity_type": "taxon",
                        "id": "animalia",
                        "name": "Animalia",
                        "rank": "kingdom",
                        "parent_taxon_id": None,
                    },
                ]
            if expected_entity_type == "animal":
                return [
                    {
                        "entity_type": "animal",
                        "id": "scrub_hare",
                        "name": "Scrub Hare",
                        "taxon_id": "lepus",
                    },
                ]
            return []

        with (
            patch(
                "core.content_catalog."
                "load_entity_definitions_from_directory",
                side_effect=load_test_definitions,
            ),
            self.assertRaisesRegex(
                ValueError,
                r"Animal 'scrub_hare' references unknown taxon 'lepus'.",
            ),
        ):
            build_content_registry(Path("content"))

    def test_rejects_animal_with_unknown_excluded_trait(self) -> None:
        from unittest.mock import patch

        def load_test_definitions(
            directory_path: Path,
            expected_entity_type: str | None = None,
        ) -> list[dict]:
            if expected_entity_type == "taxon":
                return [
                    {
                        "entity_type": "taxon",
                        "id": "animalia",
                        "name": "Animalia",
                        "rank": "kingdom",
                        "parent_taxon_id": None,
                    },
                ]
            if expected_entity_type == "trait":
                return [
                    {
                        "entity_type": "trait",
                        "id": "powerful_hindlimbs",
                        "name": "Powerful Hind Limbs",
                        "description": "Strong rear limbs.",
                    },
                ]
            if expected_entity_type == "animal":
                return [
                    {
                        "entity_type": "animal",
                        "id": "scrub_hare",
                        "name": "Scrub Hare",
                        "taxon_id": "animalia",
                        "excluded_trait_ids": [
                            "aquatic",
                        ],
                    },
                ]
            return []

        with (
            patch(
                "core.content_catalog."
                "load_entity_definitions_from_directory",
                side_effect=load_test_definitions,
            ),
            self.assertRaisesRegex(
                ValueError,
                r"Animal 'scrub_hare' references unknown excluded trait 'aquatic'.",
            ),
        ):
            build_content_registry(Path("content"))

    def test_real_animals_reference_their_lowest_defined_taxa(
        self,
    ) -> None:
        registry = build_content_registry(
            PROJECT_ROOT / "content"
        )

        self.assertEqual(
            {
                animal_id: registry.get(animal_id)["taxon_id"]
                for animal_id in (
                    "scrub_hare",
                    "springbok",
                    "bushbuck",
                )
            },
            {
                "scrub_hare": "lepus",
                "springbok": "antidorcas",
                "bushbuck": "tragelaphus",
            },
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
                    "amount_per_producer_per_day": 0.016,
                },
                {
                    "resource_id": "fruit",
                    "amount_per_producer_per_day": 0.008,
                }
            ],
        )

    def test_rejects_producer_with_unknown_resource(self) -> None:
        from unittest.mock import patch

        def load_test_definitions(
            directory_path: Path,
            expected_entity_type: str | None = None,
        ) -> list[dict]:
            if expected_entity_type == "producer":
                return [
                    {
                        "entity_type": "producer",
                        "id": "umbrella_thorn",
                        "name": "Umbrella Thorn",
                        "production": [
                            {
                                "resource_id": "seed_pod",
                                "amount_per_producer_per_day": 0.03,
                            },
                        ],
                    },
                ]
            if expected_entity_type == "resource":
                return [
                    {
                        "entity_type": "resource",
                        "id": "seed_pods",
                        "name": "Seed Pods",
                        "quantity_type": "biomass",
                        "unit": "kg",
                    },
                ]
            return []

        with (
            patch(
                "core.content_catalog."
                "load_entity_definitions_from_directory",
                side_effect=load_test_definitions,
            ),
            self.assertRaisesRegex(
                ValueError,
                r"Producer 'umbrella_thorn' references unknown production resource 'seed_pod'.",
            ),
        ):
            build_content_registry(Path("content"))

    def test_rejects_animal_with_unknown_diet_resource(
        self,
    ) -> None:
        from unittest.mock import patch

        def load_test_definitions(
            directory_path: Path,
            expected_entity_type: str | None = None,
        ) -> list[dict]:
            if expected_entity_type == "animal":
                return [
                    {
                        "entity_type": "animal",
                        "id": "bushbuck",
                        "name": "Bushbuck",
                        "diet": [
                            {
                                "resource_id": "seed_pod",
                                "preference": 0.5,
                            },
                        ],
                    },
                ]
            if expected_entity_type == "resource":
                return [
                    {
                        "entity_type": "resource",
                        "id": "seed_pods",
                        "name": "Seed Pods",
                        "quantity_type": "biomass",
                        "unit": "kg",
                    },
                ]
            return []

        with (
            patch(
                "core.content_catalog."
                "load_entity_definitions_from_directory",
                side_effect=load_test_definitions,
            ),
            self.assertRaisesRegex(
                ValueError,
                r"Animal 'bushbuck' references unknown diet resource 'seed_pod'.",
            ),
        ):
            build_content_registry(Path("content"))

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

    def test_loads_bushbuck_as_browser(self) -> None:
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
            [
                {
                    "resource_id": "leaves_browse",
                    "preference": 1.0,
                },
                {
                    "resource_id": "seed_pods",
                    "preference": 0.7,
                },
            ],
        )

    def test_loads_warthog_as_grassland_omnivore(self) -> None:
        registry = build_content_registry(
            PROJECT_ROOT / "content"
        )

        animal_definition = registry.get("warthog")

        self.assertEqual(
            animal_definition["entity_type"],
            "animal",
        )
        self.assertEqual(
            animal_definition["name"],
            "Warthog",
        )
        self.assertEqual(
            animal_definition["taxon_id"],
            "phacochoerus",
        )
        self.assertEqual(
            animal_definition["diet_type"],
            "omnivore",
        )
        self.assertEqual(
            animal_definition["typical_adult_mass_kg"],
            100.0,
        )
        self.assertEqual(
            animal_definition["preferred_habitat_ids"],
            [
                "open_grassland",
                "acacia_scrub",
            ],
        )
        self.assertEqual(
            animal_definition["diet"],
            [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
                {
                    "resource_id": "fruit",
                    "preference": 0.6,
                },
                {
                    "resource_id": "seed_pods",
                    "preference": 0.5,
                },
                {
                    "resource_id": "leaves_browse",
                    "preference": 0.3,
                },
            ],
        )

    def test_loads_helmeted_guineafowl_as_seed_eating_omnivore(
        self,
    ) -> None:
        registry = build_content_registry(
            PROJECT_ROOT / "content"
        )

        animal_definition = registry.get(
            "helmeted_guineafowl"
        )

        self.assertEqual(
            animal_definition["entity_type"],
            "animal",
        )
        self.assertEqual(
            animal_definition["taxon_id"],
            "numida",
        )
        self.assertEqual(
            animal_definition["diet_type"],
            "omnivore",
        )
        self.assertEqual(
            animal_definition["typical_adult_mass_kg"],
            1.5,
        )
        self.assertEqual(
            animal_definition["preferred_habitat_ids"],
            [
                "open_grassland",
                "acacia_scrub",
            ],
        )
        self.assertEqual(
            animal_definition["diet"],
            [
                {
                    "resource_id": "seeds",
                    "preference": 1.0,
                },
                {
                    "resource_id": "fruit",
                    "preference": 0.8,
                },
                {
                    "resource_id": "grass_forage",
                    "preference": 0.4,
                },
                {
                    "resource_id": "leaves_browse",
                    "preference": 0.2,
                },
            ],
        )
        self.assertNotIn(
            "seed_pods",
            {
                diet_entry["resource_id"]
                for diet_entry in animal_definition["diet"]
            },
        )
        self.assertEqual(
            animal_definition["primary_movement_mode"],
            "terrestrial",
        )
        self.assertEqual(
            animal_definition["available_movement_modes"],
            [
                "terrestrial",
                "flight",
            ],
        )
        self.assertEqual(
            animal_definition["flight_capabilities"],
            [
                "short_burst",
            ],
        )

    def test_real_animals_have_consistent_movement_profiles(
        self,
    ) -> None:
        registry = build_content_registry(
            PROJECT_ROOT / "content"
        )

        animal_ids = (
            "scrub_hare",
            "springbok",
            "bushbuck",
            "warthog",
            "helmeted_guineafowl",
        )

        for animal_id in animal_ids:
            with self.subTest(animal_id=animal_id):
                animal_definition = registry.get(animal_id)
                primary_mode = animal_definition[
                    "primary_movement_mode"
                ]
                available_modes = animal_definition[
                    "available_movement_modes"
                ]

                self.assertIn(
                    primary_mode,
                    available_modes,
                )

                if "flight" in available_modes:
                    self.assertTrue(
                        animal_definition["flight_capabilities"]
                    )
                else:
                    self.assertNotIn(
                        "flight_capabilities",
                        animal_definition,
                    )

if __name__ == "__main__":
    unittest.main()
