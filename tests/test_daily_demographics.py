import unittest
from copy import deepcopy
from random import Random

from core.content_registry import ContentRegistry
from simulation.calendar import CalendarState, Month, days_in_month
from simulation.condition_cohorts import InjuryCohort
from simulation.daily_demographics import (
    DemographicCarry, apply_region_daily_demographics, resolve_population_daily_demographics,
)
from simulation.daily_ecology import resolve_region_daily_ecology
from simulation.daily_feeding import feed_region_for_day
from simulation.injuries import create_injury_from_trauma
from simulation.world_state import HabitatState, RegionState


class TestDailyDemographics(unittest.TestCase):
    def setup_region(self, population=1, rate=0.0, food=0.0, local=True):
        registry = ContentRegistry()
        registry.register_all([
            {"id": "local", "entity_type": "habitat", "carrion_decay_fraction_per_cycle": 1.0},
            {"id": "animal", "entity_type": "animal", "food_requirement_per_animal_per_cycle": 31.0,
             "birth_rate_per_animal_per_cycle": rate, "typical_adult_mass_kg": 10.0,
             "diet": [{"resource_id": "food", "preference": 1.0}]},
        ])
        region = RegionState("region", animal_populations={"animal": population},
                             resource_quantities={"food": food})
        if local:
            region.habitats["local"] = HabitatState(
                "local", animal_populations={"animal": population}, resource_quantities={"food": food},
            )
        return region, registry

    def test_small_population_birth_fraction_reaches_whole_animal_at_month_end(self):
        for length in (28, 29, 30, 31):
            with self.subTest(length=length):
                population, carry = 1, DemographicCarry()
                for day in range(1, length + 1):
                    result = resolve_population_daily_demographics(population, 1.0, 1.0, length, carry)
                    population, carry = result.ending_population, result.carry
                    self.assertEqual(result.births, int(day == length))
                self.assertEqual(population, 2)
                self.assertEqual(carry, DemographicCarry())

    def test_unfed_small_population_survives_until_accumulated_loss_reaches_one(self):
        for length in (28, 29, 30, 31):
            with self.subTest(length=length):
                population, carry = 1, DemographicCarry()
                for day in range(1, length + 1):
                    result = resolve_population_daily_demographics(population, 1.0, 0.0, length, carry)
                    population, carry = result.ending_population, result.carry
                    self.assertEqual(result.starvation_deaths, int(day == length))
                    self.assertEqual(result.births, 0)
                self.assertEqual(population, 0)
                self.assertEqual(carry, DemographicCarry())

    def test_fractions_persist_across_unequal_months_without_rounding_away_births(self):
        population, carry = 1, DemographicCarry()
        for month in list(Month)[:10]:
            for _ in range(days_in_month(1, month)):
                result = resolve_population_daily_demographics(
                    population, 0.1, 1.0, days_in_month(1, month), carry,
                )
                population, carry = result.ending_population, result.carry
            self.assertEqual(population, 2 if month is Month.OCTOBER else 1)

    def test_starvation_precedes_births_and_only_survivors_contribute(self):
        result = resolve_population_daily_demographics(2, 31.0, 0.5, 31, DemographicCarry(0.75, 0.99))
        self.assertEqual(result.starvation_deaths, 1)
        self.assertEqual(result.births, 1)
        self.assertEqual(result.ending_population, 2)
        self.assertAlmostEqual(result.carry.births, 0.25)
        extinct = resolve_population_daily_demographics(1, 1000.0, 0.5, 1, DemographicCarry(0.9, 0.9))
        self.assertEqual(extinct.ending_population, 0)
        self.assertEqual(extinct.births, 0)
        self.assertEqual(extinct.carry, DemographicCarry())
        self.assertEqual(resolve_population_daily_demographics(0, 1.0, 1.0, 31, DemographicCarry(0.9, 0.9)).carry,
                         DemographicCarry())

    def test_full_nutrition_adds_no_starvation_and_zero_birth_rate_adds_no_births(self):
        carry = DemographicCarry(0.4, 0.6)
        result = resolve_population_daily_demographics(2, 0.0, 1.0, 31, carry)
        self.assertEqual(result.carry, carry)
        self.assertEqual(result.ending_population, 2)
        tiny = resolve_population_daily_demographics(1, 1e-15, 1.0, 31)
        self.assertGreater(tiny.carry.births, 0.0)

    def test_rejects_invalid_inputs_and_remainders(self):
        for population, rate, nutrition, length, error in (
            (True, 1.0, 1.0, 31, TypeError), (-1, 1.0, 1.0, 31, ValueError),
            (1, True, 1.0, 31, TypeError), (1, -0.1, 1.0, 31, ValueError),
            (1, float("inf"), 1.0, 31, ValueError), (1, 1.0, float("nan"), 31, ValueError),
            (1, 1.0, 1.1, 31, ValueError), (1, 1.0, -0.1, 31, ValueError),
            (1, 1.0, True, 31, TypeError), (1, 1.0, 1.0, True, TypeError),
            (1, 1.0, 1.0, 0, ValueError),
        ):
            with self.subTest(population=population, rate=rate, nutrition=nutrition, length=length):
                with self.assertRaises(error):
                    resolve_population_daily_demographics(population, rate, nutrition, length)
        for invalid in (-0.1, 1.0, float("nan"), float("inf")):
            for field in ("births", "starvation"):
                with self.subTest(field=field, invalid=invalid), self.assertRaises(ValueError):
                    DemographicCarry(**{field: invalid})

    def test_local_accumulation_updates_regions_and_keeps_newborns_healthy(self):
        region, registry = self.setup_region(population=2, rate=31.0, food=1.0)
        habitat = region.habitats["local"]
        injury = create_injury_from_trauma("attack", 1.0)
        habitat.injury_cohorts["animal"] = (InjuryCohort((injury,), 2),)
        habitat.demographic_carry["animal"] = DemographicCarry(0.75, 0.99)
        result = resolve_region_daily_ecology(region, registry, CalendarState(), Random(1))
        self.assertEqual(result.demographics.births, {"animal": 1})
        self.assertEqual(result.demographics.starvation_deaths, {"animal": 1})
        self.assertEqual(habitat.animal_populations["animal"], 2)
        self.assertEqual(region.animal_populations["animal"], 2)
        self.assertEqual(habitat.injury_cohorts["animal"], (InjuryCohort((injury,), 1),))
        # Decay was already resolved; today's new starvation carcass remains intact.
        self.assertEqual(habitat.carrion_deposits[0].available_biomass_kg, 10.0)
        self.assertIsNone(habitat.carrion_deposits[0].first_access_consumer_id)
        self.assertEqual(result.demographics.starvation_death_records["local"][0].count, 1)

    def test_habitat_carries_and_food_shortages_remain_independent(self):
        region, registry = self.setup_region(food=100.0)
        region.habitats["other"] = HabitatState("other", animal_populations={"animal": 1},
                                                resource_quantities={"food": 0.0})
        registry.register({"id": "other", "entity_type": "habitat"})
        region.animal_populations["animal"] = 2
        region.habitats["other"].demographic_carry["animal"] = DemographicCarry(0.0, 0.99)
        result = resolve_region_daily_ecology(region, registry, CalendarState(), Random(1))
        self.assertEqual(result.demographics.starvation_deaths["animal"], 1)
        self.assertEqual(region.habitats["local"].animal_populations["animal"], 1)
        self.assertEqual(region.habitats["other"].animal_populations["animal"], 0)
        self.assertNotIn("animal", region.habitats["other"].demographic_carry)
        self.assertEqual(region.animal_populations["animal"], 1)

    def test_region_without_habitats_accumulates_demographics(self):
        region, registry = self.setup_region(rate=31.0, food=1.0, local=False)
        result = resolve_region_daily_ecology(region, registry, CalendarState(), Random(1))
        self.assertEqual(result.demographics.births, {"animal": 1})
        self.assertEqual(region.animal_populations["animal"], 2)
        self.assertEqual(region.demographic_carry["animal"], DemographicCarry())

    def test_demographic_validation_rejects_all_plans_before_mutation(self):
        region, registry = self.setup_region(rate=31.0, food=10.0)
        registry.register({**registry.get("animal"), "id": "invalid", "birth_rate_per_animal_per_cycle": float("nan")})
        region.animal_populations["invalid"] = 1
        region.habitats["local"].animal_populations["invalid"] = 1
        feeding = feed_region_for_day(region, registry, CalendarState())
        before = deepcopy(region)
        with self.assertRaises(ValueError):
            apply_region_daily_demographics(region, registry, feeding)
        self.assertEqual(region, before)

    def test_daily_integration_preserves_carry_on_pause_and_records_birth_date(self):
        first, registry = self.setup_region(rate=1.0, food=1000.0)
        second = deepcopy(first)
        first_date, second_date = CalendarState(), CalendarState()
        first_rng, second_rng = Random(1), Random(1)
        for day in range(1, 32):
            result = resolve_region_daily_ecology(first, registry, first_date, first_rng)
            first_date.advance_day()
            if day == 12:
                # A saved/copied state includes all fractional carries.
                first = deepcopy(first)
            other = resolve_region_daily_ecology(second, registry, second_date, second_rng)
            second_date.advance_day()
            self.assertEqual(result, other)
            self.assertEqual(result.demographics.births["animal"], int(day == 31))
        self.assertEqual(first, second)
        self.assertEqual(first_rng.getstate(), second_rng.getstate())
        self.assertEqual((result.year, result.month, result.day), (1, Month.JANUARY, 31))
