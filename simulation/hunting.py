from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite
from random import Random
from typing import Any

from simulation.movement import resolve_escape_mobility, resolve_mobility
from simulation.traits import resolve_animal_trait_effect
from simulation.weather import weather_visibility_modifier


@dataclass(frozen=True)
class DetectionScores:
    """Record the visible inputs used by a hunting detection attempt."""
    detector_perception: float
    target_stealth: float
    activity_overlap_modifier: float
    weather_visibility_modifier: float
    effective_perception: float
    effective_stealth: float

def calculate_detection_scores(
    detector_definition: dict[str, Any],
    target_definition: dict[str, Any],
    activity_overlap_modifier: float,
    weather_definition: dict[str, Any],
    habitat_definition: dict[str, Any] | None = None,
    taxon_definitions: Iterable[dict[str, Any]] | None = None,
    trait_definitions: Iterable[dict[str, Any]] = (),
) -> DetectionScores:
    """Apply activity, weather, and habitat context to detection scores."""
    if (
        isinstance(activity_overlap_modifier, bool)
        or not isinstance(activity_overlap_modifier, (int, float))
    ):
        raise TypeError(
            "activity_overlap_modifier must be a number."
        )
    if not isfinite(activity_overlap_modifier):
        raise ValueError(
            "activity_overlap_modifier must be finite."
        )
    if not 0.0 <= activity_overlap_modifier <= 1.0:
        raise ValueError(
            "activity_overlap_modifier must be between 0.0 and 1.0."
        )

    detector_perception = float(
        detector_definition["statistics"]["perception"]
    )
    target_stealth = float(
        target_definition["statistics"]["stealth"]
    )
    visibility_modifier = weather_visibility_modifier(
        weather_definition
    )

    habitat_visibility_modifier = 1.0
    habitat_concealment_modifier = 1.0
    if habitat_definition is not None:
        conditions = habitat_definition["conditions"]
        habitat_visibility_modifier = float(conditions["openness"])
        habitat_concealment_modifier = (
            1.0 + float(conditions["vegetation_density"])
        )
    detection_trait_modifier = 1.0
    stealth_trait_modifier = 1.0
    if taxon_definitions is not None:
        taxon_definition_list = list(taxon_definitions)
        trait_definition_list = list(trait_definitions)
        detection_trait_effect = resolve_animal_trait_effect(
            detector_definition,
            taxon_definition_list,
            trait_definition_list,
            "detection",
        )
        stealth_trait_effect = resolve_animal_trait_effect(
            target_definition,
            taxon_definition_list,
            trait_definition_list,
            "stealth",
        )
        detection_trait_modifier = detection_trait_effect.modifier
        stealth_trait_modifier = stealth_trait_effect.modifier

    return DetectionScores(
        detector_perception=detector_perception,
        target_stealth=target_stealth,
        activity_overlap_modifier=activity_overlap_modifier,
        weather_visibility_modifier=visibility_modifier,
        effective_perception=(
            detector_perception 
            * activity_overlap_modifier 
            * visibility_modifier 
            * habitat_visibility_modifier
            * detection_trait_modifier
        ),
        effective_stealth=(
            target_stealth 
            * habitat_concealment_modifier
            * stealth_trait_modifier
        )
    )

@dataclass(frozen=True)
class DetectionResult:
    """Record the scores, probability, and outcome of detection."""
    scores: DetectionScores
    detection_probability: float
    detection_roll: float
    detected: bool

def resolve_detection(
    scores: DetectionScores,
    random_source: Random,
) -> DetectionResult:
    """Resolve one detection attempt using the supplied random generator."""
    total_score = scores.effective_perception + scores.effective_stealth
    detection_probability = (
        scores.effective_perception / total_score
        if total_score > 0.0
        else 0.0
    )
    detection_roll = random_source.random()

    return DetectionResult(
        scores=scores,
        detection_probability=detection_probability,
        detection_roll=detection_roll,
        detected=detection_roll < detection_probability,
    )

