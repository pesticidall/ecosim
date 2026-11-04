import unittest
from copy import deepcopy

from core.content_registry import ContentRegistry
from simulation.daily_cycle import run_day
from simulation.daily_demographics import DemographicCarry
from simulation.world_state import HabitatState, RegionState, WorldState
from ui.history import format_daily_history, HISTORY_CATEGORIES


class TestDailyHistory(unittest.TestCase):
    def test_category_filters_keep_solo_and_group_injuries_independent_of_hunt_details(self):
        for groups in (False, True):
            world, registry = self.setup_hunt(groups)
            result = run_day(world, registry)
            before, rng = deepcopy(world), world.random_generator.getstate()
            for category, expected in (("Weather", "Weather: Clear"), ("Hunts", "Outcome: secured"),
                                       ("Injuries", "New injury: Prey"), ("Populations", "predation death"),
                                       ("Resources", "Food:"), ("Carrion", "kg carrion remaining")):
                with self.subTest(groups=groups, category=category):
                    text = format_daily_history(result, registry, category)
                    self.assertIn(expected, text)
                    self.assertIn("1 January, Year 1 completed", text)
                    for other, excluded in (("Weather", "Weather:"), ("Hunts", "Detection:"),
                                            ("Injuries", "New injury:"), ("Populations", "predation death"),
                                            ("Resources", "Food:"), ("Carrion", "kg carrion remaining")):
                        if other != category:
                            self.assertNotIn(excluded, text)
            self.assertEqual(format_daily_history(result, registry), format_daily_history(result, registry, "All events"))
            self.assertEqual(world, before)
            self.assertEqual(world.random_generator.getstate(), rng)

    def test_category_empty_results_and_invalid_filter_are_explicit(self):
        world, registry = self.setup_hunt()
        registry.get("clear")["visibility_modifier"] = 0.0
        result = run_day(world, registry)
        self.assertIn("No matching recorded activity", format_daily_history(result, registry, "Injuries"))
        self.assertIn("0.0% food coverage", format_daily_history(result, registry, "Food coverage"))
        self.assertNotIn("Detection:", format_daily_history(result, registry, "Food coverage"))
        for category in HISTORY_CATEGORIES:
            self.assertIsInstance(format_daily_history(result, registry, category), str)
        with self.assertRaisesRegex(ValueError, "category"):
            format_daily_history(result, registry, "unknown")

    def setup_hunt(self, groups=False):
        registry = ContentRegistry()
        registry.register_all([
            {"id": "root", "entity_type": "taxon", "parent_taxon_id": None},
            {"id": "region", "entity_type": "region", "name": "Region"},
            {"id": "local", "entity_type": "habitat", "name": "Local",
             "conditions": {"openness": 1.0, "vegetation_density": 0.0}},
            {"id": "clear", "entity_type": "weather", "name": "Clear"},
            {"id": "food", "entity_type": "resource", "name": "Food", "unit": "kg"},
            {"id": "bite", "entity_type": "attack_method", "trauma_modifier": 1.0,
             "trait_effect_target": "bite_effectiveness"},
        ])
        for animal_id, power in (("hunter", 8.0), ("prey", 0.0)):
            registry.register({
                "id": animal_id, "entity_type": "animal", "name": animal_id.title(), "taxon_id": "root",
                "typical_adult_mass_kg": 10.0, "food_requirement_per_animal_per_cycle": 31.0,
                "primary_movement_mode": "terrestrial", "available_movement_modes": ["terrestrial"],
                "diet": [] if animal_id == "hunter" else [{"resource_id": "food", "preference": 1.0}],
                "statistics": {"power": power, "defense": 0.0, "mobility": power,
                               "perception": power, "stealth": 0.0, "intelligence": 5.0},
            })
        registry.get("hunter").update(attack_method_id="bite", prey_diet=[{"animal_id": "prey", "preference": 1.0}])
        if groups:
            registry.get("hunter")["max_hunting_group_size"] = 2
            registry.get("prey")["max_defensive_group_size"] = 2
        habitat = HabitatState("local", animal_populations={"hunter": 2 if groups else 1, "prey": 2},
                               resource_quantities={"food": 100.0})
        region = RegionState("region", active_weather_id="clear", habitats={"local": habitat},
                             animal_populations=dict(habitat.animal_populations), resource_quantities={"food": 100.0})
        return WorldState(1, regions={"region": region}), registry

    def test_solo_and_group_history_explain_contact_new_injury_death_and_carrion(self):
        for groups in (False, True):
            with self.subTest(groups=groups):
                world, registry = self.setup_hunt(groups)
                day = run_day(world, registry)
                before, random_before = deepcopy(world), world.random_generator.getstate()
                text = format_daily_history(day, registry)
                self.assertIn("1 January, Year 1 completed.", text)
                self.assertIn("Weather: Clear", text)
                self.assertIn("Hunter → Prey", text)
                self.assertIn("Outcome: secured.", text)
                self.assertIn("New injury: Prey", text)
                self.assertIn("1 predation death", text)
                self.assertIn("kg carrion remaining", text)
                if groups:
                    self.assertIn("Participants: 2 hunters; 2 defenders.", text)
                self.assertEqual(world, before)
                self.assertEqual(world.random_generator.getstate(), random_before)

    def test_failed_hunt_records_actual_early_exit_without_inventing_injury_or_death(self):
        world, registry = self.setup_hunt()
        registry.get("clear")["visibility_modifier"] = 0.0
        text = format_daily_history(run_day(world, registry), registry)
        self.assertIn("Detection: failed", text)
        self.assertIn("Chase: not attempted.", text)
        self.assertNotIn("New injury:", text)
        self.assertNotIn("predation death", text)
        self.assertIn("Hunter: 0.0% food coverage.", text)

    def test_starvation_and_births_keep_their_resolved_date(self):
        world, registry = self.setup_hunt()
        registry.get("hunter")["prey_diet"] = []
        registry.get("prey")["birth_rate_per_animal_per_cycle"] = 31.0
        world.regions["region"].habitats["local"].demographic_carry["hunter"] = DemographicCarry(starvation=0.99)
        day = run_day(world, registry)
        text = format_daily_history(day, registry)
        self.assertIn("Hunter: 0 births; 1 starvation death.", text)
        self.assertIn("Prey: 2 births; 0 starvation deaths.", text)
        run_day(world, registry)
        self.assertEqual(format_daily_history(day, registry), text)
