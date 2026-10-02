from core.content_registry import ContentRegistry
from simulation.feeding import PopulationFeedingResult
from simulation.world_state import RegionState


def calculate_population_births(
    population: int,
    birth_rate: float,
    nutrition_ratio: float,
) -> int:
    """Calculate whole-animal births adjusted by current nutrition."""
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
    habitat_feeding_results: dict[
        str,
        dict[str, PopulationFeedingResult],
    ] | None = None,
) -> dict[str, int]:
    """Add nutrition-adjusted births to every fed animal population."""
    if habitat_feeding_results:
        births_by_animal = {
            animal_id: 0
            for animal_id in region_state.animal_populations
        }
        for habitat_id, local_results in (
            habitat_feeding_results.items()
        ):
            habitat_state = region_state.habitats[habitat_id]
            for animal_id, feeding_result in local_results.items():
                animal_definition = registry.get(animal_id)
                population = habitat_state.animal_populations[
                    animal_id
                ]
                birth_rate = animal_definition[
                    "birth_rate_per_animal_per_cycle"
                ]
                births = calculate_population_births(
                    population,
                    birth_rate,
                    feeding_result.nutrition_ratio,
                )
                habitat_state.animal_populations[animal_id] = (
                    population + births
                )
                births_by_animal[animal_id] = (
                    births_by_animal.get(animal_id, 0)
                    + births
                )
        for animal_id in region_state.animal_populations:
            region_state.animal_populations[animal_id] = sum(
                habitat_state.animal_populations.get(animal_id, 0)
                for habitat_state in region_state.habitats.values()
            )
        return births_by_animal

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
