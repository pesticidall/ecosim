import unittest
from pathlib import Path

from simulation.scenario_loader import load_scenario

PROJECT_ROOT = Path(__file__).resolve().parents[1]
class TestScenarioLoader(unittest.TestCase):
    def test_loads_playtest_a_scenario_into_world_state(self) -> None:
        scenario_path = (
            PROJECT_ROOT
            / "scenarios"
            / "playtest_a.json"
        )
        world_state = load_scenario(scenario_path)
        region_state = world_state.regions["redgrass_savanna"]
        self.assertEqual(world_state.random_seed, 104729)
        self.assertEqual(world_state.current_cycle, 0)
        self.assertEqual(
            region_state.definition_id,
            "redgrass_savanna",
        )
        self.assertEqual(
            region_state.active_weather_id,
            "seasonal_rain",
        )
        self.assertEqual(
            region_state.animal_populations["scrub_hare"],
            80
        )
        self.assertEqual(
            region_state.producer_populations["redgrass"],
            500,
        )
        self.assertEqual(
            region_state.resource_quantities["grass_forage"],
            1200.5
        )
if __name__ == "__main__":
    unittest.main()