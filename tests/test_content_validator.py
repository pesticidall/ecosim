import unittest
from pathlib import Path

from core.content_validator import validate_entity_definition


class TestValidateEntityDefinition(unittest.TestCase):
    def test_raises_error_when_required_field_is_missing(self) -> None:
        definition = {
            "entity_type": "producer",
            "name": "Grass",
        }
        source_path = Path("content/producers/grass.json")
        with self.assertRaisesRegex(
            ValueError,
            r"grass\.json.*id",
        ):
            validate_entity_definition(definition, source_path)

    def test_accepts_valid_identity_fields(self) -> None:
        definition = {
            "entity_type": "producer",
            "id": "silverleaf_shrub",
            "name": "Silverleaf Shrub",
            "production": [
                {
                    "resource_id": "test_resource",
                    "amount_per_producer_per_day": 1.0,
                }
            ],
        }
        source_path = Path("content/producers/silverleaf_shrub.json")
        validate_entity_definition(definition, source_path)

    def test_raises_error_when_entity_field_is_not_string(self) -> None:
        definition = {
            "entity_type": "producer",
            "id": 42,
            "name": "Grass",
        }
        source_path = Path("content/producers/grass.json")
        with self.assertRaisesRegex(
            TypeError,
            r"id.*must be a string",
        ):
            validate_entity_definition(definition, source_path)

    def test_raises_error_when_entity_field_is_empty(self) -> None:
        definition = {
            "entity_type": "producer",
            "id": "grass",
            "name": "",
        }
        source_path = Path("content/producers/grass.json")
        with self.assertRaisesRegex(
            ValueError,
            r"name.*must not be empty",
        ):
            validate_entity_definition(definition, source_path)

    def test_raises_error_for_unsupported_entity_type(self) -> None:
        definition = {
            "entity_type": "plant",
            "id": "grass",
            "name": "Grass",
        }
        source_path = Path("content/producers/grass.json")
        with self.assertRaisesRegex(
            ValueError,
            r"unsupported entity type.*plant",
        ):
            validate_entity_definition(definition, source_path)

    def test_accepts_taxon_definition(self) -> None:
        definition = {
            "entity_type": "taxon",
            "id": "mammalia",
            "name": "Mammalia",
            "rank": "class",
            "parent_taxon_id": "chordata",
        }

        validate_entity_definition(
            definition,
            Path("content/taxa/mammalia.json"),
        )

    def test_rejects_taxon_missing_taxonomy_fields(self) -> None:
        definition = {
            "entity_type": "taxon",
            "id": "mammalia",
            "name": "Mammalia",
        }
        source_path = Path(
            "content/taxa/mammalia.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            (
                r"mammalia\.json"
                r".*rank"
                r".*parent_taxon_id"
            ),
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_nonstring_taxon_rank(self) -> None:
        definition = {
            "entity_type": "taxon",
            "id": "mammalia",
            "name": "Mammalia",
            "rank": 42,
            "parent_taxon_id": "chordata",
        }
        source_path = Path(
            "content/taxa/mammalia.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"rank.*must be a string",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_empty_taxon_rank(self) -> None:
        definition = {
            "entity_type": "taxon",
            "id": "mammalia",
            "name": "Mammalia",
            "rank": "   ",
            "parent_taxon_id": "chordata",
        }
        source_path = Path(
            "content/taxa/mammalia.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"rank.*must not be empty",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_unsupported_taxon_rank(self) -> None:
        definition = {
            "entity_type": "taxon",
            "id": "mammalia",
            "name": "Mammalia",
            "rank": "color",
            "parent_taxon_id": "chordata",
        }
        source_path = Path(
            "content/taxa/mammalia.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"unsupported taxonomic rank.*color",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_invalid_parent_taxon_id_type(self) -> None:
        definition = {
            "entity_type": "taxon",
            "id": "mammalia",
            "name": "Mammalia",
            "rank": "class",
            "parent_taxon_id": 42,
        }
        source_path = Path(
            "content/taxa/mammalia.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"parent_taxon_id.*must be a string or null",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_empty_parent_taxon_id(self) -> None:
        definition = {
            "entity_type": "taxon",
            "id": "mammalia",
            "name": "Mammalia",
            "rank": "class",
            "parent_taxon_id": "   ",
        }
        source_path = Path(
            "content/taxa/mammalia.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"parent_taxon_id.*must not be empty",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_invalid_parent_taxon_id_format(self) -> None:
        definition = {
            "entity_type": "taxon",
            "id": "mammalia",
            "name": "Mammalia",
            "rank": "class",
            "parent_taxon_id": "Chordata",
        }
        source_path = Path(
            "content/taxa/mammalia.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"parent_taxon_id.*lowercase snake_case",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_accepts_null_parent_for_root_taxon(self) -> None:
        definition = {
            "entity_type": "taxon",
            "id": "animalia",
            "name": "Animalia",
            "rank": "kingdom",
            "parent_taxon_id": None,
        }

        validate_entity_definition(
            definition,
            Path("content/taxa/animalia.json"),
        )

    def test_rejects_taxon_as_its_own_parent(self) -> None:
        definition = {
            "entity_type": "taxon",
            "id": "mammalia",
            "name": "Mammalia",
            "rank": "class",
            "parent_taxon_id": "mammalia",
        }
        source_path = Path(
            "content/taxa/mammalia.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"parent_taxon_id.*must not reference itself",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_raises_error_for_invalid_entity_id(self) -> None:
        definition = {
            "entity_type": "producer",
            "id": "Silverleaf Shrub",
            "name": "Silverleaf Shrub",
            "production": [
                {
                    "resource_id": "test_resource",
                    "amount_per_producer_per_day": 1.0,
                }
            ],
        }
        source_path = Path("content/producers/silverleaf_shrub.json")
        with self.assertRaisesRegex(
            ValueError,
            r"id.*lowercase snake_case",
        ):
            validate_entity_definition(definition, source_path)

    def test_raises_error_when_resource_field_is_missing(self) -> None:
        definition = {
            "entity_type": "resource",
            "id": "grass_forage",
            "name": "Grass",
            "unit": "kg",
        }
        source_path = Path(
            "content/resources/grass_forage.json"
        )
        with self.assertRaisesRegex(
            ValueError,
            r"grass_forage\.json.*quantity_type",
        ):
            validate_entity_definition(definition, source_path)

    def test_raises_error_when_resource_field_is_not_string(self) -> None:
        definition = {
            "entity_type": "resource",
            "id": "grass_forage",
            "name": "Grass",
            "quantity_type": 42,
            "unit": "kg",
        }
        source_path = Path(
            "content/resources/grass_forage.json"
        )
        with self.assertRaisesRegex(
            TypeError,
            r"quantity_type.*must be a string",
        ):
            validate_entity_definition(definition, source_path)

    def test_raises_error_when_resource_field_is_empty(self) -> None:
        definition = {
            "entity_type": "resource",
            "id": "grass_forage",
            "name": "Grass",
            "quantity_type": "biomass",
            "unit": "",
        }
        source_path = Path(
            "content/resource/grass_forage.json"
        )
        with self.assertRaisesRegex(
            ValueError,
            r"unit.*must not be empty"
        ):
            validate_entity_definition(definition, source_path)

    def test_raises_error_for_unsupported_resource_quantity_type(
            self,
    ) -> None:
        definition = {
            "entity_type": "resource",
            "id": "grass_forage",
            "name": "Grass",
            "quantity_type": "volume",
            "unit": "liters",
        }
        source_path = Path(
            "content/resources/grass_forage.json"
        )
        with self.assertRaisesRegex(
            ValueError,
            r"unsupported quantity type.*volume",
        ):
            validate_entity_definition(definition, source_path)

    def test_raises_error_for_unsupported_resource_unit(self) -> None:
        definition = {
            "entity_type": "resource",
            "id": "grass_forage",
            "name": "Grass",
            "quantity_type": "biomass",
            "unit": "grams",
        }
        source_path = Path(
            "content/resources/grass_forage.json"
        )
        with self.assertRaisesRegex(
            ValueError,
            r"unsupported unit.*grams.*biomass",
        ):
            validate_entity_definition(definition, source_path)

    def test_raises_error_when_production_is_missing(self) -> None:
        definition = {
            "entity_type": "producer",
            "id": "redgrass",
            "name": "Redgrass",
        }
        source_path = Path(
            "content/producers/redgrass.json"
        )
        with self.assertRaisesRegex(
            ValueError,
            r"redgrass\.json.*production",
        ):
            validate_entity_definition(
                definition,
                source_path
            )

    def test_raises_error_when_production_is_not_list(self) -> None:
        definition = {
            "entity_type": "producer",
            "id": "redgrass",
            "name": "Redgrass",
            "production": "grass_forage",
        }
        source_path = Path(
            "content/producers/redgrass.json"
        )
        with self.assertRaisesRegex(
            TypeError,
            r"production.*must be a list",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_raises_error_when_production_is_empty(self) -> None:
        definition = {
            "entity_type": "producer",
            "id": "redgrass",
            "name": "Redgrass",
            "production": [],
        }
        source_path = Path(
            "content/producers/redgrass.json"
        )
        with self.assertRaisesRegex(
            ValueError,
            r"production.*must not be empty",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_raises_error_when_production_entry_is_not_object(self) -> None:
        definition = {
            "entity_type": "producer",
            "id": "redgrass",
            "name": "Redgrass",
            "production": [
                "grass_forage",
            ],
        }
        source_path = Path(
            "content/producers/redgrass.json"
        )
        with self.assertRaisesRegex(
            TypeError,
            r"production entry.*must be an object",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_raises_error_when_production_entry_field_is_missing(self) -> None:
        definition = {
            "entity_type": "producer",
            "id": "redgrass",
            "name": "Redgrass",
            "production": [
                {
                    "resource_id": "grass_forage",
                }
            ],
        }
        source_path = Path(
            "content/producers/redgrass.json"
        )
        with self.assertRaisesRegex(
            ValueError,
            r"production entry 0.*amount_per_producer_per_day",
        ):
            validate_entity_definition(
                definition,
                source_path
            )

    def test_raises_error_when_production_resource_id_is_not_string(self) -> None:
        definition = {
            "entity_type": "producer",
            "id": "redgrass",
            "name": "Redgrass",
            "production": [
                {
                    "resource_id": 42,
                    "amount_per_producer_per_day": 0.25 / 31,
                }
            ],
        }
        source_path = Path(
            "content/producers/redgrass.json"
        )
        with self.assertRaisesRegex(
            TypeError,
            r"resource_id.*must be a string",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_raises_error_when_production_resource_id_is_empty(self) -> None:
        definition = {
            "entity_type": "producer",
            "id": "redgrass",
            "name": "Redgrass",
            "production": [
                {
                    "resource_id": "    ",
                    "amount_per_producer_per_day": 0.25 / 31,
                }
            ],
        }
        source_path = Path(
            "content/producers/redgrass.json"
        )
        with self.assertRaisesRegex(
            ValueError,
            r"resource_id.*must not be empty",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )
    def test_raises_error_for_invalid_production_resource_id(self) -> None:
        definition = {
            "entity_type": "producer",
            "id": "redgrass",
            "name": "Redgrass",
            "production": [
                {
                    "resource_id": "Grass",
                    "amount_per_producer_per_day": 0.25 / 31,
                }
            ],
        }
        source_path = Path(
            "content/producers/redgrass.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"resource_id.*lowercase snake_case",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )
    def test_raises_error_when_production_amount_is_not_number(self) -> None:
        definition = {
            "entity_type": "producer",
            "id": "redgrass",
            "name": "Redgrass",
            "production": [
                {
                    "resource_id": "grass_forage",
                    "amount_per_producer_per_day": "high",
                }
            ],
        }
        source_path = Path(
            "content/producers/redgrass.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"amount_per_producer_per_day.*must be a number",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )
    def test_raises_error_when_production_amount_is_boolean(self) -> None:
        definition = {
            "entity_type": "producer",
            "id": "redgrass",
            "name": "Redgrass",
            "production": [
                {
                    "resource_id": "grass_forage",
                    "amount_per_producer_per_day": True,
                }
            ],
        }
        source_path = Path(
            "content/producers/redgrass.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"amount_per_producer_per_day.*must be a number",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )
    def test_raises_error_when_production_amount_is_not_positive(self) -> None:
        for invalid_amount in (0, -0.25):
            with self.subTest(
                production_amount=invalid_amount,
            ):
                definition = {
                    "entity_type": "producer",
                    "id": "redgrass",
                    "name": "Redgrass",
                    "production": [
                        {
                            "resource_id": "grass_forage",
                            "amount_per_producer_per_day": invalid_amount,
                        }
                    ],
                }
                source_path = Path(
                    "content/producers/redgrass.json"
                )

                with self.assertRaisesRegex(
                    ValueError,
                    r"amount_per_producer_per_day.*greater than zero",
                ):
                    validate_entity_definition(
                        definition,
                        source_path,
                    )

    def test_validates_every_production_entry(self) -> None:
        definition = {
            "entity_type": "producer",
            "id": "redgrass",
            "name": "Redgrass",
            "production": [
                {
                    "resource_id": 42,
                    "amount_per_producer_per_day": 0.25 / 31,
                },
                {
                    "resource_id": "grass_forage",
                    "amount_per_producer_per_day": 0.25 / 31,
                },
            ],
        }
        source_path = Path(
            "content/producers/redgrass.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"resource_id.*must be a string",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_nonstring_animal_taxon_id(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "taxon_id": 42,
            "diet_type": "herbivore",
            "activity_pattern": "nocturnal",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"taxon_id.*must be a string",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_empty_animal_taxon_id(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "taxon_id": "   ",
            "diet_type": "herbivore",
            "activity_pattern": "nocturnal",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"taxon_id.*must not be empty",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_invalid_animal_taxon_id_format(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "taxon_id": "Lepus",
            "diet_type": "herbivore",
            "activity_pattern": "nocturnal",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"taxon_id.*lowercase snake_case",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_accepts_trait_definition(self) -> None:
        definition = {
            "entity_type": "trait",
            "id": "powerful_hindlimbs",
            "name": "Powerful Hindlimbs",
            "description": (
                "Strong hindlimbs improve rapid acceleration "
                "during escape attempts."
            ),
        }

        validate_entity_definition(
            definition,
            Path("content/traits/powerful_hindlimbs.json"),
        )

    def test_rejects_trait_missing_description(self) -> None:
        definition = {
            "entity_type": "trait",
            "id": "powerful_hindlimbs",
            "name": "Powerful Hindlimbs",
        }
        source_path = Path(
            "content/traits/powerful_hindlimbs.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"powerful_hindlimbs\.json.*description",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_nonstring_trait_description(self) -> None:
        definition = {
            "entity_type": "trait",
            "id": "powerful_hindlimbs",
            "name": "Powerful Hindlimbs",
            "description": 42,
        }
        source_path = Path(
            "content/traits/powerful_hindlimbs.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"description.*must be a string",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_empty_trait_description(self) -> None:
        definition = {
            "entity_type": "trait",
            "id": "powerful_hindlimbs",
            "name": "Powerful Hindlimbs",
            "description": "   ",
        }
        source_path = Path(
            "content/traits/powerful_hindlimbs.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"description.*must not be empty",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_nonlist_trait_tags(self) -> None:
        definition = {
            "entity_type": "trait",
            "id": "powerful_hindlimbs",
            "name": "Powerful Hind Limbs",
            "description": "Strong rear limbs.",
            "tags": "locomotion",
        }
        source_path = Path(
            "content/traits/powerful_hindlimbs.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"tags.*must be a list",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_nonstring_trait_tag(self) -> None:
        definition = {
            "entity_type": "trait",
            "id": "powerful_hindlimbs",
            "name": "Powerful Hind Limbs",
            "description": "Strong rear limbs.",
            "tags": [42],
        }
        source_path = Path(
            "content/traits/powerful_hindlimbs.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"tags.*entry 0.*must be a string",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_empty_trait_tag(self) -> None:
        definition = {
            "entity_type": "trait",
            "id": "powerful_hindlimbs",
            "name": "Powerful Hind Limbs",
            "description": "Strong rear limbs.",
            "tags": ["   "],
        }
        source_path = Path(
            "content/traits/powerful_hindlimbs.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"tags.*entry 0.*must not be empty",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_invalid_trait_tag_format(self) -> None:
        definition = {
            "entity_type": "trait",
            "id": "powerful_hindlimbs",
            "name": "Powerful Hind Limbs",
            "description": "Strong rear limbs.",
            "tags": [
                "EscapeBehavior",
            ],
        }
        source_path = Path(
            "content/traits/powerful_hindlimbs.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"tags.*entry 0.*lowercase snake_case",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_duplicate_trait_tags(self) -> None:
        definition = {
            "entity_type": "trait",
            "id": "powerful_hindlimbs",
            "name": "Powerful Hind Limbs",
            "description": "Strong rear limbs.",
            "tags": [
                "escape",
                "escape",
            ],
        }
        source_path = Path(
            "content/traits/powerful_hindlimbs.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"tags.*duplicate.*escape",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_accepts_explicit_trait_effects(self) -> None:
        definition = {
            "entity_type": "trait",
            "id": "powerful_hindlimbs",
            "name": "Powerful Hind Limbs",
            "description": "Strong rear limbs.",
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
        }

        validate_entity_definition(
            definition,
            Path(
                "content/traits/"
                "powerful_hindlimbs.json"
            ),
        )

    def test_rejects_invalid_trait_effect(self) -> None:
        invalid_cases = (
            (
                [
                    {
                        "target": "universal_power",
                        "modifier": 1.1,
                    },
                ],
                ValueError,
                r"unsupported effect target.*universal_power",
            ),
            (
                [
                    {
                        "target": "escape_mobility",
                        "modifier": "high",
                    },
                ],
                TypeError,
                r"escape_mobility.*must be a number",
            ),
            (
                [
                    {
                        "target": "escape_mobility",
                        "modifier": float("nan"),
                    },
                ],
                ValueError,
                r"escape_mobility.*must be finite",
            ),
            (
                [
                    {
                        "target": "escape_mobility",
                        "modifier": 1.1,
                    },
                    {
                        "target": "escape_mobility",
                        "modifier": 1.2,
                    },
                ],
                ValueError,
                r"duplicate target.*escape_mobility",
            ),
        )

        for effects, error_type, message_pattern in invalid_cases:
            with self.subTest(effects=effects):
                definition = {
                    "entity_type": "trait",
                    "id": "test_trait",
                    "name": "Test Trait",
                    "description": "A test trait.",
                    "effects": effects,
                }

                with self.assertRaisesRegex(
                    error_type,
                    message_pattern,
                ):
                    validate_entity_definition(
                        definition,
                        Path(
                            "content/traits/"
                            "test_trait.json"
                        ),
                    )

    def test_rejects_nonlist_taxon_default_trait_ids(self) -> None:
        definition = {
            "entity_type": "taxon",
            "id": "mammalia",
            "name": "Mammalia",
            "rank": "class",
            "parent_taxon_id": "chordata",
            "default_trait_ids": "endothermic",
        }
        source_path = Path(
            "content/taxa/mammalia.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"default_trait_ids.*must be a list",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_nonstring_taxon_default_trait_id(self) -> None:
        definition = {
            "entity_type": "taxon",
            "id": "mammalia",
            "name": "Mammalia",
            "rank": "class",
            "parent_taxon_id": "chordata",
            "default_trait_ids": [42],
        }
        source_path = Path(
            "content/taxa/mammalia.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"default_trait_ids.*entry 0.*must be a string",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_empty_taxon_default_trait_id(self) -> None:
        definition = {
            "entity_type": "taxon",
            "id": "mammalia",
            "name": "Mammalia",
            "rank": "class",
            "parent_taxon_id": "chordata",
            "default_trait_ids": ["   "],
        }
        source_path = Path(
            "content/taxa/mammalia.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"default_trait_ids.*entry 0.*must not be empty",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_invalid_taxon_default_trait_id_format(self) -> None:
        definition = {
            "entity_type": "taxon",
            "id": "mammalia",
            "name": "Mammalia",
            "rank": "class",
            "parent_taxon_id": "chordata",
            "default_trait_ids": ["Endothermic"],
        }
        source_path = Path(
            "content/taxa/mammalia.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"default_trait_ids.*entry 0.*lowercase snake_case",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_duplicate_taxon_default_trait_ids(self) -> None:
        definition = {
            "entity_type": "taxon",
            "id": "mammalia",
            "name": "Mammalia",
            "rank": "class",
            "parent_taxon_id": "chordata",
            "default_trait_ids": [
                "endothermic",
                "endothermic",
            ],
        }
        source_path = Path(
            "content/taxa/mammalia.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"default_trait_ids.*duplicate.*endothermic",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_nonlist_animal_trait_ids(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "taxon_id": "lepus",
            "trait_ids": "powerful_hindlimbs",
            "diet_type": "herbivore",
            "activity_pattern": "nocturnal",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"trait_ids.*must be a list",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_nonstring_animal_trait_id(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "taxon_id": "lepus",
            "trait_ids": [42],
            "diet_type": "herbivore",
            "activity_pattern": "nocturnal",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"trait_ids.*entry 0.*must be a string",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_empty_animal_trait_id(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "taxon_id": "lepus",
            "trait_ids": ["   "],
            "diet_type": "herbivore",
            "activity_pattern": "nocturnal",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"trait_ids.*entry 0.*must not be empty",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_invalid_animal_trait_id_format(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "taxon_id": "lepus",
            "trait_ids": ["PowerfulHindlimbs"],
            "diet_type": "herbivore",
            "activity_pattern": "nocturnal",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"trait_ids.*entry 0.*lowercase snake_case",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_duplicate_animal_trait_ids(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "taxon_id": "lepus",
            "trait_ids": [
                "powerful_hindlimbs",
                "powerful_hindlimbs",
            ],
            "diet_type": "herbivore",
            "activity_pattern": "nocturnal",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"trait_ids.*duplicate.*powerful_hindlimbs",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_nonlist_animal_excluded_trait_ids(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "taxon_id": "lepus",
            "excluded_trait_ids": "aquatic",
            "diet_type": "herbivore",
            "activity_pattern": "nocturnal",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"excluded_trait_ids.*must be a list",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_nonstring_animal_excluded_trait_id(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "taxon_id": "lepus",
            "excluded_trait_ids": [42],
            "diet_type": "herbivore",
            "activity_pattern": "nocturnal",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"excluded_trait_ids.*entry 0.*must be a string",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_empty_animal_excluded_trait_id(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "taxon_id": "lepus",
            "excluded_trait_ids": ["   "],
            "diet_type": "herbivore",
            "activity_pattern": "nocturnal",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"excluded_trait_ids.*entry 0.*must not be empty",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_invalid_animal_excluded_trait_id_format(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "taxon_id": "lepus",
            "excluded_trait_ids": ["Aquatic"],
            "diet_type": "herbivore",
            "activity_pattern": "nocturnal",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            (
                r"excluded_trait_ids.*entry 0.*"
                r"lowercase snake_case"
            ),
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_duplicate_animal_excluded_trait_ids(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "taxon_id": "lepus",
            "excluded_trait_ids": [
                "aquatic",
                "aquatic",
            ],
            "diet_type": "herbivore",
            "activity_pattern": "nocturnal",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"excluded_trait_ids.*duplicate.*aquatic",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_trait_id_that_is_also_excluded(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "taxon_id": "lepus",
            "trait_ids": ["powerful_hindlimbs"],
            "excluded_trait_ids": ["powerful_hindlimbs"],
            "diet_type": "herbivore",
            "activity_pattern": "nocturnal",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            (
                r"powerful_hindlimbs.*both trait_ids and "
                r"excluded_trait_ids"
            ),
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_nonobject_animal_statistics(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "taxon_id": "lepus",
            "statistics": [],
            "diet_type": "herbivore",
            "activity_pattern": "nocturnal",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"statistics.*must be an object",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_missing_required_animal_statistic(self) -> None:
        valid_statistics = {
            "power": 1.0,
            "defense": 1.0,
            "health": 1.0,
            "mobility": 1.0,
            "perception": 1.0,
            "stealth": 1.0,
            "intelligence": 1.0,
        }

        for missing_field in valid_statistics:
            with self.subTest(missing_field=missing_field):
                statistics = dict(valid_statistics)
                del statistics[missing_field]
                definition = {
                    "entity_type": "animal",
                    "id": "scrub_hare",
                    "name": "Scrub Hare",
                    "taxon_id": "lepus",
                    "statistics": statistics,
                    "diet_type": "herbivore",
                    "activity_pattern": "nocturnal",
                    "food_requirement_per_animal_per_cycle": 0.5,
                    "birth_rate_per_animal_per_cycle": 0.12,
                    "diet": [
                        {
                            "resource_id": "grass_forage",
                            "preference": 1.0,
                        },
                    ],
                }
                source_path = Path(
                    "content/animals/scrub_hare.json"
                )

                with self.assertRaisesRegex(
                    ValueError,
                    (
                        r"statistics.*missing required.*"
                        rf"{missing_field}"
                    ),
                ):
                    validate_entity_definition(
                        definition,
                        source_path,
                    )

    def test_rejects_nonnumeric_animal_statistic(self) -> None:
        valid_statistics = {
            "power": 1.0,
            "defense": 1.0,
            "health": 1.0,
            "mobility": 1.0,
            "perception": 1.0,
            "stealth": 1.0,
            "intelligence": 1.0,
        }

        for statistic_field in valid_statistics:
            with self.subTest(
                statistic_field=statistic_field,
            ):
                statistics = dict(valid_statistics)
                statistics[statistic_field] = "high"
                definition = {
                    "entity_type": "animal",
                    "id": "scrub_hare",
                    "name": "Scrub Hare",
                    "taxon_id": "lepus",
                    "statistics": statistics,
                    "diet_type": "herbivore",
                    "activity_pattern": "nocturnal",
                    "food_requirement_per_animal_per_cycle": 0.5,
                    "birth_rate_per_animal_per_cycle": 0.12,
                    "diet": [
                        {
                            "resource_id": "grass_forage",
                            "preference": 1.0,
                        },
                    ],
                }
                source_path = Path(
                    "content/animals/scrub_hare.json"
                )

                with self.assertRaisesRegex(
                    TypeError,
                    (
                        rf"statistics.*{statistic_field}.*"
                        r"must be a number"
                    ),
                ):
                    validate_entity_definition(
                        definition,
                        source_path,
                    )

    def test_rejects_boolean_animal_statistic(self) -> None:
        valid_statistics = {
            "power": 1.0,
            "defense": 1.0,
            "health": 1.0,
            "mobility": 1.0,
            "perception": 1.0,
            "stealth": 1.0,
            "intelligence": 1.0,
        }

        for statistic_field in valid_statistics:
            with self.subTest(
                statistic_field=statistic_field,
            ):
                statistics = dict(valid_statistics)
                statistics[statistic_field] = True
                definition = {
                    "entity_type": "animal",
                    "id": "scrub_hare",
                    "name": "Scrub Hare",
                    "taxon_id": "lepus",
                    "statistics": statistics,
                    "diet_type": "herbivore",
                    "activity_pattern": "nocturnal",
                    "food_requirement_per_animal_per_cycle": 0.5,
                    "birth_rate_per_animal_per_cycle": 0.12,
                    "diet": [
                        {
                            "resource_id": "grass_forage",
                            "preference": 1.0,
                        },
                    ],
                }
                source_path = Path(
                    "content/animals/scrub_hare.json"
                )

                with self.assertRaisesRegex(
                    TypeError,
                    (
                        rf"statistics.*{statistic_field}.*"
                        r"must be a number"
                    ),
                ):
                    validate_entity_definition(
                        definition,
                        source_path,
                    )

    def test_rejects_nonfinite_animal_statistic(self) -> None:
        valid_statistics = {
            "power": 1.0,
            "defense": 1.0,
            "health": 1.0,
            "mobility": 1.0,
            "perception": 1.0,
            "stealth": 1.0,
            "intelligence": 1.0,
        }

        for statistic_field in valid_statistics:
            for statistic_value in (
                float("nan"),
                float("inf"),
                float("-inf"),
            ):
                with self.subTest(
                    statistic_field=statistic_field,
                    statistic_value=statistic_value,
                ):
                    statistics = dict(valid_statistics)
                    statistics[statistic_field] = statistic_value
                    definition = {
                        "entity_type": "animal",
                        "id": "scrub_hare",
                        "name": "Scrub Hare",
                        "taxon_id": "lepus",
                        "statistics": statistics,
                        "diet_type": "herbivore",
                        "activity_pattern": "nocturnal",
                        "food_requirement_per_animal_per_cycle": 0.5,
                        "birth_rate_per_animal_per_cycle": 0.12,
                        "diet": [
                            {
                                "resource_id": "grass_forage",
                                "preference": 1.0,
                            },
                        ],
                    }
                    source_path = Path(
                        "content/animals/scrub_hare.json"
                    )

                    with self.assertRaisesRegex(
                        ValueError,
                        (
                            rf"statistics.*{statistic_field}.*"
                            r"must be finite"
                        ),
                    ):
                        validate_entity_definition(
                            definition,
                            source_path,
                        )

    def test_rejects_unsupported_animal_statistic(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "taxon_id": "lepus",
            "statistics": {
                "power": 1.0,
                "defense": 1.0,
                "health": 1.0,
                "mobility": 1.0,
                "perception": 1.0,
                "stealth": 1.0,
                "intelligence": 1.0,
                "speed": 1.0,
            },
            "diet_type": "herbivore",
            "activity_pattern": "nocturnal",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"statistics.*unsupported.*speed",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_negative_animal_statistic(self) -> None:
        valid_statistics = {
            "power": 1.0,
            "defense": 1.0,
            "health": 1.0,
            "mobility": 1.0,
            "perception": 1.0,
            "stealth": 1.0,
            "intelligence": 1.0,
        }

        for statistic_field in valid_statistics:
            with self.subTest(
                statistic_field=statistic_field,
            ):
                statistics = dict(valid_statistics)
                statistics[statistic_field] = -0.1
                definition = {
                    "entity_type": "animal",
                    "id": "scrub_hare",
                    "name": "Scrub Hare",
                    "taxon_id": "lepus",
                    "statistics": statistics,
                    "diet_type": "herbivore",
                    "activity_pattern": "nocturnal",
                    "food_requirement_per_animal_per_cycle": 0.5,
                    "birth_rate_per_animal_per_cycle": 0.12,
                    "diet": [
                        {
                            "resource_id": "grass_forage",
                            "preference": 1.0,
                        },
                    ],
                }
                source_path = Path(
                    "content/animals/scrub_hare.json"
                )

                with self.assertRaisesRegex(
                    ValueError,
                    (
                        rf"statistics.*{statistic_field}.*"
                        r"must not be negative"
                    ),
                ):
                    validate_entity_definition(
                        definition,
                        source_path,
                    )

    def test_rejects_nonstring_animal_body_size_category(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "taxon_id": "lepus",
            "body_size_category": 42,
            "diet_type": "herbivore",
            "activity_pattern": "nocturnal",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"body_size_category.*must be a string",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_accepts_supported_animal_body_size_categories(self) -> None:
        base_definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "taxon_id": "lepus",
            "diet_type": "herbivore",
            "activity_pattern": "nocturnal",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        for body_size_category in (
            "very_small",
            "small",
            "medium",
            "large",
            "very_large",
        ):
            with self.subTest(
                body_size_category=body_size_category,
            ):
                definition = dict(base_definition)
                definition["body_size_category"] = (
                    body_size_category
                )

                validate_entity_definition(
                    definition,
                    source_path,
                )

    def test_rejects_invalid_animal_body_size_categories(
        self,
    ) -> None:
        invalid_cases = (
            (
                "",
                ValueError,
                r"body_size_category.*must not be empty",
            ),
            (
                "gigantic",
                ValueError,
                r"unsupported body size category.*gigantic",
            ),
        )

        for value, error_type, message_pattern in invalid_cases:
            with self.subTest(value=value):
                definition = {
                    "entity_type": "animal",
                    "id": "scrub_hare",
                    "name": "Scrub Hare",
                    "taxon_id": "lepus",
                    "body_size_category": value,
                    "diet_type": "herbivore",
                    "activity_pattern": "nocturnal",
                    "food_requirement_per_animal_per_cycle": 0.5,
                    "birth_rate_per_animal_per_cycle": 0.12,
                    "diet": [
                        {
                            "resource_id": "grass_forage",
                            "preference": 1.0,
                        },
                    ],
                }

                with self.assertRaisesRegex(
                    error_type,
                    message_pattern,
                ):
                    validate_entity_definition(
                        definition,
                        Path(
                            "content/animals/scrub_hare.json"
                        ),
                    )

    def test_rejects_authored_animal_weight_class(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "taxon_id": "lepus",
            "weight_class": "very_light",
            "typical_adult_mass_kg": 3.5,
            "diet_type": "herbivore",
            "activity_pattern": "nocturnal",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }

        with self.assertRaisesRegex(
            ValueError,
            (
                r"weight_class.*must not be defined.*"
                r"derived from typical_adult_mass_kg"
            ),
        ):
            validate_entity_definition(
                definition,
                Path("content/animals/scrub_hare.json"),
            )

    def test_rejects_animal_statistic_greater_than_ten(
        self,
    ) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "taxon_id": "lepus",
            "statistics": {
                "power": 10.1,
                "defense": 1.0,
                "health": 1.0,
                "mobility": 1.0,
                "perception": 1.0,
                "stealth": 1.0,
                "intelligence": 1.0,
            },
            "diet_type": "herbivore",
            "activity_pattern": "nocturnal",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }

        with self.assertRaisesRegex(
            ValueError,
            r"statistics\.power.*must not be greater than 10",
        ):
            validate_entity_definition(
                definition,
                Path("content/animals/scrub_hare.json"),
            )

    def test_accepts_animal_statistics_independent_of_body_size(
        self,
    ) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "taxon_id": "lepus",
            "body_size_category": "small",
            "statistics": {
                "power": 3.0,
                "defense": 4.0,
                "health": 4.0,
                "mobility": 8.0,
                "perception": 7.0,
                "stealth": 5.0,
                "intelligence": 3.0,
            },
            "diet_type": "herbivore",
            "activity_pattern": "nocturnal",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }

        validate_entity_definition(
            definition,
            Path("content/animals/scrub_hare.json"),
        )

    def test_rejects_invalid_typical_adult_masses(self) -> None:
        invalid_cases = (
            (
                "heavy",
                TypeError,
                r"typical_adult_mass_kg.*must be a number",
            ),
            (
                True,
                TypeError,
                r"typical_adult_mass_kg.*must be a number",
            ),
            (
                float("nan"),
                ValueError,
                r"typical_adult_mass_kg.*must be finite",
            ),
            (
                float("inf"),
                ValueError,
                r"typical_adult_mass_kg.*must be finite",
            ),
            (
                float("-inf"),
                ValueError,
                r"typical_adult_mass_kg.*must be finite",
            ),
            (
                0,
                ValueError,
                (
                    r"typical_adult_mass_kg.*"
                    r"must be greater than zero"
                ),
            ),
            (
                -1.0,
                ValueError,
                (
                    r"typical_adult_mass_kg.*"
                    r"must be greater than zero"
                ),
            ),
        )

        for value, error_type, message_pattern in invalid_cases:
            with self.subTest(value=value):
                definition = {
                    "entity_type": "animal",
                    "id": "scrub_hare",
                    "name": "Scrub Hare",
                    "taxon_id": "lepus",
                    "typical_adult_mass_kg": value,
                    "diet_type": "herbivore",
                    "activity_pattern": "nocturnal",
                    "food_requirement_per_animal_per_cycle": 0.5,
                    "birth_rate_per_animal_per_cycle": 0.12,
                    "diet": [
                        {
                            "resource_id": "grass_forage",
                            "preference": 1.0,
                        },
                    ],
                }

                with self.assertRaisesRegex(
                    error_type,
                    message_pattern,
                ):
                    validate_entity_definition(
                        definition,
                        Path(
                            "content/animals/scrub_hare.json"
                        ),
                    )

    def test_raises_error_when_animal_feeding_field_is_missing(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            (
                r"scrub_hare\.json"
                r".*diet_type"
                r".*food_requirement_per_animal_per_cycle"
                r".*diet"
            ),
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_raises_error_when_animal_diet_type_is_not_string(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": 42,
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.25,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                }
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"diet_type.*must be a string",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_raises_error_when_animal_diet_type_is_empty(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "   ",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.25,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                }
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"diet_type.*must not be empty",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_raises_error_for_unsupported_animal_diet_type(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "photosynthetic",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.25,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                }
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"unsupported diet type.*photosynthetic",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_accepts_omnivore_animal_diet_type(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "warthog",
            "name": "Warthog",
            "diet_type": "omnivore",
            "food_requirement_per_animal_per_cycle": 2.0,
            "birth_rate_per_animal_per_cycle": 0.1,
            "diet": [
                {
                    "resource_id": "fruit",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/mammals/warthog.json"
        )

        validate_entity_definition(
            definition,
            source_path,
        )

    def test_rejects_unsupported_animal_activity_pattern(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "activity_pattern": "cathemeral",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"unsupported activity pattern.*cathemeral",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_nonstring_animal_activity_pattern(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "activity_pattern": 42,
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"activity_pattern.*must be a string",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_empty_animal_activity_pattern(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "activity_pattern": "   ",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"activity_pattern.*must not be empty",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_accepts_supported_animal_activity_patterns(self) -> None:
        for activity_pattern in (
            "diurnal",
            "nocturnal",
            "crepuscular",
            "flexible",
        ):
            with self.subTest(activity_pattern=activity_pattern):
                definition = {
                    "entity_type": "animal",
                    "id": "scrub_hare",
                    "name": "Scrub Hare",
                    "diet_type": "herbivore",
                    "activity_pattern": activity_pattern,
                    "food_requirement_per_animal_per_cycle": 0.5,
                    "birth_rate_per_animal_per_cycle": 0.12,
                    "diet": [
                        {
                            "resource_id": "grass_forage",
                            "preference": 1.0,
                        },
                    ],
                }

                validate_entity_definition(
                    definition,
                    Path("content/animals/scrub_hare.json"),
                )

    def test_accepts_supported_primary_movement_modes(self) -> None:
        for movement_mode in (
            "terrestrial",
            "flight",
        ):
            with self.subTest(movement_mode=movement_mode):
                definition = {
                    "entity_type": "animal",
                    "id": "test_animal",
                    "name": "Test Animal",
                    "diet_type": "herbivore",
                    "primary_movement_mode": movement_mode,
                    "food_requirement_per_animal_per_cycle": 1.0,
                    "birth_rate_per_animal_per_cycle": 0.1,
                    "diet": [
                        {
                            "resource_id": "grass_forage",
                            "preference": 1.0,
                        },
                    ],
                }

                validate_entity_definition(
                    definition,
                    Path("content/animals/test_animal.json"),
                )

    def test_accepts_secondary_animal_movement_mode(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "helmeted_guineafowl",
            "name": "Helmeted Guineafowl",
            "diet_type": "omnivore",
            "primary_movement_mode": "terrestrial",
            "available_movement_modes": [
                "terrestrial",
                "flight",
            ],
            "food_requirement_per_animal_per_cycle": 0.25,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "seeds",
                    "preference": 1.0,
                },
            ],
        }

        validate_entity_definition(
            definition,
            Path(
                "content/animals/birds/"
                "helmeted_guineafowl.json"
            ),
        )

    def test_rejects_primary_mode_missing_from_available_modes(
        self,
    ) -> None:
        definition = {
            "entity_type": "animal",
            "id": "helmeted_guineafowl",
            "name": "Helmeted Guineafowl",
            "diet_type": "omnivore",
            "primary_movement_mode": "terrestrial",
            "available_movement_modes": [
                "flight",
            ],
            "food_requirement_per_animal_per_cycle": 0.25,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "seeds",
                    "preference": 1.0,
                },
            ],
        }

        with self.assertRaisesRegex(
            ValueError,
            (
                r"primary_movement_mode.*must also appear in "
                r"'available_movement_modes'"
            ),
        ):
            validate_entity_definition(
                definition,
                Path(
                    "content/animals/birds/"
                    "helmeted_guineafowl.json"
                ),
            )

    def test_accepts_supported_animal_flight_capabilities(
        self,
    ) -> None:
        for capability in (
            "short_burst",
            "powered",
            "soaring",
        ):
            with self.subTest(capability=capability):
                definition = {
                    "entity_type": "animal",
                    "id": "test_bird",
                    "name": "Test Bird",
                    "diet_type": "omnivore",
                    "primary_movement_mode": "flight",
                    "available_movement_modes": [
                        "terrestrial",
                        "flight",
                    ],
                    "flight_capabilities": [
                        capability,
                    ],
                    "food_requirement_per_animal_per_cycle": 0.25,
                    "birth_rate_per_animal_per_cycle": 0.1,
                    "diet": [
                        {
                            "resource_id": "seeds",
                            "preference": 1.0,
                        },
                    ],
                }

                validate_entity_definition(
                    definition,
                    Path(
                        "content/animals/birds/test_bird.json"
                    ),
                )

    def test_rejects_flight_capabilities_without_flight_mode(
        self,
    ) -> None:
        definition = {
            "entity_type": "animal",
            "id": "test_bird",
            "name": "Test Bird",
            "diet_type": "omnivore",
            "primary_movement_mode": "terrestrial",
            "available_movement_modes": [
                "terrestrial",
            ],
            "flight_capabilities": [
                "short_burst",
            ],
            "food_requirement_per_animal_per_cycle": 0.25,
            "birth_rate_per_animal_per_cycle": 0.1,
            "diet": [
                {
                    "resource_id": "seeds",
                    "preference": 1.0,
                },
            ],
        }

        with self.assertRaisesRegex(
            ValueError,
            (
                r"flight_capabilities.*without including 'flight'.*"
                r"available_movement_modes"
            ),
        ):
            validate_entity_definition(
                definition,
                Path(
                    "content/animals/birds/test_bird.json"
                ),
            )

    def test_rejects_invalid_primary_movement_modes(self) -> None:
        invalid_cases = (
            (
                42,
                TypeError,
                r"primary_movement_mode.*must be a string",
            ),
            (
                "   ",
                ValueError,
                r"primary_movement_mode.*must not be empty",
            ),
            (
                "aquatic",
                ValueError,
                r"unsupported primary movement mode.*aquatic",
            ),
        )

        for value, error_type, message_pattern in invalid_cases:
            with self.subTest(value=value):
                definition = {
                    "entity_type": "animal",
                    "id": "test_animal",
                    "name": "Test Animal",
                    "diet_type": "herbivore",
                    "primary_movement_mode": value,
                    "food_requirement_per_animal_per_cycle": 1.0,
                    "birth_rate_per_animal_per_cycle": 0.1,
                    "diet": [
                        {
                            "resource_id": "grass_forage",
                            "preference": 1.0,
                        },
                    ],
                }

                with self.assertRaisesRegex(
                    error_type,
                    message_pattern,
                ):
                    validate_entity_definition(
                        definition,
                        Path(
                            "content/animals/test_animal.json"
                        ),
                    )

    def test_raises_error_when_animal_food_requirement_is_not_number(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "food_requirement_per_animal_per_cycle": "half a kilogram",
            "birth_rate_per_animal_per_cycle": 0.25,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                }
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            (
                r"food_requirement_per_animal_per_cycle"
                r".*must be a number"
            ),
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_raises_error_when_animal_food_requirement_is_boolean(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "food_requirement_per_animal_per_cycle": True,
            "birth_rate_per_animal_per_cycle": 0.25,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                }
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            (
                r"food_requirement_per_animal_per_cycle"
                r".*must be a number"
            ),
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_raises_error_when_animal_food_requirement_is_not_positive(self) -> None:
        for invalid_requirement in (0, -0.5):
            with self.subTest(
                food_requirement=invalid_requirement,
            ):
                definition = {
                    "entity_type": "animal",
                    "id": "scrub_hare",
                    "name": "Scrub Hare",
                    "diet_type": "herbivore",
                    "food_requirement_per_animal_per_cycle": (
                        invalid_requirement
                    ),
                    "birth_rate_per_animal_per_cycle": 0.25,
            "diet": [
                        {
                            "resource_id": "grass_forage",
                            "preference": 1.0,
                        }
                    ],
                }
                source_path = Path(
                    "content/animals/scrub_hare.json"
                )

                with self.assertRaisesRegex(
                    ValueError,
                    (
                        r"food_requirement_per_animal_per_cycle"
                        r".*must be greater than zero"
                    ),
                ):
                    validate_entity_definition(
                        definition,
                        source_path,
                    )

    def test_raises_error_when_animal_diet_is_not_list(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.25,
            "diet": "grass_forage",
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"diet.*must be a list",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_raises_error_when_animal_diet_is_empty(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.25,
            "diet": [],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"diet.*must not be empty",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_raises_error_when_animal_diet_entry_is_not_object(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.25,
            "diet": [
                "grass_forage",
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"diet entry 0.*must be an object",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_raises_error_when_animal_diet_entry_field_is_missing(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.25,
            "diet": [
                {},
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"diet entry 0.*resource_id.*preference",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_raises_error_when_animal_diet_resource_id_is_not_string(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.25,
            "diet": [
                {
                    "resource_id": 42,
                    "preference": 1.0,
                }
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"resource_id.*must be a string",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_raises_error_when_animal_diet_resource_id_is_empty(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.25,
            "diet": [
                {
                    "resource_id": "   ",
                    "preference": 1.0,
                }
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"resource_id.*must not be empty",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_raises_error_for_invalid_animal_diet_resource_id(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.25,
            "diet": [
                {
                    "resource_id": "Grass Forage",
                    "preference": 1.0,
                }
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"resource_id.*must use lowercase snake_case",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_raises_error_when_animal_diet_preference_is_not_number(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.25,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": "favorite",
                }
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"preference.*must be a number",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_raises_error_when_animal_diet_preference_is_boolean(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.25,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": True,
                }
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"preference.*must be a number",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_raises_error_when_animal_diet_preference_is_not_positive(self) -> None:
        for invalid_preference in (0, -1.0):
            with self.subTest(
                preference=invalid_preference,
            ):
                definition = {
                    "entity_type": "animal",
                    "id": "scrub_hare",
                    "name": "Scrub Hare",
                    "diet_type": "herbivore",
                    "food_requirement_per_animal_per_cycle": 0.5,
                    "birth_rate_per_animal_per_cycle": 0.25,
            "diet": [
                        {
                            "resource_id": "grass_forage",
                            "preference": invalid_preference,
                        }
                    ],
                }
                source_path = Path(
                    "content/animals/scrub_hare.json"
                )

                with self.assertRaisesRegex(
                    ValueError,
                    r"preference.*must be greater than zero",
                ):
                    validate_entity_definition(
                        definition,
                        source_path,
                    )

    def test_validates_every_animal_diet_entry(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.25,
            "diet": [
                {
                    "resource_id": 42,
                    "preference": 1.0,
                },
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"resource_id.*must be a string",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_raises_error_when_animal_birth_rate_is_missing(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "food_requirement_per_animal_per_cycle": 0.5,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"birth_rate_per_animal_per_cycle",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_raises_error_when_animal_birth_rate_is_not_number(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": "one quarter",
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            (
                r"birth_rate_per_animal_per_cycle"
                r".*must be a number"
            ),
        ):
            validate_entity_definition(
                definition,
                source_path,
            )


    def test_rejects_boolean_animal_birth_rate(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": True,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"birth_rate_per_animal_per_cycle.*must be a number",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_negative_animal_birth_rate(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": -0.25,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }
        source_path = Path(
            "content/animals/scrub_hare.json"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"birth_rate_per_animal_per_cycle.*must not be negative",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_rejects_nonnumeric_weather_production_multiplier(self) -> None:
        definition = {
            "entity_type": "weather",
            "id": "seasonal_rain",
            "name": "Seasonal Rain",
            "producer_production_multiplier": "extra rain",
        }
        source_path = Path("content/weather/seasonal_rain.json")

        with self.assertRaisesRegex(
            TypeError,
            r"producer_production_multiplier.*must be a number",
        ):
            validate_entity_definition(definition, source_path)

    def test_rejects_boolean_weather_production_multiplier(self) -> None:
        definition = {
            "entity_type": "weather",
            "id": "seasonal_rain",
            "name": "Seasonal Rain",
            "producer_production_multiplier": True,
        }
        source_path = Path("content/weather/seasonal_rain.json")

        with self.assertRaisesRegex(
            TypeError,
            r"producer_production_multiplier.*must be a number",
        ):
            validate_entity_definition(definition, source_path)

    def test_rejects_negative_weather_production_modifier(self) -> None:
        definition = {
            "entity_type": "weather",
            "id": "seasonal_rain",
            "name": "Seasonal Rain",
            "producer_production_multiplier": -0.25,
        }
        source_path = Path(
            "content/weather/seasonal_rain.json"
        )
        with self.assertRaisesRegex(
            ValueError,
            r"producer_production_multiplier.*must not be negative",
        ):
            validate_entity_definition(
                definition,
                source_path,
            )

    def test_accepts_zero_weather_production_multiplier(self) -> None:
        definition = {
            "entity_type": "weather",
            "id": "seasonal_rain",
            "name": "Seasonal Rain",
            "producer_production_multiplier": 0.0,
        }
        source_path = Path("content/weather/seasonal_rain.json")

        validate_entity_definition(definition, source_path)

    def test_accepts_weather_without_production_multiplier(self) -> None:
        definition = {
            "entity_type": "weather",
            "id": "seasonal_rain",
            "name": "Seasonal Rain",
        }
        source_path = Path("content/weather/seasonal_rain.json")

        validate_entity_definition(definition, source_path)

    def test_accepts_weather_movement_modifiers(self) -> None:
        definition = {
            "entity_type": "weather",
            "id": "heavy_rain",
            "name": "Heavy Rain",
            "movement_modifiers": {
                "terrestrial": 0.8,
                "flight": 0.65,
            },
        }

        validate_entity_definition(
            definition,
            Path("content/weather/heavy_rain.json"),
        )

    def test_accepts_weather_visibility_modifiers(self) -> None:
        for visibility_modifier in (
            0.35,
            1.0,
        ):
            with self.subTest(
                visibility_modifier=visibility_modifier
            ):
                definition = {
                    "entity_type": "weather",
                    "id": "test_weather",
                    "name": "Test Weather",
                    "visibility_modifier": visibility_modifier,
                }

                validate_entity_definition(
                    definition,
                    Path(
                        "content/weather/"
                        "test_weather.json"
                    ),
                )

    def test_rejects_invalid_weather_visibility_modifier(
        self,
    ) -> None:
        invalid_cases = (
            (
                "low",
                TypeError,
                r"visibility_modifier.*must be a number",
            ),
            (
                True,
                TypeError,
                r"visibility_modifier.*must be a number",
            ),
            (
                float("nan"),
                ValueError,
                r"visibility_modifier.*must be finite",
            ),
            (
                0.0,
                ValueError,
                r"visibility_modifier.*greater than zero.*at most 1.0",
            ),
            (
                1.1,
                ValueError,
                r"visibility_modifier.*greater than zero.*at most 1.0",
            ),
        )

        for value, error_type, message_pattern in (
            invalid_cases
        ):
            with self.subTest(value=value):
                definition = {
                    "entity_type": "weather",
                    "id": "test_weather",
                    "name": "Test Weather",
                    "visibility_modifier": value,
                }

                with self.assertRaisesRegex(
                    error_type,
                    message_pattern,
                ):
                    validate_entity_definition(
                        definition,
                        Path(
                            "content/weather/"
                            "test_weather.json"
                        ),
                    )

    def test_rejects_invalid_weather_movement_modifier(
        self,
    ) -> None:
        invalid_cases = (
            (
                {"aquatic": 1.0},
                ValueError,
                r"unsupported movement modifier mode.*aquatic",
            ),
            (
                {"terrestrial": "slow"},
                TypeError,
                r"terrestrial.*must be a number",
            ),
            (
                {"flight": float("nan")},
                ValueError,
                r"flight.*must be finite",
            ),
            (
                {"flight": 0.0},
                ValueError,
                r"flight.*must be greater than zero",
            ),
        )

        for modifiers, error_type, message_pattern in (
            invalid_cases
        ):
            with self.subTest(modifiers=modifiers):
                definition = {
                    "entity_type": "weather",
                    "id": "test_weather",
                    "name": "Test Weather",
                    "movement_modifiers": modifiers,
                }

                with self.assertRaisesRegex(
                    error_type,
                    message_pattern,
                ):
                    validate_entity_definition(
                        definition,
                        Path(
                            "content/weather/"
                            "test_weather.json"
                        ),
                    )

    def test_accepts_weather_flight_capability_modifiers(
        self,
    ) -> None:
        definition = {
            "entity_type": "weather",
            "id": "strong_wind",
            "name": "Strong Wind",
            "flight_capability_modifiers": {
                "short_burst": 0.65,
                "powered": 0.7,
                "soaring": 0.85,
            },
        }

        validate_entity_definition(
            definition,
            Path("content/weather/strong_wind.json"),
        )

    def test_rejects_invalid_weather_flight_capability_modifier(
        self,
    ) -> None:
        invalid_cases = (
            (
                {"hovering": 1.0},
                ValueError,
                r"unsupported flight capability modifier.*hovering",
            ),
            (
                {"powered": "difficult"},
                TypeError,
                r"powered.*must be a number",
            ),
            (
                {"soaring": float("nan")},
                ValueError,
                r"soaring.*must be finite",
            ),
            (
                {"short_burst": 0.0},
                ValueError,
                r"short_burst.*must be greater than zero",
            ),
        )

        for modifiers, error_type, message_pattern in (
            invalid_cases
        ):
            with self.subTest(modifiers=modifiers):
                definition = {
                    "entity_type": "weather",
                    "id": "test_weather",
                    "name": "Test Weather",
                    "flight_capability_modifiers": modifiers,
                }

                with self.assertRaisesRegex(
                    error_type,
                    message_pattern,
                ):
                    validate_entity_definition(
                        definition,
                        Path(
                            "content/weather/"
                            "test_weather.json"
                        ),
                    )

    def test_rejects_duplicate_resources_in_animal_diet(self) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "diet_type": "herbivore",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {"resource_id": "grass_forage", "preference": 1.0},
                {"resource_id": "grass_forage", "preference": 0.5},
            ],
        }
        source_path = Path("content/animals/scrub_hare.json")

        with self.assertRaisesRegex(
            ValueError,
            r"Duplicate diet resource.*grass_forage",
        ):
            validate_entity_definition(definition, source_path)

    def test_rejects_nonfinite_animal_birth_rates(self) -> None:
        for birth_rate in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(birth_rate=birth_rate):
                definition = {
                    "entity_type": "animal",
                    "id": "scrub_hare",
                    "name": "Scrub Hare",
                    "diet_type": "herbivore",
                    "food_requirement_per_animal_per_cycle": 0.5,
                    "birth_rate_per_animal_per_cycle": birth_rate,
                    "diet": [
                        {"resource_id": "grass_forage", "preference": 1.0},
                    ],
                }
                source_path = Path("content/animals/scrub_hare.json")

                with self.assertRaisesRegex(
                    ValueError,
                    r"birth_rate_per_animal_per_cycle.*must be finite",
                ):
                    validate_entity_definition(definition, source_path)

    def test_rejects_nonfinite_animal_food_requirements(self) -> None:
        for food_requirement in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(food_requirement=food_requirement):
                definition = {
                    "entity_type": "animal",
                    "id": "scrub_hare",
                    "name": "Scrub Hare",
                    "diet_type": "herbivore",
                    "food_requirement_per_animal_per_cycle": food_requirement,
                    "birth_rate_per_animal_per_cycle": 0.12,
                    "diet": [
                        {"resource_id": "grass_forage", "preference": 1.0},
                    ],
                }
                source_path = Path("content/animals/scrub_hare.json")

                with self.assertRaisesRegex(
                    ValueError,
                    r"food_requirement_per_animal_per_cycle.*must be finite",
                ):
                    validate_entity_definition(definition, source_path)

    def test_rejects_nonfinite_diet_preferences(self) -> None:
        for preference in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(preference=preference):
                definition = {
                    "entity_type": "animal",
                    "id": "scrub_hare",
                    "name": "Scrub Hare",
                    "diet_type": "herbivore",
                    "food_requirement_per_animal_per_cycle": 0.5,
                    "birth_rate_per_animal_per_cycle": 0.12,
                    "diet": [
                        {
                            "resource_id": "grass_forage",
                            "preference": preference,
                        },
                    ],
                }
                source_path = Path("content/animals/scrub_hare.json")

                with self.assertRaisesRegex(
                    ValueError,
                    r"preference.*must be finite",
                ):
                    validate_entity_definition(definition, source_path)

    def test_rejects_nonfinite_production_amounts(self) -> None:
        for production_amount in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(production_amount=production_amount):
                definition = {
                    "entity_type": "producer",
                    "id": "redgrass",
                    "name": "Redgrass",
                    "production": [
                        {
                            "resource_id": "grass_forage",
                            "amount_per_producer_per_day": production_amount,
                        },
                    ],
                }
                source_path = Path("content/producers/redgrass.json")

                with self.assertRaisesRegex(
                    ValueError,
                    r"amount_per_producer_per_day.*must be finite",
                ):
                    validate_entity_definition(definition, source_path)

    def test_rejects_nonfinite_weather_production_multipliers(self) -> None:
        for multiplier in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(multiplier=multiplier):
                definition = {
                    "entity_type": "weather",
                    "id": "seasonal_rain",
                    "name": "Seasonal Rain",
                    "producer_production_multiplier": multiplier,
                }
                source_path = Path("content/weather/seasonal_rain.json")

                with self.assertRaisesRegex(
                    ValueError,
                    r"producer_production_multiplier.*must be finite",
                ):
                    validate_entity_definition(definition, source_path)

    def test_rejects_habitat_missing_terrain_ruggedness(self) -> None:
        definition = {
            "entity_type": "habitat",
            "id": "open_grassland",
            "name": "Open Grassland",
            "description": (
                "Open terrestrial habitat dominated by grasses."
            ),
            "movement_medium": "terrestrial",
            "conditions": {
                "openness": 0.9,
                "vegetation_density": 0.3,
                "ground_firmness": 0.8,
                "shelter_availability": 0.2,
            },
        }

        with self.assertRaisesRegex(
            ValueError,
            r"conditions.*missing required.*terrain_ruggedness",
        ):
            validate_entity_definition(
                definition,
                Path("content/habitats/open_grassland.json"),
            )

    def test_rejects_duplicate_animal_preferred_habitat_ids(
        self,
    ) -> None:
        definition = {
            "entity_type": "animal",
            "id": "scrub_hare",
            "name": "Scrub Hare",
            "preferred_habitat_ids": [
                "open_grassland",
                "open_grassland",
            ],
            "diet_type": "herbivore",
            "food_requirement_per_animal_per_cycle": 0.5,
            "birth_rate_per_animal_per_cycle": 0.12,
            "diet": [
                {
                    "resource_id": "grass_forage",
                    "preference": 1.0,
                },
            ],
        }

        with self.assertRaisesRegex(
            ValueError,
            (
                r"preferred_habitat_ids.*duplicate habitat id.*"
                r"open_grassland"
            ),
        ):
            validate_entity_definition(
                definition,
                Path("content/animals/mammals/scrub_hare.json"),
            )

    def test_accepts_habitat_movement_modifiers(self) -> None:
        definition = {
            "entity_type": "habitat",
            "id": "acacia_scrub",
            "name": "Acacia Scrub",
            "description": "Shrub-dense savanna habitat.",
            "movement_medium": "terrestrial",
            "movement_modifiers": {
                "terrestrial": 0.8,
                "flight": 0.95,
            },
            "conditions": {
                "openness": 0.5,
                "vegetation_density": 0.8,
                "ground_firmness": 0.7,
                "shelter_availability": 0.7,
                "terrain_ruggedness": 0.3,
            },
        }

        validate_entity_definition(
            definition,
            Path("content/habitats/acacia_scrub.json"),
        )

    def test_rejects_invalid_habitat_movement_modifier(
        self,
    ) -> None:
        invalid_cases = (
            (
                {"aquatic": 1.0},
                ValueError,
                r"unsupported movement modifier mode.*aquatic",
            ),
            (
                {"terrestrial": "slow"},
                TypeError,
                r"terrestrial.*must be a number",
            ),
            (
                {"terrestrial": float("nan")},
                ValueError,
                r"terrestrial.*must be finite",
            ),
            (
                {"terrestrial": 0.0},
                ValueError,
                r"terrestrial.*must be greater than zero",
            ),
        )

        for modifiers, error_type, message_pattern in (
            invalid_cases
        ):
            with self.subTest(modifiers=modifiers):
                definition = {
                    "entity_type": "habitat",
                    "id": "test_habitat",
                    "name": "Test Habitat",
                    "description": "A test habitat.",
                    "movement_medium": "terrestrial",
                    "movement_modifiers": modifiers,
                    "conditions": {
                        "openness": 0.5,
                        "vegetation_density": 0.5,
                        "ground_firmness": 0.5,
                        "shelter_availability": 0.5,
                        "terrain_ruggedness": 0.5,
                    },
                }

                with self.assertRaisesRegex(
                    error_type,
                    message_pattern,
                ):
                    validate_entity_definition(
                        definition,
                        Path(
                            "content/habitats/"
                            "test_habitat.json"
                        ),
                    )

if __name__ == "__main__":
    unittest.main()
