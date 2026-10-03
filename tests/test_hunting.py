import unittest

from simulation.hunting import calculate_detection_scores


class TestHunting(unittest.TestCase):
    def test_calculates_detection_scores_from_activity_and_weather(
        self,
    ) -> None:
        detector_definition = {
            "id": "caracal",
            "statistics": {
                "perception": 8.0,
            },
        }
        target_definition = {
            "id": "scrub_hare",
            "statistics": {
                "stealth": 7.0,
            },
        }
        weather_definition = {
            "id": "heavy_fog",
            "visibility_modifier": 0.45,
        }

        scores = calculate_detection_scores(
            detector_definition,
            target_definition,
            activity_overlap_modifier=0.5,
            weather_definition=weather_definition,
        )

        self.assertEqual(scores.detector_perception, 8.0)
        self.assertEqual(scores.target_stealth, 7.0)
        self.assertEqual(
            scores.activity_overlap_modifier,
            0.5,
        )
        self.assertEqual(
            scores.weather_visibility_modifier,
            0.45,
        )
        self.assertAlmostEqual(
            scores.effective_perception,
            1.8,
        )
        self.assertEqual(scores.effective_stealth, 7.0)

    def test_resolves_detection_using_seeded_roll(self) -> None:
        from random import Random

        from simulation.hunting import DetectionScores, resolve_detection

        scores = DetectionScores(
            detector_perception=8.0,
            target_stealth=2.0,
            activity_overlap_modifier=1.0,
            weather_visibility_modifier=1.0,
            effective_perception=8.0,
            effective_stealth=2.0,
        )

        for seed, expected_detected in ((1, True), (2, False)):
            with self.subTest(seed=seed):
                result = resolve_detection(scores, Random(seed))

                self.assertEqual(result.scores, scores)
                self.assertAlmostEqual(result.detection_probability, 0.8)
                self.assertEqual(
                    result.detection_roll,
                    Random(seed).random(),
                )
                self.assertEqual(result.detected, expected_detected)

    def test_detection_with_zero_scores_cannot_succeed(self) -> None:
        from random import Random

        from simulation.hunting import DetectionScores, resolve_detection

        scores = DetectionScores(
            detector_perception=0.0,
            target_stealth=0.0,
            activity_overlap_modifier=1.0,
            weather_visibility_modifier=1.0,
            effective_perception=0.0,
            effective_stealth=0.0,
        )

        result = resolve_detection(scores, Random(1))

        self.assertEqual(result.detection_probability, 0.0)
        self.assertEqual(result.detection_roll, Random(1).random())
        self.assertFalse(result.detected)

    def test_detection_scores_include_habitat_conditions(self) -> None:
        scores = calculate_detection_scores(
            detector_definition={
                "statistics": {"perception": 8.0},
            },
            target_definition={
                "statistics": {"stealth": 7.0},
            },
            activity_overlap_modifier=0.5,
            weather_definition={
                "visibility_modifier": 0.45,
            },
            habitat_definition={
                "conditions": {
                    "openness": 0.5,
                    "vegetation_density": 0.7,
                },
            },
        )

        self.assertEqual(scores.detector_perception, 8.0)
        self.assertEqual(scores.target_stealth, 7.0)
        self.assertAlmostEqual(scores.effective_perception, 0.9)
        self.assertAlmostEqual(scores.effective_stealth, 11.9)

    def test_detection_trait_only_boosts_detector_perception(self) -> None:
        scores = calculate_detection_scores(
            detector_definition={
                "id": "test_detector",
                "taxon_id": "animalia",
                "trait_ids": ["test_detection_trait"],
                "statistics": {"perception": 8.0},
            },
            target_definition={
                "id": "test_target",
                "taxon_id": "animalia",
                "statistics": {"stealth": 7.0},
            },
            activity_overlap_modifier=1.0,
            weather_definition={"visibility_modifier": 1.0},
            taxon_definitions=[
                {
                    "id": "animalia",
                    "parent_taxon_id": None,
                },
            ],
            trait_definitions=[
                {
                    "id": "test_detection_trait",
                    "effects": [
                        {"target": "detection", "modifier": 1.5},
                        {"target": "stealth", "modifier": 2.0},
                    ],
                },
            ],
        )

        self.assertEqual(scores.detector_perception, 8.0)
        self.assertEqual(scores.target_stealth, 7.0)
        self.assertAlmostEqual(scores.effective_perception, 12.0)
        self.assertEqual(scores.effective_stealth, 7.0)

    def test_stealth_trait_only_boosts_target_stealth(self) -> None:
        scores = calculate_detection_scores(
            detector_definition={
                "id": "test_detector",
                "taxon_id": "animalia",
                "statistics": {"perception": 8.0},
            },
            target_definition={
                "id": "test_target",
                "taxon_id": "animalia",
                "trait_ids": ["test_stealth_trait"],
                "statistics": {"stealth": 7.0},
            },
            activity_overlap_modifier=1.0,
            weather_definition={"visibility_modifier": 1.0},
            taxon_definitions=[
                {
                    "id": "animalia",
                    "parent_taxon_id": None,
                },
            ],
            trait_definitions=[
                {
                    "id": "test_stealth_trait",
                    "effects": [
                        {"target": "stealth", "modifier": 1.5},
                        {"target": "detection", "modifier": 2.0},
                    ],
                },
            ],
        )

        self.assertEqual(scores.detector_perception, 8.0)
        self.assertEqual(scores.target_stealth, 7.0)
        self.assertEqual(scores.effective_perception, 8.0)
        self.assertAlmostEqual(scores.effective_stealth, 10.5)

    def test_detection_combines_environment_and_inherited_traits(self) -> None:
        scores = calculate_detection_scores(
            detector_definition={
                "taxon_id": "test_taxon",
                "statistics": {"perception": 8.0},
            },
            target_definition={
                "taxon_id": "test_taxon",
                "statistics": {"stealth": 7.0},
            },
            activity_overlap_modifier=0.5,
            weather_definition={"visibility_modifier": 0.45},
            habitat_definition={
                "conditions": {
                    "openness": 0.5,
                    "vegetation_density": 0.7,
                },
            },
            taxon_definitions=[
                {
                    "id": "test_taxon",
                    "parent_taxon_id": None,
                    "default_trait_ids": ["test_inherited_trait"],
                },
            ],
            trait_definitions=[
                {
                    "id": "test_inherited_trait",
                    "effects": [
                        {"target": "detection", "modifier": 1.5},
                        {"target": "stealth", "modifier": 2.0},
                    ],
                },
            ],
        )

        self.assertEqual(scores.detector_perception, 8.0)
        self.assertEqual(scores.target_stealth, 7.0)
        self.assertAlmostEqual(scores.effective_perception, 1.35)
        self.assertAlmostEqual(scores.effective_stealth, 23.8)

    def test_calculates_chase_scores_from_habitat_and_weather(self) -> None:
        from simulation.hunting import calculate_chase_scores

        scores = calculate_chase_scores(
            predator_definition={
                "id": "test_predator",
                "taxon_id": "test_taxon",
                "available_movement_modes": ["terrestrial"],
                "statistics": {"mobility": 8.0},
            },
            prey_definition={
                "id": "test_prey",
                "taxon_id": "test_taxon",
                "available_movement_modes": ["terrestrial"],
                "statistics": {"mobility": 6.0},
            },
            taxon_definitions=[
                {"id": "test_taxon", "parent_taxon_id": None},
            ],
            trait_definitions=[],
            habitat_definition={
                "movement_modifiers": {"terrestrial": 0.9},
            },
            weather_definition={
                "movement_modifiers": {"terrestrial": 0.9},
            },
            predator_movement_mode="terrestrial",
            prey_movement_mode="terrestrial",
        )

        self.assertAlmostEqual(scores.predator_mobility, 6.48)
        self.assertAlmostEqual(scores.prey_escape_mobility, 4.86)

    def test_chase_applies_escape_trait_only_to_prey(self) -> None:
        from simulation.hunting import calculate_chase_scores

        scores = calculate_chase_scores(
            predator_definition={
                "id": "test_predator",
                "taxon_id": "test_taxon",
                "available_movement_modes": ["terrestrial"],
                "statistics": {"mobility": 8.0},
            },
            prey_definition={
                "id": "test_prey",
                "taxon_id": "test_taxon",
                "available_movement_modes": ["terrestrial"],
                "statistics": {"mobility": 6.0},
            },
            taxon_definitions=[
                {
                    "id": "test_taxon",
                    "parent_taxon_id": None,
                    "default_trait_ids": ["test_escape_trait"],
                },
            ],
            trait_definitions=[
                {
                    "id": "test_escape_trait",
                    "effects": [
                        {"target": "escape_mobility", "modifier": 1.15},
                    ],
                },
            ],
            habitat_definition={
                "movement_modifiers": {"terrestrial": 0.9},
            },
            weather_definition={
                "movement_modifiers": {"terrestrial": 0.9},
            },
            predator_movement_mode="terrestrial",
            prey_movement_mode="terrestrial",
        )

        self.assertAlmostEqual(scores.predator_mobility, 6.48)
        self.assertAlmostEqual(scores.prey_escape_mobility, 5.589)

    def test_terrestrial_predator_cannot_follow_flying_prey(self) -> None:
        from simulation.hunting import calculate_chase_scores

        scores = calculate_chase_scores(
            predator_definition={
                "id": "test_predator",
                "taxon_id": "test_taxon",
                "available_movement_modes": ["terrestrial"],
                "statistics": {"mobility": 100.0},
            },
            prey_definition={
                "id": "test_prey",
                "taxon_id": "test_taxon",
                "available_movement_modes": ["terrestrial", "flight"],
                "flight_capabilities": ["short_burst"],
                "statistics": {"mobility": 6.0},
            },
            taxon_definitions=[
                {"id": "test_taxon", "parent_taxon_id": None},
            ],
            trait_definitions=[],
            habitat_definition={},
            weather_definition={},
            predator_movement_mode="terrestrial",
            prey_movement_mode="flight",
        )

        self.assertGreater(
            scores.predator_mobility,
            scores.prey_escape_mobility,
        )
        self.assertFalse(scores.movement_compatible)

    def test_matching_movement_modes_allow_chase(self) -> None:
        from simulation.hunting import calculate_chase_scores

        predator_definition = {
            "id": "test_predator",
            "taxon_id": "test_taxon",
            "available_movement_modes": ["terrestrial", "flight"],
            "flight_capabilities": ["powered"],
            "statistics": {"mobility": 8.0},
        }
        prey_definition = {
            "id": "test_prey",
            "taxon_id": "test_taxon",
            "available_movement_modes": ["terrestrial", "flight"],
            "flight_capabilities": ["short_burst"],
            "statistics": {"mobility": 6.0},
        }

        for movement_mode in ("terrestrial", "flight"):
            with self.subTest(movement_mode=movement_mode):
                scores = calculate_chase_scores(
                    predator_definition=predator_definition,
                    prey_definition=prey_definition,
                    taxon_definitions=[
                        {"id": "test_taxon", "parent_taxon_id": None},
                    ],
                    trait_definitions=[],
                    habitat_definition={},
                    weather_definition={},
                    predator_movement_mode=movement_mode,
                    prey_movement_mode=movement_mode,
                )

                self.assertTrue(scores.movement_compatible)

    def test_incompatible_chase_fails_without_random_roll(self) -> None:
        from random import Random

        from simulation.hunting import ChaseScores, resolve_chase

        scores = ChaseScores(
            predator_mobility=100.0,
            prey_escape_mobility=6.0,
            movement_compatible=False,
        )
        random_source = Random(104729)
        starting_random_state = random_source.getstate()

        result = resolve_chase(scores, random_source)

        self.assertEqual(result.scores, scores)
        self.assertEqual(result.catch_probability, 0.0)
        self.assertIsNone(result.chase_roll)
        self.assertFalse(result.caught)
        self.assertEqual(
            random_source.getstate(),
            starting_random_state,
        )

    def test_resolves_compatible_chase_using_seeded_roll(self) -> None:
        from random import Random

        from simulation.hunting import ChaseScores, resolve_chase

        scores = ChaseScores(
            predator_mobility=8.0,
            prey_escape_mobility=2.0,
            movement_compatible=True,
        )

        for seed, expected_caught in ((1, True), (2, False)):
            with self.subTest(seed=seed):
                random_source = Random(seed)
                expected_random_source = Random(seed)
                expected_roll = expected_random_source.random()

                result = resolve_chase(scores, random_source)

                self.assertEqual(result.scores, scores)
                self.assertAlmostEqual(result.catch_probability, 0.8)
                self.assertEqual(result.chase_roll, expected_roll)
                self.assertEqual(result.caught, expected_caught)
                self.assertEqual(
                    random_source.getstate(),
                    expected_random_source.getstate(),
                )

    def test_compatible_chase_with_zero_mobility_cannot_succeed(self) -> None:
        from random import Random

        from simulation.hunting import ChaseScores, resolve_chase

        scores = ChaseScores(
            predator_mobility=0.0,
            prey_escape_mobility=0.0,
            movement_compatible=True,
        )
        random_source = Random(104729)
        expected_random_source = Random(104729)
        expected_roll = expected_random_source.random()

        result = resolve_chase(scores, random_source)

        self.assertEqual(result.catch_probability, 0.0)
        self.assertEqual(result.chase_roll, expected_roll)
        self.assertFalse(result.caught)
        self.assertEqual(
            random_source.getstate(),
            expected_random_source.getstate(),
        )

    def test_chase_uses_selected_flight_capabilities(self) -> None:
        from simulation.hunting import calculate_chase_scores

        scores = calculate_chase_scores(
            predator_definition={
                "id": "test_predator",
                "taxon_id": "test_taxon",
                "available_movement_modes": ["flight"],
                "flight_capabilities": ["powered", "soaring"],
                "statistics": {"mobility": 8.0},
            },
            prey_definition={
                "id": "test_prey",
                "taxon_id": "test_taxon",
                "available_movement_modes": ["flight"],
                "flight_capabilities": ["powered", "short_burst"],
                "statistics": {"mobility": 6.0},
            },
            taxon_definitions=[
                {"id": "test_taxon", "parent_taxon_id": None},
            ],
            trait_definitions=[],
            habitat_definition={},
            weather_definition={
                "movement_modifiers": {"flight": 0.8},
                "flight_capability_modifiers": {
                    "powered": 0.75,
                    "soaring": 0.9,
                    "short_burst": 0.65,
                },
            },
            predator_movement_mode="flight",
            prey_movement_mode="flight",
            predator_flight_capability="soaring",
            prey_flight_capability="short_burst",
        )

        self.assertTrue(scores.movement_compatible)
        self.assertAlmostEqual(scores.predator_mobility, 5.76)
        self.assertAlmostEqual(scores.prey_escape_mobility, 3.12)

    def test_calculates_attack_scores_from_power_and_defense(self) -> None:
        from simulation.hunting import calculate_attack_scores

        scores = calculate_attack_scores(
            attacker_definition={
                "statistics": {
                    "power": 8.0,
                    "defense": 3.0,
                },
            },
            defender_definition={
                "statistics": {
                    "power": 9.0,
                    "defense": 6.0,
                },
            },
        )

        self.assertEqual(scores.attacker_power, 8.0)
        self.assertEqual(scores.defender_defense, 6.0)
        self.assertEqual(scores.effective_power, 8.0)
        self.assertEqual(scores.effective_defense, 6.0)

    def test_resolves_attack_using_effective_scores_and_seeded_roll(self) -> None:
        from random import Random

        from simulation.hunting import AttackScores, resolve_attack

        scores = AttackScores(
            attacker_power=2.0,
            defender_defense=8.0,
            effective_power=8.0,
            effective_defense=2.0,
        )

        for seed, expected_hit in ((1, True), (2, False)):
            with self.subTest(seed=seed):
                random_source = Random(seed)
                expected_random_source = Random(seed)
                expected_roll = expected_random_source.random()

                result = resolve_attack(scores, random_source)

                self.assertEqual(result.scores, scores)
                self.assertAlmostEqual(result.hit_probability, 0.8)
                self.assertEqual(result.attack_roll, expected_roll)
                self.assertEqual(result.hit, expected_hit)
                self.assertEqual(
                    random_source.getstate(),
                    expected_random_source.getstate(),
                )

    def test_attack_with_zero_effective_scores_cannot_hit(self) -> None:
        from random import Random

        from simulation.hunting import AttackScores, resolve_attack

        scores = AttackScores(
            attacker_power=8.0,
            defender_defense=6.0,
            effective_power=0.0,
            effective_defense=0.0,
        )
        random_source = Random(104729)
        expected_random_source = Random(104729)
        expected_roll = expected_random_source.random()

        result = resolve_attack(scores, random_source)

        self.assertEqual(result.scores, scores)
        self.assertEqual(result.hit_probability, 0.0)
        self.assertEqual(result.attack_roll, expected_roll)
        self.assertFalse(result.hit)
        self.assertEqual(
            random_source.getstate(),
            expected_random_source.getstate(),
        )


if __name__ == "__main__":
    unittest.main()