import unittest
from copy import deepcopy
from pathlib import Path

from core.content_catalog import build_content_registry
from simulation.calendar import CalendarState, Month
from simulation.interventions import introduce_population, remove_population, add_supplementary_food
from simulation.monthly_cycle import run_month, acknowledge_month_review
from simulation.scenario_loader import load_scenario
from simulation.world_state import WorldState
from ui.calendar_view import calendar_days, calendar_day_text, calendar_months
from ui.controller import SimulationController


ROOT = Path(__file__).resolve().parents[1]


class TestCalendarView(unittest.TestCase):
    def test_current_day_category_filters_preserve_date_status_and_hide_unrelated_interventions(self):
        record = add_supplementary_food(self.world, self.registry, "redgrass_savanna", "open_grassland", "carnivore_feed", 50)
        before = deepcopy(self.world)
        text = calendar_day_text(self.world, self.registry, 1, Month.JANUARY, 1, "Interventions")
        self.assertIn(record.event_id, text)
        text = calendar_day_text(self.world, self.registry, 1, Month.JANUARY, 1, "Weather")
        self.assertIn("Ecology has not run", text)
        self.assertIn("No weather recorded", text)
        self.assertNotIn(record.event_id, text)
        self.assertIn("Future date", calendar_day_text(self.world, self.registry, 1, Month.JANUARY, 2, "Hunts"))
        with self.assertRaisesRegex(ValueError, "category"):
            calendar_day_text(self.world, self.registry, 1, Month.JANUARY, 2, "unknown")
        self.assertEqual(self.world, before)

    def setUp(self):
        self.registry = build_content_registry(ROOT / "content")
        self.world = load_scenario(ROOT / "scenarios" / "playtest_b_carnivore_feed_trial.json", self.registry)

    def test_current_interventions_are_visible_before_ecology_and_not_duplicated_afterward(self):
        world, registry = self.world, self.registry
        introduce_population(world, registry, "redgrass_savanna", "open_grassland", "black_backed_jackal", 2)
        remove_population(world, registry, "redgrass_savanna", "open_grassland", "scrub_hare", 1)
        food = add_supplementary_food(world, registry, "redgrass_savanna", "open_grassland", "carnivore_feed", 50)
        before, rng = deepcopy(world), world.random_generator.getstate()
        days = calendar_days(world, 1, Month.JANUARY)
        self.assertEqual((days[0].status, days[0].intervention_count), ("Current", 3))
        text = calendar_day_text(world, registry, 1, Month.JANUARY, 1)
        self.assertIn("Ecology has not run", text)
        self.assertIn("introduced 2", text)
        self.assertIn("removed 1", text)
        self.assertEqual(text.count(food.event_id), 1)
        self.assertEqual(world, before)
        self.assertEqual(world.random_generator.getstate(), rng)
        controller = SimulationController(world, registry)
        controller.step_day()
        self.assertEqual(controller.calendar_days(1, Month.JANUARY)[0].status, "Completed")
        text = controller.calendar_day_text(1, Month.JANUARY, 1)
        self.assertEqual(text.count(food.event_id), 1)
        saved = text
        world.interventions.clear()
        world.regions.clear()
        self.assertEqual(controller.calendar_days(1, Month.JANUARY)[0].intervention_count, 3)
        self.assertEqual(controller.calendar_day_text(1, Month.JANUARY, 1), saved)

    def test_partial_month_leap_day_and_future_have_no_fabricated_results(self):
        world = WorldState(1, calendar=CalendarState(4, Month.FEBRUARY, 15))
        days = calendar_days(world, 4, Month.FEBRUARY)
        self.assertEqual(len(days), 29)
        self.assertEqual(days[0].status, "Unrecorded")
        self.assertEqual(days[14].status, "Current")
        self.assertEqual(days[-1].status, "Future")
        self.assertIn("No daily evidence", calendar_day_text(world, self.registry, 4, Month.FEBRUARY, 1))
        self.assertIn("No ecological results", calendar_day_text(world, self.registry, 4, Month.FEBRUARY, 29))
        self.assertEqual(len(calendar_days(world, 3, Month.FEBRUARY)), 28)
        with self.assertRaises(ValueError):
            calendar_day_text(world, self.registry, 3, Month.FEBRUARY, 29)

    def test_review_and_year_rollover_retain_chronological_months_and_old_evidence(self):
        self.world.calendar = CalendarState(1, Month.DECEMBER, 1)
        run_month(self.world, self.registry)
        self.assertEqual(calendar_months(self.world), ((2, Month.JANUARY), (1, Month.DECEMBER)))
        text = calendar_day_text(self.world, self.registry, 2, Month.JANUARY, 1)
        self.assertIn("Finish the completed month's review", text)
        before = deepcopy(self.world)
        saved = calendar_day_text(self.world, self.registry, 1, Month.DECEMBER, 31)
        self.assertEqual(self.world, before)
        acknowledge_month_review(self.world)
        run_month(self.world, self.registry)
        self.assertEqual(calendar_day_text(self.world, self.registry, 1, Month.DECEMBER, 31), saved)

    def test_browsing_during_play_does_not_change_ecology_or_resources(self):
        controller = SimulationController(self.world, self.registry)
        controller.play_month()
        before, rng = deepcopy(self.world), self.world.random_generator.getstate()
        for _ in range(3):
            for day in controller.calendar_days(1, Month.JANUARY):
                controller.calendar_day_text(day.year, day.month, day.day)
            controller.calendar_months()
        self.assertTrue(controller.running)
        self.assertEqual(self.world, before)
        self.assertEqual(self.world.random_generator.getstate(), rng)

    def test_widgets_keep_selection_show_immediate_actions_and_reset_on_reload(self):
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
            self.assertEqual(len(app._calendar_buttons), 31)
            app._select_calendar_day((1, Month.JANUARY, 1))
            app._add_food()
            self.assertIn("supplementary food", app.calendar_report.get("1.0", "end"))
            self.assertIn("+", app._calendar_buttons[1].cget("text"))
            before = deepcopy(app.controller.world)
            app.calendar_category.set("Interventions")
            app._render_calendar_detail()
            self.assertIn("supplementary food", app.calendar_report.get("1.0", "end"))
            app.calendar_category.set("Weather")
            app._render_calendar_detail()
            self.assertNotIn("supplementary food", app.calendar_report.get("1.0", "end"))
            self.assertEqual(app.controller.world, before)
            self.assertEqual(app._calendar_date, (1, Month.JANUARY, 1))
            app._step()
            self.assertEqual(app.calendar_category.get(), "Weather")
            self.assertEqual(app._calendar_date, (1, Month.JANUARY, 1))
            self.assertIn("1 January, Year 1 completed", app.calendar_report.get("1.0", "end"))
            app._select_calendar_day((1, Month.JANUARY, 31))
            self.assertIn("Future date", app.calendar_report.get("1.0", "end"))
            app.controller.play_month()
            while app.controller.running:
                app.controller.tick()
            app.refresh()
            self.assertEqual(app._calendar_date[:2], (1, Month.JANUARY))
            app.calendar_choice.set("January, Year 1")
            app._change_calendar_month()
            saved = app.calendar_report.get("1.0", "end")
            app._review()
            app._step()
            self.assertEqual(app.calendar_choice.get(), "January, Year 1")
            self.assertEqual(app.calendar_report.get("1.0", "end"), saved)
            app._load()
            self.assertEqual(app.calendar_choice.get(), "Current month / review")
            self.assertEqual(app.calendar_category.get(), "All events")
            self.assertEqual(app._calendar_date, (1, Month.JANUARY, 1))
            root.attributes("-alpha", 0)
            root.deiconify()
            root.geometry("980x620")
            app.notes_tabs.select(3)
            # A six-row month must retain a visible, scrollable detail panel.
            app.controller.world.calendar = CalendarState(1, Month.JULY, 1)
            app._change_calendar_month()
            root.update()
            panel = app.calendar_grid.master
            self.assertGreaterEqual(app.calendar_report.frame.winfo_height(), 50)
            self.assertLessEqual(app.calendar_report.frame.winfo_y() + app.calendar_report.frame.winfo_height(), panel.winfo_height())
            root.update_idletasks()
        finally:
            if app is not None:
                app.close()
            else:
                root.destroy()
