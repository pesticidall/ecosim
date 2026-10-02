import unittest


class TestTraits(unittest.TestCase):
    def test_resolves_animal_effect_from_inherited_traits(
        self,
    ) -> None:
        from simulation.traits import resolve_animal_trait_effect

        animal_definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "taxon_id": "lepus",
        }
        taxon_definitions = [
            {
                "entity_type": "taxon",
                "id": "animalia",
                "name": "Animalia",
                "rank": "kingdom",
                "parent_taxon_id": None,
            },
            {
                "entity_type": "taxon",
                "id": "lepus",
                "name": "Lepus",
                "rank": "genus",
                "parent_taxon_id": "animalia",
                "default_trait_ids": [
                    "powerful_hindlimbs",
                ],
            },
        ]
        trait_definitions = [
            {
                "entity_type": "trait",
                "id": "powerful_hindlimbs",
                "name": "Powerful Hind Limbs",
                "effects": [
                    {
                        "target": "escape_mobility",
                        "modifier": 1.15,
                    },
                ],
            },
        ]

        effect = resolve_animal_trait_effect(
            animal_definition,
            taxon_definitions,
            trait_definitions,
            "escape_mobility",
        )

        self.assertEqual(effect.modifier, 1.15)
        self.assertEqual(
            effect.contributing_trait_ids,
            ("powerful_hindlimbs",),
        )

    def test_resolves_explicit_trait_effect_for_target(
        self,
    ) -> None:
        from simulation.traits import resolve_trait_effect

        trait_definitions = [
            {
                "entity_type": "trait",
                "id": "powerful_hindlimbs",
                "name": "Powerful Hind Limbs",
                "effects": [
                    {
                        "target": "escape_mobility",
                        "modifier": 1.15,
                    },
                    {
                        "target": "counterattack_power",
                        "modifier": 1.1,
                    },
                ],
            },
        ]

        effect = resolve_trait_effect(
            ["powerful_hindlimbs"],
            trait_definitions,
            "escape_mobility",
        )
        unrelated_effect = resolve_trait_effect(
            ["powerful_hindlimbs"],
            trait_definitions,
            "stealth",
        )

        self.assertEqual(effect.target, "escape_mobility")
        self.assertEqual(effect.modifier, 1.15)
        self.assertEqual(
            effect.contributing_trait_ids,
            ("powerful_hindlimbs",),
        )
        self.assertEqual(unrelated_effect.modifier, 1.0)
        self.assertEqual(
            unrelated_effect.contributing_trait_ids,
            (),
        )

    def test_resolves_trait_inherited_from_assigned_taxon(self) -> None:
        from simulation.traits import resolve_animal_trait_ids

        animal_definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "taxon_id": "mammalia",
        }
        taxon_definitions = [
            {
                "entity_type": "taxon",
                "id": "animalia",
                "name": "Animalia",
                "rank": "kingdom",
                "parent_taxon_id": None,
            },
            {
                "entity_type": "taxon",
                "id": "mammalia",
                "name": "Mammalia",
                "rank": "class",
                "parent_taxon_id": "animalia",
                "default_trait_ids": [
                    "powerful_hindlimbs",
                ],
            },
        ]

        self.assertEqual(
            resolve_animal_trait_ids(
                animal_definition,
                taxon_definitions,
            ),
            ["powerful_hindlimbs"],
        )

    def test_resolves_trait_added_by_animal(self) -> None:
        from simulation.traits import resolve_animal_trait_ids

        animal_definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "taxon_id": "lepus",
            "trait_ids": [
                "powerful_hindlimbs",
            ],
        }
        taxon_definitions = [
            {
                "entity_type": "taxon",
                "id": "animalia",
                "name": "Animalia",
                "rank": "kingdom",
                "parent_taxon_id": None,
            },
            {
                "entity_type": "taxon",
                "id": "lepus",
                "name": "Lepus",
                "rank": "genus",
                "parent_taxon_id": "animalia",
            },
        ]

        self.assertEqual(
            resolve_animal_trait_ids(
                animal_definition,
                taxon_definitions,
            ),
            ["powerful_hindlimbs"],
        )

    def test_excludes_inherited_trait_from_animal(self) -> None:
        from simulation.traits import resolve_animal_trait_ids

        animal_definition = {
            "entity_type": "animal",
            "id": "aardwolf",
            "name": "Aardwolf",
            "taxon_id": "hyaenidae",
            "excluded_trait_ids": [
                "bone_crushing_jaws",
            ],
        }
        taxon_definitions = [
            {
                "entity_type": "taxon",
                "id": "animalia",
                "name": "Animalia",
                "rank": "kingdom",
                "parent_taxon_id": None,
            },
            {
                "entity_type": "taxon",
                "id": "hyaenidae",
                "name": "Hyaenidae",
                "rank": "family",
                "parent_taxon_id": "animalia",
                "default_trait_ids": [
                    "powerful_jaws",
                    "bone_crushing_jaws",
                ],
            },
        ]

        self.assertEqual(
            resolve_animal_trait_ids(
                animal_definition,
                taxon_definitions,
            ),
            ["powerful_jaws"],
        )

    def test_deduplicates_traits_inherited_from_multiple_taxa(self) -> None:
        from simulation.traits import resolve_animal_trait_ids

        animal_definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "taxon_id": "mammalia",
        }
        taxon_definitions = [
            {
                "entity_type": "taxon",
                "id": "animalia",
                "name": "Animalia",
                "rank": "kingdom",
                "parent_taxon_id": None,
                "default_trait_ids": [
                    "endothermic",
                ],
            },
            {
                "entity_type": "taxon",
                "id": "mammalia",
                "name": "Mammalia",
                "rank": "class",
                "parent_taxon_id": "animalia",
                "default_trait_ids": [
                    "endothermic",
                    "live_birth",
                ],
            },
        ]

        self.assertEqual(
            resolve_animal_trait_ids(
                animal_definition,
                taxon_definitions,
            ),
            [
                "endothermic",
                "live_birth",
            ],
        )


if __name__ == "__main__":
    unittest.main()
