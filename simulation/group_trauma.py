from dataclasses import dataclass
from typing import Any

from simulation.groups import GroupParticipants, GroupRole
from simulation.hunting import AttackResult, GroupAttackScores, calculate_attack_scores
from simulation.injuries import Injury, resolve_injury_from_trauma
from simulation.traits import resolve_trait_effect
from simulation.trauma import TraumaEvent, create_trauma_event


@dataclass(frozen=True)
class GroupContactInjury:
    """Retain one physical strike and the targeted participant's new condition."""

    acting_member_index: int
    target_member_index: int
    trauma: TraumaEvent | None
    injury: Injury | None
    updated_target: GroupParticipants


def resolve_group_contact_injury(
    attack_result: AttackResult,
    actors: GroupParticipants,
    targets: GroupParticipants,
    actor_definition: dict[str, Any],
    target_definition: dict[str, Any],
    attack_method_definition: dict[str, Any],
    acting_member_index: int,
    target_member_index: int,
    source_stage: str = "attack",
    contact_quality: float = 1.0,
    trait_ids: tuple[str, ...] = (),
    trait_definitions: tuple[dict, ...] = (),
) -> GroupContactInjury:
    """Resolve one member's strike, keeping collective support out of body trauma."""
    if source_stage not in ("attack", "counterattack"):
        raise ValueError("Group source_stage must be attack or counterattack.")
    expected_actor_role = GroupRole.HUNTING if source_stage == "attack" else GroupRole.DEFENSIVE
    expected_target_role = GroupRole.DEFENSIVE if source_stage == "attack" else GroupRole.HUNTING
    if actors.group.role is not expected_actor_role or targets.group.role is not expected_target_role:
        raise ValueError("Participant group roles must match the contact stage.")
    if actors.group.animal_id != actor_definition["id"] or targets.group.animal_id != target_definition["id"]:
        raise ValueError("Contact definitions must match participant species.")
    if (actors.group.region_id, actors.group.habitat_id) != (targets.group.region_id, targets.group.habitat_id):
        raise ValueError("Contact participants must share a region and habitat.")
    for index, participants in ((acting_member_index, actors), (target_member_index, targets)):
        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError("Contact member index must be an integer.")
        if not 0 <= index < participants.group.member_count:
            raise ValueError("Contact member index must identify an existing participant.")
    if isinstance(attack_result.scores, GroupAttackScores):
        if attack_result.scores.attacker_group_power.member_count != actors.group.member_count:
            raise ValueError("Contact scores must match the acting group size.")
    if not attack_result.hit:
        return GroupContactInjury(acting_member_index, target_member_index, None, None, targets)
    scores = calculate_attack_scores(actor_definition, target_definition, actors.member_injuries[acting_member_index])
    power = scores.effective_power
    if source_stage == "counterattack":
        power *= resolve_trait_effect(trait_ids, trait_definitions, "counterattack_power").modifier
    trauma = create_trauma_event(
        source_stage=source_stage, contact_succeeded=True,
        contact_power=power, opposing_defense=scores.defender_defense,
        attack_method_id=attack_method_definition["id"],
        attacker_mass_kg=actor_definition["typical_adult_mass_kg"],
        target_mass_kg=target_definition["typical_adult_mass_kg"],
        contact_quality=contact_quality,
    )
    injury = resolve_injury_from_trauma(
        trauma, attack_method_definition=attack_method_definition,
        trait_ids=trait_ids, trait_definitions=trait_definitions,
    )
    conditions = list(targets.member_injuries)
    if injury is not None:
        conditions[target_member_index] += (injury,)
    return GroupContactInjury(
        acting_member_index, target_member_index, trauma, injury,
        GroupParticipants(targets.group, tuple(conditions)),
    )
