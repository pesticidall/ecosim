from collections.abc import Iterable
from dataclasses import dataclass, fields
from typing import Any

from simulation.groups import GroupParticipants, GroupPower, GroupRole, calculate_group_power
from simulation.hunting import DetentionScores, calculate_detention_scores
from simulation.injuries import calculate_injury_modifiers


@dataclass(frozen=True)
class GroupDetentionScores(DetentionScores):
    """Retain coordinated restraint and condition-adjusted companion support."""

    hunting_power: GroupPower | None = None
    defensive_support: float = 1.0
    target_member_index: int = 0


def calculate_group_detention_scores(
    hunters: GroupParticipants,
    prey: GroupParticipants,
    predator_definition: dict[str, Any],
    prey_definition: dict[str, Any],
    target_member_index: int,
    taxon_definitions: Iterable[dict[str, Any]] | None = None,
    trait_definitions: Iterable[dict[str, Any]] = (),
) -> GroupDetentionScores:
    """Calculate restraint of one prey using updated participant condition."""
    if hunters.group.role is not GroupRole.HUNTING or prey.group.role is not GroupRole.DEFENSIVE:
        raise ValueError("Group detention requires hunting and defensive roles.")
    if (hunters.group.region_id, hunters.group.habitat_id) != (prey.group.region_id, prey.group.habitat_id):
        raise ValueError("Detention participants must share a region and habitat.")
    if isinstance(target_member_index, bool) or not isinstance(target_member_index, int):
        raise TypeError("Detention target index must be an integer.")
    if not 0 <= target_member_index < prey.group.member_count:
        raise ValueError("Detention target index must identify an existing participant.")
    hunting_power = calculate_group_power(hunters.group, predator_definition, hunters.member_injuries)
    defensive_power = calculate_group_power(prey.group, prey_definition, prey.member_injuries)
    base = calculate_detention_scores(
        predator_definition, prey_definition, (), prey.member_injuries[target_member_index],
        taxon_definitions=taxon_definitions, trait_definitions=trait_definitions,
    )
    hunter_condition = sum(calculate_injury_modifiers(injuries).power_modifier
                           for injuries in hunters.member_injuries) / hunters.group.member_count
    companions = [calculate_injury_modifiers(injuries).power_modifier
                  for index, injuries in enumerate(prey.member_injuries) if index != target_member_index]
    companion_condition = sum(companions) / len(companions) if companions else 0.0
    support = 1 + (defensive_power.group_multiplier - 1) * companion_condition
    values = {field.name: getattr(base, field.name) for field in fields(DetentionScores)}
    values.update(
        predator_injury_modifier=hunter_condition,
        effective_restraint=(hunting_power.effective_power * base.relative_mass_factor
                             * base.restraint_trait_effect.modifier),
        effective_escape=base.effective_escape * support,
    )
    return GroupDetentionScores(**values, hunting_power=hunting_power,
                                defensive_support=support, target_member_index=target_member_index)
