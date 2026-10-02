from pathlib import Path

from core.content_loader import (
    load_entity_definitions_from_directory,
)
from core.content_registry import ContentRegistry
from simulation.feeding import validate_animal_diet_resource_references
from simulation.habitats import (
    validate_animal_habitat_references,
    validate_producer_habitat_references,
    validate_region_habitat_references,
)
from simulation.production import validate_producer_resource_references
from simulation.taxonomy import (
    validate_animal_taxon_references,
    validate_taxonomy,
)
from simulation.traits import (
    validate_animal_trait_references,
    validate_taxon_trait_references,
)

CONTENT_DIRECTORIES = (
    ("animals", "animal"),
    ("habitats", "habitat"),
    ("producers", "producer"),
    ("regions", "region"),
    ("resources", "resource"),
    ("taxonomy", "taxon"),
    ("traits", "trait"),
    ("weather", "weather"),
)
def build_content_registry(
    content_root: Path,
) -> ContentRegistry:
    """Load, register, and cross-validate every content definition."""
    registry = ContentRegistry()
    animal_definitions: list[dict] = []
    habitat_definitions: list[dict] = []
    producer_definitions: list[dict] = []
    region_definitions: list[dict] = []
    resource_definitions: list[dict] = []
    taxon_definitions: list[dict] = []
    trait_definitions: list[dict] = []
    for directory_name, expected_entity_type in CONTENT_DIRECTORIES:
        directory_path = content_root / directory_name
        definitions = load_entity_definitions_from_directory(
            directory_path,
            expected_entity_type=expected_entity_type,
        )
        if expected_entity_type == "animal":
            animal_definitions.extend(definitions)
        if expected_entity_type == "habitat":
            habitat_definitions.extend(definitions)
        if expected_entity_type == "producer":
            producer_definitions.extend(definitions)
        if expected_entity_type == "region":
            region_definitions.extend(definitions)
        if expected_entity_type == "resource":
            resource_definitions.extend(definitions)
        if expected_entity_type == "taxon":
            taxon_definitions.extend(definitions)
        if expected_entity_type == "trait":
            trait_definitions.extend(definitions)
        registry.register_all(definitions)
    validate_taxonomy(taxon_definitions)
    validate_region_habitat_references(
        region_definitions,
        habitat_definitions,
    )
    validate_animal_habitat_references(
        animal_definitions,
        habitat_definitions,
    )
    validate_producer_habitat_references(
        producer_definitions,
        habitat_definitions,
    )
    validate_producer_resource_references(
        producer_definitions,
        resource_definitions,
    )
    validate_animal_diet_resource_references(
        animal_definitions,
        resource_definitions,
    )
    validate_taxon_trait_references(
        taxon_definitions,
        trait_definitions,
    )
    validate_animal_taxon_references(
        animal_definitions,
        taxon_definitions,
    )
    validate_animal_trait_references(
        animal_definitions,
        trait_definitions,
    )
    return registry
