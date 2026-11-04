import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from core.content_catalog import build_content_registry
from core.content_registry import ContentRegistry
from core.content_validator import validate_entity_definition
from simulation.calendar import Month
from simulation.carrion import CarrionDeposit
from simulation.condition_cohorts import InjuryCohort
from simulation.daily_cycle import run_day
from simulation.daily_demographics import DemographicCarry
from simulation.injuries import create_injury_from_trauma
from simulation.intervention_resources import InterventionResources
from simulation.interventions import add_supplementary_food, preview_population_removal, remove_population
from simulation.monthly_cycle import acknowledge_month_review, run_month
from simulation.monthly_reporting import format_monthly_ecology_report
from simulation.world_state import HabitatState, RegionState, WorldState
from ui.controller import SimulationController
from ui.history import format_daily_history


ROOT = Path(__file__).resolve().parents[1]


class TestPopulationRemoval(unittest.TestCase):
    def setup_world(self, local=4, other=2):
        registry = ContentRegistry()
        registry.register_all([
            {"id": "region", "entity_type": "region", "name": "Region"},
            {"id": "local", "entity_type": "habitat", "name": "Local"},
            {"id": "other", "entity_type": "habitat", "name": "Other"},
            {"id": "food", "entity_type": "resource", "name": "Food", "quantity_type": "biomass",
             "unit": "kg", "supplementary_feed_type": "herbivore"},
            {"id": "animal", "entity_type": "animal", "name": "Animal",
             "typical_adult_mass_kg": 10.0, "food_requirement_per_animal_per_cycle": 31.0,
             "birth_rate_per_animal_per_cycle": 0.0, "diet": [{"resource_id": "food", "preference": 1.0}]},
        ])
        habitats = {key: HabitatState(key, animal_populations={"animal": count}, resource_quantities={"food": 500.0})
                    for key, count in (("local", local), ("other", other))}
        region = RegionState("region", habitats=habitats, animal_populations={"animal": local + other},
                             resource_quantities={"food": 1000.0})
        return WorldState(1, regions={"region": region}), registry

    def test_preview_and_removal_update_only_target_and_budget_without_deaths_or_randomness(self):
        world, registry = self.setup_world()
        before, random_before = deepcopy(world), world.random_generator.getstate()
        quote = preview_population_removal(world, registry, "region", "local", "animal", 2)
        self.assertEqual((quote.quantity, quote.local_before, quote.local_after), (2, 4, 2))
        self.assertEqual(world, before)
        record = remove_population(world, registry, "region", "local", "animal", 2)
        self.assertEqual(world.regions["region"].animal_populations["animal"], 4)
        self.assertEqual(world.regions["region"].habitats["other"].animal_populations["animal"], 2)
        self.assertEqual(world.intervention_resources.ic, 7)
        self.assertEqual(world.intervention_resources.removal_cooldown_months, 2)
        self.assertEqual(record.charge_spent, 1)
        self.assertEqual(world.interventions, [record])
        self.assertEqual(world.calendar, before.calendar)
        self.assertEqual(world.random_generator.getstate(), random_before)
        self.assertEqual(world.regions["region"].resource_quantities, before.regions["region"].resource_quantities)
        for habitat in world.regions["region"].habitats.values():
            self.assertEqual(habitat.carrion_deposits, [])
            self.assertEqual(habitat.predation_meals, [])

    def test_injury_cohorts_reconcile_and_extinction_clears_local_fractional_carry(self):
        world, registry = self.setup_world(local=4)
        habitat = world.regions["region"].habitats["local"]
        injury = create_injury_from_trauma("attack", 1.0)
        habitat.injury_cohorts["animal"] = (InjuryCohort((injury,), 4),)
        habitat.demographic_carry["animal"] = DemographicCarry(0.8, 0.9)
        reserved = CarrionDeposit("animal", "local", 10.0, 10.0, "animal")
        habitat.carrion_deposits.append(reserved)
        remove_population(world, registry, "region", "local", "animal", 2)
        self.assertEqual(habitat.injury_cohorts["animal"], (InjuryCohort((injury,), 2),))
        self.assertEqual(habitat.demographic_carry["animal"], DemographicCarry(0.8, 0.9))
        self.assertEqual(habitat.carrion_deposits, [reserved])
        all_world, all_registry = self.setup_world(local=2)
        target = all_world.regions["region"].habitats["local"]
        target.injury_cohorts["animal"] = (InjuryCohort((injury,), 2),)
        target.demographic_carry["animal"] = DemographicCarry(0.8, 0.9)
        remove_population(all_world, all_registry, "region", "local", "animal", 2)
        self.assertEqual(target.animal_populations["animal"], 0)
        self.assertEqual(target.injury_cohorts["animal"], ())
        self.assertNotIn("animal", target.demographic_carry)

    def test_invalid_preset_population_budget_or_charge_rejects_atomically(self):
        for mutation in ("too_few", "no_ic", "cooldown", "invalid_cohort", "invalid_total"):
            world, registry = self.setup_world()
            if mutation == "too_few":
                world.regions["region"].habitats["local"].animal_populations["animal"] = 1
                world.regions["region"].animal_populations["animal"] = 3
            elif mutation == "no_ic":
                world.intervention_resources = InterventionResources(ic=2.5)
            elif mutation == "cooldown":
                world.intervention_resources = InterventionResources(removal_cooldown_months=1)
            elif mutation == "invalid_cohort":
                injury = create_injury_from_trauma("attack", 1.0)
                world.regions["region"].habitats["local"].injury_cohorts["animal"] = (InjuryCohort((injury,), 5),)
            elif mutation == "invalid_total":
                world.regions["region"].animal_populations["animal"] = 1
            before, random_before = deepcopy(world), world.random_generator.getstate()
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                remove_population(world, registry, "region", "local", "animal", 2)
            self.assertEqual(world, before)
            self.assertEqual(world.random_generator.getstate(), random_before)

    def test_shared_budget_and_history_handle_food_and_removal_together(self):
        world, registry = self.setup_world()
        food = add_supplementary_food(world, registry, "region", "local", "food", 50)
        removal = remove_population(world, registry, "region", "local", "animal", 2)
        self.assertNotEqual(food.event_id, removal.event_id)
        self.assertEqual(world.intervention_resources.ic, 6)
        self.assertEqual(world.intervention_resources.herbivore_stock_kg, 950)
        day = run_day(world, registry)
        self.assertEqual(day.interventions, (food, removal))
        text = format_daily_history(day, registry)
        self.assertIn("supplementary food", text)
        self.assertIn("removed 2 Animal", text)
        self.assertEqual(day.region_results["region"].demographics.starvation_deaths["animal"], 0)

    def test_first_and_midmonth_removals_reconcile_monthly_population_ledger(self):
        for earlier_days in (0, 10):
            with self.subTest(earlier_days=earlier_days):
                world, registry = self.setup_world()
                for _ in range(earlier_days):
                    run_day(world, registry)
                record = remove_population(world, registry, "region", "local", "animal", 2)
                summary = run_month(world, registry)
                region = summary.region_results["region"]
                self.assertEqual(region.starting_state.animal_populations["animal"], 6)
                self.assertEqual(region.ending_state.animal_populations["animal"], 4)
                self.assertEqual(region.removals, {"animal": 2})
                self.assertEqual(region.predation_deaths, {})
                self.assertEqual(region.starvation_deaths["animal"], 0)
                report = format_monthly_ecology_report(summary, registry)
                self.assertIn("Animal: 6 → 4", report)
                self.assertIn("2 removed", report)
                self.assertIn(record.event_id, report)

    def test_charge_recovers_after_two_unique_month_boundaries_and_review_does_not_accelerate_it(self):
        world, registry = self.setup_world()
        remove_population(world, registry, "region", "local", "animal", 2)
        run_month(world, registry)
        self.assertEqual(world.intervention_resources.removal_cooldown_months, 1)
        run_month(world, registry)
        self.assertEqual(world.intervention_resources.removal_cooldown_months, 1)
        acknowledge_month_review(world)
        run_day(world, registry)
        self.assertEqual(world.intervention_resources.removal_cooldown_months, 1)
        with self.assertRaises(ValueError):
            remove_population(world, registry, "region", "other", "animal", 2)
        run_month(world, registry)
        self.assertEqual(world.intervention_resources.removal_cooldown_months, 0)
        remove_population(world, registry, "region", "other", "animal", 2)
        self.assertEqual(world.intervention_resources.ic, 7)
        self.assertEqual(world.intervention_resources.removal_cooldown_months, 2)

    def test_failed_month_end_does_not_reduce_cooldown_and_copy_resume_is_deterministic(self):
        world, registry = self.setup_world()
        remove_population(world, registry, "region", "local", "animal", 2)
        for _ in range(30):
            run_day(world, registry)
        before, random_before = deepcopy(world), world.random_generator.getstate()
        with patch("simulation.daily_cycle.summarize_month", side_effect=ValueError("failed report")):
            with self.assertRaises(ValueError):
                run_day(world, registry)
        self.assertEqual(world, before)
        self.assertEqual(world.random_generator.getstate(), random_before)
        resumed = deepcopy(world)
        self.assertEqual(run_day(world, registry), run_day(resumed, registry))
        self.assertEqual(world.intervention_resources.removal_cooldown_months, 1)

    def test_real_species_need_no_intervention_presets_and_controller_requires_pause(self):
        registry = build_content_registry(ROOT / "content")
        for definition in registry.definitions_of_type("animal"):
            self.assertNotIn("removal_quantity", definition)
            self.assertNotIn("introduction_quantity", definition)
            validate_entity_definition(definition, Path("animal.json"))
        world, content = self.setup_world()
        controller = SimulationController(world, content)
        controller.play_month()
        before = deepcopy(world)
        with self.assertRaisesRegex(ValueError, "Pause"):
            controller.remove_animals("region", "local", "animal", 2)
        self.assertEqual(world, before)
        controller.pause()
        controller.remove_animals("region", "local", "animal", 2)
        self.assertIn("removed 2 Animal", controller.report_text)

    def test_desktop_removal_uses_chosen_quantity_and_disables_spent_charge(self):
        import tkinter as tk
        from ui.desktop import EcoSimApp

        root = tk.Tk()
        root.withdraw()
        app = None
        try:
            app = EcoSimApp(root, ROOT)
            trial = ROOT / "scenarios" / "playtest_b_carnivore_feed_trial.json"
            app.scenario.current(app.scenarios.index(trial))
            app._load()
            selected = app.habitats.selection()[0]
            self.assertEqual(app._locations[selected], ("redgrass_savanna", "open_grassland"))
            app.removal_species.set("Black-backed Jackal")
            app._update_removal_preview()
            self.assertIn("Quantity: 1 Black-backed Jackal", app.removal_preview.get())
            self.assertIn("2 → 1", app.removal_preview.get())
            self.assertFalse(app.removal_button.instate(["disabled"]))
            app._remove_animals()
            self.assertEqual(app.controller.world.regions["redgrass_savanna"].animal_populations["black_backed_jackal"], 1)
            self.assertEqual(app.controller.world.intervention_resources.ic, 7)
            self.assertTrue(app.removal_button.instate(["disabled"]))
            self.assertIn("2 monthly", app.removal_availability.get())
            app._step()
            self.assertIn("removed 1 Black-backed Jackal", app.history_report.get("1.0", "end"))
            root.update_idletasks()
        finally:
            if app is not None:
                app.close()
            else:
                root.destroy()
