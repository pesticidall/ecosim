from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from simulation.taxonomy import resolve_animal_taxonomic_lineage


@dataclass(frozen=True)
class TraitEffectResult:
    """Record the traits contributing to one calculation modifier."""

    target: str
    modifier: float
    contributing_trait_ids: tuple[str, ...]


def validate_taxon_trait_references(
    taxon_definitions: Iterable[dict[str, Any]],
    trait_definitions: Iterable[dict[str, Any]],
) -> None:
    """Require every taxonomic default trait to reference a loaded trait."""
    trait_ids = {
        definition["id"]
        for definition in trait_definitions
    }
    for taxon_definition in taxon_definitions:
        taxon_id = taxon_definition["id"]
        for trait_id in taxon_definition.get(
            "default_trait_ids",
            [],
        ):
            if trait_id not in trait_ids:
                raise ValueError(
                    f"Taxon '{taxon_id}' references unknown "
                    f"default trait '{trait_id}'."
                )

def validate_animal_trait_references(
    animal_definitions: Iterable[dict[str, Any]],
    trait_definitions: Iterable[dict[str, Any]],
) -> None:
    """Require every animal trait reference to identify a loaded trait."""
    trait_ids = {
        definition["id"]
        for definition in trait_definitions
    }

    for animal_definition in animal_definitions:
        animal_id = animal_definition["id"]

        for trait_id in animal_definition.get(
            "trait_ids",
            [],
        ):
            if trait_id not in trait_ids:
                raise ValueError(
                    f"Animal '{animal_id}' references unknown "
                    f"added trait '{trait_id}'."
                )

        for trait_id in animal_definition.get(
            "excluded_trait_ids",
            [],
        ):
            if trait_id not in trait_ids:
                raise ValueError(
                    f"Animal '{animal_id}' references unknown "
                    f"excluded trait '{trait_id}'."
                )

def resolve_animal_trait_ids(
    animal_definition: dict[str, Any],
    taxon_definitions: Iterable[dict[str, Any]],
) -> list[str]:
    """Return traits inherited through an animal's taxonomic lineage."""
    taxon_definition_list = list(taxon_definitions)
    lineage = resolve_animal_taxonomic_lineage(
        animal_definition,
        taxon_definition_list
    )
    taxa_by_id = {
        definition["id"]: definition
        for definition in taxon_definition_list
    }
    resolved_trait_ids: list[str] = []
    for taxon_id in lineage:
        taxon_definition = taxa_by_id[taxon_id]
        resolved_trait_ids.extend(
            taxon_definition.get(
                "default_trait_ids",
                [],
            )
        )
    resolved_trait_ids.extend(
        animal_definition.get(
            "trait_ids",
            [],
        )
    )
    excluded_trait_ids = set(
        animal_definition.get(
            "excluded_trait_ids",
            [],
        )
    )
    effective_trait_ids: list[str] = []
    seen_trait_ids: set[str] = set()
    for trait_id in resolved_trait_ids:
        if trait_id in excluded_trait_ids:
            continue
        if trait_id in seen_trait_ids:
            continue
        effective_trait_ids.append(trait_id)
        seen_trait_ids.add(trait_id)
    return effective_trait_ids


def resolve_trait_effect(
    trait_ids: Iterable[str],
    trait_definitions: Iterable[dict[str, Any]],
    target: str,
) -> TraitEffectResult:
    """Combine explicit trait effects for one calculation target."""
    definitions_by_id = {
        definition["id"]: definition
        for definition in trait_definitions
    }
    combined_modifier = 1.0
    contributing_trait_ids: list[str] = []

    for trait_id in trait_ids:
        if trait_id not in definitions_by_id:
            raise ValueError(
                f"Cannot resolve unknown trait '{trait_id}'."
            )
        trait_definition = definitions_by_id[trait_id]
        for effect in trait_definition.get("effects", []):
            if effect["target"] != target:
                continue
            combined_modifier *= effect["modifier"]
            contributing_trait_ids.append(trait_id)

    return TraitEffectResult(
        target=target,
        modifier=combined_modifier,
        contributing_trait_ids=tuple(
            contributing_trait_ids
        ),
    )


def resolve_animal_trait_effect(
    animal_definition: dict[str, Any],
    taxon_definitions: Iterable[dict[str, Any]],
    trait_definitions: Iterable[dict[str, Any]],
    target: str,
) -> TraitEffectResult:
    """Resolve one effect from an animal's effective trait set."""
    trait_ids = resolve_animal_trait_ids(
        animal_definition,
        taxon_definitions,
    )
    return resolve_trait_effect(
        trait_ids,
        trait_definitions,
        target,
    )
