from dataclasses import dataclass, field

from core.content_registry import ContentRegistry
from simulation.activity import calculate_activity_totals
from simulation.calendar import (
    ActivityPhase,
    Month,
    days_in_month,
)
from simulation.feeding import (
    PopulationFeedingResult,
    feed_region_with_habitat_results,
)
from simulation.mortality import apply_starvation_mortality
from simulation.production import apply_producer_production
from simulation.reproduction import apply_reproduction
from simulation.weather import (
    MonthlyWeatherSchedule,
    generate_monthly_weather_schedule,
)
from simulation.world_state import WorldState


@dataclass
class RegionCycleResult:
    """Capture all changes and measurements for one region in a cycle."""

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
    weather_schedule: MonthlyWeatherSchedule | None = None
    animal_activity_totals: dict[
        str,
        dict[ActivityPhase, float],
    ] = field(default_factory=dict)

@dataclass
class CycleResult:
    """Capture the calendar context and regional results of one cycle."""

    cycle_number: int
    region_results: dict[
        str,
        RegionCycleResult
    ]
    year: int = 1
    month: Month = Month.JANUARY
    days_in_month: int = 31
    activity_phase_totals: dict[
        ActivityPhase,
        int,
    ] = field(default_factory=dict)

def run_cycle(
    world_state: WorldState,
    registry: ContentRegistry,
) -> CycleResult:
    """Resolve one monthly cycle and store its result in world history."""
    completed_year = world_state.calendar.year
    completed_month = world_state.calendar.month
    completed_days = days_in_month(
        completed_year,
        completed_month
    )
    activity_phase_totals = {
        ActivityPhase.DAY: completed_days,
        ActivityPhase.NIGHT: completed_days,
    }
    region_results: dict[
        str,
        RegionCycleResult,
    ] = {}
    for region_id, region_state in world_state.regions.items():
        weather_schedule: MonthlyWeatherSchedule | None = None
        weather_weights = region_state.weather_weights
        if not weather_weights and region_state.active_weather_id is not None:
            weather_weights = {
                region_state.active_weather_id: 1.0,
            }
        if weather_weights:
            weather_schedule = generate_monthly_weather_schedule(
                weather_weights,
                completed_days,
                world_state.random_generator,
            )
        starting_animal_populations = dict(region_state.animal_populations)
        starting_resource_populations = dict(region_state.resource_quantities)
        production_changes = apply_producer_production(
            region_state,
            registry,
            days=completed_days,
            weather_day_totals=(
                weather_schedule.weather_day_totals
                if weather_schedule is not None
                else None
            ),
        )
        feeding_results, habitat_feeding_results = (
            feed_region_with_habitat_results(
                region_state,
                registry,
            )
        )
        starvation_deaths = apply_starvation_mortality(
            region_state,
            feeding_results,
            habitat_feeding_results,
        )
        births = apply_reproduction(
            region_state,
            registry,
            feeding_results,
            habitat_feeding_results,
        )
        animal_activity_totals = {
            animal_id: calculate_activity_totals(
                registry.get(animal_id).get(
                    "activity_pattern",
                    "flexible",
                ),
            activity_phase_totals,
        )
        for animal_id in region_state.animal_populations
        }
        region_results[region_id] = RegionCycleResult(
            production_changes=production_changes,
            feeding_results=feeding_results,
            starvation_deaths=starvation_deaths,
            births=births,
            starting_animal_populations=starting_animal_populations,
            ending_animal_populations=dict(region_state.animal_populations),
            starting_resource_quantities=starting_resource_populations,
            ending_resource_quantities=dict(region_state.resource_quantities),
            animal_activity_totals=animal_activity_totals,
            active_weather_id=region_state.active_weather_id,
            weather_schedule=weather_schedule,
        )
        
    world_state.current_cycle += 1
    world_state.calendar.advance_month()
    cycle_result = CycleResult(
        cycle_number=world_state.current_cycle,
        region_results=region_results,
        year=completed_year,
        month=completed_month,
        days_in_month=completed_days,
        activity_phase_totals=activity_phase_totals,
    )
    world_state.monthly_history.setdefault(
        completed_year,
        {},
    )[completed_month] = cycle_result
    return cycle_result
