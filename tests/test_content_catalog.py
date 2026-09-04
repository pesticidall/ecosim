import unittest
from pathlib import Path

from core.content_catalog import build_content_registry

PROJECT_ROOT = Path(__file__).resolve().parents[1]

class TestContentCatalog(unittest.TestCase):
    def test_builds_registry_from_all_content_directories(self) -> None:
        content_root = PROJECT_ROOT / "content"
        registry = build_content_registry(content_root)
        grass_definition = registry.get("grass")
        forage_definition = registry.get("grass_forage")
        self.assertEqual(
            grass_definition["entity_type"],
            "producer",
        )
        self.assertEqual(
            forage_definition["entity_type"],
            "resource",
        )
if __name__ == "__main__":
    unittest.main()