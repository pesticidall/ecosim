import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from core.content_registry import ContentRegistry
from core.content_catalog import build_content_registry
from core.content_validator import validate_entity_definition
from simulation.calendar import CalendarState
from simulation.carrion import CarrionDeposit
from simulation.daily_cycle import run_day
from simulation.interventions import remove_population, introduce_population, preview_population_removal
from simulation.nutrition import NutritionalState, reconcile_nutrition, update_condition
from simulation.world_state import WorldState, RegionState, HabitatState


CONFIG = {"reserve_days": 3.0, "starvation_grace_days": 7.0, "recovery_per_fed_day": 1.0}
ROOT = Path(__file__).resolve().parents[1]


class TestNutrition(unittest.TestCase):
    def setup_world(self, animals=1, food=20.0, species=("animal",), carrion=False):
        registry = ContentRegistry()
        registry.register_all([
            {"id": "region", "entity_type": "region", "name": "Region"},
            {"id": "local", "entity_type": "habitat", "name": "Local"},
            {"id": "food", "entity_type": "resource", "name": "Food", "unit": "kg"},
            {"id": "prey", "entity_type": "animal", "name": "Prey"},
        ])
        for animal in species:
            definition = {"id": animal, "entity_type": "animal", "name": animal,
                          "food_requirement_per_animal_per_cycle": 31.0,
                          "birth_rate_per_animal_per_cycle": 0.0, "typical_adult_mass_kg": 10,
                          "preferred_habitat_ids": ["local"], "nutrition": dict(CONFIG),
                          "diet": [] if carrion else [{"resource_id": "food", "preference": 1}]}
            if carrion:
                definition["scavenging_diet"] = [{"animal_id": "prey", "preference": 1}]
            registry.register(definition)
        habitat = HabitatState("local", animal_populations={a: animals for a in species}, resource_quantities={"food": food})
        region = RegionState("region", habitats={"local": habitat}, animal_populations=dict(habitat.animal_populations),
                             resource_quantities={"food": food})
        return WorldState(1, regions={"region": region}), registry, habitat

    def test_intermittent_shortage_recovers_without_conflating_health_or_rounding(self):
        state = NutritionalState(1)
        for _ in range(7):
            state, pressure = update_condition(state, 0, CONFIG)
            self.assertEqual(pressure, 0)
        state, pressure = update_condition(state, 0, CONFIG)
        self.assertGreater(pressure, 0)
        for _ in range(8):
            state, pressure = update_condition(state, 1, CONFIG)
            self.assertEqual(pressure, 0)
        self.assertEqual(state.deficit_days, 0)
        self.assertEqual(state.reserve_kg, 0)

    def test_food_is_debited_once_banked_with_a_cap_and_drawn_on_later_dates(self):
        world, registry, habitat = self.setup_world()
        first = run_day(world, registry)
        state = habitat.nutritional_states["animal"]
        self.assertAlmostEqual(state.reserve_kg, 3.1)
        deposit = first.region_results["region"].food_web.reserve_deposits["local"]["animal"][0]
        self.assertAlmostEqual(deposit.consumed_amount, 3.1)
        self.assertAlmostEqual(20, habitat.resource_quantities["food"] + state.reserve_kg + 1)
        # Remove only the remaining habitat supply to isolate stored food.
        habitat.resource_quantities["food"] = 0
        world.regions["region"].resource_quantities["food"] = 0
        for expected in (2.1, 1.1, 0.1):
            day = run_day(world, registry)
            self.assertAlmostEqual(habitat.nutritional_states["animal"].reserve_kg, expected)
            feeding = day.region_results["region"].food_web.regional_feeding["animal"]
            self.assertAlmostEqual(feeding.resource_consumption["stored_food"], 1)
            self.assertEqual(feeding.nutrition_ratio, 1)
        fourth = run_day(world, registry)
        self.assertAlmostEqual(fourth.region_results["region"].food_web.regional_feeding["animal"].nutrition_ratio, 0.1)
        self.assertEqual(habitat.nutritional_states["animal"].reserve_kg, 0)
        self.assertGreater(habitat.nutritional_states["animal"].deficit_days, 0)

    def test_daily_needs_precede_reserve_competition_and_habitat_stores_reconcile(self):
        world, registry, habitat = self.setup_world(food=5, species=("one", "two"))
        run_day(world, registry)
        self.assertAlmostEqual(habitat.nutritional_states["one"].reserve_kg, 1.5)
        self.assertAlmostEqual(habitat.nutritional_states["two"].reserve_kg, 1.5)
        self.assertEqual(habitat.resource_quantities["food"], 0)
        self.assertEqual(world.regions["region"].resource_quantities["food"], 0)
        short, content, target = self.setup_world(food=1, species=("one", "two"))
        run_day(short, content)
        self.assertTrue(all(s.reserve_kg == 0 for s in target.nutritional_states.values()))

    def test_remote_food_cannot_fill_local_reserves_and_invalid_capacity_rolls_back(self):
        world, registry, habitat = self.setup_world(food=0)
        remote = HabitatState("other", resource_quantities={"food": 100})
        world.regions["region"].habitats["other"] = remote
        world.regions["region"].resource_quantities["food"] = 100
        run_day(world, registry)
        self.assertEqual(habitat.nutritional_states["animal"].reserve_kg, 0)
        self.assertEqual(remote.resource_quantities["food"], 100)
        habitat.nutritional_states["animal"] = NutritionalState(1, 100, 0)
        before = deepcopy(world)
        with self.assertRaisesRegex(ValueError, "capacity"):
            run_day(world, registry)
        self.assertEqual(world, before)

    def test_reserve_carrion_respects_first_access_and_does_not_create_biomass(self):
        for owner in (None, "another"):
            world, registry, habitat = self.setup_world(food=0, carrion=True)
            habitat.carrion_deposits = [CarrionDeposit("prey", "local", 10, 10, owner)]
            day = run_day(world, registry)
            result = day.region_results["region"]
            state = habitat.nutritional_states["animal"]
            if owner is None:
                self.assertAlmostEqual(state.reserve_kg, 3.1)
                consumed = result.food_web.regional_feeding["animal"].consumed_amount
                decayed = sum(d.decayed_biomass_kg for d in result.carrion_decay["local"])
                self.assertAlmostEqual(10, consumed + state.reserve_kg + decayed + sum(d.available_biomass_kg for d in habitat.carrion_deposits))
            else:
                self.assertEqual(state.reserve_kg, 0)
                self.assertEqual(habitat.carrion_deposits[0].first_access_consumer_id, owner)

    def test_removal_scales_reserves_and_introduction_adds_no_food(self):
        world, registry, habitat = self.setup_world(animals=4)
        habitat.nutritional_states["animal"] = NutritionalState(4, 8, 4)
        before = deepcopy(world)
        quote = preview_population_removal(world, registry, "region", "local", "animal", 2)
        self.assertEqual(world, before)
        self.assertEqual(quote.nutrition_after, NutritionalState(2, 4, 4))
        remove_population(world, registry, "region", "local", "animal", 2)
        introduce_population(world, registry, "region", "local", "animal", 2)
        self.assertEqual(habitat.nutritional_states["animal"], NutritionalState(4, 4, 2))
        self.assertEqual(reconcile_nutrition(NutritionalState(1, 3, 4), 0), NutritionalState(0))

    def test_births_dilute_stress_and_do_not_gift_food(self):
        world, registry, habitat = self.setup_world(food=100)
        registry.get("animal")["birth_rate_per_animal_per_cycle"] = 31
        habitat.nutritional_states["animal"] = NutritionalState(1, 0, 3)
        run_day(world, registry)
        self.assertEqual(habitat.animal_populations["animal"], 2)
        self.assertAlmostEqual(habitat.nutritional_states["animal"].reserve_kg, 3.1)
        self.assertAlmostEqual(habitat.nutritional_states["animal"].deficit_days, 1)

    def test_famine_still_causes_extinction_and_clears_nutrition(self):
        world, registry, habitat = self.setup_world(food=0)
        from simulation.monthly_cycle import acknowledge_month_review
        for _ in range(90):
            if world.pending_month_review:
                acknowledge_month_review(world)
            run_day(world, registry)
        self.assertEqual(habitat.animal_populations["animal"], 0)
        self.assertNotIn("animal", habitat.nutritional_states)

    def test_failed_month_completion_and_resume_preserve_nutritional_state(self):
        world, registry, habitat = self.setup_world(food=1000)
        for _ in range(30):
            run_day(world, registry)
        before, rng = deepcopy(world), world.random_generator.getstate()
        with patch("simulation.daily_cycle.summarize_month", side_effect=ValueError("failed report")):
            with self.assertRaises(ValueError):
                run_day(world, registry)
        self.assertEqual(world, before)
        self.assertEqual(world.random_generator.getstate(), rng)
        resumed = deepcopy(world)
        self.assertEqual(run_day(world, registry), run_day(resumed, registry))
        self.assertEqual(world, resumed)

    def test_monthly_physical_consumption_includes_bank_deposits_without_inflating_nutrition(self):
        from simulation.monthly_cycle import run_month
        world, registry, habitat = self.setup_world(food=1000)
        summary = run_month(world, registry).region_results["region"]
        self.assertAlmostEqual(summary.feeding_results["animal"].consumed_amount, 31)
        self.assertAlmostEqual(summary.resource_consumption["food"], 34.1)
        self.assertAlmostEqual(habitat.nutritional_states["animal"].reserve_kg, 3.1)
        self.assertAlmostEqual(1000, summary.ending_state.resource_quantities["food"]
                               + summary.feeding_results["animal"].consumed_amount
                               + habitat.nutritional_states["animal"].reserve_kg)

    def test_invalid_content_and_state_are_rejected(self):
        definition = build_content_registry(ROOT / "content").get("caracal")
        for value in (-1, 0, True, float("nan"), float("inf")):
            candidate = deepcopy(definition)
            candidate["nutrition"]["reserve_days"] = value
            with self.subTest(value=value), self.assertRaises((ValueError, TypeError)):
                validate_entity_definition(candidate, Path("animal.json"))
        for kwargs in ({"population": True}, {"population": 1, "reserve_kg": -1},
                       {"population": 0, "reserve_kg": 1}, {"population": 1, "deficit_days": float("nan")}):
            with self.assertRaises(ValueError):
                NutritionalState(**kwargs)
