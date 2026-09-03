import json
import tempfile
import unittest
from pathlib import Path

from core.content_loader import load_json_file


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
if __name__ == "__main__":
    unittest.main()
