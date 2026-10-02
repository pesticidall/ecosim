from collections.abc import Iterable, Mapping

from core.content_registry import ContentRegistry
from simulation.world_state import RegionState


def validate_producer_resource_references(
    producer_definitions: Iterable[dict],
    resource_definitions: Iterable[dict],
) -> None:
    """Require every produced resource ID to reference loaded content"""
    resource_ids = {
        definition["id"]
        for definition in resource_definitions
    }
    for producer_definition in producer_definitions:
        producer_id = producer_definition["id"]
        for production_entry in producer_definition["production"]:
            resource_id = production_entry["resource_id"]
            if resource_id not in resource_ids:
                raise ValueError(
                    f"Producer '{producer_id}' references unknown "
                    f"production resource '{resource_id}'."
                )

def _produce_resources(
    producer_populations: dict[str, int],
    resource_quantities: dict[str, float],
    registry: ContentRegistry,
    production_multiplier: float,
    days: int,
) -> dict[str, float]:
    """Add producer output to one spatial resource collection."""
    production_changes: dict[str, float] = {}
    for producer_id, population in producer_populations.items():
        production_definition = registry.get(producer_id)
        for production_entry in production_definition["production"]:
            resource_id = production_entry["resource_id"]
            amount_per_producer = production_entry[
                "amount_per_producer_per_day"
            ]
            produced_amount = (
                population
                * amount_per_producer
                * production_multiplier
                * days
            )
            resource_quantities[resource_id] = (
                resource_quantities.get(resource_id, 0.0)
                + produced_amount
            )
            production_changes[resource_id] = (
                production_changes.get(resource_id, 0.0)
                + produced_amount
            )
    return production_changes


def apply_producer_production(
    region_state: RegionState,
    registry: ContentRegistry,
    days: int = 1,
    weather_day_totals: Mapping[str, int] | None = None,
) -> dict[str, float]:
    """Produce daily resources locally and maintain the regional totals."""
    production_multiplier = 1.0
    if isinstance(days, bool) or not isinstance(days, int):
        raise TypeError(
            "Production days must be an integer."
        )
    if days <= 0:
        raise ValueError(
            "Production days must be greater than zero."
        )

    if weather_day_totals is not None:
        if sum(weather_day_totals.values()) != days:
            raise ValueError(
                "Weather day totals must equal production days."
            )
        weather_adjusted_days = 0.0
        for weather_id, weather_days in (
            weather_day_totals.items()
        ):
            weather_definition = registry.get(weather_id)
            weather_adjusted_days += (
                weather_days
                * weather_definition.get(
                    "producer_production_multiplier",
                    1.0,
                )
            )
        production_multiplier = weather_adjusted_days / days
    elif region_state.active_weather_id is not None:
        weather_definition = registry.get(region_state.active_weather_id)
        production_multiplier = weather_definition.get(
            "producer_production_multiplier",
            1.0,
        )
    if not region_state.habitats:
        return _produce_resources(
            region_state.producer_populations,
            region_state.resource_quantities,
            registry,
            production_multiplier,
            days,
        )

    regional_changes: dict[str, float] = {}
    for habitat_state in region_state.habitats.values():
        habitat_changes = _produce_resources(
            habitat_state.producer_populations,
            habitat_state.resource_quantities,
            registry,
            production_multiplier,
            days,
        )
        for resource_id, produced_amount in habitat_changes.items():
            region_state.resource_quantities[resource_id] = (
                region_state.resource_quantities.get(resource_id, 0.0)
                + produced_amount
            )
            regional_changes[resource_id] = (
                regional_changes.get(resource_id, 0.0)
                + produced_amount
            )
    return regional_changes
