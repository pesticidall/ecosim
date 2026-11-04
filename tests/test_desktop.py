import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from core.content_catalog import build_content_registry
from simulation.daily_cycle import run_day
from simulation.monthly_cycle import run_month
from simulation.scenario_loader import load_scenario
from ui.controller import SimulationController


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TestDesktopController(unittest.TestCase):
    def setUp(self):
        self.registry = build_content_registry(PROJECT_ROOT / "content")
        scenario = sorted((PROJECT_ROOT / "scenarios").glob("*.json"))[0]
        self.world = load_scenario(scenario, self.registry)
        self.controller = SimulationController(self.world, self.registry)

    def test_paused_callbacks_do_not_advance_or_consume_randomness(self):
        before, random_before = deepcopy(self.world), self.world.random_generator.getstate()
        for _ in range(20):
            self.assertIsNone(self.controller.tick())
        self.assertEqual(self.world, before)
        self.assertEqual(self.world.random_generator.getstate(), random_before)

    def test_step_day_matches_headless_ecology(self):
        reference = deepcopy(self.world)
        self.assertEqual(self.controller.step_day(), run_day(reference, self.registry))
        self.assertEqual(self.world, reference)
        self.assertIn("completed", self.controller.report_text)

    def test_play_pause_resume_matches_headless_month_and_stops_at_review(self):
        reference = deepcopy(self.world)
        expected = run_month(reference, self.registry)
        self.controller.play_month()
        for _ in range(10):
            self.controller.tick()
        self.controller.pause()
        paused = deepcopy(self.world)
        for _ in range(30):
            self.controller.tick()
        self.assertEqual(self.world, paused)
        self.controller.play_month()
        while self.controller.running:
            self.controller.tick()
        year, month = self.world.pending_month_review
        self.assertEqual(self.world.monthly_summaries[year][month], expected)
        self.assertEqual(self.world, reference)
        self.assertEqual(self.world.random_generator.getstate(), reference.random_generator.getstate())
        self.assertIn("31 completed days", self.controller.report_text)
        self.assertIsNone(self.controller.tick())
        with self.assertRaises(ValueError):
            self.controller.play_month()
        date = deepcopy(self.world.calendar)
        self.controller.acknowledge_review()
        self.assertEqual(self.world.calendar, date)
        self.controller.step_day()
        self.assertEqual(self.world.calendar.day, 2)

    def test_extra_idle_callbacks_do_not_change_ecology(self):
        other = SimulationController(deepcopy(self.world), self.registry)
        for _ in range(5):
            self.controller.step_day()
            for _ in range(100):
                other.tick()
            other.step_day()
        self.assertEqual(self.world, other.world)
        self.assertEqual(self.world.random_generator.getstate(), other.world.random_generator.getstate())

    def test_failure_stops_play_and_preserves_unresolved_day(self):
        before = deepcopy(self.world)
        random_before = self.world.random_generator.getstate()
        self.controller.play_month()
        with patch("ui.controller.run_day", side_effect=ValueError("day failed")):
            with self.assertRaisesRegex(ValueError, "day failed"):
                self.controller.tick()
        self.assertFalse(self.controller.running)
        self.assertEqual(self.world, before)
        self.assertEqual(self.world.random_generator.getstate(), random_before)

    def test_history_browsing_is_read_only_and_retains_old_dates_across_months(self):
        self.assertEqual(self.controller.history_entries(), ())
        self.assertIn("Completed dates", self.controller.history_text())
        self.controller.step_day()
        first = self.controller.history_entries()[0]
        first_text = self.controller.history_text(first)
        self.controller.play_month()
        while self.controller.running:
            self.controller.tick()
        entries = self.controller.history_entries()
        self.assertEqual(len(entries), 32)
        self.assertEqual(entries[0].kind, "month")
        self.assertEqual(entries[1].day, 31)
        before, random_before = deepcopy(self.world), self.world.random_generator.getstate()
        self.assertIn("31 completed days", self.controller.history_text(entries[0]))
        self.assertEqual(self.controller.history_text(first), first_text)
        self.assertEqual(self.world, before)
        self.assertEqual(self.world.random_generator.getstate(), random_before)
        self.controller.acknowledge_review()
        self.controller.step_day()
        self.assertEqual(self.controller.history_text(first), first_text)
        self.assertEqual(self.controller.history_entries()[0].month, self.world.calendar.month)

    def test_latest_history_follows_completed_date_and_ignores_live_state_edits(self):
        self.controller.step_day()
        self.assertIn("1 January, Year 1 completed.", self.controller.history_text())
        entry = self.controller.history_entries()[0]
        text = self.controller.history_text(entry)
        self.controller.step_day()
        self.assertIn("2 January, Year 1 completed.", self.controller.history_text())
        for region in self.world.regions.values():
            region.active_weather_id = None
            region.resource_quantities.clear()
            for habitat in region.habitats.values():
                habitat.carrion_deposits.clear()
                habitat.injury_cohorts.clear()
        self.assertEqual(self.controller.history_text(entry), text)


