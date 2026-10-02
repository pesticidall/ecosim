import unittest

from simulation.activity import (
    activity_phase_weights,
    calculate_activity_overlap,
    calculate_activity_overlap_modifier,
    calculate_activity_totals,
)
from simulation.calendar import ActivityPhase


class TestActivity(unittest.TestCase):
    def test_calculates_activity_overlap_by_phase(self) -> None:
        diurnal_totals = {
            ActivityPhase.DAY: 31.0,
            ActivityPhase.NIGHT: 0.0,
        }
        crepuscular_totals = {
            ActivityPhase.DAY: 15.5,
            ActivityPhase.NIGHT: 15.5,
        }
        self.assertEqual(
            calculate_activity_overlap(
                diurnal_totals,
                crepuscular_totals,
            ),
            {
                ActivityPhase.DAY: 15.5,
                ActivityPhase.NIGHT: 0.0,
            },
        )

    def test_calculates_monthly_activity_totals(self) -> None:
        phase_totals = {
            ActivityPhase.DAY: 31,
            ActivityPhase.NIGHT: 31,
        }
        expected_totals = {
            "diurnal": {
                ActivityPhase.DAY: 31.0,
                ActivityPhase.NIGHT: 0.0,
            },
            "nocturnal": {
                ActivityPhase.DAY: 0.0,
                ActivityPhase.NIGHT: 31.0
            },
            "crepuscular": {
                ActivityPhase.DAY: 15.5,
                ActivityPhase.NIGHT: 15.5,
            },
            "flexible": {
                ActivityPhase.DAY: 31.0,
                ActivityPhase.NIGHT: 31.0,
            },
        }
        for activity_pattern, expected in expected_totals.items():
            with self.subTest(activity_pattern=activity_pattern):
                self.assertEqual(
                    calculate_activity_totals(
                        activity_pattern,
                        phase_totals,
                    ),
                    expected,
                )

    def test_normalizes_activity_overlap_for_encounters(
        self,
    ) -> None:
        phase_totals = {
            ActivityPhase.DAY: 31,
            ActivityPhase.NIGHT: 31,
        }
        totals_by_pattern = {
            pattern: calculate_activity_totals(
                pattern,
                phase_totals,
            )
            for pattern in (
                "diurnal",
                "nocturnal",
                "crepuscular",
                "flexible",
            )
        }
        examples = (
            ("diurnal", "diurnal", 1.0),
            ("diurnal", "nocturnal", 0.0),
            ("diurnal", "crepuscular", 0.5),
            ("diurnal", "flexible", 1.0),
        )

        for first_pattern, second_pattern, expected in examples:
            with self.subTest(
                first_pattern=first_pattern,
                second_pattern=second_pattern,
            ):
                self.assertEqual(
                    calculate_activity_overlap_modifier(
                        totals_by_pattern[first_pattern],
                        totals_by_pattern[second_pattern],
                    ),
                    expected,
                )

    def test_activity_patterns_have_distinct_phase_weights(self) -> None:
        expected_weights = {
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

        for activity_pattern, expected in expected_weights.items():
            with self.subTest(activity_pattern=activity_pattern):
                self.assertEqual(
                    activity_phase_weights(activity_pattern),
                    expected,
                )

    def test_rejects_supported_activity_pattern(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            r"Unsupported activity pattern.*cathermal",
        ):
            activity_phase_weights("cathermal")

if __name__ == "__main__":
    unittest.main()
