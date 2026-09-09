from dataclasses import dataclass
from typing import Any

from core.content_registry import ContentRegistry
from simulation.world_state import RegionState


@dataclass(frozen=True)
class PopulationFeedingResult:
    required_amount: float
    consumed_amount: float
    nutrition_ratio: float
    resource_consumption: dict[str, float]

def calculate_population_food_requirement(
    population: int,
    animal_definition: dict[str, Any],
) -> float:
    if population < 0:
        raise ValueError(
            f"population must not be negative; "
            f"received {population}."
        )
    food_requirement_per_animal = animal_definition[
        "food_requirement_per_animal_per_cycle"
    ]
    return float(
        population * food_requirement_per_animal
    )

def consume_available_resource(
    region_state: RegionState,
    resource_id: str,
    requested_amount: float,
) -> float:
    if requested_amount <0:
        raise ValueError(
            f"requested_amount must not be negative; "
            f"received {requested_amount}."
        )
    available_amount = region_state.resource_quantities.get(
        resource_id,
        0.0,
    )
    if available_amount <0:
        raise ValueError(
            f"available resource quantity for '{resource_id}' "
            f"must not be negative; received {available_amount}."
        )
    consumed_amount = min(
        requested_amount,
        available_amount,
    )
    region_state.resource_quantities[resource_id] = (
        available_amount - consumed_amount
    )
    return float(consumed_amount)

def feed_population(
    population: int,
    animal_definition: dict[str, Any],
    region_state: RegionState,
) -> PopulationFeedingResult:
    required_amount = calculate_population_food_requirement(
        population,
        animal_definition,
    )
    remaining_requirement = required_amount
    total_consumed = 0.0
    resource_consumption: dict[str, float] = {}
    ordered_diet = sorted(
        animal_definition["diet"],
        key=lambda diet_entry: diet_entry["preference"],
        reverse=True,
    )
    for diet_entry in ordered_diet:
        if remaining_requirement <= 0:
            break
        resource_id = diet_entry["resource_id"]
        consumed_from_resource = consume_available_resource(
            region_state,
            resource_id,
            remaining_requirement,
        )
        resource_consumption[resource_id] = (
            resource_consumption.get(resource_id, 0.0)
            + consumed_from_resource
        )
        total_consumed += consumed_from_resource
        remaining_requirement -= consumed_from_resource
    if required_amount > 0:
        nutrition_ratio = total_consumed / required_amount
    else:
        nutrition_ratio = 1.0

    return PopulationFeedingResult(
        required_amount=required_amount,
        consumed_amount=total_consumed,
        nutrition_ratio=nutrition_ratio,
        resource_consumption=resource_consumption,
    )

def feed_region(
    region_state: RegionState,
    registry: ContentRegistry,
) -> dict[str, PopulationFeedingResult]:
    for resource_id, available_amount in (
        region_state.resource_quantities.items()
    ):
        if available_amount < 0:
            raise ValueError(
                f"available resource quantity for '{resource_id}' "
                f"must not be negative; received {available_amount}."
            )
    required_amounts: dict[str, float] = {}
    remaining_requirements: dict[str, float] = {}
    resource_consumption: dict[
        str,
        dict[str, float],
    ] = {}
    ordered_diets: dict[
        str,
        list[dict[str, Any]],
    ] = {}
    for animal_id, population in (
        region_state.animal_populations.items()
    ):
        animal_definition = registry.get(animal_id)
        required_amount = (
            calculate_population_food_requirement(
                population,
                animal_definition,
            )
        )
        required_amounts[animal_id] = required_amount
        remaining_requirements[animal_id] = required_amount
        resource_consumption[animal_id] = {}
        ordered_diets[animal_id] = sorted(
            animal_definition["diet"],
            key=lambda diet_entry: diet_entry["preference"],
            reverse=True,
        )
    maximum_diet_length = max(
        (
            len(diet)
            for diet in ordered_diets.values()
        ),
        default=0,
    )
    for preference_index in range(maximum_diet_length):
        requests_by_resource: dict[
            str,
            dict[str, float],
        ] = {}
        for animal_id, diet in ordered_diets.items():
            remaining_requirement = (
                remaining_requirements[animal_id]
            )
            if remaining_requirement <= 0:
                continue
            if preference_index >= len(diet):
                continue
            resource_id = diet[
                preference_index
            ]["resource_id"]
            resource_requests = (
                requests_by_resource.setdefault(
                    resource_id,
                    {},
                )
            )
            resource_requests[animal_id] = (
                remaining_requirement
            )
        for resource_id, resource_requests in (
            requests_by_resource.items()
        ):
            available_amount = (
                region_state.resource_quantities.get(
                    resource_id,
                    0.0,
                )
            )
            total_requested = sum(
                resource_requests.values()
            )
            if total_requested <= 0:
                continue
            allocation_ratio = min(
                1.0,
                available_amount / total_requested,
            )
            total_allocated = 0.0
            for animal_id, requested_amount in (
                resource_requests.items()
            ):
                allocated_amount = (
                    requested_amount
                    * allocation_ratio
                )
                total_allocated += allocated_amount
                remaining_requirements[animal_id] -= (
                    allocated_amount
                )
                resource_consumption[animal_id][
                    resource_id
                ] = allocated_amount
            region_state.resource_quantities[
                resource_id
            ] = max(
                0.0,
                available_amount - total_allocated,
            )
    feeding_results: dict[
        str,
        PopulationFeedingResult,
    ] = {}
    for animal_id, required_amount in (
        required_amounts.items()
    ):
        consumed_amount = sum(
            resource_consumption[animal_id].values()
        )
        if required_amount > 0:
            nutrition_ratio = (
                consumed_amount / required_amount
            )
        else:
            nutrition_ratio = 1.0
        feeding_results[animal_id] = (
            PopulationFeedingResult(
                required_amount=required_amount,
                consumed_amount=consumed_amount,
                nutrition_ratio=nutrition_ratio,
                resource_consumption=(
                    resource_consumption[animal_id]
                ),
            )
        )
    return feeding_results