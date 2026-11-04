from dataclasses import dataclass, replace
from math import isfinite

from simulation.deaths import DeathRecord


@dataclass(frozen=True)
class CarrionDeposit:
    """Record animal remains available within one habitat."""
    source_animal_id: str
    habitat_id: str
    original_biomass_kg: float
    available_biomass_kg: float
    first_access_consumer_id: str | None

@dataclass(frozen=True)
class CarrionConsumption:
    """Record biomass consumed and the resulting carrion state."""
    consumer_id: str
    requested_biomass_kg: float
    consumed_biomass_kg: float
    access_granted: bool
    updated_carrion: CarrionDeposit

@dataclass(frozen=True)
class CarrionDecay:
    """Record biomass lost through decay and the resulting state."""
    decayed_biomass_kg: float
    updated_carrion: CarrionDeposit

def create_carrion_from_death(
    death_record: DeathRecord,
    habitat_id: str,
    first_access_consumer_id: str | None = None,
) -> CarrionDeposit:
    """Convert recorded animal deaths into habitat-local carrion."""
    carrion_biomass_kg = (
        death_record.body_mass_kg
        * death_record.count
    )
    return CarrionDeposit(
        source_animal_id=death_record.animal_id,
        habitat_id=habitat_id,
        original_biomass_kg=carrion_biomass_kg,
        available_biomass_kg=carrion_biomass_kg,
        first_access_consumer_id=first_access_consumer_id,
    )

def consume_carrion(
    carrion: CarrionDeposit,
    consumer_id: str,
    requested_biomass_kg: float,
) -> CarrionConsumption:
    """Consume available biomass without mutating carrion history."""
    if(
        isinstance(requested_biomass_kg, bool)
        or not isinstance(requested_biomass_kg, (int, float))
    ):
        raise TypeError(
            "Field 'requested_biomass_kg' must be numeric."
        )
    if not isfinite(requested_biomass_kg):
        raise ValueError(
            "Field 'requested_biomass_kg' must be finite."
        )
    if requested_biomass_kg < 0:
        raise ValueError(
            "Field 'requested_biomass_kg' must be zero or greater."
        )
    if (
        carrion.first_access_consumer_id is not None
        and consumer_id != carrion.first_access_consumer_id
    ):
        return CarrionConsumption(
            consumer_id=consumer_id,
            requested_biomass_kg=requested_biomass_kg,
            consumed_biomass_kg=0.0,
            access_granted=False,
            updated_carrion=carrion,
        )
    consumed_biomass_kg = min(
        requested_biomass_kg,
        carrion.available_biomass_kg,
    )
    updated_carrion = replace(
        carrion,
        available_biomass_kg=(
            carrion.available_biomass_kg
            - consumed_biomass_kg
        ),
    )
    return CarrionConsumption(
        consumer_id=consumer_id,
        requested_biomass_kg=requested_biomass_kg,
        consumed_biomass_kg=consumed_biomass_kg,
        access_granted=True,
        updated_carrion=updated_carrion,
    )

def release_first_access(
    carrion: CarrionDeposit,
    consumer_id: str,
) -> CarrionDeposit:
    """Release reserved carrion only for its first-access consumer."""
    if carrion.first_access_consumer_id != consumer_id:
        return carrion
    return replace(
        carrion,
        first_access_consumer_id=None,
    )

def validate_decay_fraction(decay_fraction: float) -> None:
    """Require a finite normalized numeric carrion decay fraction."""
    if (
        isinstance(decay_fraction, bool)
        or not isinstance(
            decay_fraction, 
            (int, float),
        )
    ):
        raise TypeError(
            "Field 'decay_fraction' must be numeric."
        )
    if not isfinite(decay_fraction):
        raise ValueError(
            "Field 'decay_fraction' must be finite."
        )
    if decay_fraction < 0 or decay_fraction > 1:
        raise ValueError(
            "Field 'decay_fraction' must be between zero and one."
        )
def decay_carrion(
    carrion: CarrionDeposit,
    decay_fraction: float,
) -> CarrionDecay:
    """Remove a fraction of currently available carrion biomass."""
    validate_decay_fraction(decay_fraction)
    decayed_biomass_kg = (
        carrion.available_biomass_kg
        * decay_fraction
    )
    updated_carrion = replace(
        carrion,
        available_biomass_kg=(
            carrion.available_biomass_kg
            - decayed_biomass_kg
        ),
    )
    return CarrionDecay(
        decayed_biomass_kg=decayed_biomass_kg,
        updated_carrion=updated_carrion,
    )
