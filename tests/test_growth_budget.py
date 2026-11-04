from copy import deepcopy
import json
from pathlib import Path
import unittest

from core.content_catalog import build_content_registry
from scripts.growth_budget import growth_budget
from scripts.investigate_capacity import Factors, configure, run_case
from simulation.growth import GrowthCohort, grow_cohorts, adult_count


ROOT = Path(__file__).resolve().parents[1]


class TestGrowthBudget(unittest.TestCase):
    def definition(self):
        return {"typical_adult_mass_kg": 3.5, "food_requirement_per_animal_per_cycle": 0.5,
                "growth": {"newborn_mass_fraction": 0.1, "days_to_adult": 90}}

    def test_saved_hare_ration_cannot_support_nominal_maturation_target(self):
        result = growth_budget(self.definition(), 30)
        self.assertAlmostEqual(result["food_limited_days"], 756)
        self.assertAlmostEqual(result["daily_food_for_target_kg"], 0.14)
        self.assertFalse(result["target_feasible_when_fully_fed"])
        self.assertEqual(result["effective_minimum_days"], result["food_limited_days"])

    def test_computed_floor_matches_actual_growth_and_handles_month_lengths(self):
        definition = self.definition()
        definition["food_requirement_per_animal_per_cycle"] = growth_budget(definition, 31)["monthly_food_for_target_kg"]
        for days in (28, 29, 30, 31):
            with self.subTest(days=days):
                self.assertTrue(growth_budget(definition, days)["target_feasible_when_fully_fed"])
                cohorts = (GrowthCohort(1, 0.1),)
                for _ in range(90):
                    cohorts, _ = grow_cohorts(cohorts, definition["growth"], 1,
                        definition["food_requirement_per_animal_per_cycle"] / days * 0.25 / 3.5)
                self.assertEqual(cohorts, ())

    def test_food_limited_mixed_cohorts_reach_adulthood_without_asymptotic_stall(self):
        cohorts = (GrowthCohort(1, 0.95), GrowthCohort(100, 0.1))
        config = {"newborn_mass_fraction": 0.1, "days_to_adult": 3}
        gained = 0.0
        for _ in range(5):
            cohorts, gain = grow_cohorts(cohorts, config, 1, 1.01)
            gained += gain
            self.assertLessEqual(gain, 1.01 + 1e-12)
        self.assertEqual(adult_count(101, cohorts), 1)
        self.assertEqual(cohorts[0].count, 100)
        self.assertAlmostEqual(gained, 5.05)

    def test_zero_food_and_invalid_values_have_explicit_results(self):
        definition = self.definition()
        definition["food_requirement_per_animal_per_cycle"] = 0
        self.assertIsNone(growth_budget(definition)["effective_minimum_days"])
        self.assertFalse(growth_budget(definition)["target_feasible_when_fully_fed"])
        json.dumps(growth_budget(definition), allow_nan=False)
        for days in (True, 0, 1.5):
            with self.subTest(days=days), self.assertRaises(ValueError):
                growth_budget(definition, days)
        for invalid in (True, -1, float("nan"), float("inf")):
            definition["food_requirement_per_animal_per_cycle"] = invalid
            with self.subTest(food=invalid), self.assertRaises(ValueError):
                growth_budget(definition)

    def test_floor_changes_private_rations_without_creating_food(self):
        source = json.loads((ROOT / "scenarios/playtest_b_food_web.json").read_text(encoding="utf-8"))
        registry = build_content_registry(ROOT / "content")
        original, hare = deepcopy(source), deepcopy(registry.get("scrub_hare"))
        existing = Factors(300, 2000, "small", 8, True, 60, True, 0.9, 30, 0.9, 90)
        floor = Factors(300, 2000, "small", 8, True, 60, True, 0.9, 30, 0.9, 90, True)
        _, base_content = configure(source, registry, existing, 7)
        data, content = configure(source, registry, floor, 7)
        self.assertEqual(registry.get("scrub_hare"), hare)
        self.assertEqual(source, original)
        self.assertEqual(data["regions"][0]["resource_quantities"], source["regions"][0]["resource_quantities"])
        self.assertAlmostEqual(content.get("scrub_hare")["food_requirement_per_animal_per_cycle"], 4.34)
        self.assertEqual(base_content.get("scrub_hare")["food_requirement_per_animal_per_cycle"], 0.5)
        self.assertEqual(content.get("caracal")["food_requirement_per_animal_per_cycle"], base_content.get("caracal")["food_requirement_per_animal_per_cycle"])
        self.assertEqual(content.get("brown_hyena")["food_requirement_per_animal_per_cycle"], base_content.get("brown_hyena")["food_requirement_per_animal_per_cycle"])
        self.assertEqual(content.get("warthog")["food_requirement_per_animal_per_cycle"], base_content.get("warthog")["food_requirement_per_animal_per_cycle"])
        with self.assertRaises(ValueError):
            Factors(300, 2000, "small", 8, growth_ration_floor=True)

    def test_real_floor_case_replays_and_recruitment_counts_reconcile(self):
        factors = Factors(300, 2000, "small", 8, True, 60, True, 0.9, 30, 0.9, 90, True)
        first = run_case(ROOT, factors, 7, 2)
        self.assertEqual(first, run_case(ROOT, factors, 7, 2))
        for month in first["monthly"]:
            local = month["regions"]["redgrass_savanna"]
            for animal, counts in local["recruitment"].items():
                self.assertEqual(counts["adults_at_end"] + counts["juveniles_at_end"], local["species"][animal]["end"])
            self.assertAlmostEqual(local["carrion"]["balance_error_kg"], 0)
        self.assertTrue(first["growth_budgets"]["scrub_hare"]["31"]["target_feasible_when_fully_fed"])
