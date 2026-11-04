import unittest
from dataclasses import replace

from simulation.carrion import consume_carrion, create_carrion_from_death
from simulation.deaths import DeathCause, DeathRecord
from simulation.predation import (
    PredationRemains, feed_secured_prey, summarize_predation_feeding,
)


class TestPredation(unittest.TestCase):
    def test_commits_meal_to_local_population_and_carrion(self) -> None:
        from simulation.predation import apply_predation_meal
        from simulation.world_state import HabitatState, RegionState

        for consumed, expected_deposits in ((3.0, 1), (10.0, 0)):
            with self.subTest(consumed=consumed):
                local = HabitatState("test_habitat", animal_populations={
                    "test_predator": 1, "test_prey": 1,
                })
                other = HabitatState("other", animal_populations={"test_prey": 2})
                region = RegionState("region", habitats={"test_habitat": local, "other": other},
                                     animal_populations={"test_predator": 1, "test_prey": 3})
                meal = feed_secured_prey(self.remains, consumed)
                apply_predation_meal(region, meal)
                self.assertEqual(local.animal_populations["test_prey"], 0)
                self.assertEqual(region.animal_populations["test_prey"], 2)
                self.assertEqual(other.animal_populations["test_prey"], 2)
                self.assertEqual(local.animal_populations["test_predator"], 1)
                self.assertEqual(local.predation_meals, [meal])
                self.assertEqual(len(local.carrion_deposits), expected_deposits)
                if expected_deposits:
                    self.assertEqual(local.carrion_deposits[0].available_biomass_kg, 7.0)
                with self.assertRaisesRegex(ValueError, "already been applied"):
                    apply_predation_meal(region, meal)
                self.assertEqual(local.predation_meals, [meal])

    def test_invalid_predation_commit_leaves_state_unchanged(self) -> None:
        from simulation.predation import apply_predation_meal
        from simulation.world_state import HabitatState, RegionState

        for predator_count, prey_count in ((0, 1), (1, 0)):
            with self.subTest(predator=predator_count, prey=prey_count):
                populations = {"test_predator": predator_count, "test_prey": prey_count}
                local = HabitatState("test_habitat", animal_populations=dict(populations))
                region = RegionState("region", habitats={"test_habitat": local},
                                     animal_populations=dict(populations))
                with self.assertRaises(ValueError):
                    apply_predation_meal(region, feed_secured_prey(self.remains, 3.0))
                self.assertEqual(local.animal_populations, populations)
                self.assertEqual(region.animal_populations, populations)
                self.assertEqual(local.carrion_deposits, [])
                self.assertEqual(local.predation_meals, [])

    def test_predation_nutrition_drives_starvation_and_reproduction(self) -> None:
        from simulation.mortality import calculate_starvation_deaths
        from simulation.reproduction import calculate_population_births

        predator = {"id": "test_predator", "food_requirement_per_animal_per_cycle": 2.0}
        for amount, ratio, deaths, births in (
            (0.0, 0.0, 4, 0), (4.0, 0.5, 2, 1),
            (8.0, 1.0, 0, 2), (10.0, 1.0, 0, 2),
        ):
            with self.subTest(amount=amount):
                meal = feed_secured_prey(self.remains, amount)
                result = summarize_predation_feeding(4, predator, iter((meal,)))
                self.assertEqual(result.required_amount, 8.0)
                self.assertEqual(result.consumed_amount, amount)
                self.assertEqual(result.nutrition_ratio, ratio)
                self.assertEqual(result.resource_consumption, {"test_prey": amount})
                self.assertEqual(calculate_starvation_deaths(4, ratio), deaths)
                self.assertEqual(calculate_population_births(4, 0.5, ratio), births)
                self.assertEqual(self.remains.carrion.available_biomass_kg, 10.0)

    def test_predation_summary_combines_sources_and_handles_no_meals(self) -> None:
        predator = {"id": "test_predator", "food_requirement_per_animal_per_cycle": 2.0}
        second_death = DeathRecord("other_prey", DeathCause.PREDATION, 1, 5.0)
        second = PredationRemains(
            second_death,
            create_carrion_from_death(second_death, "test_habitat", "test_predator"),
        )
        meals = (feed_secured_prey(self.remains, 2.0), feed_secured_prey(second, 3.0))
        result = summarize_predation_feeding(4, predator, meals)
        self.assertEqual(result.consumed_amount, 5.0)
        self.assertEqual(result.nutrition_ratio, 0.625)
        self.assertEqual(result.resource_consumption, {"test_prey": 2.0, "other_prey": 3.0})
        self.assertEqual(summarize_predation_feeding(4, predator, ()).nutrition_ratio, 0.0)
        self.assertEqual(summarize_predation_feeding(0, predator, ()).nutrition_ratio, 1.0)

    def test_predation_summary_rejects_another_populations_meal(self) -> None:
        meal = feed_secured_prey(self.remains, 2.0)
        with self.assertRaisesRegex(ValueError, "different predator"):
            summarize_predation_feeding(
                1, {"id": "other_predator", "food_requirement_per_animal_per_cycle": 2.0},
                (meal,),
            )

    def setUp(self) -> None:
        death = DeathRecord("test_prey", DeathCause.PREDATION, 1, 10.0)
        self.remains = PredationRemains(
            death,
            create_carrion_from_death(death, "test_habitat", "test_predator"),
        )

    def test_first_meal_conserves_biomass_and_releases_leftovers(self) -> None:
        for requested, consumed, leftover in (
            (0.0, 0.0, 10.0),
            (3.0, 3.0, 7.0),
            (10.0, 10.0, 0.0),
            (20.0, 10.0, 0.0),
        ):
            with self.subTest(requested=requested):
                meal = feed_secured_prey(self.remains, requested)
                self.assertIs(meal.death, self.remains.death)
                self.assertEqual(meal.consumption.consumer_id, "test_predator")
                self.assertEqual(meal.consumption.requested_biomass_kg, requested)
                self.assertEqual(meal.consumption.consumed_biomass_kg, consumed)
                self.assertTrue(meal.consumption.access_granted)
                self.assertEqual(meal.leftover_carrion.available_biomass_kg, leftover)
                self.assertEqual(consumed + leftover, 10.0)
                self.assertEqual(meal.leftover_carrion.habitat_id, "test_habitat")
                self.assertIsNone(meal.leftover_carrion.first_access_consumer_id)
                scavenging = consume_carrion(meal.leftover_carrion, "scavenger", 2.0)
                self.assertTrue(scavenging.access_granted)
                self.assertEqual(scavenging.consumed_biomass_kg, min(2.0, leftover))
                self.assertEqual(self.remains.carrion.available_biomass_kg, 10.0)
                self.assertEqual(self.remains.carrion.first_access_consumer_id, "test_predator")

    def test_first_meal_rejects_invalid_requests(self) -> None:
        for requested, error in (
            (True, TypeError), (None, TypeError), ("3", TypeError),
            (float("inf"), ValueError), (float("nan"), ValueError),
            (-1.0, ValueError),
        ):
            with self.subTest(requested=requested):
                with self.assertRaises(error):
                    feed_secured_prey(self.remains, requested)
                self.assertEqual(self.remains.carrion.available_biomass_kg, 10.0)

    def test_first_meal_requires_reserved_predator_access(self) -> None:
        released = replace(
            self.remains,
            carrion=replace(self.remains.carrion, first_access_consumer_id=None),
        )
        with self.assertRaisesRegex(ValueError, "predator first access"):
            feed_secured_prey(released, 3.0)


if __name__ == "__main__":
    unittest.main()
