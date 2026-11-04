"""Read-only calendar projections of actual dated simulation evidence."""

from dataclasses import dataclass

from core.content_registry import ContentRegistry
from simulation.calendar import CalendarState, Month, days_in_month
from simulation.intervention_reporting import format_intervention
from simulation.world_state import WorldState
from ui.history import format_daily_history, HISTORY_CATEGORIES


@dataclass(frozen=True)
class CalendarDay:
    year: int
    month: Month
    day: int
    status: str
    intervention_count: int


def calendar_months(world: WorldState) -> tuple[tuple[int, Month], ...]:
    months = {(world.calendar.year, world.calendar.month)}
    months.update((year, month) for year, history in world.daily_history.items() for month in history)
    months.update((record.year, record.month) for record in world.interventions)
    if world.pending_month_review is not None:
        months.add(world.pending_month_review)
    return tuple(sorted(months, reverse=True))


def calendar_days(world: WorldState, year: int, month: Month) -> tuple[CalendarDay, ...]:
    CalendarState(year, month, 1)
    history = world.daily_history.get(year, {}).get(month, {})
    current = (world.calendar.year, world.calendar.month, world.calendar.day)
    counts = {}
    for record in world.interventions:
        if (record.year, record.month) == (year, month):
            counts[record.day] = counts.get(record.day, 0) + 1
    days = []
    for day in range(1, days_in_month(year, month) + 1):
        date = (year, month, day)
        result = history.get(day)
        status = ("Completed" if result is not None else "Current" if date == current
                  else "Future" if date > current else "Unrecorded")
        # Saved evidence is authoritative once ecology has completed the date.
        count = len(result.interventions) if result is not None else counts.get(day, 0)
        days.append(CalendarDay(year, month, day, status, count))
    return tuple(days)


def calendar_day_text(world: WorldState, registry: ContentRegistry, year: int, month: Month, day: int,
                      category: str = "All events") -> str:
    CalendarState(year, month, day)
    if category not in HISTORY_CATEGORIES:
        raise ValueError("Unknown history category.")
    result = world.daily_history.get(year, {}).get(month, {}).get(day)
    if result is not None:
        return format_daily_history(result, registry, category)
    date = (year, month, day)
    current = (world.calendar.year, world.calendar.month, world.calendar.day)
    lines = [f"{day} {month.display_name}, Year {year}"]
    if date == current:
        lines.append("Current unresolved date. Ecology has not run.")
        if world.pending_month_review is not None:
            lines.append("Finish the completed month's review before advancing ecology.")
        records = [record for record in world.interventions if (record.year, record.month, record.day) == date]
        if category in ("All events", "Interventions"):
            lines.extend(format_intervention(record, registry) for record in records)
        if not records and category in ("All events", "Interventions"):
            lines.append("No interventions applied on this date.")
        if category not in ("All events", "Interventions"):
            lines.append(f"No {category.lower()} recorded before ecology runs.")
    elif date > current:
        lines.append("Future date. No ecological results have been generated.")
    else:
        lines.append("No daily evidence was recorded for this date.")
    return "\n\n".join(lines)
