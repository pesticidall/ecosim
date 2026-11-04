from copy import copy
from dataclasses import dataclass, fields, replace
from random import Random

from core.content_registry import ContentRegistry
from simulation.calendar import Month, days_in_month
from simulation.monthly_summary import summarize_month
from simulation.daily_ecology import RegionDailyEcologyResult, resolve_region_daily_ecology
from simulation.world_state import RegionState, WorldState
from simulation.interventions import InterventionRecord
from simulation.intervention_resources import InterventionResources, recover_intervention_resources


@dataclass(frozen=True)
class DailyCycleResult:
    """Record the date completed after every region finishes its daily stages."""

    year: int
    month: Month
    day: int
    region_results: dict[str, RegionDailyEcologyResult]
    interventions: tuple[InterventionRecord, ...] = ()
    intervention_resources_before: InterventionResources | None = None
    intervention_resources_after: InterventionResources | None = None


def _copy_state_containers(state):
    """Isolate mutable state containers while retaining immutable history records.

    Current state dictionaries contain scalar values, frozen records, or tuples
    of frozen records. Region habitats require their own container copies below.
    Retaining history record identities preserves duplicate-commit guards.
    """
    staged = replace(state)
    for item in fields(state):
        value = getattr(state, item.name)
        if isinstance(value, (dict, list)):
            setattr(staged, item.name, copy(value))
    return staged


def _stage_region(region: RegionState) -> RegionState:
    staged = _copy_state_containers(region)
    staged.habitats = {key: _copy_state_containers(habitat) for key, habitat in region.habitats.items()}
    return staged


def _commit_region(region: RegionState, staged: RegionState) -> None:
    # Preserve the region and habitat objects used by callers. Stages do not
    # add or remove habitats; only their saved state fields are replaced.
    for key, habitat in region.habitats.items():
        for item in fields(habitat):
            setattr(habitat, item.name, getattr(staged.habitats[key], item.name))
    for item in fields(region):
        if item.name != "habitats":
            setattr(region, item.name, getattr(staged, item.name))


def run_day(world_state: WorldState, registry: ContentRegistry) -> DailyCycleResult:
    """Resolve the next unresolved date, committing all regions together.

    Failure leaves live state, calendar, history, and the random stream intact.
    Complete months save a summary and pause for review. Legacy current_cycle
    and monthly_history retain their existing meaning. No presentation timing
    enters this operation.
    """
    if world_state.pending_month_review is not None:
        raise ValueError("Review the completed month before advancing another day.")
    calendar = replace(world_state.calendar)
    year, month, day = calendar.year, calendar.month, calendar.day
    if day in world_state.daily_history.get(year, {}).get(month, {}):
        raise ValueError("This calendar date has already been completed.")
    if month in world_state.monthly_history.get(year, {}):
        raise ValueError("This calendar month has already been completed by the monthly runner.")
    random_source = Random(0)
    random_source.setstate(world_state.random_generator.getstate())
    staged = {key: _stage_region(region) for key, region in world_state.regions.items()}
    results = {
        key: resolve_region_daily_ecology(staged[key], registry, calendar, random_source)
        for key in sorted(staged)
    }
    resources = world_state.intervention_resources
    completed = DailyCycleResult(year, month, day, results, tuple(
        record for record in world_state.interventions if (record.year, record.month, record.day) == (year, month, day)
    ), resources, resources)
    summary = None
    if day == days_in_month(year, month):
        recorded_days = {**world_state.daily_history.get(year, {}).get(month, {}), day: completed}
        # A scenario started mid-month has no evidence for its earlier dates.
        # Do not invent a full-month report for that initial partial month.
        if set(recorded_days) == set(range(1, day + 1)):
            resources = recover_intervention_resources(resources, year, month)
            completed = replace(completed, intervention_resources_after=resources)
            recorded_days[day] = completed
            preview = copy(world_state)
            preview.daily_history = {
                **world_state.daily_history,
                year: {**world_state.daily_history.get(year, {}), month: recorded_days},
            }
            summary = summarize_month(preview, year, month)
    calendar.advance_day()
    for key in sorted(staged):
        _commit_region(world_state.regions[key], staged[key])
    world_state.random_generator.setstate(random_source.getstate())
    world_state.daily_history.setdefault(year, {}).setdefault(month, {})[day] = completed
    world_state.intervention_resources = resources
    if summary is not None:
        world_state.monthly_summaries.setdefault(year, {})[month] = summary
        world_state.pending_month_review = (year, month)
    world_state.calendar.year = calendar.year
    world_state.calendar.month = calendar.month
    world_state.calendar.day = calendar.day
    return completed
