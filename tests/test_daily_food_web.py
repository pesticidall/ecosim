import unittest
from copy import deepcopy
from random import Random

from core.content_registry import ContentRegistry
from simulation.calendar import CalendarState, Month
from simulation.carrion import CarrionDeposit, create_carrion_from_death
from simulation.daily_feeding import feed_region_food_web_for_day
from simulation.deaths import DeathCause, DeathRecord
from simulation.group_feeding import feed_hunting_group
from simulation.groups import AnimalGroup, GroupRole
from simulation.predation import PredationRemains
from simulation.world_state import HabitatState, RegionState


class TestDailyFoodWeb(unittest.TestCase):
    def test_abundance_search_can_allocate_no_encounters_and_skips_search_when_fed(self):
        region, registry = self.setup_region(hunters=2)
        registry.get("hunter")["search_budget"] = {"reference_prey": 1000, "max_opportunities": 1}
        result = feed_region_food_web_for_day(region, registry, CalendarState(), Random(2))
        hunting = result.hunting_rounds["local"]["hunter"]
        self.assertEqual(hunting.search.allocated_member_opportunities, 0)
        self.assertEqual(hunting.attempts, ())
        self.assertEqual(hunting.meals, ())
        region, registry = self.setup_region(hunters=2, forage=100)
        registry.get("hunter")["search_budget"] = {"reference_prey": 60, "max_opportunities": 4}
        rng = Random(1)
        before = rng.getstate()
        result = feed_region_food_web_for_day(region, registry, CalendarState(), rng)
        self.assertIsNone(result.hunting_rounds["local"]["hunter"].search)
        self.assertEqual(rng.getstate(), before)

    def test_abundance_search_spends_member_budget_in_solo_and_group_hunts(self):
        for size in (1, 2):
            region, registry = self.setup_region(hunters=2)
            registry.get("hunter").update(max_hunting_group_size=size,
                search_budget={"reference_prey": 1, "max_opportunities": 4})
            registry.get("hunter")["statistics"]["perception"] = 0
            registry.get("prey")["statistics"]["stealth"] = 10
            result = feed_region_food_web_for_day(region, registry, CalendarState(), Random(1))
            hunting = result.hunting_rounds["local"]["hunter"]
            spent = (len(hunting.attempts) if size == 1 else
                     sum(a.hunt.hunter_change.before.group.member_count for a in hunting.attempts))
            self.assertEqual(spent, hunting.search.allocated_member_opportunities)
            self.assertEqual(hunting.meals, ())
            self.assertLessEqual(spent, 8)

    def test_concealed_approach_is_wired_for_solo_and_group_hunts(self):
        for size in (1, 2):
            region, registry = self.setup_region(hunters=2)
            registry.get("hunter").update(max_hunting_group_size=size, approach_model="concealed")
            registry.get("hunter")["statistics"]["stealth"] = 8
            registry.get("prey")["statistics"]["perception"] = 5
            registry.get("hunter")["name"] = "Hunter"
            registry.get("prey")["name"] = "Prey"
            registry.get("local")["conditions"].update(vegetation_density=0.5, shelter_availability=0.5)
            result = feed_region_food_web_for_day(region, registry, CalendarState(), Random(1))
            attempts = result.hunting_rounds["local"]["hunter"].attempts
            self.assertTrue(attempts)
            self.assertTrue(all(a.hunt.approach.stalking is not None for a in attempts))
            for attempt in attempts:
                from simulation.reporting import format_hunt_details
                text = format_hunt_details(attempt, registry)
                self.assertLess(text.index("Concealed approach:"), text.index("Chase:"))
                self.assertEqual(attempt.hunt.approach.stalking.scores.cover, 0.5)
                if size == 2:
                    self.assertEqual(attempt.hunt.approach.detection.scores.awareness_contribution, 0)

    def test_failed_solo_and_group_hunts_obey_explicit_member_opportunity_budget(self):
        for group_size, attempts in ((1, 4), (2, 2)):
            region, registry = self.setup_region(hunters=2)
            registry.get("hunter").update(max_hunting_group_size=group_size, hunting_attempts_per_animal=2)
            registry.get("hunter")["statistics"]["perception"] = 0
            registry.get("prey")["statistics"]["stealth"] = 10
            result = feed_region_food_web_for_day(region, registry, CalendarState(), Random(1))
            hunting = result.hunting_rounds["local"]["hunter"]
            self.assertEqual(len(hunting.attempts), attempts)
            self.assertEqual(hunting.meals, ())
            self.assertTrue(all(attempt.hunt.outcome.status.value == "not_detected" for attempt in hunting.attempts))

    def setup_region(self, hunters=1, forage=0.0, prey=2):
        registry = ContentRegistry()
        registry.register_all([
            {"entity_type": "taxon", "id": "root", "parent_taxon_id": None},
            {"entity_type": "attack_method", "id": "bite", "trauma_modifier": 1.0,
             "trait_effect_target": "bite_effectiveness"},
            {"entity_type": "habitat", "id": "local",
             "conditions": {"openness": 1.0, "vegetation_density": 0.0}},
        ])
        for animal_id, power, mobility, perception, diet in (
            ("hunter", 8.0, 8.0, 8.0, [{"resource_id": "forage", "preference": 1.0}]),
            ("prey", 0.0, 0.0, 0.0, [{"resource_id": "leaves", "preference": 1.0}]),
            ("scavenger", 0.0, 0.0, 0.0, []),
        ):
            registry.register({
                "entity_type": "animal", "id": animal_id, "taxon_id": "root",
                "typical_adult_mass_kg": 10.0, "primary_movement_mode": "terrestrial",
                "available_movement_modes": ["terrestrial"],
                "food_requirement_per_animal_per_cycle": 31.0, "diet": diet,
                "statistics": {"power": power, "defense": 0.0, "mobility": mobility,
                               "perception": perception, "stealth": 0.0, "intelligence": 5.0},
            })
        registry.get("hunter").update(attack_method_id="bite", prey_diet=[
            {"animal_id": "prey", "preference": 1.0},
        ])
        registry.get("scavenger")["scavenging_diet"] = [{"animal_id": "prey", "preference": 1.0}]
        habitat = HabitatState(
            "local", animal_populations={"hunter": hunters, "prey": prey, "scavenger": 1},
            resource_quantities={"forage": forage, "leaves": 100.0},
        )
        region = RegionState("region", habitats={"local": habitat},
                             animal_populations=dict(habitat.animal_populations),
                             resource_quantities=dict(habitat.resource_quantities))
        return region, registry

    def test_daily_solo_hunt_fills_resource_deficit_then_releases_scavenger_food(self):
        region, registry = self.setup_region(forage=0.25)
        calendar = CalendarState()
        original_definition = deepcopy(registry.get("hunter"))
        result = feed_region_food_web_for_day(region, registry, calendar, Random(1))
        hunter = result.regional_feeding["hunter"]
        self.assertEqual(hunter.required_amount, 1.0)
        self.assertEqual(hunter.resource_consumption, {"forage": 0.25, "prey": 0.75})
        self.assertEqual(hunter.nutrition_ratio, 1.0)
        self.assertEqual(result.hunting_rounds["local"]["hunter"].meals[0].consumption.consumed_biomass_kg, 0.75)
        self.assertEqual(result.scavenging_results["local"]["scavenger"].consumed_biomass_kg, 1.0)
        self.assertEqual(region.habitats["local"].carrion_deposits[0].available_biomass_kg, 8.25)
        self.assertEqual(region.animal_populations["prey"], 1)
        self.assertEqual(registry.get("hunter"), original_definition)
        self.assertEqual(calendar, CalendarState())
        self.assertEqual((result.year, result.month, result.day), (1, Month.JANUARY, 1))

    def test_daily_group_size_and_shared_meal_use_daily_member_demand(self):
        region, registry = self.setup_region(hunters=2)
        registry.get("hunter")["max_hunting_group_size"] = 2
        registry.get("prey")["max_defensive_group_size"] = 2
        result = feed_region_food_web_for_day(region, registry, CalendarState(), Random(1))
        hunting = result.hunting_rounds["local"]["hunter"]
        self.assertEqual(len(hunting.attempts), 1)
        self.assertEqual(hunting.attempts[0].hunt.hunter_change.before.group.member_count, 2)
        self.assertEqual(hunting.feeding.required_amount, 2.0)
        self.assertEqual(hunting.feeding.consumed_amount, 2.0)
        self.assertEqual(hunting.meals[0].death.count, 1)
        self.assertEqual(region.habitats["local"].carrion_deposits[0].available_biomass_kg, 7.0)

    def test_small_units_cap_each_meal_at_daily_group_requirement(self):
        region, registry = self.setup_region(hunters=2)
        registry.get("hunter")["max_hunting_group_size"] = 1
        registry.get("prey")["max_defensive_group_size"] = 2
        result = feed_region_food_web_for_day(region, registry, CalendarState(), Random(1))
        hunting = result.hunting_rounds["local"]["hunter"]
        self.assertEqual(len(hunting.attempts), 2)
        self.assertEqual([meal.consumption.consumed_biomass_kg for meal in hunting.meals], [1.0, 1.0])
        self.assertEqual(hunting.feeding.required_amount, 2.0)
        self.assertEqual(hunting.feeding.nutrition_ratio, 1.0)

    def test_daily_shared_meal_summary_preserves_per_member_requirement(self):
        _, registry = self.setup_region()
        death = DeathRecord("prey", DeathCause.PREDATION, 1, 10.0)
        remains = PredationRemains(death, create_carrion_from_death(death, "local", "hunter"))
        result = feed_hunting_group(
            AnimalGroup("hunter", "region", "local", 2, GroupRole.HUNTING),
            registry.get("hunter"), remains, period_fraction=1.0 / 31,
        )
        self.assertEqual(result.feeding.required_amount, 2.0)
        self.assertEqual(result.feeding.nutrition_ratio, 1.0)
        self.assertEqual(result.consumed_per_member_kg, 1.0)
        self.assertEqual(result.meal.leftover_carrion.available_biomass_kg, 8.0)

    def test_predation_rebases_surviving_prey_daily_nutrition_without_refunding_eaten_food(self):
        region, registry = self.setup_region()
        result = feed_region_food_web_for_day(region, registry, CalendarState(), Random(1))
        prey = result.regional_feeding["prey"]
        self.assertEqual(prey.required_amount, 1.0)
        self.assertEqual(prey.consumed_amount, 1.0)
        self.assertEqual(prey.resource_consumption, {"leaves": 1.0})
        self.assertEqual(region.resource_quantities["leaves"], 98.0)
        self.assertEqual(region.habitats["local"].resource_quantities["leaves"], 98.0)

    def test_resource_fed_daily_predator_does_not_hunt_or_draw_randomness(self):
        region, registry = self.setup_region(forage=1.0)
        random_source = Random(1)
        before = random_source.getstate()
        result = feed_region_food_web_for_day(region, registry, CalendarState(), random_source)
        self.assertEqual(result.hunting_rounds["local"]["hunter"].attempts, ())
        self.assertEqual(region.animal_populations["prey"], 2)
        self.assertEqual(result.scavenging_results["local"]["scavenger"].consumed_biomass_kg, 0.0)
        self.assertEqual(random_source.getstate(), before)

    def test_daily_scavenging_can_fill_failed_hunt_deficit_without_another_death(self):
        region, registry = self.setup_region()
        registry.get("hunter")["scavenging_diet"] = [{"animal_id": "prey", "preference": 1.0}]
        registry.get("hunter")["activity_pattern"] = "diurnal"
        registry.get("prey")["activity_pattern"] = "nocturnal"
        region.habitats["local"].carrion_deposits.append(CarrionDeposit("prey", "local", 10.0, 10.0, None))
        result = feed_region_food_web_for_day(region, registry, CalendarState(), Random(1))
        self.assertEqual(result.hunting_rounds["local"]["hunter"].meals, ())
        for animal_id in ("hunter", "scavenger"):
            self.assertEqual(result.regional_feeding[animal_id].required_amount, 1.0)
            self.assertEqual(result.regional_feeding[animal_id].consumed_amount, 1.0)
            self.assertEqual(result.regional_feeding[animal_id].nutrition_ratio, 1.0)
        self.assertEqual(region.animal_populations["prey"], 2)
        self.assertEqual(region.habitats["local"].carrion_deposits[0].available_biomass_kg, 8.0)

    def test_daily_scavenging_preserves_predator_first_access(self):
        region, registry = self.setup_region(forage=1.0)
        reserved = CarrionDeposit("prey", "local", 10.0, 10.0, "hunter")
        region.habitats["local"].carrion_deposits.append(reserved)
        result = feed_region_food_web_for_day(region, registry, CalendarState(), Random(1))
        self.assertEqual(result.scavenging_results["local"]["scavenger"].consumed_biomass_kg, 0.0)
        self.assertEqual(region.habitats["local"].carrion_deposits, [reserved])

    def test_daily_hunt_uses_actual_month_length_and_seeded_results(self):
        for year, month, days in ((1, Month.FEBRUARY, 28), (4, Month.FEBRUARY, 29),
                                  (1, Month.APRIL, 30), (1, Month.JANUARY, 31)):
            with self.subTest(year=year, month=month):
                region, registry = self.setup_region()
                other_region, other_registry = self.setup_region()
                first_rng, second_rng = Random(1), Random(1)
                calendar = CalendarState(year, month)
                result = feed_region_food_web_for_day(region, registry, calendar, first_rng)
                other = feed_region_food_web_for_day(other_region, other_registry, calendar, second_rng)
                self.assertEqual(result, other)
                self.assertEqual(first_rng.getstate(), second_rng.getstate())
                self.assertAlmostEqual(result.regional_feeding["hunter"].required_amount, 31.0 / days)
                self.assertAlmostEqual(result.hunting_rounds["local"]["hunter"].meals[0].consumption.consumed_biomass_kg, 31.0 / days)

    def test_later_day_does_not_recount_old_meals_or_rewrite_daily_results(self):
        region, registry = self.setup_region(prey=3)
        calendar, random_source = CalendarState(), Random(1)
        first = feed_region_food_web_for_day(region, registry, calendar, random_source)
        saved = deepcopy(first)
        calendar.advance_day()
        second = feed_region_food_web_for_day(region, registry, calendar, random_source)
        self.assertEqual(first, saved)
        self.assertEqual((first.day, second.day), (1, 2))
        self.assertEqual(len(region.habitats["local"].predation_meals), 2)
        self.assertEqual(len(second.hunting_rounds["local"]["hunter"].meals), 1)
        self.assertEqual(second.regional_feeding["hunter"].consumed_amount, 1.0)
