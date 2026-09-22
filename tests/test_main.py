import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from main import main


class TestMain(unittest.TestCase):
    def test_displays_playtest_a_random(self) -> None:
        output = StringIO()
        with patch("builtins.input", side_effect=["1", "y", "", "q", "1", "y"]), redirect_stdout(output):
            main()
        self.assertIn("Random seed: 104729", output.getvalue())

    def test_displays_completed_first_cycle_report(self) -> None:
        output = StringIO()

        with patch("builtins.input", side_effect=["1", "y", "", "q", "1", "y"]), redirect_stdout(output):
            main()

        report_lines = [
            line.removeprefix("║ ").removesuffix(" ║").strip()
            for line in output.getvalue().splitlines()
        ]
        self.assertIn("Cycle 1", report_lines)
        self.assertIn("Weather: Seasonal Rain", report_lines)
        self.assertIn("Scrub Hare ..................... 100 → 112", report_lines)
        self.assertIn("+12 births", report_lines)
        self.assertIn("Grass .......................... 100 → 126.25 kg", report_lines)

    def test_canceling_quit_preserves_current_cycle(self) -> None:
        from simulation.simulation_cycle import run_cycle

        output = StringIO()
        with (
            patch("builtins.input", side_effect=["1", "y", "", "q", "b", "q", "1", "y"]),
            patch("main.run_cycle", wraps=run_cycle) as cycle_runner,
            redirect_stdout(output),
        ):
            main()

        cycle_runner.assert_called_once()
        report_lines = [
            line.removeprefix("║ ").removesuffix(" ║").strip()
            for line in output.getvalue().splitlines()
        ]
        self.assertEqual(report_lines.count("Cycle 1"), 2)
        self.assertNotIn("Cycle 2", report_lines)

    def test_frozen_app_exports_next_to_executable(self) -> None:
        from pathlib import Path

        packaged_executable = Path("C:/Playtests/EcoSim/EcoSim.exe")
        with (
            patch("builtins.input", side_effect=["1", "y", "e", "q", "y"]),
            patch("main.sys.frozen", True, create=True),
            patch("main.sys.executable", str(packaged_executable)),
            patch("pathlib.Path.write_text", autospec=True) as write_report,
            redirect_stdout(StringIO()),
        ):
            main()

        self.assertEqual(
            write_report.call_args.args[0],
            packaged_executable.parent / "run_report.txt",
        )

    def test_exports_run_without_duplicate_reports(self) -> None:
        output = StringIO()
        with (
            patch(
                "builtins.input",
                side_effect=["1", "y", "", "q", "b", "", "e", "q", "1", "y"],
            ),
            patch("pathlib.Path.write_text", autospec=True) as write_report,
            redirect_stdout(output),
        ):
            main()

        write_report.assert_called_once()
        saved_text = write_report.call_args.args[1]
        report_lines = saved_text.splitlines()
        self.assertEqual(report_lines.count("STARTING REPORT"), 1)
        self.assertEqual(report_lines.count("Cycle 1"), 1)
        self.assertEqual(report_lines.count("Cycle 2"), 1)
        self.assertLess(
            report_lines.index("STARTING REPORT"),
            report_lines.index("Cycle 1"),
        )
        self.assertLess(
            report_lines.index("Cycle 1"),
            report_lines.index("Cycle 2"),
        )
        self.assertIn("Random seed: 104729", report_lines)

    def test_failed_export_keeps_simulation_running(self) -> None:
        from simulation.simulation_cycle import run_cycle

        output = StringIO()
        with (
            patch("builtins.input", side_effect=["1", "y", "", "e", "q", "b", "q", "1", "y"]),
            patch(
                "main.export_run_report",
                side_effect=PermissionError("Permission denied"),
            ) as export_report,
            patch("main.run_cycle", wraps=run_cycle) as cycle_runner,
            redirect_stdout(output),
        ):
            main()

        export_report.assert_called_once()
        cycle_runner.assert_called_once()
        report_text = output.getvalue()
        self.assertIn("Could not export run report:", report_text)
        self.assertNotIn("Run report saved to:", report_text)
        self.assertEqual(report_text.count("║ Cycle 1 "), 2)

    def test_selects_scenario_by_number(self) -> None:
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from main import select_scenario

        scenarios = [
            {"name": "Balanced Beginnings", "description": "A balanced start."},
            {"name": "Grazing Pressure", "description": "More animals compete for food."},
        ]
        output = StringIO()

        with TemporaryDirectory() as temporary_directory:
            scenario_paths = []
            for index, scenario in enumerate(scenarios, start=1):
                path = Path(temporary_directory) / f"scenario_{index}.json"
                path.write_text(json.dumps(scenario), encoding="utf-8")
                scenario_paths.append(path)

            with patch("builtins.input", return_value="2"), redirect_stdout(output):
                selected_path = select_scenario(scenario_paths)

            self.assertEqual(selected_path, scenario_paths[1])

        menu_text = output.getvalue()
        self.assertIn("1. Balanced Beginnings", menu_text)
        self.assertIn("A balanced start.", menu_text)
        self.assertIn("2. Grazing Pressure", menu_text)
        self.assertIn("More animals compete for food.", menu_text)

    def test_confirms_scenario_or_returns_to_selection(self) -> None:
        from pathlib import Path

        from main import confirm_scenario

        scenario_data = {
            "name": "Balanced Beginnings",
            "description": "A balanced start.",
        }

        for choice, expected in [("y", True), ("b", False), ("", False)]:
            with self.subTest(choice=choice):
                output = StringIO()
                with (
                    patch("main.load_json_file", return_value=scenario_data),
                    patch("main.clear_screen") as clear,
                    patch("builtins.input", side_effect=[choice]),
                    redirect_stdout(output),
                ):
                    confirmed = confirm_scenario(Path("example_scenario.json"))

                self.assertIs(confirmed, expected)
                clear.assert_called_once()
                self.assertIn("Balanced Beginnings", output.getvalue())
                self.assertIn("A balanced start.", output.getvalue())
                self.assertIn("Y: confirm | B or ENTER: go back", output.getvalue())

    def test_launch_returns_to_selection_before_starting(self) -> None:
        output = StringIO()
        with (
            patch("builtins.input", side_effect=["1", "b", "1", "y", "q", "y"]),
            patch("main.run_cycle") as cycle_runner,
            redirect_stdout(output),
        ):
            main()

        report_lines = [
            line.removeprefix("║ ").removesuffix(" ║").strip()
            for line in output.getvalue().splitlines()
        ]
        screen_titles = [
            line
            for line in report_lines
            if line in (
                "CHOOSE A SCENARIO",
                "CONFIRM SCENARIO",
                "STARTING REPORT",
            )
        ]

        self.assertEqual(
            screen_titles,
            [
                "CHOOSE A SCENARIO",
                "CONFIRM SCENARIO",
                "CHOOSE A SCENARIO",
                "CONFIRM SCENARIO",
                "STARTING REPORT",
            ],
        )
        self.assertIn("Starting cycle: 0", report_lines)
        cycle_runner.assert_not_called()

    def test_grazing_pressure_export_preserves_starting_conditions(self) -> None:
        output = StringIO()
        with (
            patch(
                "builtins.input",
                side_effect=["2", "y", "", "e", "q", "y"],
            ),
            patch("pathlib.Path.write_text", autospec=True) as write_report,
            redirect_stdout(output),
        ):
            main()

        write_report.assert_called_once()
        saved_text = write_report.call_args.args[1]
        starting_report, cycle_report = saved_text.split("\n\nCycle 1\n", 1)

        expected_lines = (
            "EcoSim release: playtest-a.1",
            "Scenario: Playtest A — Grazing Pressure",
            "Scenario ID: playtest_a_grazing_pressure",
            "Starting cycle: 0",
            "Random seed: 104729",
            "Region name: Redgrass Savanna",
            "Weather: Seasonal Rain",
            "Scrub Hare ..................... 200",
            "Springbok ...................... 80",
            "Bushbuck ....................... 60",
            "Redgrass ....................... 500",
            "Sandpaper Raisin ............... 100",
            "Grass .......................... 100 kg",
            "Leaves ......................... 200 kg",
        )
        for expected_line in expected_lines:
            with self.subTest(line=expected_line):
                self.assertIn(expected_line, starting_report.splitlines())

        self.assertIn("Scrub Hare ..................... 200 → 221", cycle_report)
if __name__ == "__main__":
    unittest.main()