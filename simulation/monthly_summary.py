from collections import Counter
from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from simulation.calendar import Month, days_in_month
if TYPE_CHECKING:
    from simulation.daily_cycle import DailyCycleResult
from simulation.daily_ecology import RegionDailySnapshot
from simulation.feeding import PopulationFeedingResult, _combine_feeding_results
from simulation.world_state import WorldState
from simulation.interventions import PopulationRemovalIntervention, PopulationIntroductionIntervention


@dataclass(frozen=True)
class RegionMonthlySummary:
    starting_state: RegionDailySnapshot
    ending_state: RegionDailySnapshot
    production_changes: dict[str, float]
    resource_consumption: dict[str, float]
    feeding_results: dict[str, PopulationFeedingResult]
    births: dict[str, int]
    starvation_deaths: dict[str, int]
    predation_deaths: dict[str, int]
    weather_day_totals: dict[str | None, int]
    hunt_outcomes: dict[str, dict[str, dict[str, int]]]
    scavenged_biomass_kg: dict[str, dict[str, float]]
    decayed_biomass_kg: dict[str, float]
    removals: dict[str, int] = field(default_factory=dict)
    introductions: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class MonthlyEcologySummary:
    year: int
    month: Month
    days: tuple["DailyCycleResult", ...]
    region_results: dict[str, RegionMonthlySummary]


def _add_totals(target, values):
    for key, value in values.items():
        target[key] = target.get(key, 0) + value


def summarize_month(world: WorldState, year: int, month: Month) -> MonthlyEcologySummary:
    """Read a complete month of daily evidence without running ecology again.

    Live regions and current content are not consulted. Food coverage combines
    daily survivor nutrition; physical resource expenditure is recorded separately
    so food already eaten by subsequently killed prey is still accounted for.
    """
    if isinstance(year, bool) or not isinstance(year, int):
        raise TypeError("Summary year must be an integer.")
    if year < 1 or not isinstance(month, Month):
        raise ValueError("Summary requires a positive year and a Month.")
    length = days_in_month(year, month)
    history = world.daily_history.get(year, {}).get(month, {})
    if set(history) != set(range(1, length + 1)):
        raise ValueError("Monthly summaries require complete daily history for every date in the month.")
    days = tuple(history[day] for day in range(1, length + 1))
    region_ids = set(days[0].region_results)
    for day_number, result in enumerate(days, 1):
        if (result.year, result.month, result.day) != (year, month, day_number):
            raise ValueError("Daily history contains a mismatched calendar date.")
        if set(result.region_results) != region_ids:
            raise ValueError("Monthly summaries require consistent regions across the recorded month.")
        if any((local.year, local.month, local.day) != (year, month, day_number)
               for local in result.region_results.values()):
            raise ValueError("Regional daily evidence contains a mismatched calendar date.")
    regions = {}
    for region_id in sorted(region_ids):
        local_days = [day.region_results[region_id] for day in days]
        production, consumption, births, starvation, predation = {}, {}, {}, {}, {}
        hunts, scavenging, decay = {}, {}, {}
        removals, introductions = {}, {}
        for local in local_days:
            _add_totals(production, local.production_changes)
            _add_totals(births, local.demographics.births)
            _add_totals(starvation, local.demographics.starvation_deaths)
            resources = (local.starting_state.resource_quantities.keys()
                         | local.ending_state.resource_quantities.keys() | local.production_changes.keys())
            _add_totals(consumption, {
                key: (local.starting_state.resource_quantities.get(key, 0.0)
                      + local.production_changes.get(key, 0.0) - local.ending_state.resource_quantities.get(key, 0.0))
                for key in resources
            })
            for habitat_id, rounds in local.food_web.hunting_rounds.items():
                for predator_id, hunting in rounds.items():
                    counts = hunts.setdefault(habitat_id, {}).setdefault(predator_id, {})
                    for attempt in hunting.attempts:
                        status = attempt.hunt.outcome.status.value
                        counts[status] = counts.get(status, 0) + 1
                    for meal in hunting.meals:
                        predation[meal.death.animal_id] = predation.get(meal.death.animal_id, 0) + meal.death.count
            for habitat_id, allocations in local.food_web.scavenging_results.items():
                _add_totals(scavenging.setdefault(habitat_id, {}), {
                    key: value.consumed_biomass_kg for key, value in allocations.items()
                })
            for habitat_id, deposits in local.food_web.reserve_deposits.items():
                _add_totals(scavenging.setdefault(habitat_id, {}), {
                    animal: carrion.consumed_biomass_kg for animal, (_, carrion) in deposits.items()
                })
            for habitat_id, meals in local.food_web.growth_meals.items():
                if habitat_id is not None:
                    _add_totals(scavenging.setdefault(habitat_id, {}), {
                        animal: meal.carrion.consumed_biomass_kg for animal, meal in meals.items()
                    })
            _add_totals(decay, {
                key: sum(record.decayed_biomass_kg for record in records)
                for key, records in local.carrion_decay.items()
            })
        for day in days:
            for record in day.interventions:
                if isinstance(record, PopulationRemovalIntervention) and record.region_id == region_id:
                    removals[record.animal_id] = removals.get(record.animal_id, 0) + record.quantity
                if isinstance(record, PopulationIntroductionIntervention) and record.region_id == region_id:
                    introductions[record.animal_id] = introductions.get(record.animal_id, 0) + record.quantity
        starting = deepcopy(local_days[0].starting_state)
        # First-date interventions precede ecology's opening snapshot. Restore
        # the month's pre-intervention population so the monthly ledger reconciles.
        for record in days[0].interventions:
            if isinstance(record, PopulationRemovalIntervention) and record.region_id == region_id:
                starting.animal_populations[record.animal_id] = starting.animal_populations.get(record.animal_id, 0) + record.quantity
            if isinstance(record, PopulationIntroductionIntervention) and record.region_id == region_id:
                starting.animal_populations[record.animal_id] = starting.animal_populations.get(record.animal_id, 0) - record.quantity
        regions[region_id] = RegionMonthlySummary(
            starting, deepcopy(local_days[-1].ending_state),
            production, consumption,
            _combine_feeding_results([local.food_web.regional_feeding for local in local_days]),
            births, starvation, predation, dict(Counter(local.active_weather_id for local in local_days)),
            hunts, scavenging, decay, removals, introductions,
        )
    return MonthlyEcologySummary(year, month, days, regions)
