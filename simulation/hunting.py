from dataclasses import dataclass
from math import isfinite
from typing import Any

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
) -> DetectionScores:
    """Apply activity and visibility context to detection scores"""
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
    return DetectionScores(
        detector_perception=detector_perception,
        target_stealth=target_stealth,
        activity_overlap_modifier=activity_overlap_modifier,
        weather_visibility_modifier=visibility_modifier,
        effective_perception=(
            detector_perception
            * activity_overlap_modifier
            * visibility_modifier
        ),
        effective_stealth=target_stealth
    )