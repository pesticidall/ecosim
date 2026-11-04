from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from math import isclose, isfinite
from random import Random
from typing import Any

from core.content_registry import ContentRegistry
from simulation.activity import activity_phase_weights, calculate_activity_overlap_modifier
from simulation.hunting import (
    HuntResult, calculate_attack_scores, calculate_chase_scores,
    calculate_detection_scores, resolve_hunt,
)
from simulation.injuries import Injury
from simulation.condition_cohorts import select_participant_injuries, transition_injury_cohorts
from simulation.predator_diet import PreySelection, select_habitat_prey
from simulation.predation import (
    PredationMeal, apply_predation_meal, create_predation_remains, feed_secured_prey,
    summarize_predation_feeding,
)
from simulation.feeding import PopulationFeedingResult
from simulation.world_state import HabitatState, RegionState
from simulation.approach import calculate_stalking_scores
from simulation.growth import plan_growth_loss
from simulation.search import SearchBudget, resolve_search_budget


@dataclass(frozen=True)
class HabitatHuntAttempt:
    """Retain the local prey choice and complete hunting-stage evidence."""

    habitat_id: str
    predator_id: str
    prey_selection: PreySelection
    hunt: HuntResult
    predator_starting_injuries: tuple[Injury, ...] = ()
    prey_starting_injuries: tuple[Injury, ...] = ()


def resolve_habitat_hunt(
    predator_id: str,
    habitat: HabitatState,
    registry: ContentRegistry,
    weather_definition: dict[str, Any],
    attack_method_id: str | None,
    counterattack_method_id: str | None,
    taxon_definitions: Iterable[dict[str, Any]],
    trait_definitions: Iterable[dict[str, Any]],
    temperament_definitions: Iterable[dict[str, Any]],
    contextual_suitability: Mapping[str, float],
    random_source: Random,
    injuries_by_animal: Mapping[str, tuple[Injury, ...]] | None = None,
) -> HabitatHuntAttempt | None:
    """Select local prey and resolve one hunt without committing world changes.

    Injuries supplied here describe the participating animals, not the entire
    species population. Movement uses each animal's primary movement mode.
    """
    predator = registry.get(predator_id)
    selection = select_habitat_prey(predator, habitat, random_source, registry=registry)
    if selection is None:
        return None
    prey = registry.get(selection.selected_animal_id)
    selected_attack_method = attack_method_id or predator.get("attack_method_id")
    if selected_attack_method is None:
        raise ValueError("A hunting attack_method_id is required.")
    selected_counterattack_method = prey.get("counterattack_method_id", counterattack_method_id)
    habitat_definition = registry.get(habitat.definition_id)
    taxa, traits = tuple(taxon_definitions), tuple(trait_definitions)
    overrides = injuries_by_animal or {}
    predator_cohorts = habitat.injury_cohorts.get(predator_id, ())
    predator_population = habitat.animal_populations[predator_id]
    predator_injuries = overrides.get(predator_id)
    if predator_injuries is None:
        predator_injuries = select_participant_injuries(predator_population, predator_cohorts, random_source)
    # Temporarily remove the hunter when selecting same-species prey.
    prey_cohorts = habitat.injury_cohorts.get(prey["id"], ())
    prey_population = habitat.animal_populations[prey["id"]]
    if prey["id"] == predator_id:
        prey_cohorts = transition_injury_cohorts(
            predator_population, predator_cohorts, predator_injuries, (), survived=False,
        )
        prey_population -= 1
    prey_injuries = overrides.get(prey["id"])
    if prey_injuries is None:
        prey_injuries = select_participant_injuries(prey_population, prey_cohorts, random_source)
    overlap = calculate_activity_overlap_modifier(
        activity_phase_weights(predator.get("activity_pattern", "flexible")),
        activity_phase_weights(prey.get("activity_pattern", "flexible")),
    )
    detection = calculate_detection_scores(
        predator, prey, overlap, weather_definition,
        habitat_definition=habitat_definition,
        taxon_definitions=taxa, trait_definitions=traits,
    )
    chase = calculate_chase_scores(
        predator, prey, taxa, traits, habitat_definition, weather_definition,
        predator_movement_mode=predator["primary_movement_mode"],
        prey_movement_mode=prey["primary_movement_mode"],
        predator_injuries=predator_injuries, prey_injuries=prey_injuries,
    )
    attack = calculate_attack_scores(predator, prey, predator_injuries)
    hunt = resolve_hunt(
        detection, chase, attack, predator, prey,
        registry.get(selected_attack_method),
        registry.get(selected_counterattack_method) if selected_counterattack_method else None,
        taxa, traits, temperament_definitions, contextual_suitability, random_source,
        predator_injuries=predator_injuries, prey_injuries=prey_injuries,
        stalking_scores=(calculate_stalking_scores(predator, prey, habitat_definition, weather_definition, taxa, traits)
                         if predator.get("approach_model") == "concealed" else None),
    )
    return HabitatHuntAttempt(
        habitat.definition_id, predator_id, selection, hunt,
        predator_injuries, prey_injuries,
    )


