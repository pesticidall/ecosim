import unittest

from simulation.taxonomy import (
    resolve_animal_taxonomic_lineage,
    resolve_taxonomic_lineage,
    validate_taxonomy,
)


class TestTaxonomy(unittest.TestCase):
    def test_resolves_animal_taxonomic_lineage(self) -> None:
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
                "id": "chordata",
                "name": "Chordata",
                "rank": "phylum",
                "parent_taxon_id": "animalia",
            },
            {
                "entity_type": "taxon",
                "id": "mammalia",
                "name": "Mammalia",
                "rank": "class",
                "parent_taxon_id": "chordata",
            },
            {
                "entity_type": "taxon",
                "id": "lagomorpha",
                "name": "Lagomorpha",
                "rank": "order",
                "parent_taxon_id": "mammalia",
            },
            {
                "entity_type": "taxon",
                "id": "leporidae",
                "name": "Leporidae",
                "rank": "family",
                "parent_taxon_id": "lagomorpha",
            },
            {
                "entity_type": "taxon",
                "id": "lepus",
                "name": "Lepus",
                "rank": "genus",
                "parent_taxon_id": "leporidae",
            }
        ]
        self.assertEqual(
            resolve_animal_taxonomic_lineage(
                animal_definition,
                taxon_definitions,
            ),
            [
                "animalia",
                "chordata",
                "mammalia",
                "lagomorpha",
                "leporidae",
                "lepus",
            ],
        )

    def test_resolves_taxonomic_lineage_from_root_to_taxon(self) -> None:
        definitions = [
            {
                "entity_type": "taxon",
                "id": "animalia",
                "name": "Animalia",
                "rank": "kingdom",
                "parent_taxon_id": None,
            },
            {
                "entity_type": "taxon",
                "id": "chordata",
                "rank": "phylum",
                "parent_taxon_id": "animalia",
            },
            {
                "entity_type": "taxon",
                "id": "mammalia",
                "name": "Mammalia",
                "rank": "class",
                "parent_taxon_id": "chordata",
            },
        ]
        self.assertEqual(
            resolve_taxonomic_lineage(
                "mammalia",
                definitions,
            ),
            [
                "animalia",
                "chordata",
                "mammalia",
            ],
        )

    def test_rejects_missing_parent_taxon(self) -> None:
        definitions = [
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
                "parent_taxon_id": "chordata",
            },
        ]

        with self.assertRaisesRegex(
            ValueError,
            r"mammalia.*missing parent taxon.*chordata",
        ):
            validate_taxonomy(definitions)

    def test_rejects_circular_taxonomic_relationship(self) -> None:
        definitions = [
            {
                "entity_type": "taxon",
                "id": "mammalia",
                "name": "Mammalia",
                "rank": "class",
                "parent_taxon_id": "chordata",
            },
            {
                "entity_type": "taxon",
                "id": "chordata",
                "name": "Chordata",
                "rank": "phylum",
                "parent_taxon_id": "mammalia",
            },
        ]

        with self.assertRaisesRegex(
            ValueError,
            r"circular taxonomic relationship.*mammalia.*chordata",
        ):
            validate_taxonomy(definitions)

    def test_rejects_unknown_taxon_when_resolving_lineage(self) -> None:
        definitions = [
            {
                "entity_type": "taxon",
                "id": "animalia",
                "name": "Animalia",
                "rank": "kingdom",
                "parent_taxon_id": None,
            },
        ]

        with self.assertRaisesRegex(
            ValueError,
            r"Unknown taxon.*aves",
        ):
            resolve_taxonomic_lineage(
                "aves",
                definitions,
            )


if __name__ == "__main__":
    unittest.main()