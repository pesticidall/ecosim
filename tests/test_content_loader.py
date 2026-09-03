import json
import tempfile
import unittest
from pathlib import Path

from core.content_loader import (
    load_entity_definition,
    load_entity_definitions_from_directory, 
    load_json_file,
)


class TestLoadJsonFile(unittest.TestCase):
    def test_loads_json_object(self) -> None:
        expected_data = {
            "entity_type": "producer",
            "id": "test_grass",
            "name": "Test Grass"
        }

        with tempfile.TemporaryDirectory() as temporary_directory:
            file_path = Path(temporary_directory) / "test_entity.json"
            file_path.write_text(
                '{"entity_type": "producer", '
                '"id": "test_grass", '
                '"name": "Test Grass"}',
                encoding="utf-8",
            )
            loaded_data = load_json_file(file_path)
        self.assertEqual(loaded_data, expected_data)

    def test_raises_error_for_malformed_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            file_path = Path(temporary_directory) / "malformed.json"
            file_path.write_text(
                '"{entity_type": "producer"',
                encoding="utf-8"
            )
            with self.assertRaises(json.JSONDecodeError):
                load_json_file(file_path)

    def test_raises_error_when_top_level_is_not_object(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            file_path = Path(temporary_directory) / "list.json"
            file_path.write_text(
                '["producer", "grass"]',
                encoding="utf-8"
            )
            with self.assertRaisesRegex(
                TypeError,
                "must be an object",
            ):
                load_json_file(file_path)

    def test_loads_valid_entity_definition(self) -> None:
        expected_data = {
            "entity_type": "producer",
            "id": "test_grass",
            "name": "Test Grass"
        }

        with tempfile.TemporaryDirectory() as temporary_directory:
            file_path = Path(temporary_directory) / "test_entity.json"
            file_path.write_text(
                '{"entity_type": "producer", '
                '"id": "test_grass", '
                '"name": "Test Grass"}',
                encoding="utf-8",
            )
            loaded_data = load_entity_definition(file_path)
        self.assertEqual(loaded_data, expected_data)

    def test_rejects_entity_definition_with_missing_field(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            file_path = Path(temporary_directory) / "invalid_grass.json"
            file_path.write_text(
                '{"entity_type": "producer", '
                '"name": "Invalid Grass"}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                ValueError,
                r"invalid_grass\.json.*id",
            ):
                load_entity_definition(file_path)

    def test_loads_entity_definitions_from_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory_path = Path(temporary_directory)

            shrub_path = directory_path / "b_shrub.json"
            shrub_path.write_text(
                '{"entity_type": "producer", '
                '"id": "test_shrub", '
                '"name": "Test Shrub"}',
                encoding="utf-8",
            )
            grass_path = directory_path / "a_grass.json"
            grass_path.write_text(
                '{"entity_type": "producer", '
                '"id": "test_grass", '
                '"name": "Test Grass"}',
                encoding="utf-8",
            )
            ignored_path = directory_path / "notes.txt"
            ignored_path.write_text(
                "This file should not be loaded.",
                encoding="utf-8",
            )
            definitions = load_entity_definitions_from_directory(
                directory_path
            )
        loaded_ids = [
            definition["id"]
            for definition in definitions
        ]
        self.assertEqual(
            loaded_ids,
            ["test_grass", "test_shrub"],
        )

        
if __name__ == "__main__":
    unittest.main()
