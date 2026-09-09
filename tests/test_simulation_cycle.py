import unittest

from core.content_registry import ContentRegistry
from simulation.feeding import (
    PopulationFeedingResult,
    feed_region,
)
from simulation.mortality import apply_starvation_mortality
from simulation.production import apply_producer_production
from simulation.simulation_cycle import run_cycle
from simulation.world_state import RegionState, WorldState


class TestSimulationCycle(unittest.TestCase):
    def test_advances_time_by_one_cycle(self) -> None:
        world_state = WorldState(random_seed=12345)
        registry = ContentRegistry()
        run_cycle(world_state, registry)
        self.assertEqual(world_state.current_cycle, 1)

    def test_applies_producer_production_to_every_region(self) -> None:
        registry = ContentRegistry()
        registry.register(
            {
                "entity_type": "producer",
                "id": "redgrass",
                "name": "Redgrass",
                "production": [
                    {
                        "resource_id": "grass_forage",
                        "amount_per_producer_per_cycle": 0.25,
                    },
                ],
            }
        )
        region_state = RegionState(
            definition_id="redgrass_savanna",
            producer_populations={"redgrass": 4},
            resource_quantities={"grass_forage": 10.0},
        )
        world_state = WorldState(
            random_seed=12345,
            regions={"redgrass_savanna": region_state},
        )
        run_cycle(world_state, registry)
        self.assertEqual(
            region_state.resource_quantities["grass_forage"],
            11.0
        )

    def test_applies_feeding_after_production(self) -> None:
        registry = ContentRegistry()
        registry.register(
            {
                "entity_type": "producer",
                "id": "redgrass",
                "name": "Redgrass",
                "production": [
                    {
                        "resource_id": "grass_forage",
                        "amount_per_producer_per_cycle": 0.25,
                    }
                ],
            }
        )
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
                "scrub_hare": 4,
            },
            producer_populations={
                "redgrass": 4,
            },
            resource_quantities={
                "grass_forage": 10.0,
            },
        )
        world_state = WorldState(
            random_seed=12345,
            regions={
                "redgrass_savanna": region_state,
            },
        )
        cycle_result = run_cycle(
            world_state,
            registry,
        )
        self.assertEqual(
            region_state.resource_quantities["grass_forage"],
            9.0,
        )
        self.assertEqual(world_state.current_cycle, 1)
        region_result = cycle_result.region_results[
            "redgrass_savanna"
        ]
        self.assertEqual(
            region_result.production_changes,
            {
                "grass_forage": 1.0,
            },
        )
        self.assertEqual(
            region_result.feeding_results[
                "scrub_hare"
            ].required_amount,
            2.0,
        )
        self.assertEqual(
            region_result.feeding_results[
                "scrub_hare"
            ].consumed_amount,
            2.0,
        )
        self.assertEqual(cycle_result.cycle_number, 1)

    def test_applies_starvation_mortality_after_feeding(self) -> None:
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
                ],
            }
        )
        region_state = RegionState(
            definition_id="redgrass_savanna",
            animal_populations={
            "scrub_hare": 20,
            },
            resource_quantities={
            "grass_forage": 5.0,
            }
        )
        world_state = WorldState(
            random_seed=12345,
            regions={
                "redgrass_savanna": region_state,
            },
        )
        cycle_result = run_cycle(
            world_state,
            registry,
        )
        self.assertEqual(
            region_state.animal_populations["scrub_hare"],
            10,
        )
        region_result = cycle_result.region_results[
            "redgrass_savanna"
        ]
        self.assertEqual(
            region_result.starvation_deaths,
            {
                "scrub_hare": 10,
            },
        )


if __name__ == "__main__":
    unittest.main()