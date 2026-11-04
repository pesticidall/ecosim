"""Physical juvenile growth meals, after maintenance and before reserve top-ups."""

from dataclasses import dataclass

from simulation.feeding import PopulationFeedingResult, _feed_populations
from simulation.growth import adult_count
from simulation.scavenging import ScavengingResult, allocate_habitat_scavenging


@dataclass(frozen=True)
class GrowthMeal:
    feeding: PopulationFeedingResult
    carrion: ScavengingResult
    juvenile_count: int


def feed_growth(region, registry, local_feeding, regional_feeding):
    """Charge only fed, living juveniles for a daily growth allowance.

    Existing diets govern every source. No extra hunts or implicit scavenging
    permissions are created. Flat legacy regions support resource feeding only.
    Stored reserves remain a maintenance buffer, not an extra growth source.
    """
    collections = ([(key, habitat, local_feeding[key]) for key, habitat in sorted(region.habitats.items())]
                   if region.habitats else [(None, region, regional_feeding)])
    records = {}
    for habitat_id, state, maintenance in collections:
        requests, definitions, counts = {}, {}, {}
        for animal, population in state.animal_populations.items():
            definition = registry.get(animal)
            config = definition.get("growth", {})
            if config.get("feeding_model", "shared") != "separate":
                continue
            cohorts = state.growth_cohorts.get(animal, ())
            adult_count(population, cohorts)
            juveniles = sum(c.count for c in cohorts)
            daily_growth_mass = definition["typical_adult_mass_kg"] * (1 - config["newborn_mass_fraction"]) / config["days_to_adult"]
            requests[animal] = (juveniles * daily_growth_mass / config.get("biomass_gain_per_food_kg", 0.25)
                                if maintenance[animal].nutrition_ratio >= 1 - 1e-12 else 0.0)
            definitions[animal], counts[animal] = definition, juveniles
        if not requests:
            continue
        food = _feed_populations({animal: state.animal_populations[animal] for animal in requests},
                                 state.resource_quantities, registry, required_amounts_override=requests)
        if habitat_id is not None:
            for meal in food.values():
                for resource, amount in meal.resource_consumption.items():
                    region.resource_quantities[resource] = max(0.0, region.resource_quantities.get(resource, 0) - amount)
        remaining = {animal: max(0.0, requests[animal] - food[animal].consumed_amount) for animal in requests}
        carrion = (allocate_habitat_scavenging(definitions, state, remaining) if habitat_id is not None else
                   {animal: ScavengingResult(animal, remaining[animal], 0.0, ()) for animal in requests})
        records[habitat_id] = {}
        for animal, request in requests.items():
            scavenging = carrion[animal]
            sources = dict(food[animal].resource_consumption)
            for consumption in scavenging.consumptions:
                source = consumption.updated_carrion.source_animal_id
                sources[source] = sources.get(source, 0.0) + consumption.consumed_biomass_kg
            consumed = food[animal].consumed_amount + scavenging.consumed_biomass_kg
            records[habitat_id][animal] = GrowthMeal(PopulationFeedingResult(
                request, consumed, min(1.0, consumed / request) if request else 1.0, sources), scavenging, counts[animal])
    return records
