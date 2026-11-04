from dataclasses import dataclass
from math import isfinite
from typing import Any

from core.content_registry import ContentRegistry

from simulation.carrion import CarrionConsumption, consume_carrion
from simulation.world_state import HabitatState, RegionState
from simulation.feeding import PopulationFeedingResult


@dataclass(frozen=True)
class ScavengingResult:
    """Record one local consumer's intake and carcass access decisions."""

    consumer_id: str
    requested_biomass_kg: float
    consumed_biomass_kg: float
    consumptions: tuple[CarrionConsumption, ...]


def scavenge_habitat_carrion(
    consumer_definition: dict[str, Any],
    habitat: HabitatState,
    requested_biomass_kg: float,
) -> ScavengingResult:
    """Consume compatible local carrion in dietary preference order.

    This explicit operation changes only the habitat's carrion state. Hunting
    capability and temperament do not imply scavenging compatibility.
    """
    if isinstance(requested_biomass_kg, bool) or not isinstance(requested_biomass_kg, (int, float)):
        raise TypeError("requested_biomass_kg must be numeric.")
    if not isfinite(requested_biomass_kg) or requested_biomass_kg < 0:
        raise ValueError("requested_biomass_kg must be finite and nonnegative.")
    consumer_id = consumer_definition["id"]
    if habitat.animal_populations.get(consumer_id, 0) <= 0 or requested_biomass_kg == 0:
        return ScavengingResult(consumer_id, requested_biomass_kg, 0.0, ())
    preferences = {entry["animal_id"]: entry["preference"]
                   for entry in consumer_definition.get("scavenging_diet", ())}
    deposits = list(habitat.carrion_deposits)
    if any(deposit.habitat_id != habitat.definition_id for deposit in deposits):
        raise ValueError("Carrion deposit must belong to the consumer's habitat.")
    order = sorted(
        (index for index, deposit in enumerate(deposits) if deposit.source_animal_id in preferences),
        key=lambda index: -preferences[deposits[index].source_animal_id],
    )
    remaining = requested_biomass_kg
    consumptions = []
    for index in order:
        if remaining <= 0:
            break
        consumption = consume_carrion(deposits[index], consumer_id, remaining)
        consumptions.append(consumption)
        deposits[index] = consumption.updated_carrion
        remaining -= consumption.consumed_biomass_kg
    habitat.carrion_deposits = [deposit for deposit in deposits if deposit.available_biomass_kg > 0]
    return ScavengingResult(consumer_id, requested_biomass_kg,
                            requested_biomass_kg - remaining, tuple(consumptions))


def allocate_habitat_scavenging(
    definitions: dict[str, dict[str, Any]],
    habitat: HabitatState,
    requests: dict[str, float],
) -> dict[str, ScavengingResult]:
    """Share chosen carcasses proportionally to unmet demand, preserving access."""
    for amount in requests.values():
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError("Scavenging requests must be numeric.")
        if not isfinite(amount) or amount < 0:
            raise ValueError("Scavenging requests must be finite and nonnegative.")
    deposits = list(habitat.carrion_deposits)
    if any(deposit.habitat_id != habitat.definition_id for deposit in deposits):
        raise ValueError("Carrion deposit must belong to its habitat.")
    preferences = {animal_id: {entry["animal_id"]: entry["preference"]
                              for entry in definitions[animal_id].get("scavenging_diet", ())}
                   for animal_id in requests}
    remaining = dict(requests)
    records: dict[str, list[CarrionConsumption]] = {animal_id: [] for animal_id in requests}
    while True:
        choices: dict[int, list[str]] = {}
        for animal_id in sorted(requests):
            if remaining[animal_id] <= 0 or habitat.animal_populations.get(animal_id, 0) <= 0:
                continue
            eligible = [index for index, deposit in enumerate(deposits)
                        if deposit.available_biomass_kg > 0
                        and deposit.source_animal_id in preferences[animal_id]
                        and deposit.first_access_consumer_id in (None, animal_id)]
            if eligible:
                chosen = max(eligible, key=lambda index: preferences[animal_id][deposits[index].source_animal_id])
                choices.setdefault(chosen, []).append(animal_id)
        if not choices:
            break
        progress = 0.0
        for index, consumers in sorted(choices.items()):
            available = deposits[index].available_biomass_kg
            maximum = max(remaining[animal_id] for animal_id in consumers)
            normalized_total = sum(remaining[animal_id] / maximum for animal_id in consumers)
            for animal_id in consumers:
                demand = remaining[animal_id]
                allocation = demand if available / maximum >= normalized_total else (
                    available * (demand / maximum) / normalized_total
                )
                consumption = consume_carrion(deposits[index], animal_id, allocation)
                records[animal_id].append(consumption)
                deposits[index] = consumption.updated_carrion
                remaining[animal_id] = max(remaining[animal_id] - consumption.consumed_biomass_kg, 0.0)
                progress += consumption.consumed_biomass_kg
        if progress <= 0:
            break
    habitat.carrion_deposits = [deposit for deposit in deposits if deposit.available_biomass_kg > 0]
    return {animal_id: ScavengingResult(
        animal_id, requests[animal_id],
        sum(record.consumed_biomass_kg for record in records[animal_id]),
        tuple(records[animal_id]),
    ) for animal_id in sorted(requests)}


def run_region_scavenging(
    region: RegionState,
    registry: ContentRegistry,
    habitat_feeding: dict[str, dict[str, PopulationFeedingResult]],
) -> dict[str, dict[str, ScavengingResult]]:
    """Fill remaining local food deficits through proportional carcass sharing.

    Hunting has already occurred, and predator first-access reservations still
    apply. This allocation consumes no random draws.
    """
    results: dict[str, dict[str, ScavengingResult]] = {}
    for habitat_id, habitat in sorted(region.habitats.items()):
        definitions = {}
        requests = {}
        for animal_id, prior in sorted(habitat_feeding[habitat_id].items()):
            definition = registry.get(animal_id)
            if not definition.get("scavenging_diet"):
                continue
            definitions[animal_id] = definition
            requests[animal_id] = max(prior.required_amount - prior.consumed_amount, 0.0)
        allocation = allocate_habitat_scavenging(definitions, habitat, requests)
        for animal_id, scavenging in allocation.items():
            prior = habitat_feeding[habitat_id][animal_id]
            results.setdefault(habitat_id, {})[animal_id] = scavenging
            sources = dict(prior.resource_consumption)
            for consumption in scavenging.consumptions:
                amount = consumption.consumed_biomass_kg
                if amount > 0:
                    source = consumption.updated_carrion.source_animal_id
                    sources[source] = sources.get(source, 0.0) + amount
            consumed = prior.consumed_amount + scavenging.consumed_biomass_kg
            habitat_feeding[habitat_id][animal_id] = PopulationFeedingResult(
                prior.required_amount, consumed,
                min(consumed / prior.required_amount, 1.0) if prior.required_amount else 1.0,
                sources,
            )
    return results
