from dataclasses import dataclass, field
from random import Random

from core.content_registry import ContentRegistry
from simulation.calendar import CalendarState, Month, days_in_month
from simulation.carrion import CarrionDecay, CarrionDeposit
from simulation.condition_cohorts import InjuryCohort
from simulation.carrion_cycle import run_region_carrion_decay
from simulation.daily_feeding import DailyFoodWebResult, feed_region_food_web_for_day
from simulation.daily_demographics import RegionDailyDemographicsResult, apply_region_daily_demographics
from simulation.production import apply_producer_production
from simulation.weather import generate_monthly_weather_schedule, validate_weather_weights
from simulation.world_state import RegionState
from simulation.nutrition import NutritionalState
from simulation.growth import GrowthCohort


@dataclass(frozen=True)
class RegionDailySnapshot:
    animal_populations: dict[str, int]
    resource_quantities: dict[str, float]
    carrion: dict[str, tuple[CarrionDeposit, ...]]
    injury_cohorts: dict[str, dict[str, tuple[InjuryCohort, ...]]]
    nutritional_states: dict[str, dict[str, NutritionalState]] = field(default_factory=dict)
    growth_cohorts: dict[str | None, dict[str, tuple[GrowthCohort, ...]]] = field(default_factory=dict)
    growth_loss_phases: dict[str | None, dict[str, float]] = field(default_factory=dict)


def _snapshot(region: RegionState) -> RegionDailySnapshot:
    return RegionDailySnapshot(
        dict(region.animal_populations), dict(region.resource_quantities),
        {key: tuple(habitat.carrion_deposits) for key, habitat in region.habitats.items()},
        {key: dict(habitat.injury_cohorts) for key, habitat in region.habitats.items()},
        {key: dict(habitat.nutritional_states) for key, habitat in region.habitats.items()},
        ({key: dict(habitat.growth_cohorts) for key, habitat in region.habitats.items()}
         if region.habitats else {None: dict(region.growth_cohorts)}),
        ({key: dict(habitat.growth_loss_phases) for key, habitat in region.habitats.items()}
         if region.habitats else {None: dict(region.growth_loss_phases)}),
    )


@dataclass(frozen=True)
class RegionDailyEcologyResult:
    """Retain dated evidence for daily weather, resources, meals, and decay."""

    year: int
    month: Month
    day: int
    active_weather_id: str | None
    production_changes: dict[str, float]
    food_web: DailyFoodWebResult
    carrion_decay: dict[str, tuple[CarrionDecay, ...]]
    demographics: RegionDailyDemographicsResult
    starting_state: RegionDailySnapshot
    ending_state: RegionDailySnapshot


def _select_daily_weather(region: RegionState, registry: ContentRegistry, random_source: Random) -> str | None:
    if region.weather_weights:
        validate_weather_weights(region.weather_weights)
        # Validate references before consuming randomness or changing weather.
        for weather_id in region.weather_weights:
            registry.get(weather_id)
        return generate_monthly_weather_schedule(
            dict(sorted(region.weather_weights.items())), 1, random_source,
        ).daily_weather_ids[0]
    if region.active_weather_id is not None:
        registry.get(region.active_weather_id)
    return region.active_weather_id


def resolve_region_daily_ecology(
    region: RegionState,
    registry: ContentRegistry,
    calendar: CalendarState,
    random_source: Random,
) -> RegionDailyEcologyResult:
    """Resolve the daily resource and food-web stages once for this date.

    Weather selected here affects both today's production and today's hunts.
    Production precedes meals; remaining carrion decays after scavenging.
    Demographics accumulate after meals and decay. This mutates the region but
    does not advance the date or write completed-day history. A future daily
    orchestrator owns those steps. Invoke instead of separate daily stages.
    """
    year, month, day = calendar.year, calendar.month, calendar.day
    starting_state = _snapshot(region)
    region.active_weather_id = _select_daily_weather(region, registry, random_source)
    production = apply_producer_production(region, registry, days=1)
    feeding = feed_region_food_web_for_day(region, registry, calendar, random_source)
    decay = run_region_carrion_decay(region, registry, days_in_period=days_in_month(year, month))
    demographics = apply_region_daily_demographics(region, registry, feeding)
    return RegionDailyEcologyResult(
        year, month, day, region.active_weather_id, production, feeding, decay, demographics,
        starting_state, _snapshot(region),
    )
