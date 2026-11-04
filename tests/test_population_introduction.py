import unittest
from copy import deepcopy
from pathlib import Path

from core.content_registry import ContentRegistry
from simulation.condition_cohorts import InjuryCohort, healthy_population
from simulation.daily_cycle import run_day
from simulation.daily_demographics import DemographicCarry
from simulation.injuries import create_injury_from_trauma
from simulation.intervention_resources import InterventionResources
from simulation.interventions import (
    introduce_population, preview_population_introduction, remove_population,
    preview_population_removal,
)
from simulation.monthly_cycle import run_month
from simulation.monthly_reporting import format_monthly_ecology_report
from simulation.world_state import HabitatState, RegionState, WorldState
from ui.controller import SimulationController
from ui.history import format_daily_history


class TestPopulationIntroduction(unittest.TestCase):
    def setup_world(self, local=4):
        registry = ContentRegistry()
        registry.register_all([
            {"id": "region", "entity_type": "region", "name": "Region"},
            {"id": "local", "entity_type": "habitat", "name": "Local"},
            {"id": "other", "entity_type": "habitat", "name": "Other"},
            {"id": "food", "entity_type": "resource", "name": "Food", "quantity_type": "biomass", "unit": "kg"},
            {"id": "animal", "entity_type": "animal", "name": "Animal", "preferred_habitat_ids": ["local"],
             "typical_adult_mass_kg": 10.0, "food_requirement_per_animal_per_cycle": 31.0,
             "birth_rate_per_animal_per_cycle": 0.0, "diet": [{"resource_id": "food", "preference": 1.0}]},
        ])
        habitats = {key: HabitatState(key, animal_populations={"animal": count}, resource_quantities={"food": 5000.0})
                    for key, count in (("local", local), ("other", 2))}
        region = RegionState("region", habitats=habitats, animal_populations={"animal": local + 2},
                             resource_quantities={"food": 10000.0})
        return WorldState(1, regions={"region": region}), registry

    def test_healthy_arrivals_preserve_existing_injuries_resources_and_randomness(self):
        world, registry = self.setup_world()
        habitat = world.regions["region"].habitats["local"]
        injury = create_injury_from_trauma("attack", 1.0)
        habitat.injury_cohorts["animal"] = (InjuryCohort((injury,), 3),)
        habitat.demographic_carry["animal"] = DemographicCarry(0.5, 0.5)
        before, rng = deepcopy(world), world.random_generator.getstate()
        quote = preview_population_introduction(world, registry, "region", "local", "animal", 7)
        self.assertEqual(world, before)
        self.assertEqual((quote.quantity, quote.local_before, quote.local_after, quote.regional_after), (7, 4, 11, 13))
        record = introduce_population(world, registry, "region", "local", "animal", 7)
        self.assertEqual(record.quantity, 7)
        self.assertEqual(healthy_population(11, habitat.injury_cohorts["animal"]), 8)
        self.assertEqual(habitat.injury_cohorts, before.regions["region"].habitats["local"].injury_cohorts)
        self.assertEqual(habitat.demographic_carry["animal"], DemographicCarry(0.5, 0.5))
        self.assertEqual(world.regions["region"].habitats["other"], before.regions["region"].habitats["other"])
        self.assertEqual(world.regions["region"].resource_quantities, before.regions["region"].resource_quantities)
        self.assertEqual(habitat.carrion_deposits, [])
        self.assertEqual(world.random_generator.getstate(), rng)
        self.assertEqual(world.calendar, before.calendar)
        self.assertEqual(world.intervention_resources.ic, 6)
        self.assertEqual(world.intervention_resources.introduction_cooldown_months, 3)
        self.assertEqual(world.intervention_resources.removal_cooldown_months, 0)

    def test_absent_species_can_be_introduced_and_extinct_carry_is_cleared(self):
        world, registry = self.setup_world(local=0)
        habitat = world.regions["region"].habitats["local"]
        del habitat.animal_populations["animal"]
        habitat.demographic_carry["animal"] = DemographicCarry(0.9, 0.9)
        introduce_population(world, registry, "region", "local", "animal", 10)
        self.assertEqual(habitat.animal_populations["animal"], 10)
        self.assertNotIn("animal", habitat.demographic_carry)
        self.assertEqual(world.regions["region"].animal_populations["animal"], 12)

    def test_invalid_quantities_reject_atomically_for_both_actions(self):
        for action in (introduce_population, remove_population):
            for quantity, error in ((True, TypeError), (1.5, TypeError), ("2", TypeError),
                                     (None, TypeError), (0, ValueError), (-1, ValueError), (11, ValueError)):
                world, registry = self.setup_world()
                before = deepcopy(world)
                with self.subTest(action=action.__name__, quantity=quantity), self.assertRaises(error):
                    action(world, registry, "region", "local", "animal", quantity)
                self.assertEqual(world, before)

    def test_invalid_target_state_or_budget_rejects_introduction_atomically(self):
        for mutation in ("habitat", "region", "species", "incompatible", "no_preferences", "ic", "charge", "cohorts", "totals", "resolved"):
            world, registry = self.setup_world()
            region, habitat, animal = "region", "local", "animal"
            if mutation == "habitat":
                habitat = "missing"
            elif mutation == "region":
                region = "missing"
            elif mutation == "species":
                animal = "food"
            elif mutation == "incompatible":
                habitat = "other"
            elif mutation == "no_preferences":
                registry.get("animal").pop("preferred_habitat_ids")
            elif mutation == "ic":
                world.intervention_resources = InterventionResources(ic=3.5)
            elif mutation == "charge":
                world.intervention_resources = InterventionResources(introduction_cooldown_months=1)
            elif mutation == "cohorts":
                injury = create_injury_from_trauma("attack", 1.0)
                world.regions[region].habitats[habitat].injury_cohorts[animal] = (InjuryCohort((injury,), 5),)
            elif mutation == "totals":
                world.regions[region].animal_populations[animal] = 0
            else:
                world.monthly_history.setdefault(world.calendar.year, {})[world.calendar.month] = {}
            before = deepcopy(world)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                introduce_population(world, registry, region, habitat, animal, 3)
            self.assertEqual(world, before)

    def test_removal_can_choose_full_population_and_revalidates_stale_preview(self):
        world, registry = self.setup_world()
        quote = preview_population_removal(world, registry, "region", "local", "animal", 4)
        self.assertEqual(quote.local_after, 0)
        world.regions["region"].habitats["local"].animal_populations["animal"] = 3
        world.regions["region"].animal_populations["animal"] = 5
        before = deepcopy(world)
        with self.assertRaises(ValueError):
            remove_population(world, registry, "region", "local", "animal", 4)
        self.assertEqual(world, before)
        remove_population(world, registry, "region", "local", "animal", 3)
        self.assertEqual(world.regions["region"].habitats["local"].animal_populations["animal"], 0)

    def test_first_and_midmonth_introductions_reconcile_with_removal_and_history(self):
        for earlier_days in (0, 10):
            world, registry = self.setup_world()
            for _ in range(earlier_days):
                run_day(world, registry)
            introduction = introduce_population(world, registry, "region", "local", "animal", 7)
            removal = remove_population(world, registry, "region", "local", "animal", 2)
            self.assertNotEqual(introduction.event_id, removal.event_id)
            day = run_day(world, registry)
            self.assertEqual(day.interventions, (introduction, removal))
            self.assertIn("introduced 7 Animal", format_daily_history(day, registry))
            region = run_month(world, registry).region_results["region"]
            self.assertEqual(region.starting_state.animal_populations["animal"], 6)
            self.assertEqual(region.ending_state.animal_populations["animal"], 11)
            self.assertEqual(region.introductions, {"animal": 7})
            self.assertEqual(region.removals, {"animal": 2})
            self.assertEqual(region.births["animal"], 0)
            summary = world.monthly_summaries[1][world.pending_month_review[1]]
            text = format_monthly_ecology_report(summary, registry)
            self.assertIn("Animal: 6 → 11", text)
            self.assertIn("7 introduced", text)
            self.assertIn(introduction.event_id, text)

    def test_introduction_commit_revalidates_budget_and_controller_requires_pause(self):
        world, registry = self.setup_world()
        preview_population_introduction(world, registry, "region", "local", "animal", 5)
        controller = SimulationController(world, registry)
        controller.play_month()
        before = deepcopy(world)
        with self.assertRaisesRegex(ValueError, "Pause"):
            controller.introduce_animals("region", "local", "animal", 5)
        self.assertEqual(world, before)
        controller.pause()
        world.intervention_resources = InterventionResources(ic=3)
        with self.assertRaises(ValueError):
            controller.introduce_animals("region", "local", "animal", 5)
        world.intervention_resources = InterventionResources()
        controller.introduce_animals("region", "local", "animal", 5)
        self.assertIn("introduced 5 Animal", controller.report_text)

    def test_desktop_accepts_quantities_rejects_out_of_range_and_supports_both_actions(self):
        import tkinter as tk
        from ui.desktop import EcoSimApp
        root = tk.Tk()
        root.withdraw()
        app = None
        try:
            project = Path(__file__).resolve().parents[1]
            app = EcoSimApp(root, project)
            trial = project / "scenarios" / "playtest_b_carnivore_feed_trial.json"
            app.scenario.current(app.scenarios.index(trial))
            app._load()
            app.introduction_species.set("Black-backed Jackal")
            app.introduction_amount.set("5")
            self.assertIn("2 → 7", app.introduction_preview.get())
            before = deepcopy(app.controller.world)
            for invalid in ("", "1.5", "0", "11", "abc"):
                app.introduction_amount.set(invalid)
                app.removal_amount.set(invalid)
                self.assertTrue(app.introduction_button.instate(["disabled"]))
                self.assertTrue(app.removal_button.instate(["disabled"]))
            self.assertEqual(app.controller.world, before)
            app.introduction_amount.set("5")
            app._introduce_animals()
            self.assertEqual(app.controller.world.regions["redgrass_savanna"].animal_populations["black_backed_jackal"], 7)
            self.assertTrue(app.introduction_button.instate(["disabled"]))
            app.removal_species.set("Black-backed Jackal")
            app.removal_amount.set("3")
            self.assertIn("7 → 4", app.removal_preview.get())
            app._remove_animals()
            self.assertEqual(app.controller.world.regions["redgrass_savanna"].animal_populations["black_backed_jackal"], 4)
            self.assertEqual(app.controller.world.intervention_resources.ic, 3)
            self.assertTrue(app.removal_button.instate(["disabled"]))
            root.attributes("-alpha", 0)
            root.deiconify()
            root.geometry("980x620")
            app.notes_tabs.select(2)
            for button in (app.removal_button, app.introduction_button):
                panel = button.master
                panel.master.select(panel)
                root.update()
                self.assertLessEqual(button.winfo_y() + button.winfo_height(), panel.winfo_height())
            root.update_idletasks()
        finally:
            if app is not None:
                app.close()
            else:
                root.destroy()
