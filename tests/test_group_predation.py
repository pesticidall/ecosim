import unittest
from dataclasses import replace

from simulation.condition_cohorts import InjuryCohort
from simulation.deaths import DeathCause
from simulation.group_conditions import GroupConditionChange
from simulation.group_predation import apply_group_predation
from simulation.groups import AnimalGroup, GroupParticipants, GroupRole
from simulation.injuries import create_injury_from_trauma
from simulation.predation import apply_predation_meal
from simulation.world_state import HabitatState, RegionState


class TestGroupPredation(unittest.TestCase):
    def setUp(self):
        self.minor = create_injury_from_trauma("attack", 1.0)
        self.major = create_injury_from_trauma("counterattack", 4.0)
        hunters = AnimalGroup("predator", "region", "local", 3, GroupRole.HUNTING)
        herd = AnimalGroup("prey", "region", "local", 2, GroupRole.DEFENSIVE)
        self.hunter_change = GroupConditionChange(
            GroupParticipants(hunters, ((), (), ())),
            GroupParticipants(hunters, ((), (self.major,), ())),
        )
        self.prey_change = GroupConditionChange(
            GroupParticipants(herd, ((), ())),
            GroupParticipants(herd, ((self.major,), (self.minor,))),
            dead_member_indices=(0,),
        )
        self.predator = {"id": "predator", "food_requirement_per_animal_per_cycle": 2.0}
        self.prey = {"id": "prey", "typical_adult_mass_kg": 10.0}
        self.habitat = HabitatState("local", animal_populations={"predator": 3, "prey": 3})
        self.region = RegionState("region", habitats={
            "local": self.habitat,
            "other": HabitatState("other", animal_populations={"prey": 5}),
        }, animal_populations={"predator": 3, "prey": 8})

    def commit(self):
        return apply_group_predation(self.region, self.hunter_change, self.prey_change, self.predator, self.prey)

    def test_group_kill_commits_one_death_shared_food_and_survivor_injuries(self):
        result = self.commit()
        self.assertEqual(self.habitat.animal_populations, {"predator": 3, "prey": 2})
        self.assertEqual(self.region.animal_populations["prey"], 7)
        self.assertEqual(self.region.habitats["other"].animal_populations["prey"], 5)
        self.assertIs(result.meal.death.cause, DeathCause.PREDATION)
        self.assertEqual(result.meal.death.count, 1)
        self.assertEqual(result.feeding.consumed_amount, 6.0)
        self.assertEqual(result.consumed_per_member_kg, 2.0)
        self.assertEqual(self.habitat.carrion_deposits[0].available_biomass_kg, 4.0)
        self.assertEqual(self.habitat.injury_cohorts["predator"], (InjuryCohort((self.major,), 1),))
        self.assertEqual(self.habitat.injury_cohorts["prey"], (InjuryCohort((self.minor,), 1),))
        self.assertEqual(self.habitat.predation_meals, [result.meal])
        self.assertEqual(len(self.habitat.group_condition_history), 2)
        with self.assertRaisesRegex(ValueError, "already been applied"):
            self.commit()
        with self.assertRaisesRegex(ValueError, "already been applied"):
            apply_predation_meal(self.region, result.meal)
        self.assertEqual(self.region.animal_populations["prey"], 7)

    def test_group_meal_shortfall_preserves_single_carcass_mass(self):
        self.predator["food_requirement_per_animal_per_cycle"] = 4.0
        result = self.commit()
        self.assertEqual(result.feeding.required_amount, 12.0)
        self.assertEqual(result.feeding.consumed_amount, 10.0)
        self.assertAlmostEqual(result.feeding.nutrition_ratio, 10.0 / 12.0)
        self.assertAlmostEqual(result.consumed_per_member_kg * 3, 10.0)
        self.assertEqual(self.habitat.carrion_deposits, [])

    def test_stale_participants_reject_entire_group_predation_commit(self):
        self.habitat.animal_populations["predator"] = 2
        with self.assertRaises(ValueError):
            self.commit()
        self.assertEqual(self.habitat.animal_populations["prey"], 3)
        self.assertEqual(self.habitat.injury_cohorts, {})
        self.assertEqual(self.habitat.group_condition_history, [])
        self.assertEqual(self.habitat.predation_meals, [])
        self.assertEqual(self.habitat.carrion_deposits, [])

    def test_rejects_implicit_or_multiple_prey_deaths_and_invalid_mass(self):
        original = self.prey_change
        for casualties in ((), (0, 1)):
            self.prey_change = replace(original, dead_member_indices=casualties)
            with self.subTest(casualties=casualties), self.assertRaisesRegex(ValueError, "exactly one"):
                self.commit()
        self.prey_change = original
        for mass in (0.0, float("inf"), float("nan")):
            self.prey["typical_adult_mass_kg"] = mass
            with self.subTest(mass=mass), self.assertRaises(ValueError):
                self.commit()
        self.assertEqual(self.habitat.animal_populations["prey"], 3)
        self.assertEqual(self.habitat.group_condition_history, [])
