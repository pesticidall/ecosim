import unittest
from copy import deepcopy
from random import Random

from core.content_registry import ContentRegistry
from simulation.calendar import CalendarState, Month
from simulation.carrion import CarrionDeposit
from simulation.carrion_cycle import daily_decay_fraction, run_region_carrion_decay
from simulation.daily_ecology import resolve_region_daily_ecology
from simulation.world_state import HabitatState, RegionState


class TestDailyEcology(unittest.TestCase):
    def setup_region(self):
        registry = ContentRegistry()
        registry.register_all([
            {"id": "clear", "entity_type": "weather", "producer_production_multiplier": 1.0},
            {"id": "rain", "entity_type": "weather", "producer_production_multiplier": 2.0},
            {"id": "local", "entity_type": "habitat", "carrion_decay_fraction_per_cycle": 0.5},
            {"id": "grass", "entity_type": "producer", "production": [
                {"resource_id": "leaves", "amount_per_producer_per_day": 1.0},
            ]},
            {"id": "grazer", "entity_type": "animal", "food_requirement_per_animal_per_cycle": 31.0,
             "diet": [{"resource_id": "leaves", "preference": 1.0}]},
            {"id": "scavenger", "entity_type": "animal", "food_requirement_per_animal_per_cycle": 31.0,
             "diet": [], "scavenging_diet": [{"animal_id": "prey", "preference": 1.0}]},
        ])
        habitat = HabitatState("local", animal_populations={"grazer": 1, "scavenger": 1},
                               producer_populations={"grass": 1}, resource_quantities={"leaves": 0.0})
        habitat.carrion_deposits.append(CarrionDeposit("prey", "local", 10.0, 10.0, None))
        region = RegionState("region", active_weather_id="clear", habitats={"local": habitat},
                             animal_populations=dict(habitat.animal_populations),
                             producer_populations={"grass": 1}, resource_quantities={"leaves": 0.0})
        return region, registry

    def test_daily_weather_then_production_then_feeding_then_decay(self):
        region, registry = self.setup_region()
        region.weather_weights = {"rain": 1.0}
        calendar = CalendarState()
        result = resolve_region_daily_ecology(region, registry, calendar, Random(1))
        self.assertEqual(result.active_weather_id, "rain")
        self.assertEqual(result.production_changes, {"leaves": 2.0})
        self.assertEqual(result.food_web.regional_feeding["grazer"].consumed_amount, 1.0)
        self.assertEqual(region.resource_quantities["leaves"], 1.0)
        self.assertEqual(region.habitats["local"].resource_quantities["leaves"], 1.0)
        self.assertEqual(result.food_web.scavenging_results["local"]["scavenger"].consumed_biomass_kg, 1.0)
        decay = result.carrion_decay["local"][0]
        self.assertAlmostEqual(decay.decayed_biomass_kg, 9.0 * daily_decay_fraction(0.5, 31))
        self.assertAlmostEqual(decay.updated_carrion.available_biomass_kg, 9.0 * 0.5 ** (1.0 / 31))
        self.assertEqual((result.year, result.month, result.day), (1, Month.JANUARY, 1))
        self.assertEqual(calendar, CalendarState())

    def test_daily_decay_compounds_to_monthly_loss_for_all_month_lengths(self):
        for days in (28, 29, 30, 31):
            with self.subTest(days=days):
                region, registry = self.setup_region()
                for _ in range(days):
                    run_region_carrion_decay(region, registry, days_in_period=days)
                self.assertAlmostEqual(region.habitats["local"].carrion_deposits[0].available_biomass_kg, 5.0)

    def test_daily_decay_handles_zero_total_and_tiny_monthly_loss(self):
        self.assertEqual(daily_decay_fraction(0.0, 31), 0.0)
        self.assertEqual(daily_decay_fraction(1.0, 31), 1.0)
        self.assertEqual(daily_decay_fraction(0.25, 1), 0.25)
        self.assertGreater(daily_decay_fraction(1e-15, 31), 0.0)
        region, registry = self.setup_region()
        registry.get("local")["carrion_decay_fraction_per_cycle"] = 1.0
        records = run_region_carrion_decay(region, registry, days_in_period=31)
        self.assertEqual(records["local"][0].decayed_biomass_kg, 10.0)
        self.assertEqual(region.habitats["local"].carrion_deposits, [])

    def test_daily_decay_preserves_first_access_and_validates_inputs(self):
        region, registry = self.setup_region()
        region.habitats["local"].carrion_deposits = [CarrionDeposit("prey", "local", 10.0, 10.0, "hunter")]
        run_region_carrion_decay(region, registry, days_in_period=31)
        self.assertEqual(region.habitats["local"].carrion_deposits[0].first_access_consumer_id, "hunter")
        for days, error in ((True, TypeError), (2.0, TypeError), (0, ValueError), (-1, ValueError)):
            with self.subTest(days=days), self.assertRaises(error):
                daily_decay_fraction(0.5, days)
        for fraction, error in ((True, TypeError), ("0.5", TypeError), (-0.1, ValueError),
                                (1.1, ValueError), (float("nan"), ValueError), (float("inf"), ValueError)):
            with self.subTest(fraction=fraction), self.assertRaises(error):
                daily_decay_fraction(fraction, 31)

    def test_weighted_weather_is_seeded_independent_of_mapping_order(self):
        region, registry = self.setup_region()
        other_region = deepcopy(region)
        region.weather_weights = {"rain": 2.0, "clear": 1.0}
        other_region.weather_weights = {"clear": 1.0, "rain": 2.0}
        first_rng, second_rng = Random(23), Random(23)
        first = resolve_region_daily_ecology(region, registry, CalendarState(), first_rng)
        second = resolve_region_daily_ecology(other_region, registry, CalendarState(), second_rng)
        self.assertEqual(first, second)
        self.assertEqual(first_rng.getstate(), second_rng.getstate())
        expected = Random(23)
        expected.random()
        self.assertEqual(first_rng.getstate(), expected.getstate())

    def test_fixed_or_absent_weather_uses_no_randomness(self):
        for weather in ("clear", None):
            with self.subTest(weather=weather):
                region, registry = self.setup_region()
                region.active_weather_id = weather
                random_source = Random(1)
                before = random_source.getstate()
                result = resolve_region_daily_ecology(region, registry, CalendarState(), random_source)
                self.assertEqual(result.active_weather_id, weather)
                self.assertEqual(random_source.getstate(), before)

    def test_unknown_weighted_weather_rejects_before_draw_or_region_changes(self):
        region, registry = self.setup_region()
        region.weather_weights = {"missing": 1.0}
        before = deepcopy(region)
        random_source = Random(1)
        random_before = random_source.getstate()
        with self.assertRaises(KeyError):
            resolve_region_daily_ecology(region, registry, CalendarState(), random_source)
        self.assertEqual(region, before)
        self.assertEqual(random_source.getstate(), random_before)

    def test_later_daily_stage_does_not_rewrite_earlier_evidence(self):
        region, registry = self.setup_region()
        calendar, random_source = CalendarState(), Random(1)
        first = resolve_region_daily_ecology(region, registry, calendar, random_source)
        snapshot = deepcopy(first)
        calendar.advance_day()
        resolve_region_daily_ecology(region, registry, calendar, random_source)
        self.assertEqual(first, snapshot)

    def test_selected_daily_weather_also_applies_to_hunt_detection(self):
        region, registry = self.setup_region()
        registry.get("local")["conditions"] = {"openness": 1.0, "vegetation_density": 0.0}
        registry.get("rain")["visibility_modifier"] = 0.0
        region.weather_weights = {"rain": 1.0}
        registry.register_all([
            {"id": "root", "entity_type": "taxon", "parent_taxon_id": None},
            {"id": "bite", "entity_type": "attack_method", "trauma_modifier": 1.0,
             "trait_effect_target": "bite_effectiveness"},
            {"id": "hunter", "entity_type": "animal", "food_requirement_per_animal_per_cycle": 31.0,
             "diet": [], "prey_diet": [{"animal_id": "grazer", "preference": 1.0}],
             "attack_method_id": "bite"},
        ])
        for animal_id, power in (("hunter", 8.0), ("grazer", 0.0)):
            registry.get(animal_id).update(
                taxon_id="root", typical_adult_mass_kg=10.0,
                primary_movement_mode="terrestrial", available_movement_modes=["terrestrial"],
                statistics={"power": power, "defense": 0.0, "mobility": power,
                            "perception": power, "stealth": 0.0},
            )
        region.animal_populations["hunter"] = 1
        region.habitats["local"].animal_populations["hunter"] = 1
        result = resolve_region_daily_ecology(region, registry, CalendarState(), Random(1))
        hunt = result.food_web.hunting_rounds["local"]["hunter"].attempts[0].hunt
        self.assertEqual(result.production_changes, {"leaves": 2.0})
        self.assertEqual(hunt.approach.detection.scores.weather_visibility_modifier, 0.0)
        self.assertFalse(hunt.approach.detection.detected)
        self.assertEqual(region.animal_populations["grazer"], 1)
