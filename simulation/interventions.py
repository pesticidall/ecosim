from dataclasses import dataclass
from math import isfinite

from core.content_registry import ContentRegistry
from simulation.calendar import Month
from simulation.world_state import WorldState
from simulation.intervention_resources import (
    FeedType, InterventionResources, reserve_supplementary_food, supplementary_food_cost,
    reserve_population_removal, REMOVAL_IC_COST,
    reserve_population_introduction, INTRODUCTION_IC_COST,
)
from simulation.condition_cohorts import InjuryCohort, cohorts_after_population_loss, healthy_population
from simulation.nutrition import NutritionalState, reconcile_nutrition
from simulation.growth import plan_growth_loss, commit_growth_loss


MAX_POPULATION_ACTION_QUANTITY = 10


@dataclass(frozen=True)
class SupplementaryFoodIntervention:
    year: int
    month: Month
    day: int
    region_id: str
    habitat_id: str
    resource_id: str
    amount_kg: float
    event_id: str
    feed_type: FeedType
    ic_spent: float
    resources_before: InterventionResources
    resources_after: InterventionResources


@dataclass(frozen=True)
class PopulationRemovalIntervention:
    year: int
    month: Month
    day: int
    region_id: str
    habitat_id: str
    animal_id: str
    quantity: int
    event_id: str
    ic_spent: float
    charge_spent: int
    resources_before: InterventionResources
    resources_after: InterventionResources
    local_population_before: int
    local_population_after: int


@dataclass(frozen=True)
class PopulationIntroductionIntervention:
    year: int
    month: Month
    day: int
    region_id: str
    habitat_id: str
    animal_id: str
    quantity: int
    event_id: str
    ic_spent: float
    charge_spent: int
    resources_before: InterventionResources
    resources_after: InterventionResources
    local_population_before: int
    local_population_after: int


@dataclass(frozen=True)
class PopulationIntroductionQuote:
    quantity: int
    local_before: int
    local_after: int
    regional_after: int
    resources_after: InterventionResources
    nutrition_after: NutritionalState | None = None


InterventionRecord = SupplementaryFoodIntervention | PopulationRemovalIntervention | PopulationIntroductionIntervention


@dataclass(frozen=True)
class PopulationRemovalQuote:
    quantity: int
    local_before: int
    local_after: int
    regional_after: int
    cohorts_after: tuple[InjuryCohort, ...]
    resources_after: InterventionResources
    nutrition_after: NutritionalState | None = None


@dataclass(frozen=True)
class SupplementaryFoodQuote:
    feed_type: FeedType
    amount_kg: float
    ic_cost: float
    resources_before: InterventionResources
    resources_after: InterventionResources
    local_quantity_after: float
    regional_quantity_after: float


def supplementary_food_options(world: WorldState, registry: ContentRegistry, region_id: str, habitat_id: str) -> tuple[str, ...]:
    habitat = world.regions[region_id].habitats[habitat_id]
    edible = {entry["resource_id"] for animal_id, count in habitat.animal_populations.items() if count > 0
              for entry in registry.get(animal_id).get("diet", ())}
    return tuple(sorted(resource_id for resource_id in edible
                        if registry.get(resource_id).get("entity_type") == "resource"
                        and registry.get(resource_id).get("quantity_type") == "biomass"
                        and registry.get(resource_id).get("unit") == "kg"
                        and registry.get(resource_id).get("supplementary_feed_type") in ("herbivore", "carnivore")))


def _valid_biomass(value, field, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field} must be numeric.")
    if not isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError(f"{field} must be finite and {'positive' if positive else 'nonnegative'}.")


def preview_supplementary_food(
    world: WorldState, registry: ContentRegistry, region_id: str,
    habitat_id: str, resource_id: str, amount_kg: float,
) -> SupplementaryFoodQuote:
    """Validate an entire deployment and quote its outcome without mutation."""
    _valid_biomass(amount_kg, "Supplementary food amount", positive=True)
    cost = supplementary_food_cost(amount_kg)
    year, month, day = world.calendar.year, world.calendar.month, world.calendar.day
    if day in world.daily_history.get(year, {}).get(month, {}) or month in world.monthly_history.get(year, {}):
        raise ValueError("Supplementary food requires an unresolved calendar date.")
    if region_id not in world.regions or habitat_id not in world.regions[region_id].habitats:
        raise ValueError("Select a habitat belonging to this world.")
    if resource_id not in supplementary_food_options(world, registry, region_id, habitat_id):
        raise ValueError("Select tagged kilogram biomass food compatible with a living local population.")
    feed_type = FeedType(registry.get(resource_id)["supplementary_feed_type"])
    resources_after = reserve_supplementary_food(world.intervention_resources, feed_type, amount_kg)
    region = world.regions[region_id]
    habitat = region.habitats[habitat_id]
    local = habitat.resource_quantities.get(resource_id, 0.0)
    regional = region.resource_quantities.get(resource_id, 0.0)
    _valid_biomass(local, "Local resource quantity")
    _valid_biomass(regional, "Regional resource quantity")
    updated_local, updated_region = local + amount_kg, regional + amount_kg
    _valid_biomass(updated_local, "Updated local quantity")
    _valid_biomass(updated_region, "Updated regional quantity")
    if updated_local <= local or updated_region <= regional:
        raise ValueError("Food amount is too small for the precision of existing resource quantities.")
    return SupplementaryFoodQuote(feed_type, float(amount_kg), cost, world.intervention_resources,
                                  resources_after, updated_local, updated_region)


