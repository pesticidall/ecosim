import unittest

from core.content_registry import ContentRegistry


class TestContentRegistry(unittest.TestCase):
    def test_registers_and_retrieves_definition(self) -> None:
        registry = ContentRegistry()
        definition = {
            "entity_type": "producer",
            "id": "grass",
            "name": "Grass"
        }
        registry.register(definition)
        self.assertEqual(
            registry.get("grass"),
            definition,
        )

    def test_rejects_duplicate_entity_id(self) -> None:
        registry = ContentRegistry()
        first_definition = {
            "entity_type": "producer",
            "id": "grass",
            "name": "Grass"
        }
        duplicate_definition = {
            "entity_type": "producer",
            "id": "grass",
            "name": "Green Grass"
        }
        registry.register(first_definition)
        with self.assertRaisesRegex(
            ValueError,
            r"Duplicate entity id 'grass'",
        ):
            registry.register(duplicate_definition)

    def test_registers_collection_of_definitions(self) -> None:
        registry = ContentRegistry()
        definitions = [
            {
                "entity_type": "producer",
                "id": "grass",
                "name": "Grass",
            },
            {
                "entity_type": "resource",
                "id": "grass_forage",
                "name": "Grass Forage",
            },
        ]
        registry.register_all(definitions)
        self.assertEqual(
            registry.get("grass"),
            definitions[0],
        )
        self.assertEqual(
            registry.get("grass_forage"),
            definitions[1],
        )


if __name__ == "__main__":
    unittest.main()