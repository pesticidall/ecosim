from dataclasses import dataclass, replace
from enum import Enum
from math import isfinite
from typing import Any

from simulation.hunting import HuntOutcome


class DeathCause(Enum):
    """Name the ecological process for a death."""
    PREDATION = "predation"
    STARVATION = "starvation"

@dataclass(frozen=True)
class DeathRecord:
    """Record a population death before remains become carrion."""
    animal_id: str
    cause: DeathCause
    count: int
    body_mass_kg: float
    adult_count: int | None = None
    juvenile_count: int | None = None

    def __post_init__(self):
        if self.adult_count is None and self.juvenile_count is None:
            return
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0
               for value in (self.adult_count, self.juvenile_count)) or self.adult_count + self.juvenile_count != self.count:
            raise ValueError("Death age counts must be nonnegative integers summing to the death count.")


def with_age_loss(death, plan):
    """Retain known age composition; legacy records keep age unspecified."""
    return replace(death, adult_count=plan.adults, juvenile_count=plan.juveniles) if plan is not None else death

def create_predation_death(
    hunt_outcome: HuntOutcome,
    prey_definition: dict[str, Any],
) -> DeathRecord | None:
    """Create one predation death when a hunt secures its prey."""
    if not hunt_outcome.prey_secured:
        return None

    return DeathRecord(
        animal_id=prey_definition["id"],
        cause=DeathCause.PREDATION,
        count=1,
        body_mass_kg=float(
            prey_definition["typical_adult_mass_kg"]
        )
    )


def create_starvation_death(animal_definition: dict[str, Any], count: int) -> DeathRecord | None:
    """Record known starvation losses using defined adult body mass."""
    if isinstance(count, bool) or not isinstance(count, int):
        raise TypeError("Starvation death count must be an integer.")
    if count < 0:
        raise ValueError("Starvation death count must not be negative.")
    if count == 0:
        return None
    mass = animal_definition["typical_adult_mass_kg"]
    if isinstance(mass, bool) or not isinstance(mass, (int, float)):
        raise TypeError("Starvation body mass must be numeric.")
    if not isfinite(mass) or mass <= 0:
        raise ValueError("Starvation body mass must be finite and positive.")
    return DeathRecord(animal_definition["id"], DeathCause.STARVATION, count, float(mass))
