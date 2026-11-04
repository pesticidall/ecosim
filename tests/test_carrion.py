import unittest


class TestCarrion(unittest.TestCase):
    def test_creates_carrion_from_predation_death(
        self,
    ) -> None:
        from simulation.carrion import create_carrion_from_death
        from simulation.deaths import (
            DeathCause,
            DeathRecord,
        )

        death = DeathRecord(
            animal_id="scrub_hare",
            cause=DeathCause.PREDATION,
            count=1,
            body_mass_kg=3.5,
        )

        carrion = create_carrion_from_death(
            death_record=death,
            habitat_id="acacia_scrub",
            first_access_consumer_id="caracal",
        )

        self.assertEqual(
            carrion.source_animal_id,
            "scrub_hare",
        )
        self.assertEqual(
            carrion.habitat_id,
            "acacia_scrub",
        )
        self.assertEqual(
            carrion.original_biomass_kg,
            3.5,
        )
        self.assertEqual(
            carrion.available_biomass_kg,
            3.5,
        )
        self.assertEqual(
            carrion.first_access_consumer_id,
            "caracal",
        )

    def test_first_access_consumer_eats_from_carrion(
        self,
    ) -> None:
        from simulation.carrion import (
            CarrionDeposit,
            consume_carrion,
        )

        carrion = CarrionDeposit(
            source_animal_id="scrub_hare",
            habitat_id="acacia_scrub",
            original_biomass_kg=3.5,
            available_biomass_kg=3.5,
            first_access_consumer_id="caracal",
        )

        consumption = consume_carrion(
            carrion=carrion,
            consumer_id="caracal",
            requested_biomass_kg=2.0,
        )

        self.assertEqual(
            consumption.consumer_id,
            "caracal",
        )
        self.assertEqual(
            consumption.requested_biomass_kg,
            2.0,
        )
        self.assertEqual(
            consumption.consumed_biomass_kg,
            2.0,
        )
        self.assertEqual(
            consumption.updated_carrion.original_biomass_kg,
            3.5,
        )
        self.assertEqual(
            consumption.updated_carrion.available_biomass_kg,
            1.5,
        )
        self.assertEqual(
            carrion.available_biomass_kg,
            3.5,
        )

    def test_blocks_other_consumers_during_first_access(
        self,
    ) -> None:
        from simulation.carrion import (
            CarrionDeposit,
            consume_carrion,
        )

        carrion = CarrionDeposit(
            source_animal_id="scrub_hare",
            habitat_id="acacia_scrub",
            original_biomass_kg=3.5,
            available_biomass_kg=3.5,
            first_access_consumer_id="caracal",
        )

        consumption = consume_carrion(
            carrion=carrion,
            consumer_id="brown_hyena",
            requested_biomass_kg=2.0,
        )

        self.assertFalse(consumption.access_granted)
        self.assertEqual(
            consumption.consumed_biomass_kg,
            0.0,
        )
        self.assertIs(
            consumption.updated_carrion,
            carrion,
        )
        self.assertEqual(
            consumption.updated_carrion.available_biomass_kg,
            3.5,
        )

    def test_first_access_consumer_releases_remaining_carrion(
        self,
    ) -> None:
        from simulation.carrion import (
            CarrionDeposit,
            release_first_access,
        )

        carrion = CarrionDeposit(
            source_animal_id="scrub_hare",
            habitat_id="acacia_scrub",
            original_biomass_kg=3.5,
            available_biomass_kg=1.5,
            first_access_consumer_id="caracal",
        )

        released_carrion = release_first_access(
            carrion=carrion,
            consumer_id="caracal",
        )

        self.assertIsNone(
            released_carrion.first_access_consumer_id,
        )
        self.assertEqual(
            released_carrion.available_biomass_kg,
            1.5,
        )
        self.assertEqual(
            released_carrion.original_biomass_kg,
            3.5,
        )
        self.assertEqual(
            carrion.first_access_consumer_id,
            "caracal",
        )

    def test_rejects_negative_carrion_consumption_request(
        self,
    ) -> None:
        from simulation.carrion import (
            CarrionDeposit,
            consume_carrion,
        )

        carrion = CarrionDeposit(
            source_animal_id="scrub_hare",
            habitat_id="acacia_scrub",
            original_biomass_kg=3.5,
            available_biomass_kg=1.5,
            first_access_consumer_id=None,
        )

        with self.assertRaisesRegex(
            ValueError,
            r"requested_biomass_kg.*zero or greater",
        ):
            consume_carrion(
                carrion=carrion,
                consumer_id="brown_hyena",
                requested_biomass_kg=-1.0,
            )

    def test_rejects_nonfinite_carrion_consumption_request(
        self,
    ) -> None:
        from math import inf, nan

        from simulation.carrion import (
            CarrionDeposit,
            consume_carrion,
        )

        carrion = CarrionDeposit(
            source_animal_id="scrub_hare",
            habitat_id="acacia_scrub",
            original_biomass_kg=3.5,
            available_biomass_kg=1.5,
            first_access_consumer_id=None,
        )

        for invalid_request in (
            nan,
            inf,
            -inf,
        ):
            with (
                self.subTest(requested_biomass_kg=invalid_request),
                self.assertRaisesRegex(
                    ValueError,
                    r"requested_biomass_kg.*must be finite",
                ),
            ):
                consume_carrion(
                    carrion=carrion,
                    consumer_id="brown_hyena",
                    requested_biomass_kg=invalid_request,
                )

    def test_rejects_nonnumeric_carrion_consumption_request(
        self,
    ) -> None:
        from simulation.carrion import (
            CarrionDeposit,
            consume_carrion,
        )

        carrion = CarrionDeposit(
            source_animal_id="scrub_hare",
            habitat_id="acacia_scrub",
            original_biomass_kg=3.5,
            available_biomass_kg=1.5,
            first_access_consumer_id=None,
        )

        for invalid_request in (
            "1.0",
            True,
            None,
        ):
            with (
                self.subTest(requested_biomass_kg=invalid_request),
                self.assertRaisesRegex(
                    TypeError,
                    r"requested_biomass_kg.*must be numeric",
                ),
            ):
                consume_carrion(
                    carrion=carrion,
                    consumer_id="brown_hyena",
                    requested_biomass_kg=invalid_request,
                )

    def test_decays_available_carrion_biomass(
        self,
    ) -> None:
        from simulation.carrion import (
            CarrionDeposit,
            decay_carrion,
        )

        carrion = CarrionDeposit(
            source_animal_id="scrub_hare",
            habitat_id="acacia_scrub",
            original_biomass_kg=3.5,
            available_biomass_kg=1.5,
            first_access_consumer_id=None,
        )

        decay = decay_carrion(
            carrion=carrion,
            decay_fraction=0.2,
        )

        self.assertAlmostEqual(
            decay.decayed_biomass_kg,
            0.3,
        )
        self.assertEqual(
            decay.updated_carrion.original_biomass_kg,
            3.5,
        )
        self.assertAlmostEqual(
            decay.updated_carrion.available_biomass_kg,
            1.2,
        )
        self.assertEqual(
            carrion.available_biomass_kg,
            1.5,
        )

    def test_rejects_invalid_carrion_decay_fraction(
        self,
    ) -> None:
        from math import inf, nan

        from simulation.carrion import (
            CarrionDeposit,
            decay_carrion,
        )

        carrion = CarrionDeposit(
            source_animal_id="scrub_hare",
            habitat_id="acacia_scrub",
            original_biomass_kg=3.5,
            available_biomass_kg=1.5,
            first_access_consumer_id=None,
        )
        invalid_values = (
            (
                "0.2",
                TypeError,
                r"decay_fraction.*must be numeric",
            ),
            (
                True,
                TypeError,
                r"decay_fraction.*must be numeric",
            ),
            (
                None,
                TypeError,
                r"decay_fraction.*must be numeric",
            ),
            (
                nan,
                ValueError,
                r"decay_fraction.*must be finite",
            ),
            (
                inf,
                ValueError,
                r"decay_fraction.*must be finite",
            ),
            (
                -inf,
                ValueError,
                r"decay_fraction.*must be finite",
            ),
            (
                -0.1,
                ValueError,
                r"decay_fraction.*between zero and one",
            ),
            (
                1.1,
                ValueError,
                r"decay_fraction.*between zero and one",
            ),
        )

        for invalid_value, error_type, error_pattern in invalid_values:
            with (
                self.subTest(decay_fraction=invalid_value),
                self.assertRaisesRegex(
                    error_type,
                    error_pattern,
                ),
            ):
                decay_carrion(
                    carrion=carrion,
                    decay_fraction=invalid_value,
                )


if __name__ == "__main__":
    unittest.main()