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
                    "amount_per_producer_per_cycle": 1.0,
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

    def test_raises_error_for_invalid_entity_id(self) -> None:
        definition = {
            "entity_type": "producer",
            "id": "Silverleaf Shrub",
            "name": "Silverleaf Shrub",
            "production": [
                {
                    "resource_id": "test_resource",
                    "amount_per_producer_per_cycle": 1.0,
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
            r"production entry 0.*amount_per_producer_per_cycle",
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
                    "amount_per_producer_per_cycle": 0.25,
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
                    "amount_per_producer_per_cycle": 0.25,
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
                    "amount_per_producer_per_cycle": 0.25,
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
                    "amount_per_producer_per_cycle": "high",
                }
            ],
        }
        source_path = Path(
            "content/producers/redgrass.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"amount_per_producer_per_cycle.*must be a number",
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
                    "amount_per_producer_per_cycle": True,
                }
            ],
        }
        source_path = Path(
            "content/producers/redgrass.json"
        )

        with self.assertRaisesRegex(
            TypeError,
            r"amount_per_producer_per_cycle.*must be a number",
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
                            "amount_per_producer_per_cycle": invalid_amount,
                        }
                    ],
                }
                source_path = Path(
                    "content/producers/redgrass.json"
                )

                with self.assertRaisesRegex(
                    ValueError,
                    r"amount_per_producer_per_cycle.*greater than zero",
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
                    "amount_per_producer_per_cycle": 0.25,
                },
                {
                    "resource_id": "grass_forage",
                    "amount_per_producer_per_cycle": 0.25,
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
                            "amount_per_producer_per_cycle": production_amount,
                        },
                    ],
                }
                source_path = Path("content/producers/redgrass.json")

                with self.assertRaisesRegex(
                    ValueError,
                    r"amount_per_producer_per_cycle.*must be finite",
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
if __name__ == "__main__":
    unittest.main()
