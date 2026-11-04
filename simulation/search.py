"""Bounded local-abundance encounter budgets, separate from hunt-stage success."""

from dataclasses import dataclass
from math import floor, fsum, isfinite
from simulation.activity import activity_phase_weights, calculate_activity_overlap_modifier


@dataclass(frozen=True)
class SearchBudget:
    eligible_prey: float
    reference_prey: float
    maximum_member_opportunities: int
    expected_member_opportunities: float
    allocated_member_opportunities: int
    rounding_roll: float | None


def resolve_search_budget(predator, habitat, registry, random_source):
    config = predator["search_budget"]
    reference, maximum = config["reference_prey"], config["max_opportunities"]
    if isinstance(reference, bool) or not isinstance(reference, (int, float)) or not isfinite(reference) or reference <= 0:
        raise ValueError("Search reference_prey must be finite and positive.")
    if isinstance(maximum, bool) or not isinstance(maximum, int) or not 1 <= maximum <= 8:
        raise ValueError("Search max_opportunities must be an integer between 1 and 8.")
    population = habitat.animal_populations.get(predator["id"], 0)
    if isinstance(population, bool) or not isinstance(population, int) or population < 0:
        raise ValueError("Searching population must be a nonnegative integer.")
    cap = population * maximum
    if not cap:
        return SearchBudget(0, reference, 0, 0, 0, None)
    available = []
    for entry in sorted(predator.get("prey_diet", ()), key=lambda entry: entry["animal_id"]):
        animal = entry["animal_id"]
        count = habitat.animal_populations.get(animal, 0)
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("Local prey populations must be nonnegative integers.")
        count -= int(animal == predator["id"])
        if count > 0:
            overlap = calculate_activity_overlap_modifier(
                activity_phase_weights(predator.get("activity_pattern", "flexible")),
                activity_phase_weights(registry.get(animal).get("activity_pattern", "flexible")))
            available.append(count * overlap)
    eligible = fsum(available)
    expected = cap / (1 + reference / eligible) if eligible else 0.0
    whole = floor(expected)
    fraction = expected - whole
    roll = random_source.random() if fraction > 1e-12 else None
    allocated = min(cap, whole + int(roll is not None and roll < fraction))
    return SearchBudget(eligible, reference, cap, expected, allocated, roll)
