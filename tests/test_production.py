import unittest

from core.content_registry import ContentRegistry
from simulation.production import (
    apply_producer_production,
)
from simulation.world_state import HabitatState, RegionState


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
                        "amount_per_producer_per_day": 0.25,
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

    def test_scales_daily_production_by_period_length(self) -> None:
        registry = ContentRegistry()
        registry.register(
            {
                "entity_type": "producer",
                "id": "redgrass",
                "name": "Redgrass",
                "production": [
                    {
                        "resource_id": "grass_forage",
                        "amount_per_producer_per_day": 0.25,
                    },
                ],
            }
        )

        for days in (28, 29, 30, 31):
            with self.subTest(days=days):
                region_state = RegionState(
                    definition_id="redgrass_savanna",
                    producer_populations={"redgrass": 4},
                    resource_quantities={"grass_forage": 10.0},
                )

                production_changes = apply_producer_production(
                    region_state,
                    registry,
                    days=days,
                )

                self.assertEqual(
                    production_changes,
                    {"grass_forage": float(days)},
                )
                self.assertEqual(
                    region_state.resource_quantities,
                    {"grass_forage": 10.0 + days},
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
                        "amount_per_producer_per_day": 0.25,
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

    def test_monthly_production_uses_each_weather_day(self) -> None:
        registry = ContentRegistry()
        registry.register_all(
            [
                {
                    "entity_type": "weather",
                    "id": "clear",
                    "name": "Clear",
                    "producer_production_multiplier": 1.0,
                },
                {
                    "entity_type": "weather",
                    "id": "seasonal_rain",
                    "name": "Seasonal Rain",
                    "producer_production_multiplier": 1.25,
                },
                {
                    "entity_type": "producer",
                    "id": "redgrass",
                    "name": "Redgrass",
                    "production": [
                        {
                            "resource_id": "grass_forage",
                            "amount_per_producer_per_day": 0.25,
                        },
                    ],
                },
            ]
        )
        region_state = RegionState(
            definition_id="redgrass_savanna",
            active_weather_id="clear",
            producer_populations={"redgrass": 1},
            resource_quantities={"grass_forage": 0.0},
        )

        production_changes = apply_producer_production(
            region_state,
            registry,
            days=2,
            weather_day_totals={
                "clear": 1,
                "seasonal_rain": 1,
            },
        )

        self.assertEqual(
            production_changes,
            {
                "grass_forage": 0.5625,
            },
        )

    def test_producers_add_resources_to_their_habitat(self) -> None:
        registry = ContentRegistry()
        registry.register(
            {
                "entity_type": "producer",
                "id": "redgrass",
                "name": "Redgrass",
                "production": [
                    {
                        "resource_id": "grass_forage",
                        "amount_per_producer_per_day": 0.25,
                    },
                ],
            }
        )
        region_state = RegionState(
            definition_id="redgrass_savanna",
            producer_populations={"redgrass": 4},
            resource_quantities={"grass_forage": 10.0},
            habitats={
                "open_grassland": HabitatState(
                    definition_id="open_grassland",
                    producer_populations={"redgrass": 4},
                    resource_quantities={"grass_forage": 10.0},
                ),
                "rocky_outcrop": HabitatState(
                    definition_id="rocky_outcrop",
                ),
            },
        )

        production_changes = apply_producer_production(
            region_state,
            registry,
        )

        self.assertEqual(production_changes, {"grass_forage": 1.0})
        self.assertEqual(
            region_state.habitats[
                "open_grassland"
            ].resource_quantities,
            {"grass_forage": 11.0},
        )
        self.assertEqual(
            region_state.habitats[
                "rocky_outcrop"
            ].resource_quantities,
            {},
        )
        self.assertEqual(
            region_state.resource_quantities,
            {"grass_forage": 11.0},
        )


if __name__ == "__main__":
    unittest.main()
