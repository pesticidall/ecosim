import unittest

from simulation.groups import AnimalGroup, GroupRole, calculate_group_food_requirement, form_local_groups
from simulation.world_state import HabitatState, RegionState


class TestGroups(unittest.TestCase):
    def test_defensive_gatherings_shrink_with_local_food_coverage(self):
        from simulation.groups import calculate_defensive_group_size

        for nutrition, expected in ((1.0, 4), (0.75, 3), (0.5, 2), (0.1, 1), (0.0, 1)):
            with self.subTest(nutrition=nutrition):
                self.assertEqual(calculate_defensive_group_size(10, 4, nutrition), expected)

    def test_defensive_gatherings_respect_population_and_capability_limits(self):
        from simulation.groups import calculate_defensive_group_size

        for population, ceiling, nutrition, expected in (
            (0, 4, 1.0, 0), (1, 4, 1.0, 1), (2, 4, 1.0, 2),
            (2, 4, 0.5, 1), (20, 1, 0.0, 1),
        ):
            with self.subTest(population=population, ceiling=ceiling, nutrition=nutrition):
                self.assertEqual(calculate_defensive_group_size(population, ceiling, nutrition), expected)
        self.assertEqual(calculate_defensive_group_size(10, 4), 4)

    def test_defensive_gatherings_reject_invalid_counts_and_food_coverage(self):
        from simulation.groups import calculate_defensive_group_size

        for population, ceiling, nutrition, error in (
            (True, 4, 1.0, TypeError), (2.0, 4, 1.0, TypeError),
            (-1, 4, 1.0, ValueError), (2, True, 1.0, TypeError),
            (2, 2.0, 1.0, TypeError), (2, 0, 1.0, ValueError),
            (2, -1, 1.0, ValueError), (2, 4, True, TypeError),
            (2, 4, "0.5", TypeError), (2, 4, -0.1, ValueError),
            (2, 4, 1.1, ValueError), (2, 4, float("nan"), ValueError),
            (2, 4, float("inf"), ValueError),
        ):
            with self.subTest(population=population, ceiling=ceiling, nutrition=nutrition):
                with self.assertRaises(error):
                    calculate_defensive_group_size(population, ceiling, nutrition)

    def test_group_participants_sample_without_replacing_injured_members(self):
        from random import Random
        from simulation.condition_cohorts import InjuryCohort
        from simulation.groups import calculate_group_power, select_group_participants
        from simulation.injuries import create_injury_from_trauma

        injury = create_injury_from_trauma("attack", 4.0)
        habitat = self.region.habitats["local"]
        habitat.animal_populations["predator"] = 3
        habitat.injury_cohorts["predator"] = (InjuryCohort((injury,), 1),)
        group = AnimalGroup("predator", "region", "local", 3, GroupRole.HUNTING)
        selected = select_group_participants(self.region, group, Random(2))
        self.assertEqual(selected.member_injuries.count((injury,)), 1)
        self.assertEqual(selected.member_injuries.count(()), 2)
        self.assertEqual(habitat.injury_cohorts["predator"], (InjuryCohort((injury,), 1),))
        self.assertEqual(habitat.animal_populations["predator"], 3)
        power = calculate_group_power(group, {"id": "predator", "statistics": {
            "power": 8.0, "intelligence": 10.0}}, selected.member_injuries)
        self.assertAlmostEqual(power.effective_member_power, 8.0 * 2.5 / 3)

    def test_group_participant_selection_is_seeded_and_skips_uniform_rolls(self):
        from random import Random
        from simulation.condition_cohorts import InjuryCohort
        from simulation.groups import select_group_participants
        from simulation.injuries import create_injury_from_trauma

        group = AnimalGroup("predator", "region", "local", 3, GroupRole.HUNTING)
        random_source = Random(1)
        before = random_source.getstate()
        self.assertEqual(select_group_participants(self.region, group, random_source).member_injuries, ((), (), ()))
        self.assertEqual(random_source.getstate(), before)
        habitat = self.region.habitats["local"]
        injury = create_injury_from_trauma("attack", 1.0)
        habitat.injury_cohorts["predator"] = (InjuryCohort((injury,), 2),)
        first_random, second_random = Random(19), Random(19)
        first = select_group_participants(self.region, group, first_random)
        second = select_group_participants(self.region, group, second_random)
        self.assertEqual(first, second)
        self.assertEqual(first_random.getstate(), second_random.getstate())

    def test_group_participants_reject_stale_or_misplaced_groups_before_rolls(self):
        from random import Random
        from simulation.groups import select_group_participants

        for group in (
            AnimalGroup("predator", "region", "local", 8, GroupRole.HUNTING),
            AnimalGroup("predator", "wrong_region", "local", 2, GroupRole.HUNTING),
            AnimalGroup("predator", "region", "missing", 2, GroupRole.HUNTING),
        ):
            with self.subTest(group=group):
                random_source = Random(1)
                before = random_source.getstate()
                with self.assertRaises(ValueError):
                    select_group_participants(self.region, group, random_source)
                self.assertEqual(random_source.getstate(), before)

    def detection_definitions(self):
        return (
            {"id": "predator", "statistics": {"perception": 8.0, "stealth": 4.0, "intelligence": 10.0}},
            {"id": "prey", "statistics": {"stealth": 2.0, "perception": 8.0}},
        )

    def test_solo_group_detection_matches_existing_environment_scores(self):
        from simulation.hunting import calculate_detection_scores, calculate_group_detection_scores

        predator, prey = self.detection_definitions()
        habitat = {"conditions": {"openness": 0.8, "vegetation_density": 0.25}}
        weather = {"visibility_modifier": 0.5}
        expected = calculate_detection_scores(predator, prey, 0.5, weather, habitat)
        actual = calculate_group_detection_scores(
            AnimalGroup("predator", "region", "local", 1, GroupRole.HUNTING),
            AnimalGroup("prey", "region", "local", 1, GroupRole.DEFENSIVE),
            predator, prey, 0.5, weather, habitat,
        )
        self.assertEqual(actual.effective_perception, expected.effective_perception)
        self.assertEqual(actual.effective_stealth, expected.effective_stealth)
        self.assertEqual(actual.awareness_contribution, 0.0)
        self.assertEqual(actual.search_multiplier, 1.0)

    def test_group_detection_balances_stealth_against_prey_awareness(self):
        from random import Random
        from simulation.hunting import calculate_group_detection_scores, resolve_detection

        predator, prey = self.detection_definitions()
        hunters = AnimalGroup("predator", "region", "local", 4, GroupRole.HUNTING)
        herd = AnimalGroup("prey", "region", "local", 4, GroupRole.DEFENSIVE)
        values = []
        for stealth in (0.0, 10.0):
            predator["statistics"]["stealth"] = stealth
            scores = calculate_group_detection_scores(hunters, herd, predator, prey, 1.0, {})
            values.append(resolve_detection(scores, Random(1)))
        self.assertGreater(values[1].detection_probability, values[0].detection_probability)
        self.assertEqual(values[1].detection_roll, values[0].detection_roll)
        self.assertLess(values[1].scores.exposure, values[0].scores.exposure)
        prey["statistics"]["perception"] = 0.0
        unaware = resolve_detection(calculate_group_detection_scores(hunters, herd, predator, prey, 1.0, {}), Random(1))
        self.assertGreater(unaware.detection_probability, values[1].detection_probability)

    def test_larger_prey_groups_gain_awareness_and_activity_still_limits_detection(self):
        from simulation.hunting import calculate_group_detection_scores

        predator, prey = self.detection_definitions()
        hunters = AnimalGroup("predator", "region", "local", 4, GroupRole.HUNTING)
        solo = AnimalGroup("prey", "region", "local", 1, GroupRole.DEFENSIVE)
        herd = AnimalGroup("prey", "region", "local", 4, GroupRole.DEFENSIVE)
        first = calculate_group_detection_scores(hunters, solo, predator, prey, 1.0, {})
        second = calculate_group_detection_scores(hunters, herd, predator, prey, 1.0, {})
        self.assertGreater(second.effective_stealth, first.effective_stealth)
        inactive = calculate_group_detection_scores(hunters, herd, predator, prey, 0.0, {})
        self.assertEqual(inactive.effective_perception, 0.0)

    def test_group_detection_rejects_invalid_context(self):
        from dataclasses import replace
        from simulation.hunting import calculate_group_detection_scores

        predator, prey = self.detection_definitions()
        hunters = AnimalGroup("predator", "region", "local", 2, GroupRole.HUNTING)
        herd = AnimalGroup("prey", "region", "local", 2, GroupRole.DEFENSIVE)
        for invalid in (replace(herd, habitat_id="other"), replace(herd, animal_id="other"),
                        replace(herd, role=GroupRole.HUNTING)):
            with self.subTest(group=invalid), self.assertRaises(ValueError):
                calculate_group_detection_scores(hunters, invalid, predator, prey, 1.0, {})
        for value, error in ((True, TypeError), (float("nan"), ValueError), (11, ValueError)):
            predator["statistics"]["intelligence"] = value
            with self.subTest(value=value), self.assertRaises(error):
                calculate_group_detection_scores(hunters, herd, predator, prey, 1.0, {})

    def test_solo_group_contact_matches_ordinary_attack(self):
        from simulation.hunting import calculate_attack_scores, calculate_group_attack_scores
        from simulation.injuries import create_injury_from_trauma

        attacker = {"id": "predator", "statistics": {"power": 8.0, "intelligence": 5.0}}
        defender = {"id": "prey", "statistics": {"power": 4.0, "defense": 6.0, "intelligence": 5.0}}
        injury = create_injury_from_trauma("counterattack", 4.0)
        ordinary = calculate_attack_scores(attacker, defender, (injury,))
        scores = calculate_group_attack_scores(
            AnimalGroup("predator", "region", "local", 1, GroupRole.HUNTING),
            attacker, defender,
            AnimalGroup("prey", "region", "local", 1, GroupRole.DEFENSIVE),
            member_injuries=((injury,),),
        )
        self.assertEqual(scores.attacker_power, ordinary.attacker_power)
        self.assertEqual(scores.defender_defense, ordinary.defender_defense)
        self.assertEqual(scores.effective_power, ordinary.effective_power)
        self.assertEqual(scores.effective_defense, ordinary.effective_defense)

    def test_group_contact_uses_existing_seeded_resolver_and_defensive_support(self):
        from random import Random
        from simulation.hunting import calculate_group_attack_scores, resolve_attack

        attacker = {"id": "predator", "statistics": {"power": 8.0, "intelligence": 10.0}}
        defender = {"id": "prey", "statistics": {"power": 4.0, "defense": 8.0, "intelligence": 10.0}}
        solo = AnimalGroup("predator", "region", "local", 1, GroupRole.HUNTING)
        unit = AnimalGroup("predator", "region", "local", 4, GroupRole.HUNTING)
        herd = AnimalGroup("prey", "region", "local", 4, GroupRole.DEFENSIVE)
        solo_result = resolve_attack(calculate_group_attack_scores(solo, attacker, defender), Random(5))
        group_result = resolve_attack(calculate_group_attack_scores(unit, attacker, defender), Random(5))
        defended = resolve_attack(calculate_group_attack_scores(unit, attacker, defender, herd), Random(5))
        self.assertFalse(solo_result.hit)
        self.assertTrue(group_result.hit)
        self.assertFalse(defended.hit)
        self.assertGreater(group_result.hit_probability, solo_result.hit_probability)
        self.assertLess(defended.hit_probability, group_result.hit_probability)
        self.assertEqual(group_result.attack_roll, defended.attack_roll)
        self.assertEqual(group_result.attack_roll, solo_result.attack_roll)
        self.assertAlmostEqual(defended.scores.effective_defense, 8.0 * 4 ** 0.75)
        self.assertEqual(defender["statistics"]["defense"], 8.0)

    def test_group_contact_injuries_reduce_effective_power(self):
        from simulation.hunting import calculate_group_attack_scores
        from simulation.injuries import create_injury_from_trauma

        group = AnimalGroup("predator", "region", "local", 2, GroupRole.HUNTING)
        attacker = {"id": "predator", "statistics": {"power": 8.0, "intelligence": 10.0}}
        defender = {"id": "prey", "statistics": {"defense": 6.0}}
        healthy = calculate_group_attack_scores(group, attacker, defender)
        injury = create_injury_from_trauma("counterattack", 4.0)
        injured = calculate_group_attack_scores(group, attacker, defender, member_injuries=((), (injury,)))
        self.assertAlmostEqual(injured.effective_power, healthy.effective_power * 0.75)
        self.assertEqual(injured.effective_defense, healthy.effective_defense)

    def test_group_contact_rejects_wrong_roles_and_separated_groups(self):
        from simulation.hunting import calculate_group_attack_scores

        attacker = {"id": "predator", "statistics": {"power": 8.0, "intelligence": 5.0}}
        defender = {"id": "prey", "statistics": {"power": 4.0, "defense": 6.0, "intelligence": 5.0}}
        unit = AnimalGroup("predator", "region", "local", 2, GroupRole.HUNTING)
        for region_id, habitat_id in (("elsewhere", "local"), ("region", "other")):
            with self.subTest(region=region_id, habitat=habitat_id), self.assertRaisesRegex(ValueError, "share"):
                calculate_group_attack_scores(unit, attacker, defender,
                    AnimalGroup("prey", region_id, habitat_id, 3, GroupRole.DEFENSIVE))
        with self.assertRaisesRegex(ValueError, "hunting unit"):
            calculate_group_attack_scores(
                AnimalGroup("predator", "region", "local", 2, GroupRole.DEFENSIVE), attacker, defender)
        with self.assertRaisesRegex(ValueError, "defensive role"):
            calculate_group_attack_scores(unit, attacker, defender,
                AnimalGroup("prey", "region", "local", 3, GroupRole.HUNTING))

    def test_group_power_grows_with_diminishing_returns(self):
        from simulation.groups import calculate_group_power

        definition = {"id": "predator", "statistics": {"power": 8.0, "intelligence": 10.0}}
        powers = [calculate_group_power(
            AnimalGroup("predator", "region", "local", count, GroupRole.HUNTING), definition,
        ).effective_power for count in range(1, 11)]
        self.assertEqual(powers[0], 8.0)
        for index in range(1, 10):
            self.assertGreater(powers[index], powers[index - 1])
            self.assertLess(powers[index], 8.0 * (index + 1))
        gains = [right - left for left, right in zip(powers, powers[1:])]
        self.assertTrue(all(left > right for left, right in zip(gains, gains[1:])))

    def test_intelligence_improves_group_coordination_without_boosting_solo_power(self):
        from simulation.groups import calculate_group_power

        values = []
        for intelligence in (0.0, 5.0, 10.0):
            definition = {"id": "predator", "statistics": {"power": 8.0, "intelligence": intelligence}}
            solo = AnimalGroup("predator", "region", "local", 1, GroupRole.HUNTING)
            group = AnimalGroup("predator", "region", "local", 4, GroupRole.HUNTING)
            self.assertEqual(calculate_group_power(solo, definition).effective_power, 8.0)
            values.append(calculate_group_power(group, definition))
        self.assertLess(values[0].effective_power, values[1].effective_power)
        self.assertLess(values[1].effective_power, values[2].effective_power)
        self.assertEqual(values[0].coordination, 0.5)
        self.assertEqual(values[2].coordination, 1.0)

    def test_group_power_applies_condition_to_each_participant(self):
        from simulation.groups import calculate_group_power
        from simulation.injuries import create_injury_from_trauma

        group = AnimalGroup("predator", "region", "local", 2, GroupRole.HUNTING)
        definition = {"id": "predator", "statistics": {"power": 8.0, "intelligence": 10.0}}
        injuries = ((create_injury_from_trauma("attack", 1.0),),
                    (create_injury_from_trauma("counterattack", 4.0),))
        result = calculate_group_power(group, definition, injuries)
        self.assertAlmostEqual(result.effective_member_power, 5.6)
        self.assertAlmostEqual(result.effective_power, 5.6 * 2 ** 0.75)
        self.assertEqual(definition["statistics"]["power"], 8.0)
        with self.assertRaisesRegex(ValueError, "member_count"):
            calculate_group_power(group, definition, injuries[:1])

    def test_group_power_rejects_invalid_statistics_and_wrong_species(self):
        from simulation.groups import calculate_group_power

        group = AnimalGroup("predator", "region", "local", 2, GroupRole.DEFENSIVE)
        for field in ("power", "intelligence"):
            for value, error in ((True, TypeError), ("5", TypeError), (-1, ValueError),
                                 (11, ValueError), (float("nan"), ValueError), (float("inf"), ValueError)):
                with self.subTest(field=field, value=value), self.assertRaises(error):
                    statistics = {"power": 8.0, "intelligence": 5.0, field: value}
                    calculate_group_power(group, {"id": "predator", "statistics": statistics})
        with self.assertRaisesRegex(ValueError, "match"):
            calculate_group_power(group, {"id": "prey", "statistics": {"power": 8.0, "intelligence": 5.0}})

    def setUp(self):
        self.region = RegionState("region", habitats={
            "local": HabitatState("local", animal_populations={"predator": 7, "prey": 12}),
            "other": HabitatState("other", animal_populations={"predator": 20}),
        }, animal_populations={"predator": 27, "prey": 12})

    def test_forms_same_species_local_hunting_units_without_moving_animals(self):
        groups = form_local_groups(self.region, "local", "predator", 3, GroupRole.HUNTING)
        self.assertEqual([group.member_count for group in groups], [3, 3, 1])
        self.assertTrue(all(group.animal_id == "predator" and group.region_id == "region"
                            and group.habitat_id == "local" and group.role is GroupRole.HUNTING for group in groups))
        self.assertEqual(self.region.habitats["local"].animal_populations["predator"], 7)
        self.assertEqual(self.region.habitats["other"].animal_populations["predator"], 20)

    def test_defensive_groups_reform_when_context_or_population_changes(self):
        groups = form_local_groups(self.region, "local", "prey", 5, GroupRole.DEFENSIVE)
        self.assertEqual([group.member_count for group in groups], [5, 5, 2])
        self.region.habitats["local"].animal_populations["prey"] = 4
        updated = form_local_groups(self.region, "local", "prey", 3, GroupRole.DEFENSIVE)
        self.assertEqual([group.member_count for group in updated], [3, 1])
        self.assertEqual([group.member_count for group in groups], [5, 5, 2])
        self.assertEqual(form_local_groups(self.region, "local", "absent", 3, GroupRole.HUNTING), ())

    def test_group_food_requirement_counts_every_member(self):
        definition = {"id": "predator", "food_requirement_per_animal_per_cycle": 2.5}
        groups = form_local_groups(self.region, "local", "predator", 3, GroupRole.HUNTING)
        self.assertEqual([calculate_group_food_requirement(group, definition) for group in groups], [7.5, 7.5, 2.5])
        self.assertEqual(sum(calculate_group_food_requirement(group, definition) for group in groups), 17.5)
        with self.assertRaisesRegex(ValueError, "match"):
            calculate_group_food_requirement(groups[0], {**definition, "id": "prey"})

    def test_rejects_invalid_group_counts_and_unknown_habitat(self):
        for count, error in ((True, TypeError), (1.5, TypeError), (0, ValueError), (-1, ValueError)):
            with self.subTest(count=count):
                with self.assertRaises(error):
                    form_local_groups(self.region, "local", "predator", count, GroupRole.HUNTING)
                with self.assertRaises(error):
                    AnimalGroup("predator", "region", "local", count, GroupRole.HUNTING)
        with self.assertRaises(ValueError):
            form_local_groups(self.region, "missing", "predator", 3, GroupRole.HUNTING)
