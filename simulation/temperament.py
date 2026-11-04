from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from random import Random
from typing import Any


@dataclass(frozen=True)
class ActionOption:
    """Record the inputs contributing to one eligible action's weight."""
    action_id: str
    temperament_preference: float
    contextual_suitability: float
    combined_weight: float

@dataclass(frozen=True)
class ActionSelection:
    """Record a seeded choice among contextually eligible actions."""
    options: tuple[ActionOption, ...]
    total_weight: float
    selection_roll: float
    selected_action_id: str

def validate_animal_temperament_references(
    animal_definitions: Iterable[dict[str, Any]],
    temperament_definitions: Iterable[dict[str, Any]],
) -> None:
    """Require animal temperament IDs to reference loaded profiles."""
    temperament_ids = {
        definition["id"]
        for definition in temperament_definitions
    }
    for animal_definition in animal_definitions:
        temperament_id = animal_definition.get("temperament_id")
        if temperament_id is None:
            continue
        if temperament_id not in temperament_ids:
            animal_id = animal_definition["id"]
            raise ValueError(
                f"Animal '{animal_id}' references unknown temperament "
                f"'{temperament_id}'."
            )

def resolve_animal_temperament_weights(
    animal_definition: dict[str, Any],
    temperament_definitions: Iterable[dict[str, Any]],
) -> dict[str, float]:
    """Resolve an animal's reusable or legacy inline action weights."""
    has_profile = "temperament_id" in animal_definition
    has_inline_weights = "temperament" in animal_definition
    if has_profile and has_inline_weights:
        animal_id = animal_definition["id"]
        raise ValueError(
            f"Animal '{animal_id}' defines both 'temperament_id' "
            "and 'temperament'; only one temperament source "
            "may be defined."
        )
    if has_profile:
        temperament_id = animal_definition["temperament_id"]
        definitions_by_id = {
            definition["id"]: definition
            for definition in temperament_definitions
        }
        if temperament_id not in definitions_by_id:
            animal_id = animal_definition["id"]
            raise ValueError(
                f"Animal '{animal_id}' references unknown "
                f"temperament '{temperament_id}'."
            )
        return dict(
            definitions_by_id[temperament_id]["action_weights"]
        )
    if has_inline_weights:
        return dict(animal_definition["temperament"])
    return {}

def select_animal_action(
    animal_definition: dict[str, Any],
    temperament_definitions: Iterable[dict[str, Any]],
    contextual_suitability: Mapping[str, float],
    eligible_action_ids: Iterable[str],
    random_source: Random,
) -> ActionSelection:
    """Select an eligible action from context and temperament weights."""
    temperament_weights = resolve_animal_temperament_weights(
        animal_definition,
        temperament_definitions,
    )
    options: list[ActionOption] = []
    for action_id in eligible_action_ids:
        temperament_preference = float(
            temperament_weights.get(action_id, 1.0)
        )
        suitability = float(
            contextual_suitability[action_id]
        )
        options.append(
            ActionOption(
                action_id=action_id,
                temperament_preference=temperament_preference,
                contextual_suitability=suitability,
                combined_weight=(
                    temperament_preference
                    * suitability
                ),
            )
        )
    total_weight = sum(
        option.combined_weight
        for option in options
    )
    if total_weight <= 0.0:
        raise ValueError(
            "Eligible animal actions must have positive combined weight."
        )
    selection_roll = random_source.random()
    selection_threshold = selection_roll * total_weight
    cumulative_weight = 0.0
    selected_action_id = options[-1].action_id
    for option in options:
        cumulative_weight += option.combined_weight
        if selection_threshold < cumulative_weight:
            selected_action_id = option.action_id
            break
    return ActionSelection(
        options=tuple(options),
        total_weight=total_weight,
        selection_roll=selection_roll,
        selected_action_id=selected_action_id,
    )