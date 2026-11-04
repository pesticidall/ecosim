from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from math import ceil, isclose, isfinite
from random import Random
from typing import Any

from core.content_registry import ContentRegistry
from simulation.activity import activity_phase_weights, calculate_activity_overlap_modifier
from simulation.condition_cohorts import transition_injury_cohorts
from simulation.feeding import PopulationFeedingResult, calculate_population_food_requirement
from simulation.group_hunting import GroupHuntResult, apply_group_hunt, resolve_group_hunt
from simulation.groups import (
    AnimalGroup, GroupRole, calculate_defensive_group_size, select_group_participants,
)
from simulation.predation import PredationMeal, summarize_predation_feeding
from simulation.predator_diet import PreySelection, select_habitat_prey
from simulation.world_state import RegionState
from simulation.search import SearchBudget, resolve_search_budget


@dataclass(frozen=True)
class HabitatGroupHuntAttempt:
    """Retain local prey selection and each participating group's evidence."""

    habitat_id: str
    predator_id: str
    prey_selection: PreySelection
    hunt: GroupHuntResult


@dataclass(frozen=True)
class HabitatGroupHuntingRound:
    attempts: tuple[HabitatGroupHuntAttempt, ...]
    meals: tuple[PredationMeal, ...]
    feeding: PopulationFeedingResult
    search: SearchBudget | None = None


def run_habitat_group_hunting_round(
    predator_id: str,
    habitat_id: str,
    region: RegionState,
    registry: ContentRegistry,
    weather_definition: dict[str, Any],
    taxon_definitions: Iterable[dict[str, Any]],
    trait_definitions: Iterable[dict[str, Any]],
    temperament_definitions: Iterable[dict[str, Any]],
    contextual_suitability: Mapping[str, float],
    random_source: Random,
    prior_feeding: PopulationFeedingResult | None = None,
    *,
    local_feeding: Mapping[str, PopulationFeedingResult] | None = None,
    period_fraction: float = 1.0,
) -> HabitatGroupHuntingRound:
    """Spend a bounded local hunting budget on temporary coordinated units.

    Group ceilings describe capability. Current population and food deficit
    limit the actual unit size; every participant spends one opportunity per
    attempt from the population's configured daily budget (one by default).
    The period fraction applies equally to unit size, meal limits, and nutrition.
    """
    habitat = region.habitats[habitat_id]
    predator = registry.get(predator_id)
    population = habitat.animal_populations.get(predator_id, 0)
    empty = summarize_predation_feeding(population, predator, (), period_fraction=period_fraction)
    member_demand = calculate_population_food_requirement(1, predator, period_fraction=period_fraction)
    prior_consumed = 0.0
    sources: dict[str, float] = {}
    if prior_feeding is not None:
        if not isclose(prior_feeding.required_amount, empty.required_amount):
            raise ValueError("Prior feeding demand must match this population and period.")
        prior_consumed = prior_feeding.consumed_amount
        sources = dict(prior_feeding.resource_consumption)
        if not isfinite(prior_consumed) or prior_consumed < 0:
            raise ValueError("Prior feeding intake must be finite and nonnegative.")
        if any(not isfinite(amount) or amount < 0 for amount in sources.values()):
            raise ValueError("Prior feeding sources must be finite and nonnegative.")
        if not isclose(sum(sources.values()), prior_consumed):
            raise ValueError("Prior feeding sources must sum to consumed intake.")
    remaining = max(empty.required_amount - prior_consumed, 0.0)
    budget = population * predator.get("hunting_attempts_per_animal", 1)
    search = (resolve_search_budget(predator, habitat, registry, random_source)
              if remaining > 0 and "search_budget" in predator else None)
    if search is not None:
        budget = search.allocated_member_opportunities
    attempts: list[HabitatGroupHuntAttempt] = []
    meals: list[PredationMeal] = []
    taxa, traits, temperaments = (
        tuple(taxon_definitions), tuple(trait_definitions), tuple(temperament_definitions),
    )
    while budget > 0 and remaining > 0:
        selection = select_habitat_prey(predator, habitat, random_source, registry=registry)
        if selection is None:
            break
        prey_id = selection.selected_animal_id
        prey = registry.get(prey_id)
        available_hunters = habitat.animal_populations[predator_id]
        if prey_id == predator_id:
            available_hunters -= 1
        hunter_count = min(
            predator.get("max_hunting_group_size", 1), budget, available_hunters,
            max(1, ceil(remaining / member_demand)),
        )
        hunters = select_group_participants(region, AnimalGroup(
            predator_id, region.definition_id, habitat_id, hunter_count, GroupRole.HUNTING,
        ), random_source)
        # Exclude all selected hunters before sampling same-species defenders.
        prey_region = region
        if prey_id == predator_id:
            prey_population = habitat.animal_populations[prey_id]
            cohorts = habitat.injury_cohorts.get(prey_id, ())
            for injuries in hunters.member_injuries:
                cohorts = transition_injury_cohorts(
                    prey_population, cohorts, injuries, (), survived=False,
                )
                prey_population -= 1
            prey_habitat = replace(
                habitat, animal_populations={**habitat.animal_populations, prey_id: prey_population},
                injury_cohorts={**habitat.injury_cohorts, prey_id: cohorts},
            )
            prey_region = replace(region, habitats={**region.habitats, habitat_id: prey_habitat})
        prey_nutrition = local_feeding[prey_id].nutrition_ratio if local_feeding is not None else 1.0
        prey_count = calculate_defensive_group_size(
            prey_region.habitats[habitat_id].animal_populations[prey_id],
            prey.get("max_defensive_group_size", 1), prey_nutrition,
        )
        defenders = select_group_participants(prey_region, AnimalGroup(
            prey_id, region.definition_id, habitat_id, prey_count, GroupRole.DEFENSIVE,
        ), random_source)
        overlap = calculate_activity_overlap_modifier(
            activity_phase_weights(predator.get("activity_pattern", "flexible")),
            activity_phase_weights(prey.get("activity_pattern", "flexible")),
        )
        counter_method = prey.get("counterattack_method_id")
        hunt = resolve_group_hunt(
            hunters, defenders, predator, prey, registry.get(habitat_id), weather_definition,
            registry.get(predator["attack_method_id"]),
            registry.get(counter_method) if counter_method else None,
            taxa, traits, temperaments, contextual_suitability, random_source,
            activity_overlap_modifier=overlap,
        )
        shared = apply_group_hunt(
            region, hunt, predator, prey, requested_biomass_kg=remaining,
            period_fraction=period_fraction,
        )
        attempt = HabitatGroupHuntAttempt(habitat_id, predator_id, selection, hunt)
        attempts.append(attempt)
        habitat.hunt_history.append(attempt)
        budget -= hunter_count
        if shared is not None:
            meals.append(shared.meal)
            remaining -= shared.meal.consumption.consumed_biomass_kg
    feeding = summarize_predation_feeding(population, predator, meals, period_fraction=period_fraction)
    consumed = prior_consumed + feeding.consumed_amount
    for source, amount in feeding.resource_consumption.items():
        sources[source] = sources.get(source, 0.0) + amount
    return HabitatGroupHuntingRound(tuple(attempts), tuple(meals), PopulationFeedingResult(
        empty.required_amount, consumed,
        min(consumed / empty.required_amount, 1.0) if empty.required_amount else 1.0,
        sources,
    ), search)
