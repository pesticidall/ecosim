import unittest

from simulation.habitats import (
    validate_animal_habitat_references,
    validate_producer_habitat_references,
    validate_region_habitat_references,
)


class TestHabitats(unittest.TestCase):
    def test_rejects_region_with_unknown_habitat(self) -> None:
        region_definitions = [
            {
                "entity_type": "region",
                "id": "redgrass_savanna",
                "name": "Redgrass Savanna",
                "habitat_ids": ["floodplain"],
            },
        ]
        habitat_definitions = [
            {
                "entity_type": "habitat",
                "id": "open_grassland",
                "name": "Open Grassland",
            },
        ]

        with self.assertRaisesRegex(
            ValueError,
            r"redgrass_savanna.*unknown habitat.*floodplain",
        ):
            validate_region_habitat_references(
                region_definitions,
                habitat_definitions,
            )

    def test_rejects_animal_with_unknown_preferred_habitat(
        self,
    ) -> None:
        animal_definitions = [
            {
                "entity_type": "animal",
                "id": "scrub_hare",
                "name": "Scrub Hare",
                "preferred_habitat_ids": ["floodplain"],
            },
        ]
        habitat_definitions = [
            {
                "entity_type": "habitat",
                "id": "open_grassland",
                "name": "Open Grassland",
            },
        ]

        with self.assertRaisesRegex(
            ValueError,
            r"scrub_hare.*unknown preferred habitat.*floodplain",
        ):
            validate_animal_habitat_references(
                animal_definitions,
                habitat_definitions,
            )

    def test_rejects_producer_with_unknown_preferred_habitat(
        self,
    ) -> None:
        producer_definitions = [
            {
                "entity_type": "producer",
                "id": "redgrass",
                "name": "Redgrass",
                "preferred_habitat_ids": ["floodplain"],
            },
        ]
        habitat_definitions = [
            {
                "entity_type": "habitat",
                "id": "open_grassland",
                "name": "Open Grassland",
            },
        ]

        with self.assertRaisesRegex(
            ValueError,
            r"redgrass.*unknown preferred habitat.*floodplain",
        ):
            validate_producer_habitat_references(
                producer_definitions,
                habitat_definitions,
            )

    def test_orders_preferred_habitats_without_excluding_others(
        self,
    ) -> None:
        from simulation.habitats import order_habitats_by_preference

        animal_definition = {
            "entity_type": "animal",
            "id": "springbok",
            "name": "Springbok",
            "preferred_habitat_ids": [
                "open_grassland",
            ],
        }
        region_definition = {
            "entity_type": "region",
            "id": "redgrass_savanna",
            "name": "Redgrass Savanna",
            "habitat_ids": [
                "acacia_scrub",
                "rocky_outcrop",
                "open_grassland",
            ],
        }

        self.assertEqual(
            order_habitats_by_preference(
                animal_definition,
                region_definition,
            ),
            [
                "open_grassland",
                "acacia_scrub",
                "rocky_outcrop",
            ],
        )

    def test_selects_initial_habitat_with_preference_and_fallback(
        self,
    ) -> None:
        from simulation.habitats import select_initial_habitat_id

        region_definition = {
            "entity_type": "region",
            "id": "redgrass_savanna",
            "name": "Redgrass Savanna",
            "habitat_ids": [
                "open_grassland",
                "acacia_scrub",
                "rocky_outcrop",
            ],
        }
        cases = (
            (
                {
                    "entity_type": "animal",
                    "id": "bushbuck",
                    "name": "Bushbuck",
                    "preferred_habitat_ids": [
                        "acacia_scrub",
                    ],
                },
                "acacia_scrub",
            ),
            (
                {
                    "entity_type": "animal",
                    "id": "warthog",
                    "name": "Warthog",
                },
                "open_grassland",
            ),
        )

        for animal_definition, expected_habitat_id in cases:
            with self.subTest(animal_id=animal_definition["id"]):
                self.assertEqual(
                    select_initial_habitat_id(
                        animal_definition,
                        region_definition,
                    ),
                    expected_habitat_id,
                )

    def test_moves_animals_into_a_nonpreferred_habitat(
        self,
    ) -> None:
        from simulation.habitats import move_animal_population
        from simulation.world_state import HabitatState, RegionState

        region_state = RegionState(
            definition_id="redgrass_savanna",
            animal_populations={
                "springbok": 40,
            },
            habitats={
                "open_grassland": HabitatState(
                    definition_id="open_grassland",
                    animal_populations={
                        "springbok": 40,
                    },
                ),
                "rocky_outcrop": HabitatState(
                    definition_id="rocky_outcrop",
                ),
            },
        )

        move_animal_population(
            region_state=region_state,
            animal_id="springbok",
            population=15,
            source_habitat_id="open_grassland",
            destination_habitat_id="rocky_outcrop",
        )

        self.assertEqual(
            region_state.habitats[
                "open_grassland"
            ].animal_populations,
            {
                "springbok": 25,
            },
        )
        self.assertEqual(
            region_state.habitats[
                "rocky_outcrop"
            ].animal_populations,
            {
                "springbok": 15,
            },
        )
        self.assertEqual(
            region_state.animal_populations["springbok"],
            40,
        )
        self.assertEqual(
            sum(
                habitat_state.animal_populations.get(
                    "springbok",
                    0,
                )
                for habitat_state in region_state.habitats.values()
            ),
            40,
        )


if __name__ == "__main__":
    unittest.main()
