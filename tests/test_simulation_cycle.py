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
                "birth_rate_per_animal_per_cycle": 0.0,
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
                "birth_rate_per_animal_per_cycle": 0.0,
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

    def test_applies_reproduction_after_starvation_mortality(self) -> None:
        registry = ContentRegistry()
        registry.register(
            {
                "entity_type": "animal",
                "id": "scrub_hare",
                "name": "Scrub Hare",
                "diet_type": "herbivore",
                "food_requirement_per_animal_per_cycle": 0.5,
                "birth_rate_per_animal_per_cycle": 0.25,
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
            region_state.animal_populations["scrub_hare"],
            25,
        )
        region_result = cycle_result.region_results[
            "redgrass_savanna"
        ]
        self.assertEqual(
            region_result.births,
            {
                "scrub_hare": 5,
            },
        )

    def test_reproduction_uses_post_starvation_population(self) -> None:
        registry = ContentRegistry()
        registry.register(
            {
                "entity_type": "animal",
                "id": "scrub_hare",
                "name": "Scrub Hare",
                "diet_type": "herbivore",
                "food_requirement_per_animal_per_cycle": 0.5,
                "birth_rate_per_animal_per_cycle": 0.25,
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
            animal_populations={"scrub_hare": 20},
            resource_quantities={"grass_forage": 5.0},
        )
        world_state = WorldState(
            random_seed=12345,
            regions={"redgrass_savanna": region_state},
        )

        cycle_result = run_cycle(world_state, registry)

        region_result = cycle_result.region_results["redgrass_savanna"]
        self.assertEqual(
            region_result.feeding_results["scrub_hare"].nutrition_ratio,
            0.5,
        )
        self.assertEqual(region_result.starvation_deaths, {"scrub_hare": 10})
        self.assertEqual(region_result.births, {"scrub_hare": 1})
        self.assertEqual(region_state.animal_populations["scrub_hare"], 11)

    def test_multiple_cycles_preserve_updated_world_state(self) -> None:
        registry = ContentRegistry()
        registry.register(
            {
                "entity_type": "animal",
                "id": "scrub_hare",
                "name": "Scrub Hare",
                "diet_type": "herbivore",
                "food_requirement_per_animal_per_cycle": 0.5,
                "birth_rate_per_animal_per_cycle": 0.25,
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
            animal_populations={"scrub_hare": 20},
            resource_quantities={"grass_forage": 30.0},
        )
        world_state = WorldState(
            random_seed=12345,
            regions={"redgrass_savanna": region_state},
        )

        first_result = run_cycle(world_state, registry)

        self.assertEqual(first_result.cycle_number, 1)
        self.assertEqual(world_state.current_cycle, 1)
        self.assertEqual(region_state.animal_populations["scrub_hare"], 25)
        self.assertEqual(region_state.resource_quantities["grass_forage"], 20.0)

        second_result = run_cycle(world_state, registry)

        self.assertEqual(second_result.cycle_number, 2)
        self.assertEqual(world_state.current_cycle, 2)
        self.assertEqual(region_state.animal_populations["scrub_hare"], 31)
        self.assertEqual(region_state.resource_quantities["grass_forage"], 7.5)
        second_region_result = second_result.region_results["redgrass_savanna"]
        self.assertEqual(
            second_region_result.feeding_results["scrub_hare"].required_amount,
            12.5,
        )
        self.assertEqual(second_region_result.births, {"scrub_hare": 6})
    def test_cycle_applies_seasonal_rain_before_feeding(self) -> None:
        from pathlib import Path

        from core.content_catalog import build_content_registry

        content_root = Path(__file__).resolve().parents[1] / "content"
        registry = build_content_registry(content_root)
        region_state = RegionState(
            definition_id="redgrass_savanna",
            active_weather_id="seasonal_rain",
            producer_populations={"redgrass": 4},
            animal_populations={"scrub_hare": 2},
            resource_quantities={"grass_forage": 0.0},
        )
        world_state = WorldState(
            random_seed=12345,
            regions={"redgrass_savanna": region_state},
        )

        cycle_result = run_cycle(world_state, registry)

        region_result = cycle_result.region_results["redgrass_savanna"]
        feeding_result = region_result.feeding_results["scrub_hare"]
        self.assertEqual(region_result.production_changes["grass_forage"], 1.25)
        self.assertEqual(feeding_result.consumed_amount, 1.0)
        self.assertEqual(feeding_result.nutrition_ratio, 1.0)
        self.assertEqual(region_state.resource_quantities["grass_forage"], 0.25)

    def test_preserves_animal_population_snapshots_between_cycles(self) -> None:
        registry = ContentRegistry()
        registry.register(
            {
                "entity_type": "animal",
                "id": "scrub_hare",
                "name": "Scrub Hare",
                "diet_type": "herbivore",
                "food_requirement_per_animal_per_cycle": 0.5,
                "birth_rate_per_animal_per_cycle": 0.25,
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
            animal_populations={"scrub_hare": 20},
            resource_quantities={"grass_forage": 30.0},
        )
        world_state = WorldState(
            random_seed=12345,
            regions={"redgrass_savanna": region_state},
        )

        first_result = run_cycle(world_state, registry)
        first_region_result = first_result.region_results["redgrass_savanna"]
        run_cycle(world_state, registry)

        self.assertEqual(region_state.animal_populations["scrub_hare"], 31)
        self.assertEqual(
            first_region_result.starting_animal_populations,
            {"scrub_hare": 20},
        )
        self.assertEqual(
            first_region_result.ending_animal_populations,
            {"scrub_hare": 25},
        )

    def test_preserves_resource_snapshots_between_cycles(self) -> None:
        from pathlib import Path

        from core.content_catalog import build_content_registry

        content_root = Path(__file__).resolve().parents[1] / "content"
        registry = build_content_registry(content_root)
        region_state = RegionState(
            definition_id="redgrass_savanna",
            producer_populations={"redgrass": 4},
            animal_populations={"scrub_hare": 4},
            resource_quantities={"grass_forage": 30.0},
        )
        world_state = WorldState(
            random_seed=12345,
            regions={"redgrass_savanna": region_state},
        )

        first_result = run_cycle(world_state, registry)
        first_region_result = first_result.region_results["redgrass_savanna"]
        run_cycle(world_state, registry)

        self.assertEqual(region_state.resource_quantities["grass_forage"], 28.0)
        self.assertEqual(
            first_region_result.starting_resource_quantities,
            {"grass_forage": 30.0},
        )
        self.assertEqual(
            first_region_result.ending_resource_quantities,
            {"grass_forage": 29.0},
        )

    def test_cycle_result_preserves_active_weather(self) -> None:
        registry = ContentRegistry()
        registry.register(
            {
                "entity_type": "weather",
                "id": "seasonal_rain",
                "name": "Seasonal Rain",
                "producer_production_multiplier": 1.25,
            }
        )
        region_state = RegionState(
            definition_id="redgrass_savanna",
            active_weather_id="seasonal_rain",
        )
        world_state = WorldState(
            random_seed=12345,
            regions={"redgrass_savanna": region_state},
        )

        cycle_result = run_cycle(world_state, registry)
        region_result = cycle_result.region_results["redgrass_savanna"]
        region_state.active_weather_id = None

        self.assertEqual(region_result.active_weather_id, "seasonal_rain")

    def test_playtest_scenarios_remain_nonnegative_for_100_cycles(self) -> None:
        from pathlib import Path

        from core.content_catalog import build_content_registry
        from simulation.scenario_loader import load_scenario

        project_root = Path(__file__).resolve().parents[1]
        registry = build_content_registry(project_root / "content")
        scenario_names = (
            "playtest_a_balanced_beginnings.json",
            "playtest_a_grazing_pressure.json",
        )

        for scenario_name in scenario_names:
            world_state = load_scenario(
                project_root / "scenarios" / scenario_name
            )
            for cycle_number in range(1, 101):
                run_cycle(world_state, registry)
                for region_id, region in world_state.regions.items():
                    with self.subTest(
                        scenario=scenario_name,
                        cycle=cycle_number,
                        region=region_id,
                    ):
                        for animal_id, population in region.animal_populations.items():
                            self.assertGreaterEqual(population, 0, animal_id)
                        for producer_id, population in region.producer_populations.items():
                            self.assertGreaterEqual(population, 0, producer_id)
                        for resource_id, quantity in region.resource_quantities.items():
                            self.assertGreaterEqual(quantity, 0.0, resource_id)

    def test_complete_food_exhaustion_leaves_zero_populations(self) -> None:
        from pathlib import Path

        from core.content_catalog import build_content_registry

        registry = build_content_registry(
            Path(__file__).resolve().parents[1] / "content"
        )
        starting_populations = {
            "scrub_hare": 1,
            "springbok": 2,
            "bushbuck": 3,
        }
        empty_populations = {
            animal_id: 0 for animal_id in starting_populations
        }
        empty_resources = {"grass_forage": 0.0, "leaves_browse": 0.0}
        region = RegionState(
            definition_id="redgrass_savanna",
            animal_populations=starting_populations.copy(),
            resource_quantities=empty_resources.copy(),
        )
        world_state = WorldState(
            random_seed=104729,
            regions={"redgrass_savanna": region},
        )

        first_result = run_cycle(world_state, registry)
        first_region = first_result.region_results["redgrass_savanna"]

        self.assertEqual(first_region.starvation_deaths, starting_populations)
        self.assertEqual(first_region.births, empty_populations)
        self.assertEqual(region.animal_populations, empty_populations)
        self.assertEqual(region.resource_quantities, empty_resources)

        second_result = run_cycle(world_state, registry)
        second_region = second_result.region_results["redgrass_savanna"]

        self.assertEqual(second_region.starvation_deaths, empty_populations)
        self.assertEqual(second_region.births, empty_populations)
        self.assertEqual(region.animal_populations, empty_populations)
        self.assertEqual(region.resource_quantities, empty_resources)

    def test_same_scenario_produces_identical_results_for_100_cycles(self) -> None:
        from pathlib import Path

        from core.content_catalog import build_content_registry
        from simulation.scenario_loader import load_scenario

        project_root = Path(__file__).resolve().parents[1]
        first_registry = build_content_registry(project_root / "content")
        second_registry = build_content_registry(project_root / "content")
        scenario_names = (
            "playtest_a_balanced_beginnings.json",
            "playtest_a_grazing_pressure.json",
        )

        for scenario_name in scenario_names:
            scenario_path = project_root / "scenarios" / scenario_name
            first_world = load_scenario(scenario_path)
            second_world = load_scenario(scenario_path)

            for cycle_number in range(1, 101):
                with self.subTest(
                    scenario=scenario_name,
                    cycle=cycle_number,
                ):
                    first_result = run_cycle(first_world, first_registry)
                    second_result = run_cycle(second_world, second_registry)

                    self.assertEqual(first_result, second_result)
                    self.assertEqual(first_world, second_world)

    def test_scarce_food_is_conserved_across_a_complete_cycle(self) -> None:
        from pathlib import Path

        from core.content_catalog import build_content_registry

        registry = build_content_registry(
            Path(__file__).resolve().parents[1] / "content"
        )
        region = RegionState(
            definition_id="redgrass_savanna",
            active_weather_id="seasonal_rain",
            animal_populations={
                "scrub_hare": 10,
                "springbok": 10,
                "bushbuck": 10,
            },
            producer_populations={"redgrass": 1, "sandpaper_raisin": 1},
            resource_quantities={"grass_forage": 1.0, "leaves_browse": 0.5},
        )
        world_state = WorldState(
            random_seed=104729,
            regions={"redgrass_savanna": region},
        )

        cycle_result = run_cycle(world_state, registry)
        region_result = cycle_result.region_results["redgrass_savanna"]
        expected_supply = {"grass_forage": 1.3125, "leaves_browse": 1.125}

        for resource_id, available_amount in expected_supply.items():
            with self.subTest(resource=resource_id):
                consumed_amount = sum(
                    result.resource_consumption.get(resource_id, 0.0)
                    for result in region_result.feeding_results.values()
                )
                self.assertAlmostEqual(consumed_amount, available_amount)
                self.assertGreaterEqual(
                    region.resource_quantities[resource_id], 0.0
                )
                self.assertAlmostEqual(
                    region.resource_quantities[resource_id], 0.0
                )

    def test_starting_report_does_not_change_world_state(self) -> None:
        from copy import deepcopy
        from pathlib import Path

        from core.content_catalog import build_content_registry
        from simulation.reporting import format_starting_report
        from simulation.scenario_loader import load_scenario

        project_root = Path(__file__).resolve().parents[1]
        registry = build_content_registry(project_root / "content")
        scenario_names = (
            "playtest_a_balanced_beginnings.json",
            "playtest_a_grazing_pressure.json",
        )

        for scenario_name in scenario_names:
            with self.subTest(scenario=scenario_name):
                world_state = load_scenario(
                    project_root / "scenarios" / scenario_name
                )
                original_state = deepcopy(world_state)

                first_report = format_starting_report(world_state, registry)
                self.assertEqual(world_state, original_state)

                second_report = format_starting_report(world_state, registry)
                self.assertEqual(world_state, original_state)
                self.assertEqual(first_report, second_report)

    def test_balanced_beginnings_has_a_moderate_decline_and_recovery(self) -> None:
        from pathlib import Path

        from core.content_catalog import build_content_registry
        from simulation.scenario_loader import load_scenario

        project_root = Path(__file__).resolve().parents[1]
        registry = build_content_registry(project_root / "content")
        world = load_scenario(
            project_root / "scenarios" / "playtest_a_balanced_beginnings.json"
        )
        region = world.regions["redgrass_savanna"]
        largest_decline = 0.0
        saw_decline = False
        saw_recovery = False

        for cycle in range(1, 31):
            before = sum(region.animal_populations.values())
            run_cycle(world, registry)
            after = sum(region.animal_populations.values())
            if before > 0:
                largest_decline = max(largest_decline, (before - after) / before)
            if after < before:
                saw_decline = True
            elif saw_decline and after > before:
                saw_recovery = True
            with self.subTest(cycle=cycle):
                for animal_id, population in region.animal_populations.items():
                    self.assertGreaterEqual(population, 10, animal_id)

        self.assertTrue(saw_decline, "Expected a period of population decline.")
        self.assertTrue(saw_recovery, "Expected some recovery after the decline.")
        self.assertLessEqual(largest_decline, 0.20)

    def test_balanced_beginnings_demonstrates_successful_fallback_feeding(self) -> None:
        from math import isclose
        from pathlib import Path

        from core.content_catalog import build_content_registry
        from simulation.scenario_loader import load_scenario

        project_root = Path(__file__).resolve().parents[1]
        registry = build_content_registry(project_root / "content")
        world = load_scenario(
            project_root / "scenarios" / "playtest_a_balanced_beginnings.json"
        )
        successful_fallback_cycles = []

        for cycle in range(1, 31):
            result = run_cycle(world, registry)
            feeding = result.region_results[
                "redgrass_savanna"
            ].feeding_results["springbok"]
            leaves_consumed = feeding.resource_consumption.get(
                "leaves_browse", 0.0
            )
            if leaves_consumed >= 1.0 and isclose(
                feeding.nutrition_ratio, 1.0, abs_tol=1e-9
            ):
                successful_fallback_cycles.append(cycle)

        self.assertTrue(
            successful_fallback_cycles,
            "Expected springbok to meet their food needs using some leaves.",
        )

    def test_grazing_pressure_has_a_severe_early_population_crash(self) -> None:
        from pathlib import Path

        from core.content_catalog import build_content_registry
        from simulation.scenario_loader import load_scenario

        project_root = Path(__file__).resolve().parents[1]
        registry = build_content_registry(project_root / "content")
        world = load_scenario(
            project_root / "scenarios" / "playtest_a_grazing_pressure.json"
        )
        region = world.regions["redgrass_savanna"]
        largest_decline = 0.0

        for _ in range(5):
            before = sum(region.animal_populations.values())
            run_cycle(world, registry)
            after = sum(region.animal_populations.values())
            if before > 0:
                largest_decline = max(largest_decline, (before - after) / before)

        self.assertGreaterEqual(
            largest_decline,
            0.30,
            "Expected at least a 30% single-cycle decline within five cycles.",
        )
if __name__ == "__main__":
    unittest.main()
