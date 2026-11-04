from core.content_registry import ContentRegistry
from simulation.interventions import (
    SupplementaryFoodIntervention, PopulationRemovalIntervention,
    PopulationIntroductionIntervention, InterventionRecord,
)
from simulation.reporting import format_resource_amount


def format_supplementary_food(record: SupplementaryFoodIntervention, registry: ContentRegistry) -> str:
    return (f"{record.day} {record.month.display_name}, Year {record.year} · "
            f"{registry.get(record.habitat_id)['name']}: +{format_resource_amount(record.amount_kg)} kg "
            f"{registry.get(record.resource_id)['name']} (supplementary food); "
            f"{record.ic_spent:g} IC spent from {record.feed_type.value} feed stock "
            f"[{record.event_id}].")


def format_intervention(record: InterventionRecord, registry: ContentRegistry) -> str:
    if isinstance(record, SupplementaryFoodIntervention):
        return format_supplementary_food(record, registry)
    if isinstance(record, PopulationRemovalIntervention):
        return (f"{record.day} {record.month.display_name}, Year {record.year} · "
                f"{registry.get(record.habitat_id)['name']}: removed {record.quantity} "
                f"{registry.get(record.animal_id)['name']}; {record.ic_spent:g} IC spent; "
                f"1 removal charge used [{record.event_id}].")
    if isinstance(record, PopulationIntroductionIntervention):
        return (f"{record.day} {record.month.display_name}, Year {record.year} · "
                f"{registry.get(record.habitat_id)['name']}: introduced {record.quantity} "
                f"{registry.get(record.animal_id)['name']}; {record.ic_spent:g} IC spent; "
                f"1 introduction charge used [{record.event_id}].")
    raise TypeError("Unknown intervention record type.")
