from copy import deepcopy
from math import isclose
from pathlib import Path
from textwrap import (
    fill,
    wrap,
)

from core.content_registry import ContentRegistry
from simulation.feeding import (
    calculate_population_food_requirement,
    feed_region,
)
from simulation.production import apply_producer_production
from simulation.simulation_cycle import CycleResult
from simulation.world_state import WorldState

# Change this for each distributed code or content revision.
ECOSIM_RELEASE = "playtest-a.1"


def frame_report(
    report_text: str,
    width: int = 72,
    title: str | None = None,
) -> str:
    if width < 1:
        raise ValueError("Report width must be at least 1.")
    border = "═" * (width + 2)
    lines = [f"╔{border}╗"]
    if title:
        for title_line in title.split("\n"):
            for line in wrap(title_line, width=width) or [""]:
                lines.append(f"║ {line:^{width}} ║")
            lines.append(f"╟{'─' * (width + 2)}╢")

    for original_line in report_text.split("\n"):
        wrapped_lines = wrap(original_line, width=width) or [""]
        for line in wrapped_lines:
            lines.append(f"║ {line:<{width}} ║")
    lines.append(f"╚{border}╝")
    return "\n".join(lines)

def format_resource_amount(amount: float) -> str:
    return f"{amount:.2f}".rstrip("0").rstrip(".")

def format_report_row(label: str, value: str) -> str:
    padded_label = f"{label} "
    return f"{padded_label:.<32} {value}"

def format_run_header(
    world_state: WorldState,
) -> str:
    return (
        f"EcoSim release: {ECOSIM_RELEASE}\n"
        f"Random seed: {world_state.random_seed}"
    )

def format_starting_report(
    world_state: WorldState,
    registry: ContentRegistry,
) -> str:
    lines = [
        "STARTING REPORT",
        f"Scenario: {world_state.scenario_name}",
    ]
    if world_state.scenario_description:
        lines.append(
            fill(
                world_state.scenario_description,
                width=72,
                initial_indent="Description: ",
                subsequent_indent=" " * 13,
            )
        )
    lines.extend(
        [
            "",
            "SIMULATION",
            f"Starting cycle: {world_state.current_cycle}",
            format_run_header(world_state),
        ]
    )
    if world_state.scenario_id:
        lines.append(f"Scenario ID: {world_state.scenario_id}")
    for region_state in world_state.regions.values():
        region_definition = registry.get(region_state.definition_id)
        lines.extend(["", "REGION"])
        lines.append(f"Region name: {region_definition["name"]}")
        if region_state.active_weather_id is not None:
            weather_definition = registry.get(region_state.active_weather_id)
            lines.append(f"Weather: {weather_definition['name']}")

        lines.extend(["", "STARTING POPULATIONS"])
        for animal_id, population in sorted(region_state.animal_populations.items()):
            animal_name = registry.get(animal_id)["name"]
            lines.append(format_report_row(animal_name, str(population)))
        total_animals = sum(region_state.animal_populations.values())
        lines.append(format_report_row("Total animals", str(total_animals)))
        diet_lines: list[str] = []
        for animal_id in sorted(region_state.animal_populations):
            animal_definition = registry.get(animal_id)
            ordered_diet = sorted(
                animal_definition.get("diet", []),
                key=lambda entry: entry["preference"],
                reverse=True
            )
            food_names = [
                registry.get(entry["resource_id"])["name"]
                for entry in ordered_diet
            ]
            if not food_names:
                continue
            diet_text = food_names[0]
            if len(food_names) > 1:
                alternatives = ": ".join(
                    f"{name} alternative" for name in food_names[1:]
                )
                diet_text = f"{food_names[0]} preferred; {alternatives}"
            diet_lines.append(
                format_report_row(animal_definition["name"], diet_text)
            )
        if diet_lines:
            lines.extend(["", "DIETS"])
            lines.extend(diet_lines)

        lines.extend(["", "PRODUCERS"])
        for producer_id, population in sorted(region_state.producer_populations.items()):
            producer_name = registry.get(producer_id)["name"]
            lines.append(format_report_row(producer_name, str(population)))

        lines.extend(["", "AVAILABLE RESOURCES"])
        total_biomass = 0.0
        for resource_id, quantity in sorted(region_state.resource_quantities.items()):
            resource_definition = registry.get(resource_id)
            resource_name = resource_definition["name"]
            unit = resource_definition["unit"]
            lines.append(format_report_row(resource_name, f"{format_resource_amount(quantity)} {unit}"))
            if (
                resource_definition["quantity_type"] == "biomass"
                and unit == "kg"
            ):
                total_biomass += quantity
        lines.append(format_report_row("Total available biomass", f"{format_resource_amount(total_biomass)} kg"))

        lines.extend(["", "EXPECTED FOOD DEMAND — NEXT CYCLE"])
        total_demand = 0.0
        for animal_id, population in sorted(region_state.animal_populations.items()):
            animal_definition = registry.get(animal_id)
            animal_name = animal_definition["name"]
            food_demand = calculate_population_food_requirement(
                population,
                animal_definition,
            )
            lines.append(format_report_row(animal_name, f"{format_resource_amount(food_demand)} kg"))
            total_demand += food_demand
        lines.append(format_report_row("Total demand", f"{format_resource_amount(total_demand)} kg"))
        preview_region = deepcopy(region_state)
        apply_producer_production(preview_region, registry)
        preview_feeding = feed_region(preview_region, registry)
        underfed_names = [
            registry.get(animal_id)["name"]
            for animal_id, result in sorted(preview_feeding.items())
            if result.nutrition_ratio < 1.0 
        ]
        lines.extend(["", "INITIAL OUTLOOK — NEXT CYCLE"])
        if not any(region_state.animal_populations.values()):
            lines.append("No animals are present to require food.")
        elif underfed_names:
            lines.append(
                "Food shortages are expected for: "
                + ", ".join(underfed_names)
                + "."
            )
        else:
            lines.append(
                "Enough compatible food is expected for all species."
            )
    return "\n".join(lines)

