from dataclasses import dataclass, field

from core.content_registry import ContentRegistry
from simulation.feeding import (
    PopulationFeedingResult,
    feed_region,
)
from simulation.mortality import apply_starvation_mortality
from simulation.production import apply_producer_production
from simulation.reproduction import apply_reproduction
from simulation.world_state import WorldState


@dataclass
class RegionCycleResult:
    production_changes: dict[str, float]
    feeding_results: dict[
        str,
        PopulationFeedingResult,
    ]
    starvation_deaths: dict[str, int]
    births: dict[str, int]
    starting_animal_populations: dict[str, int] = field(default_factory=dict)
    ending_animal_populations: dict[str, int] = field(default_factory=dict)
    starting_resource_quantities: dict[str, float] = field(default_factory=dict)
    ending_resource_quantities: dict[str, float] = field(default_factory=dict)
    active_weather_id: str | None = None

@dataclass
class CycleResult:
    cycle_number: int
    region_results: dict[
        str,
        RegionCycleResult
    ]

def run_cycle(
    world_state: WorldState,
    registry: ContentRegistry,
) -> CycleResult:
    region_results: dict[
        str,
        RegionCycleResult,
    ] = {}
    for region_id, region_state in world_state.regions.items():
        starting_animal_populations = dict(region_state.animal_populations)
        starting_resource_populations = dict(region_state.resource_quantities)
        production_changes = apply_producer_production(
            region_state,
            registry,
        )
        feeding_results = feed_region(
            region_state,
            registry,
        )
        starvation_deaths = apply_starvation_mortality(
            region_state,
            feeding_results,
        )
        births = apply_reproduction(
            region_state,
            registry,
            feeding_results,
        )
        region_results[region_id] = RegionCycleResult(
            production_changes=production_changes,
            feeding_results=feeding_results,
            starvation_deaths=starvation_deaths,
            births=births,
            starting_animal_populations=starting_animal_populations,
            ending_animal_populations=dict(region_state.animal_populations),
            starting_resource_quantities=starting_resource_populations,
            ending_resource_quantities=dict(region_state.resource_quantities),
            active_weather_id=region_state.active_weather_id,
        )
        
    world_state.current_cycle += 1
    return CycleResult(
        cycle_number=world_state.current_cycle,
        region_results=region_results,
    )