import json
from pathlib import Path
import unittest

from core.content_registry import ContentRegistry
from core.content_validator import validate_entity_definition
from simulation.production import apply_producer_production
from simulation.world_state import RegionState, HabitatState


class TestStandingFood(unittest.TestCase):
    def registry(self, second_capacity=2):
        registry = ContentRegistry()
        for name, capacity in (("plant", 3), ("other", second_capacity)):
            entry = {"resource_id": "food", "amount_per_producer_per_day": 2}
            if capacity is not None:
                entry["standing_capacity_per_producer"] = capacity
            registry.register({"id": name, "production": [entry]})
        registry.register({"id": "rain", "producer_production_multiplier": 10})
        return registry

    def test_saturation_consumption_and_above_capacity_stock(self):
        region = RegionState(definition_id="region", producer_populations={"plant": 2}, resource_quantities={"food": 5})
        registry = self.registry()
        self.assertEqual(apply_producer_production(region, registry, days=31), {"food": 1})
        region.resource_quantities["food"] -= 3
        self.assertEqual(apply_producer_production(region, registry), {"food": 3})
        region.resource_quantities["food"] += 50
        self.assertEqual(apply_producer_production(region, registry), {"food": 0})
        self.assertEqual(region.resource_quantities["food"], 56)

    def test_capacity_pools_sources_but_is_local_and_weather_independent(self):
        habitats = {name: HabitatState(definition_id=name, producer_populations={"plant": 1, "other": 2}, resource_quantities={"food": stock}) for name, stock in (("a", 6), ("b", 0))}
        region = RegionState(definition_id="region", habitats=habitats, resource_quantities={"food": 6}, active_weather_id="rain")
        self.assertEqual(apply_producer_production(region, self.registry()), {"food": 8})
        self.assertEqual([h.resource_quantities["food"] for h in habitats.values()], [7, 7])
        self.assertEqual(region.resource_quantities["food"], 14)

    def test_uncapped_sources_still_produce_above_bounded_capacity(self):
        region = RegionState(definition_id="region", producer_populations={"plant": 1, "other": 1}, resource_quantities={"food": 10})
        self.assertEqual(apply_producer_production(region, self.registry(None)), {"food": 2})
        self.assertEqual(region.resource_quantities["food"], 12)

    def test_capacity_schema(self):
        path = Path(__file__).resolve().parents[1] / "content/producers/redgrass.json"
        for value in (True, "3", 0, -1, float("nan"), float("inf"), 3):
            with self.subTest(value=value):
                definition = json.loads(path.read_text(encoding="utf-8"))
                definition["production"][0]["standing_capacity_per_producer"] = value
                if value == 3 and not isinstance(value, str):
                    validate_entity_definition(definition, path)
                else:
                    with self.assertRaises((ValueError, TypeError)):
                        validate_entity_definition(definition, path)
