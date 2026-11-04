import unittest
from pathlib import Path
from random import Random

from core.content_registry import ContentRegistry
from simulation.search import resolve_search_budget
from simulation.world_state import HabitatState


class TestSearchBudget(unittest.TestCase):
    def test_playable_trial_and_search_state_rollback_replay(self):
        from copy import deepcopy
        from unittest.mock import patch
        from core.content_catalog import build_content_registry
        from simulation.scenario_loader import load_scenario
        from simulation.daily_cycle import run_day
        root = Path(__file__).resolve().parents[1]
        registry = build_content_registry(root / "content")
        world = load_scenario(root / "scenarios" / "playtest_b_hunting_search_trial.json", registry)
        self.assertEqual(world.regions["redgrass_savanna"].animal_populations["scrub_hare"], 300)
        self.assertEqual(world.regions["redgrass_savanna"].producer_populations["redgrass"], 2000)
        for _ in range(30):
            run_day(world, registry)
        before, rng = deepcopy(world), world.random_generator.getstate()
        with patch("simulation.daily_cycle.summarize_month", side_effect=ValueError("failed report")):
            with self.assertRaises(ValueError):
                run_day(world, registry)
        self.assertEqual(world, before)
        self.assertEqual(world.random_generator.getstate(), rng)
        resumed = deepcopy(world)
        self.assertEqual(run_day(world, registry), run_day(resumed, registry))
        self.assertEqual(world.random_generator.getstate(), resumed.random_generator.getstate())

    def test_catalog_schema_rejects_ambiguous_or_invalid_search_configuration(self):
        from core.content_catalog import build_content_registry
        from core.content_validator import validate_entity_definition
        from copy import deepcopy
        registry = build_content_registry(Path(__file__).resolve().parents[1] / "content")
        original = registry.get("caracal")
        candidate = {**deepcopy(original), "search_budget": {"reference_prey": 60, "max_opportunities": 4}}
        candidate.pop("hunting_attempts_per_animal", None)
        validate_entity_definition(candidate, Path("animal.json"))
        for config in (None, {}, {"reference_prey": 0, "max_opportunities": 4},
                       {"reference_prey": 60, "max_opportunities": True}):
            invalid = {**candidate, "search_budget": config}
            with self.assertRaises(ValueError):
                validate_entity_definition(invalid, Path("animal.json"))
        with self.assertRaisesRegex(ValueError, "both"):
            validate_entity_definition({**candidate, "hunting_attempts_per_animal": 2}, Path("animal.json"))

    def setup_search(self, prey=60, hunters=1):
        registry = ContentRegistry()
        registry.register_all([{"id": "prey", "activity_pattern": "nocturnal"},
                               {"id": "inactive", "activity_pattern": "diurnal"}])
        predator = {"id": "hunter", "activity_pattern": "nocturnal", "prey_diet": [{"animal_id": "prey", "preference": 1}],
                    "search_budget": {"reference_prey": 60, "max_opportunities": 4}}
        habitat = HabitatState("local", animal_populations={"hunter": hunters, "prey": prey, "inactive": 10000})
        return predator, habitat, registry

    def test_absolute_abundance_increases_bounded_opportunities_with_one_prey_species(self):
        expected = []
        for count in (0, 1, 60, 300, 3000):
            predator, habitat, registry = self.setup_search(count)
            budget = resolve_search_budget(predator, habitat, registry, Random(1))
            expected.append(budget.expected_member_opportunities)
            self.assertLessEqual(budget.allocated_member_opportunities, 4)
            self.assertGreaterEqual(budget.allocated_member_opportunities, 0)
        self.assertEqual(expected, sorted(expected))
        self.assertEqual(expected[2], 2)
        self.assertAlmostEqual(expected[3], 10 / 3)

    def test_fractional_rounding_is_seeded_and_integer_or_empty_budgets_use_no_draw(self):
        predator, habitat, registry = self.setup_search(300)
        for seed, allocated in ((1, 4), (2, 3)):
            rng, reference = Random(seed), Random(seed)
            result = resolve_search_budget(predator, habitat, registry, rng)
            self.assertEqual(result.rounding_roll, reference.random())
            self.assertEqual(result.allocated_member_opportunities, allocated)
            self.assertEqual(rng.getstate(), reference.getstate())
        for prey in (0, 60):
            predator, habitat, registry = self.setup_search(prey)
            rng = Random(1)
            before = rng.getstate()
            resolve_search_budget(predator, habitat, registry, rng)
            self.assertEqual(rng.getstate(), before)

    def test_activity_locality_and_diet_limit_eligible_prey(self):
        predator, habitat, registry = self.setup_search(60)
        predator["prey_diet"].append({"animal_id": "inactive", "preference": 1})
        result = resolve_search_budget(predator, habitat, registry, Random(1))
        self.assertEqual(result.eligible_prey, 60)
        registry.get("prey")["activity_pattern"] = "crepuscular"
        self.assertEqual(resolve_search_budget(predator, habitat, registry, Random(1)).eligible_prey, 30)
        habitat.animal_populations["prey"] = 0
        self.assertEqual(resolve_search_budget(predator, habitat, registry, Random(1)).allocated_member_opportunities, 0)

    def test_same_species_search_excludes_the_hunter_and_zero_hunters_cannot_search(self):
        predator, habitat, registry = self.setup_search()
        registry.register({"id": "hunter", "activity_pattern": "nocturnal"})
        predator["prey_diet"] = [{"animal_id": "hunter", "preference": 1}]
        self.assertEqual(resolve_search_budget(predator, habitat, registry, Random(1)).eligible_prey, 0)
        habitat.animal_populations["hunter"] = 2
        self.assertEqual(resolve_search_budget(predator, habitat, registry, Random(1)).eligible_prey, 1)
        habitat.animal_populations["hunter"] = 0
        self.assertEqual(resolve_search_budget(predator, habitat, registry, Random(1)).maximum_member_opportunities, 0)

    def test_invalid_configuration_is_rejected(self):
        for field, values in (("reference_prey", (0, -1, True, float("inf"), float("nan"))),
                              ("max_opportunities", (0, 9, True, 1.5))):
            for value in values:
                predator, habitat, registry = self.setup_search()
                predator["search_budget"][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    resolve_search_budget(predator, habitat, registry, Random(1))
