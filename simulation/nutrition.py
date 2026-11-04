"""Aggregate stored food and recoverable nutritional stress, separate from health."""

from dataclasses import dataclass, replace
from math import isfinite

from simulation.feeding import PopulationFeedingResult, _feed_populations
from simulation.scavenging import ScavengingResult, allocate_habitat_scavenging


ReserveDeposit = tuple[PopulationFeedingResult, ScavengingResult]


@dataclass(frozen=True)
class NutritionalState:
    population: int
    reserve_kg: float = 0.0
    deficit_days: float = 0.0

    def __post_init__(self):
        if isinstance(self.population, bool) or not isinstance(self.population, int) or self.population < 0:
            raise ValueError("Nutritional population must be a nonnegative integer.")
        for value in (self.reserve_kg, self.deficit_days):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
                raise ValueError("Nutritional reserves and deficit must be finite and nonnegative.")
        if not self.population and (self.reserve_kg or self.deficit_days):
            raise ValueError("An empty population cannot retain nutritional state.")


def reconcile_nutrition(state, population):
    """Loss removes proportional reserves; healthy arrivals dilute stress, add no food."""
    if population == 0 or state.population == 0:
        return NutritionalState(population)
    return NutritionalState(population,
                            state.reserve_kg * min(1.0, population / state.population),
                            state.deficit_days * min(1.0, state.population / population))


def reserve_capacity(definition, population):
    return population * definition["food_requirement_per_animal_per_cycle"] / 30 * definition["nutrition"]["reserve_days"]


def update_condition(state, coverage, config, daily_requirement=None):
    if isinstance(coverage, bool) or not isinstance(coverage, (int, float)) or not isfinite(coverage) or not 0 <= coverage <= 1:
        raise ValueError("Nutrition coverage must be normalized.")
    grace = config["starvation_grace_days"]
    if config.get("recovery_requires_food", False) and coverage >= 1 - 1e-12:
        if isinstance(daily_requirement, bool) or not isinstance(daily_requirement, (int, float)) or not isfinite(daily_requirement) or daily_requirement < 0:
            raise ValueError("Food-paid recovery requires a finite nonnegative daily requirement.")
        recovery = (min(state.deficit_days, config["recovery_per_fed_day"], state.reserve_kg / daily_requirement)
                    if daily_requirement > 0 else 0.0)
        return replace(state, deficit_days=max(0.0, state.deficit_days - recovery),
                       reserve_kg=max(0.0, state.reserve_kg - recovery * daily_requirement)), 0.0
    deficit = (max(0.0, state.deficit_days - config["recovery_per_fed_day"])
               if coverage >= 1 - 1e-12 else min(2 * grace, state.deficit_days + 1 - coverage))
    pressure = min(1.0, max(0.0, (deficit - grace) / grace))
    return replace(state, deficit_days=deficit), pressure * (1 - coverage)


def draw_food_reserves(region, registry, local):
    for habitat_id, habitat in region.habitats.items():
        for animal, prior in local[habitat_id].items():
            definition = registry.get(animal)
            if "nutrition" not in definition:
                continue
            population = habitat.animal_populations[animal]
            state = reconcile_nutrition(habitat.nutritional_states.get(animal, NutritionalState(population)), population)
            if state.reserve_kg > reserve_capacity(definition, population) + 1e-9:
                raise ValueError("Stored food exceeds this population's reserve capacity.")
            used = min(state.reserve_kg, max(0.0, prior.required_amount - prior.consumed_amount))
            sources = dict(prior.resource_consumption)
            if used:
                sources["stored_food"] = sources.get("stored_food", 0.0) + used
            consumed = prior.consumed_amount + used
            local[habitat_id][animal] = PopulationFeedingResult(
                prior.required_amount, consumed, min(1.0, consumed / prior.required_amount) if prior.required_amount else 1.0, sources)
            habitat.nutritional_states[animal] = replace(state, reserve_kg=state.reserve_kg - used)


def replenish_food_reserves(region, registry, local) -> dict[str, dict[str, ReserveDeposit]]:
    """Use surplus after daily meals; top-ups are physical intake, not today's nutrition."""
    records = {}
    for habitat_id, habitat in sorted(region.habitats.items()):
        requests, definitions, states = {}, {}, {}
        for animal, population in habitat.animal_populations.items():
            definition = registry.get(animal)
            if "nutrition" not in definition:
                continue
            state = reconcile_nutrition(habitat.nutritional_states.get(animal, NutritionalState(population)), population)
            states[animal] = state
            # Refill only after the population's daily requirement was met.
            requests[animal] = (max(0.0, reserve_capacity(definition, population) - state.reserve_kg)
                                if local[habitat_id][animal].nutrition_ratio >= 1 - 1e-12 else 0.0)
            definitions[animal] = definition
        if not requests:
            continue
        food = _feed_populations({animal: habitat.animal_populations[animal] for animal in requests},
                                 habitat.resource_quantities, registry, required_amounts_override=requests)
        remaining = {}
        for animal, meal in food.items():
            for resource, amount in meal.resource_consumption.items():
                region.resource_quantities[resource] = max(0.0, region.resource_quantities.get(resource, 0) - amount)
            remaining[animal] = max(0.0, requests[animal] - meal.consumed_amount)
        # Explicit scavenging diets govern reserve access too. No implicit
        # eligibility is inferred from a hunting strategy or diet label.
        carrion = allocate_habitat_scavenging(definitions, habitat, remaining)
        records[habitat_id] = {}
        for animal, state in states.items():
            stored = food[animal].consumed_amount + carrion[animal].consumed_biomass_kg
            habitat.nutritional_states[animal] = replace(state, reserve_kg=state.reserve_kg + stored)
            records[habitat_id][animal] = (food[animal], carrion[animal])
    return records
