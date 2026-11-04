from random import Random

from core.content_registry import ContentRegistry
from simulation.feeding import (
    PopulationFeedingResult, calculate_population_food_requirement, _validate_period_fraction,
)
from simulation.habitat_hunting import HabitatHuntingRound, run_habitat_hunting_round
from simulation.group_hunting_cycle import HabitatGroupHuntingRound, run_habitat_group_hunting_round
from simulation.world_state import RegionState


def _survivor_feeding(population, definition, feeding, period_fraction=1.0):
    """Retain nutrition per survivor; food already consumed is not returned."""
    required = calculate_population_food_requirement(population, definition, period_fraction=period_fraction)
    if required == feeding.required_amount:
        return feeding
    scale = required / feeding.required_amount if feeding.required_amount else 0.0
    consumed = feeding.consumed_amount * scale
    return PopulationFeedingResult(
        required, consumed, min(consumed / required, 1.0) if required else 1.0,
        {source: amount * scale for source, amount in feeding.resource_consumption.items()},
    )


def run_region_hunting(
    region: RegionState,
    registry: ContentRegistry,
    habitat_feeding: dict[str, dict[str, PopulationFeedingResult]],
    random_source: Random,
    *,
    period_fraction: float = 1.0,
) -> dict[str, dict[str, HabitatHuntingRound | HabitatGroupHuntingRound]]:
    """Supplement local food deficits for the caller's ecological interval.

    Feeding records describe survivors after predation. Resource stores are
    never refunded for food eaten by prey before their death.
    """
    _validate_period_fraction(period_fraction)
    rounds: dict[str, dict[str, HabitatHuntingRound | HabitatGroupHuntingRound]] = {}
    taxa = registry.definitions_of_type("taxon")
    traits = registry.definitions_of_type("trait")
    temperaments = registry.definitions_of_type("temperament")
    weather = registry.get(region.active_weather_id) if region.active_weather_id else {}
    for habitat_id, habitat in sorted(region.habitats.items()):
        results = habitat_feeding[habitat_id]
        for animal_id in sorted(habitat.animal_populations):
            definition = registry.get(animal_id)
            if not definition.get("prey_diet"):
                continue
            if "attack_method_id" not in definition:
                raise ValueError(f"Hunting animal '{animal_id}' requires attack_method_id.")
            prior = _survivor_feeding(
                habitat.animal_populations[animal_id], definition, results[animal_id], period_fraction,
            )
            use_groups = definition.get("max_hunting_group_size", 1) > 1 or any(
                registry.get(entry["animal_id"]).get("max_defensive_group_size", 1) > 1
                for entry in definition["prey_diet"]
            )
            if use_groups:
                result = run_habitat_group_hunting_round(
                    animal_id, habitat_id, region, registry, weather,
                    taxa, traits, temperaments, {"escape": 1.0, "counterattack": 1.0},
                    random_source, prior_feeding=prior, local_feeding=results,
                    period_fraction=period_fraction,
                )
            else:
                result = run_habitat_hunting_round(
                    animal_id, habitat_id, region, registry, weather, None, None,
                    taxa, traits, temperaments, {"escape": 1.0, "counterattack": 1.0},
                    random_source, prior_feeding=prior,
                    period_fraction=period_fraction,
                )
            rounds.setdefault(habitat_id, {})[animal_id] = result
            results[animal_id] = result.feeding
        for animal_id, feeding in results.items():
            results[animal_id] = _survivor_feeding(
                habitat.animal_populations.get(animal_id, 0), registry.get(animal_id), feeding,
                period_fraction,
            )
    return rounds
