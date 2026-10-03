import re
from math import isfinite
from pathlib import Path
from typing import Any

REQUIRED_IDENTITY_FIELDS = (
    "entity_type",
    "id",
    "name",
)
REQUIRED_HABITAT_FIELDS =(
    "description",
    "movement_medium",
    "conditions",
)
REQUIRED_HABITAT_CONDITION_FIELDS = (
    "openness",
    "vegetation_density",
    "ground_firmness",
    "shelter_availability",
    "terrain_ruggedness",
)
SUPPORTED_HABITAT_MOVEMENT_MEDIA = frozenset(
    {
        "terrestrial"
    }
)
REQUIRED_PRODUCER_FIELDS = (
    "production",
)
REQUIRED_RESOURCE_FIELDS = (
    "quantity_type",
    "unit",
)
REQUIRED_REGION_FIELDS = (
    "habitat_ids",
)
REQUIRED_TAXON_FIELDS = (
    "rank",
    "parent_taxon_id",
)
REQUIRED_TRAIT_FIELDS = (
    "description",
)
REQUIRED_TRAIT_EFFECT_FIELDS = (
    "target",
    "modifier",
)
SUPPORTED_TRAIT_EFFECT_TARGETS = frozenset(
    {
        "detection",
        "stealth",
        "escape_mobility",
        "counterattack_power",
        "restraint",
        "restraint_resistance",
        "bite_effectiveness",
        "grapple_effectiveness",
    }
)
SUPPORTED_TAXONOMIC_RANKS = frozenset(
    {
        "kingdom",
        "phylum",
        "class",
        "order",
        "family",
        "genus",
        "species",
    }
)
REQUIRED_PRODUCTION_ENTRY_FIELDS = (
    "resource_id",
    "amount_per_producer_per_day",
)
REQUIRED_ANIMAL_FIELDS = (
    "diet_type",
    "food_requirement_per_animal_per_cycle",
    "birth_rate_per_animal_per_cycle",
    "diet",
)
REQUIRED_ANIMAL_STATISTIC_FIELDS = (
    "power",
    "defense",
    "health",
    "mobility",
    "perception",
    "stealth",
    "intelligence",
)
REQUIRED_ANIMAL_DIET_ENTRY_FIELDS = (
    "resource_id",
    "preference",
)
SUPPORTED_ENTITY_TYPES = frozenset(
    {
        "animal",
        "habitat",
        "producer",
        "region",
        "resource",
        "taxon",
        "temperament",
        "trait",
        "weather",
    }
)
SUPPORTED_RESOURCE_MEASUREMENTS = {
    "biomass": frozenset({"kg"}),
}
SUPPORTED_ANIMAL_DIET_TYPES = frozenset(
    {
        "herbivore",
        "omnivore",
    }
)
SUPPORTED_ANIMAL_ACTIVITY_PATTERNS = frozenset(
    {
        "diurnal",
        "nocturnal",
        "crepuscular",
        "flexible",
    }
)
SUPPORTED_ANIMAL_BODY_SIZE_CATEGORIES = frozenset(
    {
        "very_small",
        "small",
        "medium",
        "large",
        "very_large",
    }
)
SUPPORTED_ANIMAL_MOVEMENT_MODES = frozenset(
    {
        "terrestrial",
        "flight",
    }
)
SUPPORTED_ANIMAL_FLIGHT_CAPABILITIES = frozenset(
    {
        "short_burst",
        "powered",
        "soaring",
    }
)
ENTITY_ID_PATTERN = re.compile(
    r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*"
)


def _validate_preferred_habitat_ids(
    definition: dict[str, Any],
    source_path: Path,
) -> None:
    """Validate an optional ordered list of preferred habitat IDs."""
    if "preferred_habitat_ids" not in definition:
        return
    preferred_habitat_ids = definition["preferred_habitat_ids"]
    entity_type = definition["entity_type"]
    if not isinstance(preferred_habitat_ids, list):
        raise TypeError(
            f"Field 'preferred_habitat_ids' in {entity_type} "
            f"definition '{source_path}' must be a list."
        )
    if not preferred_habitat_ids:
        raise ValueError(
            f"Field 'preferred_habitat_ids' in {entity_type} "
            f"definition '{source_path}' must not be empty."
        )
    seen_habitat_ids: set[str] = set()
    for entry_index, habitat_id in enumerate(preferred_habitat_ids):
        if not isinstance(habitat_id, str):
            raise TypeError(
                f"Field 'preferred_habitat_ids' entry {entry_index} "
                f"in {entity_type} definition '{source_path}' must "
                "be a string."
            )
        if not habitat_id.strip():
            raise ValueError(
                f"Field 'preferred_habitat_ids' entry {entry_index} "
                f"in {entity_type} definition '{source_path}' must "
                "not be empty."
            )
        if ENTITY_ID_PATTERN.fullmatch(habitat_id) is None:
            raise ValueError(
                f"Field 'preferred_habitat_ids' entry {entry_index} "
                f"in {entity_type} definition '{source_path}' must "
                "use lowercase snake_case."
            )
        if habitat_id in seen_habitat_ids:
            raise ValueError(
                f"Field 'preferred_habitat_ids' in {entity_type} "
                f"definition '{source_path}' contains duplicate "
                f"habitat id '{habitat_id}'."
            )
        seen_habitat_ids.add(habitat_id)