def format_cycle_report(
    cycle_result: CycleResult,
    registry: ContentRegistry,
) -> str:
    lines = [f"Cycle {cycle_result.cycle_number}"]
    for region_id, region_result in cycle_result.region_results.items():
        region_definition = registry.get(region_id)
        lines.append(region_definition["name"])
        if region_result.active_weather_id is not None:
            weather_definition = registry.get(region_result.active_weather_id)
            lines.append(f"Weather: {weather_definition['name']}")
        if region_result.production_changes:
            lines.extend(["", "PRODUCTION"])
            for resource_id, amount in region_result.production_changes.items():
                resource_definition = registry.get(resource_id)
                resource_name = resource_definition["name"]
                unit = resource_definition["unit"]
                lines.append(format_report_row(resource_name, f"+{format_resource_amount(amount)} {unit}"))
        if region_result.feeding_results:
            lines.extend(["", "FEEDING"])
            for animal_id, feeding_result in region_result.feeding_results.items():
                animal_definition = registry.get(animal_id)
                lines.append(f"{animal_definition['name']} consumed:")
                for resource_id, amount in feeding_result.resource_consumption.items():
                    resource_definition = registry.get(resource_id)
                    resource_name = resource_definition["name"]
                    unit = resource_definition["unit"]
                    lines.append(format_report_row(resource_name, f"{format_resource_amount(amount)} {unit}"))
        shortage_lines: list[str] = []
        for animal_id, feeding_result in region_result.feeding_results.items():
            if feeding_result.nutrition_ratio < 1.0:
                animal_name = registry.get(animal_id)["name"]
                food_percentage = feeding_result.nutrition_ratio * 100
                percentage_text = f"{food_percentage:.1f}%"
                if percentage_text == "100.0%":
                    percentage_text = "less than 100.0%"
                shortage_lines.append(
                    f"{animal_name} received {percentage_text} "
                    "of required food."
                )
        if shortage_lines:
            lines.extend(["", "FOOD SHORTAGES"])
            lines.extend(shortage_lines)
        population_lines: list[str] = []
        animal_ids = sorted(
            region_result.births.keys()
            | region_result.starvation_deaths.keys()
            | region_result.starting_animal_populations.keys()
            | region_result.ending_animal_populations.keys()
        )
        for animal_id in animal_ids:
            births = region_result.births.get(animal_id, 0)
            deaths = region_result.starvation_deaths.get(animal_id, 0)
            changes: list[str] = []
            if births > 0:
                births_label = "birth" if births == 1 else "births"
                changes.append(f"+{births} {births_label}")
            if deaths > 0:
                death_label = "death" if deaths == 1 else "deaths"
                changes.append(f"-{deaths} starvation {death_label}")
            starting_population = region_result.starting_animal_populations.get(
                animal_id
            )
            ending_population = region_result.ending_animal_populations.get(
                animal_id
            )
            if starting_population is not None and ending_population is not None:
                animal_name = registry.get(animal_id)["name"]
                population_lines.append(
                    format_report_row(
                        animal_name,
                        f"{starting_population} → {ending_population}",
                    )
                )
                if changes:
                    population_lines.append(f"  {', '.join(changes)}")
            elif changes:
                animal_name = registry.get(animal_id)["name"]
                population_lines.append(f"{animal_name}:")
                population_lines.append(f"  {', '.join(changes)}")
        if population_lines:
            lines.extend(["", "POPULATION CHANGES"])
            lines.extend(population_lines)
        regional_total_lines: list[str] = []
        resource_ids = sorted(
            region_result.starting_resource_quantities.keys()
            | region_result.ending_resource_quantities.keys()
        )
        for resource_id in resource_ids:
            starting_quantity = region_result.starting_resource_quantities.get(
                resource_id, 0.0
            )
            ending_quantity = region_result.ending_resource_quantities.get(
                resource_id, 0.0
            )
            resource_definition = registry.get(resource_id)
            resource_name = resource_definition["name"]
            unit = resource_definition["unit"]
            regional_total_lines.append(
                format_report_row(
                    resource_name,
                    f"{format_resource_amount(starting_quantity)} → {format_resource_amount(ending_quantity)} {unit}",
                )
            )
        if (
            region_result.starting_animal_populations
            or region_result.ending_animal_populations
        ):
            starting_total = sum(
                region_result.starting_animal_populations.values()
            )
            ending_total = sum(
                region_result.ending_animal_populations.values()
            )
            regional_total_lines.append(
                format_report_row(
                    "Total animals",
                    f"{starting_total} → {ending_total}",
                )
            )
        if regional_total_lines:
            lines.extend(["", "REGIONAL TOTALS"])
            lines.extend(regional_total_lines)
        total_consumption: dict[str, float] = {}
        for feeding_result in region_result.feeding_results.values():
            for resource_id, amount in feeding_result.resource_consumption.items():
                total_consumption[resource_id] = (
                    total_consumption.get(resource_id, 0.0) + amount
                )
        event_lines: list[str] = []
        for resource_id, consumed_amount in total_consumption.items():
            produced_amount = region_result.production_changes.get(
                resource_id, 0.0
            )
            if consumed_amount > produced_amount and not isclose(
                consumed_amount,
                produced_amount,
                rel_tol=1e-12,
                abs_tol=1e-9,
            ):
                resource_name = registry.get(resource_id)["name"]
                event_lines.append(
                    f"! {resource_name} consumption exceeded "
                    f"this cycle's production."
                )
        for resource_id, starting_quantity in (
            region_result.starting_resource_quantities.items()
        ):
            ending_quantity = region_result.ending_resource_quantities.get(
                resource_id
            )
            if starting_quantity > 0.0 and ending_quantity == 0.0:
                resource_name = registry.get(resource_id)["name"]
                event_lines.append(
                    f"! {resource_name} reserves were exhausted this cycle."
                )
        for animal_id, feeding_result in region_result.feeding_results.items():
            animal_definition = registry.get(animal_id)
            ordered_diet = sorted(
                animal_definition.get("diet", []),
                key=lambda entry: entry["preference"],
                reverse=True,
            )
            for diet_entry in ordered_diet[1:]:
                resource_id = diet_entry["resource_id"]
                consumed_amount = feeding_result.resource_consumption.get(
                    resource_id, 0.0
                )
                if consumed_amount > 0.0:
                    animal_name = animal_definition["name"]
                    resource_name = registry.get(resource_id)["name"]
                    event_lines.append(
                        f"! {animal_name} used {resource_name} because "
                        "its preferred food was insufficient."
                    )
        for animal_id, starting_population in (
            region_result.starting_animal_populations.items()
        ):
            ending_population = region_result.ending_animal_populations.get(
                animal_id
            )
            if starting_population > 0 and ending_population == 0:
                animal_name = registry.get(animal_id)["name"]
                region_name = region_definition["name"]
                event_lines.append(
                    f"! {animal_name} died out in {region_name} this cycle."
                )
        if event_lines:
            lines.extend(["", "NOTABLE EVENTS"])
            lines.extend(event_lines)

    return "\n".join(lines)

def export_run_report(
    reports: list[str],
    report_path: Path,
) -> None:
    report_text = "\n\n".join(reports) + "\n"
    report_path.write_text(report_text, encoding="utf-8")