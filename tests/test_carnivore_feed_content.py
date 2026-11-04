import unittest
from copy import deepcopy
from pathlib import Path

from core.content_catalog import build_content_registry
from simulation.carrion import CarrionDeposit
from simulation.daily_cycle import run_day
from simulation.daily_feeding import feed_region_for_day
from simulation.habitats import move_animal_population
from simulation.intervention_resources import FeedType
from simulation.interventions import add_supplementary_food, supplementary_food_options
from simulation.monthly_cycle import run_month
from simulation.monthly_reporting import format_monthly_ecology_report
from simulation.scenario_loader import load_scenario


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENARIO = PROJECT_ROOT / "scenarios" / "playtest_b_carnivore_feed_trial.json"
REGION = "redgrass_savanna"
HABITAT = "open_grassland"


class TestCarnivoreFeedContent(unittest.TestCase):
    def setUp(self):
        self.registry = build_content_registry(PROJECT_ROOT / "content")
        self.world = load_scenario(SCENARIO, self.registry)

    def deploy(self):
        return add_supplementary_food(self.world, self.registry, REGION, HABITAT, "carnivore_feed", 50)

    def test_real_content_and_scenario_make_meat_available_through_explicit_diets(self):
        self.assertEqual(self.registry.get("carnivore_feed")["supplementary_feed_type"], "carnivore")
        self.assertEqual(self.registry.get("aardwolf")["diet_type"], "insectivore")
        self.assertEqual(self.registry.get("aardwolf")["diet"], [{"resource_id": "termites", "preference": 1.0}])
        self.assertIn("carnivore_feed", supplementary_food_options(self.world, self.registry, REGION, HABITAT))
        region = self.world.regions[REGION]
        population = dict(region.animal_populations)
        random_before = self.world.random_generator.getstate()
        record = self.deploy()
        self.assertIs(record.feed_type, FeedType.CARNIVORE)
        self.assertEqual(record.ic_spent, 1)
        self.assertEqual(self.world.intervention_resources.carnivore_stock_kg, 450)
        self.assertEqual(self.world.intervention_resources.herbivore_stock_kg, 1000)
        self.assertEqual(region.animal_populations, population)
        self.assertEqual(self.world.random_generator.getstate(), random_before)
        self.assertEqual(region.habitats[HABITAT].carrion_deposits, [])
        result = run_day(self.world, self.registry).region_results[REGION]
        feeding = result.food_web.habitat_feeding[HABITAT]
        self.assertAlmostEqual(feeding["black_backed_jackal"].consumed_amount, 24.0 / 31)
        self.assertEqual(feeding["black_backed_jackal"].nutrition_ratio, 1)
        self.assertEqual(result.food_web.hunting_rounds[HABITAT]["black_backed_jackal"].attempts, ())
        self.assertEqual(feeding["aardwolf"].consumed_amount, 0)
        self.assertEqual(feeding["aardwolf"].nutrition_ratio, 0)
        self.assertNotIn("carnivore_feed", feeding["scrub_hare"].resource_consumption)
        self.assertEqual(region.habitats[HABITAT].carrion_deposits, [])

    def test_specialist_and_herbivore_only_habitat_cannot_request_generic_meat(self):
        region = self.world.regions[REGION]
        move_animal_population(region, "black_backed_jackal", 2, HABITAT, "acacia_scrub")
        before, random_before = deepcopy(self.world), self.world.random_generator.getstate()
        self.assertNotIn("carnivore_feed", supplementary_food_options(self.world, self.registry, REGION, HABITAT))
        self.assertNotIn("termites", supplementary_food_options(self.world, self.registry, REGION, HABITAT))
        with self.assertRaises(ValueError):
            self.deploy()
        self.assertEqual(self.world, before)
        self.assertEqual(self.world.random_generator.getstate(), random_before)

    def test_specialist_can_consume_its_declared_food_through_ordinary_feeding(self):
        # Model an existing local termite supply, not an intervention or producer.
        region = self.world.regions[REGION]
        region.resource_quantities["termites"] = 1.0
        region.habitats[HABITAT].resource_quantities["termites"] = 1.0
        result = feed_region_for_day(region, self.registry, self.world.calendar)
        specialist = result.habitat_feeding[HABITAT]["aardwolf"]
        self.assertEqual(specialist.nutrition_ratio, 1)
        self.assertAlmostEqual(specialist.resource_consumption["termites"], 10.0 / 31)
        self.assertEqual(self.world.interventions, [])

    def test_meat_does_not_feed_same_species_in_a_different_habitat(self):
        region = self.world.regions[REGION]
        move_animal_population(region, "black_backed_jackal", 1, HABITAT, "acacia_scrub")
        self.deploy()
        result = run_day(self.world, self.registry).region_results[REGION]
        feeding = result.food_web.habitat_feeding
        self.assertEqual(feeding[HABITAT]["black_backed_jackal"].nutrition_ratio, 1)
        self.assertEqual(feeding["acacia_scrub"]["black_backed_jackal"].nutrition_ratio, 0)
        self.assertNotIn("carnivore_feed", region.habitats["acacia_scrub"].resource_quantities)

    def test_deployed_meat_and_reserved_carrion_remain_distinct(self):
        habitat = self.world.regions[REGION].habitats[HABITAT]
        reserved = CarrionDeposit("scrub_hare", HABITAT, 3.5, 3.5, "black_backed_jackal")
        habitat.carrion_deposits.append(reserved)
        self.deploy()
        self.assertEqual(habitat.carrion_deposits, [reserved])
        self.assertEqual(habitat.predation_meals, [])
        run_day(self.world, self.registry)
        self.assertEqual(habitat.carrion_deposits, [reserved])
        self.assertEqual(habitat.predation_meals, [])

    def test_competing_compatible_content_shares_limited_meat_through_normal_feeding(self):
        # A test-only additional consumer exercises content-driven competition.
        competitor = {**self.registry.get("black_backed_jackal"), "id": "trial_competitor",
                      "food_requirement_per_animal_per_cycle": 3100.0,
                      "prey_diet": [], "scavenging_diet": []}
        self.registry.register(competitor)
        region = self.world.regions[REGION]
        region.animal_populations["trial_competitor"] = 1
        region.habitats[HABITAT].animal_populations["trial_competitor"] = 1
        self.deploy()
        result = feed_region_for_day(region, self.registry, self.world.calendar)
        feeding = result.habitat_feeding[HABITAT]
        jackal, other = feeding["black_backed_jackal"], feeding["trial_competitor"]
        self.assertAlmostEqual(jackal.nutrition_ratio, other.nutrition_ratio)
        self.assertAlmostEqual(jackal.consumed_amount + other.consumed_amount, 50)
        self.assertEqual(region.habitats[HABITAT].resource_quantities["carnivore_feed"], 0)
        self.assertEqual(feeding["aardwolf"].consumed_amount, 0)

    def test_unfed_trial_exercises_real_hunting_content_and_completes_month(self):
        result = run_month(self.world, self.registry)
        attempts = [attempt for day in result.days
                    for hunting in day.region_results[REGION].food_web.hunting_rounds.get(HABITAT, {}).values()
                    for attempt in hunting.attempts]
        self.assertTrue(attempts)
        self.assertTrue(all(attempt.predator_id == "black_backed_jackal" for attempt in attempts))
        region = result.region_results[REGION]
        for animal_id, count in region.ending_state.animal_populations.items():
            self.assertEqual(count, region.starting_state.animal_populations[animal_id]
                             + region.births.get(animal_id, 0) - region.starvation_deaths.get(animal_id, 0)
                             - region.predation_deaths.get(animal_id, 0))
        self.assertEqual(self.world.interventions, [])

    def test_actual_trial_completes_month_deterministically_with_recorded_cost_and_specialist_shortage(self):
        other = deepcopy(self.world)
        self.deploy()
        add_supplementary_food(other, self.registry, REGION, HABITAT, "carnivore_feed", 50)
        result = run_month(self.world, self.registry)
        self.assertEqual(result, run_month(other, self.registry))
        self.assertEqual(self.world.random_generator.getstate(), other.random_generator.getstate())
        region = result.region_results[REGION]
        self.assertEqual(region.predation_deaths, {})
        self.assertEqual(region.starvation_deaths["aardwolf"], 1)
        self.assertEqual(region.starvation_deaths["black_backed_jackal"], 0)
        stored = sum(states.get("black_backed_jackal").reserve_kg for states in region.ending_state.nutritional_states.values()
                     if "black_backed_jackal" in states)
        self.assertAlmostEqual(region.ending_state.resource_quantities["carnivore_feed"] + stored, 26)
        self.assertEqual(self.world.intervention_resources.ic, 10)
        self.assertEqual(self.world.intervention_resources.carnivore_stock_kg, 500)
        report = format_monthly_ecology_report(result, self.registry)
        self.assertIn("1 IC spent from carnivore feed stock", report)
        self.assertIn("Carnivore Feed", report)

    def test_desktop_can_select_real_trial_and_deploy_carnivore_food(self):
        import tkinter as tk
        from ui.desktop import EcoSimApp

        root = tk.Tk()
        root.withdraw()
        app = None
        try:
            app = EcoSimApp(root, PROJECT_ROOT)
            app.scenario.current(app.scenarios.index(SCENARIO))
            app._load()
            location = next(key for key, value in app._locations.items() if value == (REGION, HABITAT))
            app.habitats.selection_set(location)
            app._render_local()
            self.assertIn("Carnivore Feed", app._food_options)
            app.food_resource.set("Carnivore Feed")
            app._update_food_preview()
            self.assertEqual(float(app.food_quantity.cget("to")), 500)
            self.assertIn("Carnivore reserve after: 450 kg", app.food_preview.get())
            app._add_food()
            self.assertEqual(app.controller.world.intervention_resources.carnivore_stock_kg, 450)
            self.assertIn("Carnivore feed 450/500 kg", app.budget_text.get())
            app._step()
            self.assertIn("Carnivore Feed", app.history_report.get("1.0", "end"))
            root.update_idletasks()
        finally:
            if app is not None:
                app.close()
            else:
                root.destroy()
