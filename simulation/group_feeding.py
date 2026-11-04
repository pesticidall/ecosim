from dataclasses import dataclass
from math import isfinite
from typing import Any

from simulation.feeding import PopulationFeedingResult
from simulation.groups import AnimalGroup, GroupRole, calculate_group_food_requirement
from simulation.predation import (
    PredationMeal, PredationRemains, feed_secured_prey, summarize_predation_feeding,
)


@dataclass(frozen=True)
class GroupMeal:
    """Record a single carcass meal shared equally by the hunting unit."""

    group: AnimalGroup
    meal: PredationMeal
    feeding: PopulationFeedingResult
    consumed_per_member_kg: float


def feed_hunting_group(
    group: AnimalGroup,
    animal_definition: dict[str, Any],
    remains: PredationRemains,
    *,
    requested_biomass_kg: float | None = None,
    period_fraction: float = 1.0,
) -> GroupMeal:
    """Feed all participating hunters from one kill without duplicating biomass.

    Equal shares are an initial allocation rule. The caller commits the single
    returned meal once, rather than recording one prey death per group member.
    """
    if group.role is not GroupRole.HUNTING:
        raise ValueError("Only a hunting unit can share its secured prey meal.")
    if group.habitat_id != remains.carrion.habitat_id:
        raise ValueError("Hunting group and carcass must share a habitat.")
    if remains.carrion.first_access_consumer_id != group.animal_id:
        raise ValueError("Carcass first access must belong to the hunting group species.")
    demand = calculate_group_food_requirement(group, animal_definition, period_fraction=period_fraction)
    if requested_biomass_kg is not None:
        if isinstance(requested_biomass_kg, bool) or not isinstance(requested_biomass_kg, (int, float)):
            raise TypeError("Requested group meal biomass must be numeric.")
        if not isfinite(requested_biomass_kg) or requested_biomass_kg < 0:
            raise ValueError("Requested group meal biomass must be finite and nonnegative.")
        demand = min(demand, requested_biomass_kg)
    meal = feed_secured_prey(remains, demand)
    feeding = summarize_predation_feeding(
        group.member_count, animal_definition, (meal,), period_fraction=period_fraction,
    )
    return GroupMeal(
        group=group,
        meal=meal,
        feeding=feeding,
        consumed_per_member_kg=meal.consumption.consumed_biomass_kg / group.member_count,
    )
