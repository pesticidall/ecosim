import unittest
from random import Random

from simulation.group_hunting import apply_group_hunt, resolve_group_hunt
from simulation.groups import AnimalGroup, GroupParticipants, GroupRole
from simulation.hunting import HuntOutcomeStatus
from simulation.world_state import HabitatState, RegionState


class TestGroupHunting(unittest.TestCase):
    def test_group_hunt_commit_consumes_only_requested_supplement(self):
        result = self.hunt(Random(1))
        meal = apply_group_hunt(
            self.region, result, self.predator, self.prey, requested_biomass_kg=1.0,
        )
        self.assertEqual(meal.feeding.required_amount, 4.0)
        self.assertEqual(meal.feeding.consumed_amount, 1.0)
        self.assertEqual(meal.consumed_per_member_kg, 0.5)
        self.assertEqual(self.habitat.carrion_deposits[0].available_biomass_kg, 9.0)
        self.assertEqual(self.habitat.animal_populations, {"predator": 2, "prey": 0})
        self.assertEqual(len(self.habitat.predation_meals), 1)

    def test_invalid_meal_limit_rejects_hunt_commit_before_world_mutation(self):
        result = self.hunt(Random(1))
        with self.assertRaises(ValueError):
            apply_group_hunt(
                self.region, result, self.predator, self.prey, requested_biomass_kg=float("nan"),
            )
        self.assertEqual(self.habitat.animal_populations, {"predator": 2, "prey": 1})
        self.assertEqual(self.region.animal_populations, {"predator": 2, "prey": 1})
        self.assertEqual(self.habitat.injury_cohorts, {})
        self.assertEqual(self.habitat.group_condition_history, [])
        self.assertEqual(self.habitat.predation_meals, [])
        self.assertEqual(self.habitat.carrion_deposits, [])

    def test_failed_chase_and_missed_attack_stop_group_hunt_without_extra_rolls(self):
        for hunter_mobility, prey_mobility, power, defense, status, rolls in (
            (0.0, 1.0, 8.0, 0.0, HuntOutcomeStatus.ESCAPED_CHASE, 2),
            (8.0, 0.0, 0.0, 1.0, HuntOutcomeStatus.ATTACK_MISSED, 3),
        ):
            with self.subTest(status=status):
                self.predator["statistics"]["mobility"] = hunter_mobility
                self.prey["statistics"]["mobility"] = prey_mobility
                self.predator["statistics"]["power"] = power
                self.prey["statistics"]["defense"] = defense
                random_source = Random(1)
                result = self.hunt(random_source)
                self.assertIs(result.outcome.status, status)
                self.assertIsNone(result.response)
                self.assertIsNone(result.contact_injury)
                self.assertIsNone(result.detention)
                self.assertEqual(result.prey_change.dead_member_indices, ())
                expected = Random(1)
                for _ in range(rolls):
                    expected.random()
                self.assertEqual(random_source.getstate(), expected.getstate())

    def setUp(self):
        self.hunters = GroupParticipants(AnimalGroup("predator", "region", "local", 2, GroupRole.HUNTING), ((), ()))
        self.prey_group = GroupParticipants(AnimalGroup("prey", "region", "local", 1, GroupRole.DEFENSIVE), ((),))
        self.predator = {"id": "predator", "taxon_id": "root", "typical_adult_mass_kg": 10.0,
                         "primary_movement_mode": "terrestrial", "available_movement_modes": ["terrestrial"],
                         "food_requirement_per_animal_per_cycle": 2.0,
                         "statistics": {"power": 8.0, "defense": 0.0, "mobility": 8.0,
                                        "perception": 8.0, "stealth": 5.0, "intelligence": 10.0}}
        self.prey = {"id": "prey", "taxon_id": "root", "typical_adult_mass_kg": 10.0,
                     "primary_movement_mode": "terrestrial", "available_movement_modes": ["terrestrial"],
                     "statistics": {"power": 0.0, "defense": 0.0, "mobility": 0.0,
                                    "perception": 0.0, "stealth": 0.0, "intelligence": 5.0}}
        self.method = {"id": "bite", "trauma_modifier": 1.0, "trait_effect_target": "bite_effectiveness"}
        self.habitat = HabitatState("local", animal_populations={"predator": 2, "prey": 1})
        self.region = RegionState("region", habitats={"local": self.habitat},
                                  animal_populations=dict(self.habitat.animal_populations))

    def hunt(self, random_source, overlap=1.0, counterattack=False):
        traits = [{"id": "retaliation", "action_capabilities": ["counterattack"]}] if counterattack else []
        return resolve_group_hunt(
            self.hunters, self.prey_group, self.predator, self.prey,
            {"conditions": {"openness": 1.0, "vegetation_density": 0.0}}, {}, self.method,
            self.method if counterattack else None,
            iter([{"id": "root", "parent_taxon_id": None}]), iter(traits), (),
            {"escape": float(not counterattack), "counterattack": float(counterattack)},
            random_source, activity_overlap_modifier=overlap,
        )

    def test_complete_group_hunt_commits_one_kill_and_shared_meal(self):
        random_source = Random(1)
        result = self.hunt(random_source)
        self.assertIs(result.outcome.status, HuntOutcomeStatus.SECURED)
        self.assertEqual(result.contact_injury.trauma.contact_power, 8.0)
        self.assertEqual(result.prey_change.dead_member_indices, (0,))
        expected = Random(1)
        for _ in range(5):
            expected.random()
        self.assertEqual(random_source.getstate(), expected.getstate())
        meal = apply_group_hunt(self.region, result, self.predator, self.prey)
        self.assertEqual(meal.consumed_per_member_kg, 2.0)
        self.assertEqual(self.habitat.animal_populations, {"predator": 2, "prey": 0})
        self.assertEqual(self.habitat.carrion_deposits[0].available_biomass_kg, 6.0)
        self.assertEqual(len(self.habitat.predation_meals), 1)

    def test_detection_failure_skips_contact_and_commits_no_death(self):
        random_source = Random(1)
        result = self.hunt(random_source, overlap=0.0)
        self.assertIs(result.outcome.status, HuntOutcomeStatus.NOT_DETECTED)
        self.assertIsNone(result.approach.chase)
        self.assertIsNone(result.contact_injury)
        self.assertIsNone(result.detention)
        self.assertIsNone(apply_group_hunt(self.region, result, self.predator, self.prey))
        self.assertEqual(self.habitat.animal_populations["prey"], 1)
        expected = Random(1)
        expected.random()
        self.assertEqual(random_source.getstate(), expected.getstate())

    def test_injured_escape_persists_without_predation_death(self):
        self.prey["statistics"]["power"] = 10.0
        self.prey["typical_adult_mass_kg"] = 10000.0
        result = self.hunt(Random(1))
        self.assertIs(result.outcome.status, HuntOutcomeStatus.ESCAPED_DETENTION)
        self.assertEqual(result.prey_change.dead_member_indices, ())
        self.assertIsNone(apply_group_hunt(self.region, result, self.predator, self.prey))
        self.assertEqual(self.habitat.animal_populations["prey"], 1)
        self.assertEqual(len(self.habitat.injury_cohorts["prey"]), 1)
        self.assertEqual(self.habitat.predation_meals, [])

    def test_retaliation_injures_selected_hunter_before_group_detention(self):
        self.prey["statistics"]["power"] = 8.0
        self.prey["trait_ids"] = ["retaliation"]
        result = self.hunt(Random(1), counterattack=True)
        self.assertEqual(result.response.selected_action_id, "counterattack")
        self.assertTrue(result.counterattack.hit)
        self.assertEqual(len(result.hunter_change.after.member_injuries[0]), 1)
        self.assertEqual(result.hunter_change.after.member_injuries[1], ())
        self.assertLess(result.detention.scores.predator_injury_modifier, 1.0)
        self.assertEqual(result, self.hunt(Random(1), counterattack=True))
