from core.content_registry import ContentRegistry
from simulation.daily_cycle import run_day
from simulation.monthly_cycle import acknowledge_month_review
from simulation.monthly_reporting import format_monthly_ecology_report
from simulation.world_state import WorldState
from ui.history import HistoryEntry, format_daily_history
from simulation.interventions import add_supplementary_food, remove_population, introduce_population
from simulation.intervention_reporting import format_supplementary_food, format_intervention
from ui.calendar_view import calendar_months, calendar_days, calendar_day_text


class SimulationController:
    """Advance at most one ecological date per presentation callback."""

    def __init__(self, world: WorldState, registry: ContentRegistry):
        self.world = world
        self.registry = registry
        self.running = False
        self._target_month = None
        self.report_text = world.scenario_description or "Choose a habitat to inspect its populations and resources."
        if world.pending_month_review is not None:
            year, month = world.pending_month_review
            self.report_text = format_monthly_ecology_report(world.monthly_summaries[year][month], registry)

    def _advance(self):
        try:
            result = run_day(self.world, self.registry)
        except Exception:
            self.running = False
            raise
        if self.world.pending_month_review is not None:
            self.running = False
            year, month = self.world.pending_month_review
            self.report_text = format_monthly_ecology_report(self.world.monthly_summaries[year][month], self.registry)
        else:
            self.report_text = format_daily_history(result, self.registry)
        return result

    def step_day(self):
        if self.running:
            raise ValueError("Pause month play before stepping a day.")
        return self._advance()

    def play_month(self):
        if self.world.pending_month_review is not None:
            raise ValueError("Review the completed month before continuing.")
        self._target_month = (self.world.calendar.year, self.world.calendar.month)
        self.running = True

    def pause(self):
        self.running = False

    def tick(self):
        if not self.running:
            return None
        result = self._advance()
        if (self.world.calendar.year, self.world.calendar.month) != self._target_month:
            self.running = False
        return result

    def acknowledge_review(self):
        if self.running:
            raise ValueError("Pause before acknowledging a report.")
        return acknowledge_month_review(self.world)

    def history_entries(self) -> tuple[HistoryEntry, ...]:
        entries = [HistoryEntry("day", year, month, day)
                   for year, months in self.world.daily_history.items()
                   for month, days in months.items() for day in days]
        entries.extend(HistoryEntry("month", year, month)
                       for year, months in self.world.monthly_summaries.items() for month in months)
        return tuple(sorted(entries, key=lambda entry: (entry.year, entry.month, entry.day if entry.kind == "day" else 32), reverse=True))

    def add_food(self, region_id, habitat_id, resource_id, amount_kg):
        if self.running:
            raise ValueError("Pause month play before applying supplementary food.")
        record = add_supplementary_food(self.world, self.registry, region_id, habitat_id, resource_id, amount_kg)
        self.report_text = format_supplementary_food(record, self.registry) + "\n\nApplied on the next unresolved date; ecology has not advanced."
        return record

    def remove_animals(self, region_id, habitat_id, animal_id, quantity):
        if self.running:
            raise ValueError("Pause month play before removing animals.")
        record = remove_population(self.world, self.registry, region_id, habitat_id, animal_id, quantity)
        self.report_text = format_intervention(record, self.registry) + "\n\nRemoved from the ecosystem; no carrion or death was generated."
        return record

    def introduce_animals(self, region_id, habitat_id, animal_id, quantity):
        if self.running:
            raise ValueError("Pause month play before introducing animals.")
        record = introduce_population(self.world, self.registry, region_id, habitat_id, animal_id, quantity)
        self.report_text = format_intervention(record, self.registry) + "\n\nHealthy animals introduced on the current unresolved date; ecology has not advanced."
        return record

    def calendar_months(self):
        return calendar_months(self.world)

    def calendar_days(self, year, month):
        return calendar_days(self.world, year, month)

    def calendar_day_text(self, year, month, day, category="All events"):
        return calendar_day_text(self.world, self.registry, year, month, day, category)

    def history_text(self, entry: HistoryEntry | None = None) -> str:
        if entry is None:
            entry = next((item for item in self.history_entries() if item.kind == "day"), None)
            if entry is None:
                return "Completed dates and monthly reports will appear here as the simulation advances."
        if entry.kind == "day":
            return format_daily_history(self.world.daily_history[entry.year][entry.month][entry.day], self.registry)
        if entry.kind == "month":
            return format_monthly_ecology_report(self.world.monthly_summaries[entry.year][entry.month], self.registry)
        raise ValueError("Unknown history entry kind.")
