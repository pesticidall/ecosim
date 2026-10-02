import unittest

from simulation.world_state import HabitatState, RegionState, WorldState


class TestWorldState(unittest.TestCase):
    def test_stores_seed_and_starts_at_cycle_zero(self) -> None:
        world_state = WorldState(random_seed=12345)
        self.assertEqual(world_state.random_seed, 12345)
        self.assertEqual(world_state.current_cycle, 0)

    def test_stores_region_state_by_definition_id(self) -> None:
        region_state = RegionState(
            definition_id="redgrass_savanna",
        )
        world_state = WorldState(
            random_seed=12345,
            regions={
                "redgrass_savanna": region_state,
            },
        )
        self.assertIs(
            world_state.regions["redgrass_savanna"],
            region_state,
        )
        self.assertEqual(
            region_state.definition_id,
            "redgrass_savanna",
        )

    def test_stores_regional_animal_populations(self) -> None:
        region_state = RegionState(
            definition_id="redgrass_savanna",
            animal_populations={
                "scrub_hare": 80,
            }
        )
        self.assertEqual(
            region_state.animal_populations["scrub_hare"],
            80,
        )

    def test_stores_regional_producer_populations(self) -> None:
        region_state = RegionState(
            definition_id="redgrass_savanna",
            producer_populations={
                "redgrass": 500,
            }
        )
        self.assertEqual(
            region_state.producer_populations["redgrass"],
            500,
        )

    def test_stores_regional_resource_quantities(self) -> None:
        region_state = RegionState(
            definition_id="redgrass_savanna",
            resource_quantities={
                "grass_forage": 1200.5,
            },
        )
        self.assertEqual(
            region_state.resource_quantities["grass_forage"],
            1200.5,
        )

    def test_each_region_has_independent_habitat_state(self) -> None:
        first_region = RegionState(
            definition_id="redgrass_savanna",
        )
        second_region = RegionState(
            definition_id="redgrass_savanna",
        )
        first_region.habitats["open_grassland"] = HabitatState(
            definition_id="open_grassland",
        )

        self.assertEqual(second_region.habitats, {})
        self.assertEqual(
            first_region.habitats["open_grassland"].definition_id,
            "open_grassland",
        )

    def test_each_habitat_has_independent_animal_populations(
        self,
    ) -> None:
        grassland_state = HabitatState(
            definition_id="open_grassland",
        )
        scrub_state = HabitatState(
            definition_id="acacia_scrub",
        )

        grassland_state.animal_populations["springbok"] = 40

        self.assertEqual(
            grassland_state.animal_populations,
            {
                "springbok": 40,
            },
        )
        self.assertEqual(
            scrub_state.animal_populations,
            {},
        )

    def test_each_habitat_has_independent_producers_and_resources(
        self,
    ) -> None:
        grassland_state = HabitatState(
            definition_id="open_grassland",
        )
        scrub_state = HabitatState(
            definition_id="acacia_scrub",
        )

        grassland_state.producer_populations["redgrass"] = 500
        grassland_state.resource_quantities["grass_forage"] = 100.0

        self.assertEqual(
            grassland_state.producer_populations,
            {
                "redgrass": 500,
            },
        )
        self.assertEqual(
            grassland_state.resource_quantities,
            {
                "grass_forage": 100.0,
            },
        )
        self.assertEqual(scrub_state.producer_populations, {})
        self.assertEqual(scrub_state.resource_quantities, {})
        
    def test_stores_current_regional_weather(self) -> None:
        region_state = RegionState(
            definition_id="redgrass_savanna",
            active_weather_id="seasonal_rain",
        )
        self.assertEqual(
            region_state.active_weather_id,
            "seasonal_rain",
        )

    def test_each_world_has_an_independent_calendar(self) -> None:
        from simulation.calendar import Month

        first_world = WorldState(random_seed=12345)
        second_world = WorldState(random_seed=67890)

        first_world.calendar.advance_month()

        self.assertIsNot(first_world.calendar, second_world.calendar)
        self.assertIs(first_world.calendar.month, Month.FEBRUARY)
        self.assertEqual(first_world.calendar.year, 1)
        self.assertIs(second_world.calendar.month, Month.JANUARY)
        self.assertEqual(second_world.calendar.year, 1)

    def test_each_world_has_an_independent_seeded_random_stream(
        self,
    ) -> None:
        first_world = WorldState(random_seed=104729)
        second_world = WorldState(random_seed=104729)

        first_values = [
            first_world.random_generator.random()
            for _ in range(3)
        ]
        second_values = [
            second_world.random_generator.random()
            for _ in range(3)
        ]

        self.assertIsNot(
            first_world.random_generator,
            second_world.random_generator,
        )
        self.assertEqual(first_values, second_values)


if __name__ == "__main__":
    unittest.main()
