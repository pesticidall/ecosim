import unittest
from copy import deepcopy
from pathlib import Path
from random import Random

from core.content_catalog import build_content_registry
from core.content_validator import validate_entity_definition
from simulation.approach import StalkingScores, calculate_stalking_scores, resolve_stalking
from simulation.hunting import DetectionScores, ChaseScores, resolve_hunt_approach
from scripts.investigate_balance import run_experiment


ROOT = Path(__file__).resolve().parents[1]


class TestConcealedApproach(unittest.TestCase):
    def test_shelter_and_vegetation_each_supply_cover_and_normalization_stays_finite(self):
        predator, prey = {"statistics": {"stealth": 8}}, {"statistics": {"perception": 4}}
        for vegetation, shelter in ((1, 0), (0, 1)):
            result = calculate_stalking_scores(predator, prey,
                {"conditions": {"vegetation_density": vegetation, "shelter_availability": shelter}}, {})
            self.assertEqual(result.cover, 0.5)
            self.assertEqual(result.concealment, 4)
        huge = resolve_stalking(StalkingScores(1, 1e308, 1e308), Random(1))
        self.assertEqual(huge.unnoticed_probability, 0.5)

    def scores(self, cover=0.5, stealth=8, perception=4, hunters=1, defenders=1):
        return calculate_stalking_scores({"statistics": {"stealth": stealth}},
            {"statistics": {"perception": perception}},
            {"conditions": {"vegetation_density": cover, "shelter_availability": cover}}, {},
            hunter_count=hunters, defender_count=defenders)

    def test_cover_stealth_and_group_awareness_have_distinct_effects(self):
        ordinary = self.scores()
        probability = lambda s: s.concealment / (s.concealment + s.awareness)
        self.assertGreater(probability(self.scores(cover=1)), probability(ordinary))
        self.assertGreater(probability(self.scores(stealth=10)), probability(ordinary))
        self.assertLess(probability(self.scores(perception=8)), probability(ordinary))
        self.assertLess(probability(self.scores(hunters=4)), probability(ordinary))
        self.assertLess(probability(self.scores(defenders=4)), probability(ordinary))
        self.assertEqual(self.scores().cover, 0.5)

    def test_no_cover_or_zero_stealth_gives_no_advantage_or_random_draw(self):
        for scores in (self.scores(cover=0), self.scores(stealth=0)):
            rng = Random(1)
            before = rng.getstate()
            result = resolve_stalking(scores, rng)
            self.assertFalse(result.unnoticed)
            self.assertEqual(result.escape_multiplier, 1)
            self.assertEqual(rng.getstate(), before)

    def test_seeded_advantage_is_bounded_and_scores_are_immutable(self):
        scores = self.scores(cover=1)
        before = deepcopy(scores)
        result = resolve_stalking(scores, Random(1))
        self.assertTrue(result.unnoticed)
        self.assertEqual(result.escape_multiplier, 0.5)
        noticed = resolve_stalking(scores, Random(2))
        self.assertFalse(noticed.unnoticed)
        self.assertEqual(noticed.escape_multiplier, 1)
        self.assertEqual(result, resolve_stalking(scores, Random(1)))
        self.assertEqual(scores, before)

    def test_detection_failure_or_incompatible_movement_never_invokes_approach(self):
        detection = DetectionScores(0, 10, 1, 1, 0, 10)
        chase = ChaseScores(5, 5, True)
        # Read actual attack-score fields through the public calculator.
        from simulation.hunting import calculate_attack_scores
        animal = {"statistics": {"power": 5, "defense": 5}}
        attack = calculate_attack_scores(animal, animal)
        rng, reference = Random(1), Random(1)
        result = resolve_hunt_approach(detection, chase, attack, rng, self.scores())
        reference.random()
        self.assertIsNone(result.stalking)
        self.assertEqual(rng.getstate(), reference.getstate())
        detected = DetectionScores(10, 0, 1, 1, 10, 0)
        rng, reference = Random(1), Random(1)
        result = resolve_hunt_approach(detected, ChaseScores(5, 5, False), attack, rng, self.scores())
        reference.random()
        self.assertIsNone(result.stalking)
        self.assertFalse(result.chase.caught)
        self.assertEqual(rng.getstate(), reference.getstate())

    def test_no_cover_and_opt_out_preserve_identical_stage_results(self):
        from simulation.hunting import calculate_attack_scores
        animal = {"statistics": {"power": 5, "defense": 5}}
        attack = calculate_attack_scores(animal, animal)
        detected = DetectionScores(10, 0, 1, 1, 10, 0)
        for seed in range(5):
            plain = resolve_hunt_approach(detected, ChaseScores(5, 5, True), attack, Random(seed))
            uncovered = resolve_hunt_approach(detected, ChaseScores(5, 5, True), attack, Random(seed), self.scores(cover=0))
            self.assertEqual(plain.chase, uncovered.chase)
            self.assertEqual(plain.attack, uncovered.attack)

    def test_approach_does_not_guarantee_capture_or_change_mobility(self):
        from simulation.hunting import calculate_attack_scores
        animal = {"statistics": {"power": 5, "defense": 5}}
        attack = calculate_attack_scores(animal, animal)
        detected = DetectionScores(10, 0, 1, 1, 10, 0)
        original = ChaseScores(1, 10, True)
        results = [resolve_hunt_approach(detected, original, attack, Random(seed), self.scores(cover=1)) for seed in range(30)]
        self.assertTrue(any(r.stalking.unnoticed and not r.chase.caught for r in results))
        self.assertEqual(original.prey_escape_mobility, 10)

    def test_real_content_and_diagnostics_replay_with_separate_approach_stage(self):
        first = run_experiment(ROOT, "baseline", 104729, 1)
        self.assertEqual(first, run_experiment(ROOT, "baseline", 104729, 1))
        species = first["months"][0]["regions"]["redgrass_savanna"]
        for animal in ("caracal", "black_backed_jackal"):
            stages = species[animal]["stages"]
            self.assertEqual(stages["stalking"]["reached"], stages["detection"]["passed"])
            self.assertGreater(stages["stalking"]["reached"], 0)
        registry = build_content_registry(ROOT / "content")
        for value in (None, True, "unknown"):
            definition = {**registry.get("caracal"), "approach_model": value}
            with self.assertRaisesRegex(ValueError, "approach_model"):
                validate_entity_definition(definition, Path("animal.json"))
        for value in (-1, float("inf")):
            with self.assertRaises(ValueError):
                StalkingScores(value, 1, 1)
