import unittest
from dataclasses import replace
from random import Random

from simulation.condition_cohorts import InjuryCohort
from simulation.group_conditions import GroupConditionChange, apply_group_condition_changes
from simulation.group_trauma import resolve_group_contact_injury
from simulation.groups import AnimalGroup, GroupParticipants, GroupRole, select_group_participants
from simulation.hunting import AttackResult, calculate_group_attack_scores
from simulation.injuries import create_injury_from_trauma
from simulation.world_state import HabitatState, RegionState


class TestGroupConditions(unittest.TestCase):
    def test_explicit_casualty_removes_only_target_and_updates_regional_total(self):
        self.habitat.injury_cohorts["prey"] = (InjuryCohort((self.minor,), 1),)
        self.region.habitats["other"] = HabitatState("other", animal_populations={"prey": 4})
        self.region.animal_populations["prey"] = 7
        before = GroupParticipants(self.group, ((self.minor,), ()))
        after = GroupParticipants(self.group, ((self.minor, self.major), (self.major,)))
        change = GroupConditionChange(before, after, dead_member_indices=(0,))
        apply_group_condition_changes(self.region, (change,))
        self.assertEqual(self.habitat.animal_populations["prey"], 2)
        self.assertEqual(self.region.animal_populations["prey"], 6)
        self.assertEqual(self.region.habitats["other"].animal_populations["prey"], 4)
        self.assertEqual(self.habitat.injury_cohorts["prey"], (InjuryCohort((self.major,), 1),))
        self.assertEqual(before.member_injuries, ((self.minor,), ()))
        with self.assertRaisesRegex(ValueError, "already been applied"):
            apply_group_condition_changes(self.region, (change,))
        self.assertEqual(self.region.animal_populations["prey"], 6)

    def test_all_group_casualties_leave_no_injured_members(self):
        self.habitat.animal_populations["prey"] = 2
        self.habitat.injury_cohorts["prey"] = (InjuryCohort((self.minor,), 2),)
        before = GroupParticipants(self.group, ((self.minor,), (self.minor,)))
        change = GroupConditionChange(before, before, dead_member_indices=(0, 1))
        apply_group_condition_changes(self.region, (change,))
        self.assertEqual(self.habitat.animal_populations["prey"], 0)
        self.assertEqual(self.region.animal_populations["prey"], 0)
        self.assertEqual(self.habitat.injury_cohorts["prey"], ())

    def test_critical_injury_does_not_implicitly_create_casualty(self):
        critical = create_injury_from_trauma("attack", 8.0)
        before = GroupParticipants(self.group, ((), ()))
        after = GroupParticipants(self.group, ((critical,), ()))
        apply_group_condition_changes(self.region, (GroupConditionChange(before, after),))
        self.assertEqual(self.habitat.animal_populations["prey"], 3)
        self.assertEqual(self.habitat.injury_cohorts["prey"], (InjuryCohort((critical,), 1),))

    def test_invalid_casualty_indices_are_rejected_without_state_changes(self):
        before = GroupParticipants(self.group, ((), ()))
        for indices, error in (((True,), TypeError), ((1.5,), TypeError),
                               ((-1,), ValueError), ((2,), ValueError), ((0, 0), ValueError)):
            with self.subTest(indices=indices), self.assertRaises(error):
                GroupConditionChange(before, before, dead_member_indices=indices)
        self.assertEqual(self.habitat.animal_populations["prey"], 3)
        self.assertEqual(self.habitat.group_condition_history, [])

    def setUp(self):
        self.minor = create_injury_from_trauma("attack", 1.0)
        self.major = create_injury_from_trauma("counterattack", 4.0)
        self.group = AnimalGroup("prey", "region", "local", 2, GroupRole.DEFENSIVE)
        self.habitat = HabitatState("local", animal_populations={"prey": 3})
        self.region = RegionState("region", habitats={"local": self.habitat}, animal_populations={"prey": 3})

    def test_commits_targeted_contact_and_reuses_persistent_condition(self):
        hunters = GroupParticipants(AnimalGroup("predator", "region", "local", 2, GroupRole.HUNTING), ((), ()))
        targets = GroupParticipants(self.group, ((), ()))
        predator = {"id": "predator", "typical_adult_mass_kg": 10.0,
                    "statistics": {"power": 8.0, "intelligence": 10.0}}
        prey = {"id": "prey", "typical_adult_mass_kg": 10.0,
                "statistics": {"power": 3.0, "defense": 3.0, "intelligence": 5.0}}
        attack = AttackResult(calculate_group_attack_scores(hunters.group, predator, prey), 0.5, 0.1, True)
        contact = resolve_group_contact_injury(attack, hunters, targets, predator, prey,
            {"id": "bite", "trauma_modifier": 1.0, "trait_effect_target": "bite_effectiveness"}, 0, 1)
        change = GroupConditionChange(targets, contact.updated_target)
        apply_group_condition_changes(self.region, (change,))
        self.assertEqual(self.habitat.injury_cohorts["prey"], (InjuryCohort((contact.injury,), 1),))
        self.assertEqual(self.habitat.animal_populations["prey"], 3)
        all_members = select_group_participants(self.region, replace(self.group, member_count=3), Random(1))
        self.assertEqual(all_members.member_injuries.count((contact.injury,)), 1)
        with self.assertRaisesRegex(ValueError, "already been applied"):
            apply_group_condition_changes(self.region, (change,))

    def test_preserves_unselected_members_and_cumulative_injuries(self):
        self.habitat.injury_cohorts["prey"] = (InjuryCohort((self.minor,), 2),)
        before = GroupParticipants(self.group, ((self.minor,), ()))
        after = GroupParticipants(self.group, ((self.minor, self.major), (self.major,)))
        apply_group_condition_changes(self.region, (GroupConditionChange(before, after),))
        counts = {cohort.injuries: cohort.count for cohort in self.habitat.injury_cohorts["prey"]}
        self.assertEqual(counts, {(self.minor,): 1, (self.minor, self.major): 1, (self.major,): 1})
        self.assertEqual(self.region.animal_populations["prey"], 3)

    def test_batch_cannot_reuse_newly_injured_member_as_starting_participant(self):
        solo = replace(self.group, member_count=1)
        healthy = GroupParticipants(solo, ((),))
        injured = GroupParticipants(solo, ((self.minor,),))
        more_injured = GroupParticipants(solo, ((self.minor, self.major),))
        changes = (GroupConditionChange(healthy, injured), GroupConditionChange(injured, more_injured))
        with self.assertRaisesRegex(ValueError, "starting injury cohort"):
            apply_group_condition_changes(self.region, changes)
        self.assertEqual(self.habitat.injury_cohorts, {})
        self.assertEqual(self.habitat.group_condition_history, [])
        self.assertEqual(self.habitat.animal_populations["prey"], 3)

    def test_rejects_stale_counts_and_wrong_membership_atomically(self):
        before = GroupParticipants(self.group, ((), ()))
        after = GroupParticipants(self.group, ((self.major,), ()))
        change = GroupConditionChange(before, after)
        self.habitat.animal_populations["prey"] = 1
        with self.assertRaises(ValueError):
            apply_group_condition_changes(self.region, (change,))
        self.assertEqual(self.habitat.injury_cohorts, {})
        self.assertEqual(self.habitat.group_condition_history, [])
        with self.assertRaises(ValueError):
            GroupConditionChange(before, replace(after, group=replace(self.group, habitat_id="other")))
