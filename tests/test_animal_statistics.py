import unittest

from simulation.animal_statistics import weight_class_for_mass


class TestAnimalStatistics(unittest.TestCase):
    def test_derives_representative_weight_classes(self) -> None:
        expected_classes = {
            3.5: "very_light",
            10.0: "light",
            35.0: "medium",
            100.0: "heavy",
            300.0: "very_heavy",
        }

        for mass_kg, expected_class in expected_classes.items():
            with self.subTest(mass_kg=mass_kg):
                self.assertEqual(
                    weight_class_for_mass(mass_kg),
                    expected_class,
                )

    def test_weight_class_boundaries_are_deterministic(self) -> None:
        boundary_cases = (
            (4.999, "very_light"),
            (5.0, "light"),
            (19.999, "light"),
            (20.0, "medium"),
            (74.999, "medium"),
            (75.0, "heavy"),
            (249.999, "heavy"),
            (250.0, "very_heavy"),
        )

        for mass_kg, expected_class in boundary_cases:
            with self.subTest(mass_kg=mass_kg):
                self.assertEqual(
                    weight_class_for_mass(mass_kg),
                    expected_class,
                )

    def test_rejects_invalid_mass_for_weight_class(self) -> None:
        invalid_cases = (
            (
                "heavy",
                TypeError,
                r"mass_kg must be a number",
            ),
            (
                True,
                TypeError,
                r"mass_kg must be a number",
            ),
            (
                float("nan"),
                ValueError,
                r"mass_kg must be finite",
            ),
            (
                float("inf"),
                ValueError,
                r"mass_kg must be finite",
            ),
            (
                float("-inf"),
                ValueError,
                r"mass_kg must be finite",
            ),
            (
                0,
                ValueError,
                r"mass_kg must be greater than zero",
            ),
            (
                -1.0,
                ValueError,
                r"mass_kg must be greater than zero",
            ),
        )

        for value, error_type, message_pattern in invalid_cases:
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    error_type,
                    message_pattern,
                ):
                    weight_class_for_mass(value)


if __name__ == "__main__":
    unittest.main()
