from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from core.content_catalog import build_content_registry
from scripts.investigate_balance import summarize_evidence
from scripts.investigate_capacity import Factors, configure, run_case
from simulation.carrion import CarrionDeposit
from simulation.monthly_cycle import acknowledge_month_review, run_month
from simulation.scenario_loader import load_scenario


ROOT = Path(__file__).resolve().parents[1]


class TestCarrionTurnover(unittest.TestCase):
    def test_private_override_and_omitted_setting_preserve_source_content(self):
        source = json.loads((ROOT / "scenarios/playtest_b_food_web.json").read_text(encoding="utf-8"))
        registry = build_content_registry(ROOT / "content")
        registry.get("open_grassland")["carrion_decay_fraction_per_cycle"] = 0.2
        original = deepcopy(registry.get("open_grassland"))
        _, unchanged = configure(source, registry, Factors(300, 2000, "small", 8), 7)
        self.assertEqual(unchanged.get("open_grassland"), original)
        for loss in (0, 0.5, 0.9, 1):
            with self.subTest(loss=loss):
                factors = Factors(300, 2000, "small", 8, carrion_monthly_loss=loss)
                _, content = configure(source, registry, factors, 7)
                self.assertTrue(all(h["carrion_decay_fraction_per_cycle"] == loss for h in content.definitions_of_type("habitat")))
                self.assertEqual(registry.get("open_grassland"), original)
                self.assertIn(f"_decay{loss:g}", factors.label)
        for loss in (True, "0.5", -0.1, 1.1, float("nan"), float("inf")):
            with self.subTest(invalid=loss), self.assertRaises(ValueError):
                Factors(300, 2000, "small", 8, carrion_monthly_loss=loss)

    def test_untouched_carcass_monthly_budget_across_january_and_february(self):
        source = json.loads((ROOT / "scenarios/playtest_b_food_web.json").read_text(encoding="utf-8"))
        data, registry = configure(source, build_content_registry(ROOT / "content"),
                                   Factors(300, 2000, "small", 8, carrion_monthly_loss=0.5), 7)
        data["regions"][0]["animal_populations"] = {key: 0 for key in data["regions"][0]["animal_populations"]}
        with TemporaryDirectory(prefix=".turnover-", dir=ROOT) as folder:
            path = Path(folder) / "scenario.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            world = load_scenario(path, registry)
        world.regions["redgrass_savanna"].habitats["open_grassland"].carrion_deposits.append(
            CarrionDeposit("scrub_hare", "open_grassland", 100, 100, None))
        for starting, ending, length in ((100, 50, 31), (50, 25, 28)):
            summary = run_month(world, registry)
            budget = summarize_evidence(summary, registry)["carrion_budgets"]["redgrass_savanna"]
            self.assertEqual(len(summary.days), length)
            self.assertAlmostEqual(budget["starting_kg"], starting)
            self.assertAlmostEqual(budget["ending_kg"], ending)
            self.assertAlmostEqual(budget["decayed_kg"], starting - ending)
            self.assertAlmostEqual(budget["balance_error_kg"], 0)
            self.assertEqual(budget["scavenged_kg"], 0)
            self.assertEqual(budget["starvation_created_kg"], 0)
            acknowledge_month_review(world)

    def test_populated_decay_case_replays_with_balanced_carcass_evidence(self):
        factors = Factors(300, 2000, "small", 8, True, 60, True, 0.9, 30, 0.9)
        first = run_case(ROOT, factors, 7, 3)
        self.assertEqual(first, run_case(ROOT, factors, 7, 3))
        budgets = [month["regions"]["redgrass_savanna"]["carrion"] for month in first["monthly"]]
        self.assertGreater(sum(b["decayed_kg"] for b in budgets), 0)
        for budget in budgets:
            self.assertAlmostEqual(budget["balance_error_kg"], 0)
