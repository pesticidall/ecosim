import os
import sys
from pathlib import Path

from core.content_catalog import build_content_registry
from core.content_loader import load_json_file
from simulation.reporting import (
    export_run_report,
    format_cycle_report,
    format_starting_report,
    frame_report,
)
from simulation.scenario_loader import load_scenario
from simulation.simulation_cycle import run_cycle


def clear_screen() -> None:
    if sys.stdout.isatty():
        os.system("cls" if os.name == "nt" else "clear")

def confirm_quit() -> bool:
    clear_screen()
    print(
        frame_report(
            "Are you sure you want to quit EcoSim?",
            title="ECOSIM — PLAYTEST A\nCONFIRM QUIT",
        )
    )
    print()
    print("Y: quit | B or ENTER: go back")
    while True:
        choice = input("> ").strip().lower()
        if choice == "y":
            return True
        if choice in ("b", ""):
            return False
        print("Please enter Y to quit, or B to go back.")

def select_scenario(scenario_paths: list[Path]) -> Path:
    if not scenario_paths:
        raise ValueError("No scenarios are available.")
    choices = {}
    lines = []
    for number, scenario_path in enumerate(scenario_paths, start=1):
        scenario_data = load_json_file(scenario_path)
        if lines:
            lines.append("")
        lines.append(f"{number}. {scenario_data['name']}")
        description = scenario_data.get("description", "")
        if description:
            lines.append(description)
        choices[str(number)] = scenario_path
    clear_screen()
    print(
        frame_report(
            "\n".join(lines),
            title="ECOSIM — PLAYTEST A\nCHOOSE A SCENARIO",
        )
    )    
    print()
    while True:
        choice = input("Enter a scenario number: ").strip()
        if choice in choices:
            return choices[choice]
        print("Please enter one of the listed scenario numbers.")

def confirm_scenario(scenario_path: Path) -> bool:
    scenario_data = load_json_file(scenario_path)
    lines = [scenario_data["name"]]
    description = scenario_data.get("description", "")
    if description:
        lines.extend(["", description])
    clear_screen()
    print(
        frame_report(
            "\n".join(lines),
            title="ECOSIM — PLAYTEST A\nCONFIRM SCENARIO",
        )
    )
    print()
    print("Y: confirm | B or ENTER: go back")
    while True:
        choice = input("> ").strip().lower()
        if choice == "y":
            return True
        if choice in ("b", ""):
            return False
        print("Please enter Y to confirm, or B to go back")

def main() -> None:
    project_root = Path(__file__).resolve().parent
    scenario_paths = sorted((project_root / "scenarios").glob("*.json"))
    while True:
        scenario_path = select_scenario(scenario_paths)
        if confirm_scenario(scenario_path):
            break
    if getattr(sys, "frozen", False):
        report_directory = Path(sys.executable).resolve().parent
    else:
        report_directory = project_root
    report_path = report_directory / "run_report.txt"
    registry = build_content_registry(project_root / "content")
    world_state = load_scenario(scenario_path)
    current_report = format_starting_report(world_state, registry)
    report_history = [current_report]

    while True:
        clear_screen()
        report_heading = (
            "STARTING REPORT" if world_state.current_cycle == 0 else "CYCLE REPORT"
        )
        display_title = f"ECOSIM — PLAYTEST A\n{report_heading}"
        display_report = current_report.removeprefix("STARTING REPORT\n")
        print(frame_report(display_report, title=display_title))
        print()

        while True:
            next_cycle = world_state.current_cycle + 1
            choice = input(
                f"ENTER: begin Cycle {next_cycle} | E: export | Q: quit > "
            ).strip().lower()
            if choice == "e":
                try:
                    export_run_report(report_history, report_path)
                except OSError as error:
                    print(f"Could not export run report: {error}")
                else: 
                    print(f"Run report saved to: {report_path}")
                continue
            if choice in ("", "q"):
                break
            print("Please press ENTER to advance, E to export, or Q to quit.")
        if choice == "q":
            if confirm_quit():
                return
            continue
        cycle_result = run_cycle(world_state, registry)
        current_report = format_cycle_report(cycle_result, registry)
        report_history.append(current_report)

if __name__ == "__main__":
    main()