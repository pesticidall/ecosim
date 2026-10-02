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
                    "amount_per_producer_per_day": 0.008,
                },
                {
                    "resource_id": "seeds",
                    "amount_per_producer_per_day": 0.002,
                }
            ]
        )

    def test_loads_real_umbrella_thorn_producer_into_registry(
        self,
    ) -> None:
        producer_definitions = load_entity_definitions_from_directory(
            PROJECT_ROOT / "content" / "producers",
            expected_entity_type="producer",
        )
        registry = ContentRegistry()
        registry.register_all(producer_definitions)

        umbrella_thorn_definition = registry.get("umbrella_thorn")

        self.assertEqual(
            umbrella_thorn_definition["entity_type"],
            "producer",
        )
        self.assertEqual(
            umbrella_thorn_definition["name"],
            "Umbrella Thorn",
        )
        self.assertEqual(
            umbrella_thorn_definition["preferred_habitat_ids"],
            ["acacia_scrub"],
        )
        self.assertEqual(
            umbrella_thorn_definition["production"],
            [
                {
                    "resource_id": "leaves_browse",
                    "amount_per_producer_per_day": 0.014,
                },
                {
                    "resource_id": "seed_pods",
                    "amount_per_producer_per_day": 0.03,
                },
            ],
        )

    def test_real_producers_define_habitat_preferences(self) -> None:
        producer_definitions = load_entity_definitions_from_directory(
            PROJECT_ROOT / "content" / "producers",
            expected_entity_type="producer",
        )
        producers_by_id = {
            definition["id"]: definition
            for definition in producer_definitions
        }

        self.assertEqual(
            {
                producer_id: producers_by_id[producer_id][
                    "preferred_habitat_ids"
                ]
                for producer_id in (
                    "redgrass",
                    "sandpaper_raisin",
                )
            },
            {
                "redgrass": ["open_grassland"],
                "sandpaper_raisin": ["acacia_scrub"],
            },
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

    def test_real_animals_define_body_size(self) -> None:
        animal_definitions = load_entity_definitions_from_directory(
            PROJECT_ROOT / "content" / "animals",
            expected_entity_type="animal",
        )
        animals_by_id = {
            definition["id"]: definition
            for definition in animal_definitions
        }

        self.assertEqual(
            {
                animal_id: animals_by_id[animal_id][
                    "body_size_category"
                ]
                for animal_id in (
                    "scrub_hare",
                    "springbok",
                    "bushbuck",
                )
            },
            {
                "scrub_hare": "small",
                "springbok": "medium",
                "bushbuck": "medium",
            },
        )

    def test_real_animals_define_typical_adult_mass(self) -> None:
        animal_definitions = load_entity_definitions_from_directory(
            PROJECT_ROOT / "content" / "animals",
            expected_entity_type="animal",
        )
        animals_by_id = {
            definition["id"]: definition
            for definition in animal_definitions
        }

        self.assertEqual(
            {
                animal_id: animals_by_id[animal_id][
                    "typical_adult_mass_kg"
                ]
                for animal_id in (
                    "scrub_hare",
                    "springbok",
                    "bushbuck",
                )
            },
            {
                "scrub_hare": 3.5,
                "springbok": 35.0,
                "bushbuck": 50.0,
            },
        )

    def test_real_animals_define_species_statistics(self) -> None:
        animal_definitions = load_entity_definitions_from_directory(
            PROJECT_ROOT / "content" / "animals",
            expected_entity_type="animal",
        )
        animals_by_id = {
            definition["id"]: definition
            for definition in animal_definitions
        }

        self.assertEqual(
            {
                animal_id: animals_by_id[animal_id]["statistics"]
                for animal_id in (
                    "scrub_hare",
                    "springbok",
                    "bushbuck",
                )
            },
            {
                "scrub_hare": {
                    "power": 3.0,
                    "defense": 3.0,
                    "health": 4.0,
                    "mobility": 8.0,
                    "perception": 7.0,
                    "stealth": 7.0,
                    "intelligence": 3.0,
                },
                "springbok": {
                    "power": 6.0,
                    "defense": 5.0,
                    "health": 7.0,
                    "mobility": 9.0,
                    "perception": 8.0,
                    "stealth": 3.0,
                    "intelligence": 4.0,
                },
                "bushbuck": {
                    "power": 6.0,
                    "defense": 6.0,
                    "health": 7.0,
                    "mobility": 6.0,
                    "perception": 7.0,
                    "stealth": 7.0,
                    "intelligence": 3.0,
                },
            },
        )

    def test_real_animals_define_habitat_preferences(self) -> None:
        animal_definitions = load_entity_definitions_from_directory(
            PROJECT_ROOT / "content" / "animals",
            expected_entity_type="animal",
        )
        animals_by_id = {
            definition["id"]: definition
            for definition in animal_definitions
        }

        self.assertEqual(
            {
                animal_id: animals_by_id[animal_id][
                    "preferred_habitat_ids"
                ]
                for animal_id in (
                    "scrub_hare",
                    "springbok",
                    "bushbuck",
                )
            },
            {
                "scrub_hare": [
                    "open_grassland",
                    "acacia_scrub",
                ],
                "springbok": [
                    "open_grassland",
                ],
                "bushbuck": [
                    "acacia_scrub",
                ],
            },
        )

    def test_real_animals_define_activity_patterns(self) -> None:
        animal_directory = (
            PROJECT_ROOT
            / "content"
            / "animals"
        )
        definitions = load_entity_definitions_from_directory(
            animal_directory,
            expected_entity_type="animal",
        )
        registry = ContentRegistry()
        registry.register_all(definitions)

        self.assertEqual(
            {
                animal_id: registry.get(animal_id)["activity_pattern"]
                for animal_id in (
                    "scrub_hare",
                    "springbok",
                    "bushbuck",
                )
            },
            {
                "scrub_hare": "nocturnal",
                "springbok": "diurnal",
                "bushbuck": "crepuscular",
            },
        )

    def test_resolves_real_animal_taxonomic_lineages(self) -> None:
        from simulation.taxonomy import (
            resolve_animal_taxonomic_lineage,
        )

        animal_definitions = load_entity_definitions_from_directory(
            PROJECT_ROOT / "content" / "animals",
            expected_entity_type="animal",
        )
        taxon_definitions = load_entity_definitions_from_directory(
            PROJECT_ROOT / "content" / "taxonomy",
            expected_entity_type="taxon",
        )
        animals_by_id = {
            definition["id"]: definition
            for definition in animal_definitions
        }

        expected_lineages = {
            "scrub_hare": [
                "animalia",
                "chordata",
                "mammalia",
                "lagomorpha",
                "leporidae",
                "lepus",
            ],
            "springbok": [
                "animalia",
                "chordata",
                "mammalia",
                "artiodactyla",
                "bovidae",
                "antidorcas",
            ],
            "bushbuck": [
                "animalia",
                "chordata",
                "mammalia",
                "artiodactyla",
                "bovidae",
                "tragelaphus",
            ],
        }

        for animal_id, expected_lineage in expected_lineages.items():
            with self.subTest(animal=animal_id):
                self.assertEqual(
                    resolve_animal_taxonomic_lineage(
                        animals_by_id[animal_id],
                        taxon_definitions,
                    ),
                    expected_lineage,
                )

    def test_resolves_new_playtest_b_taxonomic_lineages(
        self,
    ) -> None:
        from simulation.taxonomy import (
            resolve_taxonomic_lineage,
        )

        taxon_definitions = load_entity_definitions_from_directory(
            PROJECT_ROOT / "content" / "taxonomy",
            expected_entity_type="taxon",
        )
        expected_lineages = {
            "phacochoerus": [
                "animalia",
                "chordata",
                "mammalia",
                "artiodactyla",
                "suidae",
                "phacochoerus",
            ],
            "proteles": [
                "animalia",
                "chordata",
                "mammalia",
                "carnivora",
                "hyaenidae",
                "proteles",
            ],
            "lupulella": [
                "animalia",
                "chordata",
                "mammalia",
                "carnivora",
                "canidae",
                "lupulella",
            ],
            "caracal_genus": [
                "animalia",
                "chordata",
                "mammalia",
                "carnivora",
                "felidae",
                "caracal_genus",
            ],
            "parahyaena": [
                "animalia",
                "chordata",
                "mammalia",
                "carnivora",
                "hyaenidae",
                "parahyaena",
            ],
            "numida": [
                "animalia",
                "chordata",
                "aves",
                "galliformes",
                "numididae",
                "numida",
            ],
            "gyps": [
                "animalia",
                "chordata",
                "aves",
                "accipitriformes",
                "accipitridae",
                "gyps",
            ],
        }

        for taxon_id, expected_lineage in (
            expected_lineages.items()
        ):
            with self.subTest(taxon_id=taxon_id):
                self.assertEqual(
                    resolve_taxonomic_lineage(
                        taxon_id,
                        taxon_definitions,
                    ),
                    expected_lineage,
                )

    def test_resolves_real_scrub_hare_traits(self) -> None:
        from simulation.traits import resolve_animal_trait_ids

        animal_definitions = load_entity_definitions_from_directory(
            PROJECT_ROOT / "content" / "animals",
            expected_entity_type="animal",
        )
        taxon_definitions = load_entity_definitions_from_directory(
            PROJECT_ROOT / "content" / "taxonomy",
            expected_entity_type="taxon",
        )
        animals_by_id = {
            definition["id"]: definition
            for definition in animal_definitions
        }

        self.assertEqual(
            resolve_animal_trait_ids(
                animals_by_id["scrub_hare"],
                taxon_definitions,
            ),
            [
                "powerful_hindlimbs",
            ],
        )

    def test_resolves_real_scrub_hare_escape_trait_effect(
        self,
    ) -> None:
        from simulation.traits import resolve_animal_trait_effect

        animal_definitions = load_entity_definitions_from_directory(
            PROJECT_ROOT / "content" / "animals",
            expected_entity_type="animal",
        )
        taxon_definitions = load_entity_definitions_from_directory(
            PROJECT_ROOT / "content" / "taxonomy",
            expected_entity_type="taxon",
        )
        trait_definitions = load_entity_definitions_from_directory(
            PROJECT_ROOT / "content" / "traits",
            expected_entity_type="trait",
        )
        animals_by_id = {
            definition["id"]: definition
            for definition in animal_definitions
        }

        effect = resolve_animal_trait_effect(
            animals_by_id["scrub_hare"],
            taxon_definitions,
            trait_definitions,
            "escape_mobility",
        )

        self.assertEqual(effect.modifier, 1.15)
        self.assertEqual(
            effect.contributing_trait_ids,
            ("powerful_hindlimbs",),
        )

    def test_derives_real_animal_weight_classes(self) -> None:
        from simulation.animal_statistics import (
            weight_class_for_mass,
        )

        animal_definitions = load_entity_definitions_from_directory(
            PROJECT_ROOT / "content" / "animals",
            expected_entity_type="animal",
        )
        animals_by_id = {
            definition["id"]: definition
            for definition in animal_definitions
        }

        self.assertEqual(
            {
                animal_id: weight_class_for_mass(
                    animals_by_id[animal_id][
                        "typical_adult_mass_kg"
                    ]
                )
                for animal_id in (
                    "scrub_hare",
                    "springbok",
                    "bushbuck",
                )
            },
            {
                "scrub_hare": "very_light",
                "springbok": "medium",
                "bushbuck": "medium",
            },
        )


if __name__ == "__main__":
    unittest.main()
