from dataclasses import dataclass, field


@dataclass
class RegionState:
    definition_id: str
    active_weather_id: str | None = None
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
    random_seed: int
    current_cycle: int = 0
    regions: dict[str, RegionState] = field(
        default_factory=dict,
    )
    scenario_name: str = ""
    scenario_description: str = ""
    scenario_id: str = ""
