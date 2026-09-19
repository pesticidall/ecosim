import unittest

from core.content_registry import ContentRegistry
from simulation.reporting import (
    format_cycle_report,
    format_run_header,
)
from simulation.simulation_cycle import (
    CycleResult,
    RegionCycleResult,
)
from simulation.world_state import WorldState


class TestReporting(unittest.TestCase):
    def test_run_header_includes_random_seed(self) -> None:
        world_state = WorldState(random_seed=104729)
        report_text = format_run_header(world_state)
        self.assertIn("Random seed: 104729", report_text)

    def test_run_header_includes_release_identifier(self) -> None:
        world_state = WorldState(random_seed=104729)

        report_text = format_run_header(world_state)

        self.assertIn("EcoSim release: playtest-a.1", report_text.splitlines())
        self.assertIn("Random seed: 104729", report_text.splitlines())

    def test_cycle_report_includes_cycle_number(self) -> None:
        cycle_result = CycleResult(
            cycle_number=7,
            region_results={},
        )

        report_text = format_cycle_report(cycle_result, registry=ContentRegistry())
        self.assertIn("Cycle 7", report_text.splitlines())

    def test_cycle_report_includes_region_name(self) -> None:
        registry = ContentRegistry()
        registry.register(
            {
                "entity_type": "region",
                "id": "redgrass_savanna",
                "name": "Redgrass Savanna",
            }
        )
        cycle_result = CycleResult(
            cycle_number=7,
            region_results={
                "redgrass_savanna": RegionCycleResult(
                    production_changes={},
                    feeding_results={},
                    starvation_deaths={},
                    births={},
                ),
            },
        )
        report_text = format_cycle_report(cycle_result, registry=registry)
        self.assertIn("Redgrass Savanna", report_text.splitlines())

    def test_cycle_report_includes_resource_production(self) -> None:
        registry = ContentRegistry()
        registry.register(
            {
                "entity_type": "region",
                "id": "redgrass_savanna",
                "name": "Redgrass Savanna",
            }
        )
        registry.register(
            {
                "entity_type": "resource",
                "id": "grass_forage",
                "name": "Grass",
                "quantity_type": "biomass",
                "unit": "kg",
            }
        )
        cycle_result = CycleResult(
            cycle_number=7,
            region_results={
                "redgrass_savanna": RegionCycleResult(
                    production_changes={"grass_forage": 120.0},
                    feeding_results={},
                    starvation_deaths={},
                    births={},
                ),
            },
        )
        report_text = format_cycle_report(cycle_result, registry=registry)
        self.assertIn("PRODUCTION\nGrass .......................... +120 kg", report_text)

    def test_cycle_report_includes_food_consumed_by_species(self) -> None:
        from simulation.feeding import PopulationFeedingResult
        registry = ContentRegistry()
        registry.register_all(
            [
                {
                    "entity_type": "region",
                    "id": "redgrass_savanna",
                    "name": "Redgrass Savanna",
                },
                {
                    "entity_type": "animal",
                    "id": "scrub_hare",
                    "name": "Scrub Hare",
                },
                {
                    "entity_type": "resource",
                    "id": "grass_forage",
                    "name": "Grass",
                    "quantity_type": "biomass",
                    "unit": "kg",
                },
            ]
        )
        cycle_result = CycleResult(
            cycle_number=7,
            region_results={
                "redgrass_savanna": RegionCycleResult(
                    production_changes={},
                    feeding_results={
                        "scrub_hare": PopulationFeedingResult(
                            required_amount=108.0,
                            consumed_amount=108.0,
                            nutrition_ratio=1.0,
                            resource_consumption={"grass_forage": 108.0},
                        ),
                    },
                    starvation_deaths={},
                    births={},
                ),
            },
        )
        report_text = format_cycle_report(cycle_result, registry=registry)
        self.assertIn(
            "FEEDING\nScrub Hare consumed:\nGrass .......................... 108",
            report_text,
        )

    def test_cycle_report_warns_only_about_underfed_species(self) -> None:
        from simulation.feeding import PopulationFeedingResult

        registry = ContentRegistry()
        registry.register_all(
            [
                {
                    "entity_type": "region",
                    "id": "redgrass_savanna",
                    "name": "Redgrass Savanna",
                },
                {
                    "entity_type": "animal",
                    "id": "scrub_hare",
                    "name": "Scrub Hare",
                },
                {
                    "entity_type": "animal",
                    "id": "springbok",
                    "name": "Springbok",
                },
                {
                    "entity_type": "resource",
                    "id": "grass_forage",
                    "name": "Grass",
                    "quantity_type": "biomass",
                    "unit": "kg",
                },
            ]
        )
        cycle_result = CycleResult(
            cycle_number=7,
            region_results={
                "redgrass_savanna": RegionCycleResult(
                    production_changes={},
                    feeding_results={
                        "scrub_hare": PopulationFeedingResult(
                            required_amount=10.0,
                            consumed_amount=10.0,
                            nutrition_ratio=1.0,
                            resource_consumption={"grass_forage": 10.0},
                        ),
                        "springbok": PopulationFeedingResult(
                            required_amount=100.0,
                            consumed_amount=82.0,
                            nutrition_ratio=0.82,
                            resource_consumption={"grass_forage": 82.0},
                        ),
                    },
                    starvation_deaths={},
                    births={},
                ),
            },
        )

        report_text = format_cycle_report(cycle_result, registry=registry)

        self.assertIn(
            "FOOD SHORTAGES\nSpringbok received 82.0% of required food.",
            report_text,
        )
        self.assertNotIn("Scrub Hare received", report_text)

    def test_cycle_report_does_not_round_shortage_up_to_full_feeding(self) -> None:
        from simulation.feeding import PopulationFeedingResult

        registry = ContentRegistry()
        registry.register_all([
            {
                "entity_type": "region",
                "id": "redgrass_savanna",
                "name": "Redgrass Savanna",
            },
            {
                "entity_type": "animal",
                "id": "springbok",
                "name": "Springbok",
            },
            {
                "entity_type": "resource",
                "id": "grass_forage",
                "name": "Grass",
                "quantity_type": "biomass",
                "unit": "kg",
            },
        ])
        feeding_result = PopulationFeedingResult(
            required_amount=100.0,
            consumed_amount=99.99,
            nutrition_ratio=0.9999,
            resource_consumption={"grass_forage": 99.99},
        )
        cycle_result = CycleResult(
            cycle_number=7,
            region_results={
                "redgrass_savanna": RegionCycleResult(
                    production_changes={},
                    feeding_results={"springbok": feeding_result},
                    starvation_deaths={},
                    births={},
                ),
            },
        )

        report_text = format_cycle_report(cycle_result, registry=registry)

        self.assertIn(
            "FOOD SHORTAGES\n"
            "Springbok received less than 100.0% of required food.",
            report_text,
        )
        self.assertEqual(feeding_result.nutrition_ratio, 0.9999)
        self.assertEqual(feeding_result.consumed_amount, 99.99)

    def test_cycle_report_includes_births_and_starvation_deaths(self) -> None:
        registry = ContentRegistry()
        registry.register_all(
            [
                {
                    "entity_type": "region",
                    "id": "redgrass_savanna",
                    "name": "Redgrass Savanna",
                },
                {
                    "entity_type": "animal",
                    "id": "scrub_hare",
                    "name": "Scrub Hare",
                },
            ]
        )
        cycle_result = CycleResult(
            cycle_number=7,
            region_results={
                "redgrass_savanna": RegionCycleResult(
                    production_changes={},
                    feeding_results={},
                    starvation_deaths={"scrub_hare": 2},
                    births={"scrub_hare": 5},
                ),
            },
        )

        report_text = format_cycle_report(cycle_result, registry=registry)

        self.assertIn(
            "POPULATION CHANGES\n"
            "Scrub Hare:\n  +5 births, -2 starvation deaths",
            report_text,
        )

    def test_cycle_report_includes_starting_and_ending_populations(self) -> None:
        registry = ContentRegistry()
        registry.register_all(
            [
                {
                    "entity_type": "region",
                    "id": "redgrass_savanna",
                    "name": "Redgrass Savanna",
                },
                {
                    "entity_type": "animal",
                    "id": "scrub_hare",
                    "name": "Scrub Hare",
                },
            ]
        )
        cycle_result = CycleResult(
            cycle_number=7,
            region_results={
                "redgrass_savanna": RegionCycleResult(
                    production_changes={},
                    feeding_results={},
                    starvation_deaths={"scrub_hare": 2},
                    births={"scrub_hare": 5},
                    starting_animal_populations={"scrub_hare": 65},
                    ending_animal_populations={"scrub_hare": 68},
                ),
            },
        )

        report_text = format_cycle_report(cycle_result, registry=registry)

        self.assertIn(
            "Scrub Hare ..................... 65 → 68\n  +5 births, -2 starvation deaths",
            report_text,
        )

    def test_cycle_report_includes_starting_and_ending_resource(self) -> None:
        registry = ContentRegistry()
        registry.register_all(
            [
                {
                    "entity_type": "region",
                    "id": "redgrass_savanna",
                    "name": "Redgrass Savanna",
                },
                {
                    "entity_type": "resource",
                    "id": "grass_forage",
                    "name": "Grass",
                    "quantity_type": "biomass",
                    "unit": "kg",
                },
            ]
        )
        cycle_result = CycleResult(
            cycle_number=7,
            region_results={
                "redgrass_savanna": RegionCycleResult(
                    production_changes={},
                    feeding_results={},
                    starvation_deaths={},
                    births={},
                    starting_resource_quantities={"grass_forage": 30.0},
                    ending_resource_quantities={"grass_forage": 29.0},
                ),
            },
        )
        report_text = format_cycle_report(cycle_result, registry=registry)
        self.assertIn(
            "REGIONAL TOTALS\nGrass .......................... 30 → 29 kg",
            report_text,
        )

    def test_cycle_report_includes_total_animals(self) -> None:
        registry = ContentRegistry()
        registry.register_all(
            [
                {
                    "entity_type": "region",
                    "id": "redgrass_savanna",
                    "name": "Redgrass Savanna",
                },
                {
                    "entity_type": "animal",
                    "id": "scrub_hare",
                    "name": "Scrub Hare",
                },
                {
                    "entity_type": "animal",
                    "id": "springbok",
                    "name": "Springbok",
                },
            ]
        )
        cycle_result = CycleResult(
            cycle_number=7,
            region_results={
                "redgrass_savanna": RegionCycleResult(
                    production_changes={},
                    feeding_results={},
                    starvation_deaths={"scrub_hare": 2, "springbok": 2},
                    births={"scrub_hare": 5, "springbok": 0},
                    starting_animal_populations={
                        "scrub_hare": 65,
                        "springbok": 18,
                    },
                    ending_animal_populations={
                        "scrub_hare": 68,
                        "springbok": 16,
                    },
                ),
            },
        )

        report_text = format_cycle_report(cycle_result, registry=registry)

        self.assertIn(
            "REGIONAL TOTALS\nTotal animals .................. 83 → 84",
            report_text,
        )

    def test_warns_when_combined_consumption_exceeds_production(self) -> None:
        from simulation.feeding import PopulationFeedingResult

        registry = ContentRegistry()
        registry.register_all(
            [
                {
                    "entity_type": "region",
                    "id": "redgrass_savanna",
                    "name": "Redgrass Savanna",
                },
                {
                    "entity_type": "animal",
                    "id": "scrub_hare",
                    "name": "Scrub Hare",
                },
                {
                    "entity_type": "animal",
                    "id": "springbok",
                    "name": "Springbok",
                },
                {
                    "entity_type": "resource",
                    "id": "grass_forage",
                    "name": "Grass",
                    "quantity_type": "biomass",
                    "unit": "kg",
                },
            ]
        )
        cycle_result = CycleResult(
            cycle_number=7,
            region_results={
                "redgrass_savanna": RegionCycleResult(
                    production_changes={"grass_forage": 120.0},
                    feeding_results={
                        "scrub_hare": PopulationFeedingResult(
                            required_amount=60.0,
                            consumed_amount=60.0,
                            nutrition_ratio=1.0,
                            resource_consumption={"grass_forage": 60.0},
                        ),
                        "springbok": PopulationFeedingResult(
                            required_amount=80.0,
                            consumed_amount=80.0,
                            nutrition_ratio=1.0,
                            resource_consumption={"grass_forage": 80.0},
                        ),
                    },
                    starvation_deaths={},
                    births={},
                ),
            },
        )

        report_text = format_cycle_report(cycle_result, registry=registry)

        self.assertIn(
            "NOTABLE EVENTS\n"
            "! Grass consumption exceeded this cycle's production.",
            report_text,
        )

    def test_omits_warning_when_consumption_equals_production(self) -> None:
        from simulation.feeding import PopulationFeedingResult

        registry = ContentRegistry()
        registry.register_all(
            [
                {
                    "entity_type": "region",
                    "id": "redgrass_savanna",
                    "name": "Redgrass Savanna",
                },
                {
                    "entity_type": "animal",
                    "id": "scrub_hare",
                    "name": "Scrub Hare",
                },
                {
                    "entity_type": "animal",
                    "id": "springbok",
                    "name": "Springbok",
                },
                {
                    "entity_type": "resource",
                    "id": "grass_forage",
                    "name": "Grass",
                    "quantity_type": "biomass",
                    "unit": "kg",
                },
            ]
        )
        cycle_result = CycleResult(
            cycle_number=7,
            region_results={
                "redgrass_savanna": RegionCycleResult(
                    production_changes={"grass_forage": 140.0},
                    feeding_results={
                        "scrub_hare": PopulationFeedingResult(
                            required_amount=60.0,
                            consumed_amount=60.0,
                            nutrition_ratio=1.0,
                            resource_consumption={"grass_forage": 60.0},
                        ),
                        "springbok": PopulationFeedingResult(
                            required_amount=80.0,
                            consumed_amount=80.0,
                            nutrition_ratio=1.0,
                            resource_consumption={"grass_forage": 80.0},
                        ),
                    },
                    starvation_deaths={},
                    births={},
                ),
            },
        )

        report_text = format_cycle_report(cycle_result, registry=registry)

        self.assertNotIn(
            "! Grass consumption exceeded this cycle's production.",
            report_text,
        )
        self.assertNotIn("NOTABLE EVENTS", report_text.splitlines())

    def test_cycle_report_includes_recorded_weather_name(self) -> None:
        registry = ContentRegistry()
        registry.register_all(
            [
                {
                    "entity_type": "region",
                    "id": "redgrass_savanna",
                    "name": "Redgrass Savanna",
                },
                {
                    "entity_type": "weather",
                    "id": "seasonal_rain",
                    "name": "Seasonal Rain",
                },
            ]
        )
        cycle_result = CycleResult(
            cycle_number=7,
            region_results={
                "redgrass_savanna": RegionCycleResult(
                    production_changes={},
                    feeding_results={},
                    starvation_deaths={},
                    births={},
                    active_weather_id="seasonal_rain",
                ),
            },
        )

        report_text = format_cycle_report(cycle_result, registry=registry)

        self.assertIn("Weather: Seasonal Rain", report_text.splitlines())

    def test_starting_report_includes_cycle_and_seed(self) -> None:
        from simulation.reporting import format_starting_report

        world_state = WorldState(random_seed=104729)
        registry = ContentRegistry()

        report_text = format_starting_report(world_state, registry)

        report_lines = report_text.splitlines()
        self.assertIn("STARTING REPORT", report_lines)
        self.assertIn("Starting cycle: 0", report_lines)
        self.assertIn("Random seed: 104729", report_lines)

    def test_starting_report_includes_region_and_weather(self) -> None:
        from simulation.reporting import format_starting_report
        from simulation.world_state import RegionState

        registry = ContentRegistry()
        registry.register_all(
            [
                {
                    "entity_type": "region",
                    "id": "redgrass_savanna",
                    "name": "Redgrass Savanna",
                },
                {
                    "entity_type": "weather",
                    "id": "seasonal_rain",
                    "name": "Seasonal Rain",
                },
            ]
        )
        region_state = RegionState(
            definition_id="redgrass_savanna",
            active_weather_id="seasonal_rain",
        )
        world_state = WorldState(
            random_seed=104729,
            regions={"redgrass_savanna": region_state},
        )

        report_text = format_starting_report(world_state, registry)

        self.assertIn(
            "Redgrass Savanna\nWeather: Seasonal Rain",
            report_text,
        )

    def test_exports_reports_in_order(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from simulation.reporting import export_run_report

        reports = [
            "STARTING REPORT\nRandom seed: 104729",
            "Cycle 1\nTotal animals: 80 → 100",
            "Cycle 2\nTotal animals: 100 → 125",
        ]

        with TemporaryDirectory() as temporary_directory:
            report_path = Path(temporary_directory) / "run_report.txt"
            export_run_report(reports, report_path)
            saved_text = report_path.read_text(encoding="utf-8")

        self.assertEqual(
            saved_text,
            "STARTING REPORT\nRandom seed: 104729\n\n"
            "Cycle 1\nTotal animals: 80 → 100\n\n"
            "Cycle 2\nTotal animals: 100 → 125\n",
        )

    def test_starting_report_includes_scenario_name(self) -> None:
        from simulation.reporting import format_starting_report

        world_state = WorldState(
            random_seed=104729,
            scenario_name="Balanced Beginnings",
        )

        report_text = format_starting_report(
            world_state,
            registry=ContentRegistry(),
        )

        self.assertTrue(
            report_text.startswith(
                "STARTING REPORT\nScenario: Balanced Beginnings\n"
            ),
            report_text,
        )

    def test_starting_report_includes_scenario_description(self) -> None:
        from simulation.reporting import format_starting_report

        world_state = WorldState(
            random_seed=104729,
            scenario_name="Balanced Beginnings",
            scenario_description="Observe feeding and population changes in a savanna.",
        )

        report_text = format_starting_report(
            world_state,
            registry=ContentRegistry(),
        )

        self.assertIn(
            "Scenario: Balanced Beginnings\n"
            "Description: Observe feeding and population changes in a savanna.\n",
            report_text,
        )

    def test_frames_report_with_wrapping_and_blank_lines(self) -> None:
        from simulation.reporting import frame_report

        report_text = "Grass: 40 kg\n\nHares share the grass."

        framed_text = frame_report(report_text, width=12)

        self.assertEqual(
            framed_text.splitlines(),
            [
                "╔══════════════╗",
                "║ Grass: 40 kg ║",
                "║              ║",
                "║ Hares share  ║",
                "║ the grass.   ║",
                "╚══════════════╝",
            ],
        )

    def test_omits_consumption_warning_for_rounding_noise(self) -> None:
        from pathlib import Path

        from core.content_catalog import build_content_registry
        from simulation.feeding import PopulationFeedingResult

        content_root = Path(__file__).resolve().parents[1] / "content"
        registry = build_content_registry(content_root)
        consumed_amount = 0.1 + 0.2

        cycle_result = CycleResult(
            cycle_number=1,
            region_results={
                "redgrass_savanna": RegionCycleResult(
                    production_changes={"grass_forage": 0.3},
                    feeding_results={
                        "scrub_hare": PopulationFeedingResult(
                            required_amount=consumed_amount,
                            consumed_amount=consumed_amount,
                            nutrition_ratio=1.0,
                            resource_consumption={"grass_forage": consumed_amount},
                        ),
                    },
                    starvation_deaths={},
                    births={},
                ),
            },
        )

        report_text = format_cycle_report(cycle_result, registry)

        self.assertNotIn(
            "! Grass consumption exceeded this cycle's production.",
            report_text,
        )
        self.assertNotIn("NOTABLE EVENTS", report_text.splitlines())

    def test_reports_when_a_resource_reserve_is_exhausted(self) -> None:
        registry = ContentRegistry()
        registry.register_all(
            [
                {
                    "entity_type": "region",
                    "id": "redgrass_savanna",
                    "name": "Redgrass Savanna",
                },
                {
                    "entity_type": "resource",
                    "id": "grass_forage",
                    "name": "Grass",
                    "quantity_type": "biomass",
                    "unit": "kg",
                },
            ]
        )
        cycle_result = CycleResult(
            cycle_number=8,
            region_results={
                "redgrass_savanna": RegionCycleResult(
                    production_changes={},
                    feeding_results={},
                    starvation_deaths={},
                    births={},
                    starting_resource_quantities={"grass_forage": 100.0},
                    ending_resource_quantities={"grass_forage": 0.0},
                ),
            },
        )

        report_text = format_cycle_report(cycle_result, registry=registry)

        self.assertIn(
            "NOTABLE EVENTS\n"
            "! Grass reserves were exhausted this cycle.",
            report_text,
        )

    def test_omits_depletion_event_when_reserve_was_already_empty(self) -> None:
        registry = ContentRegistry()
        registry.register_all(
            [
                {
                    "entity_type": "region",
                    "id": "redgrass_savanna",
                    "name": "Redgrass Savanna",
                },
                {
                    "entity_type": "resource",
                    "id": "grass_forage",
                    "name": "Grass",
                    "quantity_type": "biomass",
                    "unit": "kg",
                },
            ]
        )
        cycle_result = CycleResult(
            cycle_number=9,
            region_results={
                "redgrass_savanna": RegionCycleResult(
                    production_changes={},
                    feeding_results={},
                    starvation_deaths={},
                    births={},
                    starting_resource_quantities={"grass_forage": 0.0},
                    ending_resource_quantities={"grass_forage": 0.0},
                ),
            },
        )

        report_text = format_cycle_report(cycle_result, registry=registry)

        self.assertNotIn("reserves were exhausted", report_text)
        self.assertNotIn("NOTABLE EVENTS", report_text.splitlines())

    def test_reports_when_an_animal_uses_fallback_food(self) -> None:
        from pathlib import Path

        from core.content_catalog import build_content_registry
        from simulation.feeding import PopulationFeedingResult

        registry = build_content_registry(
            Path(__file__).resolve().parents[1] / "content"
        )
        cycle_result = CycleResult(
            cycle_number=8,
            region_results={
                "redgrass_savanna": RegionCycleResult(
                    production_changes={},
                    feeding_results={
                        "springbok": PopulationFeedingResult(
                            required_amount=100.0,
                            consumed_amount=100.0,
                            nutrition_ratio=1.0,
                            resource_consumption={
                                "grass_forage": 60.0,
                                "leaves_browse": 40.0,
                            },
                        ),
                    },
                    starvation_deaths={},
                    births={},
                ),
            },
        )

        report_text = format_cycle_report(cycle_result, registry=registry)

        self.assertIn(
            "! Springbok used Leaves because its preferred food was insufficient.",
            report_text.split("NOTABLE EVENTS\n", 1)[-1].splitlines(),
        )

    def test_omits_fallback_event_when_no_alternative_food_was_eaten(self) -> None:
        from pathlib import Path

        from core.content_catalog import build_content_registry
        from simulation.feeding import PopulationFeedingResult

        registry = build_content_registry(
            Path(__file__).resolve().parents[1] / "content"
        )
        cycle_result = CycleResult(
            cycle_number=9,
            region_results={
                "redgrass_savanna": RegionCycleResult(
                    production_changes={"grass_forage": 60.0},
                    feeding_results={
                        "springbok": PopulationFeedingResult(
                            required_amount=100.0,
                            consumed_amount=60.0,
                            nutrition_ratio=0.6,
                            resource_consumption={
                                "grass_forage": 60.0,
                                "leaves_browse": 0.0,
                            },
                        ),
                    },
                    starvation_deaths={},
                    births={},
                ),
            },
        )

        report_text = format_cycle_report(cycle_result, registry=registry)

        self.assertNotIn("Springbok used Leaves", report_text)
        self.assertIn(
            "Springbok received 60.0% of required food.",
            report_text,
        )

    def test_reports_when_a_species_dies_out_in_a_region(self) -> None:
        from pathlib import Path

        from core.content_catalog import build_content_registry

        registry = build_content_registry(
            Path(__file__).resolve().parents[1] / "content"
        )
        cycle_result = CycleResult(
            cycle_number=10,
            region_results={
                "redgrass_savanna": RegionCycleResult(
                    production_changes={},
                    feeding_results={},
                    starvation_deaths={"scrub_hare": 5},
                    births={},
                    starting_animal_populations={"scrub_hare": 5},
                    ending_animal_populations={"scrub_hare": 0},
                ),
            },
        )

        report_text = format_cycle_report(cycle_result, registry=registry)

        self.assertIn(
            "NOTABLE EVENTS\n"
            "! Scrub Hare died out in Redgrass Savanna this cycle.",
            report_text,
        )

    def test_omits_extinction_event_when_species_was_already_absent(self) -> None:
        from pathlib import Path

        from core.content_catalog import build_content_registry

        registry = build_content_registry(
            Path(__file__).resolve().parents[1] / "content"
        )
        cycle_result = CycleResult(
            cycle_number=11,
            region_results={
                "redgrass_savanna": RegionCycleResult(
                    production_changes={},
                    feeding_results={},
                    starvation_deaths={},
                    births={},
                    starting_animal_populations={"scrub_hare": 0},
                    ending_animal_populations={"scrub_hare": 0},
                ),
            },
        )

        report_text = format_cycle_report(cycle_result, registry=registry)

        self.assertNotIn("died out", report_text)
        self.assertNotIn("NOTABLE EVENTS", report_text.splitlines())

    def test_formats_resource_amounts_with_at_most_two_decimal_places(self) -> None:
        from simulation.reporting import format_resource_amount

        examples = (
            (147.961, "147.96"),
            (8.28912, "8.29"),
            (62.5, "62.5"),
            (200.0, "200"),
            (0.0, "0"),
        )
        for amount, expected_text in examples:
            with self.subTest(amount=amount):
                self.assertEqual(format_resource_amount(amount), expected_text)

    def test_uses_singular_words_for_one_birth_and_one_death(self) -> None:
        from pathlib import Path

        from core.content_catalog import build_content_registry

        registry = build_content_registry(
            Path(__file__).resolve().parents[1] / "content"
        )
        cycle_result = CycleResult(
            cycle_number=10,
            region_results={
                "redgrass_savanna": RegionCycleResult(
                    production_changes={},
                    feeding_results={},
                    starvation_deaths={"scrub_hare": 1},
                    births={"scrub_hare": 1},
                    starting_animal_populations={"scrub_hare": 10},
                    ending_animal_populations={"scrub_hare": 10},
                ),
            },
        )

        report_text = format_cycle_report(cycle_result, registry=registry)

        self.assertIn(
            "  +1 birth, -1 starvation death",
            report_text.splitlines(),
        )

    def test_starting_report_explains_species_diets(self) -> None:
        from pathlib import Path

        from core.content_catalog import build_content_registry
        from simulation.reporting import format_starting_report
        from simulation.scenario_loader import load_scenario

        project_root = Path(__file__).resolve().parents[1]
        registry = build_content_registry(project_root / "content")
        world_state = load_scenario(
            project_root / "scenarios" / "playtest_a_balanced_beginnings.json"
        )

        report_text = format_starting_report(world_state, registry)

        self.assertIn(
            "DIETS\n"
            "Bushbuck ....................... Leaves\n"
            "Scrub Hare ..................... Grass\n"
            "Springbok ...................... Grass preferred; Leaves alternative",
            report_text,
        )
if __name__ == "__main__":
    unittest.main()