from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from simulation.traits import TraitEffectResult, resolve_animal_trait_effect


@dataclass(frozen=True)
class EscapeMovementPerformance:
    """Record environmental and trait inputs used for an escape."""
    movement: MovementPerformance
    trait_effect: TraitEffectResult
    resolved_escape_mobility: float

def resolve_escape_mobility(
    animal_definition: dict[str, Any],
    taxon_definitions: Iterable[dict[str, Any]],
    trait_definitions: Iterable[dict[str, Any]],
    habitat_definition: dict[str, Any],
    weather_definition: dict[str, Any],
    movement_mode: str,
    flight_capability: str | None = None,
) -> EscapeMovementPerformance:
    """Resolve escape Mobility from movement context and targeted traits."""
    movement = resolve_mobility(
        animal_definition,
        habitat_definition,
        weather_definition,
        movement_mode,
        flight_capability,
    )
    trait_effect = resolve_animal_trait_effect(
        animal_definition,
        taxon_definitions,
        trait_definitions,
        "escape_mobility",
    )
    return EscapeMovementPerformance(
        movement=movement,
        trait_effect=trait_effect,
        resolved_escape_mobility=(
            movement.resolved_mobility
            * trait_effect.modifier
        ),
    )
@dataclass(frozen=True)
class MovementPerformance:
    """Record the inputs and result of one movement calculation."""

    movement_mode: str
    base_mobility: float
    habitat_modifier: float
    weather_modifier: float
    flight_capability: str | None
    flight_capability_modifier: float
    resolved_mobility: float


def base_mobility_for_mode(
    animal_definition: dict[str, Any],
    movement_mode: str,
) -> float:
    """Return an animal's base Mobility for an available movement mode."""
    available_movement_modes = animal_definition[
        "available_movement_modes"
    ]
    if movement_mode not in available_movement_modes:
        raise ValueError(
            f"Animal '{animal_definition['id']}' cannot use "
            f"movement mode '{movement_mode}'."
        )
    return float(
        animal_definition["statistics"]["mobility"]
    )

def habitat_mobility_modifier(
    habitat_definition: dict[str, Any],
    movement_mode: str,
) -> float:
    """Return a habitat's modifier for one movement mode."""
    movement_modifiers = habitat_definition.get(
        "movement_modifiers",
        {},
    )
    return float(
        movement_modifiers.get(
            movement_mode,
            1.0,
        )
    )


def weather_mobility_modifier(
    weather_definition: dict[str, Any],
    movement_mode: str,
) -> float:
    """Return a weather condition's modifier for one movement mode."""
    movement_modifiers = weather_definition.get(
        "movement_modifiers",
        {},
    )
    return float(
        movement_modifiers.get(
            movement_mode,
            1.0,
        )
    )


def weather_flight_capability_modifier(
    weather_definition: dict[str, Any],
    flight_capability: str,
) -> float:
    """Return weather's modifier for one form of flight."""
    capability_modifiers = weather_definition.get(
        "flight_capability_modifiers",
        {},
    )
    return float(
        capability_modifiers.get(
            flight_capability,
            1.0,
        )
    )


def resolve_habitat_mobility(
    animal_definition: dict[str, Any],
    habitat_definition: dict[str, Any],
    movement_mode: str,
) -> MovementPerformance:
    """Resolve Mobility after applying one habitat modifier."""
    return resolve_mobility(
        animal_definition,
        habitat_definition,
        {},
        movement_mode,
    )


def resolve_mobility(
    animal_definition: dict[str, Any],
    habitat_definition: dict[str, Any],
    weather_definition: dict[str, Any],
    movement_mode: str,
    flight_capability: str | None = None,
) -> MovementPerformance:
    """Resolve Mobility from species, habitat, and daily weather."""
    base_mobility = base_mobility_for_mode(
        animal_definition,
        movement_mode,
    )
    habitat_modifier = habitat_mobility_modifier(
        habitat_definition,
        movement_mode,
    )
    weather_modifier = weather_mobility_modifier(
        weather_definition,
        movement_mode,
    )
    selected_flight_capability: str | None = None
    flight_capability_modifier = 1.0
    if movement_mode == "flight":
        available_capabilities = animal_definition.get(
            "flight_capabilities",
            [],
        )
        if flight_capability is None:
            if len(available_capabilities) != 1:
                raise ValueError(
                    f"Animal '{animal_definition['id']}' must select "
                    "one available flight capability."
                )
            selected_flight_capability = available_capabilities[0]
        else:
            if flight_capability not in available_capabilities:
                raise ValueError(
                    f"Animal '{animal_definition['id']}' cannot use "
                    f"flight capability '{flight_capability}'."
                )
            selected_flight_capability = flight_capability
        flight_capability_modifier = (
            weather_flight_capability_modifier(
                weather_definition,
                selected_flight_capability,
            )
        )
    elif flight_capability is not None:
        raise ValueError(
            "A flight capability can only be selected for "
            "movement mode 'flight'."
        )

    return MovementPerformance(
        movement_mode=movement_mode,
        base_mobility=base_mobility,
        habitat_modifier=habitat_modifier,
        weather_modifier=weather_modifier,
        flight_capability=selected_flight_capability,
        flight_capability_modifier=(
            flight_capability_modifier
        ),
        resolved_mobility=(
            base_mobility
            * habitat_modifier
            * weather_modifier
            * flight_capability_modifier
        ),
    )
