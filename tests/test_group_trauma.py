import unittest
from dataclasses import replace

from simulation.group_trauma import resolve_group_contact_injury
from simulation.groups import AnimalGroup, GroupParticipants, GroupRole
from simulation.hunting import AttackResult, calculate_group_attack_scores, calculate_attack_scores
from simulation.injuries import InjurySeverity, create_injury_from_trauma


class TestGroupTrauma(unittest.TestCase):
    def setUp(self):
        self.predator = {"id": "predator", "typical_adult_mass_kg": 10.0,
                         "statistics": {"power": 8.0, "defense": 3.0, "intelligence": 10.0}}
        self.prey = {"id": "prey", "typical_adult_mass_kg": 10.0,
                     "statistics": {"power": 8.0, "defense": 3.0, "intelligence": 10.0}}
        self.hunters = GroupParticipants(AnimalGroup("predator", "region", "local", 4, GroupRole.HUNTING), ((),) * 4)
        self.herd = GroupParticipants(AnimalGroup("prey", "region", "local", 2, GroupRole.DEFENSIVE), ((),) * 2)
        self.method = {"id": "bite", "trauma_modifier": 1.0, "trait_effect_target": "bite_effectiveness"}

    def contact(self, hunters=None, hit=True, actor_index=0, target_index=1):
        hunters = hunters or self.hunters
        scores = calculate_group_attack_scores(hunters.group, self.predator, self.prey,
                                               self.herd.group, hunters.member_injuries)
        return resolve_group_contact_injury(
            AttackResult(scores, 0.5, 0.1 if hit else 0.9, hit), hunters, self.herd,
            self.predator, self.prey, self.method, actor_index, target_index,
        )

    def test_group_contact_uses_one_members_power_and_mass(self):
        result = self.contact()
        self.assertEqual(result.trauma.contact_power, 8.0)
        self.assertEqual(result.trauma.attacker_mass_kg, 10.0)
        self.assertEqual(result.trauma.target_mass_kg, 10.0)
        self.assertEqual(result.trauma.opposing_defense, 3.0)
        self.assertIs(result.injury.severity, InjurySeverity.MAJOR)
        self.assertEqual(result.updated_target.member_injuries[0], ())
        self.assertEqual(result.updated_target.member_injuries[1], (result.injury,))
        self.assertEqual(self.herd.member_injuries, ((), ()))

    def test_selected_member_condition_affects_trauma_and_misses_leave_targets_unchanged(self):
        existing = create_injury_from_trauma("counterattack", 4.0)
        hunters = replace(self.hunters, member_injuries=((existing,), (), (), ()))
        injured = self.contact(hunters)
        healthy = self.contact(hunters, actor_index=1)
        self.assertEqual(injured.trauma.contact_power, 4.0)
        self.assertIs(injured.injury.severity, InjurySeverity.MINOR)
        self.assertEqual(healthy.trauma.contact_power, 8.0)
        missed = self.contact(hit=False)
        self.assertIsNone(missed.trauma)
        self.assertIsNone(missed.injury)
        self.assertIs(missed.updated_target, self.herd)

    def test_counterattack_injures_only_targeted_hunter_and_preserves_existing_injuries(self):
        existing = create_injury_from_trauma("attack", 1.0)
        targets = replace(self.hunters, member_injuries=((), (), (existing,), ()))
        result = resolve_group_contact_injury(
            AttackResult(calculate_attack_scores(self.prey, self.predator), 0.5, 0.1, True),
            self.herd, targets, self.prey, self.predator, self.method, 0, 2,
            source_stage="counterattack",
        )
        self.assertEqual(result.trauma.source_stage, "counterattack")
        self.assertEqual(result.updated_target.member_injuries[2], (existing, result.injury))
        self.assertEqual(result.updated_target.member_injuries[:2], ((), ()))
        self.assertEqual(result.updated_target.member_injuries[3], ())

    def test_rejects_missing_members_or_mismatched_group_context(self):
        for index in (-1, 2):
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.contact(target_index=index)
        with self.assertRaises(TypeError):
            self.contact(actor_index=True)
        invalid = replace(self.hunters, group=replace(self.hunters.group, habitat_id="other"))
        with self.assertRaises(ValueError):
            self.contact(invalid)
