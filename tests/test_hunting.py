import unittest

from simulation.hunting import calculate_detection_scores


class TestHunting(unittest.TestCase):
    def test_calculates_detection_scores_from_activity_and_weather(
        self,
    ) -> None:
        detector_definition = {
            "id": "caracal",
            "statistics": {
                "perception": 8.0,
            },
        }
        target_definition = {
            "id": "scrub_hare",
            "statistics": {
                "stealth": 7.0,
            },
        }
        weather_definition = {
            "id": "heavy_fog",
            "visibility_modifier": 0.45,
        }

        scores = calculate_detection_scores(
            detector_definition,
            target_definition,
            activity_overlap_modifier=0.5,
            weather_definition=weather_definition,
        )

        self.assertEqual(scores.detector_perception, 8.0)
        self.assertEqual(scores.target_stealth, 7.0)
        self.assertEqual(
            scores.activity_overlap_modifier,
            0.5,
        )
        self.assertEqual(
            scores.weather_visibility_modifier,
            0.45,
        )
        self.assertAlmostEqual(
            scores.effective_perception,
            1.8,
        )
        self.assertEqual(scores.effective_stealth, 7.0)


if __name__ == "__main__":
    unittest.main()