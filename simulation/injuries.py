from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from simulation.trauma import (
    TraumaEvent,
    calculate_residual_trauma,
    calculate_trauma_pressure,
)


class InjurySeverity(Enum):
    """Name the intial persistant injury serverity levels."""
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"

MODERATE_TRAUMA_THRESHOLD = 2.0
MAJOR_TRAUMA_THRESHOLD = 4.0
CRITICAL_TRAUMA_THRESHOLD = 7.0

INJURY_CONDITION_MODIFIERS = {
    InjurySeverity.MINOR: 0.9,
    InjurySeverity.MODERATE: 0.75,
    InjurySeverity.MAJOR: 0.5,
    InjurySeverity.CRITICAL: 0.25,
}

def classify_injury_severity(
    residual_trauma: float
) -> InjurySeverity | None:
    """Classify unmitigated trauma without applying health consequences."""
    if residual_trauma <= 0:
        return None
    if residual_trauma < MODERATE_TRAUMA_THRESHOLD:
        return InjurySeverity.MINOR
    if residual_trauma < MAJOR_TRAUMA_THRESHOLD:
        return InjurySeverity.MODERATE
    if residual_trauma < CRITICAL_TRAUMA_THRESHOLD:
        return InjurySeverity.MAJOR
    return InjurySeverity.CRITICAL
    
@dataclass(frozen=True)
class Injury:
    """Record one injury and its current condition modifiers."""
    severity: InjurySeverity
    source_stage: str
    power_modifier: float
    mobility_modifier: float

def create_injury_from_trauma(
    source_stage: str,
    residual_trauma: float,
) -> Injury | None:
    """Create a persistent injury from unmitigated trauma."""
    severity = classify_injury_severity(residual_trauma)
    if severity is None:
        return None
    condition_modifier = INJURY_CONDITION_MODIFIERS[severity]
    return Injury(
        severity=severity,
        source_stage=source_stage,
        power_modifier=condition_modifier,
        mobility_modifier=condition_modifier,
    )

def resolve_injury_from_trauma(
    trauma_event: TraumaEvent,
    attack_method_definition: dict | None = None,
    trait_ids: tuple[str, ...] = (),
    trait_definitions: tuple[dict, ...] = (),
) -> Injury | None:
    """Convert trauma into injury using method and trait modifiers."""
    trauma_pressure = calculate_trauma_pressure(
        trauma_event,
        attack_method_definition=attack_method_definition,
        trait_ids=trait_ids,
        trait_definitions=trait_definitions,
    )
    residual_trauma = calculate_residual_trauma(
        trauma_pressure,
    )
    return create_injury_from_trauma(
        source_stage=trauma_event.source_stage,
        residual_trauma=residual_trauma,
    )

@dataclass(frozen=True)
class InjuryModifiers:
    """Record cumulative condition effects from current injuries."""
    power_modifier: float
    mobility_modifier: float

def calculate_injury_modifiers(
    injuries: Iterable[Injury],
) -> InjuryModifiers:
    """Combine current injury effects without changing base statistics."""
    power_modifier = 1.0
    mobility_modifier = 1.0
    for injury in injuries:
        power_modifier *= injury.power_modifier
        mobility_modifier *= injury.mobility_modifier
    return InjuryModifiers(
        power_modifier=power_modifier,
        mobility_modifier=mobility_modifier,
    )
