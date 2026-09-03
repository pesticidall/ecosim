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
if __name__ == "__main__":
    unittest.main()