from math import isfinite
from typing import Any

from simulation.carrion import create_carrion_from_death
from simulation.deaths import DeathCause, DeathRecord, with_age_loss
from simulation.group_conditions import GroupConditionChange, apply_group_condition_changes
from simulation.group_feeding import GroupMeal, feed_hunting_group
from simulation.groups import GroupRole
from simulation.predation import PredationRemains
from simulation.world_state import RegionState
from simulation.growth import plan_growth_loss


def apply_group_predation(
    region: RegionState,
    hunter_change: GroupConditionChange,
    prey_change: GroupConditionChange,
    predator_definition: dict[str, Any],
    prey_definition: dict[str, Any],
    *,
    requested_biomass_kg: float | None = None,
    period_fraction: float = 1.0,
) -> GroupMeal:
    """Commit one context-resolved group kill, survivor injuries, and shared food.

    The caller must explicitly designate the secured prey as a casualty. Group
    condition commits perform the population subtraction; the meal is then
    recorded without invoking the single-animal predation subtraction again.
    """
    hunters, prey = hunter_change.before.group, prey_change.before.group
    if hunters.role is not GroupRole.HUNTING or prey.role is not GroupRole.DEFENSIVE:
        raise ValueError("Group predation requires hunting and defensive group roles.")
    if hunter_change.dead_member_indices:
        raise ValueError("The shared meal requires surviving hunting participants.")
    if len(prey_change.dead_member_indices) != 1:
        raise ValueError("Group predation must designate exactly one prey casualty.")
    if hunters.animal_id != predator_definition["id"] or prey.animal_id != prey_definition["id"]:
        raise ValueError("Predation definitions must match the participating species.")
    if (hunters.region_id, hunters.habitat_id) != (prey.region_id, prey.habitat_id):
        raise ValueError("Group predation participants must share a region and habitat.")
    if hunters.region_id != region.definition_id or hunters.habitat_id not in region.habitats:
        raise ValueError("Group predation habitat must belong to this region.")
    habitat = region.habitats[hunters.habitat_id]
    age_loss = plan_growth_loss(habitat, prey.animal_id, 1)
    units = age_loss.removed_mass_units
    mass = prey_definition["typical_adult_mass_kg"]
    if isinstance(mass, bool) or not isinstance(mass, (int, float)):
        raise TypeError("Prey body mass must be numeric.")
    if not isfinite(mass) or mass <= 0:
        raise ValueError("Prey body mass must be finite and positive.")
    mass *= units
    death = DeathRecord(prey.animal_id, DeathCause.PREDATION, 1, float(mass))
    if "growth" in prey_definition or prey.animal_id in habitat.growth_cohorts or prey.animal_id in habitat.growth_loss_phases:
        death = with_age_loss(death, age_loss)
    remains = PredationRemains(
        death, create_carrion_from_death(death, hunters.habitat_id, hunters.animal_id),
    )
    shared_meal = feed_hunting_group(
        hunters, predator_definition, remains, requested_biomass_kg=requested_biomass_kg,
        period_fraction=period_fraction,
    )
    # Every potentially failing condition/population check occurs before mutation.
    apply_group_condition_changes(region, (hunter_change, prey_change))
    habitat = region.habitats[hunters.habitat_id]
    habitat.predation_meals.append(shared_meal.meal)
    if shared_meal.meal.leftover_carrion.available_biomass_kg > 0:
        habitat.carrion_deposits.append(shared_meal.meal.leftover_carrion)
    return shared_meal
