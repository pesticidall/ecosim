from dataclasses import dataclass
from enum import Enum
from math import ceil, isfinite
from random import Random
from typing import Any

from simulation.feeding import calculate_population_food_requirement
from simulation.world_state import RegionState
from simulation.injuries import Injury, calculate_injury_modifiers
from simulation.condition_cohorts import (
    healthy_population, select_participant_injuries, transition_injury_cohorts,
)


class GroupRole(Enum):
    HUNTING = "hunting"
    DEFENSIVE = "defensive"


@dataclass(frozen=True)
class AnimalGroup:
    """Snapshot one local, same-species group without individual identities."""

    animal_id: str
    region_id: str
    habitat_id: str
    member_count: int
    role: GroupRole

    def __post_init__(self) -> None:
        if isinstance(self.member_count, bool) or not isinstance(self.member_count, int):
            raise TypeError("Group member_count must be an integer.")
        if self.member_count <= 0:
            raise ValueError("Group member_count must be positive.")
        if not isinstance(self.role, GroupRole):
            raise TypeError("Group role must be a GroupRole.")


def form_local_groups(
    region: RegionState,
    habitat_id: str,
    animal_id: str,
    maximum_group_size: int,
    role: GroupRole,
) -> tuple[AnimalGroup, ...]:
    """Partition the current local population using a context-supplied size limit.

    Groups are temporary snapshots, not persistent species traits. Formation
    neither moves animals nor changes populations and consumes no randomness.
    """
    if isinstance(maximum_group_size, bool) or not isinstance(maximum_group_size, int):
        raise TypeError("maximum_group_size must be an integer.")
    if maximum_group_size <= 0:
        raise ValueError("maximum_group_size must be positive.")
    if not isinstance(role, GroupRole):
        raise TypeError("Group role must be a GroupRole.")
    if habitat_id not in region.habitats:
        raise ValueError("Group habitat must belong to the region.")
    population = region.habitats[habitat_id].animal_populations.get(animal_id, 0)
    if isinstance(population, bool) or not isinstance(population, int):
        raise TypeError("Local group population must be an integer.")
    if population < 0:
        raise ValueError("Local group population must not be negative.")
    full_groups, remainder = divmod(population, maximum_group_size)
    sizes = [maximum_group_size] * full_groups
    if remainder:
        sizes.append(remainder)
    return tuple(AnimalGroup(animal_id, region.definition_id, habitat_id, size, role)
                 for size in sizes)


def calculate_defensive_group_size(
    available_population: int,
    maximum_group_size: int,
    nutrition_ratio: float = 1.0,
) -> int:
    """Limit temporary defensive gatherings by local food coverage.

    Initial balance rule: scale the available group ceiling by nutrition,
    rounding up and retaining at least the targeted animal. Hungry animals
    disperse to forage; this neither removes them nor reduces their food demand.
    No food context means the caller's population and capability limits apply.
    """
    for field, value, minimum in (
        ("available_population", available_population, 0),
        ("maximum_group_size", maximum_group_size, 1),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{field} must be an integer.")
        if value < minimum:
            raise ValueError(f"{field} must be at least {minimum}.")
    if isinstance(nutrition_ratio, bool) or not isinstance(nutrition_ratio, (int, float)):
        raise TypeError("nutrition_ratio must be numeric.")
    if not isfinite(nutrition_ratio) or not 0 <= nutrition_ratio <= 1:
        raise ValueError("nutrition_ratio must be finite and between zero and one.")
    ceiling = min(available_population, maximum_group_size)
    return min(ceiling, max(1, ceil(ceiling * nutrition_ratio)))


def calculate_group_food_requirement(
    group: AnimalGroup, animal_definition: dict[str, Any], *, period_fraction: float = 1.0,
) -> float:
    """Count every member's existing per-cycle food demand."""
    if animal_definition["id"] != group.animal_id:
        raise ValueError("Food definition must match the group's species.")
    requirement = calculate_population_food_requirement(
        group.member_count, animal_definition, period_fraction=period_fraction,
    )
    if not isfinite(requirement) or requirement < 0:
        raise ValueError("Group food requirement must be finite and nonnegative.")
    return requirement


@dataclass(frozen=True)
class GroupParticipants:
    """Snapshot distinct participants' condition without persistent identities."""

    group: AnimalGroup
    member_injuries: tuple[tuple[Injury, ...], ...]

    def __post_init__(self) -> None:
        if len(self.member_injuries) != self.group.member_count:
            raise ValueError("Participant injury sets must match group member_count.")


def select_group_participants(
    region: RegionState, group: AnimalGroup, random_source: Random,
) -> GroupParticipants:
    """Sample one group's condition without replacement or world-state changes.

    The returned member indices exist only within this group attempt. Separate
    attempts must resolve against current state before committing their results.
    """
    if group.region_id != region.definition_id or group.habitat_id not in region.habitats:
        raise ValueError("Group must belong to this region and habitat.")
    habitat = region.habitats[group.habitat_id]
    population = habitat.animal_populations.get(group.animal_id, 0)
    cohorts = habitat.injury_cohorts.get(group.animal_id, ())
    healthy_population(population, cohorts)
    if group.member_count > population:
        raise ValueError("Group member_count exceeds available local population.")
    selected = []
    for _ in range(group.member_count):
        injuries = select_participant_injuries(population, cohorts, random_source)
        selected.append(injuries)
        cohorts = transition_injury_cohorts(population, cohorts, injuries, (), survived=False)
        population -= 1
    return GroupParticipants(group, tuple(selected))


GROUP_POWER_EXPONENT = 0.75
MINIMUM_GROUP_COORDINATION = 0.5


@dataclass(frozen=True)
class GroupPower:
    """Expose base Power, participant condition, and coordination inputs."""

    member_count: int
    base_member_power: float
    effective_member_power: float
    intelligence: float
    coordination: float
    group_multiplier: float
    effective_power: float


def calculate_group_power(
    group: AnimalGroup,
    animal_definition: dict[str, Any],
    member_injuries: tuple[tuple[Injury, ...], ...] | None = None,
) -> GroupPower:
    """Apply diminishing group returns to mean condition-adjusted member Power.

    Intelligence affects only the extra contribution of other members, never
    solo Power. The exponent and coordination floor are initial balance rules.
    """
    if animal_definition["id"] != group.animal_id:
        raise ValueError("Power definition must match the group's species.")
    statistics = animal_definition["statistics"]
    power, intelligence = statistics["power"], statistics["intelligence"]
    for field, value in (("power", power), ("intelligence", intelligence)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"Group {field} must be a number.")
        if not isfinite(value) or not 0 <= value <= 10:
            raise ValueError(f"Group {field} must be finite and between zero and ten.")
    if member_injuries is None:
        effective_member_power = float(power)
    else:
        if len(member_injuries) != group.member_count:
            raise ValueError("Member injury sets must match group member_count.")
        effective_member_power = power * sum(
            calculate_injury_modifiers(injuries).power_modifier
            for injuries in member_injuries
        ) / group.member_count
    coordination = MINIMUM_GROUP_COORDINATION + (1 - MINIMUM_GROUP_COORDINATION) * intelligence / 10
    multiplier = 1 + (group.member_count ** GROUP_POWER_EXPONENT - 1) * coordination
    return GroupPower(
        group.member_count, float(power), effective_member_power, float(intelligence),
        coordination, multiplier, effective_member_power * multiplier,
    )