def add_supplementary_food(
    world: WorldState, registry: ContentRegistry, region_id: str,
    habitat_id: str, resource_id: str, amount_kg: float,
) -> SupplementaryFoodIntervention:
    """Commit the IC debit, stock debit, deposit, and record atomically.

    A fresh quote is validated on every commit; an older UI preview cannot
    authorize spending balances that have since changed. No randomness is used.
    """
    quote = preview_supplementary_food(world, registry, region_id, habitat_id, resource_id, amount_kg)
    date = world.calendar
    record = SupplementaryFoodIntervention(
        date.year, date.month, date.day, region_id, habitat_id, resource_id, quote.amount_kg,
        f"intervention_{len(world.interventions) + 1:06d}", quote.feed_type, quote.ic_cost,
        quote.resources_before, quote.resources_after,
    )
    world.regions[region_id].habitats[habitat_id].resource_quantities[resource_id] = quote.local_quantity_after
    world.regions[region_id].resource_quantities[resource_id] = quote.regional_quantity_after
    world.intervention_resources = quote.resources_after
    world.interventions.append(record)
    return record


def preview_population_removal(
    world: WorldState, registry: ContentRegistry, region_id: str, habitat_id: str, animal_id: str,
    quantity: int,
) -> PopulationRemovalQuote:
    """Quote the requested whole-animal quantity without mutation or randomness."""
    date = world.calendar
    if date.day in world.daily_history.get(date.year, {}).get(date.month, {}) or date.month in world.monthly_history.get(date.year, {}):
        raise ValueError("Population removal requires an unresolved calendar date.")
    if region_id not in world.regions or habitat_id not in world.regions[region_id].habitats:
        raise ValueError("Select a habitat belonging to this world.")
    definition = registry.get(animal_id)
    if definition.get("entity_type") != "animal":
        raise ValueError("Population removal requires an animal species.")
    _validate_population_quantity(quantity)
    region = world.regions[region_id]
    habitat = region.habitats[habitat_id]
    population = habitat.animal_populations.get(animal_id, 0)
    if isinstance(population, bool) or not isinstance(population, int) or population < quantity:
        raise ValueError(f"Removal requires {quantity} local animals; only {population} are available.")
    regional = region.animal_populations.get(animal_id, 0)
    if (isinstance(regional, bool) or not isinstance(regional, int)
            or regional != sum(item.animal_populations.get(animal_id, 0) for item in region.habitats.values())):
        raise ValueError("Regional population does not match its habitat totals.")
    cohorts = cohorts_after_population_loss(population, habitat.injury_cohorts.get(animal_id, ()), quantity)
    resources = reserve_population_removal(world.intervention_resources)
    nutritional = habitat.nutritional_states.get(animal_id)
    nutritional = reconcile_nutrition(nutritional, population - quantity) if nutritional is not None else None
    return PopulationRemovalQuote(quantity, population, population - quantity, regional - quantity, cohorts, resources, nutritional)


