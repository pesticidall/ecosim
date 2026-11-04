import unittest
from dataclasses import replace
from random import Random

from simulation.group_detention import calculate_group_detention_scores
from simulation.groups import AnimalGroup, GroupParticipants, GroupRole
from simulation.hunting import calculate_detention_scores, resolve_detention
from simulation.injuries import create_injury_from_trauma


class TestGroupDetention(unittest.TestCase):
    def setUp(self):
        self.predator = {"id": "predator", "typical_adult_mass_kg": 40.0,
                         "statistics": {"power": 8.0, "intelligence": 10.0}}
        self.prey = {"id": "prey", "typical_adult_mass_kg": 10.0,
                     "statistics": {"power": 4.0, "mobility": 6.0, "intelligence": 10.0}}

    def participants(self, animal_id, count, role):
        return GroupParticipants(AnimalGroup(animal_id, "region", "local", count, role), ((),) * count)

    def test_solo_group_detention_matches_ordinary_injured_participants(self):
        injury = create_injury_from_trauma("attack", 4.0)
        hunters = replace(self.participants("predator", 1, GroupRole.HUNTING), member_injuries=((injury,),))
        prey = replace(self.participants("prey", 1, GroupRole.DEFENSIVE), member_injuries=((injury,),))
        expected = calculate_detention_scores(self.predator, self.prey, (injury,), (injury,))
        actual = calculate_group_detention_scores(hunters, prey, self.predator, self.prey, 0)
        self.assertEqual(actual.effective_restraint, expected.effective_restraint)
        self.assertEqual(actual.effective_escape, expected.effective_escape)
        self.assertEqual(actual.relative_mass_factor, expected.relative_mass_factor)
        self.assertEqual(actual.defensive_support, 1.0)

    def test_more_hunters_help_restraint_and_more_defenders_help_escape(self):
        solo = self.participants("predator", 1, GroupRole.HUNTING)
        hunters = self.participants("predator", 4, GroupRole.HUNTING)
        target = self.participants("prey", 1, GroupRole.DEFENSIVE)
        herd = self.participants("prey", 4, GroupRole.DEFENSIVE)
        first = calculate_group_detention_scores(solo, target, self.predator, self.prey, 0)
        second = calculate_group_detention_scores(hunters, target, self.predator, self.prey, 0)
        defended = calculate_group_detention_scores(hunters, herd, self.predator, self.prey, 0)
        results = [resolve_detention(scores, Random(5)) for scores in (first, second, defended)]
        self.assertGreater(results[1].detention_probability, results[0].detention_probability)
        self.assertLess(results[2].detention_probability, results[1].detention_probability)
        self.assertEqual(results[0].detention_roll, results[2].detention_roll)
        self.assertEqual(second.relative_mass_factor, first.relative_mass_factor)
        self.assertLess(second.effective_restraint, first.effective_restraint * 4)

    def test_updated_hunter_target_and_companion_injuries_have_separate_effects(self):
        injury = create_injury_from_trauma("counterattack", 4.0)
        hunters = self.participants("predator", 2, GroupRole.HUNTING)
        herd = self.participants("prey", 2, GroupRole.DEFENSIVE)
        healthy = calculate_group_detention_scores(hunters, herd, self.predator, self.prey, 0)
        wounded_hunters = replace(hunters, member_injuries=((injury,), ()))
        wounded_herd = replace(herd, member_injuries=((injury,), (injury,)))
        wounded = calculate_group_detention_scores(wounded_hunters, wounded_herd, self.predator, self.prey, 0)
        self.assertAlmostEqual(wounded.effective_restraint, healthy.effective_restraint * 0.75)
        self.assertLess(wounded.defensive_support, healthy.defensive_support)
        self.assertEqual(wounded.effective_break_free_power, 2.0)
        self.assertEqual(wounded.prey_injury_modifier, 0.5)

    def test_group_detention_preserves_traits_and_rejects_bad_target_context(self):
        hunters = self.participants("predator", 2, GroupRole.HUNTING)
        prey = self.participants("prey", 2, GroupRole.DEFENSIVE)
        predator = {**self.predator, "taxon_id": "root", "trait_ids": ["restraint"]}
        target = {**self.prey, "taxon_id": "root", "trait_ids": ["resistance"]}
        baseline = calculate_group_detention_scores(hunters, prey, predator, target, 0)
        scores = calculate_group_detention_scores(hunters, prey, predator, target, 0,
            [{"id": "root", "parent_taxon_id": None}], [
                {"id": "restraint", "effects": [{"target": "restraint", "modifier": 1.2}]},
                {"id": "resistance", "effects": [{"target": "restraint_resistance", "modifier": 1.3}]},
            ])
        self.assertAlmostEqual(scores.effective_restraint, baseline.effective_restraint * 1.2)
        self.assertAlmostEqual(scores.effective_escape, baseline.effective_escape * 1.3)
        for index, error in ((True, TypeError), (-1, ValueError), (2, ValueError)):
            with self.subTest(index=index), self.assertRaises(error):
                calculate_group_detention_scores(hunters, prey, predator, target, index)
        displaced = replace(prey, group=replace(prey.group, habitat_id="other"))
        with self.assertRaises(ValueError):
            calculate_group_detention_scores(hunters, displaced, predator, target, 0)
