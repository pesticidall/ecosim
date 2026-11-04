from copy import deepcopy
import json
from pathlib import Path
from random import Random
import unittest

from core.content_validator import validate_entity_definition
from simulation.calendar import CalendarState
from simulation.daily_cycle import run_day
from simulation.daily_demographics import DemographicCarry, apply_region_daily_demographics
from simulation.daily_feeding import feed_region_for_day
from simulation.growth import GrowthCohort, adult_count, grow_cohorts, mass_units, remove_members


class TestGrowth(unittest.TestCase):
    def setup_region(self, population=2, food=1000, rate=0):
        import test_daily_demographics
        region, registry = test_daily_demographics.TestDailyDemographics().setup_region(population, rate, food)
        registry.get("animal")["growth"] = {"newborn_mass_fraction": 0.1, "days_to_adult": 3}
        return region, registry

    def demographics(self, region, registry):
        feeding = feed_region_for_day(region, registry, CalendarState())
        return apply_region_daily_demographics(region, registry, feeding)

    def test_growth_depends_on_food_and_matures_without_changing_headcount(self):
        config = {"newborn_mass_fraction": 0.1, "days_to_adult": 3}
        cohorts = (GrowthCohort(2, 0.1),)
        self.assertEqual(grow_cohorts(cohorts, config, 0, 10), (cohorts, 0))
        half, gain = grow_cohorts(cohorts, config, 0.5, 10)
        self.assertAlmostEqual(half[0].mass_fraction, 0.25)
        self.assertAlmostEqual(gain, 0.3)
        for _ in range(3):
            cohorts, _ = grow_cohorts(cohorts, config, 1, 10)
        self.assertEqual(cohorts, ())
        self.assertEqual(adult_count(2, cohorts), 2)

    def test_losses_conserve_counts_and_mass(self):
        cohorts = (GrowthCohort(3, 0.2), GrowthCohort(2, 0.7))
        for count in range(9):
            with self.subTest(count=count):
                survivors, removed = remove_members(8, cohorts, count)
                self.assertAlmostEqual(mass_units(8, cohorts), mass_units(8-count, survivors) + removed)
                self.assertGreaterEqual(adult_count(8-count, survivors), 0)

    def test_newborn_mass_and_next_day_growth_are_saved(self):
        region, registry = self.setup_region(rate=31)
        result = self.demographics(region, registry)
        habitat = region.habitats["local"]
        self.assertEqual(result.births["animal"], 2)
        self.assertEqual(habitat.growth_cohorts["animal"], (GrowthCohort(2, 0.1),))
        ledger = result.growth_changes["local"]["animal"]
        self.assertEqual(ledger.newborn_biomass_kg, 2)
        self.assertEqual(ledger.ending_biomass_kg, 22)
        self.assertEqual(ledger.growth_biomass_kg, 0)
        # Adult food allowance remains fully charged, including juveniles.
        registry.get("animal")["birth_rate_per_animal_per_cycle"] = 0
        feeding = feed_region_for_day(region, registry, CalendarState())
        self.assertEqual(feeding.habitat_feeding["local"]["animal"].required_amount, 4)
        second = apply_region_daily_demographics(region, registry, feeding)
        self.assertAlmostEqual(second.growth_changes["local"]["animal"].growth_biomass_kg, 0.5)

    def test_growth_cannot_exceed_retained_food_budget(self):
        config = {"newborn_mass_fraction": 0.1, "days_to_adult": 1}
        cohorts = (GrowthCohort(10, 0.1),)
        updated, gain = grow_cohorts(cohorts, config, 1, 0.01)
        self.assertAlmostEqual(gain, 0.01)
        self.assertAlmostEqual(updated[0].mass_fraction, 0.101)
        self.assertEqual(grow_cohorts(cohorts, config, 1, 0), (cohorts, 0))

    def test_juveniles_cannot_reproduce_and_unfed_animals_do_not_grow(self):
        for food in (0, 1000):
            region, registry = self.setup_region(food=food, rate=31)
            region.habitats["local"].growth_cohorts["animal"] = (GrowthCohort(2, 0.1),)
            result = self.demographics(region, registry)
            self.assertEqual(result.births["animal"], 0)
            if not food:
                self.assertEqual(result.growth_changes["local"]["animal"].growth_biomass_kg, 0)

    def test_starvation_carcasses_use_removed_juvenile_mass(self):
        region, registry = self.setup_region(food=0)
        habitat = region.habitats["local"]
        habitat.growth_cohorts["animal"] = (GrowthCohort(2, 0.1),)
        habitat.demographic_carry["animal"] = DemographicCarry(starvation=0.99)
        result = self.demographics(region, registry)
        self.assertEqual(result.starvation_deaths["animal"], 1)
        self.assertEqual(result.starvation_death_records["local"][0].body_mass_kg, 1)
        self.assertEqual(habitat.carrion_deposits[0].available_biomass_kg, 1)
        self.assertEqual(habitat.growth_cohorts["animal"], (GrowthCohort(1, 0.1),))

    def test_group_predation_uses_juvenile_mass_and_reconciles_cohorts(self):
        import test_group_predation
        fixture = test_group_predation.TestGroupPredation()
        fixture.setUp()
        fixture.habitat.growth_cohorts["prey"] = (GrowthCohort(3, 0.2),)
        result = fixture.commit()
        self.assertEqual(result.meal.death.body_mass_kg, 2)
        self.assertEqual(result.meal.consumption.consumed_biomass_kg, 2)
        self.assertEqual(fixture.habitat.growth_cohorts["prey"], (GrowthCohort(2, 0.2),))

    def test_single_predation_uses_juvenile_mass(self):
        import test_habitat_hunting
        fixture = test_habitat_hunting.TestHabitatHunting()
        fixture.setUp()
        fixture.habitat.growth_cohorts["prey"] = (GrowthCohort(2, 0.2),)
        fixture.predator["food_requirement_per_animal_per_cycle"] = 2
        result = fixture.hunting_round(Random(1))
        self.assertEqual(len(result.meals), 1)
        self.assertEqual(result.meals[0].death.body_mass_kg, 2)
        self.assertEqual(fixture.habitat.growth_cohorts["prey"], (GrowthCohort(1, 0.2),))

    def test_failed_day_leaves_growth_state_and_random_stream_unchanged(self):
        import test_daily_cycle
        world, registry = test_daily_cycle.TestDailyCycle().setup_world(two_regions=True)
        for region in world.regions.values():
            animal = next(iter(region.animal_populations))
            definition = registry.get(animal)
            definition.update(typical_adult_mass_kg=10, growth={"newborn_mass_fraction": 0.1, "days_to_adult": 3})
            region.habitats["local"].growth_cohorts[animal] = (GrowthCohort(1, 0.1),)
        world.regions["b"].habitats["local"].growth_cohorts["animal_b"] = (GrowthCohort(2, 0.1),)
        before, rng = deepcopy(world.regions), world.random_generator.getstate()
        with self.assertRaisesRegex(ValueError, "Juvenile count"):
            run_day(world, registry)
        self.assertEqual(world.regions, before)
        self.assertEqual(world.random_generator.getstate(), rng)
        self.assertEqual(world.daily_history, {})

    def test_population_removal_reconciles_juveniles_without_carrion(self):
        import test_population_removal
        from simulation.interventions import remove_population
        world, registry = test_population_removal.TestPopulationRemoval().setup_world()
        habitat = world.regions["region"].habitats["local"]
        habitat.growth_cohorts["animal"] = (GrowthCohort(4, 0.2),)
        remove_population(world, registry, "region", "local", "animal", 2)
        self.assertEqual(habitat.growth_cohorts["animal"], (GrowthCohort(2, 0.2),))
        self.assertEqual(habitat.carrion_deposits, [])

    def test_schema_validates_growth_configuration(self):
        path = Path(__file__).resolve().parents[1] / "content/animals/mammals/scrub_hare.json"
        base = json.loads(path.read_text(encoding="utf-8"))
        for config in ({"newborn_mass_fraction": 0.1, "days_to_adult": 90},
                       {}, {"newborn_mass_fraction": True, "days_to_adult": 90},
                       {"newborn_mass_fraction": float("nan"), "days_to_adult": 90},
                       {"newborn_mass_fraction": 0, "days_to_adult": 90},
                       {"newborn_mass_fraction": 1, "days_to_adult": 90},
                       {"newborn_mass_fraction": 0.1, "days_to_adult": True},
                       {"newborn_mass_fraction": 0.1, "days_to_adult": 0}):
            definition = {**base, "growth": config}
            with self.subTest(config=config):
                if config == {"newborn_mass_fraction": 0.1, "days_to_adult": 90}:
                    validate_entity_definition(definition, path)
                else:
                    with self.assertRaises(ValueError):
                        validate_entity_definition(definition, path)

    def test_introductions_add_adults_and_replay_preserves_saved_cohorts(self):
        import test_population_introduction
        from simulation.interventions import introduce_population
        world, registry = test_population_introduction.TestPopulationIntroduction().setup_world(local=2)
        habitat = world.regions["region"].habitats["local"]
        registry.get("animal")["growth"] = {"newborn_mass_fraction": 0.1, "days_to_adult": 90}
        habitat.growth_cohorts["animal"] = (GrowthCohort(2, 0.2),)
        introduce_population(world, registry, "region", "local", "animal", 2)
        self.assertEqual(adult_count(habitat.animal_populations["animal"], habitat.growth_cohorts["animal"]), 2)
        replay = deepcopy(world)
        first = run_day(world, registry)
        self.assertEqual(first, run_day(replay, registry))
        self.assertEqual(first.region_results["region"].starting_state.growth_cohorts["local"]["animal"], (GrowthCohort(2, 0.2),))
        self.assertEqual(world.regions, replay.regions)

    def test_growth_case_reconciles_full_monthly_live_and_dead_biomass(self):
        from scripts.investigate_capacity import Factors, run_case
        root = Path(__file__).resolve().parents[1]
        factors = Factors(300, 2000, "small", 8, True, 60, True, 0.9, 30, 0.9, 90)
        first = run_case(root, factors, 7, 2)
        self.assertEqual(first, run_case(root, factors, 7, 2))
        self.assertGreater(sum(m["regions"]["redgrass_savanna"]["growth"]["scrub_hare"]["newborn_biomass_kg"] for m in first["monthly"]), 0)

    def test_invalid_cohorts_growth_budgets_and_retention_are_rejected(self):
        for count, fraction in ((True, 0.1), (0, 0.1), (1, 0), (1, 1), (1, float("nan"))):
            with self.subTest(count=count, fraction=fraction), self.assertRaises(ValueError):
                GrowthCohort(count, fraction)
        for budget in (True, -1, float("nan"), float("inf")):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                grow_cohorts((), {"newborn_mass_fraction": 0.1, "days_to_adult": 90}, 1, budget)
        path = Path(__file__).resolve().parents[1] / "content/animals/mammals/scrub_hare.json"
        base = json.loads(path.read_text(encoding="utf-8"))
        for value in (True, 0, -1, 1.1, float("nan"), "0.25"):
            definition = {**base, "growth": {"newborn_mass_fraction": 0.1, "days_to_adult": 90, "biomass_gain_per_food_kg": value}}
            with self.subTest(retention=value), self.assertRaises(ValueError):
                validate_entity_definition(definition, path)

    def test_growth_experiment_changes_private_definitions_only(self):
        from core.content_catalog import build_content_registry
        from scripts.investigate_capacity import Factors, configure
        root = Path(__file__).resolve().parents[1]
        registry = build_content_registry(root / "content")
        source = json.loads((root / "scenarios/playtest_b_food_web.json").read_text(encoding="utf-8"))
        original = deepcopy(registry.get("scrub_hare"))
        _, configured = configure(source, registry, Factors(300, 2000, "small", 8, growth_days=90), 7)
        self.assertEqual(configured.get("scrub_hare")["growth"]["days_to_adult"], 90)
        self.assertEqual(registry.get("scrub_hare"), original)
        for value in (-1, True, 1.5):
            with self.subTest(days=value), self.assertRaises(ValueError):
                Factors(300, 2000, "small", 8, growth_days=value)
