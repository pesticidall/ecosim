import unittest


class TestTrauma(unittest.TestCase):
    def test_attack_method_target_selects_matching_trait_effect(self) -> None:
        from simulation.trauma import (
            calculate_trauma_pressure,
            create_trauma_event,
        )

        trauma = create_trauma_event(
            source_stage="attack",
            contact_succeeded=True,
            contact_power=8.0,
            opposing_defense=3.0,
            attack_method_id="test_method",
            attacker_mass_kg=10.0,
            target_mass_kg=10.0,
            contact_quality=0.5,
        )
        method_definition = {
            "entity_type": "attack_method",
            "id": "test_method",
            "name": "Test Method",
            "description": "Verifies data-driven trait targeting.",
            "trauma_modifier": 1.5,
            "trait_effect_target": "grapple_effectiveness",
        }
        trait_definition = {
            "entity_type": "trait",
            "id": "test_trait",
            "name": "Test Trait",
            "description": "Modifies two different attack methods.",
            "effects": [
                {"target": "grapple_effectiveness", "modifier": 1.2},
                {"target": "bite_effectiveness", "modifier": 2.0},
            ],
        }

        pressure = calculate_trauma_pressure(
            trauma,
            attack_method_definition=method_definition,
            trait_ids=("test_trait",),
            trait_definitions=(trait_definition,),
        )

        self.assertAlmostEqual(pressure.contact_pressure, 7.2)
        self.assertEqual(pressure.opposing_defense, 3.0)
        self.assertEqual(pressure.attack_method_id, "test_method")

    def test_rejects_mismatched_attack_method_definition(self) -> None:
        from simulation.trauma import (
            calculate_trauma_pressure,
            create_trauma_event,
        )

        trauma = create_trauma_event(
            source_stage="attack",
            contact_succeeded=True,
            contact_power=8.0,
            opposing_defense=3.0,
            attack_method_id="bite",
            attacker_mass_kg=10.0,
            target_mass_kg=10.0,
        )
        method_definition = {
            "entity_type": "attack_method",
            "id": "grapple",
            "name": "Grapple",
            "description": "Uses the limbs and body to restrain prey.",
            "trauma_modifier": 1.0,
            "trait_effect_target": "grapple_effectiveness",
        }

        with self.assertRaisesRegex(
            ValueError,
            r"attack method.*grapple.*does not match.*bite",
        ):
            calculate_trauma_pressure(
                trauma,
                attack_method_definition=method_definition,
            )

    def test_attack_method_modifier_scales_trauma_pressure(self) -> None:
        from simulation.trauma import (
            calculate_trauma_pressure,
            create_trauma_event,
        )

        trauma = create_trauma_event(
            source_stage="attack",
            contact_succeeded=True,
            contact_power=8.0,
            opposing_defense=3.0,
            attack_method_id="test_method",
            attacker_mass_kg=10.0,
            target_mass_kg=10.0,
            contact_quality=0.5,
        )
        method_definition = {
            "entity_type": "attack_method",
            "id": "test_method",
            "name": "Test Method",
            "description": "A method used to verify trauma scaling.",
            "trauma_modifier": 1.5,
            "trait_effect_target": "bite_effectiveness",
        }

        pressure = calculate_trauma_pressure(
            trauma,
            attack_method_definition=method_definition,
        )

        self.assertAlmostEqual(pressure.contact_pressure, 6.0)
        self.assertEqual(pressure.attack_method_id, "test_method")
        self.assertEqual(pressure.opposing_defense, 3.0)
        self.assertEqual(trauma.contact_power, 8.0)

    def test_creates_trauma_only_after_successful_contact(
        self,
    ) -> None:
        from simulation.trauma import create_trauma_event

        missed_trauma = create_trauma_event(
            source_stage="attack",
            contact_succeeded=False,
            contact_power=7.0,
            opposing_defense=5.0,
        )
        landed_trauma = create_trauma_event(
            source_stage="counterattack",
            contact_succeeded=True,
            attack_method_id="strike",
            contact_power=3.3,
            attacker_mass_kg=3.5,
            opposing_defense=6.0,
            target_mass_kg=14.0,
            contact_quality=0.8,
        )

        self.assertIsNone(missed_trauma)
        self.assertIsNotNone(landed_trauma)
        self.assertEqual(
            landed_trauma.source_stage,
            "counterattack",
        )
        self.assertEqual(
            landed_trauma.contact_power,
            3.3,
        )
        self.assertEqual(
            landed_trauma.opposing_defense,
            6.0,
        )

    def test_trauma_preserves_method_mass_and_contact_quality(
        self,
    ) -> None:
        from simulation.trauma import create_trauma_event

        trauma = create_trauma_event(
            source_stage="counterattack",
            contact_succeeded=True,
            attack_method_id="strike",
            contact_power=3.3,
            attacker_mass_kg=3.5,
            opposing_defense=6.0,
            target_mass_kg=14.0,
            contact_quality=0.8,
        )

        self.assertIsNotNone(trauma)
        self.assertEqual(
            trauma.attack_method_id,
            "strike",
        )
        self.assertEqual(
            trauma.attacker_mass_kg,
            3.5,
        )
        self.assertEqual(
            trauma.target_mass_kg,
            14.0,
        )
        self.assertEqual(
            trauma.contact_quality,
            0.8,
        )

    def test_requires_complete_context_for_successful_contact(
        self,
    ) -> None:
        from simulation.trauma import create_trauma_event

        complete_context = {
            "source_stage": "attack",
            "contact_succeeded": True,
            "attack_method_id": "bite",
            "contact_power": 7.0,
            "attacker_mass_kg": 13.0,
            "opposing_defense": 4.0,
            "target_mass_kg": 3.5,
            "contact_quality": 0.9,
        }

        for missing_field in (
            "attack_method_id",
            "attacker_mass_kg",
            "target_mass_kg",
        ):
            with self.subTest(missing_field=missing_field):
                incomplete_context = complete_context.copy()
                incomplete_context.pop(missing_field)

                with self.assertRaisesRegex(
                    ValueError,
                    rf"{missing_field}.*required.*successful contact",
                ):
                    create_trauma_event(**incomplete_context)

    def test_rejects_nonpositive_mass_for_successful_contact(
        self,
    ) -> None:
        from simulation.trauma import create_trauma_event

        complete_context = {
            "source_stage": "attack",
            "contact_succeeded": True,
            "attack_method_id": "bite",
            "contact_power": 7.0,
            "attacker_mass_kg": 13.0,
            "opposing_defense": 4.0,
            "target_mass_kg": 3.5,
            "contact_quality": 0.9,
        }

        for field_name in (
            "attacker_mass_kg",
            "target_mass_kg",
        ):
            for invalid_mass in (0.0, -1.0):
                with self.subTest(
                    field_name=field_name,
                    invalid_mass=invalid_mass,
                ):
                    invalid_context = complete_context.copy()
                    invalid_context[field_name] = invalid_mass

                    with self.assertRaisesRegex(
                        ValueError,
                        rf"{field_name}.*greater than zero",
                    ):
                        create_trauma_event(**invalid_context)

    def test_rejects_nonfinite_mass_for_successful_contact(
        self,
    ) -> None:
        from math import inf, nan

        from simulation.trauma import create_trauma_event

        complete_context = {
            "source_stage": "attack",
            "contact_succeeded": True,
            "attack_method_id": "bite",
            "contact_power": 7.0,
            "attacker_mass_kg": 13.0,
            "opposing_defense": 4.0,
            "target_mass_kg": 3.5,
            "contact_quality": 0.9,
        }

        for field_name in (
            "attacker_mass_kg",
            "target_mass_kg",
        ):
            for invalid_mass in (
                nan,
                inf,
                -inf,
            ):
                with self.subTest(
                    field_name=field_name,
                    invalid_mass=invalid_mass,
                ):
                    invalid_context = complete_context.copy()
                    invalid_context[field_name] = invalid_mass

                    with self.assertRaisesRegex(
                        ValueError,
                        rf"{field_name}.*must be finite",
                    ):
                        create_trauma_event(**invalid_context)

    def test_rejects_nonfinite_contact_quality(
        self,
    ) -> None:
        from math import inf, nan

        from simulation.trauma import create_trauma_event

        for invalid_quality in (
            nan,
            inf,
            -inf,
        ):
            with (
                self.subTest(
                    contact_quality=invalid_quality,
                ),
                self.assertRaisesRegex(
                    ValueError,
                    r"contact_quality.*must be finite",
                ),
            ):
                create_trauma_event(
                    source_stage="attack",
                    contact_succeeded=True,
                    attack_method_id="bite",
                    contact_power=7.0,
                    attacker_mass_kg=13.0,
                    opposing_defense=4.0,
                    target_mass_kg=3.5,
                    contact_quality=invalid_quality,
                )

    def test_rejects_contact_quality_outside_normalized_range(
        self,
    ) -> None:
        from simulation.trauma import create_trauma_event

        for invalid_quality in (
            -0.1,
            0.0,
            1.1,
        ):
            with (
                self.subTest(
                    contact_quality=invalid_quality,
                ),
                self.assertRaisesRegex(
                    ValueError,
                    r"contact_quality.*greater than zero.*at most one",
                ),
            ):
                create_trauma_event(
                    source_stage="attack",
                    contact_succeeded=True,
                    attack_method_id="bite",
                    contact_power=7.0,
                    attacker_mass_kg=13.0,
                    opposing_defense=4.0,
                    target_mass_kg=3.5,
                    contact_quality=invalid_quality,
                )

    def test_rejects_nonfinite_trauma_statistics(
        self,
    ) -> None:
        from math import inf, nan

        from simulation.trauma import create_trauma_event

        complete_context = {
            "source_stage": "attack",
            "contact_succeeded": True,
            "attack_method_id": "bite",
            "contact_power": 7.0,
            "attacker_mass_kg": 13.0,
            "opposing_defense": 4.0,
            "target_mass_kg": 3.5,
            "contact_quality": 0.9,
        }

        for field_name in (
            "contact_power",
            "opposing_defense",
        ):
            for invalid_value in (
                nan,
                inf,
                -inf,
            ):
                with (
                    self.subTest(
                        field_name=field_name,
                        invalid_value=invalid_value,
                    ),
                    self.assertRaisesRegex(
                        ValueError,
                        rf"{field_name}.*must be finite",
                    ),
                ):
                    invalid_context = complete_context.copy()
                    invalid_context[field_name] = invalid_value
                    create_trauma_event(**invalid_context)

    def test_rejects_invalid_trauma_statistic_ranges(
        self,
    ) -> None:
        from simulation.trauma import create_trauma_event

        complete_context = {
            "source_stage": "attack",
            "contact_succeeded": True,
            "attack_method_id": "bite",
            "contact_power": 7.0,
            "attacker_mass_kg": 13.0,
            "opposing_defense": 4.0,
            "target_mass_kg": 3.5,
            "contact_quality": 0.9,
        }

        invalid_values = (
            (
                "contact_power",
                0.0,
                r"contact_power.*greater than zero",
            ),
            (
                "contact_power",
                -1.0,
                r"contact_power.*greater than zero",
            ),
            (
                "opposing_defense",
                -1.0,
                r"opposing_defense.*zero or greater",
            ),
        )

        for field_name, invalid_value, error_pattern in invalid_values:
            with (
                self.subTest(
                    field_name=field_name,
                    invalid_value=invalid_value,
                ),
                self.assertRaisesRegex(
                    ValueError,
                    error_pattern,
                ),
            ):
                invalid_context = complete_context.copy()
                invalid_context[field_name] = invalid_value
                create_trauma_event(**invalid_context)

    def test_rejects_boolean_trauma_numeric_inputs(
        self,
    ) -> None:
        from simulation.trauma import create_trauma_event

        complete_context = {
            "source_stage": "attack",
            "contact_succeeded": True,
            "attack_method_id": "bite",
            "contact_power": 7.0,
            "attacker_mass_kg": 13.0,
            "opposing_defense": 4.0,
            "target_mass_kg": 3.5,
            "contact_quality": 0.9,
        }

        for field_name in (
            "contact_power",
            "attacker_mass_kg",
            "opposing_defense",
            "target_mass_kg",
            "contact_quality",
        ):
            with (
                self.subTest(field_name=field_name),
                self.assertRaisesRegex(
                    TypeError,
                    rf"{field_name}.*must be numeric",
                ),
            ):
                invalid_context = complete_context.copy()
                invalid_context[field_name] = True
                create_trauma_event(**invalid_context)

    def test_rejects_invalid_trauma_identifiers(
        self,
    ) -> None:
        from simulation.trauma import create_trauma_event

        complete_context = {
            "source_stage": "attack",
            "contact_succeeded": True,
            "attack_method_id": "bite",
            "contact_power": 7.0,
            "attacker_mass_kg": 13.0,
            "opposing_defense": 4.0,
            "target_mass_kg": 3.5,
            "contact_quality": 0.9,
        }

        for field_name in (
            "source_stage",
            "attack_method_id",
        ):
            for invalid_identifier in (
                "",
                "Talon Strike",
                "talon-strike",
            ):
                with (
                    self.subTest(
                        field_name=field_name,
                        invalid_identifier=invalid_identifier,
                    ),
                    self.assertRaisesRegex(
                        ValueError,
                        rf"{field_name}.*lowercase snake_case",
                    ),
                ):
                    invalid_context = complete_context.copy()
                    invalid_context[field_name] = invalid_identifier
                    create_trauma_event(**invalid_context)

    def test_rejects_nonstring_trauma_identifiers(
        self,
    ) -> None:
        from simulation.trauma import create_trauma_event

        complete_context = {
            "source_stage": "attack",
            "contact_succeeded": True,
            "attack_method_id": "bite",
            "contact_power": 7.0,
            "attacker_mass_kg": 13.0,
            "opposing_defense": 4.0,
            "target_mass_kg": 3.5,
            "contact_quality": 0.9,
        }

        for field_name in (
            "source_stage",
            "attack_method_id",
        ):
            with (
                self.subTest(field_name=field_name),
                self.assertRaisesRegex(
                    TypeError,
                    rf"{field_name}.*must be a string",
                ),
            ):
                invalid_context = complete_context.copy()
                invalid_context[field_name] = 42
                create_trauma_event(**invalid_context)

    def test_compresses_relative_mass_advantage(
        self,
    ) -> None:
        from simulation.trauma import calculate_relative_mass_factor

        equal_mass_factor = calculate_relative_mass_factor(
            attacker_mass_kg=10.0,
            target_mass_kg=10.0,
        )
        heavier_attacker_factor = calculate_relative_mass_factor(
            attacker_mass_kg=40.0,
            target_mass_kg=10.0,
        )
        heavier_target_factor = calculate_relative_mass_factor(
            attacker_mass_kg=10.0,
            target_mass_kg=40.0,
        )

        self.assertEqual(equal_mass_factor, 1.0)
        self.assertGreater(
            heavier_attacker_factor,
            1.0,
        )
        self.assertLess(
            heavier_attacker_factor,
            4.0,
        )
        self.assertLess(
            heavier_target_factor,
            1.0,
        )
        self.assertGreater(
            heavier_target_factor,
            0.25,
        )
        self.assertAlmostEqual(
            heavier_attacker_factor
            * heavier_target_factor,
            1.0,
        )

    def test_calculates_contact_pressure_without_assigning_injury(
        self,
    ) -> None:
        from simulation.trauma import (
            calculate_trauma_pressure,
            create_trauma_event,
        )

        trauma = create_trauma_event(
            source_stage="attack",
            contact_succeeded=True,
            attack_method_id="bite",
            contact_power=6.0,
            attacker_mass_kg=16.0,
            opposing_defense=4.0,
            target_mass_kg=1.0,
            contact_quality=0.5,
        )

        pressure = calculate_trauma_pressure(trauma)

        self.assertEqual(
            pressure.attack_method_id,
            "bite",
        )
        self.assertEqual(
            pressure.relative_mass_factor,
            2.0,
        )
        self.assertEqual(
            pressure.contact_pressure,
            6.0,
        )
        self.assertEqual(
            pressure.opposing_defense,
            4.0,
        )

    def test_calculates_residual_trauma_after_defense(
        self,
    ) -> None:
        from simulation.trauma import (
            TraumaPressure,
            calculate_residual_trauma,
        )

        partially_mitigated = TraumaPressure(
            attack_method_id="bite",
            relative_mass_factor=2.0,
            contact_pressure=6.0,
            opposing_defense=4.0,
        )
        fully_mitigated = TraumaPressure(
            attack_method_id="bite",
            relative_mass_factor=2.0,
            contact_pressure=6.0,
            opposing_defense=8.0,
        )

        self.assertEqual(
            calculate_residual_trauma(partially_mitigated),
            2.0,
        )
        self.assertEqual(
            calculate_residual_trauma(fully_mitigated),
            0.0,
        )

    def test_classifies_residual_trauma_by_severity(
        self,
    ) -> None:
        from simulation.injuries import (
            InjurySeverity,
            classify_injury_severity,
        )

        expected_severities = (
            (0.0, None),
            (0.5, InjurySeverity.MINOR),
            (2.0, InjurySeverity.MODERATE),
            (4.0, InjurySeverity.MAJOR),
            (7.0, InjurySeverity.CRITICAL),
        )

        for residual_trauma, expected_severity in expected_severities:
            with self.subTest(residual_trauma=residual_trauma):
                self.assertIs(
                    classify_injury_severity(residual_trauma),
                    expected_severity,
                )


if __name__ == "__main__":
    unittest.main()