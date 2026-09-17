import unittest

from core.content_registry import ContentRegistry
from simulation.production import (
    apply_producer_production,
)
from simulation.world_state import RegionState


class TestProducerProduction(unittest.TestCase):
    def test_producers_add_resources_to_region(self) -> None:
        registry = ContentRegistry()
        registry.register(
            {
                "entity_type": "producer",
                "id": "redgrass",
                "name": "Redgrass",
                "production": [
                    {
                        "resource_id": "grass_forage",
                        "amount_per_producer_per_cycle": 0.25,
                    }
                ],
            }
        )
        registry.register(
            {
                "entity_type": "resource",
                "id": "grass_forage",
                "name": "Grass",
                "quantity_type": "biomass",
                "unit": "kg",
            }
        )
        region_state = RegionState(
            definition_id="redgrass_savanna",
            producer_populations={
                "redgrass": 4,
            },
            resource_quantities={
                "grass_forage": 10.0,
            },
        )
        production_changes = apply_producer_production(
            region_state,
            registry
        )
        self.assertEqual(
            region_state.resource_quantities["grass_forage"],
            11.0,
        )
        self.assertEqual(
            production_changes["grass_forage"],
            1.0
        )

    def test_seasonal_rain_increases_new_production_by_25_percent(self) -> None:
        registry = ContentRegistry()
        registry.register(
            {
                "entity_type": "weather",
                "id": "seasonal_rain",
                "name": "Seasonal Rain",
                "producer_production_multiplier": 1.25,
            }
        )
        registry.register(
            {
                "entity_type": "producer",
                "id": "redgrass",
                "name": "Redgrass",
                "production": [
                    {
                        "resource_id": "grass_forage",
                        "amount_per_producer_per_cycle": 0.25,
                    },
                ],
            }
        )
        region_state = RegionState(
            definition_id="redgrass_savanna",
            active_weather_id="seasonal_rain",
            producer_populations={"redgrass": 4},
            resource_quantities={"grass_forage": 10.0},
        )

        production_changes = apply_producer_production(
            region_state,
            registry,
        )

        self.assertEqual(production_changes["grass_forage"], 1.25)
        self.assertEqual(region_state.resource_quantities["grass_forage"], 11.25)


if __name__ == "__main__":
    unittest.main()