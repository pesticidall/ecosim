from collections.abc import Iterable, Mapping
from typing import Any

from simulation.world_state import RegionState


def validate_region_habitat_references(
    region_definitions: Iterable[dict[str, Any]],
    habitat_definitions: Iterable[dict[str, Any]],
) -> None:
    """Require every region habitat ID to reference loaded habitat content."""
    habitat_ids = {
        definition["id"]
        for definition in habitat_definitions
    }
    for region_definition in region_definitions:
        region_id = region_definition["id"]
        for habitat_id in region_definition["habitat_ids"]:
            if habitat_id not in habitat_ids:
                raise ValueError(
                    f"Region '{region_id}' references unknown "
                    f"habitat '{habitat_id}'."
                )


def validate_animal_habitat_references(
    animal_definitions: Iterable[dict[str, Any]],
    habitat_definitions: Iterable[dict[str, Any]],
) -> None:
    """Require animal habitat preference IDs to reference loaded content."""
    habitat_ids = {
        definition["id"]
        for definition in habitat_definitions
    }
    for animal_definition in animal_definitions:
        animal_id = animal_definition["id"]
        for habitat_id in animal_definition.get(
            "preferred_habitat_ids",
            [],
        ):
            if habitat_id not in habitat_ids:
                raise ValueError(
                    f"Animal '{animal_id}' references unknown "
                    f"preferred habitat '{habitat_id}'."
                )


def validate_producer_habitat_references(
    producer_definitions: Iterable[dict[str, Any]],
    habitat_definitions: Iterable[dict[str, Any]],
) -> None:
    """Require producer habitat preference IDs to reference loaded content."""
    habitat_ids = {
        definition["id"]
        for definition in habitat_definitions
    }
    for producer_definition in producer_definitions:
        producer_id = producer_definition["id"]
        for habitat_id in producer_definition.get(
            "preferred_habitat_ids",
            [],
        ):
            if habitat_id not in habitat_ids:
                raise ValueError(
                    f"Producer '{producer_id}' references unknown "
                    f"preferred habitat '{habitat_id}'."
                )

def order_habitats_by_preference(
    entity_definition: dict[str, Any],
    region_definition: dict[str, Any],
) -> list[str]:
    """Return every regional habitat with an entity's preferences first."""
    regional_habitat_ids = region_definition["habitat_ids"]
    preferred_habitat_ids = set(
        entity_definition.get(
            "preferred_habitat_ids",
            [],
        ),
    )
    preferred_choices = [
        habitat_id
        for habitat_id in regional_habitat_ids
        if habitat_id in preferred_habitat_ids
    ]
    other_choices = [
        habitat_id
        for habitat_id in regional_habitat_ids
        if habitat_id not in preferred_habitat_ids
    ]
    return preferred_choices + other_choices

def select_initial_habitat_id(
    entity_definition: dict[str, Any],
    region_definition: dict[str, Any],
) -> str:
    """Choose the first available habitat after applying preferences."""
    ordered_habitat_ids = order_habitats_by_preference(
        entity_definition,
        region_definition,
    )
    if not ordered_habitat_ids:
        raise ValueError(
            f"Region '{region_definition['id']}' has no habitats "
            f"available for entity '{entity_definition['id']}'."
        )
    return ordered_habitat_ids[0]


def distribute_resource_by_production(
    region_state: RegionState,
    resource_id: str,
    quantity: float,
    producer_definitions: Mapping[str, dict[str, Any]],
) -> None:
    """Distribute starting biomass by each habitat's production capacity."""
    capacity_by_habitat: dict[str, float] = {}
    for habitat_id, habitat_state in region_state.habitats.items():
        habitat_capacity = 0.0
        for producer_id, population in (
            habitat_state.producer_populations.items()
        ):
            producer_definition = producer_definitions[producer_id]
            for production_entry in producer_definition["production"]:
                if production_entry["resource_id"] == resource_id:
                    habitat_capacity += (
                        population
                        * production_entry[
                            "amount_per_producer_per_day"
                        ]
                    )
        if habitat_capacity > 0.0:
            capacity_by_habitat[habitat_id] = habitat_capacity

    total_capacity = sum(capacity_by_habitat.values())
    if total_capacity <= 0.0:
        raise ValueError(
            f"Region '{region_state.definition_id}' has no producer "
            f"for starting resource '{resource_id}'."
        )

    distributed_quantity = 0.0
    habitat_capacity_items = list(capacity_by_habitat.items())
    for item_index, (habitat_id, habitat_capacity) in enumerate(
        habitat_capacity_items
    ):
        if item_index == len(habitat_capacity_items) - 1:
            habitat_quantity = quantity - distributed_quantity
        else:
            habitat_quantity = quantity * habitat_capacity / total_capacity
            distributed_quantity += habitat_quantity
        region_state.habitats[
            habitat_id
        ].resource_quantities[resource_id] = habitat_quantity


def move_animal_population(
    region_state: RegionState,
    animal_id: str,
    population: int,
    source_habitat_id: str,
    destination_habitat_id: str,
) -> None:
    """Move animals between habitats without changing the regional total."""
    if isinstance(population, bool) or not isinstance(population, int):
        raise TypeError("Moving population must be an integer.")
    if population <= 0:
        raise ValueError("Moving population must be greater than zero.")
    if source_habitat_id not in region_state.habitats:
        raise ValueError(
            f"Region '{region_state.definition_id}' does not contain "
            f"source habitat '{source_habitat_id}'."
        )
    if destination_habitat_id not in region_state.habitats:
        raise ValueError(
            f"Region '{region_state.definition_id}' does not contain "
            f"destination habitat '{destination_habitat_id}'."
        )
    source_populations = region_state.habitats[
        source_habitat_id
    ].animal_populations
    available_population = source_populations.get(animal_id, 0)
    if population > available_population:
        raise ValueError(
            f"Cannot move {population} '{animal_id}' animals from "
            f"habitat '{source_habitat_id}'; only "
            f"{available_population} are present."
        )
    remaining_population = available_population - population
    if remaining_population:
        source_populations[animal_id] = remaining_population
    else:
        source_populations.pop(animal_id, None)
    destination_populations = region_state.habitats[
        destination_habitat_id
    ].animal_populations
    destination_populations[animal_id] = (
        destination_populations.get(animal_id, 0)
        + population
    )
