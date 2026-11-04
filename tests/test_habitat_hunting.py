import unittest
from random import Random

from core.content_registry import ContentRegistry
from simulation.habitat_hunting import apply_habitat_hunt, resolve_habitat_hunt
from simulation.hunting import HuntOutcomeStatus
from simulation.world_state import HabitatState, RegionState


class TestHabitatHunting(unittest.TestCase):
    def test_hunting_only_fills_remaining_resource_food_demand(self) -> None:
        from simulation.feeding import PopulationFeedingResult

        self.predator["food_requirement_per_animal_per_cycle"] = 8.0
        prior = PopulationFeedingResult(8.0, 3.0, 0.375, {"forage": 3.0})
        result = self.hunting_round(Random(1), prior_feeding=prior)
        self.assertEqual(len(result.attempts), 1)
        self.assertEqual(result.meals[0].consumption.consumed_biomass_kg, 5.0)
        self.assertEqual(result.feeding.required_amount, 8.0)
        self.assertEqual(result.feeding.consumed_amount, 8.0)
        self.assertEqual(result.feeding.nutrition_ratio, 1.0)
        self.assertEqual(result.feeding.resource_consumption, {"forage": 3.0, "prey": 5.0})
        self.assertEqual(self.habitat.carrion_deposits[0].available_biomass_kg, 5.0)
        self.assertEqual(prior.resource_consumption, {"forage": 3.0})

    def test_fully_fed_population_skips_hunting_and_preserves_prior_sources(self) -> None:
        from simulation.feeding import PopulationFeedingResult

        self.predator["food_requirement_per_animal_per_cycle"] = 8.0
        prior = PopulationFeedingResult(8.0, 8.0, 1.0, {"forage": 8.0})
        random_source = Random(1)
        before = random_source.getstate()
        result = self.hunting_round(random_source, prior_feeding=prior)
        self.assertEqual(result.attempts, ())
        self.assertEqual(result.feeding, prior)
        self.assertEqual(random_source.getstate(), before)
        self.assertEqual(self.habitat.animal_populations["prey"], 2)

    def test_invalid_prior_feeding_is_rejected_before_hunting(self) -> None:
        from simulation.feeding import PopulationFeedingResult

        self.predator["food_requirement_per_animal_per_cycle"] = 8.0
        for prior in (
            PopulationFeedingResult(16.0, 0.0, 0.0, {}),
            PopulationFeedingResult(8.0, -1.0, 0.0, {}),
            PopulationFeedingResult(8.0, float("nan"), 0.0, {}),
            PopulationFeedingResult(8.0, 3.0, 0.0, {"forage": 2.0}),
        ):
            with self.subTest(prior=prior):
                random_source = Random(1)
                before = random_source.getstate()
                with self.assertRaises(ValueError):
                    self.hunting_round(random_source, prior_feeding=prior)
                self.assertEqual(random_source.getstate(), before)
                self.assertEqual(self.habitat.hunt_history, [])
                self.assertEqual(self.habitat.animal_populations["prey"], 2)

    def test_selected_prey_uses_its_own_counterattack_method(self) -> None:
        from simulation.injuries import InjurySeverity

        self.predator["attack_method_id"] = "bite"
        self.prey["counterattack_method_id"] = "retaliation_method"
        self.prey["trait_ids"] = ["retaliation"]
        self.prey["statistics"]["power"] = 8.0
        self.registry.register({"id": "retaliation_method", "trauma_modifier": 2.0,
                                "trait_effect_target": "grapple_effectiveness"})
        result = resolve_habitat_hunt(
            "hunter", self.habitat, self.registry, {}, None, "bite",
            [{"id": "root", "parent_taxon_id": None}],
            [{"id": "retaliation", "action_capabilities": ["counterattack"]}], (),
            {"escape": 0.0, "counterattack": 1.0}, Random(1),
        )
        self.assertTrue(result.hunt.contact.counterattack.hit)
        self.assertEqual(result.hunt.contact.counterattack.scores.effective_power, 2.0)
        self.assertIs(result.hunt.contact.predator_injuries[0].severity, InjurySeverity.MAJOR)

    def test_hunt_uses_content_methods_without_granting_counterattack_capability(self) -> None:
        self.predator["attack_method_id"] = "bite"
        self.prey["counterattack_method_id"] = "other_method"
        self.registry.register({"id": "other_method", "trauma_modifier": 1.0,
                                "trait_effect_target": "grapple_effectiveness"})
        result = resolve_habitat_hunt(
            "hunter", self.habitat, self.registry, {}, None, None,
            [{"id": "root", "parent_taxon_id": None}], (), (),
            {"escape": 1.0}, Random(1),
        )
        self.assertIs(result.hunt.outcome.status, HuntOutcomeStatus.SECURED)
        self.assertEqual(result.hunt.contact.response.selected_action_id, "escape")
        self.assertIsNone(result.hunt.contact.counterattack)

    def hunting_round(self, random_source, prior_feeding=None):
        from simulation.habitat_hunting import run_habitat_hunting_round

        return run_habitat_hunting_round(
            "hunter", "local", self.region(), self.registry, {}, "bite", None,
            iter([{"id": "root", "parent_taxon_id": None}]), iter(()), iter(()),
            {"escape": 1.0}, random_source,
            prior_feeding=prior_feeding,
        )

    def test_hunting_round_stops_when_population_demand_is_met(self) -> None:
        self.predator["food_requirement_per_animal_per_cycle"] = 2.0
        self.habitat.animal_populations["hunter"] = 3
        random_source = Random(1)
        result = self.hunting_round(random_source)
        self.assertEqual(len(result.attempts), 1)
        self.assertEqual(len(result.meals), 1)
        self.assertEqual(result.feeding.required_amount, 6.0)
        self.assertEqual(result.feeding.consumed_amount, 6.0)
        self.assertEqual(result.feeding.nutrition_ratio, 1.0)
        self.assertEqual(self.habitat.animal_populations["prey"], 1)
        self.assertEqual(self.habitat.carrion_deposits[0].available_biomass_kg, 4.0)
        expected = Random(1)
        for _ in range(6):
            expected.random()
        self.assertEqual(random_source.getstate(), expected.getstate())

    def test_hunting_round_combines_meals_without_recounting_history(self) -> None:
        self.predator["food_requirement_per_animal_per_cycle"] = 8.0
        self.habitat.animal_populations["hunter"] = 2
        result = self.hunting_round(Random(1))
        self.assertEqual(len(result.attempts), 2)
        self.assertEqual(result.feeding.consumed_amount, 16.0)
        self.assertEqual(result.feeding.resource_consumption, {"prey": 16.0})
        self.assertEqual(self.habitat.animal_populations["prey"], 0)
        self.assertEqual(self.habitat.carrion_deposits[0].available_biomass_kg, 4.0)
        later = self.hunting_round(Random(1))
        self.assertEqual(later.attempts, ())
        self.assertEqual(later.feeding.consumed_amount, 0.0)
        self.assertEqual(later.feeding.nutrition_ratio, 0.0)

    def test_hunting_round_is_bounded_when_all_hunts_fail(self) -> None:
        self.predator["food_requirement_per_animal_per_cycle"] = 2.0
        self.predator["activity_pattern"] = "diurnal"
        self.prey["activity_pattern"] = "nocturnal"
        self.habitat.animal_populations["hunter"] = 3
        result = self.hunting_round(Random(1))
        self.assertEqual(len(result.attempts), 3)
        self.assertEqual(result.meals, ())
        self.assertEqual(result.feeding.nutrition_ratio, 0.0)
        self.assertEqual(self.habitat.animal_populations["prey"], 2)

    def test_empty_or_no_demand_round_does_not_consume_randomness(self) -> None:
        for population, requirement in ((0, 2.0), (1, 0.0)):
            with self.subTest(population=population, requirement=requirement):
                self.predator["food_requirement_per_animal_per_cycle"] = requirement
                self.habitat.animal_populations["hunter"] = population
                random_source = Random(1)
                state = random_source.getstate()
                result = self.hunting_round(random_source)
                self.assertEqual(result.attempts, ())
                self.assertEqual(result.feeding.nutrition_ratio, 1.0)
                self.assertEqual(random_source.getstate(), state)

    def test_escaped_prey_injuries_persist_into_later_hunts(self) -> None:
        self.prey["statistics"]["power"] = 100.0
        self.habitat.animal_populations["prey"] = 1
        region = self.region()
        first = self.attempt(Random(1))
        self.assertIs(first.hunt.outcome.status, HuntOutcomeStatus.ESCAPED_DETENTION)
        apply_habitat_hunt(region, first, self.registry, 3.0)
        cohorts = self.habitat.injury_cohorts["prey"]
        self.assertEqual(len(cohorts), 1)
        self.assertEqual(cohorts[0].count, 1)
        self.assertEqual(cohorts[0].injuries, first.hunt.contact.prey_injuries)
        second = self.attempt(Random(1))
        self.assertEqual(second.prey_starting_injuries, cohorts[0].injuries)
        self.assertEqual(len(second.hunt.contact.prey_injuries), 2)
        self.assertEqual(self.habitat.animal_populations["prey"], 1)

    def test_injured_hunter_uses_persistent_condition_for_attack(self) -> None:
        from simulation.condition_cohorts import InjuryCohort
        from simulation.injuries import create_injury_from_trauma

        injury = create_injury_from_trauma("counterattack", 4.0)
        self.habitat.injury_cohorts["hunter"] = (InjuryCohort((injury,), 1),)
        attempt = self.attempt(Random(1))
        self.assertEqual(attempt.predator_starting_injuries, (injury,))
        self.assertEqual(attempt.hunt.approach.attack.scores.effective_power, 4.0)
        apply_habitat_hunt(self.region(), attempt, self.registry, 3.0)
        self.assertEqual(self.habitat.injury_cohorts["hunter"], (InjuryCohort((injury,), 1),))
        self.assertEqual(self.habitat.injury_cohorts["prey"], ())

    def test_stale_condition_rejects_commit_before_population_changes(self) -> None:
        from simulation.condition_cohorts import InjuryCohort
        from simulation.injuries import create_injury_from_trauma

        attempt = self.attempt(Random(1))
        injury = create_injury_from_trauma("attack", 1.0)
        self.habitat.injury_cohorts["hunter"] = (InjuryCohort((injury,), 1),)
        region = self.region()
        with self.assertRaisesRegex(ValueError, "No healthy animal"):
            apply_habitat_hunt(region, attempt, self.registry, 3.0)
        self.assertEqual(self.habitat.animal_populations["prey"], 2)
        self.assertEqual(self.habitat.hunt_history, [])
        self.assertEqual(self.habitat.predation_meals, [])

    def region(self):
        return RegionState("region", habitats={"local": self.habitat},
                           animal_populations=dict(self.habitat.animal_populations))

    def test_commits_complete_hunt_meal_and_history_once(self) -> None:
        attempt = self.attempt(Random(1))
        region = self.region()
        meal = apply_habitat_hunt(region, attempt, self.registry, 3.0)
        self.assertEqual(meal.consumption.consumed_biomass_kg, 3.0)
        self.assertEqual(self.habitat.animal_populations["prey"], 1)
        self.assertEqual(region.animal_populations["prey"], 1)
        self.assertEqual(self.habitat.carrion_deposits[0].available_biomass_kg, 7.0)
        self.assertIsNone(self.habitat.carrion_deposits[0].first_access_consumer_id)
        self.assertEqual(self.habitat.predation_meals, [meal])
        self.assertEqual(self.habitat.hunt_history, [attempt])
        with self.assertRaisesRegex(ValueError, "already been applied"):
            apply_habitat_hunt(region, attempt, self.registry, 3.0)
        self.assertEqual(self.habitat.animal_populations["prey"], 1)
        self.assertEqual(len(self.habitat.predation_meals), 1)

    def test_failed_hunt_records_history_without_death_or_meal(self) -> None:
        self.predator["activity_pattern"] = "diurnal"
        self.prey["activity_pattern"] = "nocturnal"
        attempt = self.attempt(Random(1))
        region = self.region()
        self.assertIsNone(apply_habitat_hunt(region, attempt, self.registry, 3.0))
        self.assertEqual(self.habitat.hunt_history, [attempt])
        self.assertEqual(self.habitat.animal_populations["prey"], 2)
        self.assertEqual(region.animal_populations["prey"], 2)
        self.assertEqual(self.habitat.predation_meals, [])
        self.assertEqual(self.habitat.carrion_deposits, [])

    def test_depleted_prey_rejects_commit_without_partial_history(self) -> None:
        attempt = self.attempt(Random(1))
        self.habitat.animal_populations["prey"] = 0
        region = self.region()
        with self.assertRaisesRegex(ValueError, "available prey"):
            apply_habitat_hunt(region, attempt, self.registry, 3.0)
        self.assertEqual(self.habitat.hunt_history, [])
        self.assertEqual(self.habitat.predation_meals, [])
        self.assertEqual(self.habitat.carrion_deposits, [])
        self.assertEqual(region.animal_populations["prey"], 0)

    def test_invalid_meal_request_leaves_attempt_uncommitted(self) -> None:
        attempt = self.attempt(Random(1))
        region = self.region()
        for request, error in ((True, TypeError), (-1.0, ValueError), (float("nan"), ValueError)):
            with self.subTest(request=request):
                with self.assertRaises(error):
                    apply_habitat_hunt(region, attempt, self.registry, request)
                self.assertEqual(self.habitat.hunt_history, [])
                self.assertEqual(self.habitat.animal_populations["prey"], 2)

    def setUp(self) -> None:
        self.registry = ContentRegistry()
        self.predator = {
            "id": "hunter", "taxon_id": "root", "typical_adult_mass_kg": 10.0,
            "primary_movement_mode": "terrestrial", "available_movement_modes": ["terrestrial"],
            "statistics": {"power": 8.0, "defense": 0.0, "perception": 8.0, "mobility": 8.0},
            "prey_diet": [{"animal_id": "prey", "preference": 1.0}],
        }
        self.prey = {
            "id": "prey", "taxon_id": "root", "typical_adult_mass_kg": 10.0,
            "primary_movement_mode": "terrestrial", "available_movement_modes": ["terrestrial"],
            "statistics": {"power": 0.0, "defense": 0.0, "stealth": 0.0, "mobility": 0.0},
        }
        self.registry.register_all([
            self.predator, self.prey,
            {"id": "local", "conditions": {"openness": 1.0, "vegetation_density": 0.0}},
            {"id": "bite", "trauma_modifier": 1.0, "trait_effect_target": "bite_effectiveness"},
        ])
        self.habitat = HabitatState("local", animal_populations={"hunter": 1, "prey": 2})

    def attempt(self, random_source):
        return resolve_habitat_hunt(
            "hunter", self.habitat, self.registry, {}, "bite", None,
            iter([{"id": "root", "parent_taxon_id": None}]), iter(()), (),
            {"escape": 1.0}, random_source,
        )

    def test_local_selection_resolves_complete_hunt_without_mutating_state(self) -> None:
        random_source = Random(1)
        result = self.attempt(random_source)
        expected = Random(1)
        for _ in range(6):
            expected.random()
        self.assertEqual(result.prey_selection.selected_animal_id, "prey")
        self.assertEqual(result.habitat_id, "local")
        self.assertIs(result.hunt.outcome.status, HuntOutcomeStatus.SECURED)
        self.assertEqual(len(result.hunt.contact.prey_injuries), 1)
        self.assertEqual(random_source.getstate(), expected.getstate())
        self.assertEqual(self.habitat.animal_populations, {"hunter": 1, "prey": 2})
        self.assertEqual(self.habitat.predation_meals, [])
        self.assertEqual(self.attempt(Random(1)), result)

    def test_nonoverlapping_activity_prevents_detection(self) -> None:
        self.predator["activity_pattern"] = "diurnal"
        self.prey["activity_pattern"] = "nocturnal"
        result = self.attempt(Random(1))
        self.assertIs(result.hunt.outcome.status, HuntOutcomeStatus.NOT_DETECTED)
        self.assertEqual(result.hunt.approach.detection.scores.activity_overlap_modifier, 0.0)
        self.assertIsNone(result.hunt.approach.chase)

    def test_no_local_prey_skips_attempt_without_consuming_randomness(self) -> None:
        self.habitat.animal_populations["prey"] = 0
        random_source = Random(1)
        before = random_source.getstate()
        self.assertIsNone(self.attempt(random_source))
        self.assertEqual(random_source.getstate(), before)
