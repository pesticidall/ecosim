from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from math import isfinite
from random import Random


@dataclass(frozen=True)
class MonthlyWeatherSchedule:
    """Store ordered daily weather and aggregated monthly totals."""

    daily_weather_ids: tuple[str, ...]
    weather_day_totals: dict[str, int]

    @property
    def day_count(self) -> int:
        """Return the number of simulated days in the schedule."""
        return len(self.daily_weather_ids)


def build_monthly_weather_schedule(
    daily_weather_ids: Iterable[str],
    expected_day_count: int,
) -> MonthlyWeatherSchedule:
    """Build a monthly schedule from one weather ID per day."""
    if isinstance(expected_day_count, bool) or not isinstance(
        expected_day_count,
        int,
    ):
        raise TypeError(
            "expected_day_count must be an integer."
        )
    if expected_day_count <= 0:
        raise ValueError(
            "expected_day_count must be greater than zero."
        )

    weather_ids = tuple(daily_weather_ids)
    if len(weather_ids) != expected_day_count:
        raise ValueError(
            "Daily weather count must match "
            f"expected_day_count {expected_day_count}; received "
            f"{len(weather_ids)}."
        )

    for day_number, weather_id in enumerate(
        weather_ids,
        start=1,
    ):
        if not isinstance(weather_id, str):
            raise TypeError(
                f"Weather ID for day {day_number} must be a string."
            )
        if not weather_id.strip():
            raise ValueError(
                f"Weather ID for day {day_number} must not be empty."
            )

    return MonthlyWeatherSchedule(
        daily_weather_ids=weather_ids,
        weather_day_totals=dict(Counter(weather_ids)),
    )


def generate_monthly_weather_schedule(
    weather_weights: Mapping[str, int | float],
    expected_day_count: int,
    random_generator: Random,
) -> MonthlyWeatherSchedule:
    """Generate a reproducible weighted weather ID for every day."""
    validate_weather_weights(weather_weights)

    weather_ids = list(weather_weights)
    weights = [
        float(weight)
        for weight in weather_weights.values()
    ]
    daily_weather_ids = random_generator.choices(
        weather_ids,
        weights=weights,
        k=expected_day_count,
    )
    return build_monthly_weather_schedule(
        daily_weather_ids,
        expected_day_count,
    )


def validate_weather_weights(
    weather_weights: Mapping[str, int | float],
) -> None:
    """Validate weighted weather choices before schedule generation."""
    if not weather_weights:
        raise ValueError(
            "weather_weights must not be empty."
        )

    total_weight = 0.0
    for weather_id, weight in weather_weights.items():
        if not isinstance(weather_id, str):
            raise TypeError(
                "Weather weight IDs must be strings."
            )
        if not weather_id.strip():
            raise ValueError(
                "Weather weight IDs must not be empty."
            )
        if isinstance(weight, bool) or not isinstance(
            weight,
            (int, float),
        ):
            raise TypeError(
                f"Weather weight for '{weather_id}' must be a number."
            )
        if not isfinite(weight):
            raise ValueError(
                f"Weather weight for '{weather_id}' must be finite."
            )
        if weight < 0:
            raise ValueError(
                f"Weather weight for '{weather_id}' must not be negative."
            )

        total_weight += float(weight)

    if total_weight <= 0.0:
        raise ValueError(
            "At least one weather weight must be greater than zero."
        )


def weather_id_for_day(
    schedule: MonthlyWeatherSchedule,
    day_of_month: int,
) -> str:
    """Return the weather ID assigned to a one-based calendar day."""
    if isinstance(day_of_month, bool) or not isinstance(
        day_of_month,
        int,
    ):
        raise TypeError(
            "day_of_month must be an integer."
        )
    if not 1 <= day_of_month <= schedule.day_count:
        raise ValueError(
            f"day_of_month must be between 1 and "
            f"{schedule.day_count}."
        )

    return schedule.daily_weather_ids[day_of_month - 1]


def weather_visibility_modifier(
    weather_definition: Mapping[str, object],
) -> float:
    """Return a weather condition's visibility modifier."""
    return float(
        weather_definition.get(
            "visibility_modifier",
            1.0,
        )
    )
