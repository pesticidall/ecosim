from simulation.calendar import ActivityPhase

_ACTIVITY_PHASE_WEIGHTS = {
    "diurnal": {
        ActivityPhase.DAY: 1.0,
        ActivityPhase.NIGHT: 0.0,
    },
    "nocturnal": {
        ActivityPhase.DAY: 0.0,
        ActivityPhase.NIGHT: 1.0,
    },
    "crepuscular": {
        ActivityPhase.DAY: 0.5,
        ActivityPhase.NIGHT: 0.5,
    },
    "flexible": {
        ActivityPhase.DAY: 1.0,
        ActivityPhase.NIGHT: 1.0,
    },
}

def activity_phase_weights(
    activity_pattern: str,
) -> dict[ActivityPhase, float]:
    """Return independent phase weights for a supported activity pattern."""
    try:
        weights = _ACTIVITY_PHASE_WEIGHTS[activity_pattern]
    except KeyError:
        raise ValueError(
            f"Unsupported activity pattern '{activity_pattern}'."
        ) from None
    return dict(weights)

def calculate_activity_totals(
    activity_pattern: str,
    phase_totals: dict[ActivityPhase, int],
) -> dict[ActivityPhase, float]:
    """Convert calendar phase totals into an animal's active phase-days."""
    weights = activity_phase_weights(activity_pattern)
    return {
        phase: phase_totals[phase] * weight
        for phase, weight in weights.items()
    }

def calculate_activity_overlap(
    first_totals: dict[ActivityPhase, float],
    second_totals: dict[ActivityPhase, float],
) -> dict[ActivityPhase, float]:
    """Measure the phase-days when two activity schedules overlap."""
    return {
        phase: min(
            first_totals[phase],
            second_totals[phase],
        )
        for phase in ActivityPhase
    }


def calculate_activity_overlap_modifier(
    first_totals: dict[ActivityPhase, float],
    second_totals: dict[ActivityPhase, float],
) -> float:
    """Return the share of the narrower activity schedule that overlaps."""
    overlap_totals = calculate_activity_overlap(
        first_totals,
        second_totals,
    )
    maximum_possible_overlap = min(
        sum(first_totals.values()),
        sum(second_totals.values()),
    )
    if maximum_possible_overlap <= 0.0:
        return 0.0

    return (
        sum(overlap_totals.values())
        / maximum_possible_overlap
    )
