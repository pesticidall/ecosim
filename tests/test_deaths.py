import unittest


class TestDeaths(unittest.TestCase):
    def test_records_starvation_counts_and_validates_mass(self) -> None:
        from simulation.deaths import DeathCause, create_starvation_death

        definition = {"id": "prey", "typical_adult_mass_kg": 3.5}
        self.assertIsNone(create_starvation_death(definition, 0))
        record = create_starvation_death(definition, 2)
        self.assertIs(record.cause, DeathCause.STARVATION)
        self.assertEqual(record.count, 2)
        self.assertEqual(record.body_mass_kg, 3.5)
        for count, error in ((True, TypeError), (-1, ValueError), (1.5, TypeError)):
            with self.subTest(count=count), self.assertRaises(error):
                create_starvation_death(definition, count)
        for mass in (0.0, -1.0, float("nan"), float("inf")):
            with self.subTest(mass=mass), self.assertRaises(ValueError):
                create_starvation_death({**definition, "typical_adult_mass_kg": mass}, 1)
    def test_secured_hunt_creates_predation_death(
        self,
    ) -> None:
        from simulation.deaths import (
            DeathCause,
            create_predation_death,
        )
        from simulation.hunting import build_hunt_outcome

        secured_outcome = build_hunt_outcome(
            detected=True,
            caught=True,
            hit=True,
            detained=True,
        )
        escaped_outcome = build_hunt_outcome(
            detected=True,
            caught=True,
            hit=True,
            detained=False,
        )
        prey_definition = {
            "id": "scrub_hare",
            "typical_adult_mass_kg": 3.5,
        }

        predation_death = create_predation_death(
            hunt_outcome=secured_outcome,
            prey_definition=prey_definition,
        )
        escaped_death = create_predation_death(
            hunt_outcome=escaped_outcome,
            prey_definition=prey_definition,
        )

        self.assertIsNone(escaped_death)
        self.assertIsNotNone(predation_death)
        self.assertEqual(
            predation_death.animal_id,
            "scrub_hare",
        )
        self.assertIs(
            predation_death.cause,
            DeathCause.PREDATION,
        )
        self.assertEqual(
            predation_death.count,
            1,
        )
        self.assertEqual(
            predation_death.body_mass_kg,
            3.5,
        )


if __name__ == "__main__":
    unittest.main()
