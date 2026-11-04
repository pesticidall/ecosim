import unittest


class TestTemperament(unittest.TestCase):
    def test_resolves_reusable_animal_temperament_profile(
        self,
    ) -> None:
        from simulation.temperament import (
            resolve_animal_temperament_weights,
        )

        animal_definition = {
            "id": "scrub_hare",
            "temperament_id": "skittish",
        }
        temperament_definitions = [
            {
                "entity_type": "temperament",
                "id": "skittish",
                "name": "Skittish",
                "description": (
                    "Favors escape while retaining defensive options."
                ),
                "action_weights": {
                    "escape": 1.4,
                    "counterattack": 0.7,
                },
            },
        ]

        weights = resolve_animal_temperament_weights(
            animal_definition,
            temperament_definitions,
        )

        self.assertEqual(
            weights,
            {
                "escape": 1.4,
                "counterattack": 0.7,
            },
        )

    def test_combines_context_and_temperament_for_action_selection(
        self,
    ) -> None:
        from random import Random

        from simulation.temperament import select_animal_action

        animal_definition = {
            "id": "scrub_hare",
            "temperament_id": "skittish",
        }
        temperament_definitions = [
            {
                "entity_type": "temperament",
                "id": "skittish",
                "name": "Skittish",
                "description": (
                    "Favors escape while retaining defensive options."
                ),
                "action_weights": {
                    "escape": 1.4,
                    "counterattack": 0.7,
                },
            },
        ]

        selection = select_animal_action(
            animal_definition=animal_definition,
            temperament_definitions=temperament_definitions,
            contextual_suitability={
                "escape": 0.5,
                "counterattack": 1.0,
            },
            eligible_action_ids=[
                "escape",
                "counterattack",
            ],
            random_source=Random(1),
        )

        self.assertEqual(
            [
                option.action_id
                for option in selection.options
            ],
            [
                "escape",
                "counterattack",
            ],
        )
        self.assertEqual(
            [
                option.temperament_preference
                for option in selection.options
            ],
            [
                1.4,
                0.7,
            ],
        )
        self.assertEqual(
            [
                option.contextual_suitability
                for option in selection.options
            ],
            [
                0.5,
                1.0,
            ],
        )
        self.assertEqual(
            [
                option.combined_weight
                for option in selection.options
            ],
            [
                0.7,
                0.7,
            ],
        )
        self.assertEqual(selection.total_weight, 1.4)
        self.assertEqual(selection.selected_action_id, "escape")


if __name__ == "__main__":
    unittest.main()