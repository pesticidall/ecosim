from core.content_registry import ContentRegistry
from simulation.daily_cycle import run_day
from simulation.monthly_summary import MonthlyEcologySummary
from simulation.world_state import WorldState


def run_month(world_state: WorldState, registry: ContentRegistry) -> MonthlyEcologySummary:
    """Finish the current month through daily steps, then stop for review.

    Earlier completed days are retained. If a later day fails, the completed
    prefix remains committed and the failing date can be retried. Calling while
    review is pending returns the stored summary without advancing anything.
    """
    if world_state.pending_month_review is not None:
        year, month = world_state.pending_month_review
        return world_state.monthly_summaries[year][month]
    year, month, day = world_state.calendar.year, world_state.calendar.month, world_state.calendar.day
    prefix = world_state.daily_history.get(year, {}).get(month, {})
    if set(prefix) != set(range(1, day)):
        raise ValueError("Month advancement requires daily history from the first date of the month.")
    while (world_state.calendar.year, world_state.calendar.month) == (year, month):
        run_day(world_state, registry)
    return world_state.monthly_summaries[year][month]


def acknowledge_month_review(world_state: WorldState) -> MonthlyEcologySummary:
    """Release the month-end pause without resolving the next date."""
    if world_state.pending_month_review is None:
        raise ValueError("There is no completed month awaiting review.")
    year, month = world_state.pending_month_review
    summary = world_state.monthly_summaries[year][month]
    world_state.pending_month_review = None
    return summary
