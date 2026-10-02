from dataclasses import dataclass, field
from random import Random
from typing import TYPE_CHECKING

from simulation.calendar import CalendarState, Month

if TYPE_CHECKING:
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
    scenario_name: str = ""
    scenario_description: str = ""
    scenario_id: str = ""

    def __post_init__(self) -> None:
        """Create this world's independent deterministic random stream."""
        self.random_generator = Random(self.random_seed)
