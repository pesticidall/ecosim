from collections.abc import Iterable
from typing import Any


def validate_taxonomy(
    definitions: Iterable[dict[str, Any]],
) -> None:
    """Reject missing parents and cycles in a collection of taxa."""
    definitions_by_id = {
        definition["id"]: definition
        for definition in definitions
    }
    for taxon_id, definition in definitions_by_id.items():
        parent_taxon_id = definition["parent_taxon_id"]
        if (
            parent_taxon_id is not None
            and parent_taxon_id not in definitions_by_id
        ):
            raise ValueError(
                f"Taxon '{taxon_id}' references missing parent "
                f"taxon '{parent_taxon_id}'."
            )
    for starting_taxon_id in definitions_by_id:
        lineage: list[str] = []
        current_taxon_id: str | None = starting_taxon_id

        while current_taxon_id is not None:
            if current_taxon_id in lineage:
                cycle_start = lineage.index(current_taxon_id)
                cycle = (
                    lineage[cycle_start:]
                    + [current_taxon_id]
                )
                raise ValueError(
                    "Detected circular taxonomic relationship: "
                    + " -> ".join(cycle)
                    + "."
                )

            lineage.append(current_taxon_id)
            current_taxon_id = definitions_by_id[
                current_taxon_id
            ]["parent_taxon_id"]

def validate_animal_taxon_references(
    animal_definitions: Iterable[dict[str, Any]],
    taxon_definitions: Iterable[dict[str, Any]],
) -> None:
    """Require every animal taxon ID to reference a loaded taxon."""
    taxon_ids = {
        definition["id"]
        for definition in taxon_definitions
    }
    for animal_definition in animal_definitions:
        taxon_id = animal_definition.get("taxon_id")
        if taxon_id is None:
            continue
        if taxon_id not in taxon_ids:
            animal_id = animal_definition["id"]
            raise ValueError(
                f"Animal '{animal_id}' references unknown "
                f"taxon '{taxon_id}'."
            )

def resolve_taxonomic_lineage(
    taxon_id: str,
    definitions: Iterable[dict[str, Any]],
) -> list[str]:
    """Return taxon IDs from the root through the requested taxon."""
    definition_list = list(definitions)
    validate_taxonomy(definition_list)

    definitions_by_id = {
        definition["id"]: definition
        for definition in definition_list
    }
    if taxon_id not in definitions_by_id:
        raise ValueError(
            f"Unknown taxon '{taxon_id}'."
        )
    lineage: list[str] = []
    current_taxon_id: str | None = taxon_id

    while current_taxon_id is not None:
        lineage.append(current_taxon_id)
        current_taxon_id = definitions_by_id[
            current_taxon_id
        ]["parent_taxon_id"]

    lineage.reverse()
    return lineage

def resolve_animal_taxonomic_lineage(
    animal_definition: dict[str, Any],
    taxon_definitions: Iterable[dict[str, Any]],
) -> list[str]:
    """Resolve the complete lineage for an animal's assigned taxon."""
    return resolve_taxonomic_lineage(
        animal_definition["taxon_id"],
        taxon_definitions,
    )
