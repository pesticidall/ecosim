from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from core.content_validator import validate_entity_definition
from simulation.calendar import CalendarState
from simulation.carrion import CarrionDeposit
from simulation.daily_cycle import run_day
from simulation.daily_demographics import apply_region_daily_demographics
from simulation.growth import GrowthCohort
from simulation.monthly_cycle import run_month
from simulation.world_state import WorldState


class TestGrowthFeeding(unittest.TestCase):
    def setup_world(self, food=1000, juveniles=1, flat=False):
        import test_daily_demographics
        region, registry = test_daily_demographics.TestDailyDemographics().setup_region(2, food=food, local=not flat)
        registry.get("animal")["growth"] = {
            "newborn_mass_fraction": 0.1, "days_to_adult": 3, "feeding_model": "separate"}
        state = region if flat else region.habitats["local"]
        if juveniles:
            state.growth_cohorts["animal"] = (GrowthCohort(juveniles, 0.1),)
        return WorldState(7, regions={"region": region}), registry, state

    def test_only_juveniles_pay_growth_food_and_maintenance_is_not_reused(self):
        world, registry, habitat = self.setup_world(food=8)
        result = run_day(world, registry).region_results["region"]
        self.assertEqual(result.food_web.regional_feeding["animal"].consumed_amount, 2)
        growth = result.food_web.growth_meals["local"]["animal"].feeding
        self.assertEqual(growth.required_amount, 12)
        self.assertEqual(growth.consumed_amount, 6)
        self.assertEqual(habitat.resource_quantities["food"], 0)
        self.assertEqual(world.regions["region"].resource_quantities["food"], 0)
        self.assertAlmostEqual(habitat.growth_cohorts["animal"][0].mass_fraction, 0.25)
        self.assertAlmostEqual(result.demographics.growth_changes["local"]["animal"].growth_biomass_kg, 1.5)

    def test_adult_only_population_has_no_extra_demand(self):
        world, registry, _ = self.setup_world(juveniles=0)
        result = run_day(world, registry).region_results["region"]
        self.assertEqual(result.food_web.growth_meals["local"]["animal"].feeding.required_amount, 0)
        self.assertEqual(world.regions["region"].resource_quantities["food"], 998)

    def test_growth_shortage_does_not_become_maintenance_starvation(self):
        world, registry, habitat = self.setup_world(food=2)
        result = run_day(world, registry).region_results["region"]
        self.assertEqual(result.food_web.regional_feeding["animal"].nutrition_ratio, 1)
        self.assertEqual(result.demographics.starvation_deaths["animal"], 0)
        self.assertEqual(result.demographics.growth_changes["local"]["animal"].growth_biomass_kg, 0)
        self.assertEqual(habitat.growth_cohorts["animal"], (GrowthCohort(1, 0.1),))

    def test_maintenance_shortage_blocks_growth(self):
        world, registry, _ = self.setup_world(food=1)
        result = run_day(world, registry).region_results["region"]
        self.assertEqual(result.food_web.regional_feeding["animal"].nutrition_ratio, 0.5)
        self.assertEqual(result.food_web.growth_meals["local"]["animal"].feeding.required_amount, 0)
        self.assertEqual(result.demographics.growth_changes["local"]["animal"].growth_biomass_kg, 0)

    def test_growth_consumers_share_local_resources_after_all_maintenance(self):
        world, registry, habitat = self.setup_world(food=16)
        definition = {**registry.get("animal"), "id": "other"}
        registry.register(definition)
        habitat.animal_populations["other"] = 2
        habitat.growth_cohorts["other"] = (GrowthCohort(1, 0.1),)
        world.regions["region"].animal_populations["other"] = 2
        result = run_day(world, registry).region_results["region"]
        for animal in ("animal", "other"):
            self.assertEqual(result.food_web.regional_feeding[animal].consumed_amount, 2)
            self.assertEqual(result.food_web.growth_meals["local"][animal].feeding.consumed_amount, 6)
        self.assertEqual(habitat.resource_quantities["food"], 0)

    def test_flat_region_supports_physical_growth_meals(self):
        world, registry, region = self.setup_world(flat=True)
        result = run_day(world, registry).region_results["region"]
        self.assertEqual(result.food_web.growth_meals[None]["animal"].feeding.consumed_amount, 12)
        self.assertEqual(region.resource_quantities["food"], 986)

    def test_growth_food_stays_in_its_habitat(self):
        world, registry, habitat = self.setup_world()
        empty = deepcopy(habitat)
        empty.definition_id = "empty"
        empty.resource_quantities["food"] = 0
        registry.register({"id": "empty", "entity_type": "habitat"})
        region = world.regions["region"]
        region.habitats["empty"] = empty
        region.animal_populations["animal"] = 4
        result = run_day(world, registry).region_results["region"]
        self.assertEqual(result.food_web.growth_meals["empty"]["animal"].feeding.consumed_amount, 0)
        self.assertEqual(result.food_web.growth_meals["local"]["animal"].feeding.consumed_amount, 12)

    def test_growth_carrion_is_included_once_in_monthly_physical_accounting(self):
        import test_nutrition
        from scripts.investigate_balance import summarize_evidence
        from simulation.monthly_reporting import format_monthly_ecology_report
        from ui.history import format_daily_history
        world, registry, habitat = test_nutrition.TestNutrition().setup_world(animals=2, food=0, carrion=True)
        registry.get("animal")["growth"] = {"newborn_mass_fraction": 0.1, "days_to_adult": 3, "feeding_model": "separate"}
        habitat.growth_cohorts["animal"] = (GrowthCohort(1, 0.1),)
        habitat.carrion_deposits.append(CarrionDeposit("prey", "local", 1000, 1000, None))
        summary = run_month(world, registry)
        budget = summarize_evidence(summary, registry)["carrion_budgets"]["region"]
        self.assertAlmostEqual(budget["scavenged_kg"], 104.2)
        self.assertAlmostEqual(budget["ending_kg"], 895.8)
        self.assertAlmostEqual(budget["balance_error_kg"], 0)
        self.assertAlmostEqual(summary.region_results["region"].scavenged_biomass_kg["local"]["animal"], 104.2)
        self.assertIn("JUVENILE GROWTH FOOD", format_monthly_ecology_report(summary, registry))
        self.assertIn("juvenile growth food", format_daily_history(summary.days[0], registry))

    def test_growth_does_not_infer_carrion_compatibility_or_bypass_first_access(self):
        for reserved in (False, True):
            world, registry, habitat = self.setup_world(food=2)
            if reserved:
                registry.get("animal")["scavenging_diet"] = [{"animal_id": "prey", "preference": 1}]
            habitat.carrion_deposits.append(CarrionDeposit("prey", "local", 20, 20, "other" if reserved else None))
            result = run_day(world, registry).region_results["region"]
            self.assertEqual(result.food_web.growth_meals["local"]["animal"].feeding.consumed_amount, 0)
            # Fixture habitat has complete decay after feeding; inspect access evidence.
            self.assertEqual(result.food_web.growth_meals["local"]["animal"].carrion.consumed_biomass_kg, 0)

    def test_failed_day_rolls_back_growth_food_and_cohorts_and_replays(self):
        world, registry, _ = self.setup_world()
        before = deepcopy(world)
        with patch("simulation.daily_ecology.apply_region_daily_demographics", side_effect=ValueError("failure")):
            with self.assertRaises(ValueError):
                run_day(world, registry)
        self.assertEqual(world.regions, before.regions)
        self.assertEqual(world.random_generator.getstate(), before.random_generator.getstate())
        self.assertEqual(world.daily_history, {})
        self.assertEqual(run_day(world, registry), run_day(before, registry))

    def test_separate_mode_requires_recorded_growth_feeding(self):
        from simulation.daily_feeding import feed_region_for_day
        world, registry, _ = self.setup_world()
        region = world.regions["region"]
        feeding = feed_region_for_day(region, registry, CalendarState())
        with self.assertRaisesRegex(ValueError, "recorded growth feeding"):
            apply_region_daily_demographics(region, registry, feeding)

    def test_schema_accepts_explicit_shared_or_separate_and_rejects_unknown_models(self):
        root = Path(__file__).resolve().parents[1]
        path = root / "content/animals/mammals/scrub_hare.json"
        for model in ("shared", "separate", "free", None, True):
            definition = json.loads(path.read_text(encoding="utf-8"))
            definition["growth"] = {"newborn_mass_fraction": 0.1, "days_to_adult": 90, "feeding_model": model}
            with self.subTest(model=model):
                if model in ("shared", "separate"):
                    validate_entity_definition(definition, path)
                else:
                    with self.assertRaises(ValueError):
                        validate_entity_definition(definition, path)

    def test_maturation_stops_extra_charges_and_monthly_resources_reconcile(self):
        world, registry, habitat = self.setup_world()
        summary = run_month(world, registry)
        local = summary.region_results["region"]
        self.assertAlmostEqual(local.resource_consumption["food"], 98)
        self.assertAlmostEqual(local.feeding_results["animal"].consumed_amount, 62)
        self.assertAlmostEqual(habitat.resource_quantities["food"], 902)
        meals = [day.region_results["region"].food_web.growth_meals["local"]["animal"] for day in summary.days]
        self.assertEqual([meal.feeding.required_amount for meal in meals[:4]], [12, 12, 12, 0])
        self.assertEqual(habitat.growth_cohorts, {})

    def test_birth_day_adds_no_retroactive_growth_food_charge(self):
        world, registry, _ = self.setup_world(juveniles=0)
        registry.get("animal")["birth_rate_per_animal_per_cycle"] = 31
        first = run_day(world, registry).region_results["region"]
        self.assertEqual(first.demographics.births["animal"], 2)
        self.assertEqual(first.food_web.growth_meals["local"]["animal"].feeding.required_amount, 0)
        second = run_day(world, registry).region_results["region"]
        self.assertEqual(second.food_web.growth_meals["local"]["animal"].feeding.required_amount, 24)

    def test_growth_meal_precedes_reserve_top_up(self):
        import test_nutrition
        world, registry, habitat = test_nutrition.TestNutrition().setup_world(animals=2, food=10)
        registry.get("animal")["growth"] = {"newborn_mass_fraction": 0.1, "days_to_adult": 3, "feeding_model": "separate"}
        habitat.growth_cohorts["animal"] = (GrowthCohort(1, 0.1),)
        result = run_day(world, registry).region_results["region"]
        self.assertEqual(result.food_web.growth_meals["local"]["animal"].feeding.consumed_amount, 8)
        self.assertEqual(habitat.nutritional_states["animal"].reserve_kg, 0)

    def test_separate_growth_experiment_replays_with_live_and_carcass_ledgers(self):
        from scripts.investigate_capacity import Factors, run_case
        root = Path(__file__).resolve().parents[1]
        factors = Factors(300, 2000, "small", 8, True, 60, True, 0.9, 30, 0.9, 90, separate_growth_food=True)
        first = run_case(root, factors, 7, 2)
        self.assertEqual(first, run_case(root, factors, 7, 2))
        self.assertEqual(first["growth_budgets"]["scrub_hare"]["31"]["effective_minimum_days"], 90)
        self.assertGreater(sum(m["regions"]["redgrass_savanna"]["growth_food"]["scrub_hare"]["consumed_kg"] for m in first["monthly"]), 0)
        with self.assertRaises(ValueError):
            replace(factors, growth_days=0)
        with self.assertRaises(ValueError):
            replace(factors, growth_ration_floor=True)