def remove_population(
    world: WorldState, registry: ContentRegistry, region_id: str, habitat_id: str, animal_id: str,
    quantity: int,
) -> PopulationRemovalIntervention:
    """Remove the requested quantity from the simulation, creating no remains.

    Injury cohorts use deterministic proportional population-loss allocation.
    Partial removal retains aggregate fractional demographic carry; local
    extinction clears it. The caller owns presentation pause controls.
    """
    quote = preview_population_removal(world, registry, region_id, habitat_id, animal_id, quantity)
    date = world.calendar
    record = PopulationRemovalIntervention(
        date.year, date.month, date.day, region_id, habitat_id, animal_id, quote.quantity,
        f"intervention_{len(world.interventions) + 1:06d}", REMOVAL_IC_COST, 1,
        world.intervention_resources, quote.resources_after, quote.local_before, quote.local_after,
    )
    habitat = world.regions[region_id].habitats[habitat_id]
    growth_loss = plan_growth_loss(habitat, animal_id, quote.quantity)
    commit_growth_loss(habitat, animal_id, growth_loss)
    habitat.animal_populations[animal_id] = quote.local_after
    world.regions[region_id].animal_populations[animal_id] = quote.regional_after
    if animal_id in habitat.injury_cohorts:
        habitat.injury_cohorts[animal_id] = quote.cohorts_after
    if quote.local_after == 0:
        habitat.demographic_carry.pop(animal_id, None)
        habitat.nutritional_states.pop(animal_id, None)
    elif quote.nutrition_after is not None:
        habitat.nutritional_states[animal_id] = quote.nutrition_after
    world.intervention_resources = quote.resources_after
    world.interventions.append(record)
    return record


def preview_population_introduction(
    world: WorldState, registry: ContentRegistry, region_id: str, habitat_id: str, animal_id: str,
    quantity: int,
) -> PopulationIntroductionQuote:
    """Quote healthy arrivals into an explicitly preferred habitat; never mutate."""
    date = world.calendar
    if date.day in world.daily_history.get(date.year, {}).get(date.month, {}) or date.month in world.monthly_history.get(date.year, {}):
        raise ValueError("Population introduction requires an unresolved calendar date.")
    if region_id not in world.regions or habitat_id not in world.regions[region_id].habitats:
        raise ValueError("Select a habitat belonging to this world.")
    definition = registry.get(animal_id)
    if definition.get("entity_type") != "animal":
        raise ValueError("Population introduction requires an animal species.")
    _validate_population_quantity(quantity)
    if habitat_id not in definition.get("preferred_habitat_ids", ()):
        raise ValueError("Population introduction requires a preferred habitat for this species.")
    region = world.regions[region_id]
    habitat = region.habitats[habitat_id]
    counts = [item.animal_populations.get(animal_id, 0) for item in region.habitats.values()]
    regional = region.animal_populations.get(animal_id, 0)
    if any(isinstance(count, bool) or not isinstance(count, int) or count < 0 for count in counts):
        raise ValueError("Habitat populations must be nonnegative integers.")
    if isinstance(regional, bool) or not isinstance(regional, int) or regional != sum(counts):
        raise ValueError("Regional population does not match its habitat totals.")
    population = habitat.animal_populations.get(animal_id, 0)
    healthy_population(population, habitat.injury_cohorts.get(animal_id, ()))
    resources = reserve_population_introduction(world.intervention_resources)
    nutritional = habitat.nutritional_states.get(animal_id)
    nutritional = reconcile_nutrition(nutritional, population + quantity) if nutritional is not None else None
    return PopulationIntroductionQuote(quantity, population, population + quantity, regional + quantity, resources, nutritional)


def introduce_population(
    world: WorldState, registry: ContentRegistry, region_id: str, habitat_id: str, animal_id: str,
    quantity: int,
) -> PopulationIntroductionIntervention:
    """Commit a fresh validated quantity; arrivals are healthy, not births."""
    quote = preview_population_introduction(world, registry, region_id, habitat_id, animal_id, quantity)
    date = world.calendar
    record = PopulationIntroductionIntervention(
        date.year, date.month, date.day, region_id, habitat_id, animal_id, quote.quantity,
        f"intervention_{len(world.interventions) + 1:06d}", INTRODUCTION_IC_COST, 1,
        world.intervention_resources, quote.resources_after, quote.local_before, quote.local_after,
    )
    habitat = world.regions[region_id].habitats[habitat_id]
    habitat.animal_populations[animal_id] = quote.local_after
    world.regions[region_id].animal_populations[animal_id] = quote.regional_after
    if quote.local_before == 0:
        habitat.demographic_carry.pop(animal_id, None)
    if quote.nutrition_after is not None:
        habitat.nutritional_states[animal_id] = quote.nutrition_after
    world.intervention_resources = quote.resources_after
    world.interventions.append(record)
    return record


def _validate_population_quantity(quantity: int) -> None:
    if isinstance(quantity, bool) or not isinstance(quantity, int):
        raise TypeError("Animal quantity must be an integer.")
    if not 1 <= quantity <= MAX_POPULATION_ACTION_QUANTITY:
        raise ValueError(f"Animal quantity must be between 1 and {MAX_POPULATION_ACTION_QUANTITY}.")