def validate_entity_definition(
        definition: dict[str, Any],
        source_path: Path,
) -> None:
    """Validate one content definition's fields and internal structure."""
    missing_fields = [
        field
        for field in REQUIRED_IDENTITY_FIELDS
        if field not in definition
    ]
    if missing_fields:
        field_list = ", ".join(missing_fields)
        raise ValueError(
            f"Definition '{source_path}' is missing required "
            f"field(s): {field_list}."
        )
    for field in REQUIRED_IDENTITY_FIELDS:
        field_value = definition[field]
        if not isinstance(field_value, str):
            raise TypeError(
                f"Field '{field}' in definition '{source_path}' "
                f"must be a string."
            )
        if not field_value.strip():
            raise ValueError(
                f"Field '{field}' in definition '{source_path}' "
                f"must not be empty."
            )
    entity_type = definition["entity_type"]
    if entity_type not in SUPPORTED_ENTITY_TYPES:
        raise ValueError(
            f"Definition '{source_path}' has unsupported "
            f"entity type '{entity_type}'."
        )
    if entity_type == "temperament":
        missing_temperament_fields = [
            field
            for field in ("description", "action_weights")
            if field not in definition
        ]
        if missing_temperament_fields:
            field_list = ", ".join(missing_temperament_fields)
            raise ValueError(
                f"Temperament definition '{source_path}' is missing "
                f"required field(s): {field_list}."
            )
        description = definition["description"]
        if not isinstance(description, str):
            raise TypeError(
                f"Field 'description' in temperament definition "
                f"'{source_path}' must be a string."
            )
        if not description.strip():
            raise ValueError(
                f"Field 'description' in temperament definition "
                f"'{source_path}' must not be empty."
            )
        action_weights = definition["action_weights"]
        if not isinstance(action_weights, dict):
            raise TypeError(
                f"Field 'action_weights' in temperament definition "
                f"'{source_path}' must be an object."
            )
        for action, weight in action_weights.items():
            if isinstance(weight, bool) or not isinstance(
                weight,
                (int, float)
            ):
                raise TypeError(
                    f"Field 'action_weights' weight for action '{action}' "
                    f"in temperament definition '{source_path}' "
                    f"must be a number."
                )
            if not isfinite(weight):
                raise ValueError(
                    f"Field 'action_weights' weight for action '{action}' "
                    f"in temperament definition '{source_path}' "
                    f"must be finite."
                )
            if weight <= 0:
                raise ValueError(
                    f"Field 'action_weights' weight for action '{action}' "
                    f"in temperament definition '{source_path}' "
                    f"must be greater than zero."
                )
    if entity_type == "animal":
        missing_animal_fields = [
            field
            for field in REQUIRED_ANIMAL_FIELDS
            if field not in definition
        ]
        if missing_animal_fields:
            field_list = ", ".join(missing_animal_fields)
            raise ValueError(
                f"Animal definition '{source_path}' is missing "
                f"required field(s): {field_list}."
            )
        if "temperament" in definition:
            temperament = definition["temperament"]
            if not isinstance(temperament, dict):
                raise TypeError(
                    f"Field 'temperament' in animal definition "
                    f"'{source_path}' must be an object."
                )
            for action, weight in temperament.items():
                if isinstance(weight, bool) or not isinstance(
                    weight,
                    (int, float)
                ):
                    raise TypeError(
                        f"Field 'temperament' weight for action '{action}' "
                        f"in animal definition '{source_path}' "
                        f"must be a number."
                    )
                if not isfinite(weight):
                    raise ValueError(
                        f"Field 'temperament' weight for action '{action}' "
                        f"in animal definition '{source_path}' "
                        f"must be finite."
                    )
                if weight <= 0:
                    raise ValueError(
                        f"Field 'temperament' weight for action '{action}' "
                        f"in animal definition '{source_path}' "
                        f"must be greater than zero."
                    )
        if "taxon_id" in definition:
            taxon_id = definition["taxon_id"]
            if not isinstance(taxon_id, str):
                raise TypeError(
                    f"Field 'taxon_id' in animal definition "
                    f"'{source_path}' must be a string."
                )
            if not taxon_id.strip():
                raise ValueError(
                    f"Field 'taxon_id' in animal definition "
                    f"'{source_path}' must not be empty."
                )
            if ENTITY_ID_PATTERN.fullmatch(taxon_id) is None:
                raise ValueError(
                    f"Field 'taxon_id' in animal definition "
                    f"'{source_path}' must use lowercase snake_case."
                )
        if "body_size_category" in definition:
            body_size_category = definition[
                "body_size_category"
            ]
            if not isinstance(body_size_category, str):
                raise TypeError(
                    f"Field 'body_size_category' in animal "
                    f"definition '{source_path}' must be a string."
                )
            if not body_size_category.strip():
                raise ValueError(
                    f"Field 'body_size_category' in animal "
                    f"definition '{source_path}' must not be empty."
                )
            if (
                body_size_category
                not in SUPPORTED_ANIMAL_BODY_SIZE_CATEGORIES
            ):
                raise ValueError(
                    f"Animal definition '{source_path}' has "
                    f"unsupported body size category "
                    f"'{body_size_category}'."
                )
        if "weight_class" in definition:
            raise ValueError(
                f"Field 'weight_class' in definition "
                f"'{source_path}' must not be defined; weight "
                "class is derived from typical_adult_mass_kg."
            )
        if "typical_adult_mass_kg" in definition:
            typical_adult_mass_kg = definition[
                "typical_adult_mass_kg"
            ]
            if isinstance(
                typical_adult_mass_kg,
                bool,
            ) or not isinstance(
                typical_adult_mass_kg,
                (int, float),
            ):
                raise TypeError(
                    f"Field 'typical_adult_mass_kg' in animal "
                    f"definition '{source_path}' must be a number."
                )
            if not isfinite(typical_adult_mass_kg):
                raise ValueError(
                    f"Field 'typical_adult_mass_kg' in animal "
                    f"definition '{source_path}' must be finite."
                )
            if typical_adult_mass_kg <= 0:
                raise ValueError(
                    f"Field 'typical_adult_mass_kg' in animal "
                    f"definition '{source_path}' must be "
                    "greater than zero."
                )
        _validate_preferred_habitat_ids(definition, source_path)
        if "primary_movement_mode" in definition:
            primary_movement_mode = definition[
                "primary_movement_mode"
            ]
            if not isinstance(primary_movement_mode, str):
                raise TypeError(
                    f"Field 'primary_movement_mode' in animal "
                    f"definition '{source_path}' must be a string."
                )
            if not primary_movement_mode.strip():
                raise ValueError(
                    f"Field 'primary_movement_mode' in animal "
                    f"definition '{source_path}' must not be empty."
                )
            if (
                primary_movement_mode
                not in SUPPORTED_ANIMAL_MOVEMENT_MODES
            ):
                raise ValueError(
                    f"Animal definition '{source_path}' has unsupported "
                    f"primary movement mode "
                    f"'{primary_movement_mode}'."
                )
        if "available_movement_modes" in definition:
            available_movement_modes = definition[
                "available_movement_modes"
            ]
            if not isinstance(available_movement_modes, list):
                raise TypeError(
                    f"Field 'available_movement_modes' in animal "
                    f"definition '{source_path}' must be a list."
                )
            if not available_movement_modes:
                raise ValueError(
                    f"Field 'available_movement_modes' in animal "
                    f"definition '{source_path}' must not be empty."
                )
            seen_movement_modes: set[str] = set()
            for entry_index, movement_mode in enumerate(
                available_movement_modes
            ):
                if not isinstance(movement_mode, str):
                    raise TypeError(
                        f"Field 'available_movement_modes' entry "
                        f"'{source_path}' must be a string."
                    )
                if not movement_mode.strip():
                    raise ValueError(
                        f"Field 'available_movement_modes' entry "
                        f"{entry_index} in animal definition "
                        f"'{source_path}' must not be empty."
                    )
                if (
                    movement_mode
                    not in SUPPORTED_ANIMAL_MOVEMENT_MODES
                ):
                    raise ValueError(
                        f"Animal definition '{source_path}' has "
                        f"unsupported available movement mode "
                        f"'{movement_mode}'."
                    )
                if movement_mode in seen_movement_modes:
                    raise ValueError(
                        f"Field 'available_movement_modes' in animal "
                        f"definition '{source_path}' contains duplicate "
                        f"movement mode '{movement_mode}'."
                    )
                seen_movement_modes.add(movement_mode)
            if (
                "primary_movement_mode" in definition
                and definition["primary_movement_mode"]
                not in seen_movement_modes
            ):
                raise ValueError(
                    f"Field 'primary_movement_mode' in animal "
                    f"definition '{source_path}' must also appear in "
                    "'available_movement_modes'."
                )
            if "flight_capabilities" in definition:
                flight_capabilities = definition[
                    "flight_capabilities"
                ]
                if not isinstance(flight_capabilities, list):
                    raise TypeError(
                        f"Field 'flight_capabilities' in animal "
                        f"definition '{source_path}' must be a list."
                    )
                if not flight_capabilities:
                    raise ValueError(
                        f"Field 'flight_capabilities' in animal "
                        f"definition '{source_path}' must not be empty."
                    )
                if (
                    "available_movement_modes" not in definition
                    or "flight"
                    not in definition["available_movement_modes"]
                ):
                    raise ValueError(
                        f"Animal definition '{source_path}' cannot definite "
                        f"'flight_capabilities' without including 'flight' "
                        "in 'available_movement_modes."
                    )
                seen_flight_capabilties: set[str] = set()
                for entry_index, capability in enumerate(
                    flight_capabilities
                ):
                    if not isinstance(capability, str):
                        raise TypeError(
                            f"Field 'flight_capabilities' entry "
                            f"{entry_index} in animal definition "
                            f"'{source_path}' must be a string."
                        )
                    if not capability.strip():
                        raise ValueError(
                            f"Field 'flight_capabilities' entry "
                            f"{entry_index} in animal definition "
                            f"'{source_path}' must not be empty."
                        )
                    if (
                        capability
                        not in SUPPORTED_ANIMAL_FLIGHT_CAPABILITIES
                    ):
                        raise ValueError(
                            f"Animal definition '{source_path}' has "
                            f"unsupported flight capability "
                            f"'{capability}'."
                        )
                    seen_flight_capabilties.add(capability)
        if "statistics" in definition:
            statistics = definition["statistics"]
            if not isinstance(statistics, dict):
                raise TypeError(
                    f"Field 'statistics' in animal definition "
                    f"'{source_path}' must be an object."
                )
            missing_statistic_fields = [
                field
                for field in REQUIRED_ANIMAL_STATISTIC_FIELDS
                if field not in statistics
            ]
            if missing_statistic_fields:
                field_list = ", ".join(
                    missing_statistic_fields
                )
                raise ValueError(
                    f"Field 'statistics' in animal definition "
                    f"'{source_path}' is missing required "
                    f"field(s): {field_list}."
                )
            for statistic_field in REQUIRED_ANIMAL_STATISTIC_FIELDS:
                statistic_value = statistics[statistic_field]
                if isinstance(
                    statistic_value,
                    bool,
                ) or not isinstance(
                    statistic_value,
                    (int, float),
                ):
                    raise TypeError(
                        f"Field 'statistics.{statistic_field}' "
                        f"in animal definition '{source_path}' "
                        "must be a number."
                    )
                if not isfinite(statistic_value):
                    raise ValueError(
                        f"Field 'statistics.{statistic_field}' "
                        f"in animal definition '{source_path}' "
                        "must be finite."
                    )
                unsupported_statistic_fields = [
                    field
                    for field in statistics
                    if field not in REQUIRED_ANIMAL_STATISTIC_FIELDS
                ]
                if unsupported_statistic_fields:
                    field_list = ", ".join(
                        unsupported_statistic_fields
                    )
                    raise ValueError(
                        f"Field 'statistics' in animal definition "
                        f"'{source_path}' contains unsupported "
                        f"field(s): {field_list}."
                    )
                if statistic_value < 0:
                    raise ValueError(
                        f"Field 'statistics.{statistic_field}' "
                        f"in animal definition '{source_path}' "
                        "must not be negative."
                    )
                if statistic_value > 10:
                    raise ValueError(
                        f"Field 'statistics.{statistic_field}' "
                        f"in animal definition '{source_path}' "
                        "must not be greater than 10."
                    )
        if "trait_ids" in definition:
            trait_ids = definition["trait_ids"]
            if not isinstance(trait_ids, list):
                raise TypeError(
                    f"Field 'trait_ids' in animal definition "
                    f"'{source_path}' must be a list."
                )
            seen_trait_ids: set[str] = set()
            for entry_index, trait_id in enumerate(trait_ids):
                if not isinstance(trait_id, str):
                    raise TypeError(
                        f"Field 'trait_ids' entry {entry_index} "
                        f"in animal definition '{source_path}' "
                        "must be a string."
                    )
                if not trait_id.strip():
                    raise ValueError(
                        f"Field 'trait_ids' entry {entry_index} "
                        f"in animal definition '{source_path}' "
                        "must not be empty."
                    )
                if ENTITY_ID_PATTERN.fullmatch(trait_id) is None:
                    raise ValueError(
                        f"Field 'trait_ids' entry {entry_index} "
                        f"in animal definition '{source_path}' "
                        "must use lowercase snake_case."
                    )
                if trait_id in seen_trait_ids:
                    raise ValueError(
                        f"Field 'trait_ids' in animal definition "
                        f"'{source_path}' contains duplicate "
                        f"trait id '{trait_id}'."
                    )
                seen_trait_ids.add(trait_id)
        if "excluded_trait_ids" in definition:
            excluded_trait_ids = definition["excluded_trait_ids"]
            if not isinstance(excluded_trait_ids, list):
                raise TypeError(
                    f"Field 'excluded_trait_ids' in animal "
                    f"definition '{source_path}' must be a list."
                )
            seen_excluded_trait_ids: set[str] = set()
            for entry_index, trait_id in enumerate(
                excluded_trait_ids
            ):
                if not isinstance(trait_id, str):
                    raise TypeError(
                        f"Field 'excluded_trait_ids' entry "
                        f"{entry_index} in animal definition "
                        f"'{source_path}' must be a string."
                    )
                if not trait_id.strip():
                    raise ValueError(
                        f"Field 'excluded_trait_ids' entry "
                        f"{entry_index} in animal definition "
                        f"'{source_path}' must not be empty."
                    )
                if ENTITY_ID_PATTERN.fullmatch(trait_id) is None:
                    raise ValueError(
                        f"Field 'excluded_trait_ids' entry "
                        f"{entry_index} in animal definition "
                        f"'{source_path}' must use lowercase "
                        "snake_case."
                    )
                if trait_id in seen_excluded_trait_ids:
                    raise ValueError(
                        f"Field 'excluded_trait_ids' in animal "
                        f"definition '{source_path}' contains "
                        f"duplicate trait id '{trait_id}'."
                    )
                if (
                    "trait_ids" in definition
                    and trait_id in definition["trait_ids"]
                ):
                    raise ValueError(
                        f"Trait id '{trait_id}' in animal "
                        f"definition '{source_path}' cannot appear "
                        "in both trait_ids and excluded_trait_ids."
                    )
                seen_excluded_trait_ids.add(trait_id)
        diet_type = definition["diet_type"]
        if not isinstance(diet_type, str):
            raise TypeError(
                f"Field 'diet_type' in animal definition "
                f"'{source_path}' must be a string."
            )
        if not diet_type.strip():
            raise ValueError(
                f"Field 'diet_type' in animal definition "
                f"'{source_path}' must not be empty."
            )
        if diet_type not in SUPPORTED_ANIMAL_DIET_TYPES:
            raise ValueError(
                f"Animal definition '{source_path}' has unsupported "
                f"diet type '{diet_type}'."
            )
        if "activity_pattern" in definition:
            activity_pattern = definition["activity_pattern"]
            if not isinstance(activity_pattern, str):
                raise TypeError(
                    f"Field 'activity_pattern' in animal definition"
                    f"'{source_path}' must be a string."
                )
            if not activity_pattern.strip():
                raise ValueError(
                    f"Field 'activity_pattern' in animal definition "
                    f"'{source_path}' must not be empty."
                )
            if (
                activity_pattern
                not in SUPPORTED_ANIMAL_ACTIVITY_PATTERNS
            ):
                raise ValueError(
                    f"Animal definition '{source_path}' has unsupported "
                    f"activity pattern '{activity_pattern}'."
                )
        food_requirement = definition[
            "food_requirement_per_animal_per_cycle"
        ]
        if isinstance(food_requirement, bool) or not isinstance(
            food_requirement,
            (int, float),
        ):
            raise TypeError(
                f"Field 'food_requirement_per_animal_per_cycle' in "
                f"animal definition '{source_path}' must be a number."
            )
        if not isfinite(food_requirement):
            raise ValueError(
                "Field 'food_requirement_per_animal_per_cycle' in "
                f"animal definition '{source_path}' must be finite."
            )
        if food_requirement <= 0:
            raise ValueError(
                f"Field 'food_requirement_per_animal_per_cycle' in "
                f"animal definition '{source_path}' must be greater than zero."
            )
        birth_rate = definition[
            "birth_rate_per_animal_per_cycle"
        ]
        if isinstance(birth_rate, bool) or not isinstance(
            birth_rate,
            (int, float),
        ):
            raise TypeError(
                "Field 'birth_rate_per_animal_per_cycle' in "
                f"animal definition '{source_path}' must be a number."
            )
        if not isfinite(birth_rate):
            raise ValueError(
                "Field 'birth_rate_per_animal_per_cycle' in "
                f"animal definition '{source_path}' must be finite."
            )
        if birth_rate < 0:
            raise ValueError(
                "Field 'birth_rate_per_animal_per_cycle' in "
                f"animal definition '{source_path}' must not be negative."
            )
        diet = definition["diet"]
        if not isinstance(diet, list):
            raise TypeError(
                f"Field 'diet' in animal definition "
                f"'{source_path}' must be a list."
            )
        if not diet:
            raise ValueError(
                f"Field 'diet' in animal definition "
                f"'{source_path}' must not be empty."
            )
        seen_resource_ids: set[str] = set()
        for entry_index, diet_entry in enumerate(diet):
            if not isinstance(diet_entry, dict):
                raise TypeError(
                    f"Animal diet entry {entry_index} in definition "
                    f"'{source_path}' must be an object."
                )
            missing_diet_entry_fields = [
                field
                for field in REQUIRED_ANIMAL_DIET_ENTRY_FIELDS
                if field not in diet_entry
            ]
            if missing_diet_entry_fields:
                field_list = ", ".join(
                    missing_diet_entry_fields
                )
                raise ValueError(
                    f"Animal diet entry {entry_index} in definition "
                    f"'{source_path}' is missing required field(s): "
                    f"{field_list}."
                )
            resource_id = diet_entry["resource_id"]
            if not isinstance(resource_id, str):
                raise TypeError(
                    f"Field 'resource_id' in animal diet entry "
                    f"{entry_index} of definition '{source_path}' "
                    f"must be a string."
                )
            if not resource_id.strip():
                raise ValueError(
                    f"Field 'resource_id' in animal diet entry "
                    f"{entry_index} of definition '{source_path}' "
                    f"must not be empty."
                )
            if ENTITY_ID_PATTERN.fullmatch(resource_id) is None:
                raise ValueError(
                    f"Field 'resource_id' in animal diet entry "
                    f"{entry_index} of definition '{source_path}' "
                    f"must use lowercase snake_case."
                )
            if resource_id in seen_resource_ids:
                raise ValueError(
                    f"Duplicate diet resource '{resource_id}' in "
                    f"animal definition '{source_path}'."
                )
            seen_resource_ids.add(resource_id)
            preference = diet_entry["preference"]
            if isinstance(preference, bool) or not isinstance(
                preference,
                (int, float),
            ):
                raise TypeError(
                    f"Field 'preference' in animal diet entry "
                    f"{entry_index} of definition '{source_path}' "
                    f"must be a number."
                )
            if not isfinite(preference):
                raise ValueError(
                    f"Field 'preference' in animal diet entry "
                    f"{entry_index} of definition '{source_path}' "
                    "must be finite."
                )
            if preference <= 0:
                raise ValueError(
                    f"Field 'preference' in animal diet entry "
                    f"{entry_index} of definition '{source_path}' "
                    f"must be greater than zero."
                )
    if entity_type == "trait":
        missing_trait_fields = [
            field
            for field in REQUIRED_TRAIT_FIELDS
            if field not in definition
        ]
        if missing_trait_fields:
            field_list = ", ".join(
                missing_trait_fields
            )
            raise ValueError(
                f"Trait definitions '{source_path}' is missing "
                f"required field(s): {field_list}."
            )
        description = definition["description"]
        if not isinstance(description, str):
            raise TypeError(
                f"Field 'description' in trait definition "
                f"'{source_path}' must be a string."
            )
        if not description.strip():
            raise ValueError(
                f"Field 'description' in trait definition "
                f"'{source_path}' must not be empty."
            )
        if "action_capabilities" in definition:
            action_capabilities = definition["action_capabilities"]
            if not isinstance(action_capabilities, list):
                raise TypeError(
                    f"Field 'action_capabilities' in trait definition "
                    f"'{source_path}' must be a list."
                )
            seen_capabilities: set[str] = set()
            for entry_index, capability in enumerate(action_capabilities):
                if not isinstance(capability, str):
                    raise TypeError(
                        f"Field 'action_capabilities' entry {entry_index} "
                        f"in trait definition '{source_path}' "
                        "must be a string."
                    )
                if not capability.strip():
                    raise ValueError(
                        f"Field 'action_capabilities' entry {entry_index} "
                        f"in trait definition '{source_path}' "
                        "must not be empty."
                    )
                if ENTITY_ID_PATTERN.fullmatch(capability) is None:
                    raise ValueError(
                        f"Field 'action_capabilities' entry {entry_index} "
                        f"in trait definition '{source_path}' "
                        "must use lowercase snake_case."
                    )
                if capability in seen_capabilities:
                    raise ValueError(
                        f"Field 'action_capabilities' in trait definition "
                        f"'{source_path}' contains duplicate "
                        f" action capability '{capability}'."
                    )
                seen_capabilities.add(capability)
        if "tags" in definition:
            tags = definition["tags"]
            if not isinstance(tags, list):
                raise TypeError(
                    f"Field 'tags' in trait definition "
                    f"'{source_path}' must be a list."
                )
            seen_tags: set[str] = set()
            for entry_index, tag in enumerate(tags):
                if not isinstance(tag, str):
                    raise TypeError(
                        f"Field 'tags' entry {entry_index} "
                        f"in trait definition '{source_path}' "
                        "must be a string."
                    )
                if not tag.strip():
                    raise ValueError(
                        f"Field 'tags' entry {entry_index} "
                        f"in trait definition '{source_path}' "
                        "must not be empty."
                    )
                if ENTITY_ID_PATTERN.fullmatch(tag) is None:
                    raise ValueError(
                        f"Field 'tags' entry {entry_index} "
                        f"in trait definition '{source_path}' "
                        "must use lowercase snake_case."
                    )
                if tag in seen_tags:
                    raise ValueError(
                        f"Field 'tags' in trait definition "
                        f"'{source_path}' contains duplicate "
                        f" tag '{tag}'."
                    )
                seen_tags.add(tag)
        if "effects" in definition:
            effects = definition["effects"]
            if not isinstance(effects, list):
                raise TypeError(
                    f"Field 'effects' in trait definition "
                    f"'{source_path}' must be a list."
                )
            if not effects:
                raise ValueError(
                    f"Field 'effects' in trait definition "
                    f"'{source_path}' must not be empty."
                )

            seen_effect_targets: set[str] = set()
            for entry_index, effect in enumerate(effects):
                if not isinstance(effect, dict):
                    raise TypeError(
                        f"Trait effect entry {entry_index} in "
                        f"definition '{source_path}' must be an object."
                    )
                missing_effect_fields = [
                    field
                    for field in REQUIRED_TRAIT_EFFECT_FIELDS
                    if field not in effect
                ]
                if missing_effect_fields:
                    field_list = ", ".join(
                        missing_effect_fields
                    )
                    raise ValueError(
                        f"Trait effect entry {entry_index} in "
                        f"definition '{source_path}' is missing "
                        f"required field(s): {field_list}."
                    )

                target = effect["target"]
                if not isinstance(target, str):
                    raise TypeError(
                        f"Field 'target' in trait effect entry "
                        f"{entry_index} of definition "
                        f"'{source_path}' must be a string."
                    )
                if target not in SUPPORTED_TRAIT_EFFECT_TARGETS:
                    raise ValueError(
                        f"Trait definition '{source_path}' has "
                        f"unsupported effect target '{target}'."
                    )
                if target in seen_effect_targets:
                    raise ValueError(
                        f"Field 'effects' in trait definition "
                        f"'{source_path}' contains duplicate target "
                        f"'{target}'."
                    )
                seen_effect_targets.add(target)

                modifier = effect["modifier"]
                if isinstance(modifier, bool) or not isinstance(
                    modifier,
                    (int, float),
                ):
                    raise TypeError(
                        f"Field 'modifier' for trait effect target "
                        f"'{target}' in definition '{source_path}' "
                        "must be a number."
                    )
                if not isfinite(modifier):
                    raise ValueError(
                        f"Field 'modifier' for trait effect target "
                        f"'{target}' in definition '{source_path}' "
                        "must be finite."
                    )
                if modifier <= 0:
                    raise ValueError(
                        f"Field 'modifier' for trait effect target "
                        f"'{target}' in definition '{source_path}' "
                        "must be greater than zero."
                    )
    if entity_type == "taxon":
        missing_taxon_fields = [
            field
            for field in REQUIRED_TAXON_FIELDS
            if field not in definition
        ]
        if missing_taxon_fields:
            field_list = ", ".join(
                missing_taxon_fields
            )
            raise ValueError(
                f"Taxon definition '{source_path}' is missing "
                f"required field(s): {field_list}."
            )
        taxon_rank = definition["rank"]
        if not isinstance(taxon_rank, str):
            raise TypeError(
                f"Field 'rank' in taxon definition "
                f"'{source_path}' must be a string."
            )
        if not taxon_rank.strip():
            raise ValueError(
                f"Field 'rank' in taxon definition "
                f"'{source_path}' must not be empty."
            )
        if taxon_rank not in SUPPORTED_TAXONOMIC_RANKS:
            raise ValueError(
                f"Taxon definition '{source_path}' has unsupported "
                f"taxonomic rank '{taxon_rank}'."
            )
        parent_taxon_id = definition["parent_taxon_id"]
        if parent_taxon_id is not None and not isinstance(parent_taxon_id, str):
            raise TypeError(
                f"Field 'parent_taxon_id' in taxon definition "
                f"'{source_path}' must be a string or null."
            )
        if (
            isinstance(parent_taxon_id, str)
            and not parent_taxon_id.strip()
        ):
            raise ValueError(
                f" Field 'parent_taxon_id' in taxon definition "
                f"'{source_path}' must not be empty."
            )
        if (
            isinstance(parent_taxon_id, str)
            and ENTITY_ID_PATTERN.fullmatch(parent_taxon_id) is None
        ):
            raise ValueError(
                f"Field 'parent_taxon_id' in taxon definition "
                f"'{source_path}' must use lowercase snake_case."
            )
        if parent_taxon_id == definition["id"]:
            raise ValueError(
                f"Field 'parent_taxon_id' in taxon definition "
                f"'{source_path}' must not reference itself."
            )
        if "default_trait_ids" in definition:
            default_trait_ids = definition["default_trait_ids"]
            seen_default_trait_ids: set[str] = set()
            if not isinstance(default_trait_ids, list):
                raise TypeError(
                    f"Field 'default_trait_ids' in taxon definition "
                    f"'{source_path}' must be a list."
                )
            for entry_index, trait_id in enumerate(
                default_trait_ids
            ):
                if not isinstance(trait_id, str):
                    raise TypeError(
                        f"Field 'default_trait_ids' entry "
                        f"{entry_index} in taxon definition "
                        f"'{source_path}' must be a string."
                    )
                if not trait_id.strip():
                    raise ValueError(
                        f"Field 'default_trait_ids' entry "
                        f"{entry_index} in taxon definition "
                        f"'{source_path}' must not be empty."
                    )
                if ENTITY_ID_PATTERN.fullmatch(trait_id) is None:
                    raise ValueError(
                        f"Field 'default_trait_ids' entry "
                        f"{entry_index} in taxon definition "
                        f"'{source_path}' must use lowercase "
                        "snake_case."
                    )
                if trait_id in seen_default_trait_ids:
                    raise ValueError(
                        f"Field 'default_trait_ids' in taxon "
                        f"definition '{source_path}' contains "
                        f"duplicate trait id '{trait_id}'."
                    )
                seen_default_trait_ids.add(trait_id)
    if entity_type == "habitat":
        missing_habitat_fields = [
            field
            for field in REQUIRED_HABITAT_FIELDS
            if field not in definition
        ]
        if missing_habitat_fields:
            field_list = ", ".join(
                missing_habitat_fields
            )
            raise ValueError(
                f"Habitat definition '{source_path}' is missing "
                f"required field(s): {field_list}."
            )
        description = definition["description"]
        if not isinstance(description, str):
            raise TypeError(
                f"Field 'description' in habitat definition "
                f"'{source_path}' must be a string."
            )
        if not description.strip():
            raise ValueError(
                f"Field 'description' in habitat definition "
                f"'{source_path}' must not be empty."
            )
        movement_medium = definition["movement_medium"]
        if not isinstance(movement_medium, str):
            raise TypeError(
                f"Field 'movement_medium' in habitat definition "
                f"'{source_path}' must be a string."
            )
        if not movement_medium.strip():
            raise ValueError(
                f"Field 'movement_medium' in habitat definition "
                f"'{source_path}' must not be empty."
            )
        if (
            movement_medium
            not in SUPPORTED_HABITAT_MOVEMENT_MEDIA
        ):
            raise ValueError(
                f"Habitat definition '{source_path}' has "
                f"unsupported movement medium "
                f"'{movement_medium}'."
            )
        if "movement_modifiers" in definition:
            movement_modifiers = definition[
                "movement_modifiers"
            ]
            if not isinstance(movement_modifiers, dict):
                raise TypeError(
                    f"Field 'movement_modifiers' in habitat "
                    f"definition '{source_path}' must be an object."
                )
            if not movement_modifiers:
                raise ValueError(
                    f"Field 'movement_modifiers' in habitat "
                    f"definition '{source_path}' must not be empty."
                )

            for movement_mode, modifier in (
                movement_modifiers.items()
            ):
                if (
                    movement_mode
                    not in SUPPORTED_ANIMAL_MOVEMENT_MODES
                ):
                    raise ValueError(
                        f"Habitat definition '{source_path}' has "
                        f"unsupported movement modifier mode "
                        f"'{movement_mode}'."
                    )
                if isinstance(modifier, bool) or not isinstance(
                    modifier,
                    (int, float),
                ):
                    raise TypeError(
                        f"Movement modifier for mode "
                        f"'{movement_mode}' in habitat definition "
                        f"'{source_path}' must be a number."
                    )
                if not isfinite(modifier):
                    raise ValueError(
                        f"Movement modifier for mode "
                        f"'{movement_mode}' in habitat definition "
                        f"'{source_path}' must be finite."
                    )
                if modifier <= 0:
                    raise ValueError(
                        f"Movement modifier for mode "
                        f"'{movement_mode}' in habitat definition "
                        f"'{source_path}' must be greater than zero."
                    )
        conditions = definition["conditions"]
        if not isinstance(conditions, dict):
            raise TypeError(
                f"Field 'conditions' in habitat definition "
                f"'{source_path}' must be an object."
            )
        missing_condition_fields = [
            field
            for field in REQUIRED_HABITAT_CONDITION_FIELDS
            if field not in conditions
        ]
        if missing_condition_fields:
            field_list = ", ".join(
                missing_condition_fields
            )
            raise ValueError(
                f"Field 'conditions' in habitat definition "
                f"'{source_path}' is missing required "
                f"field(s): {field_list}."
            )
        unsupported_condition_fields = [
            field
            for field in conditions
            if field not in REQUIRED_HABITAT_CONDITION_FIELDS
        ]
        if unsupported_condition_fields:
            field_list = ", ".join(
                unsupported_condition_fields
            )
            raise ValueError(
                f"Field 'conditions' in habitat definition "
                f"'{source_path}' contains unsupported "
                f"field(s): {field_list}"
            )
        for condition_field in(
            REQUIRED_HABITAT_CONDITION_FIELDS
        ):
            condition_value = conditions[condition_field]
            if isinstance(
                condition_value,
                bool,
            ) or not isinstance(
                condition_value,
                (int, float),
            ):
                raise TypeError(
                    f"Field 'conditions.{condition_field}' "
                    f"in habitat definition '{source_path}' "
                    "must be a number."
                )
            if not isfinite(condition_value):
                raise ValueError(
                    f"Field 'conditions.{condition_field}' "
                    f"in habitat definition '{source_path}' "
                    "must be finite."
                )
            if not 0.0 <= condition_value <= 1.0:
                raise ValueError(
                    f"Field 'conditions.{condition_field}' "
                    f"in habitat definition '{source_path}' "
                    "must be between 0.0 and 1.0."
                )
    if entity_type == "region":
        missing_region_fields = [
            field
            for field in REQUIRED_REGION_FIELDS
            if field not in definition
        ]
        if missing_region_fields:
            field_list = ", ".join(missing_region_fields)
            raise ValueError(
                f"Region definition '{source_path}' is missing "
                f"required field(s): {field_list}."
            )
        habitat_ids = definition["habitat_ids"]
        if not isinstance(habitat_ids, list):
            raise TypeError(
                f"Field 'habitat_ids' in region definition "
                f"'{source_path}' must be a list."
            )
        if not habitat_ids:
            raise ValueError(
                f"Field 'habitat_ids' in region definition "
                f"'{source_path}' must not be empty."
            )
        seen_habitat_ids: set[str] = set()
        for entry_index, habitat_id in enumerate(habitat_ids):
            if not isinstance(habitat_id, str):
                raise TypeError(
                    f"Field 'habitat_ids' entry {entry_index} "
                    f"in region definition '{source_path}' "
                    "must be a string."
                )
            if not habitat_id.strip():
                raise ValueError(
                    f"Field 'habitat_ids' entry {entry_index} "
                    f"in region definition '{source_path}' "
                    "must not be empty."
                )
            if ENTITY_ID_PATTERN.fullmatch(habitat_id) is None:
                raise ValueError(
                    f"Field 'habitat_ids' entry {entry_index} "
                    f"in region definition '{source_path}' must "
                    "use lowercase snake_case."
                )
            if habitat_id in seen_habitat_ids:
                raise ValueError(
                    f"Field 'habitat_ids' in region definition "
                    f"'{source_path}' contains duplicate habitat "
                    f"id '{habitat_id}'."
                )
            seen_habitat_ids.add(habitat_id)
    if entity_type == "producer":
        _validate_preferred_habitat_ids(definition, source_path)
        missing_producer_fields = [
            field
            for field in REQUIRED_PRODUCER_FIELDS
            if field not in definition
        ]
        if missing_producer_fields:
            field_list = ", ".join(
                missing_producer_fields
            )
            raise ValueError(
                f"Producer definition '{source_path}' is missing "
                f"required field(s): {field_list}."
            )
        production = definition["production"]
        if not isinstance(production, list):
            raise TypeError(
                f"Field 'production' in producer definition "
                f"'{source_path}' must be a list."
            )
        if not production:
            raise ValueError(
                f"Field 'production' in producer definition "
                f"'{source_path}' must not be empty."
            )
        for entry_index, production_entry in enumerate(
            production
        ):
            if not isinstance(production_entry, dict):
                raise TypeError(
                    f"Producer production entry {entry_index} in "
                    f"definition '{source_path}' must be an object."
                )
            missing_entry_fields = [
                field
                for field in REQUIRED_PRODUCTION_ENTRY_FIELDS
                if field not in production_entry
            ]
            if missing_entry_fields:
                field_list = ", ".join(
                    missing_entry_fields
                )
                raise ValueError(
                    f"Producer production entry {entry_index} in "
                    f"definition '{source_path}' is missing required "
                    f"field(s): {field_list}."
                )
            resource_id = production_entry["resource_id"]
            if not isinstance(resource_id, str):
                raise TypeError(
                    f"Field 'resource_id' in producer production "
                    f"entry {entry_index} of definition "
                    f"'{source_path}' must be a string."
                )
            if not resource_id.strip():
                raise ValueError(
                    f"Field 'resource_id' in producer production "
                    f"entry {entry_index} of definition "
                    f"'{source_path}' must not be empty."
                )
            if ENTITY_ID_PATTERN.fullmatch(resource_id) is None:
                raise ValueError(
                    f"Field 'resource_id' in producer production "
                    f"entry {entry_index} of definition "
                    f"'{source_path}' must use lowercase snake_case."
                )
            production_amount = production_entry[
                "amount_per_producer_per_day"
            ]
            if isinstance(production_amount, bool) or not isinstance(
                production_amount,
                (int, float),
            ):
                raise TypeError(
                    f"Field 'amount_per_producer_per_day' in "
                    f"producer production entry {entry_index} of "
                    f"definition '{source_path}' must be a number."
                )
            if not isfinite(production_amount):
                raise ValueError(
                    "Field 'amount_per_producer_per_day' in "
                    f"producer production entry {entry_index} of "
                    f"definition '{source_path}' must be finite."
                )
            if production_amount <= 0:
                raise ValueError(
                    f"Field 'amount_per_producer_per_day' in "
                    f"producer production entry {entry_index} of "
                    f"definition '{source_path}' must be greater than zero."
                )
    if entity_type == "resource":
        missing_resource_fields = [
            field
            for field in REQUIRED_RESOURCE_FIELDS
            if field not in definition
        ]
        if missing_resource_fields:
            field_list = ", ".join(missing_resource_fields)
            raise ValueError(
                f"Resource definition '{source_path}' is missing "
                f"required field(s): {field_list}"
            )
        for field in REQUIRED_RESOURCE_FIELDS:
            field_value = definition[field]
            if not isinstance(field_value, str):
                raise TypeError(
                    f"Resource field '{field}' in definition "
                    f"'{source_path}' must be a string."
                )
            if not field_value.strip():
                raise ValueError(
                    f"Resource field '{field}' in definition "
                    f"'{source_path}' must not be empty."
                )
        quantity_type = definition["quantity_type"]
        if quantity_type not in SUPPORTED_RESOURCE_MEASUREMENTS:
            raise ValueError(
                f"Resource definition '{source_path}' has unsupported "
                f"quantity type '{quantity_type}'."
            )
        unit = definition["unit"]
        supported_units = SUPPORTED_RESOURCE_MEASUREMENTS[quantity_type]
        if unit not in supported_units:
            raise ValueError(
                f"Resource definition '{source_path}' has unsupported "
                f"unit '{unit}' for quantity type '{quantity_type}'."
            )
    if entity_type == "weather":
        production_multiplier = definition.get(
            "producer_production_multiplier",
            1.0,
        )
        if isinstance(production_multiplier, bool) or not isinstance(
            production_multiplier, 
            (int, float),
        ):
            raise TypeError(
                "Field 'producer_production_multiplier' in "
                f"weather definition '{source_path}' must be a number."
            )
        if not isfinite(production_multiplier):
            raise ValueError(
                "Field 'producer_production_multiplier' in "
                f"weather definition '{source_path}' must be finite."
            )
        if production_multiplier < 0:
            raise ValueError(
                "Field 'producer_production_multiplier' in "
                f"weather definition '{source_path}' must not be negative."
            )
        if "visibility_modifier" in definition:
            visibility_modifier = definition[
                "visibility_modifier"
            ]
            if isinstance(
                visibility_modifier,
                bool,
            ) or not isinstance(
                visibility_modifier,
                (int, float),
            ):
                raise TypeError(
                    "Field 'visibility_modifier' in weather "
                    f"definition '{source_path}' must be a number."
                )
            if not isfinite(visibility_modifier):
                raise ValueError(
                    "Field 'visibility_modifier' in weather "
                    f"definition '{source_path}' must be finite."
                )
            if not 0.0 < visibility_modifier <= 1.0:
                raise ValueError(
                    "Field 'visibility_modifier' in weather "
                    f"definition '{source_path}' must be greater "
                    "than zero and at most 1.0."
                )
        if "movement_modifiers" in definition:
            movement_modifiers = definition[
                "movement_modifiers"
            ]
            if not isinstance(movement_modifiers, dict):
                raise TypeError(
                    f"Field 'movement_modifiers' in weather "
                    f"definition '{source_path}' must be an object."
                )
            if not movement_modifiers:
                raise ValueError(
                    f"Field 'movement_modifiers' in weather "
                    f"definition '{source_path}' must not be empty."
                )

            for movement_mode, modifier in (
                movement_modifiers.items()
            ):
                if (
                    movement_mode
                    not in SUPPORTED_ANIMAL_MOVEMENT_MODES
                ):
                    raise ValueError(
                        f"Weather definition '{source_path}' has "
                        f"unsupported movement modifier mode "
                        f"'{movement_mode}'."
                    )
                if isinstance(modifier, bool) or not isinstance(
                    modifier,
                    (int, float),
                ):
                    raise TypeError(
                        f"Movement modifier for mode "
                        f"'{movement_mode}' in weather definition "
                        f"'{source_path}' must be a number."
                    )
                if not isfinite(modifier):
                    raise ValueError(
                        f"Movement modifier for mode "
                        f"'{movement_mode}' in weather definition "
                        f"'{source_path}' must be finite."
                    )
                if modifier <= 0:
                    raise ValueError(
                        f"Movement modifier for mode "
                        f"'{movement_mode}' in weather definition "
                        f"'{source_path}' must be greater than zero."
                    )
        if "flight_capability_modifiers" in definition:
            flight_capability_modifiers = definition[
                "flight_capability_modifiers"
            ]
            if not isinstance(
                flight_capability_modifiers,
                dict,
            ):
                raise TypeError(
                    "Field 'flight_capability_modifiers' in weather "
                    f"definition '{source_path}' must be an object."
                )
            if not flight_capability_modifiers:
                raise ValueError(
                    "Field 'flight_capability_modifiers' in weather "
                    f"definition '{source_path}' must not be empty."
                )

            for capability, modifier in (
                flight_capability_modifiers.items()
            ):
                if (
                    capability
                    not in SUPPORTED_ANIMAL_FLIGHT_CAPABILITIES
                ):
                    raise ValueError(
                        f"Weather definition '{source_path}' has "
                        f"unsupported flight capability modifier "
                        f"'{capability}'."
                    )
                if isinstance(modifier, bool) or not isinstance(
                    modifier,
                    (int, float),
                ):
                    raise TypeError(
                        f"Flight capability modifier for "
                        f"'{capability}' in weather definition "
                        f"'{source_path}' must be a number."
                    )
                if not isfinite(modifier):
                    raise ValueError(
                        f"Flight capability modifier for "
                        f"'{capability}' in weather definition "
                        f"'{source_path}' must be finite."
                    )
                if modifier <= 0:
                    raise ValueError(
                        f"Flight capability modifier for "
                        f"'{capability}' in weather definition "
                        f"'{source_path}' must be greater than zero."
                    )
    entity_id = definition["id"]
    if ENTITY_ID_PATTERN.fullmatch(entity_id) is None:
        raise ValueError(
            f"Field 'id' in definition '{source_path}' "
            f"must use lowercase snake_case."
        )
