from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from enum import Enum
from math import isfinite
from random import Random
from typing import Any

from simulation.injuries import (
    Injury,
    calculate_injury_modifiers,
    resolve_injury_from_trauma,
)
from simulation.movement import resolve_escape_mobility, resolve_mobility
from simulation.temperament import (
    ActionSelection,
    select_animal_action,
)
from simulation.traits import (
    TraitEffectResult,
    resolve_animal_action_capabilities,
    resolve_animal_trait_effect,
    resolve_animal_trait_ids,
)
from simulation.trauma import calculate_relative_mass_factor, create_trauma_event
from simulation.weather import weather_visibility_modifier
from simulation.groups import AnimalGroup, GroupPower, GroupRole, calculate_group_power
from simulation.approach import StalkingScores, StalkingResult, resolve_stalking


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
class GroupDetectionScores(DetectionScores):
    """Expose group search gains and awareness of collective exposure."""

    search_multiplier: float
    exposure: float
    awareness_contribution: float


def calculate_group_detection_scores(
    hunting_group: AnimalGroup,
    defensive_group: AnimalGroup,
    predator_definition: dict[str, Any],
    prey_definition: dict[str, Any],
    activity_overlap_modifier: float,
    weather_definition: dict[str, Any],
    habitat_definition: dict[str, Any] | None = None,
    taxon_definitions: Iterable[dict[str, Any]] | None = None,
    trait_definitions: Iterable[dict[str, Any]] = (),
) -> GroupDetectionScores:
    """Combine ordinary detection context with diminishing group awareness.

    Extra hunters add coordinated search but create exposure opposed by their
    Stealth. Extra prey contribute Perception. Singles retain ordinary scores.
    """
    if hunting_group.role is not GroupRole.HUNTING or defensive_group.role is not GroupRole.DEFENSIVE:
        raise ValueError("Group detection requires hunting and defensive roles.")
    if hunting_group.animal_id != predator_definition["id"] or defensive_group.animal_id != prey_definition["id"]:
        raise ValueError("Group detection definitions must match group species.")
    if (hunting_group.region_id, hunting_group.habitat_id) != (defensive_group.region_id, defensive_group.habitat_id):
        raise ValueError("Detection groups must share a region and habitat.")
    intelligence = predator_definition["statistics"]["intelligence"]
    stealth = predator_definition["statistics"]["stealth"]
    perception = prey_definition["statistics"]["perception"]
    for field, value in (("intelligence", intelligence), ("stealth", stealth), ("perception", perception)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"Group detection {field} must be numeric.")
        if not isfinite(value) or not 0 <= value <= 10:
            raise ValueError(f"Group detection {field} must be finite and between zero and ten.")
    base = calculate_detection_scores(
        predator_definition, prey_definition, activity_overlap_modifier, weather_definition,
        habitat_definition=habitat_definition, taxon_definitions=taxon_definitions,
        trait_definitions=trait_definitions,
    )
    extra_hunters = hunting_group.member_count ** 0.5 - 1
    search_multiplier = 1 + extra_hunters * intelligence / 10
    exposure = extra_hunters / (1 + stealth)
    awareness = perception * base.weather_visibility_modifier * (
        defensive_group.member_count ** 0.5 - 1 + exposure
    )
    if predator_definition.get("approach_model") == "concealed":
        # Prey noticing the hunters is now resolved in its own approach stage.
        awareness = 0.0
    return GroupDetectionScores(
        detector_perception=base.detector_perception,
        target_stealth=base.target_stealth,
        activity_overlap_modifier=base.activity_overlap_modifier,
        weather_visibility_modifier=base.weather_visibility_modifier,
        effective_perception=base.effective_perception * search_multiplier,
        effective_stealth=base.effective_stealth + awareness,
        search_multiplier=search_multiplier,
        exposure=exposure,
        awareness_contribution=awareness,
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
    predator_injuries: Iterable[Injury] = (),
    prey_injuries: Iterable[Injury] = (),
) -> ChaseScores:
    """Combine movement context, escape traits, and injury condition."""
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

    predator_condition = calculate_injury_modifiers(predator_injuries)
    prey_condition = calculate_injury_modifiers(prey_injuries)
    return ChaseScores(
        predator_mobility=(
            predator_movement.resolved_mobility
            * predator_condition.mobility_modifier
        ),
        prey_escape_mobility=(
            prey_movement.resolved_escape_mobility
            * prey_condition.mobility_modifier
        ),
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
    attacker_injuries: Iterable[Injury] = (),
) -> AttackScores:
    """Apply attacker condition while preserving base Power and Defense."""
    attacker_power = float(
        attacker_definition["statistics"]["power"]
    )
    defender_defense = float(
        defender_definition["statistics"]["defense"]
    )
    condition = calculate_injury_modifiers(attacker_injuries)

    return AttackScores(
        attacker_power=attacker_power,
        defender_defense=defender_defense,
        effective_power=attacker_power * condition.power_modifier,
        effective_defense=defender_defense,
    )

