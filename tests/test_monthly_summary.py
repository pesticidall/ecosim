import unittest
from copy import deepcopy
from dataclasses import replace

from core.content_registry import ContentRegistry
from simulation.calendar import CalendarState, Month, days_in_month
from simulation.daily_cycle import run_day
from simulation.monthly_cycle import acknowledge_month_review
from simulation.monthly_reporting import format_monthly_ecology_report
from simulation.monthly_summary import summarize_month
from simulation.world_state import HabitatState, RegionState, WorldState


class TestMonthlySummary(unittest.TestCase):
    def setup_world(self, year=1, month=Month.JANUARY):
        registry = ContentRegistry()
        registry.register_all([
            {"id": "region", "entity_type": "region", "name": "Test Region"},
            {"id": "local", "entity_type": "habitat", "name": "Local",
             "conditions": {"openness": 1.0, "vegetation_density": 0.0}},
            {"id": "clear", "entity_type": "weather", "name": "Clear"},
            {"id": "food", "entity_type": "resource", "name": "Food", "unit": "kg"},
            {"id": "plant", "entity_type": "producer", "production": [
                {"resource_id": "food", "amount_per_producer_per_day": 1.0},
            ]},
            {"id": "grazer", "entity_type": "animal", "name": "Grazer",
             "food_requirement_per_animal_per_cycle": 31.0,
             "birth_rate_per_animal_per_cycle": 1.0,
             "diet": [{"resource_id": "food", "preference": 1.0}]},
        ])
        habitat = HabitatState("local", animal_populations={"grazer": 1},
                               producer_populations={"plant": 1}, resource_quantities={"food": 10.0})
        region = RegionState("region", active_weather_id="clear", habitats={"local": habitat},
                             animal_populations={"grazer": 1}, producer_populations={"plant": 1},
                             resource_quantities={"food": 10.0})
        world = WorldState(random_seed=1, calendar=CalendarState(year, month), regions={"region": region})
        return world, registry

    def complete_month(self, world, registry):
        for _ in range(days_in_month(world.calendar.year, world.calendar.month)):
            run_day(world, registry)

    def test_monthly_summary_uses_all_daily_totals_and_boundary_snapshots(self):
        world, registry = self.setup_world()
        self.complete_month(world, registry)
        summary = summarize_month(world, 1, Month.JANUARY)
        region = summary.region_results["region"]
        self.assertEqual(region.production_changes, {"food": 31.0})
        self.assertEqual(region.resource_consumption, {"food": 31.0})
        self.assertEqual(region.feeding_results["grazer"].consumed_amount, 31.0)
        self.assertEqual(region.births, {"grazer": 1})
        self.assertEqual(region.starvation_deaths, {"grazer": 0})
        self.assertEqual(region.starting_state.animal_populations, {"grazer": 1})
        self.assertEqual(region.ending_state.animal_populations, {"grazer": 2})
        self.assertEqual(region.ending_state.resource_quantities, {"food": 10.0})
        self.assertEqual(region.weather_day_totals, {"clear": 31})
        self.assertEqual([day.day for day in summary.days], list(range(1, 32)))

    def test_summary_is_read_only_and_does_not_draw_randomness(self):
        world, registry = self.setup_world()
        self.complete_month(world, registry)
        before, random_before = deepcopy(world), world.random_generator.getstate()
        first = summarize_month(world, 1, Month.JANUARY)
        self.assertEqual(first, summarize_month(world, 1, Month.JANUARY))
        self.assertEqual(world, before)
        self.assertEqual(world.random_generator.getstate(), random_before)

    def test_full_month_lengths_include_gregorian_leap_rules(self):
        for year, month, length in ((1, Month.JANUARY, 31), (1, Month.APRIL, 30),
                                    (1, Month.FEBRUARY, 28), (4, Month.FEBRUARY, 29),
                                    (100, Month.FEBRUARY, 28), (400, Month.FEBRUARY, 29)):
            with self.subTest(year=year, month=month):
                world, registry = self.setup_world(year, month)
                # Ensure February food demand is fully supported.
                world.regions["region"].habitats["local"].resource_quantities["food"] = 100.0
                world.regions["region"].resource_quantities["food"] = 100.0
                self.complete_month(world, registry)
                result = summarize_month(world, year, month)
                self.assertEqual(len(result.days), length)
                self.assertEqual(result.region_results["region"].production_changes["food"], length)
                self.assertAlmostEqual(result.region_results["region"].feeding_results["grazer"].required_amount, 31.0)

    def test_partial_month_and_missing_record_are_rejected(self):
        world, registry = self.setup_world()
        run_day(world, registry)
        with self.assertRaisesRegex(ValueError, "complete daily history"):
            summarize_month(world, 1, Month.JANUARY)
        for _ in range(30):
            run_day(world, registry)
        del world.daily_history[1][Month.JANUARY][18]
        with self.assertRaisesRegex(ValueError, "complete daily history"):
            summarize_month(world, 1, Month.JANUARY)

    def test_mismatched_dates_and_regions_are_rejected(self):
        world, registry = self.setup_world()
        self.complete_month(world, registry)
        original = world.daily_history[1][Month.JANUARY][2]
        world.daily_history[1][Month.JANUARY][2] = replace(original, day=1)
        with self.assertRaisesRegex(ValueError, "mismatched calendar date"):
            summarize_month(world, 1, Month.JANUARY)
        world.daily_history[1][Month.JANUARY][2] = replace(original, region_results={})
        with self.assertRaisesRegex(ValueError, "consistent regions"):
            summarize_month(world, 1, Month.JANUARY)

    def test_later_live_state_changes_do_not_rewrite_old_report(self):
        world, registry = self.setup_world()
        self.complete_month(world, registry)
        original = summarize_month(world, 1, Month.JANUARY)
        text = format_monthly_ecology_report(original, registry)
        acknowledge_month_review(world)
        for _ in range(5):
            run_day(world, registry)
        world.regions["region"].animal_populations["grazer"] = 999
        world.regions["region"].resource_quantities["food"] = 999.0
        rebuilt = summarize_month(world, 1, Month.JANUARY)
        self.assertEqual(rebuilt, original)
        self.assertEqual(format_monthly_ecology_report(rebuilt, registry), text)
        self.assertIn("January, Year 1 (31 completed days)", text)
        self.assertIn("Grazer: 1 → 2; 1 birth", text)
        self.assertIn("Grazer: 100.0% of required food.", text)
        self.assertIn("+31 kg produced; 31 kg consumed; 10 kg remaining", text)

    def test_predation_and_scavenging_are_counted_once_and_eaten_prey_food_is_retained(self):
        world, registry = self.setup_world()
        registry.get("grazer")["birth_rate_per_animal_per_cycle"] = 0.0
        registry.register_all([
            {"id": "root", "entity_type": "taxon", "parent_taxon_id": None},
            {"id": "bite", "entity_type": "attack_method", "trauma_modifier": 1.0,
             "trait_effect_target": "bite_effectiveness"},
            {"id": "hunter", "name": "Hunter", "entity_type": "animal",
             "food_requirement_per_animal_per_cycle": 31.0, "diet": [],
             "attack_method_id": "bite", "prey_diet": [{"animal_id": "grazer", "preference": 1.0}]},
            {"id": "scavenger", "name": "Scavenger", "entity_type": "animal",
             "food_requirement_per_animal_per_cycle": 31.0, "diet": [],
             "scavenging_diet": [{"animal_id": "grazer", "preference": 1.0}]},
        ])
        for animal_id, power in (("grazer", 0.0), ("hunter", 8.0)):
            registry.get(animal_id).update(
                taxon_id="root", typical_adult_mass_kg=10.0,
                primary_movement_mode="terrestrial", available_movement_modes=["terrestrial"],
                statistics={"power": power, "defense": 0.0, "mobility": power,
                            "perception": power, "stealth": 0.0},
            )
        region = world.regions["region"]
        region.animal_populations = {"grazer": 31, "hunter": 1, "scavenger": 1}
        region.habitats["local"].animal_populations = dict(region.animal_populations)
        region.resource_quantities["food"] = 1000.0
        region.habitats["local"].resource_quantities["food"] = 1000.0
        registry.get("local")["carrion_decay_fraction_per_cycle"] = 0.5
        self.complete_month(world, registry)
        summary = summarize_month(world, 1, Month.JANUARY).region_results["region"]
        self.assertEqual(summary.predation_deaths, {"grazer": 31})
        self.assertEqual(summary.hunt_outcomes["local"]["hunter"], {"secured": 31})
        self.assertEqual(summary.scavenged_biomass_kg["local"]["scavenger"], 31.0)
        self.assertEqual(summary.resource_consumption["food"], 496.0)
        self.assertEqual(summary.ending_state.resource_quantities["food"], 535.0)
        self.assertEqual(summary.feeding_results["grazer"].resource_consumption["food"], 465.0)
        remaining = sum(deposit.available_biomass_kg for deposit in summary.ending_state.carrion["local"])
        self.assertAlmostEqual(remaining + summary.decayed_biomass_kg["local"] + 31.0 + 31.0, 310.0)
        self.assertIn("31 secured", format_monthly_ecology_report(summarize_month(world, 1, Month.JANUARY), registry))
