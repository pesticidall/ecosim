from simulation.feeding import PopulationFeedingResult
from simulation.world_state import RegionState


def calculate_starvation_deaths(
    population: int,
    nutrition_ratio: float,
) -> int:
    """Calculate whole-animal deaths from the population's food deficit."""
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
    habitat_feeding_results: dict[
        str,
        dict[str, PopulationFeedingResult],
    ] | None = None,
) -> dict[str, int]:
    """Apply starvation losses and return deaths for each population."""
    if habitat_feeding_results:
        starvation_deaths = {
            animal_id: 0
            for animal_id in region_state.animal_populations
        }
        for habitat_id, local_results in (
            habitat_feeding_results.items()
        ):
            habitat_state = region_state.habitats[habitat_id]
            for animal_id, feeding_result in local_results.items():
                population = habitat_state.animal_populations[
                    animal_id
                ]
                deaths = calculate_starvation_deaths(
                    population,
                    feeding_result.nutrition_ratio,
                )
                habitat_state.animal_populations[animal_id] = (
                    population - deaths
                )
                starvation_deaths[animal_id] = (
                    starvation_deaths.get(animal_id, 0)
                    + deaths
                )
        for animal_id in region_state.animal_populations:
            region_state.animal_populations[animal_id] = sum(
                habitat_state.animal_populations.get(animal_id, 0)
                for habitat_state in region_state.habitats.values()
            )
        return starvation_deaths

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
