import unittest
import json
from tempfile import TemporaryDirectory
from copy import deepcopy
from pathlib import Path

from core.content_catalog import build_content_registry
from core.content_validator import validate_entity_definition
from simulation.carrion import CarrionDeposit
from simulation.daily_cycle import run_day
from simulation.interventions import add_supplementary_food, introduce_population, remove_population
from simulation.monthly_cycle import run_month, acknowledge_month_review
from simulation.production import apply_producer_production
from simulation.scavenging import allocate_habitat_scavenging
from simulation.scenario_loader import load_scenario


ROOT = Path(__file__).resolve().parents[1]
REGION = "redgrass_savanna"
HABITAT = "open_grassland"


class TestPlaytestBRoster(unittest.TestCase):
    def setUp(self):
        self.registry = build_content_registry(ROOT / "content")
        self.world = load_scenario(ROOT / "scenarios" / "playtest_b_food_web.json", self.registry)

    def test_roster_loads_with_explicit_diets_and_stable_plant_ids(self):
        for animal in ("warthog", "aardwolf", "helmeted_guineafowl", "black_backed_jackal",
                       "caracal", "brown_hyena", "white_backed_vulture"):
            self.assertEqual(self.registry.get(animal)["entity_type"], "animal")
            self.assertGreater(self.world.regions[REGION].animal_populations[animal], 0)
        self.assertEqual(self.registry.get("redgrass")["name"], "Red Grass")
        self.assertEqual(self.registry.get("umbrella_thorn")["name"], "Umbrella Tree")
        self.assertEqual(self.registry.get("termite_colony")["entity_type"], "colony")
        self.assertIn("soaring", self.registry.get("white_backed_vulture")["flight_capabilities"])
        self.assertNotIn("prey_diet", self.registry.get("white_backed_vulture"))
        self.assertIn("prey_diet", self.registry.get("caracal"))

    def test_colonies_produce_local_termite_food_without_being_plants_or_feed(self):
        region = self.world.regions[REGION]
        self.assertEqual(region.colony_populations, {"termite_colony": 60})
        self.assertNotIn("termite_colony", region.producer_populations)
        before = region.resource_quantities["termites"]
        changes = apply_producer_production(region, self.registry)
        self.assertAlmostEqual(changes["termites"], 1.5)
        self.assertAlmostEqual(region.resource_quantities["termites"], before + 1.5)
        self.assertNotIn("termites", region.habitats["acacia_scrub"].resource_quantities)
        self.assertNotIn("supplementary_feed_type", self.registry.get("termites"))
        result = run_day(self.world, self.registry)
        self.assertEqual(result.region_results[REGION].food_web.regional_feeding["aardwolf"].nutrition_ratio, 1)

    def test_colony_schema_and_scenario_population_validation(self):
        definition = self.registry.get("termite_colony")
        for value in (-1, 0, True, float("inf")):
            candidate = deepcopy(definition)
            candidate["production"][0]["amount_per_producer_per_day"] = value
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                validate_entity_definition(candidate, Path("colony.json"))
        # No-registry loading still preserves the separate colony state.
        world = load_scenario(ROOT / "scenarios" / "playtest_b_food_web.json")
        self.assertEqual(world.regions[REGION].colony_populations, {"termite_colony": 60})
        original = json.loads((ROOT / "scenarios" / "playtest_b_food_web.json").read_text(encoding="utf-8"))
        with TemporaryDirectory() as folder:
            path = Path(folder) / "scenario.json"
            for colony, count in (("termite_colony", True), ("termite_colony", -1), ("redgrass", 1)):
                candidate = deepcopy(original)
                candidate["regions"][0]["colony_populations"] = {colony: count}
                path.write_text(json.dumps(candidate), encoding="utf-8")
                with self.subTest(colony=colony, count=count), self.assertRaises(ValueError):
                    load_scenario(path, self.registry)

    def test_full_roster_replays_deterministically_for_three_months(self):
        other = deepcopy(self.world)
        for _ in range(3):
            self.assertEqual(run_month(self.world, self.registry), run_month(other, self.registry))
            acknowledge_month_review(self.world)
            acknowledge_month_review(other)
        self.assertEqual(self.world, other)
        self.assertEqual(self.world.random_generator.getstate(), other.random_generator.getstate())

    def test_real_scavengers_compete_for_unreserved_carrion_and_respect_first_access(self):
        habitat = self.world.regions[REGION].habitats[HABITAT]
        habitat.carrion_deposits = [CarrionDeposit("warthog", HABITAT, 10, 10, "caracal")]
        definitions = {animal: self.registry.get(animal) for animal in ("brown_hyena", "white_backed_vulture")}
        requests = {animal: 10.0 for animal in definitions}
        result = allocate_habitat_scavenging(definitions, habitat, requests)
        self.assertEqual(sum(item.consumed_biomass_kg for item in result.values()), 0)
        habitat.carrion_deposits = [CarrionDeposit("warthog", HABITAT, 10, 10, None)]
        result = allocate_habitat_scavenging(definitions, habitat, requests)
        for item in result.values():
            self.assertAlmostEqual(item.consumed_biomass_kg, 5)

    def test_year_run_with_interventions_and_empty_ic_reconciles_every_month(self):
        world, registry = self.world, self.registry
        introduce_population(world, registry, REGION, HABITAT, "helmeted_guineafowl", 5)
        remove_population(world, registry, REGION, HABITAT, "warthog", 1)
        add_supplementary_food(world, registry, REGION, HABITAT, "grass_forage", 250)
        self.assertEqual(world.intervention_resources.ic, 0)
        before = deepcopy(world)
        with self.assertRaises(ValueError):
            add_supplementary_food(world, registry, REGION, HABITAT, "grass_forage", 50)
        self.assertEqual(world, before)
        for number in range(12):
            summary = run_month(world, registry)
            for result in summary.region_results.values():
                for animal, ending in result.ending_state.animal_populations.items():
                    expected = (result.starting_state.animal_populations.get(animal, 0)
                                + result.births.get(animal, 0) + result.introductions.get(animal, 0)
                                - result.removals.get(animal, 0) - result.starvation_deaths.get(animal, 0)
                                - result.predation_deaths.get(animal, 0))
                    self.assertEqual(ending, expected)
            self.assertEqual(world.intervention_resources.ic, min(10, (number + 1) * 2))
            region = world.regions[REGION]
            for resource, amount in region.resource_quantities.items():
                self.assertGreaterEqual(amount, 0)
                self.assertAlmostEqual(amount, sum(h.resource_quantities.get(resource, 0) for h in region.habitats.values()))
            for animal, count in region.animal_populations.items():
                self.assertGreaterEqual(count, 0)
                self.assertEqual(count, sum(h.animal_populations.get(animal, 0) for h in region.habitats.values()))
            for habitat in region.habitats.values():
                for animal, cohorts in habitat.injury_cohorts.items():
                    self.assertLessEqual(sum(c.count for c in cohorts), habitat.animal_populations.get(animal, 0))
                self.assertTrue(all(c.available_biomass_kg >= 0 for c in habitat.carrion_deposits))
            acknowledge_month_review(world)
        self.assertEqual((world.calendar.year, world.calendar.day), (2, 1))