def apply_habitat_hunt(
    region: RegionState,
    attempt: HabitatHuntAttempt,
    registry: ContentRegistry,
    requested_biomass_kg: float,
) -> PredationMeal | None:
    """Commit a resolved attempt and its optional meal to habitat history.

    Survivor condition cohorts persist for later hunts. Reapplying the same
    attempt object is rejected.
    """
    if isinstance(requested_biomass_kg, bool) or not isinstance(requested_biomass_kg, (int, float)):
        raise TypeError("requested_biomass_kg must be numeric.")
    if not isfinite(requested_biomass_kg) or requested_biomass_kg < 0:
        raise ValueError("requested_biomass_kg must be finite and nonnegative.")
    if attempt.habitat_id not in region.habitats:
        raise ValueError("Hunt habitat does not exist in this region.")
    habitat = region.habitats[attempt.habitat_id]
    if any(previous is attempt for previous in habitat.hunt_history):
        raise ValueError("This hunt attempt has already been applied.")
    if habitat.animal_populations.get(attempt.predator_id, 0) <= 0:
        raise ValueError("Hunt requires a living local predator.")
    prey_id = attempt.prey_selection.selected_animal_id
    if habitat.animal_populations.get(prey_id, 0) <= 0:
        raise ValueError("Hunt requires available prey in the habitat.")
    if prey_id == attempt.predator_id and habitat.animal_populations.get(prey_id, 0) < 2:
        raise ValueError("Same-species predation requires another local animal.")
    updated_cohorts = dict(habitat.injury_cohorts)
    for animal_id, previous, resulting, survived in (
        (attempt.predator_id, attempt.predator_starting_injuries,
         attempt.hunt.contact.predator_injuries, True),
        (prey_id, attempt.prey_starting_injuries,
         attempt.hunt.contact.prey_injuries, not attempt.hunt.outcome.prey_secured),
    ):
        updated_cohorts[animal_id] = transition_injury_cohorts(
            habitat.animal_populations[animal_id], updated_cohorts.get(animal_id, ()),
            previous, resulting, survived=survived,
        )
    prey_definition = registry.get(prey_id)
    age_loss = None
    if attempt.hunt.outcome.prey_secured and ("growth" in prey_definition or prey_id in habitat.growth_cohorts or prey_id in habitat.growth_loss_phases):
        age_loss = plan_growth_loss(habitat, prey_id, 1)
        units = age_loss.removed_mass_units
        prey_definition = {**prey_definition, "typical_adult_mass_kg": prey_definition["typical_adult_mass_kg"] * units}
    remains = create_predation_remains(
        attempt.hunt, prey_definition, attempt.predator_id, attempt.habitat_id, age_loss=age_loss,
    )
    meal = None
    if remains is not None:
        meal = feed_secured_prey(remains, requested_biomass_kg)
        apply_predation_meal(region, meal)
    habitat.injury_cohorts = updated_cohorts
    habitat.hunt_history.append(attempt)
    return meal


