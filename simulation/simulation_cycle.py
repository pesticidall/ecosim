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
    _combine_feeding_results,
)
from simulation.hunting_cycle import run_region_hunting
from simulation.habitat_hunting import HabitatHuntingRound
from simulation.group_hunting_cycle import HabitatGroupHuntingRound
from simulation.mortality import apply_starvation_mortality
from simulation.production import apply_producer_production
from simulation.reproduction import apply_reproduction
from simulation.scavenging import ScavengingResult, run_region_scavenging
from simulation.carrion import CarrionDecay, CarrionDeposit
from simulation.condition_cohorts import InjuryCohort
from simulation.carrion_cycle import record_starvation_carrion, run_region_carrion_decay
from simulation.deaths import DeathRecord
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
    hunting_rounds: dict[str, dict[str, HabitatHuntingRound | HabitatGroupHuntingRound]] = field(default_factory=dict)
    predation_deaths: dict[str, int] = field(default_factory=dict)
    scavenging_results: dict[str, dict[str, ScavengingResult]] = field(default_factory=dict)
    carrion_decay_results: dict[str, tuple[CarrionDecay, ...]] = field(default_factory=dict)
    starvation_death_records: dict[str, tuple[DeathRecord, ...]] = field(default_factory=dict)
    ending_carrion: dict[str, tuple[CarrionDeposit, ...]] = field(default_factory=dict)
    ending_injury_cohorts: dict[str, dict[str, tuple[InjuryCohort, ...]]] = field(default_factory=dict)
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
    if world_state.pending_month_review is not None:
        raise ValueError("Review the completed month before advancing another month.")
    if world_state.calendar.day != 1 or world_state.daily_history.get(
        world_state.calendar.year, {},
    ).get(world_state.calendar.month):
        raise ValueError("The legacy monthly runner cannot resolve a partially completed month; use daily advancement.")
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
        hunting_rounds = run_region_hunting(
            region_state, registry, habitat_feeding_results, world_state.random_generator,
        )
        predation_deaths: dict[str, int] = {}
        for local_rounds in hunting_rounds.values():
            for hunting_round in local_rounds.values():
                for meal in hunting_round.meals:
                    animal_id = meal.death.animal_id
                    predation_deaths[animal_id] = predation_deaths.get(animal_id, 0) + meal.death.count
        scavenging_results = run_region_scavenging(region_state, registry, habitat_feeding_results)
        carrion_decay_results = run_region_carrion_decay(region_state, registry)
        if habitat_feeding_results:
            feeding_results = _combine_feeding_results(list(habitat_feeding_results.values()))
        populations_before_starvation = {
            habitat_id: dict(habitat.animal_populations)
            for habitat_id, habitat in region_state.habitats.items()
        }
        starvation_deaths = apply_starvation_mortality(
            region_state,
            feeding_results,
            habitat_feeding_results,
        )
        starvation_death_records = record_starvation_carrion(
            region_state, registry, populations_before_starvation,
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
            hunting_rounds=hunting_rounds,
            predation_deaths=predation_deaths,
            scavenging_results=scavenging_results,
            carrion_decay_results=carrion_decay_results,
            starvation_death_records=starvation_death_records,
            ending_carrion={habitat_id: tuple(habitat.carrion_deposits)
                            for habitat_id, habitat in region_state.habitats.items()},
            ending_injury_cohorts={habitat_id: dict(habitat.injury_cohorts)
                                  for habitat_id, habitat in region_state.habitats.items()},
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
