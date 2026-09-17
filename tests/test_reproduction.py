import unittest

from core.content_registry import ContentRegistry
from simulation.feeding import PopulationFeedingResult
from simulation.reproduction import (
    apply_reproduction,
    calculate_population_births,
)
from simulation.world_state import RegionState


class TestReproduction(unittest.TestCase):
    def test_calculates_births_for_fully_fed_population(self) -> None:
        births = calculate_population_births(
            population=20,
            birth_rate=0.25,
            nutrition_ratio=1.0,
        )
        self.assertEqual(births, 5)

    def test_reduces_births_when_population_is_underfed(self) -> None:
        births = calculate_population_births(
            population=20,
            birth_rate=0.25,
            nutrition_ratio=0.5,
        )
        self.assertEqual(births, 2)

    def test_completely_unfed_population_has_no_births(self) -> None:
        births = calculate_population_births(
            population=20,
            birth_rate=0.25,
            nutrition_ratio=0.0,
        )
        self.assertEqual(births, 0)

    def test_rejects_negative_population(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            r"population.*must not be negative",
        ):
            calculate_population_births(
                population=-20,
                birth_rate=0.25,
                nutrition_ratio=1.0
            )

    def test_rejects_negative_birth_rate(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            r"birth_rate.*must not be negative",
        ):
            calculate_population_births(
                population=20,
                birth_rate=-0.25,
                nutrition_ratio=1.0,
            )

    def test_rejects_negative_nutrition_ratio(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            r"nutrition_ratio.*must be between 0.0 and 1.0",
        ):
            calculate_population_births(
                population=20,
                birth_rate=0.25,
                nutrition_ratio=-0.1,
            )

    def test_rejects_nutrition_above_one(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            r"nutrition_ratio.*must be between 0.0 and 1.0",
        ):
            calculate_population_births(
                population=20,
                birth_rate=0.25,
                nutrition_ratio=1.1,
            )

    def test_applies_births_to_population(self) -> None:
        registry = ContentRegistry()
        registry.register(
            {
                "entity_type": "animal",
                "id": "scrub_hare",
                "name": "Scrub Hare",
                "birth_rate_per_animal_per_cycle": 0.25,
            }
        )
        region_state = RegionState(
            definition_id="redgrass_savanna",
            animal_populations={
                "scrub_hare": 20,
            },
        )
        feeding_results = {
            "scrub_hare": PopulationFeedingResult(
                required_amount=10.0,
                consumed_amount=10.0,
                nutrition_ratio=1.0,
                resource_consumption={
                    "grass_forage": 10.0,
                },
            ),
        }

        births = apply_reproduction(
            region_state,
            registry,
            feeding_results,
        )

        self.assertEqual(
            births,
            {
                "scrub_hare": 5,
            },
        )
        self.assertEqual(
            region_state.animal_populations["scrub_hare"],
            25,
        )

    def test_applies_reproduction_to_every_population(self) -> None:
        registry = ContentRegistry()
        registry.register(
            {
                "entity_type": "animal",
                "id": "scrub_hare",
                "name": "Scrub Hare",
                "birth_rate_per_animal_per_cycle": 0.25,
            }
        )
        registry.register(
            {
                "entity_type": "animal",
                "id": "springbok",
                "name": "Springbok",
                "birth_rate_per_animal_per_cycle": 0.1,
            }
        )
        region_state = RegionState(
            definition_id="redgrass_savanna",
            animal_populations={
                "scrub_hare": 20,
                "springbok": 10,
            },
        )
        feeding_results = {
            "scrub_hare": PopulationFeedingResult(
                required_amount=10.0,
                consumed_amount=10.0,
                nutrition_ratio=1.0,
                resource_consumption={
                    "grass_forage": 10.0,
                },
            ),
            "springbok": PopulationFeedingResult(
                required_amount=20.0,
                consumed_amount=10.0,
                nutrition_ratio=0.5,
                resource_consumption={
                    "grass_forage": 10.0,
                },
            ),
        }

        births = apply_reproduction(
            region_state,
            registry,
            feeding_results,
        )

        self.assertEqual(
            births,
            {
                "scrub_hare": 5,
                "springbok": 0,
            },
        )
        self.assertEqual(
            region_state.animal_populations,
            {
                "scrub_hare": 25,
                "springbok": 10,
            },
        )
if __name__ == "__main__":
    unittest.main()