import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from core.content_catalog import build_content_registry
from core.content_validator import validate_entity_definition
from simulation.nutrition import NutritionalState, update_condition
from simulation.daily_demographics import DemographicCarry, resolve_population_daily_demographics
from simulation.daily_cycle import run_day
from simulation.monthly_cycle import run_month
from simulation.monthly_reporting import format_monthly_ecology_report


CONFIG = {"reserve_days": 3, "starvation_grace_days": 7, "recovery_per_fed_day": 1,
          "recovery_requires_food": True}


class TestFoodPaidRecovery(unittest.TestCase):
    def test_recovery_consumes_only_real_reserves_and_stops_when_they_are_empty(self):
        state = NutritionalState(2, 3, 2)
        first, pressure = update_condition(state, 1, CONFIG, 2)
        self.assertEqual(first, NutritionalState(2, 1, 1))
        self.assertEqual(pressure, 0)
        second, _ = update_condition(first, 1, CONFIG, 2)
        self.assertEqual(second, NutritionalState(2, 0, 0.5))
        third, _ = update_condition(second, 1, CONFIG, 2)
        self.assertEqual(third, second)
        self.assertEqual(state, NutritionalState(2, 3, 2))

    def test_deficit_days_still_accumulate_and_legacy_recovery_stays_opt_out(self):
        state = NutritionalState(1, 2, 8)
        hungry, pressure = update_condition(state, 0.5, CONFIG, 1)
        self.assertEqual(hungry.deficit_days, 8.5)
        self.assertEqual(hungry.reserve_kg, 2)
        self.assertGreater(pressure, 0)
        legacy, _ = update_condition(NutritionalState(1, 0, 2), 1, {**CONFIG, "recovery_requires_food": False})
        self.assertEqual(legacy.deficit_days, 1)
        for requirement in (None, True, -1, float("nan")):
            with self.assertRaises(ValueError):
                update_condition(state, 1, CONFIG, requirement)

    def test_birth_threshold_preserves_rounding_and_full_food_fertility(self):
        carry = DemographicCarry(0.7, 0.2)
        hungry = resolve_population_daily_demographics(10, 1, 0.8, 10, carry,
            starvation_deficit=0, reproduction_food_threshold=0.9)
        self.assertEqual(hungry.births, 0)
        self.assertEqual(hungry.carry, carry)
        partial = resolve_population_daily_demographics(10, 1, 0.95, 10,
            starvation_deficit=0, reproduction_food_threshold=0.9)
        self.assertAlmostEqual(partial.carry.births, 0.5)
        fed = resolve_population_daily_demographics(10, 1, 1, 10, reproduction_food_threshold=0.9)
        legacy = resolve_population_daily_demographics(10, 1, 1, 10)
        self.assertEqual(fed, legacy)

    def test_monthly_physical_food_ledger_accounts_for_recovery_and_storage(self):
        import test_nutrition
        world, registry, habitat = test_nutrition.TestNutrition().setup_world(food=1000)
        registry.get("animal")["nutrition"] = dict(CONFIG)
        habitat.nutritional_states["animal"] = NutritionalState(1, 0, 2)
        summary = run_month(world, registry)
        result = summary.region_results["region"]
        recovery = sum(day.region_results["region"].demographics.condition_recovery_kg["animal"] for day in summary.days)
        self.assertAlmostEqual(recovery, 2)
        self.assertEqual(habitat.nutritional_states["animal"].deficit_days, 0)
        self.assertAlmostEqual(1000, habitat.resource_quantities["food"]
                               + habitat.nutritional_states["animal"].reserve_kg
                               + result.feeding_results["animal"].consumed_amount + recovery)
        self.assertAlmostEqual(result.resource_consumption["food"], 36.1)
        self.assertIn("2.00 kg stored food used", format_monthly_ecology_report(summary, registry))

    def test_failed_recovery_commit_rolls_back_reserves_condition_and_recovery_record(self):
        import test_nutrition
        world, registry, habitat = test_nutrition.TestNutrition().setup_world(food=1000)
        registry.get("animal")["nutrition"] = dict(CONFIG)
        for _ in range(30):
            run_day(world, registry)
        habitat.nutritional_states["animal"] = NutritionalState(1, 2, 2)
        before = deepcopy(world)
        with patch("simulation.daily_cycle.summarize_month", side_effect=ValueError("failed report")):
            with self.assertRaises(ValueError):
                run_day(world, registry)
        self.assertEqual(world, before)
        resumed = deepcopy(world)
        self.assertEqual(run_day(world, registry), run_day(resumed, registry))

    def test_optional_content_fields_are_validated(self):
        registry = build_content_registry(Path(__file__).resolve().parents[1] / "content")
        source = deepcopy(registry.get("caracal"))
        source["nutrition"]["recovery_requires_food"] = True
        source["reproduction_food_threshold"] = 0.9
        validate_entity_definition(source, Path("animal.json"))
        for value in (True, -1, 1, float("nan")):
            with self.assertRaises(ValueError):
                validate_entity_definition({**source, "reproduction_food_threshold": value}, Path("animal.json"))
        source["nutrition"]["recovery_requires_food"] = 1
        with self.assertRaises(TypeError):
            validate_entity_definition(source, Path("animal.json"))
