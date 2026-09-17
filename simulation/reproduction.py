from core.content_registry import ContentRegistry
from simulation.feeding import PopulationFeedingResult
from simulation.world_state import RegionState


def calculate_population_births(
    population: int,
    birth_rate: float,
    nutrition_ratio: float,
) -> int:
    if population < 0:
        raise ValueError(
            f"population must not be negative; "
            f"received {population}."
        )
    if birth_rate < 0:
        raise ValueError(
            f"birth_rate must not be negative; "
            f"received {birth_rate}."
        )
    if not 0.0 <= nutrition_ratio <= 1.0:
        raise ValueError(
            "nutrition_ratio must be between 0.0 and 1.0; "
            f"received {nutrition_ratio}."
        )
    expected_births = (
        population
        * birth_rate
        * nutrition_ratio
    )
    return int(expected_births)

def apply_reproduction(
    region_state: RegionState,
    registry: ContentRegistry,
    feeding_results: dict[
        str,
        PopulationFeedingResult,
    ],
) -> dict[str, int]:
    births_by_animal: dict[str, int] = {}
    for animal_id, feeding_result in feeding_results.items():
        animal_definition = registry.get(animal_id)
        population = region_state.animal_populations[animal_id]
        birth_rate = animal_definition[
            "birth_rate_per_animal_per_cycle"
        ]
        births = calculate_population_births(
            population,
            birth_rate,
            feeding_result.nutrition_ratio,
        )
        region_state.animal_populations[animal_id] = (
            population + births
        )
        births_by_animal[animal_id] = births

    return births_by_animal