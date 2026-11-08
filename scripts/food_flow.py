"""Read-only daily food-flow projection; no simulation state or random draws."""

from dataclasses import asdict
from math import isclose

from simulation.growth import adult_count


def carrion_sources(record):
    sources = {}
    if record is not None:
        for consumption in record.consumptions:
            source = consumption.updated_carrion.source_animal_id
            sources[source] = sources.get(source, 0.0) + consumption.consumed_biomass_kg
    return sources


def daily_food_flow(day, registry):
    """Project one RegionDailyEcologyResult, retaining stage boundaries.

    First meals and maintenance scavenging are components of maintenance intake;
    reserve deposits are additional physical intake. Recovery spends reserves.
    Released leftovers are a transfer, not another carcass source.
    """
    web = day.food_web
    consumers = {a["id"] for a in registry.definitions_of_type("animal")
                 if a.get("prey_diet") or a.get("scavenging_diet")}
    prey_ids = {e["animal_id"] for a in registry.definitions_of_type("animal")
                for e in a.get("prey_diet", ())}
    habitats = {}
    for habitat_id, feeding in web.habitat_feeding.items():
        records = {}
        for animal in sorted(consumers.intersection(feeding)):
            nutrition = feeding[animal]
            hunt = web.hunting_rounds.get(habitat_id, {}).get(animal)
            prey = {}
            def entry(key):
                return prey.setdefault(key, dict(attempts=0, secured_count=0,
                    carcass_kg=0.0, first_meal_kg=0.0, released_leftovers_kg=0.0))
            if hunt is not None:
                for attempt in hunt.attempts:
                    entry(attempt.prey_selection.selected_animal_id)["attempts"] += 1
                for meal in hunt.meals:
                    row = entry(meal.death.animal_id)
                    mass = meal.death.count * meal.death.body_mass_kg
                    first = meal.consumption.consumed_biomass_kg
                    leftover = meal.leftover_carrion.available_biomass_kg
                    if not isclose(mass, first + leftover, abs_tol=1e-9):
                        raise ValueError("First meal and released carcass do not reconcile.")
                    row["secured_count"] += meal.death.count
                    row["carcass_kg"] += mass
                    row["first_meal_kg"] += first
                    row["released_leftovers_kg"] += leftover
            scavenging = carrion_sources(web.scavenging_results.get(habitat_id, {}).get(animal))
            deposit = web.reserve_deposits.get(habitat_id, {}).get(animal)
            growth = web.growth_meals.get(habitat_id, {}).get(animal)
            if not isclose(sum(nutrition.resource_consumption.values()), nutrition.consumed_amount, abs_tol=1e-9):
                raise ValueError("Maintenance sources do not reconcile.")
            records[animal] = {
                "maintenance_required_kg": nutrition.required_amount,
                "maintenance_consumed_kg": nutrition.consumed_amount,
                "maintenance_coverage": nutrition.nutrition_ratio,
                "maintenance_sources_kg": dict(nutrition.resource_consumption),
                "hunts_by_prey": prey,
                "search": asdict(hunt.search) if hunt is not None and hunt.search is not None else None,
                "maintenance_scavenging_by_prey_kg": scavenging,
                "reserve_resource_deposits_kg": dict(deposit[0].resource_consumption) if deposit else {},
                "reserve_scavenging_by_prey_kg": carrion_sources(deposit[1]) if deposit else {},
                "growth_scavenging_by_prey_kg": carrion_sources(growth.carrion) if growth else {},
                "nutrition_at_start": asdict(day.starting_state.nutritional_states[habitat_id][animal])
                    if animal in day.starting_state.nutritional_states.get(habitat_id, {}) else None,
                "nutrition_at_end": asdict(day.ending_state.nutritional_states[habitat_id][animal])
                    if animal in day.ending_state.nutritional_states.get(habitat_id, {}) else None,
            }
        habitats[habitat_id] = records
    prey_counts = {}
    for animal in sorted(prey_ids.intersection(day.starting_state.animal_populations)):
        start = day.starting_state.animal_populations[animal]
        end = day.ending_state.animal_populations[animal]
        adults = lambda snapshot, count: adult_count(count, tuple(c for local in
            snapshot.growth_cohorts.values() for c in local.get(animal, ())))
        prey_counts[animal] = dict(start=start, end=end,
            adults_at_start=adults(day.starting_state, start),
            adults_at_end=adults(day.ending_state, end),
            births=day.demographics.births.get(animal, 0),
            starvation_deaths=day.demographics.starvation_deaths.get(animal, 0))
    return dict(year=day.year, month=day.month.value, day=day.day, habitats=habitats,
                regional_prey_counts=prey_counts,
                regional_recovery_spent_kg=dict(day.demographics.condition_recovery_kg))
