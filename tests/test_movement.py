import unittest

from simulation.movement import (
    base_mobility_for_mode,
    habitat_mobility_modifier,
    resolve_habitat_mobility,
    resolve_mobility,
    weather_flight_capability_modifier,
    weather_mobility_modifier,
)


class TestMovement(unittest.TestCase):
    def test_returns_base_mobility_for_available_modes(
        self,
    ) -> None:
        animal_definition = {
            "id": "helmeted_guineafowl",
            "available_movement_modes": [
                "terrestrial",
                "flight",
            ],
            "statistics": {
                "mobility": 7.0,
            },
        }

        for movement_mode in (
            "terrestrial",
            "flight",
        ):
            with self.subTest(
                movement_mode=movement_mode
            ):
                self.assertEqual(
                    base_mobility_for_mode(
                        animal_definition,
                        movement_mode,
                    ),
                    7.0,
                )

    def test_rejects_unavailable_movement_mode(
        self,
    ) -> None:
        animal_definition = {
            "id": "warthog",
            "available_movement_modes": [
                "terrestrial",
            ],
            "statistics": {
                "mobility": 7.0,
            },
        }

        with self.assertRaisesRegex(
            ValueError,
            r"warthog.*cannot use.*flight",
        ):
            base_mobility_for_mode(
                animal_definition,
                "flight",
            )

    def test_returns_mode_specific_habitat_modifier(
        self,
    ) -> None:
        habitat_definition = {
            "id": "acacia_scrub",
            "movement_modifiers": {
                "terrestrial": 0.8,
                "flight": 0.95,
            },
        }

        self.assertEqual(
            habitat_mobility_modifier(
                habitat_definition,
                "terrestrial",
            ),
            0.8,
        )
        self.assertEqual(
            habitat_mobility_modifier(
                habitat_definition,
                "flight",
            ),
            0.95,
        )

    def test_defaults_missing_habitat_modifier_to_neutral(
        self,
    ) -> None:
        habitat_definition = {
            "id": "open_grassland",
        }

        self.assertEqual(
            habitat_mobility_modifier(
                habitat_definition,
                "terrestrial",
            ),
            1.0,
        )

    def test_resolves_habitat_mobility_with_visible_inputs(
        self,
    ) -> None:
        animal_definition = {
            "id": "scrub_hare",
            "available_movement_modes": [
                "terrestrial",
            ],
            "statistics": {
                "mobility": 8.0,
            },
        }
        habitat_definition = {
            "id": "acacia_scrub",
            "movement_modifiers": {
                "terrestrial": 0.9,
            },
        }

        performance = resolve_habitat_mobility(
            animal_definition,
            habitat_definition,
            "terrestrial",
        )

        self.assertEqual(
            performance.movement_mode,
            "terrestrial",
        )
        self.assertEqual(
            performance.base_mobility,
            8.0,
        )
        self.assertEqual(
            performance.habitat_modifier,
            0.9,
        )
        self.assertEqual(
            performance.weather_modifier,
            1.0,
        )
        self.assertIsNone(performance.flight_capability)
        self.assertEqual(
            performance.flight_capability_modifier,
            1.0,
        )
        self.assertAlmostEqual(
            performance.resolved_mobility,
            7.2,
        )

    def test_resolves_mobility_with_daily_weather(self) -> None:
        animal_definition = {
            "id": "helmeted_guineafowl",
            "available_movement_modes": [
                "terrestrial",
                "flight",
            ],
            "flight_capabilities": [
                "short_burst",
            ],
            "statistics": {
                "mobility": 7.0,
            },
        }
        habitat_definition = {
            "id": "acacia_scrub",
            "movement_modifiers": {
                "flight": 0.95,
            },
        }
        weather_definition = {
            "id": "strong_wind",
            "movement_modifiers": {
                "flight": 1.0,
            },
            "flight_capability_modifiers": {
                "short_burst": 0.65,
            },
        }

        performance = resolve_mobility(
            animal_definition,
            habitat_definition,
            weather_definition,
            "flight",
        )

        self.assertEqual(performance.base_mobility, 7.0)
        self.assertEqual(performance.habitat_modifier, 0.95)
        self.assertEqual(performance.weather_modifier, 1.0)
        self.assertEqual(
            performance.flight_capability,
            "short_burst",
        )
        self.assertEqual(
            performance.flight_capability_modifier,
            0.65,
        )
        self.assertAlmostEqual(
            performance.resolved_mobility,
            4.3225,
        )

    def test_returns_flight_capability_weather_modifier(
        self,
    ) -> None:
        weather_definition = {
            "id": "strong_wind",
            "flight_capability_modifiers": {
                "short_burst": 0.65,
                "powered": 0.75,
                "soaring": 0.9,
            },
        }

        self.assertEqual(
            weather_flight_capability_modifier(
                weather_definition,
                "soaring",
            ),
            0.9,
        )

    def test_returns_weather_modifier_or_neutral_default(
        self,
    ) -> None:
        rainy_weather = {
            "id": "seasonal_rain",
            "movement_modifiers": {
                "terrestrial": 0.9,
                "flight": 0.8,
            },
        }
        calm_weather = {
            "id": "clear",
        }

        self.assertEqual(
            weather_mobility_modifier(
                rainy_weather,
                "flight",
            ),
            0.8,
        )
        self.assertEqual(
            weather_mobility_modifier(
                calm_weather,
                "terrestrial",
            ),
            1.0,
        )

    def test_applies_inherited_trait_only_to_escape_mobility(
        self,
    ) -> None:
        from simulation.movement import resolve_escape_mobility

        animal_definition = {
            "id": "scrub_hare",
            "taxon_id": "lepus",
            "available_movement_modes": [
                "terrestrial",
            ],
            "statistics": {
                "mobility": 8.0,
            },
        }
        taxon_definitions = [
            {
                "entity_type": "taxon",
                "id": "animalia",
                "name": "Animalia",
                "rank": "kingdom",
                "parent_taxon_id": None,
            },
            {
                "entity_type": "taxon",
                "id": "lepus",
                "name": "Lepus",
                "rank": "genus",
                "parent_taxon_id": "animalia",
                "default_trait_ids": [
                    "powerful_hindlimbs",
                ],
            },
        ]
        trait_definitions = [
            {
                "entity_type": "trait",
                "id": "powerful_hindlimbs",
                "name": "Powerful Hind Limbs",
                "effects": [
                    {
                        "target": "escape_mobility",
                        "modifier": 1.15,
                    },
                ],
            },
        ]
        habitat_definition = {
            "id": "acacia_scrub",
            "movement_modifiers": {
                "terrestrial": 0.9,
            },
        }
        weather_definition = {
            "id": "seasonal_rain",
            "movement_modifiers": {
                "terrestrial": 0.9,
            },
        }

        ordinary_movement = resolve_mobility(
            animal_definition,
            habitat_definition,
            weather_definition,
            "terrestrial",
        )
        escape_movement = resolve_escape_mobility(
            animal_definition,
            taxon_definitions,
            trait_definitions,
            habitat_definition,
            weather_definition,
            "terrestrial",
        )

        self.assertAlmostEqual(
            ordinary_movement.resolved_mobility,
            6.48,
        )
        self.assertAlmostEqual(
            escape_movement.movement.resolved_mobility,
            6.48,
        )
        self.assertEqual(
            escape_movement.trait_effect.modifier,
            1.15,
        )
        self.assertEqual(
            escape_movement.trait_effect.contributing_trait_ids,
            ("powerful_hindlimbs",),
        )
        self.assertAlmostEqual(
            escape_movement.resolved_escape_mobility,
            7.452,
        )


if __name__ == "__main__":
    unittest.main()