class TestDesktopWidgets(unittest.TestCase):
    def test_real_scenario_controls_render_and_review_pauses_month_play(self):
        import tkinter as tk
        from ui.desktop import EcoSimApp

        root = tk.Tk()
        root.withdraw()
        app = None
        try:
            app = EcoSimApp(root, PROJECT_ROOT)
            root.update_idletasks()
            self.assertTrue(app._locations)
            self.assertIn("Year 1", app.date_text.get())
            self.assertFalse(app.day_button.instate(["disabled"]))
            app._play()
            self.assertTrue(app.controller.running)
            self.assertIsNotNone(app._scheduled)
            app._pause()
            self.assertIsNone(app._scheduled)
            self.assertFalse(app.controller.running)
            app._step()
            self.assertEqual(app.controller.world.calendar.day, 2)
            self.assertIn("1 January, Year 1 completed.", app.history_report.get("1.0", "end"))
            selected = app.controller.history_entries()[0]
            app.history_choice.set(selected.label)
            app._render_history()
            historical_text = app.history_report.get("1.0", "end")
            app._step()
            self.assertEqual(app.history_choice.get(), selected.label)
            self.assertEqual(app.history_report.get("1.0", "end"), historical_text)
            app.controller.play_month()
            while app.controller.running:
                app.controller.tick()
            app.refresh()
            self.assertTrue(app.day_button.instate(["disabled"]))
            self.assertTrue(app.play_button.instate(["disabled"]))
            self.assertFalse(app.review_button.instate(["disabled"]))
            self.assertIn("31 completed days", app.report.get("1.0", "end"))
            app._review()
            self.assertFalse(app.day_button.instate(["disabled"]))
            self.assertTrue(app.review_button.instate(["disabled"]))
            app._load()
            self.assertEqual(app.history_choice.get(), "Latest completed day")
            self.assertEqual(app.controller.history_entries(), ())
            self.assertIn("Completed dates", app.history_report.get("1.0", "end"))
            for location in app._locations:
                app.habitats.selection_set(location)
                app._render_local()
                if app._food_options:
                    break
            self.assertFalse(app.food_button.instate(["disabled"]))
            self.assertEqual(app.food_amount.get(), "50")
            self.assertEqual(float(app.food_quantity.cget("increment")), 50)
            self.assertIn("Cost: 1 IC", app.food_preview.get())
            self.assertIn("IC 10/10", app.budget_text.get())
            app.food_amount.set("150")
            self.assertIn("Cost: 2 IC", app.food_preview.get())
            app.food_amount.set("75")
            self.assertTrue(app.food_button.instate(["disabled"]))
            date = deepcopy(app.controller.world.calendar)
            app.food_amount.set("50")
            app._add_food()
            self.assertEqual(app.controller.world.calendar, date)
            self.assertEqual(app.controller.world.interventions[0].amount_kg, 50)
            self.assertIn("IC 9/10", app.budget_text.get())
            self.assertEqual(app.controller.world.intervention_resources.herbivore_stock_kg, 950)
            self.assertIn("supplementary food", app.report.get("1.0", "end"))
            app.food_amount.set("900")
            self.assertIn("Cost: 9 IC", app.food_preview.get())
            app._add_food()
            self.assertIn("IC 0/10", app.budget_text.get())
            self.assertEqual(app.controller.world.intervention_resources.herbivore_stock_kg, 50)
            self.assertTrue(app.food_button.instate(["disabled"]))
            app._step()
            self.assertIn("supplementary food", app.history_report.get("1.0", "end"))
            root.update_idletasks()
        finally:
            if app is not None:
                app.close()
            else:
                root.destroy()
