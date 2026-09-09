import unittest

from core.content_registry import ContentRegistry
from simulation.feeding import (
    PopulationFeedingResult,
    calculate_population_food_requirement,
    consume_available_resource,
    feed_population,
    feed_region,
)
from simulation.world_state import RegionState


class TestFeeding(unittest.TestCase):
    def test_calculates_population_food_requirement(self) -> None:
        animal_definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "food_requirement_per_animal_per_cycle": 0.5,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                }
            ],
        }

        food_requirement = calculate_population_food_requirement(
            population=80,
            animal_definition=animal_definition,
        )

        self.assertEqual(food_requirement, 40.0)

    def test_consumes_only_available_resource_quantity(self) -> None:
        region_state = RegionState(
            definition_id="redgrass_savanna",
            resource_quantities={
                "grass_forage": 10.0,
            },
        )
        consumed_amount = consume_available_resource(
            region_state=region_state,
            resource_id="grass_forage",
            requested_amount=12.0,
        )
        self.assertEqual(consumed_amount, 10.0)
        self.assertEqual(
            region_state.resource_quantities["grass_forage"],
            0.0,
        )

    def test_consumes_requested_resource_quantity_when_available(self) -> None:
        region_state = RegionState(
            definition_id="redgrass_savanna",
            resource_quantities={
                "grass_forage": 10.0,
            },
        )
        consumed_amount = consume_available_resource(
            region_state=region_state,
            resource_id="grass_forage",
            requested_amount=4.0,
        )
        self.assertEqual(consumed_amount, 4.0)
        self.assertEqual(
            region_state.resource_quantities["grass_forage"],
            6.0
        )

    def test_consumes_zero_when_resource_is_unavailable(self) -> None:
        region_state = RegionState(
            definition_id="redgrass_savanna",
        )
        consumed_amount = consume_available_resource(
            region_state=region_state,
            resource_id="grass_forage",
            requested_amount=4.0,
        )
        self.assertEqual(consumed_amount, 0.0)
        self.assertEqual(
            region_state.resource_quantities["grass_forage"],
            0.0,
        )

    def test_feeds_population_from_compatible_resource(self) -> None:
        animal_definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "food_requirement_per_animal_per_cycle": 0.5,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                }
            ],
        }
        region_state = RegionState(
            definition_id="redgrass_savanna",
            resource_quantities={
                "grass_forage": 50.0,
            }
        )
        feeding_result = feed_population(
            population=80,
            animal_definition=animal_definition,
            region_state=region_state,
        )
        self.assertEqual(
            feeding_result,
            PopulationFeedingResult(
                required_amount=40.0,
                consumed_amount=40.0,
                nutrition_ratio=1.0,
                resource_consumption={
                    "grass_forage": 40.0,
                }
            )
        )
        self.assertEqual(
            region_state.resource_quantities["grass_forage"],
            10.0,
        )

    def test_reports_partial_nutrition_during_food_shortage(self) -> None:
        animal_definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "food_requirement_per_animal_per_cycle": 0.5,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                }
            ],
        }
        region_state = RegionState(
            definition_id="redgrass_savanna",
            resource_quantities={
                "grass_forage": 30.0,
            },
        )

        feeding_result = feed_population(
            population=80,
            animal_definition=animal_definition,
            region_state=region_state,
        )

        self.assertEqual(feeding_result.required_amount, 40.0)
        self.assertEqual(feeding_result.consumed_amount, 30.0)
        self.assertEqual(feeding_result.nutrition_ratio, 0.75)
        self.assertEqual(
            feeding_result.resource_consumption,
            {
                "grass_forage": 30.0,
            },
        )
        self.assertEqual(
            region_state.resource_quantities["grass_forage"],
            0.0,
        )

    def test_zero_population_requires_and_consumes_no_food(self) -> None:
        animal_definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "food_requirement_per_animal_per_cycle": 0.5,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                }
            ],
        }
        region_state = RegionState(
            definition_id="redgrass_savanna",
            resource_quantities={
                "grass_forage": 30.0,
            },
        )

        feeding_result = feed_population(
            population=0,
            animal_definition=animal_definition,
            region_state=region_state,
        )

        self.assertEqual(feeding_result.required_amount, 0.0)
        self.assertEqual(feeding_result.consumed_amount, 0.0)
        self.assertEqual(feeding_result.nutrition_ratio, 1.0)
        self.assertEqual(
            region_state.resource_quantities["grass_forage"],
            30.0,
        )

    def test_uses_alternative_resource_to_complete_feeding(self) -> None:
        animal_definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "food_requirement_per_animal_per_cycle": 0.5,
            "diet": [
                {
                    "resource_id": "leaves_browse",
                    "preference": 0.4,
                },
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        region_state = RegionState(
            definition_id="redgrass_savanna",
            resource_quantities={
                "grass_forage": 25.0,
                "leaves_browse": 30.0,
            },
        )

        feeding_result = feed_population(
            population=80,
            animal_definition=animal_definition,
            region_state=region_state,
        )

        self.assertEqual(feeding_result.required_amount, 40.0)
        self.assertEqual(feeding_result.consumed_amount, 40.0)
        self.assertEqual(feeding_result.nutrition_ratio, 1.0)
        self.assertEqual(
            feeding_result.resource_consumption,
            {
                "grass_forage": 25.0,
                "leaves_browse": 15.0,
            },
        )
        self.assertEqual(
            region_state.resource_quantities["grass_forage"],
            0.0,
        )
        self.assertEqual(
            region_state.resource_quantities["leaves_browse"],
            15.0,
        )

    def test_feeds_animal_populations_in_region(self) -> None:
        registry = ContentRegistry()
        registry.register(
            {
                "entity_type": "animal",
                "id": "scrub_hare",
                "name": "Scrub Hare",
                "diet_type": "herbivore",
                "food_requirement_per_animal_per_cycle": 0.5,
                "diet": [
                    {
                        "resource_id": "grass_forage",
                        "preference": 1.0,
                    }
                ],
            }
        )
        region_state = RegionState(
            definition_id="redgrass_savanna",
            animal_populations={
                "scrub_hare": 80,
            },
            resource_quantities={
                "grass_forage": 50.0,
            },
        )

        feeding_results = feed_region(
            region_state,
            registry,
        )

        self.assertEqual(
            feeding_results["scrub_hare"],
            PopulationFeedingResult(
                required_amount=40.0,
                consumed_amount=40.0,
                nutrition_ratio=1.0,
                resource_consumption={
                    "grass_forage": 40.0,
                },
            ),
        )
        self.assertEqual(
            region_state.resource_quantities["grass_forage"],
            10.0,
        )

    def test_shared_resource_is_divided_proportionally(self) -> None:
        registry = ContentRegistry()

        for animal_id, animal_name in (
            ("scrub_hare", "Scrub Hare"),
            ("springbok", "Springbok"),
        ):
            registry.register(
                {
                    "entity_type": "animal",
                    "id": animal_id,
                    "name": animal_name,
                    "diet_type": "herbivore",
                    "food_requirement_per_animal_per_cycle": 0.5,
                    "diet": [
                        {
                            "resource_id": "grass_forage",
                            "preference": 1.0,
                        }
                    ],
                }
            )

        region_state = RegionState(
            definition_id="redgrass_savanna",
            animal_populations={
                "scrub_hare": 20,
                "springbok": 20,
            },
            resource_quantities={
                "grass_forage": 10.0,
            },
        )

        feeding_results = feed_region(
            region_state,
            registry,
        )

        self.assertEqual(
            feeding_results["scrub_hare"].consumed_amount,
            5.0,
        )
        self.assertEqual(
            feeding_results["springbok"].consumed_amount,
            5.0,
        )
        self.assertEqual(
            feeding_results["scrub_hare"].nutrition_ratio,
            0.5,
        )
        self.assertEqual(
            feeding_results["springbok"].nutrition_ratio,
            0.5,
        )
        self.assertEqual(
            region_state.resource_quantities["grass_forage"],
            0.0,
        )

    def test_underfed_population_uses_alternative_after_competition(self) -> None:
        registry = ContentRegistry()
        registry.register(
            {
                "entity_type": "animal",
                "id": "scrub_hare",
                "name": "Scrub Hare",
                "diet_type": "herbivore",
                "food_requirement_per_animal_per_cycle": 0.5,
                "diet": [
                    {
                        "resource_id": "grass_forage",
                        "preference": 1.0,
                    },
                    {
                        "resource_id": "leaves_browse",
                        "preference": 0.5,
                    },
                ],
            }
        )
        registry.register(
            {
                "entity_type": "animal",
                "id": "springbok",
                "name": "Springbok",
                "diet_type": "herbivore",
                "food_requirement_per_animal_per_cycle": 0.5,
                "diet": [
                    {
                        "resource_id": "grass_forage",
                        "preference": 1.0,
                    }
                ],
            }
        )
        region_state = RegionState(
            definition_id="redgrass_savanna",
            animal_populations={
                "scrub_hare": 20,
                "springbok": 20,
            },
            resource_quantities={
                "grass_forage": 10.0,
                "leaves_browse": 10.0,
            },
        )
        feeding_results = feed_region(
            region_state,
            registry,
        )
        self.assertEqual(
            feeding_results["scrub_hare"].consumed_amount,
            10.0,
        )
        self.assertEqual(
            feeding_results["scrub_hare"].nutrition_ratio,
            1.0,
        )
        self.assertEqual(
            feeding_results["scrub_hare"].resource_consumption,
            {
                "grass_forage": 5.0,
                "leaves_browse": 5.0,
            },
        )
        self.assertEqual(
            feeding_results["springbok"].consumed_amount,
            5.0,
        )
        self.assertEqual(
            feeding_results["springbok"].nutrition_ratio,
            0.5,
        )
        self.assertEqual(
            region_state.resource_quantities["grass_forage"],
            0.0,
        )
        self.assertEqual(
            region_state.resource_quantities["leaves_browse"],
            5.0,
        )

    def test_rejects_negative_resource_request(self) -> None:
        region_state = RegionState(
            definition_id="redgrass_savanna",
            resource_quantities={
                "grass_forage": 10.0,
            },
        )

        with self.assertRaisesRegex(
            ValueError,
            r"requested_amount.*must not be negative",
        ):
            consume_available_resource(
                region_state=region_state,
                resource_id="grass_forage",
                requested_amount=-4.0,
            )

    def test_rejects_negative_population_food_requirement(self) -> None:
        animal_definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "food_requirement_per_animal_per_cycle": 0.5,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                }
            ],
        }
        with self.assertRaisesRegex(
            ValueError,
            r"population.*must not be negative",
        ):
            calculate_population_food_requirement(
                population=-4,
                animal_definition=animal_definition,
            )

    def test_rejects_negative_available_resource_quantity(self) -> None:
        region_state = RegionState(
            definition_id="redgrass_savanna",
            resource_quantities={
                "grass_forage": -2.0,
            },
        )

        with self.assertRaisesRegex(
            ValueError,
            r"available resource quantity.*must not be negative",
        ):
            consume_available_resource(
                region_state=region_state,
                resource_id="grass_forage",
                requested_amount=4.0,
            )

    def test_region_feeding_rejects_negative_resource_quantity(self) -> None:
        registry = ContentRegistry()
        registry.register(
            {
                "entity": "animal",
                "id": "scrub_hare",
                "name": "Scrub Hare",
                "diet_type": "herbivore",
                "food_requirement_per_animal_per_cycle": 0.5,
                "diet": [
                    {
                        "resource_id": "grass_forage",
                        "preference": 1.0,
                    }
                ],
            }
        )
        region_state = RegionState(
            definition_id="regrass_savanna",
            animal_populations={
                "scrub_hare": 20,
            },
            resource_quantities={
                "grass_forage": -5.0,
            },
        )
        with self.assertRaisesRegex(
            ValueError,
            r"available resource quantity.*must not be negative",
        ):
            feed_region(
                region_state,
                registry,
            )
if __name__ == "__main__":
    unittest.main()