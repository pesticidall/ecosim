from dataclasses import dataclass

from core.content_registry import ContentRegistry
from simulation.calendar import Month
from simulation.daily_cycle import DailyCycleResult
from simulation.group_hunting import GroupHuntResult
from simulation.reporting import format_hunt_details, format_resource_amount
from simulation.intervention_reporting import format_intervention


HISTORY_CATEGORIES = (
    "All events", "Weather", "Interventions", "Populations", "Food coverage",
    "Hunts", "Injuries", "Resources", "Carrion",
)


@dataclass(frozen=True)
class HistoryEntry:
    kind: str
    year: int
    month: Month
    day: int = 0

    @property
    def label(self) -> str:
        if self.kind == "month":
            return f"{self.month.display_name}, Year {self.year} · month report"
        return f"{self.day} {self.month.display_name}, Year {self.year}"


def _count(value: int, label: str) -> str:
    return f"{value} {label}{'' if value == 1 else 's'}"


def format_daily_history(result: DailyCycleResult, registry: ContentRegistry, category: str = "All events") -> str:
    """Explain retained daily evidence without consulting live world state."""
    if category not in HISTORY_CATEGORIES:
        raise ValueError("Unknown history category.")
    def includes(name):
        return category in ("All events", name)

    lines = [f"{result.day} {result.month.display_name}, Year {result.year} completed."]
    if category != "All events":
        lines.append(f"Category: {category}")
    for region_id, local in sorted(result.region_results.items()):
        weather = registry.get(local.active_weather_id)["name"] if local.active_weather_id else "Unspecified"
        lines.extend(["", registry.get(region_id)["name"]])
        if includes("Weather"):
            lines.append(f"Weather: {weather}")
        if includes("Interventions"):
            lines.extend(format_intervention(record, registry) for record in result.interventions if record.region_id == region_id)
        for animal_id in sorted(local.demographics.births.keys() | local.demographics.starvation_deaths.keys()):
            born = local.demographics.births.get(animal_id, 0)
            died = local.demographics.starvation_deaths.get(animal_id, 0)
            if includes("Populations") and (born or died):
                lines.append(f"{registry.get(animal_id)['name']}: {_count(born, 'birth')}; {_count(died, 'starvation death')}.")
        for animal_id, feeding in sorted(local.food_web.regional_feeding.items()):
            if includes("Food coverage") and feeding.nutrition_ratio < 1:
                lines.append(f"{registry.get(animal_id)['name']}: {feeding.nutrition_ratio:.1%} food coverage.")
        for habitat_id, rounds in sorted(local.food_web.hunting_rounds.items()):
            for predator_id, hunting in sorted(rounds.items()):
                if includes("Hunts") and hunting.search is not None:
                    search = hunting.search
                    lines.append(f"{registry.get(habitat_id)['name']} / {registry.get(predator_id)['name']} search: eligible prey {search.eligible_prey:.2f}; "
                                 f"expected {search.expected_member_opportunities:.2f}, allocated {search.allocated_member_opportunities} member opportunities.")
                for attempt in hunting.attempts:
                    if includes("Hunts"):
                        lines.extend(["", registry.get(habitat_id)["name"], format_hunt_details(attempt, registry)])
                    if isinstance(attempt.hunt, GroupHuntResult):
                        contacts = ((attempt.hunt.contact_injury, attempt.prey_selection.selected_animal_id),
                                    (attempt.hunt.counterattack_injury, attempt.predator_id))
                        injuries = [(animal_id, contact.injury) for contact, animal_id in contacts
                                    if contact is not None and contact.injury is not None]
                    else:
                        injuries = []
                        for animal_id, before, after in (
                            (attempt.predator_id, attempt.predator_starting_injuries, attempt.hunt.contact.predator_injuries),
                            (attempt.prey_selection.selected_animal_id, attempt.prey_starting_injuries, attempt.hunt.contact.prey_injuries),
                        ):
                            injuries.extend((animal_id, injury) for injury in after[len(before):])
                    if includes("Injuries"):
                        for animal_id, injury in injuries:
                            lines.append(f"New injury: {registry.get(animal_id)['name']} · {injury.severity.value} ({injury.source_stage}).")
                for meal in hunting.meals:
                    if includes("Populations"):
                        lines.append(f"{registry.get(meal.death.animal_id)['name']}: {_count(meal.death.count, 'predation death')}.")
        for resource_id in sorted(local.starting_state.resource_quantities.keys() | local.ending_state.resource_quantities.keys()):
            if not includes("Resources"):
                continue
            definition = registry.get(resource_id)
            before = local.starting_state.resource_quantities.get(resource_id, 0.0)
            after = local.ending_state.resource_quantities.get(resource_id, 0.0)
            produced = local.production_changes.get(resource_id, 0.0)
            lines.append(f"{definition['name']}: {format_resource_amount(before)} → {format_resource_amount(after)} "
                         f"{definition['unit']}; +{format_resource_amount(produced)} produced.")
        for habitat_id in sorted(local.ending_state.carrion.keys() | local.carrion_decay.keys()):
            scavenged = sum(item.consumed_biomass_kg for item in local.food_web.scavenging_results.get(habitat_id, {}).values())
            scavenged += sum(carrion.consumed_biomass_kg for _, carrion in local.food_web.reserve_deposits.get(habitat_id, {}).values())
            scavenged += sum(meal.carrion.consumed_biomass_kg for meal in local.food_web.growth_meals.get(habitat_id, {}).values())
            decayed = sum(item.decayed_biomass_kg for item in local.carrion_decay.get(habitat_id, ()))
            remaining = sum(item.available_biomass_kg for item in local.ending_state.carrion.get(habitat_id, ()))
            if includes("Carrion") and (scavenged or decayed or remaining):
                lines.append(f"{registry.get(habitat_id)['name']}: {format_resource_amount(scavenged)} kg scavenged; "
                             f"{format_resource_amount(decayed)} kg decayed; {format_resource_amount(remaining)} kg carrion remaining.")
        if includes("Food coverage"):
            for habitat_id, meals in local.food_web.growth_meals.items():
                for animal_id, meal in sorted(meals.items()):
                    if meal.feeding.required_amount:
                        lines.append(f"{registry.get(animal_id)['name']}: {meal.feeding.consumed_amount:.2f} / "
                                     f"{meal.feeding.required_amount:.2f} kg juvenile growth food.")
            for animal_id, amount in sorted(local.demographics.condition_recovery_kg.items()):
                if amount > 0:
                    lines.append(f"{registry.get(animal_id)['name']}: {amount:.2f} kg stored food used for condition recovery.")
            for habitat_id, states in sorted(local.ending_state.nutritional_states.items()):
                for animal_id, state in sorted(states.items()):
                    if state.population:
                        lines.append(f"{registry.get(habitat_id)['name']} / {registry.get(animal_id)['name']}: "
                                     f"{state.reserve_kg:.2f} kg stored food; {state.deficit_days:.2f} deficit-days.")
        for habitat_id, animals in sorted(local.ending_state.injury_cohorts.items()):
            for animal_id, cohorts in sorted(animals.items()):
                injured = sum(cohort.count for cohort in cohorts)
                if includes("Injuries") and injured:
                    lines.append(f"{registry.get(habitat_id)['name']} / {registry.get(animal_id)['name']}: {injured} injured at day end.")
    if category != "All events" and len(lines) == 2 + 2 * len(result.region_results):
        lines.append("No matching recorded activity.")
    return "\n".join(lines)
