import unittest

from simulation.hunting import calculate_detection_scores


class TestHunting(unittest.TestCase):
    def test_complete_hunt_retains_all_stage_outcomes_and_random_order(self) -> None:
        from random import Random

        from simulation.carrion import consume_carrion
        from simulation.deaths import DeathCause
        from simulation.predation import create_predation_remains

        from simulation.hunting import (
            AttackScores, ChaseScores, DetectionScores, HuntOutcomeStatus,
            resolve_hunt,
        )

        method = {"id": "test_method", "trauma_modifier": 1.0,
                  "trait_effect_target": "bite_effectiveness"}
        predator = {"id": "predator", "taxon_id": "root",
                    "typical_adult_mass_kg": 10.0,
                    "statistics": {"power": 8.0, "defense": 0.0}}
        prey = {"id": "prey", "taxon_id": "root",
                "available_movement_modes": ["terrestrial"],
                "typical_adult_mass_kg": 10.0,
                "statistics": {"power": 8.0, "defense": 0.0, "mobility": 6.0}}
        cases = (
            (False, True, True, 1, 1, HuntOutcomeStatus.NOT_DETECTED),
            (True, False, True, 1, 2, HuntOutcomeStatus.ESCAPED_CHASE),
            (True, True, False, 1, 3, HuntOutcomeStatus.ATTACK_MISSED),
            (True, True, True, 1, 5, HuntOutcomeStatus.SECURED),
            (True, True, True, 5, 5, HuntOutcomeStatus.ESCAPED_DETENTION),
        )
        for detected, caught, hit, seed, rolls, status in cases:
            with self.subTest(status=status):
                random_source = Random(seed)
                expected_random = Random(seed)
                for _ in range(rolls):
                    expected_random.random()
                result = resolve_hunt(
                    DetectionScores(1.0, 1.0, 1.0, 1.0, float(detected), float(not detected)),
                    ChaseScores(float(caught), float(not caught), True),
                    AttackScores(8.0, 0.0, 8.0 if hit else 0.0, 0.0 if hit else 1.0),
                    predator, prey, method, None,
                    taxon_definitions=iter([{"id": "root", "parent_taxon_id": None}]),
                    trait_definitions=iter(()), temperament_definitions=(),
                    contextual_suitability={"escape": 1.0},
                    random_source=random_source,
                )
                self.assertIs(result.outcome.status, status)
                self.assertEqual(result.outcome.prey_secured, status is HuntOutcomeStatus.SECURED)
                self.assertEqual(random_source.getstate(), expected_random.getstate())
                if status in (HuntOutcomeStatus.SECURED, HuntOutcomeStatus.ESCAPED_DETENTION):
                    self.assertEqual(len(result.contact.prey_injuries), 1)
                    self.assertEqual(result.contact.response.selected_action_id, "escape")
                    self.assertEqual(result.outcome.detained, result.contact.detention.detained)
                else:
                    self.assertEqual(result.contact.prey_injuries, ())
                    self.assertIsNone(result.contact.response)
                    self.assertIsNone(result.contact.detention)
                self.assertEqual(result.contact.predator_injuries, ())
                self.assertEqual(prey["statistics"]["power"], 8.0)
                remains = create_predation_remains(
                    result, prey, predator_id=predator["id"], habitat_id="test_habitat",
                )
                if status is not HuntOutcomeStatus.SECURED:
                    self.assertIsNone(remains)
                else:
                    self.assertIsNotNone(remains)
                    self.assertIs(remains.death.cause, DeathCause.PREDATION)
                    self.assertEqual(remains.death.animal_id, "prey")
                    self.assertEqual(remains.death.count, 1)
                    self.assertEqual(remains.carrion.source_animal_id, "prey")
                    self.assertEqual(remains.carrion.habitat_id, "test_habitat")
                    self.assertEqual(remains.carrion.original_biomass_kg, 10.0)
                    self.assertEqual(remains.carrion.available_biomass_kg, 10.0)
                    self.assertEqual(remains.carrion.first_access_consumer_id, "predator")
                    blocked = consume_carrion(remains.carrion, "scavenger", 2.0)
                    self.assertFalse(blocked.access_granted)
                    self.assertEqual(blocked.consumed_biomass_kg, 0.0)
                    feeding = consume_carrion(remains.carrion, "predator", 2.0)
                    self.assertTrue(feeding.access_granted)
                    self.assertEqual(feeding.consumed_biomass_kg, 2.0)
                    self.assertEqual(feeding.updated_carrion.available_biomass_kg, 8.0)
                    self.assertEqual(remains.carrion.available_biomass_kg, 10.0)
                self.assertEqual(random_source.getstate(), expected_random.getstate())

    def test_hunt_contact_integrates_injury_response_and_detention(self) -> None:
        from random import Random

        from simulation.hunting import AttackResult, AttackScores, resolve_hunt_contact
        from simulation.injuries import InjurySeverity

        method = {
            "id": "test_method", "trauma_modifier": 1.0,
            "trait_effect_target": "bite_effectiveness",
        }
        predator = {
            "id": "predator", "taxon_id": "root",
            "typical_adult_mass_kg": 10.0,
            "statistics": {"power": 8.0, "defense": 0.0},
        }
        for hit, action, expected_rolls in (
            (False, "escape", 0),
            (True, "escape", 2),
            (True, "counterattack", 3),
        ):
            with self.subTest(hit=hit, action=action):
                prey = {
                    "id": "prey", "taxon_id": "root",
                    "trait_ids": ["retaliation"],
                    "available_movement_modes": ["terrestrial"],
                    "typical_adult_mass_kg": 10.0,
                    "statistics": {"power": 8.0, "defense": 0.0, "mobility": 6.0},
                }
                attack = AttackResult(AttackScores(8.0, 0.0, 8.0, 0.0), 1.0, 0.0, hit)
                random_source = Random(1)
                expected_random = Random(1)
                for _ in range(expected_rolls):
                    expected_random.random()
                result = resolve_hunt_contact(
                    attack, predator, prey, method, method,
                    taxon_definitions=iter([{"id": "root", "parent_taxon_id": None}]),
                    trait_definitions=iter([{
                        "id": "retaliation", "action_capabilities": ["counterattack"],
                    }]),
                    temperament_definitions=(),
                    contextual_suitability={"escape": float(action == "escape"),
                                            "counterattack": float(action == "counterattack")},
                    random_source=random_source,
                )
                self.assertEqual(random_source.getstate(), expected_random.getstate())
                self.assertEqual(prey["statistics"]["power"], 8.0)
                if not hit:
                    self.assertEqual(result.prey_injuries, ())
                    self.assertEqual(result.predator_injuries, ())
                    self.assertIsNone(result.response)
                    self.assertIsNone(result.detention)
                    continue
                self.assertEqual(result.response.selected_action_id, action)
                self.assertIs(result.prey_injuries[0].severity, InjurySeverity.CRITICAL)
                self.assertEqual(result.detention.scores.effective_escape, 3.5)
                if action == "counterattack":
                    self.assertEqual(result.counterattack.scores.effective_power, 2.0)
                    self.assertIs(result.predator_injuries[0].severity, InjurySeverity.MODERATE)
                    self.assertEqual(result.predator_injuries[0].source_stage, "counterattack")
                    self.assertEqual(result.detention.scores.effective_restraint, 6.0)
                else:
                    self.assertIsNone(result.counterattack)
                    self.assertEqual(result.predator_injuries, ())
                    self.assertEqual(result.detention.scores.effective_restraint, 8.0)

    def test_hunt_approach_stops_at_failed_stages_and_preserves_random_order(self) -> None:
        from random import Random

        from simulation.hunting import (
            AttackScores,
            ChaseScores,
            DetectionScores,
            resolve_hunt_approach,
        )

        cases = (
            (False, True, True, True, 1, False, False),
            (True, False, True, True, 1, True, False),
            (True, True, False, True, 2, True, False),
            (True, True, True, False, 3, True, True),
            (True, True, True, True, 3, True, True),
        )
        for detected, compatible, caught, hit, rolls, has_chase, has_attack in cases:
            with self.subTest(detected=detected, compatible=compatible,
                              caught=caught, hit=hit):
                detection = DetectionScores(
                    detector_perception=1.0 if detected else 0.0,
                    target_stealth=0.0 if detected else 1.0,
                    activity_overlap_modifier=1.0,
                    weather_visibility_modifier=1.0,
                    effective_perception=1.0 if detected else 0.0,
                    effective_stealth=0.0 if detected else 1.0,
                )
                chase = ChaseScores(
                    predator_mobility=1.0 if caught else 0.0,
                    prey_escape_mobility=0.0 if caught else 1.0,
                    movement_compatible=compatible,
                )
                attack = AttackScores(
                    attacker_power=1.0 if hit else 0.0,
                    defender_defense=0.0 if hit else 1.0,
                    effective_power=1.0 if hit else 0.0,
                    effective_defense=0.0 if hit else 1.0,
                )
                random_source = Random(19)
                expected_random = Random(19)
                expected_rolls = [expected_random.random() for _ in range(rolls)]
                result = resolve_hunt_approach(detection, chase, attack, random_source)

                self.assertIs(result.detection.scores, detection)
                self.assertEqual(result.detection.detected, detected)
                self.assertEqual(result.detection.detection_roll, expected_rolls[0])
                self.assertEqual(result.chase is not None, has_chase)
                self.assertEqual(result.attack is not None, has_attack)
                if has_chase:
                    self.assertIs(result.chase.scores, chase)
                    self.assertEqual(result.chase.caught, compatible and caught)
                    if compatible:
                        self.assertEqual(result.chase.chase_roll, expected_rolls[1])
                    else:
                        self.assertIsNone(result.chase.chase_roll)
                if has_attack:
                    self.assertIs(result.attack.scores, attack)
                    self.assertEqual(result.attack.hit, hit)
                    self.assertEqual(result.attack.attack_roll, expected_rolls[2])
                self.assertEqual(random_source.getstate(), expected_random.getstate())

    def test_prey_power_improves_breaking_free_without_guaranteeing_escape(self) -> None:
        from random import Random

        from simulation.hunting import calculate_detention_scores, resolve_detention

        predator = {"statistics": {"power": 8.0}}
        results = []
        for power in (0.0, 8.0):
            scores = calculate_detention_scores(
                predator, {"statistics": {"mobility": 6.0, "power": power}},
                predator_injuries=(), prey_injuries=(),
            )
            self.assertEqual(scores.prey_power, power)
            self.assertEqual(scores.effective_break_free_power, power)
            self.assertEqual(scores.effective_escape, 6.0 + power)
            results.append(resolve_detention(scores, Random(1)))

        weak, strong = results
        self.assertLess(strong.detention_probability, weak.detention_probability)
        self.assertGreater(strong.detention_probability, 0.0)
        self.assertEqual(strong.detention_roll, weak.detention_roll)
        self.assertTrue(strong.detained)

    def test_detention_applies_power_and_mobility_injuries_separately(self) -> None:
        from simulation.hunting import calculate_detention_scores
        from simulation.injuries import Injury, InjurySeverity

        injury = Injury(
            severity=InjurySeverity.MAJOR,
            source_stage="attack",
            power_modifier=0.5,
            mobility_modifier=0.75,
        )
        prey = {
            "taxon_id": "test_taxon",
            "trait_ids": ["resistance_trait"],
            "statistics": {"mobility": 6.0, "power": 8.0},
        }
        scores = calculate_detention_scores(
            {"taxon_id": "test_taxon", "statistics": {"power": 8.0}},
            prey, predator_injuries=(), prey_injuries=(injury,),
            taxon_definitions=[{"id": "test_taxon", "parent_taxon_id": None}],
            trait_definitions=[{
                "id": "resistance_trait",
                "effects": [{"target": "restraint_resistance", "modifier": 1.2}],
            }],
        )
        self.assertEqual(scores.effective_break_free_power, 4.0)
        self.assertAlmostEqual(scores.effective_escape, 10.2)
        self.assertEqual(scores.effective_restraint, 8.0)
        self.assertEqual(prey["statistics"], {"mobility": 6.0, "power": 8.0})

    def test_chase_combines_each_animals_injuries_with_movement_context(self) -> None:
        from simulation.hunting import calculate_chase_scores
        from simulation.injuries import create_injury_from_trauma

        predator = {
            "id": "test_predator",
            "taxon_id": "test_taxon",
            "available_movement_modes": ["terrestrial"],
            "statistics": {"mobility": 8.0},
        }
        prey = {
            "id": "test_prey",
            "taxon_id": "test_taxon",
            "trait_ids": ["escape_trait"],
            "available_movement_modes": ["terrestrial"],
            "statistics": {"mobility": 6.0},
        }
        major = create_injury_from_trauma("counterattack", 4.0)
        minor = create_injury_from_trauma("attack", 1.0)
        for predator_injuries, prey_injuries, predator_factor, prey_factor in (
            ((), (), 1.0, 1.0),
            ((major,), (), 0.5, 1.0),
            ((), (minor,), 1.0, 0.9),
            ((major,), (minor, major), 0.5, 0.45),
        ):
            with self.subTest(predator=predator_factor, prey=prey_factor):
                scores = calculate_chase_scores(
                    predator_definition=predator,
                    prey_definition=prey,
                    taxon_definitions=[
                        {"id": "test_taxon", "parent_taxon_id": None},
                    ],
                    trait_definitions=[{
                        "id": "escape_trait",
                        "effects": [{"target": "escape_mobility", "modifier": 1.2}],
                    }],
                    habitat_definition={"movement_modifiers": {"terrestrial": 0.9}},
                    weather_definition={"movement_modifiers": {"terrestrial": 0.8}},
                    predator_movement_mode="terrestrial",
                    prey_movement_mode="terrestrial",
                    predator_injuries=iter(predator_injuries),
                    prey_injuries=iter(prey_injuries),
                )
                self.assertAlmostEqual(scores.predator_mobility, 5.76 * predator_factor)
                self.assertAlmostEqual(scores.prey_escape_mobility, 5.184 * prey_factor)
                self.assertTrue(scores.movement_compatible)
                self.assertEqual(predator["statistics"]["mobility"], 8.0)
                self.assertEqual(prey["statistics"]["mobility"], 6.0)

    def test_attack_power_applies_cumulative_injury_condition(self) -> None:
        from simulation.hunting import calculate_attack_scores
        from simulation.injuries import create_injury_from_trauma

        attacker = {"statistics": {"power": 8.0}}
        defender = {"statistics": {"defense": 3.0}}
        injuries = (
            create_injury_from_trauma("attack", 1.0),
            create_injury_from_trauma("counterattack", 4.0),
        )
        healthy = calculate_attack_scores(attacker, defender)
        injured = calculate_attack_scores(
            attacker, defender, attacker_injuries=iter(injuries),
        )

        self.assertEqual(healthy.effective_power, 8.0)
        self.assertAlmostEqual(injured.effective_power, 3.6)
        self.assertEqual(injured.attacker_power, 8.0)
        self.assertEqual(injured.defender_defense, 3.0)
        self.assertEqual(injured.effective_defense, 3.0)
        self.assertEqual(attacker["statistics"]["power"], 8.0)

    def test_counterattack_combines_injury_and_trait_power(self) -> None:
        from random import Random

        from simulation.hunting import resolve_counterattack
        from simulation.injuries import create_injury_from_trauma

        prey = {
            "id": "test_prey",
            "taxon_id": "test_taxon",
            "trait_ids": ["test_trait"],
            "statistics": {"power": 8.0},
        }
        predator = {"statistics": {"defense": 3.0}}
        taxa = [{"id": "test_taxon", "parent_taxon_id": None}]
        traits = [{
            "id": "test_trait",
            "effects": [{"target": "counterattack_power", "modifier": 1.5}],
        }]
        injury = create_injury_from_trauma("attack", 4.0)
        result = resolve_counterattack(
            prey, predator, taxa, traits, Random(1),
            prey_injuries=(injury,),
        )
        healthy = resolve_counterattack(
            prey, predator, taxa, traits, Random(1),
        )

        self.assertEqual(result.scores.attacker_power, 8.0)
        self.assertEqual(result.scores.effective_power, 6.0)
        self.assertEqual(healthy.scores.effective_power, 12.0)
        self.assertEqual(result.scores.effective_defense, 3.0)
        self.assertAlmostEqual(result.hit_probability, 6.0 / 9.0)
        self.assertEqual(result.attack_roll, healthy.attack_roll)
        self.assertTrue(result.hit)
        self.assertEqual(prey["statistics"]["power"], 8.0)

    def test_resolves_attack_and_counterattack_contact_into_injury(self) -> None:
        from simulation.hunting import (
            AttackResult,
            AttackScores,
            resolve_attack_injury,
        )
        from simulation.injuries import InjurySeverity

        method = {
            "entity_type": "attack_method",
            "id": "test_method",
            "name": "Test Method",
            "description": "Tests contact injury resolution.",
            "trauma_modifier": 1.5,
            "trait_effect_target": "grapple_effectiveness",
        }
        trait = {
            "entity_type": "trait",
            "id": "test_trait",
            "name": "Test Trait",
            "description": "Improves grappling.",
            "effects": [
                {"target": "grapple_effectiveness", "modifier": 1.2},
            ],
        }
        for stage in ("attack", "counterattack"):
            for hit, defense, expected_injury in (
                (False, 3.0, False),
                (True, 20.0, False),
                (True, 3.0, True),
            ):
                with self.subTest(stage=stage, hit=hit, defense=defense):
                    scores = AttackScores(
                        attacker_power=4.0,
                        defender_defense=0.0,
                        effective_power=8.0,
                        effective_defense=defense,
                    )
                    result = AttackResult(
                        scores=scores,
                        hit_probability=8.0 / (8.0 + defense),
                        attack_roll=0.0 if hit else 0.99,
                        hit=hit,
                    )
                    injury = resolve_attack_injury(
                        result,
                        attack_method_definition=method,
                        attacker_mass_kg=10.0,
                        target_mass_kg=10.0,
                        contact_quality=0.5,
                        source_stage=stage,
                        trait_ids=("test_trait",),
                        trait_definitions=(trait,),
                    )
                    if not expected_injury:
                        self.assertIsNone(injury)
                    else:
                        self.assertIsNotNone(injury)
                        self.assertIs(injury.severity, InjurySeverity.MAJOR)
                        self.assertEqual(injury.source_stage, stage)
                        self.assertEqual(injury.power_modifier, 0.5)
                        self.assertEqual(injury.mobility_modifier, 0.5)
                    self.assertEqual(result.scores, scores)

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

    def test_post_contact_response_allows_ordinary_escape(
        self,
    ) -> None:
        from random import Random

        from simulation.hunting import select_post_contact_response

        prey_definition = {
            "id": "scrub_hare",
            "taxon_id": "animalia",
            "temperament_id": "skittish",
            "available_movement_modes": [
                "terrestrial",
            ],
        }
        taxon_definitions = [
            {
                "entity_type": "taxon",
                "id": "animalia",
                "name": "Animalia",
                "rank": "kingdom",
                "parent_taxon_id": None,
            },
        ]
        trait_definitions = []
        temperament_definitions = [
            {
                "entity_type": "temperament",
                "id": "skittish",
                "name": "Skittish",
                "description": (
                    "Favors escape while retaining defensive options."
                ),
                "action_weights": {
                    "escape": 1.4,
                    "counterattack": 0.7,
                },
            },
        ]

        selection = select_post_contact_response(
            prey_definition=prey_definition,
            taxon_definitions=taxon_definitions,
            trait_definitions=trait_definitions,
            temperament_definitions=temperament_definitions,
            contextual_suitability={
                "escape": 1.0,
                "counterattack": 1.0,
            },
            random_source=Random(0),
        )

        self.assertEqual(
            [
                option.action_id
                for option in selection.options
            ],
            ["escape"],
        )
        self.assertEqual(
            selection.options[0].temperament_preference,
            1.4,
        )
        self.assertEqual(
            selection.selected_action_id,
            "escape",
        )

    def test_post_contact_response_allows_capable_counterattack(
        self,
    ) -> None:
        from random import Random

        from simulation.hunting import select_post_contact_response

        prey_definition = {
            "id": "scrub_hare",
            "taxon_id": "leporidae",
            "temperament_id": "skittish",
            "available_movement_modes": [
                "terrestrial",
            ],
        }
        taxon_definitions = [
            {
                "entity_type": "taxon",
                "id": "animalia",
                "name": "Animalia",
                "rank": "kingdom",
                "parent_taxon_id": None,
            },
            {
                "entity_type": "taxon",
                "id": "leporidae",
                "name": "Leporidae",
                "rank": "family",
                "parent_taxon_id": "animalia",
                "default_trait_ids": [
                    "powerful_hindlimbs",
                ],
            },
        ]
        trait_definitions = [
            {
                "entity_type": "trait",
                "id": "powerful_hindlimbs",
                "name": "Powerful Hind Limbs",
                "description": "Strong rear limbs.",
                "action_capabilities": [
                    "counterattack",
                ],
            },
        ]
        temperament_definitions = [
            {
                "entity_type": "temperament",
                "id": "skittish",
                "name": "Skittish",
                "description": (
                    "Favors escape while retaining defensive options."
                ),
                "action_weights": {
                    "escape": 1.4,
                    "counterattack": 0.7,
                },
            },
        ]

        selection = select_post_contact_response(
            prey_definition=prey_definition,
            taxon_definitions=taxon_definitions,
            trait_definitions=trait_definitions,
            temperament_definitions=temperament_definitions,
            contextual_suitability={
                "escape": 0.1,
                "counterattack": 1.0,
            },
            random_source=Random(0),
        )

        self.assertEqual(
            [
                option.action_id
                for option in selection.options
            ],
            [
                "escape",
                "counterattack",
            ],
        )
        self.assertAlmostEqual(
            selection.options[0].combined_weight,
            0.14,
        )
        self.assertAlmostEqual(
            selection.options[1].combined_weight,
            0.7,
        )
        self.assertEqual(
            selection.selected_action_id,
            "counterattack",
        )

    def test_counterattack_reverses_roles_and_applies_trait_power(
        self,
    ) -> None:
        from simulation.hunting import calculate_counterattack_scores

        prey_definition = {
            "id": "scrub_hare",
            "taxon_id": "leporidae",
            "statistics": {
                "power": 3.0,
                "defense": 3.0,
            },
        }
        predator_definition = {
            "id": "caracal",
            "statistics": {
                "power": 7.0,
                "defense": 6.0,
            },
        }
        taxon_definitions = [
            {
                "entity_type": "taxon",
                "id": "animalia",
                "name": "Animalia",
                "rank": "kingdom",
                "parent_taxon_id": None,
            },
            {
                "entity_type": "taxon",
                "id": "leporidae",
                "name": "Leporidae",
                "rank": "family",
                "parent_taxon_id": "animalia",
                "default_trait_ids": [
                    "powerful_hindlimbs",
                ],
            },
        ]
        trait_definitions = [
            {
                "entity_type": "trait",
                "id": "powerful_hindlimbs",
                "name": "Powerful Hind Limbs",
                "description": "Strong rear limbs.",
                "effects": [
                    {
                        "target": "counterattack_power",
                        "modifier": 1.1,
                    },
                ],
            },
        ]

        scores = calculate_counterattack_scores(
            prey_definition=prey_definition,
            predator_definition=predator_definition,
            taxon_definitions=taxon_definitions,
            trait_definitions=trait_definitions,
        )

        self.assertEqual(scores.attacker_power, 3.0)
        self.assertEqual(scores.defender_defense, 6.0)
        self.assertAlmostEqual(scores.effective_power, 3.3)
        self.assertEqual(scores.effective_defense, 6.0)

    def test_resolves_counterattack_as_seeded_attack_contact(
        self,
    ) -> None:
        from random import Random

        from simulation.hunting import resolve_counterattack

        prey_definition = {
            "id": "scrub_hare",
            "taxon_id": "leporidae",
            "statistics": {
                "power": 3.0,
                "defense": 3.0,
            },
        }
        predator_definition = {
            "id": "caracal",
            "statistics": {
                "power": 7.0,
                "defense": 6.0,
            },
        }
        taxon_definitions = [
            {
                "entity_type": "taxon",
                "id": "animalia",
                "name": "Animalia",
                "rank": "kingdom",
                "parent_taxon_id": None,
            },
            {
                "entity_type": "taxon",
                "id": "leporidae",
                "name": "Leporidae",
                "rank": "family",
                "parent_taxon_id": "animalia",
                "default_trait_ids": [
                    "powerful_hindlimbs",
                ],
            },
        ]
        trait_definitions = [
            {
                "entity_type": "trait",
                "id": "powerful_hindlimbs",
                "name": "Powerful Hind Limbs",
                "description": "Strong rear limbs.",
                "effects": [
                    {
                        "target": "counterattack_power",
                        "modifier": 1.1,
                    },
                ],
            },
        ]
        random_source = Random(1)

        result = resolve_counterattack(
            prey_definition=prey_definition,
            predator_definition=predator_definition,
            taxon_definitions=taxon_definitions,
            trait_definitions=trait_definitions,
            random_source=random_source,
        )

        self.assertAlmostEqual(
            result.scores.effective_power,
            3.3,
        )
        self.assertEqual(
            result.scores.effective_defense,
            6.0,
        )
        self.assertAlmostEqual(
            result.hit_probability,
            3.3 / 9.3,
        )
        self.assertTrue(result.hit)
        self.assertEqual(
            result.scores.power_trait_effect.contributing_trait_ids,
            ("powerful_hindlimbs",),
        )

    def test_detention_scores_apply_injuries_to_both_animals(
        self,
    ) -> None:
        from simulation.hunting import calculate_detention_scores
        from simulation.injuries import (
            Injury,
            InjurySeverity,
        )

        predator_definition = {
            "statistics": {
                "power": 8.0,
            },
        }
        prey_definition = {
            "statistics": {
                "mobility": 6.0,
            },
        }
        predator_injuries = [
            Injury(
                severity=InjurySeverity.MAJOR,
                source_stage="counterattack",
                power_modifier=0.5,
                mobility_modifier=0.5,
            ),
        ]
        prey_injuries = [
            Injury(
                severity=InjurySeverity.MODERATE,
                source_stage="attack",
                power_modifier=0.75,
                mobility_modifier=0.75,
            ),
        ]

        scores = calculate_detention_scores(
            predator_definition=predator_definition,
            prey_definition=prey_definition,
            predator_injuries=predator_injuries,
            prey_injuries=prey_injuries,
        )

        self.assertEqual(scores.predator_restraint, 8.0)
        self.assertEqual(scores.prey_escape, 6.0)
        self.assertEqual(
            scores.predator_injury_modifier,
            0.5,
        )
        self.assertEqual(
            scores.prey_injury_modifier,
            0.75,
        )
        self.assertEqual(
            scores.effective_restraint,
            4.0,
        )
        self.assertEqual(
            scores.effective_escape,
            4.5,
        )

    def test_detention_uses_compressed_relative_mass(
        self,
    ) -> None:
        from simulation.hunting import calculate_detention_scores

        predator_definition = {
            "typical_adult_mass_kg": 56.0,
            "statistics": {
                "power": 8.0,
            },
        }
        prey_definition = {
            "typical_adult_mass_kg": 3.5,
            "statistics": {
                "mobility": 6.0,
            },
        }

        scores = calculate_detention_scores(
            predator_definition=predator_definition,
            prey_definition=prey_definition,
            predator_injuries=[],
            prey_injuries=[],
        )

        self.assertEqual(
            scores.relative_mass_factor,
            2.0,
        )
        self.assertEqual(
            scores.effective_restraint,
            16.0,
        )
        self.assertEqual(
            scores.effective_escape,
            6.0,
        )

    def test_detention_applies_restraint_trait_effects(
        self,
    ) -> None:
        from simulation.hunting import calculate_detention_scores

        predator_definition = {
            "id": "caracal",
            "taxon_id": "animalia",
            "typical_adult_mass_kg": 10.0,
            "trait_ids": ["powerful_grapple"],
            "statistics": {
                "power": 8.0,
            },
        }
        prey_definition = {
            "id": "scrub_hare",
            "taxon_id": "animalia",
            "typical_adult_mass_kg": 10.0,
            "trait_ids": ["powerful_hindlimbs"],
            "statistics": {
                "mobility": 6.0,
            },
        }
        taxon_definitions = [
            {
                "entity_type": "taxon",
                "id": "animalia",
                "name": "Animalia",
                "rank": "kingdom",
                "parent_taxon_id": None,
            },
        ]
        trait_definitions = [
            {
                "entity_type": "trait",
                "id": "powerful_grapple",
                "name": "Powerful Grapple",
                "description": "Improves physical restraint.",
                "effects": [
                    {
                        "target": "restraint",
                        "modifier": 1.2,
                    },
                ],
            },
            {
                "entity_type": "trait",
                "id": "powerful_hindlimbs",
                "name": "Powerful Hind Limbs",
                "description": "Improves resistance to restraint.",
                "effects": [
                    {
                        "target": "restraint_resistance",
                        "modifier": 1.1,
                    },
                ],
            },
        ]

        scores = calculate_detention_scores(
            predator_definition=predator_definition,
            prey_definition=prey_definition,
            predator_injuries=[],
            prey_injuries=[],
            taxon_definitions=taxon_definitions,
            trait_definitions=trait_definitions,
        )

        self.assertEqual(
            scores.restraint_trait_effect.modifier,
            1.2,
        )
        self.assertEqual(
            scores.resistance_trait_effect.modifier,
            1.1,
        )
        self.assertAlmostEqual(
            scores.effective_restraint,
            9.6,
        )
        self.assertAlmostEqual(
            scores.effective_escape,
            6.6,
        )

    def test_resolves_detention_with_seeded_roll(
        self,
    ) -> None:
        from random import Random

        from simulation.hunting import (
            calculate_detention_scores,
            resolve_detention,
        )

        scores = calculate_detention_scores(
            predator_definition={
                "statistics": {
                    "power": 8.0,
                },
            },
            prey_definition={
                "statistics": {
                    "mobility": 2.0,
                },
            },
            predator_injuries=[],
            prey_injuries=[],
        )

        result = resolve_detention(
            scores=scores,
            random_source=Random(1),
        )

        self.assertIs(result.scores, scores)
        self.assertEqual(
            result.detention_probability,
            0.8,
        )
        self.assertAlmostEqual(
            result.detention_roll,
            0.13436424411240122,
        )
        self.assertTrue(result.detained)

    def test_zero_restraint_cannot_detain_or_consume_randomness(
        self,
    ) -> None:
        from random import Random

        from simulation.hunting import (
            calculate_detention_scores,
            resolve_detention,
        )

        scores = calculate_detention_scores(
            predator_definition={
                "statistics": {
                    "power": 0.0,
                },
            },
            prey_definition={
                "statistics": {
                    "mobility": 0.0,
                },
            },
            predator_injuries=[],
            prey_injuries=[],
        )
        random_source = Random(1)
        expected_random_source = Random(1)

        result = resolve_detention(
            scores=scores,
            random_source=random_source,
        )

        self.assertEqual(
            result.detention_probability,
            0.0,
        )
        self.assertIsNone(result.detention_roll)
        self.assertFalse(result.detained)
        self.assertEqual(
            random_source.getstate(),
            expected_random_source.getstate(),
        )

    def test_classifies_hunt_outcome_by_completed_stage(
        self,
    ) -> None:
        from simulation.hunting import (
            HuntOutcomeStatus,
            classify_hunt_outcome,
        )

        cases = (
            (
                False,
                False,
                False,
                False,
                HuntOutcomeStatus.NOT_DETECTED,
            ),
            (
                True,
                False,
                False,
                False,
                HuntOutcomeStatus.ESCAPED_CHASE,
            ),
            (
                True,
                True,
                False,
                False,
                HuntOutcomeStatus.ATTACK_MISSED,
            ),
            (
                True,
                True,
                True,
                False,
                HuntOutcomeStatus.ESCAPED_DETENTION,
            ),
            (
                True,
                True,
                True,
                True,
                HuntOutcomeStatus.SECURED,
            ),
        )

        for detected, caught, hit, detained, expected in cases:
            with self.subTest(expected=expected.value):
                self.assertIs(
                    classify_hunt_outcome(
                        detected=detected,
                        caught=caught,
                        hit=hit,
                        detained=detained,
                    ),
                    expected,
                )

    def test_builds_structured_secured_hunt_outcome(
        self,
    ) -> None:
        from simulation.hunting import (
            HuntOutcomeStatus,
            build_hunt_outcome,
        )

        outcome = build_hunt_outcome(
            detected=True,
            caught=True,
            hit=True,
            detained=True,
        )

        self.assertTrue(outcome.detected)
        self.assertTrue(outcome.caught)
        self.assertTrue(outcome.hit)
        self.assertTrue(outcome.detained)
        self.assertIs(
            outcome.status,
            HuntOutcomeStatus.SECURED,
        )
        self.assertTrue(outcome.prey_secured)


if __name__ == "__main__":
    unittest.main()
