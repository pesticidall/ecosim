"""Predator concealment versus prey awareness after prey has been found."""

from dataclasses import dataclass
from math import isfinite, sqrt
from simulation.traits import resolve_animal_trait_effect
from simulation.weather import weather_visibility_modifier


def _number(value, field, maximum):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field} must be numeric.")
    if not isfinite(value) or not 0 <= value <= maximum:
        raise ValueError(f"{field} must be finite and between zero and {maximum}.")
    return float(value)


@dataclass(frozen=True)
class StalkingScores:
    cover: float
    concealment: float
    awareness: float

    def __post_init__(self):
        _number(self.cover, "Cover", 1)
        for value in (self.concealment, self.awareness):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
                raise ValueError("Approach scores must be finite and nonnegative.")


@dataclass(frozen=True)
class StalkingResult:
    scores: StalkingScores
    unnoticed_probability: float
    roll: float | None
    unnoticed: bool
    escape_multiplier: float


def calculate_stalking_scores(predator, prey, habitat, weather, taxa=(), traits=(),
                              hunter_count=1, defender_count=1):
    for count in (hunter_count, defender_count):
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise ValueError("Approach group counts must be positive integers.")
    conditions = habitat.get("conditions", {})
    vegetation = _number(conditions.get("vegetation_density", 0), "Vegetation density", 1)
    shelter = _number(conditions.get("shelter_availability", 0), "Shelter availability", 1)
    stealth = _number(predator["statistics"]["stealth"], "Predator stealth", 10)
    perception = _number(prey["statistics"]["perception"], "Prey perception", 10)
    modifier = resolve_animal_trait_effect(predator, list(taxa), list(traits), "stealth").modifier if taxa else 1.0
    cover = (vegetation + shelter) / 2
    return StalkingScores(cover, stealth * modifier * cover / sqrt(hunter_count),
                          perception * weather_visibility_modifier(weather) * sqrt(defender_count))


def resolve_stalking(scores, random_source):
    maximum = max(scores.concealment, scores.awareness)
    probability = ((scores.concealment / maximum) / (scores.concealment / maximum + scores.awareness / maximum)
                   if maximum else 0.0)
    if scores.cover == 0 or probability == 0:
        return StalkingResult(scores, 0.0, None, False, 1.0)
    roll = random_source.random()
    unnoticed = roll < probability
    # Starting-distance advantage only; mobility itself and injuries are intact.
    multiplier = 1 - 0.5 * scores.cover if unnoticed else 1.0
    return StalkingResult(scores, probability, roll, unnoticed, multiplier)
