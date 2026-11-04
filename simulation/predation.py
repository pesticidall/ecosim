from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite
from typing import Any

from simulation.carrion import (
    CarrionConsumption,
    CarrionDeposit,
    consume_carrion,
    create_carrion_from_death,
    release_first_access,
)
from simulation.deaths import DeathRecord, create_predation_death, with_age_loss
from simulation.hunting import HuntResult
from simulation.feeding import PopulationFeedingResult, calculate_population_food_requirement
from simulation.world_state import RegionState
from simulation.growth import plan_growth_loss, commit_growth_loss


@dataclass(frozen=True)
class PredationRemains:
    """Record a secured prey death and its reserved carcass."""

    death: DeathRecord
    carrion: CarrionDeposit


def create_predation_remains(
    hunt_result: HuntResult,
    prey_definition: dict[str, Any],
    predator_id: str,
    habitat_id: str,
    *, age_loss=None,
) -> PredationRemains | None:
    """Create remains only for secured prey, without changing populations.

    The caller applies this result once when committing the hunt to world state.
    """
    death = create_predation_death(hunt_result.outcome, prey_definition)
    if death is None:
        return None
    death = with_age_loss(death, age_loss)
    carrion = create_carrion_from_death(
        death,
        habitat_id=habitat_id,
        first_access_consumer_id=predator_id,
    )
    return PredationRemains(death=death, carrion=carrion)


@dataclass(frozen=True)
class PredationMeal:
    """Record the predator's first meal and released leftover carrion."""

    death: DeathRecord
    consumption: CarrionConsumption
    leftover_carrion: CarrionDeposit


def feed_secured_prey(
    remains: PredationRemains,
    requested_biomass_kg: float,
) -> PredationMeal:
    """Complete the reserved predator's meal, then release first access.

    This returns new records; the caller commits the meal once to world state.
    """
    predator_id = remains.carrion.first_access_consumer_id
    if predator_id is None:
        raise ValueError("Secured prey must retain predator first access before feeding.")
    consumption = consume_carrion(
        remains.carrion, predator_id, requested_biomass_kg,
    )
    leftover_carrion = release_first_access(
        consumption.updated_carrion, predator_id,
    )
    return PredationMeal(
        death=remains.death,
        consumption=consumption,
        leftover_carrion=leftover_carrion,
    )


def summarize_predation_feeding(
    population: int,
    predator_definition: dict[str, Any],
    meals: Iterable[PredationMeal],
    *,
    period_fraction: float = 1.0,
) -> PopulationFeedingResult:
    """Summarize distinct committed meals for one population and reporting period.

    Food requirements and meal biomass use kilograms. Callers supply each meal
    once; this function neither consumes carrion nor changes population state.
    """
    if isinstance(population, bool) or not isinstance(population, int):
        raise TypeError("Predator population must be an integer.")
    required = calculate_population_food_requirement(
        population, predator_definition, period_fraction=period_fraction,
    )
    if not isfinite(required) or required < 0:
        raise ValueError("Predator food requirement must be finite and nonnegative.")
    consumed = 0.0
    sources: dict[str, float] = {}
    for meal in meals:
        if meal.consumption.consumer_id != predator_definition["id"]:
            raise ValueError("Predation meal belongs to a different predator population.")
        amount = meal.consumption.consumed_biomass_kg
        consumed += amount
        source_id = meal.death.animal_id
        sources[source_id] = sources.get(source_id, 0.0) + amount
    nutrition = min(consumed / required, 1.0) if required > 0 else 1.0
    return PopulationFeedingResult(
        required_amount=required,
        consumed_amount=consumed,
        nutrition_ratio=nutrition,
        resource_consumption=sources,
    )


def apply_predation_meal(region: RegionState, meal: PredationMeal) -> None:
    """Commit one meal to its habitat after validating population availability."""
    habitat_id = meal.leftover_carrion.habitat_id
    if habitat_id not in region.habitats:
        raise ValueError(f"Unknown predation habitat '{habitat_id}'.")
    habitat = region.habitats[habitat_id]
    if any(existing is meal for existing in habitat.predation_meals):
        raise ValueError("This predation meal has already been applied.")
    prey_id = meal.death.animal_id
    predator_id = meal.consumption.consumer_id
    if habitat.animal_populations.get(predator_id, 0) <= 0:
        raise ValueError("Predation requires a living predator in the habitat.")
    if meal.death.count != 1:
        raise ValueError("A single hunt must record exactly one prey death.")
    if habitat.animal_populations.get(prey_id, 0) < meal.death.count:
        raise ValueError("Predation requires available prey in the habitat.")
    growth_loss = plan_growth_loss(habitat, prey_id, meal.death.count)
    commit_growth_loss(habitat, prey_id, growth_loss)
    habitat.animal_populations[prey_id] -= meal.death.count
    region.animal_populations[prey_id] = sum(
        local.animal_populations.get(prey_id, 0)
        for local in region.habitats.values()
    )
    habitat.predation_meals.append(meal)
    if meal.leftover_carrion.available_biomass_kg > 0:
        habitat.carrion_deposits.append(meal.leftover_carrion)
