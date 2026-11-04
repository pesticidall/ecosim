import json
import unittest
from copy import deepcopy
from pathlib import Path

from core.content_catalog import build_content_registry
from scripts.investigate_capacity import Factors, GUILDS, configure, run_case, check_accounting
from simulation.monthly_cycle import run_month
from simulation.scenario_loader import load_scenario


ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "scenarios" / "playtest_b_food_web.json"


class TestCapacityInvestigation(unittest.TestCase):
    def test_factors_change_only_the_intended_inputs_and_keep_starting_stores_fixed(self):
        source = json.loads(SCENARIO.read_text(encoding="utf-8"))
        registry = build_content_registry(ROOT / "content")
        original, caracal = deepcopy(source), deepcopy(registry.get("caracal"))
        data, content = configure(source, registry, Factors(300, 2000, "small", 2), 7)
        region = data["regions"][0]
        self.assertEqual(region["animal_populations"]["scrub_hare"], 300)
        self.assertEqual(region["producer_populations"]["redgrass"], 2000)
        self.assertEqual({animal: region["animal_populations"][animal] for animal in GUILDS["small"]}, GUILDS["small"])
        self.assertEqual(region["resource_quantities"], source["regions"][0]["resource_quantities"])
        self.assertEqual(region["colony_populations"], source["regions"][0]["colony_populations"])
        self.assertEqual(content.get("caracal")["hunting_attempts_per_animal"], 2)
        self.assertEqual(source, original)
        self.assertEqual(registry.get("caracal"), caracal)
        self.assertEqual(data["random_seed"], 7)
        _, strict = configure(source, registry, Factors(300, 2000, "small", 4, True, 60, True, 0.9), 7)
        self.assertTrue(strict.get("caracal")["nutrition"]["recovery_requires_food"])
        self.assertEqual(strict.get("scrub_hare")["reproduction_food_threshold"], 0.9)
        self.assertEqual(registry.get("caracal"), caracal)
        self.assertNotIn("reproduction_food_threshold", registry.get("scrub_hare"))
        _, bounded = configure(source, registry, Factors(300, 2000, "small", 8, True, 60, True, 0.9, 30), 7)
        for entry in bounded.get("redgrass")["production"]:
            self.assertEqual(entry["standing_capacity_per_producer"], entry["amount_per_producer_per_day"] * 30)
        self.assertNotIn("standing_capacity_per_producer", registry.get("redgrass")["production"][0])
        self.assertNotIn("standing_capacity_per_producer", bounded.get("termite_colony")["production"][0])

    def test_real_case_is_reproducible_and_has_verified_monthly_ledgers(self):
        factors = Factors(300, 2000, "small", 2)
        first = run_case(ROOT, factors, 104729, 1)
        self.assertEqual(first, run_case(ROOT, factors, 104729, 1))
        local = first["monthly"][0]["regions"]["redgrass_savanna"]
        self.assertEqual(local["species"]["scrub_hare"]["start"], 300)
        self.assertEqual(local["species"]["black_backed_jackal"]["start"], 2)
        self.assertAlmostEqual(local["resources"]["grass_forage"]["produced_kg"], 620)
        self.assertAlmostEqual(local["carrion"]["balance_error_kg"], 0)
        for animal, result in local["species"].items():
            self.assertEqual(result["end"], result["start"] + result["births"]
                             - result["predation_deaths"] - result["starvation_deaths"])

    def test_invalid_factors_and_duration_are_rejected(self):
        for value in (True, -1, float("nan"), float("inf")):
            with self.subTest(standing_days=value), self.assertRaises(ValueError):
                Factors(300, 2000, "small", 8, standing_days=value)
        for args in ((0, 500, "current", 1), (60, True, "current", 1), (60, 500, "bad", 1),
                     (60, 500, "small", 9), (60, 500, "small", 1.5)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                Factors(*args)
        with self.assertRaises(ValueError):
            run_case(ROOT, Factors(60, 500, "current", 1), 1, 0)

    def test_accounting_failure_is_reported_instead_of_counting_a_run_as_valid(self):
        registry = build_content_registry(ROOT / "content")
        world = load_scenario(SCENARIO, registry)
        summary = run_month(world, registry)
        check_accounting(world, summary)
        world.regions["redgrass_savanna"].resource_quantities["grass_forage"] += 1
        with self.assertRaisesRegex(ValueError, "Resource"):
            check_accounting(world, summary)

    def test_bounded_month_replays_and_records_only_actual_growth(self):
        factors = Factors(300, 2000, "small", 8, True, 60, True, 0.9, 1)
        first = run_case(ROOT, factors, 7, 1)
        self.assertEqual(first, run_case(ROOT, factors, 7, 1))
        resources = first["monthly"][0]["regions"]["redgrass_savanna"]["resources"]
        self.assertLess(resources["grass_forage"]["produced_kg"], 620)
        for amounts in resources.values():
            self.assertAlmostEqual(amounts["start_kg"] + amounts["produced_kg"] - amounts["consumed_kg"], amounts["end_kg"])
