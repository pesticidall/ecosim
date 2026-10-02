import json
import tempfile
import unittest
from pathlib import Path

from core.content_loader import (
    load_entity_definition,
    load_entity_definitions_from_directory,
    load_json_file,
)


def make_test_producer_definition(
    entity_id: str,
    name: str,
) -> dict[str, object]:
    return {
        "entity_type": "producer",
        "id": entity_id,
        "name": name,
        "production": [
            {
                "resource_id": "test_resource",
                "amount_per_producer_per_day": 1.0
            }
        ]
    }
class TestLoadJsonFile(unittest.TestCase):
    def test_loads_json_object(self) -> None:
        expected_data = {
            "entity_type": "producer",
            "id": "test_grass",
            "name": "Test Grass",
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
                encoding="utf-8",
            )
            with self.assertRaises(json.JSONDecodeError):
                load_json_file(file_path)

    def test_raises_error_when_top_level_is_not_object(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            file_path = Path(temporary_directory) / "list.json"
            file_path.write_text(
                '["producer", "grass"]',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                TypeError,
                "must be an object",
            ):
                load_json_file(file_path)

    def test_loads_valid_entity_definition(self) -> None:
        expected_data = make_test_producer_definition(
            "test_grass",
            "Test Grass",
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            file_path = Path(temporary_directory) / "test_entity.json"
            file_path.write_text(
                json.dumps(expected_data),
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
                json.dumps(
                    make_test_producer_definition(
                        "test_shrub",
                        "Test Shrub",
                    )
                ),
                encoding="utf-8",
            )
            grass_path = directory_path / "a_grass.json"
            grass_path.write_text(
                    json.dumps(
                        make_test_producer_definition(
                            "test_grass",
                            "Test Grass",
                        )
                ),
                encoding="utf-8",
            )
            ignored_path = directory_path / "notes.txt"
            ignored_path.write_text(
                "This file should not be loaded.",
                encoding="utf-8",
            )
            definitions = load_entity_definitions_from_directory(
                directory_path,
            )
        loaded_ids = [
            definition["id"]
            for definition in definitions
        ]
        self.assertEqual(
            loaded_ids,
            ["test_grass", "test_shrub"],
        )

    def test_loads_animal_from_nested_organizational_folder(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            animals_directory = (
                Path(temporary_directory)
                / "animals"
            )
            misleading_directory = (
                animals_directory
                / "birds"
            )
            misleading_directory.mkdir(parents=True)
            animal_path = (
                misleading_directory
                / "scrub_hare.json"
            )
            animal_path.write_text(
                json.dumps(
                    {
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
                ),
                encoding="utf-8",
            )

            definitions = (
                load_entity_definitions_from_directory(
                    animals_directory,
                    expected_entity_type="animal",
                )
            )

        self.assertEqual(len(definitions), 1)
        self.assertEqual(
            definitions[0]["id"],
            "scrub_hare",
        )
        self.assertEqual(
            definitions[0]["taxon_id"],
            "lepus",
        )

    def test_taxon_rank_does_not_depend_on_folder_name(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            taxonomy_directory = (
                Path(temporary_directory)
                / "taxonomy"
            )
            misleading_directory = (
                taxonomy_directory
                / "06_genus"
            )
            misleading_directory.mkdir(parents=True)
            taxon_path = (
                misleading_directory
                / "animalia.json"
            )
            taxon_path.write_text(
                json.dumps(
                    {
                        "entity_type": "taxon",
                        "id": "animalia",
                        "name": "Animalia",
                        "rank": "kingdom",
                        "parent_taxon_id": None,
                    }
                ),
                encoding="utf-8",
            )

            definitions = (
                load_entity_definitions_from_directory(
                    taxonomy_directory,
                    expected_entity_type="taxon",
                )
            )

        self.assertEqual(len(definitions), 1)
        self.assertEqual(
            definitions[0]["id"],
            "animalia",
        )
        self.assertEqual(
            definitions[0]["rank"],
            "kingdom",
        )

    def test_raises_error_when_directory_does_not_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing_directory = (
                Path(temporary_directory)
                / "missing"
            )
            with self.assertRaisesRegex(
                FileNotFoundError,
                r"Content directory.*missing.*does not exist",
            ):
                load_entity_definitions_from_directory(
                    missing_directory,
                )

    def test_rejects_unexpected_entity_type_in_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory_path = Path(temporary_directory)
            file_path = directory_path / "wrong_type.json"
            file_path.write_text(
                json.dumps(
                    make_test_producer_definition(
                        "test_grass",
                        "Test Grass",
                    )
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                ValueError,
                r"wrong_type\.json.*producer.*resource",
            ):
                load_entity_definitions_from_directory(
                    directory_path,
                    expected_entity_type="resource",
                )


if __name__ == "__main__":
    unittest.main()
