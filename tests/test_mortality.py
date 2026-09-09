import unittest

from simulation.feeding import PopulationFeedingResult
from simulation.mortality import (
    apply_starvation_mortality,
    calculate_starvation_deaths,
)
from simulation.world_state import RegionState


class TestStarvationMortality(unittest.TestCase):
    def test_calculates_deaths_from_missing_nutrition(self) -> None:
        starvation_deaths = calculate_starvation_deaths(
            population=20,
            nutrition_ratio=0.75,
        )
        self.assertEqual(starvation_deaths, 5)

    def test_fully_fed_population_has_no_starvation_deaths(self) -> None:
        starvation_deaths = calculate_starvation_deaths(
            population=20,
            nutrition_ratio=1.0,
        )
        self.assertEqual(starvation_deaths, 0)

    def test_completely_unfed_population_all_dies(self) -> None:
        starvation_deaths = calculate_starvation_deaths(
            population=20,
            nutrition_ratio=0.0,
        )
        self.assertEqual(starvation_deaths, 20)

    def test_rejects_negative_population(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            r"population.*must not be negative",
        ):
            calculate_starvation_deaths(
                population=-20,
                nutrition_ratio=0.75,
            )

    def test_rejects_negative_nutrition_ratio(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            r"nutrition_ratio.*must be between 0.0 and 1.0",
        ):
            calculate_starvation_deaths(
                population=20,
                nutrition_ratio=-0.25,
            )

    def test_rejects_nutrition_ratio_above_one(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            r"nutrition_ratio.*between 0.0 and 1.0",
        ):
            calculate_starvation_deaths(
                population=20,
                nutrition_ratio=1.1,
            )

    def test_rounds_fractional_starvation_deaths_down(self) -> None:
        starvation_deaths = calculate_starvation_deaths(
            population=19,
            nutrition_ratio=0.75,
        )
        self.assertEqual(starvation_deaths, 4)

    def test_applies_starvation_deaths_to_population(self) -> None:
        region_state = RegionState(
            definition_id="redgrass_savanna",
            animal_populations={
                "scrub_hare": 20,
            },
        )
        feeding_results = {
            "scrub_hare": PopulationFeedingResult(
                required_amount=10.0,
                consumed_amount=7.5,
                nutrition_ratio=0.75,
                resource_consumption={
                    "grass_forage": 7.5,
                },
            ),
        }
        starvation_deaths = apply_starvation_mortality(
            region_state,
            feeding_results,
        )
        self.assertEqual(
            starvation_deaths,
            {
                "scrub_hare": 5,
            },
        )
        self.assertEqual(
            region_state.animal_populations["scrub_hare"],
            15,
        )

    def test_applies_starvation_mortality_to_every_population(self) -> None:
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
                consumed_amount=7.5,
                nutrition_ratio=0.75,
                resource_consumption={
                    "grass_forage": 7.5,
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

        starvation_deaths = apply_starvation_mortality(
            region_state,
            feeding_results,
        )

        self.assertEqual(
            starvation_deaths,
            {
                "scrub_hare": 5,
                "springbok": 5,
            },
        )
        self.assertEqual(
            region_state.animal_populations,
            {
                "scrub_hare": 15,
                "springbok": 5,
            },
        )


if __name__ == "__main__":
    unittest.main()