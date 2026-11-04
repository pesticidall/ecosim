from math import expm1, log1p

from core.content_registry import ContentRegistry
from simulation.carrion import CarrionDecay, create_carrion_from_death, decay_carrion, validate_decay_fraction
from simulation.deaths import DeathRecord, create_starvation_death
from simulation.world_state import HabitatState, RegionState


def decay_habitat_carrion(habitat: HabitatState, decay_fraction: float) -> tuple[CarrionDecay, ...]:
    """Apply one configured decay interval and retain immutable decay records."""
    validate_decay_fraction(decay_fraction)
    if any(deposit.habitat_id != habitat.definition_id for deposit in habitat.carrion_deposits):
        raise ValueError("Carrion deposit must belong to its habitat.")
    records = tuple(decay_carrion(deposit, decay_fraction) for deposit in habitat.carrion_deposits)
    habitat.carrion_deposits = [record.updated_carrion for record in records
                               if record.updated_carrion.available_biomass_kg > 0]
    return records


def daily_decay_fraction(monthly_fraction: float, days_in_period: int) -> float:
    """Convert monthly proportional loss to an equivalent daily loss.

    For untouched carrion, repeated daily retention compounds to the configured
    monthly retention. Complete monthly loss means complete daily loss; a finite
    constant proportional rate cannot otherwise yield zero remaining biomass.
    """
    validate_decay_fraction(monthly_fraction)
    if isinstance(days_in_period, bool) or not isinstance(days_in_period, int):
        raise TypeError("Decay days_in_period must be an integer.")
    if days_in_period <= 0:
        raise ValueError("Decay days_in_period must be positive.")
    if monthly_fraction in (0.0, 1.0) or days_in_period == 1:
        return monthly_fraction
    return -expm1(log1p(-monthly_fraction) / days_in_period)


def run_region_carrion_decay(
    region: RegionState, registry: ContentRegistry, *, days_in_period: int = 1,
) -> dict[str, tuple[CarrionDecay, ...]]:
    """Decay after feeding; supply month length when resolving one day."""
    daily_decay_fraction(0.0, days_in_period)
    results = {}
    for habitat_id, habitat in sorted(region.habitats.items()):
        if not habitat.carrion_deposits:
            continue
        fraction = registry.get(habitat.definition_id).get("carrion_decay_fraction_per_cycle", 0.0)
        results[habitat_id] = decay_habitat_carrion(habitat, daily_decay_fraction(fraction, days_in_period))
    return results


def record_starvation_carrion(
    region: RegionState,
    registry: ContentRegistry,
    populations_before_starvation: dict[str, dict[str, int]],
) -> dict[str, tuple[DeathRecord, ...]]:
    """Record habitat starvation losses once after mortality has been applied.

    Legacy definitions without adult mass still record population losses but
    cannot produce a quantified carcass. No body mass is inferred.
    """
    records: dict[str, tuple[DeathRecord, ...]] = {}
    deposits = []
    for habitat_id, starting in sorted(populations_before_starvation.items()):
        habitat = region.habitats[habitat_id]
        local_records = []
        for animal_id, before in sorted(starting.items()):
            count = before - habitat.animal_populations.get(animal_id, 0)
            definition = registry.get(animal_id)
            if count <= 0 or "typical_adult_mass_kg" not in definition:
                continue
            death = create_starvation_death(definition, count)
            local_records.append(death)
            deposits.append((habitat, create_carrion_from_death(death, habitat_id)))
        if local_records:
            records[habitat_id] = tuple(local_records)
    for habitat, deposit in deposits:
        habitat.carrion_deposits.append(deposit)
    return records
