import unittest
from pathlib import Path

from simulation.scenario_loader import load_scenario

PROJECT_ROOT = Path(__file__).resolve().parents[1]
class TestScenarioLoader(unittest.TestCase):
    def test_loads_playtest_a_scenario_into_world_state(self) -> None:
        scenario_path = (
            PROJECT_ROOT
            / "scenarios"
            / "playtest_a_balanced_beginnings.json"
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
            100
        )
        self.assertEqual(
            region_state.producer_populations["redgrass"],
            500,
        )
        self.assertEqual(
            region_state.resource_quantities["grass_forage"],
            100.0
        )

    def test_preserves_scenario_name(self) -> None:
        scenario_path = PROJECT_ROOT / "scenarios" / "playtest_a_balanced_beginnings.json"

        world_state = load_scenario(scenario_path)

        self.assertEqual(
            world_state.scenario_name,
            "Playtest A — Balanced Beginnings",
        )

    def test_preserves_scenario_description(self) -> None:
        from unittest.mock import patch

        scenario_data = {
            "name": "Balanced Beginnings",
            "description": "Observe feeding and population changes in a savanna.",
            "random_seed": 104729,
            "regions": [],
        }

        with patch(
            "simulation.scenario_loader.load_json_file",
            return_value=scenario_data,
        ):
            world_state = load_scenario(Path("example_scenario.json"))

        self.assertEqual(
            world_state.scenario_description,
            scenario_data["description"],
        )

    def test_loads_starting_shrubs_and_leaves(self) -> None:
        scenario_path = PROJECT_ROOT / "scenarios" / "playtest_a_balanced_beginnings.json"
        world_state = load_scenario(scenario_path)
        region_state = world_state.regions["redgrass_savanna"]

        self.assertEqual(
            region_state.producer_populations["sandpaper_raisin"],
            100,
        )
        self.assertEqual(
            region_state.resource_quantities["leaves_browse"],
            200.0,
        )

    def test_loads_starting_bushbuck_population(self) -> None:
        scenario_path = PROJECT_ROOT / "scenarios" / "playtest_a_balanced_beginnings.json"
        world_state = load_scenario(scenario_path)
        region_state = world_state.regions["redgrass_savanna"]

        self.assertEqual(
            region_state.animal_populations["bushbuck"],
            30,
        )

    def test_grazing_pressure_doubles_animals_in_the_same_environment(self) -> None:
        scenario_directory = PROJECT_ROOT / "scenarios"
        balanced_world = load_scenario(scenario_directory / "playtest_a_balanced_beginnings.json")
        pressure_world = load_scenario(
            scenario_directory / "playtest_a_grazing_pressure.json"
        )
        balanced_region = balanced_world.regions["redgrass_savanna"]
        pressure_region = pressure_world.regions["redgrass_savanna"]

        self.assertEqual(
            pressure_world.scenario_name,
            "Playtest A — Grazing Pressure",
        )
        self.assertEqual(pressure_world.random_seed, balanced_world.random_seed)
        self.assertEqual(
            pressure_region.animal_populations,
            {
                animal_id: population * 2
                for animal_id, population in balanced_region.animal_populations.items()
            },
        )
        self.assertEqual(
            pressure_region.producer_populations,
            balanced_region.producer_populations,
        )
        self.assertEqual(
            pressure_region.resource_quantities,
            balanced_region.resource_quantities,
        )
        self.assertEqual(
            pressure_region.active_weather_id,
            balanced_region.active_weather_id,
        )

    def test_preserves_scenario_id(self) -> None:
        scenario_ids = (
            "playtest_a_balanced_beginnings",
            "playtest_a_grazing_pressure",
        )
        for scenario_id in scenario_ids:
            with self.subTest(scenario=scenario_id):
                scenario_path = (
                    PROJECT_ROOT / "scenarios" / f"{scenario_id}.json"
                )

                world_state = load_scenario(scenario_path)

                self.assertEqual(world_state.scenario_id, scenario_id)
if __name__ == "__main__":
    unittest.main()