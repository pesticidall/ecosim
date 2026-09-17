from pathlib import Path

from core.content_loader import load_json_file
from simulation.world_state import RegionState, WorldState


def load_scenario(
    scenario_path: Path,
) -> WorldState:
    scenario_data = load_json_file(scenario_path)
    world_state = WorldState(
        random_seed=scenario_data["random_seed"],
        scenario_name=scenario_data["name"],
        scenario_id=scenario_data.get("scenario_id", ""),
        scenario_description=scenario_data.get("description", ""),
    )
    for region_data in scenario_data["regions"]:
        region_state = RegionState(
            definition_id=region_data["definition_id"],
            active_weather_id=region_data["active_weather_id"],
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
        world_state.regions[
            region_state.definition_id
        ] = region_state
    return world_state