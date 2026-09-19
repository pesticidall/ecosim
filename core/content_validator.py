import re
from math import isfinite
from pathlib import Path
from typing import Any

REQUIRED_IDENTITY_FIELDS = (
    "entity_type",
    "id",
    "name",
)
REQUIRED_PRODUCER_FIELDS = (
    "production",
)
REQUIRED_RESOURCE_FIELDS = (
    "quantity_type",
    "unit",
)
REQUIRED_PRODUCTION_ENTRY_FIELDS = (
    "resource_id",
    "amount_per_producer_per_cycle",
)
REQUIRED_ANIMAL_FIELDS = (
    "diet_type",
    "food_requirement_per_animal_per_cycle",
    "birth_rate_per_animal_per_cycle",
    "diet",
)
REQUIRED_ANIMAL_DIET_ENTRY_FIELDS = (
    "resource_id",
    "preference",
)
SUPPORTED_ENTITY_TYPES = frozenset(
    {
        "animal",
        "producer",
        "region",
        "resource",
        "weather",
    }
)
SUPPORTED_RESOURCE_MEASUREMENTS = {
    "biomass": frozenset({"kg"}),
}
SUPPORTED_ANIMAL_DIET_TYPES = frozenset(
    {
        "herbivore",
    }
)
ENTITY_ID_PATTERN = re.compile(
    r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*"
)

def validate_entity_definition(
        definition: dict[str, Any],
        source_path: Path,
) -> None:
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
    if entity_type == "producer":
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
                "amount_per_producer_per_cycle"
            ]
            if isinstance(production_amount, bool) or not isinstance(
                production_amount,
                (int, float),
            ):
                raise TypeError(
                    f"Field 'amount_per_producer_per_cycle' in "
                    f"producer production entry {entry_index} of "
                    f"definition '{source_path}' must be a number."
                )
            if not isfinite(production_amount):
                raise ValueError(
                    "Field 'amount_per_producer_per_cycle' in "
                    f"producer production entry {entry_index} of "
                    f"definition '{source_path}' must be finite."
                )
            if production_amount <= 0:
                raise ValueError(
                    f"Field 'amount_per_producer_per_cycle' in "
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
    entity_id = definition["id"]
    if ENTITY_ID_PATTERN.fullmatch(entity_id) is None:
        raise ValueError(
            f"Field 'id' in definition '{source_path}' "
            f"must use lowercase snake_case."
        )