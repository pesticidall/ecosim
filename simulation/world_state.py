from dataclasses import dataclass, field
from random import Random
from typing import TYPE_CHECKING

from simulation.calendar import CalendarState, Month
from simulation.intervention_resources import InterventionResources

if TYPE_CHECKING:
    from simulation.growth import GrowthCohort
    from simulation.interventions import InterventionRecord
    from simulation.nutrition import NutritionalState
    from simulation.monthly_summary import MonthlyEcologySummary
    from simulation.daily_cycle import DailyCycleResult
    from simulation.daily_demographics import DemographicCarry
    from simulation.group_conditions import GroupConditionChange
    from simulation.condition_cohorts import InjuryCohort
    from simulation.habitat_hunting import HabitatHuntAttempt
    from simulation.group_hunting_cycle import HabitatGroupHuntAttempt
    from simulation.carrion import CarrionDeposit
    from simulation.predation import PredationMeal
    from simulation.simulation_cycle import CycleResult


@dataclass
class HabitatState:
    """Hold mutable populations, resources, and conditions for one habitat."""

    definition_id: str
    animal_populations: dict[str, int] = field(
        default_factory=dict,
    )
    producer_populations: dict[str, int] = field(
        default_factory=dict,
    )
    resource_quantities: dict[str, float] = field(
        default_factory=dict,
    )
    carrion_deposits: list["CarrionDeposit"] = field(default_factory=list)
    predation_meals: list["PredationMeal"] = field(default_factory=list)
    hunt_history: list["HabitatHuntAttempt | HabitatGroupHuntAttempt"] = field(default_factory=list)
    injury_cohorts: dict[str, tuple["InjuryCohort", ...]] = field(default_factory=dict)
    group_condition_history: list["GroupConditionChange"] = field(default_factory=list)
    demographic_carry: dict[str, "DemographicCarry"] = field(default_factory=dict)
    colony_populations: dict[str, int] = field(default_factory=dict)
    nutritional_states: dict[str, "NutritionalState"] = field(default_factory=dict)
    growth_cohorts: dict[str, tuple["GrowthCohort", ...]] = field(default_factory=dict)
    growth_loss_phases: dict[str, float] = field(default_factory=dict)


@dataclass
class RegionState:
    """Hold the mutable populations, resources, and weather of one region."""

    definition_id: str
    active_weather_id: str | None = None
    weather_weights: dict[str, float] = field(
        default_factory=dict,
    )
    habitats: dict[str, HabitatState] = field(
        default_factory=dict,
    )
    animal_populations: dict[str, int] = field(
        default_factory=dict,
    )
    producer_populations: dict[str, int] = field(
        default_factory=dict,
    )
    resource_quantities: dict[str, float] = field(
        default_factory=dict,
    )

    demographic_carry: dict[str, "DemographicCarry"] = field(default_factory=dict)
    colony_populations: dict[str, int] = field(default_factory=dict)
    growth_cohorts: dict[str, tuple["GrowthCohort", ...]] = field(default_factory=dict)
    growth_loss_phases: dict[str, float] = field(default_factory=dict)


@dataclass
class WorldState:
    """Hold the complete mutable state and history of one simulation run."""

    random_seed: int
    random_generator: Random = field(
        init=False,
        repr=False,
        compare=False,
    )
    current_cycle: int = 0
    calendar: CalendarState = field(
        default_factory=CalendarState,
    )
    regions: dict[str, RegionState] = field(
        default_factory=dict,
    )
    monthly_history: dict[
        int,
        dict[Month, "CycleResult"],
    ] = field(default_factory=dict)
    daily_history: dict[int, dict[Month, dict[int, "DailyCycleResult"]]] = field(default_factory=dict)
    monthly_summaries: dict[int, dict[Month, "MonthlyEcologySummary"]] = field(default_factory=dict)
    pending_month_review: tuple[int, Month] | None = None
    interventions: list["InterventionRecord"] = field(default_factory=list)
    intervention_resources: InterventionResources = field(default_factory=InterventionResources)
    scenario_name: str = ""
    scenario_description: str = ""
    scenario_id: str = ""

    def __post_init__(self) -> None:
        """Create this world's independent deterministic random stream."""
        self.random_generator = Random(self.random_seed)
