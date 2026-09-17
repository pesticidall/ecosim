from core.content_registry import ContentRegistry
from simulation.world_state import RegionState


def apply_producer_production(
    region_state: RegionState,
    registry: ContentRegistry,
) -> dict[str, float]:
    production_multiplier = 1.0
    if region_state.active_weather_id is not None:
        weather_definition = registry.get(region_state.active_weather_id)
        production_multiplier = weather_definition.get(
            "producer_production_multiplier",
            1.0,
        )
    production_changes: dict[str, float] = {}
    for producer_id, population in region_state.producer_populations.items():
        production_definition = registry.get(producer_id)
        for production_entry in production_definition["production"]:
            resource_id = production_entry["resource_id"]
            amount_per_producer = production_entry[
                "amount_per_producer_per_cycle"
            ]
            produced_amount = (
                population
                * amount_per_producer
                * production_multiplier
            )
            current_quantity = region_state.resource_quantities.get(
                resource_id,
                0.0,
            )
            region_state.resource_quantities[resource_id] = (
                current_quantity + produced_amount
            )
            production_changes[resource_id] = (
                production_changes.get(resource_id, 0.0)
                + produced_amount
            )
    return production_changes