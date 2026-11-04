from core.content_registry import ContentRegistry
from simulation.monthly_summary import MonthlyEcologySummary
from simulation.reporting import format_resource_amount
from simulation.intervention_reporting import format_intervention


def _count(value: int, label: str) -> str:
    return f"{value} {label}{'' if value == 1 else 's'}"


def format_monthly_ecology_report(summary: MonthlyEcologySummary, registry: ContentRegistry) -> str:
    """Present completed daily evidence as a monthly review."""
    lines = [f"{summary.month.display_name}, Year {summary.year} ({len(summary.days)} completed days)"]
    for region_id, region in sorted(summary.region_results.items()):
        lines.extend(["", registry.get(region_id)["name"], "WEATHER"])
        for weather_id, count in sorted(region.weather_day_totals.items(), key=lambda item: item[0] or ""):
            name = registry.get(weather_id)["name"] if weather_id is not None else "Unspecified weather"
            lines.append(f"{name}: {count} days.")
        interventions = [record for day in summary.days for record in day.interventions if record.region_id == region_id]
        if interventions:
            lines.extend(["INTERVENTIONS", *(format_intervention(record, registry) for record in interventions)])
        lines.append("POPULATIONS")
        for animal_id in sorted(region.starting_state.animal_populations.keys() | region.ending_state.animal_populations.keys()):
            lines.append(
                f"{registry.get(animal_id)['name']}: {region.starting_state.animal_populations.get(animal_id, 0)} → "
                f"{region.ending_state.animal_populations.get(animal_id, 0)}; "
                f"{_count(region.births.get(animal_id, 0), 'birth')}; "
                f"{_count(region.starvation_deaths.get(animal_id, 0), 'starvation death')}; "
                f"{_count(region.predation_deaths.get(animal_id, 0), 'predation death')}"
                + (f"; {region.removals[animal_id]} removed" if region.removals.get(animal_id, 0) else "")
                + (f"; {region.introductions[animal_id]} introduced" if region.introductions.get(animal_id, 0) else "") + "."
            )
        if region.feeding_results:
            lines.append("FOOD COVERAGE")
            for animal_id, feeding in sorted(region.feeding_results.items()):
                lines.append(f"{registry.get(animal_id)['name']}: {feeding.nutrition_ratio:.1%} of required food.")
        states = [(habitat_id, animal, state) for habitat_id, animals in region.ending_state.nutritional_states.items()
                  for animal, state in animals.items() if state.population]
        if states:
            lines.append("NUTRITION AT MONTH END")
            for habitat_id, animal, state in sorted(states):
                lines.append(f"{registry.get(habitat_id)['name']} / {registry.get(animal)['name']}: "
                             f"{state.reserve_kg:.2f} kg stored food; {state.deficit_days:.2f} deficit-days.")
        recovery = {}
        for day in summary.days:
            for animal, amount in day.region_results[region_id].demographics.condition_recovery_kg.items():
                recovery[animal] = recovery.get(animal, 0.0) + amount
        if any(amount > 0 for amount in recovery.values()):
            lines.append("CONDITION RECOVERY")
            for animal, amount in sorted(recovery.items()):
                if amount > 0:
                    lines.append(f"{registry.get(animal)['name']}: {amount:.2f} kg stored food used.")
        growth_food = {}
        for day in summary.days:
            for meals in day.region_results[region_id].food_web.growth_meals.values():
                for animal, meal in meals.items():
                    required, consumed = growth_food.get(animal, (0.0, 0.0))
                    growth_food[animal] = (required + meal.feeding.required_amount, consumed + meal.feeding.consumed_amount)
        if any(required for required, _ in growth_food.values()):
            lines.append("JUVENILE GROWTH FOOD")
            for animal, (required, consumed) in sorted(growth_food.items()):
                if required:
                    lines.append(f"{registry.get(animal)['name']}: {consumed:.2f} / {required:.2f} kg consumed for growth.")
        lines.append("RESOURCES")
        for resource_id in sorted(region.resource_consumption):
            definition = registry.get(resource_id)
            lines.append(
                f"{definition['name']}: +{format_resource_amount(region.production_changes.get(resource_id, 0.0))} "
                f"{definition['unit']} produced; {format_resource_amount(region.resource_consumption[resource_id])} "
                f"{definition['unit']} consumed; {format_resource_amount(region.ending_state.resource_quantities.get(resource_id, 0.0))} "
                f"{definition['unit']} remaining."
            )
        for habitat_id, predators in sorted(region.hunt_outcomes.items()):
            for predator_id, outcomes in sorted(predators.items()):
                if outcomes:
                    counts = ", ".join(f"{count} {status.replace('_', ' ')}" for status, count in sorted(outcomes.items()))
                    lines.append(f"{registry.get(habitat_id)['name']} / {registry.get(predator_id)['name']}: {counts}.")
        for habitat_id in sorted(region.ending_state.carrion.keys() | region.decayed_biomass_kg.keys()):
            remaining = sum(deposit.available_biomass_kg for deposit in region.ending_state.carrion.get(habitat_id, ()))
            scavenged = sum(region.scavenged_biomass_kg.get(habitat_id, {}).values())
            decayed = region.decayed_biomass_kg.get(habitat_id, 0.0)
            if remaining or scavenged or decayed:
                lines.append(
                    f"{registry.get(habitat_id)['name']}: {format_resource_amount(scavenged)} kg scavenged; "
                    f"{format_resource_amount(decayed)} kg decayed; {format_resource_amount(remaining)} kg carrion remaining."
                )
    return "\n".join(lines)
