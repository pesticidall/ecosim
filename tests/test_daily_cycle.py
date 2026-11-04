import unittest
from copy import deepcopy

from core.content_registry import ContentRegistry
from simulation.calendar import CalendarState, Month
from simulation.daily_cycle import run_day
from simulation.monthly_cycle import acknowledge_month_review
from simulation.deaths import DeathCause, DeathRecord
from simulation.carrion import create_carrion_from_death
from simulation.predation import PredationRemains, apply_predation_meal, feed_secured_prey
from simulation.simulation_cycle import run_cycle
from simulation.world_state import HabitatState, RegionState, WorldState


class TestDailyCycle(unittest.TestCase):
    def setup_world(self, two_regions=False):
        registry = ContentRegistry()
        registry.register_all([
            {"id": "clear", "entity_type": "weather", "producer_production_multiplier": 1.0},
            {"id": "rain", "entity_type": "weather", "producer_production_multiplier": 2.0},
            {"id": "local", "entity_type": "habitat"},
            {"id": "plant", "entity_type": "producer", "production": [
                {"resource_id": "food", "amount_per_producer_per_day": 1.0},
            ]},
        ])
        regions = {}
        for region_id in (("a", "b") if two_regions else ("a",)):
            animal_id = "animal_" + region_id
            registry.register({"id": animal_id, "entity_type": "animal",
                               "food_requirement_per_animal_per_cycle": 31.0,
                               "birth_rate_per_animal_per_cycle": 1.0,
                               "diet": [{"resource_id": "food", "preference": 1.0}]})
            habitat = HabitatState("local", animal_populations={animal_id: 1},
                                   producer_populations={"plant": 1}, resource_quantities={"food": 1000.0})
            regions[region_id] = RegionState(
                region_id, weather_weights={"clear": 1.0, "rain": 1.0}, habitats={"local": habitat},
                animal_populations=dict(habitat.animal_populations), producer_populations={"plant": 1},
                resource_quantities={"food": 1000.0},
            )
        return WorldState(random_seed=17, regions=regions), registry

    def test_run_day_commits_all_stages_and_records_completed_date(self):
        world, registry = self.setup_world(two_regions=True)
        calendar, random_source = world.calendar, world.random_generator
        region, habitat = world.regions["a"], world.regions["a"].habitats["local"]
        result = run_day(world, registry)
        self.assertEqual((result.year, result.month, result.day), (1, Month.JANUARY, 1))
        self.assertEqual(set(result.region_results), {"a", "b"})
        self.assertIs(world.daily_history[1][Month.JANUARY][1], result)
        self.assertEqual(world.calendar, CalendarState(1, Month.JANUARY, 2))
        self.assertIs(world.calendar, calendar)
        self.assertIs(world.random_generator, random_source)
        self.assertIs(world.regions["a"], region)
        self.assertIs(region.habitats["local"], habitat)
        self.assertGreater(habitat.demographic_carry["animal_a"].births, 0.0)
        self.assertEqual(world.current_cycle, 0)
        self.assertEqual(world.monthly_history, {})

    def test_failure_in_later_region_rolls_back_state_history_date_and_randomness(self):
        world, registry = self.setup_world(two_regions=True)
        registry.get("animal_b")["birth_rate_per_animal_per_cycle"] = float("nan")
        before = deepcopy(world)
        random_before = world.random_generator.getstate()
        resources = world.regions["a"].habitats["local"].resource_quantities
        with self.assertRaises(ValueError):
            run_day(world, registry)
        self.assertEqual(world, before)
        self.assertEqual(world.random_generator.getstate(), random_before)
        self.assertIs(world.regions["a"].habitats["local"].resource_quantities, resources)
        registry.get("animal_b")["birth_rate_per_animal_per_cycle"] = 1.0
        retried = run_day(world, registry)
        fresh, fresh_registry = self.setup_world(two_regions=True)
        self.assertEqual(retried, run_day(fresh, fresh_registry))
        self.assertEqual(world, fresh)
        self.assertEqual(world.random_generator.getstate(), fresh.random_generator.getstate())

    def test_day_boundaries_record_actual_dates_including_leap_day_and_new_year(self):
        for start, expected in (
            (CalendarState(1, Month.JANUARY, 31), CalendarState(1, Month.FEBRUARY, 1)),
            (CalendarState(1, Month.FEBRUARY, 28), CalendarState(1, Month.MARCH, 1)),
            (CalendarState(4, Month.FEBRUARY, 28), CalendarState(4, Month.FEBRUARY, 29)),
            (CalendarState(4, Month.FEBRUARY, 29), CalendarState(4, Month.MARCH, 1)),
            (CalendarState(1, Month.DECEMBER, 31), CalendarState(2, Month.JANUARY, 1)),
        ):
            with self.subTest(start=start):
                world, registry = self.setup_world()
                world.calendar = deepcopy(start)
                result = run_day(world, registry)
                self.assertEqual((result.year, result.month, result.day), (start.year, start.month, start.day))
                self.assertEqual(world.calendar, expected)
                self.assertIs(world.daily_history[start.year][start.month][start.day], result)

    def test_short_scenario_is_equivalent_after_pause_and_saved_state_copy(self):
        uninterrupted, registry = self.setup_world(two_regions=True)
        resumed = deepcopy(uninterrupted)
        for _ in range(35):
            if uninterrupted.pending_month_review is not None:
                acknowledge_month_review(uninterrupted)
            run_day(uninterrupted, registry)
        for _ in range(12):
            run_day(resumed, registry)
        saved_rng = resumed.random_generator.getstate()
        resumed = deepcopy(resumed)
        self.assertEqual(resumed.random_generator.getstate(), saved_rng)
        for _ in range(23):
            if resumed.pending_month_review is not None:
                acknowledge_month_review(resumed)
            run_day(resumed, registry)
        self.assertEqual(resumed, uninterrupted)
        self.assertEqual(resumed.random_generator.getstate(), uninterrupted.random_generator.getstate())
        self.assertEqual(resumed.calendar, CalendarState(1, Month.FEBRUARY, 5))
        self.assertEqual(len(resumed.daily_history[1][Month.JANUARY]), 31)
        self.assertEqual(len(resumed.daily_history[1][Month.FEBRUARY]), 4)
        self.assertEqual(resumed.daily_history[1][Month.JANUARY][31].region_results["a"].demographics.births["animal_a"], 1)

    def test_region_mapping_order_does_not_change_seeded_results(self):
        first, registry = self.setup_world(two_regions=True)
        second = deepcopy(first)
        second.regions = dict(reversed(list(second.regions.items())))
        self.assertEqual(run_day(first, registry), run_day(second, registry))
        self.assertEqual(first.random_generator.getstate(), second.random_generator.getstate())

    def test_later_days_do_not_rewrite_completed_day_results(self):
        world, registry = self.setup_world()
        first = run_day(world, registry)
        saved = deepcopy(first)
        run_day(world, registry)
        self.assertEqual(first, saved)
        self.assertIs(world.daily_history[1][Month.JANUARY][1], first)

    def test_rewinding_to_completed_day_rejects_before_any_changes(self):
        world, registry = self.setup_world()
        run_day(world, registry)
        world.calendar.day = 1
        before = deepcopy(world)
        random_before = world.random_generator.getstate()
        with self.assertRaisesRegex(ValueError, "already been completed"):
            run_day(world, registry)
        self.assertEqual(world, before)
        self.assertEqual(world.random_generator.getstate(), random_before)

    def test_legacy_monthly_runner_cannot_reprocess_partially_completed_month(self):
        world, registry = self.setup_world()
        run_day(world, registry)
        before = deepcopy(world)
        with self.assertRaisesRegex(ValueError, "partially completed month"):
            run_cycle(world, registry)
        self.assertEqual(world, before)

    def test_daily_staging_retains_previous_meal_identity_for_duplicate_guards(self):
        world, registry = self.setup_world()
        death = DeathRecord("prey", DeathCause.PREDATION, 1, 10.0)
        meal = feed_secured_prey(PredationRemains(
            death, create_carrion_from_death(death, "local", "animal_a"),
        ), 1.0)
        world.regions["a"].habitats["local"].predation_meals.append(meal)
        run_day(world, registry)
        run_day(world, registry)
        self.assertIs(world.regions["a"].habitats["local"].predation_meals[0], meal)
        with self.assertRaisesRegex(ValueError, "already been applied"):
            apply_predation_meal(world.regions["a"], meal)
