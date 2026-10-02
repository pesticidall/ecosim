import unittest
from pathlib import Path

from core.content_catalog import build_content_registry
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
            region_state.weather_weights,
            {
                "seasonal_rain": 1.0,
            },
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

    def test_rejects_unknown_scenario_weather_weight(self) -> None:
        from unittest.mock import patch

        scenario_data = {
            "name": "Test Scenario",
            "random_seed": 104729,
            "regions": [
                {
                    "definition_id": "redgrass_savanna",
                    "active_weather_id": "clear",
                    "weather_weights": {
                        "dust_storm": 1.0,
                    },
                },
            ],
        }
        registry = build_content_registry(
            PROJECT_ROOT / "content"
        )

        with (
            patch(
                "simulation.scenario_loader.load_json_file",
                return_value=scenario_data,
            ),
            self.assertRaisesRegex(
                ValueError,
                r"redgrass_savanna.*unknown weather.*dust_storm",
            ),
        ):
            load_scenario(
                Path("test_scenario.json"),
                registry,
            )

    def test_rejects_invalid_scenario_weather_weight(self) -> None:
        from unittest.mock import patch

        scenario_data = {
            "name": "Test Scenario",
            "random_seed": 104729,
            "regions": [
                {
                    "definition_id": "redgrass_savanna",
                    "active_weather_id": "clear",
                    "weather_weights": {
                        "clear": -1.0,
                    },
                },
            ],
        }

        with (
            patch(
                "simulation.scenario_loader.load_json_file",
                return_value=scenario_data,
            ),
            self.assertRaisesRegex(
                ValueError,
                r"Weather weight for 'clear'.*must not be negative",
            ),
        ):
            load_scenario(Path("test_scenario.json"))

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

    def test_initializes_habitat_state_from_region_content(self) -> None:
        registry = build_content_registry(PROJECT_ROOT / "content")
        scenario_path = (
            PROJECT_ROOT
            / "scenarios"
            / "playtest_a_balanced_beginnings.json"
        )

        world_state = load_scenario(scenario_path, registry)
        region_state = world_state.regions["redgrass_savanna"]

        self.assertEqual(
            list(region_state.habitats),
            [
                "open_grassland",
                "acacia_scrub",
                "rocky_outcrop",
            ],
        )
        for habitat_id, habitat_state in (
            region_state.habitats.items()
        ):
            with self.subTest(habitat_id=habitat_id):
                self.assertEqual(
                    habitat_state.definition_id,
                    habitat_id,
                )
                self.assertFalse(hasattr(habitat_state, "conditions"))

    def test_places_starting_animals_in_preferred_habitats(
        self,
    ) -> None:
        registry = build_content_registry(PROJECT_ROOT / "content")
        scenario_path = (
            PROJECT_ROOT
            / "scenarios"
            / "playtest_a_balanced_beginnings.json"
        )

        world_state = load_scenario(scenario_path, registry)
        region_state = world_state.regions["redgrass_savanna"]

        self.assertEqual(
            region_state.habitats[
                "open_grassland"
            ].animal_populations,
            {
                "scrub_hare": 100,
                "springbok": 40,
            },
        )
        self.assertEqual(
            region_state.habitats[
                "acacia_scrub"
            ].animal_populations,
            {
                "bushbuck": 30,
            },
        )
        self.assertEqual(
            region_state.habitats[
                "rocky_outcrop"
            ].animal_populations,
            {},
        )
        self.assertEqual(
            sum(
                population
                for habitat_state in region_state.habitats.values()
                for population in (
                    habitat_state.animal_populations.values()
                )
            ),
            sum(region_state.animal_populations.values()),
        )

    def test_places_starting_producers_in_preferred_habitats(
        self,
    ) -> None:
        registry = build_content_registry(PROJECT_ROOT / "content")
        scenario_path = (
            PROJECT_ROOT
            / "scenarios"
            / "playtest_a_balanced_beginnings.json"
        )

        world_state = load_scenario(scenario_path, registry)
        region_state = world_state.regions["redgrass_savanna"]

        self.assertEqual(
            region_state.habitats[
                "open_grassland"
            ].producer_populations,
            {
                "redgrass": 500,
            },
        )
        self.assertEqual(
            region_state.habitats[
                "acacia_scrub"
            ].producer_populations,
            {
                "sandpaper_raisin": 100,
            },
        )
        self.assertEqual(
            region_state.habitats[
                "rocky_outcrop"
            ].producer_populations,
            {},
        )
        self.assertEqual(
            sum(
                population
                for habitat_state in region_state.habitats.values()
                for population in (
                    habitat_state.producer_populations.values()
                )
            ),
            sum(region_state.producer_populations.values()),
        )

    def test_distributes_starting_resources_with_their_producers(
        self,
    ) -> None:
        registry = build_content_registry(PROJECT_ROOT / "content")
        scenario_path = (
            PROJECT_ROOT
            / "scenarios"
            / "playtest_a_balanced_beginnings.json"
        )

        world_state = load_scenario(scenario_path, registry)
        region_state = world_state.regions["redgrass_savanna"]

        self.assertEqual(
            region_state.habitats[
                "open_grassland"
            ].resource_quantities,
            {
                "grass_forage": 100.0,
            },
        )
        self.assertEqual(
            region_state.habitats[
                "acacia_scrub"
            ].resource_quantities,
            {
                "leaves_browse": 200.0,
            },
        )
        self.assertEqual(
            region_state.habitats[
                "rocky_outcrop"
            ].resource_quantities,
            {},
        )
        for resource_id, regional_quantity in (
            region_state.resource_quantities.items()
        ):
            with self.subTest(resource_id=resource_id):
                self.assertAlmostEqual(
                    sum(
                        habitat_state.resource_quantities.get(
                            resource_id,
                            0.0,
                        )
                        for habitat_state in (
                            region_state.habitats.values()
                        )
                    ),
                    regional_quantity,
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
