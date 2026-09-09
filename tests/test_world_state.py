import unittest

from simulation.world_state import RegionState, WorldState

class TestWorldState(unittest.TestCase):
    def test_stores_seed_and_starts_at_cycle_zero(self) -> None:
        world_state = WorldState(random_seed=12345)
        self.assertEqual(world_state.random_seed, 12345)
        self.assertEqual(world_state.current_cycle, 0)

    def test_stores_region_state_by_definition_id(self) -> None:
        region_state = RegionState(
            definition_id="redgrass_savanna",
        )
        world_state = WorldState(
            random_seed=12345,
            regions={
                "redgrass_savanna": region_state,
            },
        )
        self.assertIs(
            world_state.regions["redgrass_savanna"],
            region_state,
        )
        self.assertEqual(
            region_state.definition_id,
            "redgrass_savanna",
        )

    def test_stores_regional_animal_populations(self) -> None:
        region_state = RegionState(
            definition_id="redgrass_savanna",
            animal_populations={
                "scrub_hare": 80,
            }
        )
        self.assertEqual(
            region_state.animal_populations["scrub_hare"],
            80,
        )

    def test_stores_regional_producer_populations(self) -> None:
        region_state = RegionState(
            definition_id="redgrass_savanna",
            producer_populations={
                "redgrass": 500,
            }
        )
        self.assertEqual(
            region_state.producer_populations["redgrass"],
            500,
        )

    def test_stores_regional_resource_quantities(self) -> None:
        region_state = RegionState(
            definition_id="redgrass_savanna",
            resource_quantities={
                "grass_forage": 1200.5,
            },
        )
        self.assertEqual(
            region_state.resource_quantities["grass_forage"],
            1200.5,
        )
        
    def test_stores_current_regional_weather(self) -> None:
        region_state = RegionState(
            definition_id="redgrass_savanna",
            active_weather_id="seasonal_rain",
        )
        self.assertEqual(
            region_state.active_weather_id,
            "seasonal_rain",
        )
if __name__ == "__main__":
    unittest.main()