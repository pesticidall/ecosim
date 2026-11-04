import unittest
from pathlib import Path
from unittest.mock import patch

from core.content_catalog import build_content_registry
from core.content_validator import validate_entity_definition


class TestPredatorDiet(unittest.TestCase):
    def test_activity_abundance_weights_use_local_counts_and_overlap(self):
        from random import Random
        from core.content_registry import ContentRegistry
        from simulation.predator_diet import select_habitat_prey
        from simulation.world_state import HabitatState
        registry = ContentRegistry()
        registry.register_all([
            {"id": "prey_a", "activity_pattern": "crepuscular"},
            {"id": "prey_b", "activity_pattern": "nocturnal"},
            {"id": "inactive", "activity_pattern": "diurnal"},
        ])
        predator = {"id": "hunter", "activity_pattern": "nocturnal", "encounter_model": "activity_abundance",
                    "prey_diet": [{"animal_id": a, "preference": 1.0} for a in ("prey_a", "prey_b", "inactive")]}
        habitat = HabitatState("local", animal_populations={"hunter": 1, "prey_a": 9, "prey_b": 1, "inactive": 1000})
        rng, reference = Random(1), Random(1)
        result = select_habitat_prey(predator, habitat, rng, registry=registry)
        reference.random()
        self.assertEqual(rng.getstate(), reference.getstate())
        self.assertEqual([c.animal_id for c in result.candidates], ["prey_a", "prey_b"])
        self.assertAlmostEqual(result.candidates[0].selection_probability, 0.6)
        self.assertAlmostEqual(result.candidates[1].selection_probability, 0.4)
        self.assertEqual(result.candidates[0].activity_overlap, 0.5)
        # Abundance changes opportunity, not just a present/absent gate.
        habitat.animal_populations["prey_a"] = 1
        changed = select_habitat_prey(predator, habitat, Random(1), registry=registry)
        self.assertAlmostEqual(changed.candidates[0].selection_probability, 1 / 3)

    def test_all_inactive_prey_give_no_encounter_or_random_draw(self):
        from random import Random
        from core.content_registry import ContentRegistry
        from simulation.predator_diet import select_habitat_prey
        from simulation.world_state import HabitatState
        registry = ContentRegistry()
        registry.register({"id": "prey", "activity_pattern": "diurnal"})
        predator = {"id": "hunter", "activity_pattern": "nocturnal", "encounter_model": "activity_abundance",
                    "prey_diet": [{"animal_id": "prey", "preference": 1.0}]}
        habitat = HabitatState("local", animal_populations={"hunter": 1, "prey": 100})
        rng = Random(1)
        before = rng.getstate()
        self.assertIsNone(select_habitat_prey(predator, habitat, rng, registry=registry))
        self.assertEqual(rng.getstate(), before)
        with self.assertRaisesRegex(ValueError, "registry"):
            select_habitat_prey(predator, habitat, rng)

    def test_encounter_normalization_handles_large_weights_and_same_species_exclusion(self):
        from random import Random
        from core.content_registry import ContentRegistry
        from simulation.predator_diet import select_habitat_prey
        from simulation.world_state import HabitatState
        registry = ContentRegistry()
        registry.register_all([{"id": "hunter"}, {"id": "prey"}])
        predator = {"id": "hunter", "encounter_model": "activity_abundance",
                    "prey_diet": [{"animal_id": a, "preference": 1e308} for a in ("hunter", "prey")]}
        habitat = HabitatState("local", animal_populations={"hunter": 2, "prey": 9})
        result = select_habitat_prey(predator, habitat, Random(1), registry=registry)
        self.assertEqual(result.candidates[0].available_population, 1)
        self.assertAlmostEqual(result.candidates[0].selection_probability, 0.25)
        habitat.animal_populations["prey"] = 10 ** 400
        result = select_habitat_prey(predator, habitat, Random(1), registry=registry)
        self.assertAlmostEqual(sum(c.selection_probability for c in result.candidates), 1)

    def test_validates_encounter_model_and_bounded_opportunities(self):
        for field, values in (("encounter_model", ("bad", 1, None)),
                              ("hunting_attempts_per_animal", (0, 9, True, 1.5, None))):
            for value in values:
                definition = self.definition()
                definition[field] = value
                with self.subTest(field=field, value=value), self.assertRaises((ValueError, TypeError)):
                    validate_entity_definition(definition, Path("animal.json"))
        for mode in ("preference", "activity_abundance"):
            definition = {**self.definition(), "encounter_model": mode, "hunting_attempts_per_animal": 2}
            validate_entity_definition(definition, Path("animal.json"))

    def test_validates_optional_group_size_ceilings(self):
        validate_entity_definition(self.definition(), Path("animal.json"))
        for field in ("max_hunting_group_size", "max_defensive_group_size"):
            for value, error in ((1, None), (4, None), (True, TypeError), (2.0, TypeError),
                                 ("2", TypeError), (None, TypeError), (0, ValueError), (-1, ValueError)):
                with self.subTest(field=field, value=value):
                    definition = {**self.definition(), field: value}
                    if error is None:
                        validate_entity_definition(definition, Path("animal.json"))
                    else:
                        with self.assertRaisesRegex(error, field):
                            validate_entity_definition(definition, Path("animal.json"))

    def test_validates_animal_attack_method_id_fields(self) -> None:
        for field in ("attack_method_id", "counterattack_method_id"):
            for value, error in (("bite", None), (42, TypeError), (None, TypeError),
                                 ("", ValueError), ("Bad ID", ValueError)):
                with self.subTest(field=field, value=value):
                    definition = self.definition()
                    definition[field] = value
                    if error is None:
                        validate_entity_definition(definition, Path("animal.json"))
                    else:
                        with self.assertRaisesRegex(error, field):
                            validate_entity_definition(definition, Path("animal.json"))

    def test_catalog_validates_both_animal_method_references(self) -> None:
        for field in ("attack_method_id", "counterattack_method_id"):
            for loaded in (False, True):
                with self.subTest(field=field, loaded=loaded):
                    definition = self.definition()
                    definition[field] = "bite"

                    def loader(path, expected_entity_type=None):
                        if expected_entity_type == "animal":
                            return [definition]
                        if expected_entity_type == "resource":
                            return [{"id": "forage"}]
                        if expected_entity_type == "attack_method" and loaded:
                            return [{"id": "bite"}]
                        return []

                    with patch("core.content_catalog.load_entity_definitions_from_directory", side_effect=loader):
                        if loaded:
                            self.assertEqual(build_content_registry(Path("content")).get("test_predator")[field], "bite")
                        else:
                            with self.assertRaisesRegex(ValueError, f"unknown {field}.*bite"):
                                build_content_registry(Path("content"))
    def test_selects_local_prey_with_seeded_preference_weights(self) -> None:
        from random import Random
        from simulation.predator_diet import select_habitat_prey
        from simulation.world_state import HabitatState

        predator = {"id": "hunter", "prey_diet": [
            {"animal_id": "prey_b", "preference": 3.0},
            {"animal_id": "prey_a", "preference": 1.0},
            {"animal_id": "absent", "preference": 100.0},
        ]}
        populations = {"hunter": 1, "prey_a": 2, "prey_b": 5, "nonprey": 100}
        for seed, expected in ((1, "prey_a"), (2, "prey_b")):
            with self.subTest(seed=seed):
                habitat = HabitatState("local", animal_populations=dict(populations))
                random_source = Random(seed)
                expected_random = Random(seed)
                roll = expected_random.random()
                result = select_habitat_prey(predator, habitat, random_source)
                self.assertEqual(result.selected_animal_id, expected)
                self.assertEqual(result.selection_roll, roll)
                self.assertEqual([c.animal_id for c in result.candidates], ["prey_a", "prey_b"])
                self.assertEqual([c.selection_probability for c in result.candidates], [0.25, 0.75])
                self.assertEqual([c.available_population for c in result.candidates], [2, 5])
                self.assertEqual(random_source.getstate(), expected_random.getstate())
                self.assertEqual(habitat.animal_populations, populations)
                reordered = HabitatState("local", animal_populations=dict(reversed(list(populations.items()))))
                self.assertEqual(select_habitat_prey(predator, reordered, Random(seed)), result)

    def test_no_available_prey_consumes_no_randomness(self) -> None:
        from random import Random
        from simulation.predator_diet import select_habitat_prey
        from simulation.world_state import HabitatState

        for populations, diet in (
            ({"hunter": 1, "prey": 0}, [{"animal_id": "prey", "preference": 1.0}]),
            ({"hunter": 0, "prey": 3}, [{"animal_id": "prey", "preference": 1.0}]),
            ({"hunter": 1, "prey": 3}, []),
        ):
            with self.subTest(populations=populations, diet=diet):
                random_source = Random(1)
                state = random_source.getstate()
                self.assertIsNone(select_habitat_prey(
                    {"id": "hunter", "prey_diet": diet},
                    HabitatState("local", animal_populations=populations), random_source,
                ))
                self.assertEqual(random_source.getstate(), state)

    def test_explicit_same_species_prey_requires_another_animal(self) -> None:
        from random import Random
        from simulation.predator_diet import select_habitat_prey
        from simulation.world_state import HabitatState

        predator = {"id": "hunter", "prey_diet": [{"animal_id": "hunter", "preference": 1.0}]}
        for count in (1, 2):
            with self.subTest(count=count):
                result = select_habitat_prey(predator, HabitatState("local", animal_populations={"hunter": count}), Random(1))
                if count == 1:
                    self.assertIsNone(result)
                else:
                    self.assertEqual(result.selected_animal_id, "hunter")
                    self.assertEqual(result.candidates[0].available_population, 1)

    def definition(self) -> dict:
        return {
            "entity_type": "animal", "id": "test_predator", "name": "Test Predator",
            "diet_type": "omnivore", "food_requirement_per_animal_per_cycle": 2.0,
            "birth_rate_per_animal_per_cycle": 0.1,
            "diet": [{"resource_id": "forage", "preference": 1.0}],
        }

    def test_accepts_optional_empty_and_explicit_prey_diets(self) -> None:
        for entries in (None, [], [{"animal_id": "test_prey", "preference": 1.5}]):
            with self.subTest(entries=entries):
                definition = self.definition()
                if entries is not None:
                    definition["prey_diet"] = entries
                validate_entity_definition(definition, Path("test_predator.json"))

    def test_rejects_invalid_prey_diets(self) -> None:
        cases = [({}, TypeError), ([None], TypeError), ([{}], ValueError)]
        for animal_id in (None, 42, "", "Bad ID"):
            cases.append(([{"animal_id": animal_id, "preference": 1.0}],
                          TypeError if not isinstance(animal_id, str) else ValueError))
        for preference in (True, "1", None, 0.0, -1.0, float("inf"), float("nan")):
            cases.append(([{"animal_id": "test_prey", "preference": preference}],
                          TypeError if preference is None or isinstance(preference, (bool, str)) else ValueError))
        entry = {"animal_id": "test_prey", "preference": 1.0}
        cases.append(([entry, entry], ValueError))
        for entries, error in cases:
            with self.subTest(entries=entries):
                definition = self.definition()
                definition["prey_diet"] = entries
                with self.assertRaises(error):
                    validate_entity_definition(definition, Path("test_predator.json"))

    def test_catalog_checks_prey_targets_against_loaded_animals(self) -> None:
        predator = self.definition()
        predator["prey_diet"] = [{"animal_id": "test_prey", "preference": 1.0}]
        for include_prey in (False, True):
            with self.subTest(include_prey=include_prey):
                animals = [predator]
                if include_prey:
                    animals.append({"id": "test_prey"})

                def loader(path, expected_entity_type=None):
                    if expected_entity_type == "animal":
                        return animals
                    if expected_entity_type == "resource":
                        return [{"id": "forage"}]
                    return []

                with patch("core.content_catalog.load_entity_definitions_from_directory", side_effect=loader):
                    if include_prey:
                        registry = build_content_registry(Path("content"))
                        self.assertEqual(registry.get("test_predator")["prey_diet"], predator["prey_diet"])
                    else:
                        with self.assertRaisesRegex(ValueError, "test_predator.*unknown prey.*test_prey"):
                            build_content_registry(Path("content"))