@dataclass(frozen=True)
class ChaseScores:
    """Record the effective mobility scores used for a chase."""
    predator_mobility: float
    prey_escape_mobility: float
    movement_compatible: bool

def calculate_chase_scores(
    predator_definition: dict[str, Any],
    prey_definition: dict[str, Any],
    taxon_definitions: list[dict[str, Any]],
    trait_definitions: list[dict[str, Any]],
    habitat_definition: dict[str, Any],
    weather_definition: dict[str, Any],
    predator_movement_mode: str,
    prey_movement_mode: str,
    predator_flight_capability: str | None = None,
    prey_flight_capability: str | None = None,
) -> ChaseScores:
    """Calculate pursuit and escape mobility using existing resolvers."""
    predator_movement = resolve_mobility(
        animal_definition=predator_definition,
        habitat_definition=habitat_definition,
        weather_definition=weather_definition,
        movement_mode=predator_movement_mode,
        flight_capability=predator_flight_capability,
    )
    prey_movement = resolve_escape_mobility(
        animal_definition=prey_definition,
        taxon_definitions=taxon_definitions,
        trait_definitions=trait_definitions,
        habitat_definition=habitat_definition,
        weather_definition=weather_definition,
        movement_mode=prey_movement_mode,
        flight_capability=prey_flight_capability,
    )

    return ChaseScores(
        predator_mobility=predator_movement.resolved_mobility,
        prey_escape_mobility=prey_movement.resolved_escape_mobility,
        movement_compatible=(
            predator_movement_mode == prey_movement_mode
        )
    )

@dataclass(frozen=True)
class ChaseResult:
    """Record the scores and outcome of a chase attempt."""
    scores: ChaseScores
    catch_probability: float
    chase_roll: float | None
    caught: bool

def resolve_chase(
    scores: ChaseScores,
    random_source: Random,
) -> ChaseResult:
    """Reject incompatible chases without consuming randomness."""
    if not scores.movement_compatible:
        return ChaseResult(
            scores=scores,
            catch_probability=0.0,
            chase_roll=None,
            caught=False,
        )

    total_mobility = scores.predator_mobility + scores.prey_escape_mobility
    catch_probability = (
        scores.predator_mobility / total_mobility
        if total_mobility > 0.0
        else 0.0
    )
    chase_roll = random_source.random()

    return ChaseResult(
        scores=scores,
        catch_probability=catch_probability,
        chase_roll=chase_roll,
        caught=chase_roll < catch_probability,
    )

@dataclass(frozen=True)
class AttackScores:
    """Record base and effective scores for an attack attempt."""
    attacker_power: float
    defender_defense: float
    effective_power: float
    effective_defense: float

def calculate_attack_scores(
    attacker_definition: dict[str, Any],
    defender_definition: dict[str, Any],
) -> AttackScores:
    """Read attacking Power and defending Defense from animal definitions."""
    attacker_power = float(
        attacker_definition["statistics"]["power"]
    )
    defender_defense = float(
        defender_definition["statistics"]["defense"]
    )

    return AttackScores(
        attacker_power=attacker_power,
        defender_defense=defender_defense,
        effective_power=attacker_power,
        effective_defense=defender_defense,
    )

@dataclass(frozen=True)
class AttackResult:
    """Record the scores and outcome of an attack attempt."""
    scores: AttackScores
    hit_probability: float
    attack_roll: float
    hit: bool

def resolve_attack(
    scores: AttackScores,
    random_source: Random,
) -> AttackResult:
    """Resolve whether an attack lands using one seeded roll."""
    total_score = scores.effective_power + scores.effective_defense
    hit_probability = (
        scores.effective_power / total_score
        if total_score > 0.0
        else 0.0
    )
    attack_roll = random_source.random()

    return AttackResult(
        scores=scores,
        hit_probability=hit_probability,
        attack_roll=attack_roll,
        hit=attack_roll < hit_probability,
    )