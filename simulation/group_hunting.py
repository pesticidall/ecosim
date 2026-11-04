from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from random import Random
from typing import Any

from simulation.group_conditions import GroupConditionChange, apply_group_condition_changes
from simulation.group_detention import calculate_group_detention_scores
from simulation.group_feeding import GroupMeal
from simulation.group_predation import apply_group_predation
from simulation.group_trauma import GroupContactInjury, resolve_group_contact_injury
from simulation.groups import GroupParticipants
from simulation.hunting import (
    AttackResult, DetentionResult, HuntApproachResult, HuntOutcome,
    build_hunt_outcome, calculate_chase_scores, calculate_counterattack_scores,
    calculate_group_attack_scores, calculate_group_detection_scores,
    resolve_attack, resolve_detention, resolve_hunt_approach, select_post_contact_response,
)
from simulation.injuries import calculate_injury_modifiers
from simulation.temperament import ActionSelection
from simulation.traits import resolve_animal_trait_ids
from simulation.world_state import RegionState
from simulation.approach import calculate_stalking_scores


@dataclass(frozen=True)
class GroupHuntResult:
    """Retain all stage evidence and explicit group condition changes."""

    approach: HuntApproachResult
    outcome: HuntOutcome
    hunter_change: GroupConditionChange
    prey_change: GroupConditionChange
    response: ActionSelection | None = None
    contact_injury: GroupContactInjury | None = None
    counterattack: AttackResult | None = None
    counterattack_injury: GroupContactInjury | None = None
    detention: DetentionResult | None = None


def resolve_group_hunt(
    hunters: GroupParticipants,
    prey: GroupParticipants,
    predator_definition: dict[str, Any],
    prey_definition: dict[str, Any],
    habitat_definition: dict[str, Any],
    weather_definition: dict[str, Any],
    attack_method_definition: dict[str, Any],
    counterattack_method_definition: dict[str, Any] | None,
    taxon_definitions: Iterable[dict[str, Any]],
    trait_definitions: Iterable[dict[str, Any]],
    temperament_definitions: Iterable[dict[str, Any]],
    contextual_suitability: Mapping[str, float],
    random_source: Random,
    acting_member_index: int = 0,
    target_member_index: int = 0,
    activity_overlap_modifier: float = 1.0,
) -> GroupHuntResult:
    """Resolve one group hunt without mutating populations or creating deaths.

    Hunters pursue together at their slowest member's condition-adjusted
    mobility. One selected participant strikes one selected prey; retaliation
    targets that hunter. These are initial group encounter rules.
    """
    for index, participants in ((acting_member_index, hunters), (target_member_index, prey)):
        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError("Group hunt member index must be an integer.")
        if not 0 <= index < participants.group.member_count:
            raise ValueError("Group hunt member index must identify a participant.")
    taxa, traits = tuple(taxon_definitions), tuple(trait_definitions)
    detection = calculate_group_detection_scores(
        hunters.group, prey.group, predator_definition, prey_definition,
        activity_overlap_modifier, weather_definition, habitat_definition, taxa, traits,
    )
    slowest = min(hunters.member_injuries,
                  key=lambda injuries: calculate_injury_modifiers(injuries).mobility_modifier)
    chase = calculate_chase_scores(
        predator_definition, prey_definition, taxa, traits, habitat_definition, weather_definition,
        predator_definition["primary_movement_mode"], prey_definition["primary_movement_mode"],
        predator_injuries=slowest, prey_injuries=prey.member_injuries[target_member_index],
    )
    attack_scores = calculate_group_attack_scores(
        hunters.group, predator_definition, prey_definition, prey.group, hunters.member_injuries,
    )
    stalking = (calculate_stalking_scores(predator_definition, prey_definition, habitat_definition, weather_definition,
                taxa, traits, hunters.group.member_count, prey.group.member_count)
                if predator_definition.get("approach_model") == "concealed" else None)
    approach = resolve_hunt_approach(detection, chase, attack_scores, random_source, stalking)
    updated_hunters, updated_prey = hunters, prey
    response = contact = counterattack = counter_injury = detention = None
    if approach.attack is not None and approach.attack.hit:
        contact = resolve_group_contact_injury(
            approach.attack, hunters, prey, predator_definition, prey_definition,
            attack_method_definition, acting_member_index, target_member_index,
            trait_ids=tuple(resolve_animal_trait_ids(predator_definition, taxa)), trait_definitions=traits,
        )
        updated_prey = contact.updated_target
        response = select_post_contact_response(
            prey_definition, taxa, traits, temperament_definitions, contextual_suitability, random_source,
        )
        if response.selected_action_id == "counterattack":
            if counterattack_method_definition is None:
                raise ValueError("A counterattack method is required for group retaliation.")
            counter_scores = calculate_counterattack_scores(
                prey_definition, predator_definition, taxa, traits,
                updated_prey.member_injuries[target_member_index],
            )
            counterattack = resolve_attack(counter_scores, random_source)
            counter_injury = resolve_group_contact_injury(
                counterattack, updated_prey, hunters, prey_definition, predator_definition,
                counterattack_method_definition, target_member_index, acting_member_index,
                source_stage="counterattack",
                trait_ids=tuple(resolve_animal_trait_ids(prey_definition, taxa)), trait_definitions=traits,
            )
            updated_hunters = counter_injury.updated_target
        detention = resolve_detention(calculate_group_detention_scores(
            updated_hunters, updated_prey, predator_definition, prey_definition,
            target_member_index, taxa, traits,
        ), random_source)
    outcome = build_hunt_outcome(
        approach.detection.detected,
        approach.chase is not None and approach.chase.caught,
        approach.attack is not None and approach.attack.hit,
        detention is not None and detention.detained,
    )
    return GroupHuntResult(
        approach, outcome, GroupConditionChange(hunters, updated_hunters),
        GroupConditionChange(prey, updated_prey,
                             dead_member_indices=(target_member_index,) if outcome.prey_secured else ()),
        response, contact, counterattack, counter_injury, detention,
    )


def apply_group_hunt(
    region: RegionState, result: GroupHuntResult,
    predator_definition: dict[str, Any], prey_definition: dict[str, Any],
    *, requested_biomass_kg: float | None = None,
    period_fraction: float = 1.0,
) -> GroupMeal | None:
    """Commit survivor injuries or one secured-prey death and shared meal."""
    if result.outcome.prey_secured:
        return apply_group_predation(region, result.hunter_change, result.prey_change,
                                     predator_definition, prey_definition,
                                     requested_biomass_kg=requested_biomass_kg,
                                     period_fraction=period_fraction)
    apply_group_condition_changes(region, (result.hunter_change, result.prey_change))
    return None
