import unittest
from copy import deepcopy
from unittest.mock import patch
from pathlib import Path

from core.content_registry import ContentRegistry
from simulation.daily_cycle import run_day
from simulation.daily_demographics import DemographicCarry
from simulation.interventions import add_supplementary_food, supplementary_food_options, preview_supplementary_food
from simulation.intervention_resources import FeedType, InterventionResources
from core.content_validator import validate_entity_definition
from simulation.calendar import Month
from simulation.monthly_cycle import acknowledge_month_review, run_month
from simulation.monthly_reporting import format_monthly_ecology_report
from simulation.world_state import HabitatState, RegionState, WorldState
from ui.controller import SimulationController
from ui.history import format_daily_history


class TestSupplementaryFood(unittest.TestCase):
    def test_preview_is_read_only_and_commit_revalidates_balances_after_other_spending(self):
        world, registry = self.setup_world()
        before, random_before = deepcopy(world), world.random_generator.getstate()
        quote = preview_supplementary_food(world, registry, "region", "local", "food", 150)
        self.assertEqual(quote.ic_cost, 2)
        self.assertEqual(quote.resources_after.ic, 8)
        self.assertEqual(quote.resources_after.herbivore_stock_kg, 850)
        self.assertEqual(world, before)
        self.assertEqual(world.random_generator.getstate(), random_before)
        add_supplementary_food(world, registry, "region", "local", "food", 1000)
        spent = deepcopy(world)
        with self.assertRaisesRegex(ValueError, "Insufficient"):
            add_supplementary_food(world, registry, "region", "local", "food", 150)
        self.assertEqual(world, spent)
        self.assertEqual(len(world.interventions), 1)

    def test_insufficient_budgets_and_invalid_steps_leave_all_state_unchanged(self):
        for resources, amount in ((InterventionResources(ic=0.5), 50),
                                   (InterventionResources(herbivore_stock_kg=0), 50),
                                   (InterventionResources(), 1), (InterventionResources(), 75),
                                   (InterventionResources(), 1050)):
            world, registry = self.setup_world()
            world.intervention_resources = resources
            before, random_before = deepcopy(world), world.random_generator.getstate()
            with self.subTest(resources=resources, amount=amount), self.assertRaises(ValueError):
                add_supplementary_food(world, registry, "region", "local", "food", amount)
            self.assertEqual(world, before)
            self.assertEqual(world.random_generator.getstate(), random_before)

    def test_carnivore_tag_uses_meat_reserve_and_ordinary_feeding_without_creating_carrion(self):
        world, registry = self.setup_world()
        registry.register({"id": "meat", "entity_type": "resource", "name": "Meat", "quantity_type": "biomass",
                           "unit": "kg", "supplementary_feed_type": "carnivore"})
        registry.get("animal")["diet"].append({"resource_id": "meat", "preference": 2.0})
        record = add_supplementary_food(world, registry, "region", "local", "meat", 150)
        self.assertIs(record.feed_type, FeedType.CARNIVORE)
        self.assertEqual(record.resources_after, InterventionResources(8, 1000, 350))
        self.assertEqual(record.resources_before, InterventionResources())
        self.assertEqual(world.regions["region"].resource_quantities["meat"], 150)
        before = deepcopy(world)
        with self.assertRaises(ValueError):
            add_supplementary_food(world, registry, "region", "local", "meat", 400)
        self.assertEqual(world, before)
        result = run_day(world, registry)
        feeding = result.region_results["region"].food_web.habitat_feeding
        self.assertEqual(feeding["local"]["animal"].resource_consumption["meat"], 1)
        self.assertNotIn("meat", world.regions["region"].habitats["other"].resource_quantities)
        for habitat in world.regions["region"].habitats.values():
            self.assertEqual(habitat.carrion_deposits, [])
            self.assertEqual(habitat.predation_meals, [])

    def test_feed_tags_are_optional_for_ordinary_resources_but_required_for_deployment(self):
        world, registry = self.setup_world()
        base = dict(registry.get("food"))
        for tag, error in (("herbivore", None), ("carnivore", None), ("unknown", ValueError),
                           (True, TypeError), (None, TypeError)):
            candidate = {**base, "supplementary_feed_type": tag}
            with self.subTest(tag=tag):
                if error:
                    with self.assertRaisesRegex(error, "supplementary_feed_type"):
                        validate_entity_definition(candidate, Path("feed.json"))
                else:
                    validate_entity_definition(candidate, Path("feed.json"))
        del registry.get("food")["supplementary_feed_type"]
        validate_entity_definition(registry.get("food"), Path("food.json"))
        self.assertEqual(supplementary_food_options(world, registry, "region", "local"), ())
        with self.assertRaises(ValueError):
            add_supplementary_food(world, registry, "region", "local", "food", 50)

    def test_spent_balances_recover_once_and_past_intervention_record_stays_fixed(self):
        world, registry = self.setup_world()
        record = add_supplementary_food(world, registry, "region", "local", "food", 150)
        summary = run_month(world, registry)
        self.assertEqual(world.intervention_resources, InterventionResources(10, 950, 500, (1, Month.JANUARY)))
        self.assertEqual(record.resources_after, InterventionResources(8, 850, 500))
        report = format_monthly_ecology_report(summary, registry)
        self.assertIn("2 IC spent from herbivore feed stock", report)
        self.assertIn(record.event_id, report)

    def test_failed_ecology_keeps_applied_action_available_for_one_safe_retry(self):
        world, registry = self.setup_world()
        record = add_supplementary_food(world, registry, "region", "local", "food", 50.0)
        before, random_before = deepcopy(world), world.random_generator.getstate()
        with patch("simulation.daily_cycle.resolve_region_daily_ecology", side_effect=ValueError("failed day")):
            with self.assertRaises(ValueError):
                run_day(world, registry)
        self.assertEqual(world, before)
        self.assertEqual(world.random_generator.getstate(), random_before)
        result = run_day(world, registry)
        self.assertEqual(result.interventions, (record,))
        self.assertEqual(world.interventions, [record])
        self.assertEqual(world.regions["region"].habitats["local"].resource_quantities["food"], 49.0)

    def setup_world(self):
        registry = ContentRegistry()
        registry.register_all([
            {"id": "region", "entity_type": "region", "name": "Region"},
            {"id": "local", "entity_type": "habitat", "name": "Local"},
            {"id": "other", "entity_type": "habitat", "name": "Other"},
            {"id": "food", "entity_type": "resource", "name": "Food", "quantity_type": "biomass", "unit": "kg",
             "supplementary_feed_type": "herbivore"},
            {"id": "animal", "entity_type": "animal", "name": "Animal",
             "typical_adult_mass_kg": 10.0, "food_requirement_per_animal_per_cycle": 31.0,
             "birth_rate_per_animal_per_cycle": 0.0, "diet": [{"resource_id": "food", "preference": 1.0}]},
        ])
        local = HabitatState("local", animal_populations={"animal": 1}, resource_quantities={"food": 0.0})
        other = HabitatState("other", animal_populations={"animal": 1}, resource_quantities={"food": 5.0})
        region = RegionState("region", habitats={"local": local, "other": other},
                             animal_populations={"animal": 2}, resource_quantities={"food": 5.0})
        return WorldState(1, regions={"region": region}), registry

    def test_adds_only_to_selected_habitat_and_regional_total_without_time_or_random_draw(self):
        world, registry = self.setup_world()
        before = world.random_generator.getstate()
        date = deepcopy(world.calendar)
        record = add_supplementary_food(world, registry, "region", "local", "food", 150.0)
        self.assertEqual(world.regions["region"].habitats["local"].resource_quantities["food"], 150.0)
        self.assertEqual(world.regions["region"].habitats["other"].resource_quantities["food"], 5.0)
        self.assertEqual(world.regions["region"].resource_quantities["food"], 155.0)
        self.assertEqual(world.intervention_resources.ic, 8.0)
        self.assertEqual(world.intervention_resources.herbivore_stock_kg, 850.0)
        self.assertEqual(record.ic_spent, 2.0)
        self.assertEqual(world.interventions, [record])
        self.assertEqual((record.year, record.month, record.day), (date.year, date.month, date.day))
        self.assertEqual(world.calendar, date)
        self.assertEqual(world.random_generator.getstate(), before)

    def test_food_is_available_to_todays_feeding_and_can_prevent_accumulated_starvation(self):
        world, registry = self.setup_world()
        world.regions["region"].habitats["local"].demographic_carry["animal"] = DemographicCarry(starvation=0.99)
        unfed = deepcopy(world)
        record = add_supplementary_food(world, registry, "region", "local", "food", 50.0)
        fed_day = run_day(world, registry)
        unfed_day = run_day(unfed, registry)
        self.assertEqual(fed_day.region_results["region"].food_web.habitat_feeding["local"]["animal"].nutrition_ratio, 1.0)
        self.assertEqual(fed_day.region_results["region"].demographics.starvation_deaths["animal"], 0)
        self.assertEqual(unfed_day.region_results["region"].demographics.starvation_deaths["animal"], 1)
        self.assertEqual(fed_day.interventions, (record,))
        self.assertIn("1 January, Year 1 · Local: +50 kg Food (supplementary food)", format_daily_history(fed_day, registry))

    def test_rejects_invalid_amounts_targets_and_overflow_before_any_mutation(self):
        for amount, error in ((True, TypeError), ("2", TypeError), (0, ValueError), (-1, ValueError),
                              (float("nan"), ValueError), (float("inf"), ValueError)):
            world, registry = self.setup_world()
            before = deepcopy(world)
            with self.subTest(amount=amount), self.assertRaises(error):
                add_supplementary_food(world, registry, "region", "local", "food", amount)
            self.assertEqual(world, before)
        for region_id, habitat_id, resource_id in (("missing", "local", "food"), ("region", "missing", "food"),
                                                    ("region", "local", "missing")):
            world, registry = self.setup_world()
            before = deepcopy(world)
            with self.subTest(target=(region_id, habitat_id, resource_id)), self.assertRaises(ValueError):
                add_supplementary_food(world, registry, region_id, habitat_id, resource_id, 50.0)
            self.assertEqual(world, before)
        world, registry = self.setup_world()
        world.regions["region"].resource_quantities["food"] = 1e308
        world.regions["region"].habitats["local"].resource_quantities["food"] = 1e308
        before = deepcopy(world)
        with self.assertRaises(ValueError):
            add_supplementary_food(world, registry, "region", "local", "food", 1e308)
        with self.assertRaisesRegex(ValueError, "precision"):
            add_supplementary_food(world, registry, "region", "local", "food", 50)
        self.assertEqual(world, before)

    def test_only_compatible_biomass_food_for_living_local_populations_is_offered(self):
        world, registry = self.setup_world()
        self.assertEqual(supplementary_food_options(world, registry, "region", "local"), ("food",))
        for field, invalid in (("unit", "litres"), ("quantity_type", "liquid"), ("entity_type", "weather")):
            definition = registry.get("food")
            original = definition[field]
            definition[field] = invalid
            with self.subTest(field=field):
                self.assertEqual(supplementary_food_options(world, registry, "region", "local"), ())
            definition[field] = original
        world.regions["region"].habitats["local"].animal_populations["animal"] = 0
        self.assertEqual(supplementary_food_options(world, registry, "region", "local"), ())

    def test_multiple_actions_are_recorded_once_each_and_never_retroactively(self):
        world, registry = self.setup_world()
        first = add_supplementary_food(world, registry, "region", "local", "food", 50.0)
        second = add_supplementary_food(world, registry, "region", "local", "food", 100.0)
        self.assertNotEqual(first.event_id, second.event_id)
        day = run_day(world, registry)
        self.assertEqual(day.interventions, (first, second))
        self.assertEqual(run_day(world, registry).interventions, ())
        self.assertEqual(day.interventions, (first, second))
        world.calendar.day = 1
        before = deepcopy(world)
        with self.assertRaisesRegex(ValueError, "unresolved"):
            add_supplementary_food(world, registry, "region", "local", "food", 50.0)
        self.assertEqual(world, before)

    def test_controller_requires_pause_and_month_review_actions_apply_to_next_month(self):
        world, registry = self.setup_world()
        controller = SimulationController(world, registry)
        controller.play_month()
        before = deepcopy(world)
        with self.assertRaisesRegex(ValueError, "Pause"):
            controller.add_food("region", "local", "food", 1.0)
        self.assertEqual(world, before)
        controller.pause()
        controller.add_food("region", "local", "food", 50.0)
        january = run_month(world, registry)
        report = format_monthly_ecology_report(january, registry)
        self.assertIn("INTERVENTIONS", report)
        self.assertIn("1 January, Year 1", report)
        record = controller.add_food("region", "local", "food", 50.0)
        self.assertEqual(record.month, world.calendar.month)
        self.assertEqual(record.day, 1)
        self.assertEqual(format_monthly_ecology_report(january, registry), report)
        acknowledge_month_review(world)
        day = run_day(world, registry)
        self.assertEqual(day.interventions, (record,))
