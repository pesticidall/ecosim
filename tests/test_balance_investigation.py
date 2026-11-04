import unittest
from copy import deepcopy
from pathlib import Path

from core.content_catalog import build_content_registry
from scripts.investigate_balance import experiment_registry, run_experiment
from simulation.daily_demographics import DemographicCarry, resolve_population_daily_demographics


ROOT = Path(__file__).resolve().parents[1]


class TestBalanceInvestigation(unittest.TestCase):
    def test_counterfactuals_do_not_modify_authoritative_content(self):
        registry = build_content_registry(ROOT / "content")
        original = deepcopy(registry.get("caracal"))
        changed = experiment_registry(registry, "caracal_both")
        self.assertEqual(changed.get("caracal")["activity_pattern"], "crepuscular")
        self.assertEqual(changed.get("caracal")["scavenging_diet"], original["prey_diet"])
        self.assertEqual(registry.get("caracal"), original)
        baseline = experiment_registry(registry, "baseline")
        self.assertEqual(baseline.get("caracal"), original)
        self.assertIsNot(baseline.get("caracal"), registry.get("caracal"))
        with self.assertRaises(ValueError):
            experiment_registry(registry, "unknown")

    def test_evidence_replays_and_separates_hunt_opportunities_from_nutrition(self):
        result = run_experiment(ROOT, "legacy", 104729, 1)
        self.assertEqual(result, run_experiment(ROOT, "legacy", 104729, 1))
        caracal = result["months"][0]["regions"]["redgrass_savanna"]["caracal"]
        self.assertGreater(caracal["zero_overlap_attempts"], 0)
        self.assertGreater(caracal["hunt_outcomes"]["secured"], 0)
        self.assertEqual(caracal["scavenged_kg"], 0)
        self.assertLess(caracal["coverage"], 0.2)
        self.assertEqual(sum(caracal["hunt_outcomes"].values()), sum(caracal["prey_choices"].values()))
        self.assertAlmostEqual(caracal["consumed_kg"], sum(caracal["food_sources_kg"].values()))
        trial = run_experiment(ROOT, "caracal_twilight", 104729, 1)
        self.assertEqual(trial["months"][0]["regions"]["redgrass_savanna"]["caracal"]["zero_overlap_attempts"], 0)

    def test_starvation_fraction_is_rounding_carry_not_a_recoverable_energy_store(self):
        change = resolve_population_daily_demographics(1, 0, 0, 30)
        self.assertAlmostEqual(change.carry.starvation, 1 / 30)
        for _ in range(60):
            change = resolve_population_daily_demographics(1, 0, 1, 30, change.carry)
        self.assertAlmostEqual(change.carry.starvation, 1 / 30)
        self.assertEqual(change.starvation_deaths, 0)
        # A final small deficit can eventually round to a death, even if fed
        # days separate the deficits. This records current semantics, not a fix.
        final = resolve_population_daily_demographics(1, 0, 0, 30, DemographicCarry(starvation=29 / 30))
        self.assertEqual(final.starvation_deaths, 1)

    def test_stage_diagnostics_and_carrion_budget_reconcile_real_content(self):
        run = run_experiment(ROOT, "baseline", 104729, 1)
        month = run["months"][0]
        species = month["regions"]["redgrass_savanna"]
        for animal in ("caracal", "black_backed_jackal"):
            self.assertEqual(species[animal]["zero_overlap_attempts"], 0)
            stages = species[animal]["stages"]
            self.assertEqual(stages["detection"]["reached"], sum(species[animal]["hunt_outcomes"].values()))
            self.assertEqual(stages["detection"]["passed"], stages["chase"]["reached"])
            for stage in stages.values():
                self.assertLessEqual(stage["passed"], stage["reached"])
                self.assertLessEqual(stage["probability_sum"], stage["reached"])
        budget = month["carrion_budgets"]["redgrass_savanna"]
        self.assertAlmostEqual(budget["balance_error_kg"], 0)
        self.assertGreater(budget["predation_created_kg"], 0)
        self.assertAlmostEqual(budget["scavenged_kg"], sum(s["scavenged_kg"] for s in species.values()))
        for item in species.values():
            self.assertAlmostEqual(item["scavenged_kg"], sum(item["scavenged_by_source_kg"].values()))

    def test_opportunity_and_demand_experiments_are_independent_private_changes(self):
        registry = build_content_registry(ROOT / "content")
        original = deepcopy(registry.get("brown_hyena"))
        prior = experiment_registry(registry, "prior_encounters")
        self.assertNotIn("encounter_model", prior.get("caracal"))
        twice = experiment_registry(registry, "attempts_two")
        self.assertEqual(twice.get("caracal")["hunting_attempts_per_animal"], 2)
        self.assertEqual(twice.get("brown_hyena"), original)
        half = experiment_registry(registry, "scavenger_demand_half")
        self.assertEqual(half.get("brown_hyena")["food_requirement_per_animal_per_cycle"], original["food_requirement_per_animal_per_cycle"] / 2)
        self.assertNotIn("hunting_attempts_per_animal", half.get("caracal"))
        self.assertEqual(registry.get("brown_hyena"), original)
