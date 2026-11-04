from dataclasses import dataclass, field
from random import Random

from core.content_registry import ContentRegistry
from simulation.calendar import CalendarState, Month, days_in_month
from simulation.feeding import (
    PopulationFeedingResult, feed_region_with_habitat_results, _combine_feeding_results,
)
from simulation.group_hunting_cycle import HabitatGroupHuntingRound
from simulation.habitat_hunting import HabitatHuntingRound
from simulation.hunting_cycle import run_region_hunting
from simulation.scavenging import ScavengingResult, run_region_scavenging
from simulation.world_state import RegionState
from simulation.nutrition import ReserveDeposit, draw_food_reserves, replenish_food_reserves
from simulation.growth_feeding import GrowthMeal, feed_growth


@dataclass(frozen=True)
class DailyFeedingResult:
    """Retain the resolved date and resource feeding for one daily stage."""

    year: int
    month: Month
    day: int
    regional_feeding: dict[str, PopulationFeedingResult]
    habitat_feeding: dict[str, dict[str, PopulationFeedingResult]]


def feed_region_for_day(
    region: RegionState,
    registry: ContentRegistry,
    calendar: CalendarState,
) -> DailyFeedingResult:
    """Allocate one date's resource food without completing that date.

    Existing per-cycle content represents a monthly allowance. Divide it by
    this month's actual length, including leap days. Later daily stages must
    supplement this same demand before mortality and calendar advancement.
    The caller invokes this mutating stage once per region and date.
    """
    year, month, day = calendar.year, calendar.month, calendar.day
    regional, habitats = feed_region_with_habitat_results(
        region, registry, period_fraction=1.0 / days_in_month(year, month),
    )
    return DailyFeedingResult(year, month, day, regional, habitats)


@dataclass(frozen=True)
class DailyFoodWebResult(DailyFeedingResult):
    """Record one date's resource, hunting, and scavenging nutrition."""

    hunting_rounds: dict[str, dict[str, HabitatHuntingRound | HabitatGroupHuntingRound]]
    scavenging_results: dict[str, dict[str, ScavengingResult]]
    reserve_deposits: dict[str, dict[str, ReserveDeposit]] = field(default_factory=dict)
    growth_meals: dict[str | None, dict[str, GrowthMeal]] = field(default_factory=dict)


def feed_region_food_web_for_day(
    region: RegionState,
    registry: ContentRegistry,
    calendar: CalendarState,
    random_source: Random,
) -> DailyFoodWebResult:
    """Resolve daily food in ecological order without advancing the calendar.

    Invoke instead of the resource-only stage, once per region and date. Food
    demand shares one interval across resources, hunts, and scavengers. This
    does not yet resolve production, weather selection, decay, or demographics.
    """
    resource_feeding = feed_region_for_day(region, registry, calendar)
    local = resource_feeding.habitat_feeding
    draw_food_reserves(region, registry, local)
    period_fraction = 1.0 / days_in_month(resource_feeding.year, resource_feeding.month)
    hunts = run_region_hunting(region, registry, local, random_source, period_fraction=period_fraction)
    scavenging = run_region_scavenging(region, registry, local)
    growth_meals = feed_growth(region, registry, local, resource_feeding.regional_feeding)
    deposits = replenish_food_reserves(region, registry, local)
    regional = (_combine_feeding_results(list(local.values())) if local
                else resource_feeding.regional_feeding)
    return DailyFoodWebResult(
        resource_feeding.year, resource_feeding.month, resource_feeding.day,
        regional, local, hunts, scavenging, deposits, growth_meals,
    )
