import unittest
from copy import deepcopy
from pathlib import Path

from scripts.investigate_capacity import Factors, run_case


ROOT = Path(__file__).resolve().parents[1]


class TestFoodFlow(unittest.TestCase):
    def test_daily_projection_preserves_replay_and_reconciles_monthly_transfers(self):
        factors = Factors(300, 4000, "small", 8, True, 60, True, 0.9,
                          30, 0.9, 90, False, True, "flexible_bird_diet")
        plain = run_case(ROOT, factors, 7, 1)
        traced = run_case(ROOT, factors, 7, 1, food_flows=True)
        self.assertEqual(traced, run_case(ROOT, factors, 7, 1, food_flows=True))
        stripped = deepcopy(traced)
        local = stripped["monthly"][0]["regions"]["redgrass_savanna"]
        days = local.pop("food_flows")
        self.assertEqual(stripped, plain)
        self.assertEqual([day["day"] for day in days], list(range(1, 32)))
        totals = dict(carcass=0.0, first=0.0, scavenging=0.0, reserve=0.0)
        kills = {}
        for day in days:
            for habitat in day["habitats"].values():
                for animal, flow in habitat.items():
                    self.assertAlmostEqual(sum(flow["maintenance_sources_kg"].values()), flow["maintenance_consumed_kg"])
                    for prey, hunt in flow["hunts_by_prey"].items():
                        kills[prey] = kills.get(prey, 0) + hunt["secured_count"]
                        self.assertGreaterEqual(hunt["attempts"], hunt["secured_count"])
                        self.assertAlmostEqual(hunt["carcass_kg"], hunt["first_meal_kg"] + hunt["released_leftovers_kg"])
                        totals["carcass"] += hunt["carcass_kg"]
                        totals["first"] += hunt["first_meal_kg"]
                        self.assertAlmostEqual(flow["maintenance_sources_kg"].get(prey, 0),
                            hunt["first_meal_kg"] + flow["maintenance_scavenging_by_prey_kg"].get(prey, 0))
                    for field in ("maintenance_scavenging_by_prey_kg", "reserve_scavenging_by_prey_kg", "growth_scavenging_by_prey_kg"):
                        totals["scavenging"] += sum(flow[field].values())
                    totals["reserve"] += sum(flow["reserve_scavenging_by_prey_kg"].values())
        self.assertGreater(totals["reserve"], 0)
        self.assertAlmostEqual(totals["carcass"], local["carrion"]["predation_created_kg"])
        self.assertAlmostEqual(totals["first"], local["carrion"]["predator_first_meal_kg"])
        self.assertAlmostEqual(totals["scavenging"], local["carrion"]["scavenged_kg"])
        for prey, count in kills.items():
            self.assertEqual(count, local["species"][prey]["predation_deaths"])
            self.assertEqual(sum(d["regional_prey_counts"][prey]["births"] for d in days), local["species"][prey]["births"])
        for animal, values in local["species"].items():
            self.assertAlmostEqual(sum(d["regional_recovery_spent_kg"].get(animal, 0) for d in days), values["condition_recovery_kg"])
