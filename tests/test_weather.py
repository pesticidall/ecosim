import unittest
from random import Random

from simulation.weather import (
    build_monthly_weather_schedule,
    generate_monthly_weather_schedule,
    weather_id_for_day,
    weather_visibility_modifier,
)


class TestWeather(unittest.TestCase):
    def test_builds_daily_schedule_and_monthly_totals(
        self,
    ) -> None:
        daily_weather_ids = (
            ["clear"] * 14
            + ["seasonal_rain"] * 9
            + ["heavy_rain"] * 3
            + ["mist"] * 4
            + ["heavy_fog"]
        )

        schedule = build_monthly_weather_schedule(
            daily_weather_ids,
            expected_day_count=31,
        )

        self.assertEqual(schedule.day_count, 31)
        self.assertEqual(
            schedule.daily_weather_ids,
            tuple(daily_weather_ids),
        )
        self.assertEqual(
            schedule.weather_day_totals,
            {
                "clear": 14,
                "seasonal_rain": 9,
                "heavy_rain": 3,
                "mist": 4,
                "heavy_fog": 1,
            },
        )

    def test_rejects_schedule_with_wrong_day_count(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            r"expected_day_count 31.*received 30",
        ):
            build_monthly_weather_schedule(
                ["clear"] * 30,
                expected_day_count=31,
            )

    def test_seeded_weather_generation_is_reproducible(
        self,
    ) -> None:
        weather_weights = {
            "clear": 5.0,
            "seasonal_rain": 3.0,
            "heavy_rain": 1.0,
            "mist": 1.0,
            "heavy_fog": 0.5,
            "strong_wind": 1.0,
        }

        first_schedule = generate_monthly_weather_schedule(
            weather_weights,
            expected_day_count=31,
            random_generator=Random(104729),
        )
        second_schedule = generate_monthly_weather_schedule(
            weather_weights,
            expected_day_count=31,
            random_generator=Random(104729),
        )

        self.assertEqual(
            first_schedule,
            second_schedule,
        )
        self.assertEqual(first_schedule.day_count, 31)
        self.assertEqual(
            sum(first_schedule.weather_day_totals.values()),
            31,
        )

    def test_returns_weather_for_one_based_calendar_day(
        self,
    ) -> None:
        schedule = build_monthly_weather_schedule(
            [
                "clear",
                "mist",
                "heavy_rain",
            ],
            expected_day_count=3,
        )

        self.assertEqual(
            weather_id_for_day(schedule, 1),
            "clear",
        )
        self.assertEqual(
            weather_id_for_day(schedule, 3),
            "heavy_rain",
        )

    def test_rejects_day_outside_weather_schedule(self) -> None:
        schedule = build_monthly_weather_schedule(
            ["clear"] * 31,
            expected_day_count=31,
        )

        for day_of_month in (0, 32):
            with self.subTest(day_of_month=day_of_month):
                with self.assertRaisesRegex(
                    ValueError,
                    r"day_of_month must be between 1 and 31",
                ):
                    weather_id_for_day(
                        schedule,
                        day_of_month,
                    )

    def test_returns_weather_visibility_or_neutral_default(
        self,
    ) -> None:
        self.assertEqual(
            weather_visibility_modifier(
                {
                    "id": "heavy_fog",
                    "visibility_modifier": 0.45,
                }
            ),
            0.45,
        )
        self.assertEqual(
            weather_visibility_modifier(
                {
                    "id": "clear",
                }
            ),
            1.0,
        )


if __name__ == "__main__":
    unittest.main()