@dataclass(frozen=True)
class GroupAttackScores(AttackScores):
    """Expose coordinated attackers and defensive support for contact only."""

    attacker_group_power: GroupPower
    defender_group_power: GroupPower | None


def calculate_group_attack_scores(
    attacking_group: AnimalGroup,
    attacker_definition: dict[str, Any],
    defender_definition: dict[str, Any],
    defending_group: AnimalGroup | None = None,
    member_injuries: tuple[tuple[Injury, ...], ...] | None = None,
) -> GroupAttackScores:
    """Build contact scores without assigning group trauma or population losses."""
    if attacking_group.role is not GroupRole.HUNTING:
        raise ValueError("Attacking group must be a hunting unit.")
    attacker_power = calculate_group_power(attacking_group, attacker_definition, member_injuries)
    defender_power = None
    defense_multiplier = 1.0
    if defending_group is not None:
        if defending_group.role is not GroupRole.DEFENSIVE:
            raise ValueError("Defending group must have a defensive role.")
        if (attacking_group.region_id, attacking_group.habitat_id) != (
            defending_group.region_id, defending_group.habitat_id,
        ):
            raise ValueError("Opposing groups must share a region and habitat.")
        defender_power = calculate_group_power(defending_group, defender_definition)
        defense_multiplier = defender_power.group_multiplier
    defense = defender_definition["statistics"]["defense"]
    if isinstance(defense, bool) or not isinstance(defense, (int, float)):
        raise TypeError("Group defender defense must be a number.")
    if not isfinite(defense) or not 0 <= defense <= 10:
        raise ValueError("Group defender defense must be finite and between zero and ten.")
    return GroupAttackScores(
        attacker_power=attacker_power.base_member_power,
        defender_defense=float(defense),
        effective_power=attacker_power.effective_power,
        effective_defense=defense * defense_multiplier,
        attacker_group_power=attacker_power,
        defender_group_power=defender_power,
    )


@dataclass(frozen=True)
class CounterattackScores(AttackScores):
    """Record attack scores and the trait effect used by retaliation."""
    power_trait_effect: TraitEffectResult
