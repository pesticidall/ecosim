from pathlib import Path

from core.content_loader import load_json_file
from core.content_registry import ContentRegistry
from simulation.habitats import (
    distribute_resource_by_production,
    select_initial_habitat_id,
)
from simulation.weather import validate_weather_weights
from simulation.world_state import HabitatState, RegionState, WorldState


def load_scenario(
    scenario_path: Path,
    registry: ContentRegistry | None = None,
) -> WorldState:
    """Build an independent world state from a scenario definition."""
    scenario_data = load_json_file(scenario_path)
    world_state = WorldState(
        random_seed=scenario_data["random_seed"],
        scenario_name=scenario_data["name"],
        scenario_id=scenario_data.get("scenario_id", ""),
        scenario_description=scenario_data.get("description", ""),
    )
    for region_data in scenario_data["regions"]:
        weather_weights = dict(
            region_data.get(
                "weather_weights",
                {
                    region_data["active_weather_id"]: 1.0,
                },
            ),
        )
        validate_weather_weights(weather_weights)
        if registry is not None:
            for weather_id in weather_weights:
                try:
                    weather_definition = registry.get(weather_id)
                except KeyError:
                    raise ValueError(
                        f"Region '{region_data['definition_id']}' "
                        f"references unknown weather "
                        f"'{weather_id}'."
                    ) from None
                if weather_definition["entity_type"] != "weather":
                    raise ValueError(
                        f"Region '{region_data['definition_id']}' "
                        f"references non-weather content "
                        f"'{weather_id}' in weather_weights."
                    )
        habitat_states: dict[str, HabitatState] = {}
        if registry is not None:
            region_definition = registry.get(
                region_data["definition_id"]
            )
            habitat_states = {
                    habitat_id: HabitatState(
                        definition_id=habitat_id,
                    )
                    for habitat_id in region_definition["habitat_ids"]
            }
            for animal_id, population in region_data[
                "animal_populations"
            ].items():
                animal_definition = registry.get(animal_id)
                habitat_id = select_initial_habitat_id(
                    animal_definition,
                    region_definition,
                )
                habitat_states[
                    habitat_id
                ].animal_populations[animal_id] = population
            for producer_id, population in region_data[
                "producer_populations"
            ].items():
                producer_definition = registry.get(producer_id)
                habitat_id = select_initial_habitat_id(
                    producer_definition,
                    region_definition,
                )
                habitat_states[
                    habitat_id
                ].producer_populations[producer_id] = population
        region_state = RegionState(
            definition_id=region_data["definition_id"],
            active_weather_id=region_data["active_weather_id"],
            weather_weights=weather_weights,
            habitats=habitat_states,
            animal_populations=dict(
                region_data["animal_populations"],
            ),
            producer_populations=dict(
                region_data["producer_populations"],
            ),
            resource_quantities=dict(
                region_data["resource_quantities"],
            )
        )
        if registry is not None:
            producer_definitions = {
                producer_id: registry.get(producer_id)
                for producer_id in region_data[
                    "producer_populations"
                ]
            }
            for resource_id, quantity in region_data[
                "resource_quantities"
            ].items():
                distribute_resource_by_production(
                    region_state,
                    resource_id,
                    quantity,
                    producer_definitions,
                )
        world_state.regions[
            region_state.definition_id
        ] = region_state
    return world_state
