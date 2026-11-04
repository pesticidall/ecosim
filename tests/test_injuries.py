import unittest


class TestInjuries(unittest.TestCase):
    def test_injury_resolution_applies_method_and_trait_modifiers(self) -> None:
        from simulation.injuries import (
            InjurySeverity,
            resolve_injury_from_trauma,
        )
        from simulation.trauma import create_trauma_event

        trauma = create_trauma_event(
            source_stage="attack",
            contact_succeeded=True,
            attack_method_id="test_method",
            contact_power=8.0,
            attacker_mass_kg=10.0,
            opposing_defense=3.0,
            target_mass_kg=10.0,
            contact_quality=0.5,
        )
        method_definition = {
            "entity_type": "attack_method",
            "id": "test_method",
            "name": "Test Method",
            "description": "Verifies injury resolution modifiers.",
            "trauma_modifier": 1.5,
            "trait_effect_target": "grapple_effectiveness",
        }
        trait_definition = {
            "entity_type": "trait",
            "id": "test_trait",
            "name": "Test Trait",
            "description": "Improves grappling effectiveness.",
            "effects": [
                {"target": "grapple_effectiveness", "modifier": 1.2},
            ],
        }

        baseline_injury = resolve_injury_from_trauma(trauma)
        self.assertIsNotNone(baseline_injury)
        self.assertIs(baseline_injury.severity, InjurySeverity.MINOR)

        method_injury = resolve_injury_from_trauma(
            trauma,
            attack_method_definition=method_definition,
        )
        self.assertIsNotNone(method_injury)
        self.assertIs(method_injury.severity, InjurySeverity.MODERATE)

        injury = resolve_injury_from_trauma(
            trauma,
            attack_method_definition=method_definition,
            trait_ids=("test_trait",),
            trait_definitions=(trait_definition,),
        )

        self.assertIsNotNone(injury)
        self.assertIs(injury.severity, InjurySeverity.MAJOR)
        self.assertEqual(injury.source_stage, "attack")
        self.assertEqual(injury.power_modifier, 0.5)
        self.assertEqual(injury.mobility_modifier, 0.5)


    def test_injury_records_severity_source_and_condition_effects(
        self,
    ) -> None:
        from simulation.injuries import (
            Injury,
            InjurySeverity,
        )

        injury = Injury(
            severity=InjurySeverity.MAJOR,
            source_stage="counterattack",
            power_modifier=0.6,
            mobility_modifier=0.75,
        )

        self.assertIs(
            injury.severity,
            InjurySeverity.MAJOR,
        )
        self.assertEqual(
            injury.source_stage,
            "counterattack",
        )
        self.assertEqual(
            injury.power_modifier,
            0.6,
        )
        self.assertEqual(
            injury.mobility_modifier,
            0.75,
        )

    def test_defines_four_ordered_injury_severity_labels(
        self,
    ) -> None:
        from simulation.injuries import InjurySeverity

        self.assertEqual(
            [
                severity.value
                for severity in InjurySeverity
            ],
            [
                "minor",
                "moderate",
                "major",
                "critical",
            ],
        )

    def test_combines_injury_condition_modifiers(
        self,
    ) -> None:
        from simulation.injuries import (
            Injury,
            InjurySeverity,
            calculate_injury_modifiers,
        )

        injuries = [
            Injury(
                severity=InjurySeverity.MINOR,
                source_stage="attack",
                power_modifier=0.9,
                mobility_modifier=0.85,
            ),
            Injury(
                severity=InjurySeverity.MAJOR,
                source_stage="counterattack",
                power_modifier=0.8,
                mobility_modifier=0.7,
            ),
        ]

        modifiers = calculate_injury_modifiers(injuries)

        self.assertAlmostEqual(
            modifiers.power_modifier,
            0.72,
        )
        self.assertAlmostEqual(
            modifiers.mobility_modifier,
            0.595,
        )

    def test_creates_injury_from_residual_trauma(
        self,
    ) -> None:
        from simulation.injuries import (
            InjurySeverity,
            create_injury_from_trauma,
        )

        no_injury = create_injury_from_trauma(
            source_stage="attack",
            residual_trauma=0.0,
        )
        moderate_injury = create_injury_from_trauma(
            source_stage="counterattack",
            residual_trauma=3.0,
        )

        self.assertIsNone(no_injury)
        self.assertIsNotNone(moderate_injury)
        self.assertIs(
            moderate_injury.severity,
            InjurySeverity.MODERATE,
        )
        self.assertEqual(
            moderate_injury.source_stage,
            "counterattack",
        )
        self.assertEqual(
            moderate_injury.power_modifier,
            0.75,
        )
        self.assertEqual(
            moderate_injury.mobility_modifier,
            0.75,
        )

    def test_resolves_injury_from_complete_trauma_event(
        self,
    ) -> None:
        from simulation.injuries import (
            InjurySeverity,
            resolve_injury_from_trauma,
        )
        from simulation.trauma import create_trauma_event

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

        injury = resolve_injury_from_trauma(trauma)

        self.assertIsNotNone(injury)
        self.assertIs(
            injury.severity,
            InjurySeverity.MODERATE,
        )
        self.assertEqual(
            injury.source_stage,
            "attack",
        )
        self.assertEqual(
            injury.power_modifier,
            0.75,
        )
        self.assertEqual(
            injury.mobility_modifier,
            0.75,
        )


if __name__ == "__main__":
    unittest.main()
