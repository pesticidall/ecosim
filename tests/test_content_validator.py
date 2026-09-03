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
        }
        source_path = Path("content/producers/silverleaf_shrub.json")
        with self.assertRaisesRegex(
            ValueError,
            r"id.*lowercase snake_case",
        ):
            validate_entity_definition(definition, source_path)
if __name__ == "__main__":
    unittest.main()