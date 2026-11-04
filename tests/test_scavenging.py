import unittest
from pathlib import Path

from simulation.carrion import CarrionDeposit
from simulation.scavenging import scavenge_habitat_carrion
from simulation.world_state import HabitatState


class TestScavenging(unittest.TestCase):
    def test_competing_consumers_share_in_proportion_to_unmet_demand(self):
        from simulation.scavenging import allocate_habitat_scavenging

        definitions = {animal_id: {"id": animal_id, "scavenging_diet": [
            {"animal_id": "prey", "preference": 1.0}]} for animal_id in ("a", "b")}
        for request_items in ((('a', 2.0), ('b', 6.0)), (('b', 6.0), ('a', 2.0))):
            with self.subTest(order=request_items):
                habitat = HabitatState("local", animal_populations={"a": 1, "b": 1},
                                       carrion_deposits=[CarrionDeposit("prey", "local", 6.0, 6.0, None)])
                result = allocate_habitat_scavenging(definitions, habitat, dict(request_items))
                self.assertAlmostEqual(result["a"].consumed_biomass_kg, 1.5)
                self.assertAlmostEqual(result["b"].consumed_biomass_kg, 4.5)
                self.assertEqual(habitat.carrion_deposits, [])

    def test_competition_falls_back_to_alternative_carcasses(self):
        from simulation.scavenging import allocate_habitat_scavenging

        definitions = {animal_id: {"id": animal_id, "scavenging_diet": [
            {"animal_id": "preferred", "preference": 2.0},
            {"animal_id": "alternative", "preference": 1.0}]} for animal_id in ("a", "b")}
        habitat = HabitatState("local", animal_populations={"a": 1, "b": 1}, carrion_deposits=[
            CarrionDeposit("preferred", "local", 2.0, 2.0, None),
            CarrionDeposit("alternative", "local", 6.0, 6.0, None),
        ])
        result = allocate_habitat_scavenging(definitions, habitat, {"a": 3.0, "b": 3.0})
        self.assertEqual([result[key].consumed_biomass_kg for key in ("a", "b")], [3.0, 3.0])
        self.assertEqual(habitat.carrion_deposits[0].available_biomass_kg, 2.0)

    def test_competition_cannot_bypass_predator_first_access(self):
        from simulation.scavenging import allocate_habitat_scavenging

        definitions = {animal_id: {"id": animal_id, "scavenging_diet": [
            {"animal_id": "prey", "preference": 1.0}]} for animal_id in ("predator", "scavenger")}
        reserved = CarrionDeposit("prey", "local", 10.0, 10.0, "predator")
        habitat = HabitatState("local", animal_populations={"predator": 1, "scavenger": 1}, carrion_deposits=[reserved])
        result = allocate_habitat_scavenging(definitions, habitat, {"predator": 2.0, "scavenger": 6.0})
        self.assertEqual(result["predator"].consumed_biomass_kg, 2.0)
        self.assertEqual(result["scavenger"].consumed_biomass_kg, 0.0)
        self.assertEqual(habitat.carrion_deposits[0].first_access_consumer_id, "predator")
        self.assertEqual(habitat.carrion_deposits[0].available_biomass_kg, 8.0)

    def setUp(self):
        self.consumer = {"id": "scavenger", "scavenging_diet": [
            {"animal_id": "preferred", "preference": 2.0},
            {"animal_id": "alternative", "preference": 1.0},
        ]}
        self.habitat = HabitatState("local", animal_populations={"scavenger": 1})

    def test_consumes_compatible_sources_in_preference_order(self):
        original = [CarrionDeposit(source, "local", mass, mass, None)
                    for source, mass in (("alternative", 5.0), ("incompatible", 10.0), ("preferred", 2.0))]
        self.habitat.carrion_deposits = list(original)
        result = scavenge_habitat_carrion(self.consumer, self.habitat, 4.0)
        self.assertEqual(result.consumed_biomass_kg, 4.0)
        self.assertEqual([c.consumed_biomass_kg for c in result.consumptions], [2.0, 2.0])
        self.assertEqual([d.available_biomass_kg for d in self.habitat.carrion_deposits], [3.0, 10.0])
        self.assertEqual(original[0].available_biomass_kg, 5.0)

    def test_reservation_blocks_scavenger_and_empty_population_cannot_feed(self):
        reserved = CarrionDeposit("preferred", "local", 10.0, 10.0, "predator")
        self.habitat.carrion_deposits = [reserved]
        result = scavenge_habitat_carrion(self.consumer, self.habitat, 3.0)
        self.assertEqual(result.consumed_biomass_kg, 0.0)
        self.assertFalse(result.consumptions[0].access_granted)
        self.habitat.animal_populations["scavenger"] = 0
        self.assertEqual(scavenge_habitat_carrion(self.consumer, self.habitat, 3.0).consumptions, ())
        self.assertEqual(self.habitat.carrion_deposits, [reserved])

    def test_invalid_request_leaves_carrion_unchanged(self):
        for amount, error in ((True, TypeError), (-1.0, ValueError), (float("inf"), ValueError)):
            with self.subTest(amount=amount), self.assertRaises(error):
                scavenge_habitat_carrion(self.consumer, self.habitat, amount)
        self.assertEqual(self.habitat.carrion_deposits, [])

    def test_scavenging_diet_schema_and_references(self):
        from core.content_validator import validate_entity_definition
        from simulation.predator_diet import validate_animal_prey_references

        definition = {**self.consumer, "entity_type": "animal", "name": "Scavenger",
                      "diet_type": "omnivore", "diet": [{"resource_id": "forage", "preference": 1.0}],
                      "food_requirement_per_animal_per_cycle": 2.0, "birth_rate_per_animal_per_cycle": 0.0}
        validate_entity_definition(definition, Path("scavenger.json"))
        validate_animal_prey_references([definition, {"id": "preferred"}, {"id": "alternative"}])
        with self.assertRaisesRegex(ValueError, "unknown scavenging source"):
            validate_animal_prey_references([definition])
        for diet in ({}, [{"animal_id": "preferred", "preference": 0.0}], [{"animal_id": "Bad ID", "preference": 1.0}]):
            with self.subTest(diet=diet), self.assertRaises((TypeError, ValueError)):
                validate_entity_definition({**definition, "scavenging_diet": diet}, Path("scavenger.json"))