@dataclass(frozen=True)
class HabitatHuntingRound:
    """Record one bounded set of hunting opportunities and its nutrition."""

    attempts: tuple[HabitatHuntAttempt, ...]
    meals: tuple[PredationMeal, ...]
    feeding: PopulationFeedingResult
    search: SearchBudget | None = None


def run_habitat_hunting_round(
    predator_id: str,
    habitat_id: str,
    region: RegionState,
    registry: ContentRegistry,
    weather_definition: dict[str, Any],
    attack_method_id: str | None,
    counterattack_method_id: str | None,
    taxon_definitions: Iterable[dict[str, Any]],
    trait_definitions: Iterable[dict[str, Any]],
    temperament_definitions: Iterable[dict[str, Any]],
    contextual_suitability: Mapping[str, float],
    random_source: Random,
    prior_feeding: PopulationFeedingResult | None = None,
    *,
    period_fraction: float = 1.0,
) -> HabitatHuntingRound:
    """Spend bounded opportunities per starting predator, stopping when fed.

    This is an explicit feeding round, not a calendar timestep. Demand uses
    the existing per-cycle food requirement. Optional prior feeding belongs to
    this same population and period; older meal history is never recounted.
    """
    habitat = region.habitats[habitat_id]
    predator = registry.get(predator_id)
    population = habitat.animal_populations.get(predator_id, 0)
    empty_feeding = summarize_predation_feeding(
        population, predator, (), period_fraction=period_fraction,
    )
    prior_consumed = 0.0
    prior_sources: dict[str, float] = {}
    if prior_feeding is not None:
        if not isclose(prior_feeding.required_amount, empty_feeding.required_amount):
            raise ValueError("Prior feeding demand must match this population and period.")
        prior_consumed = prior_feeding.consumed_amount
        if not isfinite(prior_consumed) or prior_consumed < 0:
            raise ValueError("Prior feeding intake must be finite and nonnegative.")
        prior_sources = dict(prior_feeding.resource_consumption)
        if any(not isfinite(value) or value < 0 for value in prior_sources.values()):
            raise ValueError("Prior feeding sources must be finite and nonnegative.")
        if not isclose(sum(prior_sources.values()), prior_consumed):
            raise ValueError("Prior feeding sources must sum to consumed intake.")
    remaining = max(empty_feeding.required_amount - prior_consumed, 0.0)
    taxa, traits, temperaments = (
        tuple(taxon_definitions), tuple(trait_definitions), tuple(temperament_definitions),
    )
    attempts: list[HabitatHuntAttempt] = []
    meals: list[PredationMeal] = []
    search = (resolve_search_budget(predator, habitat, registry, random_source)
              if remaining > 0 and "search_budget" in predator else None)
    budget = search.allocated_member_opportunities if search is not None else population * predator.get("hunting_attempts_per_animal", 1)
    for _ in range(budget):
        if remaining <= 0:
            break
        attempt = resolve_habitat_hunt(
            predator_id, habitat, registry, weather_definition,
            attack_method_id, counterattack_method_id, taxa, traits, temperaments,
            contextual_suitability, random_source,
        )
        if attempt is None:
            break
        meal = apply_habitat_hunt(region, attempt, registry, remaining)
        attempts.append(attempt)
        if meal is not None:
            meals.append(meal)
            remaining -= meal.consumption.consumed_biomass_kg
    feeding = summarize_predation_feeding(
        population, predator, meals, period_fraction=period_fraction,
    )
    consumed = prior_consumed + feeding.consumed_amount
    sources = dict(prior_sources)
    for source_id, amount in feeding.resource_consumption.items():
        sources[source_id] = sources.get(source_id, 0.0) + amount
    feeding = PopulationFeedingResult(
        required_amount=feeding.required_amount,
        consumed_amount=consumed,
        nutrition_ratio=min(consumed / feeding.required_amount, 1.0) if feeding.required_amount else 1.0,
        resource_consumption=sources,
    )
    return HabitatHuntingRound(tuple(attempts), tuple(meals), feeding, search)
