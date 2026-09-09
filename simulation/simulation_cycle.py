from dataclasses import dataclass

from core.content_registry import ContentRegistry
from simulation.feeding import (
    PopulationFeedingResult,
    feed_region,
)
from simulation.mortality import apply_starvation_mortality
from simulation.production import apply_producer_production
from simulation.world_state import WorldState


@dataclass
class RegionCycleResult:
    production_changes: dict[str, float]
    feeding_results: dict[
        str,
        PopulationFeedingResult,
    ]
    starvation_deaths: dict[str, int]

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
        production_changes = apply_producer_production(
            region_state,
            registry,
        )
        feeding_results = feed_region(
            region_state,
            registry
        )
        starvation_deaths = apply_starvation_mortality(
            region_state,
            feeding_results,
        )
        region_results[region_id] = RegionCycleResult(
            production_changes=production_changes,
            feeding_results=feeding_results,
            starvation_deaths=starvation_deaths,
        )
    world_state.current_cycle += 1
    return CycleResult(
        cycle_number=world_state.current_cycle,
        region_results=region_results,
    )