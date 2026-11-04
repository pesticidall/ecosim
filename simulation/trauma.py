from dataclasses import dataclass
from math import isfinite
from re import fullmatch


@dataclass(frozen=True)
class TraumaEvent:
    """Record physical inputs from successful contact."""
    source_stage: str
    contact_power: float
    opposing_defense: float
    attack_method_id: str
    attacker_mass_kg: float
    target_mass_kg: float
    contact_quality: float

@dataclass(frozen=True)
class TraumaPressure:
    """Record physical pressure before injury resistance is resolved."""
    attack_method_id: str
    relative_mass_factor: float
    contact_pressure: float
    opposing_defense: float

MASS_SCALING_EXPONENT = 0.25

def calculate_relative_mass_factor(
    attacker_mass_kg: float,
    target_mass_kg: float,
) -> float:
    """Calculate the effect of attacker mass relative to target mass."""
    mass_ratio = attacker_mass_kg / target_mass_kg
    return mass_ratio ** MASS_SCALING_EXPONENT

def calculate_trauma_pressure(
    trauma_event: TraumaEvent,
    attack_method_definition: dict | None = None,
    trait_ids: tuple[str, ...] = (),
    trait_definitions: tuple[dict, ...] = (),
) -> TraumaPressure:
    """Apply attack-method and matching trait modifiers to contact pressure."""
    from simulation.traits import resolve_trait_effect
    trauma_modifier = 1.0
    trait_modifier = 1.0
    if attack_method_definition is not None:
        method_id = attack_method_definition["id"]
        if method_id != trauma_event.attack_method_id:
            raise ValueError(
                f"Supplied attack method '{method_id}' does not match "
                f"trauma event attack method '{trauma_event.attack_method_id}'."
            )
        trauma_modifier = attack_method_definition["trauma_modifier"]
        trait_effect = resolve_trait_effect(
            trait_ids=trait_ids,
            trait_definitions=trait_definitions,
            target=attack_method_definition["trait_effect_target"],
        )
        trait_modifier = trait_effect.modifier
    relative_mass_factor = calculate_relative_mass_factor(
        attacker_mass_kg=trauma_event.attacker_mass_kg,
        target_mass_kg=trauma_event.target_mass_kg,
    )
    contact_pressure = (
        trauma_event.contact_power
        * trauma_event.contact_quality
        * relative_mass_factor
        * trauma_modifier
        * trait_modifier
    )
    return TraumaPressure(
        attack_method_id=trauma_event.attack_method_id,
        relative_mass_factor=relative_mass_factor,
        contact_pressure=contact_pressure,
        opposing_defense=trauma_event.opposing_defense,
    )

def calculate_residual_trauma(
    trauma_pressure: TraumaPressure,
) -> float:
    """Return contact pressure remaining after defensive mitigation."""
    return max(
        trauma_pressure.contact_pressure 
        - trauma_pressure.opposing_defense,
        0.0,
    )

def create_trauma_event(
    source_stage: str,
    contact_succeeded: bool,
    contact_power: float,
    opposing_defense: float,
    attack_method_id: str | None = None,
    attacker_mass_kg: float | None = None,
    target_mass_kg: float | None = None,
    contact_quality: float = 1.0,
) -> TraumaEvent | None:
    """Create a trauma inputs only when physical contact succeeds."""
    if not contact_succeeded:
        return None
    required_context = {
        "attack_method_id": attack_method_id,
        "attacker_mass_kg": attacker_mass_kg,
        "target_mass_kg": target_mass_kg,
    }
    for field_name, field_value in required_context.items():
        if field_value is None:
            raise ValueError(
                f"{field_name} is required for successful contact"
            )
    identifier_context = {
        "source_stage": source_stage,
        "attack_method_id": attack_method_id,
    }
    for field_name, field_value in identifier_context.items():
        if not isinstance(field_value, str):
            raise TypeError(
                f"Field '{field_name}' must be a string."
            )
    for field_name, field_value in identifier_context.items():
        if fullmatch(
            r"[a-z][a-z0-9_]*(?:_[a-z0-9_]+)*",
            field_value,
        ) is None:
            raise ValueError(
                f"Field '{field_name}' must be lowercase snake_case."
            )
    numeric_context = {
        "contact_power": contact_power,
        "opposing_defense": opposing_defense,
        "attacker_mass_kg": attacker_mass_kg,
        "target_mass_kg": target_mass_kg,
        "contact_quality": contact_quality,
    }
    for field_name, field_value in numeric_context.items():
        if (
            isinstance(field_value, bool)
            or not isinstance(field_value, (int, float))
        ):
            raise TypeError(
                f"Field '{field_name}' must be numeric."
            )
    statistic_context = {
        "contact_power": contact_power,
        "opposing_defense": opposing_defense,
    }
    for field_name, field_value in statistic_context.items():
        if not isfinite(field_value):
            raise ValueError(
                f"Field '{field_name}' must be finite."
            )

    if contact_power <= 0:
        raise ValueError(
            "Field 'contact_power' must be greater than zero."
        )
    if opposing_defense < 0:
        raise ValueError(
            "Field 'opposing_defense' must be zero or greater."
        )

    mass_context = {
        "attacker_mass_kg": attacker_mass_kg,
        "target_mass_kg": target_mass_kg,
    }
    for field_name, field_value in mass_context.items():
        if not isfinite(field_value):
            raise ValueError(
                f"Field '{field_name}' must be finite."
            )
    for field_name, field_value in mass_context.items():
        if field_value <= 0:
            raise ValueError(
                f"Field '{field_name}' must be greater than zero."
            )
    if not isfinite(contact_quality):
        raise ValueError(
            "Field 'contact_quality' must be finite."
        )
    if not 0.0 < contact_quality <= 1.0:
        raise ValueError(
            "Field 'contact_quality' must be greater than zero "
            "and at most one."
        )
    return TraumaEvent(
        source_stage=source_stage,
        contact_power=contact_power,
        opposing_defense=opposing_defense,
        attack_method_id=attack_method_id,
        attacker_mass_kg=attacker_mass_kg,
        target_mass_kg=target_mass_kg,
        contact_quality=contact_quality,
    )
