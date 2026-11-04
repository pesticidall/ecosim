import unittest
from dataclasses import replace

from simulation.carrion import create_carrion_from_death
from simulation.deaths import DeathCause, DeathRecord
from simulation.group_feeding import feed_hunting_group
from simulation.groups import AnimalGroup, GroupRole
from simulation.predation import PredationRemains, apply_predation_meal, feed_secured_prey
from simulation.world_state import HabitatState, RegionState


class TestGroupFeeding(unittest.TestCase):
    def test_shared_meal_caps_intake_at_remaining_deficit_and_group_requirement(self):
        group = AnimalGroup("predator", "region", "local", 2, GroupRole.HUNTING)
        for requested, consumed in ((0.0, 0.0), (3.0, 3.0), (20.0, 8.0)):
            with self.subTest(requested=requested):
                result = feed_hunting_group(
                    group, self.definition, self.remains, requested_biomass_kg=requested,
                )
                self.assertEqual(result.feeding.required_amount, 8.0)
                self.assertEqual(result.feeding.consumed_amount, consumed)
                self.assertEqual(result.feeding.nutrition_ratio, consumed / 8.0)
                self.assertEqual(result.consumed_per_member_kg, consumed / 2.0)
                self.assertEqual(result.meal.leftover_carrion.available_biomass_kg, 10.0 - consumed)
                self.assertIsNone(result.meal.leftover_carrion.first_access_consumer_id)

    def test_rejects_invalid_group_meal_limits(self):
        group = AnimalGroup("predator", "region", "local", 2, GroupRole.HUNTING)
        for requested, error in ((True, TypeError), ("3", TypeError), (-1, ValueError),
                                 (float("inf"), ValueError), (float("nan"), ValueError)):
            with self.subTest(requested=requested), self.assertRaises(error):
                feed_hunting_group(group, self.definition, self.remains, requested_biomass_kg=requested)
        self.assertEqual(self.remains.carrion.available_biomass_kg, 10.0)

    def setUp(self):
        self.definition = {"id": "predator", "food_requirement_per_animal_per_cycle": 4.0}
        death = DeathRecord("prey", DeathCause.PREDATION, 1, 10.0)
        self.remains = PredationRemains(death, create_carrion_from_death(death, "local", "predator"))

    def test_shares_actual_biomass_across_all_members_and_retains_shortfall(self):
        for members, consumed, share, nutrition, leftover in (
            (1, 4.0, 4.0, 1.0, 6.0),
            (2, 8.0, 4.0, 1.0, 2.0),
            (4, 10.0, 2.5, 0.625, 0.0),
        ):
            with self.subTest(members=members):
                group = AnimalGroup("predator", "region", "local", members, GroupRole.HUNTING)
                result = feed_hunting_group(group, self.definition, self.remains)
                self.assertEqual(result.feeding.required_amount, members * 4.0)
                self.assertEqual(result.feeding.consumed_amount, consumed)
                self.assertEqual(result.consumed_per_member_kg, share)
                self.assertEqual(share * members, consumed)
                self.assertEqual(result.feeding.nutrition_ratio, nutrition)
                self.assertEqual(result.meal.leftover_carrion.available_biomass_kg, leftover)
                self.assertEqual(consumed + leftover, 10.0)
                self.assertIsNone(result.meal.leftover_carrion.first_access_consumer_id)
                self.assertEqual(self.remains.carrion.available_biomass_kg, 10.0)

    def test_shared_meal_commits_one_prey_death_not_one_per_member(self):
        group = AnimalGroup("predator", "region", "local", 4, GroupRole.HUNTING)
        result = feed_hunting_group(group, self.definition, self.remains)
        habitat = HabitatState("local", animal_populations={"predator": 4, "prey": 5})
        region = RegionState("region", habitats={"local": habitat},
                             animal_populations=dict(habitat.animal_populations))
        apply_predation_meal(region, result.meal)
        self.assertEqual(habitat.animal_populations, {"predator": 4, "prey": 4})
        self.assertEqual(region.animal_populations["prey"], 4)
        self.assertEqual(len(habitat.predation_meals), 1)

    def test_solo_group_meal_matches_existing_secured_prey_feeding(self):
        group = AnimalGroup("predator", "region", "local", 1, GroupRole.HUNTING)
        result = feed_hunting_group(group, self.definition, self.remains)
        self.assertEqual(result.meal, feed_secured_prey(self.remains, 4.0))

    def test_rejects_wrong_role_habitat_species_or_first_access(self):
        group = AnimalGroup("predator", "region", "local", 2, GroupRole.HUNTING)
        for invalid_group in (replace(group, role=GroupRole.DEFENSIVE),
                              replace(group, habitat_id="elsewhere"),
                              replace(group, animal_id="other_predator")):
            with self.subTest(group=invalid_group), self.assertRaises(ValueError):
                feed_hunting_group(invalid_group, self.definition, self.remains)
        with self.assertRaises(ValueError):
            feed_hunting_group(group, {**self.definition, "id": "wrong_species"}, self.remains)
        released = replace(self.remains, carrion=replace(self.remains.carrion, first_access_consumer_id=None))
        with self.assertRaises(ValueError):
            feed_hunting_group(group, self.definition, released)
