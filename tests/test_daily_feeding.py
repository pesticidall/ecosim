import unittest
from copy import deepcopy

from core.content_registry import ContentRegistry
from simulation.calendar import CalendarState, Month, days_in_month
from simulation.daily_feeding import feed_region_for_day
from simulation.feeding import calculate_population_food_requirement, feed_population, feed_region
from simulation.world_state import HabitatState, RegionState


class TestDailyFeeding(unittest.TestCase):
    def setup_region(self, local=True, food=1000.0):
        registry = ContentRegistry()
        registry.register({
            "id": "grazer", "entity_type": "animal",
            "food_requirement_per_animal_per_cycle": 31.0,
            "diet": [{"resource_id": "grass", "preference": 1.0}],
        })
        region = RegionState("region", animal_populations={"grazer": 2},
                             resource_quantities={"grass": food})
        if local:
            region.habitats["local"] = HabitatState(
                "local", animal_populations={"grazer": 2}, resource_quantities={"grass": food},
            )
        return region, registry

    def test_daily_demand_uses_actual_month_length_including_leap_year_rules(self):
        for year, month, length in (
            (1, Month.JANUARY, 31), (1, Month.APRIL, 30),
            (1, Month.FEBRUARY, 28), (4, Month.FEBRUARY, 29),
            (100, Month.FEBRUARY, 28), (400, Month.FEBRUARY, 29),
        ):
            with self.subTest(year=year, month=month):
                region, registry = self.setup_region()
                result = feed_region_for_day(region, registry, CalendarState(year, month, 1))
                feeding = result.regional_feeding["grazer"]
                self.assertAlmostEqual(feeding.required_amount, 62.0 / length)
                self.assertEqual(feeding.consumed_amount, feeding.required_amount)
                self.assertEqual(feeding.nutrition_ratio, 1.0)
                self.assertAlmostEqual(region.resource_quantities["grass"], 1000.0 - 62.0 / length)

    def test_each_months_daily_intake_sums_to_existing_monthly_allowance(self):
        for year, month in ((1, Month.JANUARY), (1, Month.FEBRUARY),
                            (4, Month.FEBRUARY), (1, Month.APRIL)):
            with self.subTest(year=year, month=month):
                region, registry = self.setup_region()
                calendar = CalendarState(year, month)
                consumed = 0.0
                for _ in range(days_in_month(year, month)):
                    result = feed_region_for_day(region, registry, calendar)
                    consumed += result.regional_feeding["grazer"].consumed_amount
                    calendar.advance_day()
                self.assertAlmostEqual(consumed, 62.0)
                self.assertAlmostEqual(region.resource_quantities["grass"], 938.0)
                self.assertAlmostEqual(region.habitats["local"].resource_quantities["grass"], 938.0)

    def test_daily_stage_retains_date_without_advancing_calendar_or_mutating_content(self):
        region, registry = self.setup_region()
        definition = deepcopy(registry.get("grazer"))
        calendar = CalendarState(4, Month.FEBRUARY, 29)
        result = feed_region_for_day(region, registry, calendar)
        self.assertEqual((result.year, result.month, result.day), (4, Month.FEBRUARY, 29))
        self.assertEqual(calendar, CalendarState(4, Month.FEBRUARY, 29))
        self.assertEqual(region.animal_populations, {"grazer": 2})
        self.assertEqual(registry.get("grazer"), definition)
        calendar.advance_day()
        self.assertEqual((result.year, result.month, result.day), (4, Month.FEBRUARY, 29))

    def test_daily_feeding_preserves_local_scarcity_and_regional_totals(self):
        region, registry = self.setup_region(food=1.0)
        region.habitats["other"] = HabitatState(
            "other", animal_populations={"grazer": 2}, resource_quantities={"grass": 10.0},
        )
        region.animal_populations["grazer"] = 4
        region.resource_quantities["grass"] = 11.0
        result = feed_region_for_day(region, registry, CalendarState())
        self.assertEqual(result.habitat_feeding["local"]["grazer"].nutrition_ratio, 0.5)
        self.assertEqual(result.habitat_feeding["other"]["grazer"].nutrition_ratio, 1.0)
        self.assertEqual(result.regional_feeding["grazer"].required_amount, 4.0)
        self.assertEqual(result.regional_feeding["grazer"].consumed_amount, 3.0)
        self.assertEqual(region.resource_quantities["grass"], 8.0)

    def test_daily_allocation_also_supports_regions_without_habitats(self):
        region, registry = self.setup_region(local=False)
        result = feed_region_for_day(region, registry, CalendarState())
        self.assertEqual(result.habitat_feeding, {})
        self.assertEqual(result.regional_feeding["grazer"].consumed_amount, 2.0)
        self.assertEqual(region.resource_quantities["grass"], 998.0)

    def test_existing_monthly_feeding_and_explicit_single_population_fraction(self):
        region, registry = self.setup_region(local=False)
        result = feed_region(region, registry)
        self.assertEqual(result["grazer"].required_amount, 62.0)
        self.assertEqual(region.resource_quantities["grass"], 938.0)
        result = feed_population(2, registry.get("grazer"), region, period_fraction=1.0 / 31)
        self.assertEqual(result.required_amount, 2.0)
        self.assertEqual(region.resource_quantities["grass"], 936.0)

    def test_invalid_period_fractions_reject_before_consumption_even_for_empty_region(self):
        for value, error in ((True, TypeError), ("0.5", TypeError), (0.0, ValueError),
                             (-0.1, ValueError), (1.1, ValueError),
                             (float("nan"), ValueError), (float("inf"), ValueError)):
            with self.subTest(value=value):
                region, registry = self.setup_region()
                with self.assertRaises(error):
                    feed_region(region, registry, period_fraction=value)
                self.assertEqual(region.resource_quantities["grass"], 1000.0)
                self.assertEqual(region.habitats["local"].resource_quantities["grass"], 1000.0)
                with self.assertRaises(error):
                    feed_region(RegionState("empty"), registry, period_fraction=value)
                with self.assertRaises(error):
                    calculate_population_food_requirement(2, registry.get("grazer"), period_fraction=value)
