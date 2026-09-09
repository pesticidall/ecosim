from simulation.feeding import PopulationFeedingResult
from simulation.world_state import RegionState


def calculate_starvation_deaths(
    population: int,
    nutrition_ratio: float,
) -> int:
    if population < 0:
        raise ValueError(
            f"population must not be negative; "
            f"recieved {population}."
        )
    if not 0.0 <= nutrition_ratio <= 1.0:
        raise ValueError(
            f"nutrition_ratio must be between 0.0 and 1.0; "
            f"recieved {nutrition_ratio}."
        )
    unfed_proportion = 1.0 - nutrition_ratio

    return int(population * unfed_proportion)

def apply_starvation_mortality(
    region_state: RegionState,
    feeding_results: dict[
        str,
        PopulationFeedingResult,
    ],
) -> dict[str, int]:
    starvation_deaths: dict[str, int] = {}
    for animal_id, feeding_result in feeding_results.items():
        population = region_state.animal_populations[animal_id]
        deaths = calculate_starvation_deaths(
            population,
            feeding_result.nutrition_ratio,
        )
        region_state.animal_populations[animal_id] = (
            population - deaths
        )
        starvation_deaths[animal_id] = deaths
    return starvation_deaths