def calculate_counterattack_scores(
    prey_definition: dict[str, Any],
    predator_definition: dict[str, Any],
    taxon_definitions: Iterable[dict[str, Any]],
    trait_definitions: Iterable[dict[str, Any]],
    prey_injuries: Iterable[Injury] = (),
) -> CounterattackScores:
    """Calculate a prey counterattack with predator and prey roles reversed."""
    base_scores = calculate_attack_scores(
        attacker_definition=prey_definition,
        defender_definition=predator_definition,
        attacker_injuries=prey_injuries,
    )
    power_trait_effect = resolve_animal_trait_effect(
        prey_definition,
        taxon_definitions,
        trait_definitions,
        "counterattack_power",
    )
    return CounterattackScores(
        attacker_power=base_scores.attacker_power,
        defender_defense=base_scores.defender_defense,
        effective_power=(
            base_scores.effective_power
            *power_trait_effect.modifier
        ),
        effective_defense=base_scores.effective_defense,
        power_trait_effect=power_trait_effect,
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

@dataclass(frozen=True)
class HuntApproachResult:
    """Retain completed stages leading up to physical contact."""

    detection: DetectionResult
    chase: ChaseResult | None = None
    attack: AttackResult | None = None
    stalking: StalkingResult | None = None


def resolve_hunt_approach(
    detection_scores: DetectionScores,
    chase_scores: ChaseScores,
    attack_scores: AttackScores,
    random_source: Random,
    stalking_scores: StalkingScores | None = None,
) -> HuntApproachResult:
    """Resolve detection, chase, and contact, stopping at failed stages."""
    detection = resolve_detection(detection_scores, random_source)
    if not detection.detected:
        return HuntApproachResult(detection=detection)
    stalking = None
    if stalking_scores is not None and chase_scores.movement_compatible:
        stalking = resolve_stalking(stalking_scores, random_source)
        chase_scores = replace(chase_scores, prey_escape_mobility=chase_scores.prey_escape_mobility * stalking.escape_multiplier)
    chase = resolve_chase(chase_scores, random_source)
    if not chase.caught:
        return HuntApproachResult(detection=detection, chase=chase, stalking=stalking)
    attack = resolve_attack(attack_scores, random_source)
    return HuntApproachResult(detection=detection, chase=chase, attack=attack, stalking=stalking)


def resolve_attack_injury(
    attack_result: AttackResult,
    attack_method_definition: dict[str, Any],
    attacker_mass_kg: float,
    target_mass_kg: float,
    contact_quality: float = 1.0,
    source_stage: str = "attack",
    trait_ids: tuple[str, ...] = (),
    trait_definitions: tuple[dict, ...] = (),
) -> Injury | None:
    """Convert successful attack or counterattack contact into optional injury."""
    if not attack_result.hit:
        return None
    trauma_event = create_trauma_event(
        source_stage=source_stage,
        contact_succeeded=True,
        contact_power=attack_result.scores.effective_power,
        opposing_defense=attack_result.scores.effective_defense,
        attack_method_id=attack_method_definition["id"],
        attacker_mass_kg=attacker_mass_kg,
        target_mass_kg=target_mass_kg,
        contact_quality=contact_quality,
    )
    return resolve_injury_from_trauma(
        trauma_event,
        attack_method_definition=attack_method_definition,
        trait_ids=trait_ids,
        trait_definitions=trait_definitions,
    )


def resolve_counterattack(
    prey_definition: dict[str, Any],
    predator_definition: dict[str, Any],
    taxon_definitions: Iterable[dict[str, Any]],
    trait_definitions: Iterable[dict[str, Any]],
    random_source: Random,
    prey_injuries: Iterable[Injury] = (),
) -> AttackResult:
    """Resolve prey retaliation as an ordinary seeded attack contact.."""
    scores = calculate_counterattack_scores(
        prey_definition=prey_definition,
        predator_definition=predator_definition,
        taxon_definitions=taxon_definitions,
        trait_definitions=trait_definitions,
        prey_injuries=prey_injuries,
    )
    return resolve_attack(
        scores=scores, 
        random_source=random_source
    )

@dataclass(frozen=True)
class DetentionScores:
    """Record restraint and escape inputs used during detention."""
    predator_restraint: float
    prey_escape: float
    predator_injury_modifier: float
    prey_injury_modifier: float
    relative_mass_factor: float
    restraint_trait_effect: TraitEffectResult
    resistance_trait_effect: TraitEffectResult
    effective_restraint: float
    effective_escape: float
    prey_power: float = 0.0
    effective_break_free_power: float = 0.0

def calculate_detention_scores(
    predator_definition: dict[str, Any],
    prey_definition: dict[str, Any],
    predator_injuries: Iterable[Injury],
    prey_injuries: Iterable[Injury],
    taxon_definitions: Iterable[dict[str, Any]] | None = None,
    trait_definitions: Iterable[dict[str, Any]] = (),
) -> DetentionScores:
    """Calculate detention scores from condition, mass, and traits."""
    predator_restraint = float(
        predator_definition["statistics"]["power"]
    )
    prey_escape = float(
        prey_definition["statistics"]["mobility"]
    )
    prey_power = float(prey_definition["statistics"].get("power", 0.0))

    predator_condition = calculate_injury_modifiers(
        predator_injuries,
    )
    prey_condition = calculate_injury_modifiers(
        prey_injuries,
    )
    predator_mass_kg = float(
        predator_definition.get(
            "typical_adult_mass_kg",
            1.0,
        )
    )
    prey_mass_kg = float(
        prey_definition.get(
            "typical_adult_mass_kg",
            1.0,
        )
    )
    relative_mass_factor = calculate_relative_mass_factor(
        attacker_mass_kg=predator_mass_kg,
        target_mass_kg=prey_mass_kg,
    )

    if taxon_definitions is None:
        restraint_trait_effect = TraitEffectResult(
            target="restraint",
            modifier=1.0,
            contributing_trait_ids=(),
        )
        resistance_trait_effect = TraitEffectResult(
            target="restraint_resistance",
            modifier=1.0,
            contributing_trait_ids=(),
        )
    else:
        taxon_definition_list = list(taxon_definitions)
        trait_definition_list = list(trait_definitions)
        restraint_trait_effect = resolve_animal_trait_effect(
            predator_definition,
            taxon_definition_list,
            trait_definition_list,
            "restraint",
        )
        resistance_trait_effect = resolve_animal_trait_effect(
            prey_definition,
            taxon_definition_list,
            trait_definition_list,
            "restraint_resistance",
        )

    effective_restraint = (
        predator_restraint
        * predator_condition.power_modifier
        * relative_mass_factor
        * restraint_trait_effect.modifier
    )
    effective_break_free_power = prey_power * prey_condition.power_modifier
    effective_escape = (
        prey_escape * prey_condition.mobility_modifier
        + effective_break_free_power
    ) * resistance_trait_effect.modifier
    return DetentionScores(
        predator_restraint=predator_restraint,
        prey_escape=prey_escape,
        predator_injury_modifier=(
            predator_condition.power_modifier
        ),
        prey_injury_modifier=(
            prey_condition.mobility_modifier
        ),
        relative_mass_factor=relative_mass_factor,
        restraint_trait_effect=restraint_trait_effect,
        resistance_trait_effect=resistance_trait_effect,
        effective_restraint=effective_restraint,
        effective_escape=effective_escape,
        prey_power=prey_power,
        effective_break_free_power=effective_break_free_power,
    )

@dataclass(frozen=True)
class DetentionResult:
    """Record the scores, probability, and outcome of detention."""

    scores: DetentionScores
    detention_probability: float
    detention_roll: float | None
    detained: bool


def resolve_detention(
    scores: DetentionScores,
    random_source: Random,
) -> DetentionResult:
    """Resolve restraint against escape using one seeded roll."""

    if scores.effective_restraint <= 0.0:
        return DetentionResult(
            scores=scores,
            detention_probability=0.0,
            detention_roll=None,
            detained=False,
        )

    total_score = (
        scores.effective_restraint
        + scores.effective_escape
    )
    detention_probability = (
        scores.effective_restraint / total_score
        if total_score > 0.0
        else 0.0
    )
    detention_roll = random_source.random()

    return DetentionResult(
        scores=scores,
        detention_probability=detention_probability,
        detention_roll=detention_roll,
        detained=(
            detention_roll < detention_probability
        ),
    )

class HuntOutcomeStatus(Enum):
    """Name the stage at which a hunt ended."""

    NOT_DETECTED = "not_detected"
    ESCAPED_CHASE = "escaped_chase"
    ATTACK_MISSED = "attack_missed"
    ESCAPED_DETENTION = "escaped_detention"
    SECURED = "secured"

@dataclass(frozen=True)
class HuntOutcome:
    """Record completed hunting stages and the resulting status."""
    detected: bool
    caught: bool
    hit: bool
    detained: bool
    status: HuntOutcomeStatus
    prey_secured: bool


def classify_hunt_outcome(
    detected: bool,
    caught: bool,
    hit: bool,
    detained: bool,
) -> HuntOutcomeStatus:
    """Classify a hunt by the first stage that did not succeed."""

    if not detected:
        return HuntOutcomeStatus.NOT_DETECTED
    if not caught:
        return HuntOutcomeStatus.ESCAPED_CHASE
    if not hit:
        return HuntOutcomeStatus.ATTACK_MISSED
    if not detained:
        return HuntOutcomeStatus.ESCAPED_DETENTION
    return HuntOutcomeStatus.SECURED

def build_hunt_outcome(
    detected: bool,
    caught: bool,
    hit: bool,
    detained: bool,
) -> HuntOutcome:
    """Build a structured hunt outcome from completed hunting stages."""
    status = classify_hunt_outcome(
        detected=detected,
        caught=caught,
        hit=hit,
        detained=detained,
    )
    return HuntOutcome(
        detected=detected,
        caught=caught,
        hit=hit,
        detained=detained,
        status=status,
        prey_secured=(
            status is HuntOutcomeStatus.SECURED
        ),
    )

def select_post_contact_response(
    prey_definition: dict[str, Any],
    taxon_definitions: Iterable[dict[str, Any]],
    trait_definitions: Iterable[dict[str, Any]],
    temperament_definitions: Iterable[dict[str, Any]],
    contextual_suitability: Mapping[str, float],
    random_source: Random,
) -> ActionSelection:
    """Select an eligible prey response after predator contact."""
    eligible_action_ids: list[str] = []
    if prey_definition.get("available_movement_modes"):
        eligible_action_ids.append("escape")
    action_capabilities = resolve_animal_action_capabilities(
        prey_definition,
        taxon_definitions,
        trait_definitions,
    )
    if "counterattack" in action_capabilities:
        eligible_action_ids.append("counterattack")
    return select_animal_action(
        animal_definition=prey_definition,
        temperament_definitions=temperament_definitions,
        contextual_suitability=contextual_suitability,
        eligible_action_ids=eligible_action_ids,
        random_source=random_source,
    )


@dataclass(frozen=True)
class HuntContactResult:
    """Retain post-contact decisions, injuries, and restraint results."""

    predator_injuries: tuple[Injury, ...]
    prey_injuries: tuple[Injury, ...]
    response: ActionSelection | None = None
    counterattack: AttackResult | None = None
    detention: DetentionResult | None = None


def resolve_hunt_contact(
    attack_result: AttackResult,
    predator_definition: dict[str, Any],
    prey_definition: dict[str, Any],
    attack_method_definition: dict[str, Any],
    counterattack_method_definition: dict[str, Any] | None,
    taxon_definitions: Iterable[dict[str, Any]],
    trait_definitions: Iterable[dict[str, Any]],
    temperament_definitions: Iterable[dict[str, Any]],
    contextual_suitability: Mapping[str, float],
    random_source: Random,
    predator_injuries: Iterable[Injury] = (),
    prey_injuries: Iterable[Injury] = (),
    contact_quality: float = 1.0,
    counterattack_contact_quality: float = 1.0,
) -> HuntContactResult:
    """Resolve contact consequences before the hunting context decides death."""
    predator_condition = tuple(predator_injuries)
    prey_condition = tuple(prey_injuries)
    if not attack_result.hit:
        return HuntContactResult(predator_condition, prey_condition)

    taxa = tuple(taxon_definitions)
    traits = tuple(trait_definitions)
    predator_mass = predator_definition["typical_adult_mass_kg"]
    prey_mass = prey_definition["typical_adult_mass_kg"]
    injury = resolve_attack_injury(
        attack_result, attack_method_definition, predator_mass, prey_mass,
        contact_quality=contact_quality,
        trait_ids=tuple(resolve_animal_trait_ids(predator_definition, taxa)),
        trait_definitions=traits,
    )
    if injury is not None:
        prey_condition += (injury,)
    response = select_post_contact_response(
        prey_definition, taxa, traits, temperament_definitions,
        contextual_suitability, random_source,
    )
    counterattack = None
    if response.selected_action_id == "counterattack":
        if counterattack_method_definition is None:
            raise ValueError("A counterattack method is required for retaliation.")
        counterattack = resolve_counterattack(
            prey_definition, predator_definition, taxa, traits, random_source,
            prey_injuries=prey_condition,
        )
        injury = resolve_attack_injury(
            counterattack, counterattack_method_definition, prey_mass, predator_mass,
            source_stage="counterattack",
            contact_quality=counterattack_contact_quality,
            trait_ids=tuple(resolve_animal_trait_ids(prey_definition, taxa)),
            trait_definitions=traits,
        )
        if injury is not None:
            predator_condition += (injury,)
    scores = calculate_detention_scores(
        predator_definition, prey_definition, predator_condition, prey_condition,
        taxon_definitions=taxa, trait_definitions=traits,
    )
    detention = resolve_detention(scores, random_source)
    return HuntContactResult(
        predator_condition, prey_condition, response, counterattack, detention,
    )


@dataclass(frozen=True)
class HuntResult:
    """Retain stage evidence, condition changes, and one final hunt outcome."""

    approach: HuntApproachResult
    contact: HuntContactResult
    outcome: HuntOutcome


def resolve_hunt(
    detection_scores: DetectionScores,
    chase_scores: ChaseScores,
    attack_scores: AttackScores,
    predator_definition: dict[str, Any],
    prey_definition: dict[str, Any],
    attack_method_definition: dict[str, Any],
    counterattack_method_definition: dict[str, Any] | None,
    taxon_definitions: Iterable[dict[str, Any]],
    trait_definitions: Iterable[dict[str, Any]],
    temperament_definitions: Iterable[dict[str, Any]],
    contextual_suitability: Mapping[str, float],
    random_source: Random,
    predator_injuries: Iterable[Injury] = (),
    prey_injuries: Iterable[Injury] = (),
    contact_quality: float = 1.0,
    counterattack_contact_quality: float = 1.0,
    stalking_scores: StalkingScores | None = None,
) -> HuntResult:
    """Compose supplied approach scores and post-contact resolution for one hunt.

    Callers calculate approach scores from current ecological conditions.
    Population changes, predation death, and carrion belong to the caller.
    """
    approach = resolve_hunt_approach(
        detection_scores, chase_scores, attack_scores, random_source, stalking_scores,
    )
    contact = HuntContactResult(tuple(predator_injuries), tuple(prey_injuries))
    if approach.attack is not None and approach.attack.hit:
        contact = resolve_hunt_contact(
            approach.attack, predator_definition, prey_definition,
            attack_method_definition, counterattack_method_definition,
            taxon_definitions, trait_definitions, temperament_definitions,
            contextual_suitability, random_source,
            predator_injuries=contact.predator_injuries,
            prey_injuries=contact.prey_injuries,
            contact_quality=contact_quality,
            counterattack_contact_quality=counterattack_contact_quality,
        )
    outcome = build_hunt_outcome(
        detected=approach.detection.detected,
        caught=approach.chase is not None and approach.chase.caught,
        hit=approach.attack is not None and approach.attack.hit,
        detained=contact.detention is not None and contact.detention.detained,
    )
    return HuntResult(approach=approach, contact=contact, outcome=outcome)
