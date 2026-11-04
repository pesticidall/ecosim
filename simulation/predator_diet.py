from collections.abc import Iterable
from dataclasses import dataclass
from random import Random
from math import exp, log
from typing import Any

from simulation.world_state import HabitatState
from simulation.activity import activity_phase_weights, calculate_activity_overlap_modifier
from core.content_registry import ContentRegistry


def validate_animal_attack_method_references(
    animal_definitions: Iterable[dict[str, Any]],
    attack_method_definitions: Iterable[dict[str, Any]],
) -> None:
    """Keep animal method references distinct from traits and temperament."""
    method_ids = {definition["id"] for definition in attack_method_definitions}
    for definition in animal_definitions:
        for field in ("attack_method_id", "counterattack_method_id"):
            if field in definition and definition[field] not in method_ids:
                raise ValueError(
                    f"Animal '{definition['id']}' references unknown {field} "
                    f"'{definition[field]}'."
                )


def validate_animal_prey_references(
    animal_definitions: Iterable[dict[str, Any]],
) -> None:
    """Require every explicit prey target to identify a loaded animal."""
    animals = tuple(animal_definitions)
    animal_ids = {definition["id"] for definition in animals}
    for definition in animals:
        for field in ("prey_diet", "scavenging_diet"):
            for entry in definition.get(field, ()):
                if entry["animal_id"] not in animal_ids:
                    label = "prey" if field == "prey_diet" else "scavenging source"
                    raise ValueError(
                        f"Animal '{definition['id']}' references unknown {label} "
                        f"'{entry['animal_id']}'."
                    )


@dataclass(frozen=True)
class PreyCandidate:
    """Record local availability and dietary preference for one prey species."""

    animal_id: str
    available_population: int
    preference: float
    selection_probability: float
    activity_overlap: float = 1.0


@dataclass(frozen=True)
class PreySelection:
    """Retain candidates and the seeded choice for one hunting attempt."""

    candidates: tuple[PreyCandidate, ...]
    selection_roll: float
    selected_animal_id: str


def select_habitat_prey(
    predator_definition: dict[str, Any],
    habitat: HabitatState,
    random_source: Random,
    *, registry: ContentRegistry | None = None,
) -> PreySelection | None:
    """Choose among validated prey-diet entries present in the local habitat.

    Legacy selection weights only preference. Opt-in activity_abundance weights
    preference by sqrt(local population) and activity overlap, excluding zero
    overlap. Explicit same-species prey requires another animal besides the hunter.
    """
    predator_id = predator_definition["id"]
    encounter_model = predator_definition.get("encounter_model", "preference")
    if encounter_model not in ("preference", "activity_abundance"):
        raise ValueError("Unsupported encounter_model.")
    if encounter_model == "activity_abundance" and registry is None:
        raise ValueError("Activity-aware encounter selection requires content registry.")
    if habitat.animal_populations.get(predator_id, 0) <= 0:
        return None
    available = []
    for entry in sorted(predator_definition.get("prey_diet", ()),
                        key=lambda entry: entry["animal_id"]):
        animal_id = entry["animal_id"]
        population = habitat.animal_populations.get(animal_id, 0)
        if animal_id == predator_id:
            population -= 1
        if population > 0:
            overlap = 1.0
            if encounter_model == "activity_abundance":
                overlap = calculate_activity_overlap_modifier(
                    activity_phase_weights(predator_definition.get("activity_pattern", "flexible")),
                    activity_phase_weights(registry.get(animal_id).get("activity_pattern", "flexible")))
            if overlap > 0:
                available.append((animal_id, population, entry["preference"], overlap))
    if not available:
        return None
    # Scaling first avoids overflowing the sum of finite preference weights.
    # Log weights avoid overflow in preference × sqrt(population) × overlap.
    if encounter_model == "activity_abundance":
        weights = [log(preference) + 0.5 * log(population) + log(overlap)
                   for _, population, preference, overlap in available]
        maximum = max(weights)
        normalized = [exp(weight - maximum) for weight in weights]
    else:
        maximum = max(preference for _, _, preference, _ in available)
        normalized = [preference / maximum for _, _, preference, _ in available]
    total = sum(normalized)
    candidates = tuple(
        PreyCandidate(animal_id, population, preference, weight / total, overlap)
        for (animal_id, population, preference, overlap), weight in zip(available, normalized)
    )
    roll = random_source.random()
    cumulative = 0.0
    selected = candidates[-1].animal_id
    for candidate in candidates:
        cumulative += candidate.selection_probability
        if roll < cumulative:
            selected = candidate.animal_id
            break
    return PreySelection(candidates, roll, selected)
