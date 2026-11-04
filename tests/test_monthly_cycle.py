import unittest
from copy import deepcopy
from unittest.mock import patch

from core.content_registry import ContentRegistry
from simulation.calendar import CalendarState, Month
from simulation.daily_cycle import run_day
from simulation.daily_ecology import resolve_region_daily_ecology
from simulation.monthly_cycle import acknowledge_month_review, run_month
from simulation.monthly_reporting import format_monthly_ecology_report
from simulation.simulation_cycle import run_cycle
from simulation.world_state import HabitatState, RegionState, WorldState


class TestMonthlyCycle(unittest.TestCase):
    def setup_world(self, year=1, month=Month.JANUARY):
        registry = ContentRegistry()
        registry.register_all([
            {"id": "region", "entity_type": "region", "name": "Region"},
            {"id": "local", "entity_type": "habitat", "name": "Local"},
            {"id": "clear", "entity_type": "weather", "name": "Clear"},
            {"id": "rain", "entity_type": "weather", "name": "Rain", "producer_production_multiplier": 2.0},
            {"id": "food", "entity_type": "resource", "name": "Food", "unit": "kg"},
            {"id": "plant", "entity_type": "producer", "production": [
                {"resource_id": "food", "amount_per_producer_per_day": 1.0},
            ]},
            {"id": "animal", "entity_type": "animal", "name": "Animal",
             "food_requirement_per_animal_per_cycle": 31.0, "birth_rate_per_animal_per_cycle": 0.1,
             "diet": [{"resource_id": "food", "preference": 1.0}]},
        ])
        habitat = HabitatState("local", animal_populations={"animal": 1},
                               producer_populations={"plant": 1}, resource_quantities={"food": 1000.0})
        region = RegionState("region", weather_weights={"clear": 1.0, "rain": 1.0},
                             habitats={"local": habitat}, animal_populations={"animal": 1},
                             producer_populations={"plant": 1}, resource_quantities={"food": 1000.0})
        return WorldState(17, calendar=CalendarState(year, month), regions={"region": region}), registry

    def test_month_advance_uses_actual_days_stores_summary_and_stops_before_next_day(self):
        for year, month, length, next_date in (
            (1, Month.JANUARY, 31, CalendarState(1, Month.FEBRUARY)),
            (1, Month.APRIL, 30, CalendarState(1, Month.MAY)),
            (1, Month.FEBRUARY, 28, CalendarState(1, Month.MARCH)),
            (4, Month.FEBRUARY, 29, CalendarState(4, Month.MARCH)),
            (1, Month.DECEMBER, 31, CalendarState(2, Month.JANUARY)),
        ):
            with self.subTest(year=year, month=month):
                world, registry = self.setup_world(year, month)
                result = run_month(world, registry)
                self.assertEqual(len(result.days), length)
                self.assertEqual(world.calendar, next_date)
                self.assertEqual(world.pending_month_review, (year, month))
                self.assertIs(world.monthly_summaries[year][month], result)
                self.assertNotIn(next_date.month, world.daily_history.get(next_date.year, {}))
                self.assertEqual(world.current_cycle, 0)
                self.assertEqual(world.monthly_history, {})

    def test_finishing_partial_month_retains_completed_days_and_matches_daily_run(self):
        world, registry = self.setup_world()
        for _ in range(10):
            run_day(world, registry)
        first = world.daily_history[1][Month.JANUARY][1]
        result = run_month(world, registry)
        reference, reference_registry = self.setup_world()
        for _ in range(31):
            run_day(reference, reference_registry)
        self.assertIs(world.daily_history[1][Month.JANUARY][1], first)
        self.assertEqual(result, reference.monthly_summaries[1][Month.JANUARY])
        self.assertEqual(world, reference)
        self.assertEqual(world.random_generator.getstate(), reference.random_generator.getstate())

    def test_review_blocks_daily_and_legacy_monthly_steps_without_changes(self):
        world, registry = self.setup_world()
        result = run_month(world, registry)
        before, random_before = deepcopy(world), world.random_generator.getstate()
        self.assertIs(run_month(world, registry), result)
        for operation in (run_day, run_cycle):
            with self.subTest(operation=operation.__name__), self.assertRaisesRegex(ValueError, "Review"):
                operation(world, registry)
        self.assertEqual(world, before)
        self.assertEqual(world.random_generator.getstate(), random_before)

    def test_acknowledgement_releases_review_without_advancing_and_retains_past_reports(self):
        world, registry = self.setup_world()
        january = run_month(world, registry)
        report = format_monthly_ecology_report(january, registry)
        date, random_before = deepcopy(world.calendar), world.random_generator.getstate()
        self.assertIs(acknowledge_month_review(world), january)
        self.assertIsNone(world.pending_month_review)
        self.assertEqual(world.calendar, date)
        self.assertEqual(world.random_generator.getstate(), random_before)
        february = run_month(world, registry)
        self.assertEqual(february.month, Month.FEBRUARY)
        self.assertEqual(world.calendar, CalendarState(1, Month.MARCH))
        self.assertIs(world.monthly_summaries[1][Month.JANUARY], january)
        self.assertEqual(format_monthly_ecology_report(january, registry), report)
        with self.assertRaises(ValueError):
            acknowledge_month_review(self.setup_world()[0])

    def test_failed_day_retains_completed_prefix_and_retry_matches_clean_month(self):
        world, registry = self.setup_world()

        def fail_on_third_day(region, content, calendar, random_source):
            if calendar.day == 3:
                raise ValueError("injected day failure")
            return resolve_region_daily_ecology(region, content, calendar, random_source)

        with patch("simulation.daily_cycle.resolve_region_daily_ecology", side_effect=fail_on_third_day):
            with self.assertRaisesRegex(ValueError, "injected day failure"):
                run_month(world, registry)
        self.assertEqual(world.calendar, CalendarState(1, Month.JANUARY, 3))
        self.assertEqual(set(world.daily_history[1][Month.JANUARY]), {1, 2})
        self.assertEqual(world.monthly_summaries, {})
        self.assertIsNone(world.pending_month_review)
        actual = run_month(world, registry)
        reference, other_registry = self.setup_world()
        self.assertEqual(actual, run_month(reference, other_registry))
        self.assertEqual(world.random_generator.getstate(), reference.random_generator.getstate())

    def test_summary_failure_rolls_back_last_day_and_safe_retry_stores_report(self):
        world, registry = self.setup_world()
        for _ in range(30):
            run_day(world, registry)
        before, random_before = deepcopy(world), world.random_generator.getstate()
        with patch("simulation.daily_cycle.summarize_month", side_effect=ValueError("report failure")):
            with self.assertRaisesRegex(ValueError, "report failure"):
                run_day(world, registry)
        self.assertEqual(world, before)
        self.assertEqual(world.random_generator.getstate(), random_before)
        run_day(world, registry)
        self.assertEqual(world.pending_month_review, (1, Month.JANUARY))

    def test_month_advance_rejects_missing_prefix_without_inventing_dates(self):
        world, registry = self.setup_world()
        world.calendar.day = 10
        before = deepcopy(world)
        with self.assertRaisesRegex(ValueError, "first date"):
            run_month(world, registry)
        self.assertEqual(world, before)

    def test_saved_state_preserves_pending_review_and_future_equivalence(self):
        world, registry = self.setup_world()
        run_month(world, registry)
        resumed = deepcopy(world)
        self.assertEqual(run_month(resumed, registry), world.monthly_summaries[1][Month.JANUARY])
        acknowledge_month_review(world)
        acknowledge_month_review(resumed)
        self.assertEqual(run_month(world, registry), run_month(resumed, registry))
        self.assertEqual(world, resumed)
        self.assertEqual(world.random_generator.getstate(), resumed.random_generator.getstate())
