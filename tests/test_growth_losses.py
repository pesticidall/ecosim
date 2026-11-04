from copy import deepcopy
from random import Random
import unittest

from simulation.growth import (
    GrowthCohort, LOSS_PHASE_STEP, adult_count, mass_units, remove_members,
    plan_growth_loss, commit_growth_loss,
)
from simulation.world_state import HabitatState, WorldState
from simulation.daily_cycle import run_day


class TestGrowthLosses(unittest.TestCase):
    def state(self):
        return HabitatState("local", animal_populations={"prey": 319},
                            growth_cohorts={"prey": tuple(GrowthCohort(2, 0.5) for _ in range(121))})

    def test_fragmenting_or_reordering_equivalent_cohorts_does_not_change_losses(self):
        merged = (GrowthCohort(242, 0.5),)
        split = tuple(GrowthCohort(2, 0.5) for _ in range(121))
        for phase in (0, 0.1, 0.5, 0.999999):
            for count in (0, 1, 2, 7, 80, 319):
                with self.subTest(phase=phase, count=count):
                    a, amass = remove_members(319, merged, count, phase=phase)
                    b, bmass = remove_members(319, split, count, phase=phase)
                    self.assertEqual(amass, bmass)
                    self.assertEqual(mass_units(319-count, a), mass_units(319-count, b))
        cohorts = (GrowthCohort(3, 0.2), GrowthCohort(2, 0.7))
        self.assertEqual(remove_members(8, cohorts, 3), remove_members(8, cohorts[::-1], 3))

    def test_repeated_single_losses_follow_animal_counts_in_a_fixed_mix(self):
        state = self.state()
        cohorts = state.growth_cohorts["prey"]
        adult_losses = 0
        for _ in range(10000):
            # Replace the removed animal with one of the same age to hold the
            # composition fixed while testing phase progression across events.
            state.growth_cohorts["prey"] = cohorts
            plan = plan_growth_loss(state, "prey", 1)
            adult_losses += plan.adults
            commit_growth_loss(state, "prey", plan)
        self.assertLess(abs(adult_losses - 10000 * 77 / 319), 5)

    def test_preview_is_pure_and_commits_phase_only_once(self):
        state = self.state()
        before = deepcopy(state)
        first = plan_growth_loss(state, "prey", 1)
        self.assertEqual(first, plan_growth_loss(state, "prey", 1))
        self.assertEqual(state, before)
        self.assertEqual((first.adults, first.juveniles), (0, 1))
        self.assertEqual(first.removed_mass_units, 0.5)
        commit_growth_loss(state, "prey", first)
        state.animal_populations["prey"] -= 1
        self.assertAlmostEqual(state.growth_loss_phases["prey"], (0.5 + LOSS_PHASE_STEP) % 1)
        self.assertEqual(sum(c.count for c in state.growth_cohorts["prey"]), 241)

    def test_batches_conserve_integer_counts_and_exact_removed_mass(self):
        cohorts = (GrowthCohort(3, 0.2), GrowthCohort(2, 0.7))
        for phase in (0, 0.001, 0.5, 0.999999):
            for count in range(9):
                with self.subTest(phase=phase, count=count):
                    survivors, removed = remove_members(8, cohorts, count, phase=phase)
                    self.assertAlmostEqual(mass_units(8, cohorts), mass_units(8-count, survivors) + removed)
                    self.assertGreaterEqual(adult_count(8-count, survivors), 0)
        for phase in (True, -0.1, 1, float("nan"), float("inf")):
            with self.subTest(invalid=phase), self.assertRaises(ValueError):
                remove_members(8, cohorts, 1, phase=phase)

    def test_single_hunt_mass_matches_the_committed_age_loss(self):
        import test_habitat_hunting
        fixture = test_habitat_hunting.TestHabitatHunting()
        fixture.setUp()
        fixture.predator["food_requirement_per_animal_per_cycle"] = 2
        fixture.habitat.growth_cohorts["prey"] = (GrowthCohort(1, 0.2),)
        result = fixture.hunting_round(Random(1))
        self.assertEqual(result.meals[0].death.body_mass_kg, 2)
        self.assertEqual((result.meals[0].death.adult_count, result.meals[0].death.juvenile_count), (0, 1))
        self.assertEqual(fixture.habitat.animal_populations["prey"], 1)
        self.assertEqual(adult_count(1, fixture.habitat.growth_cohorts["prey"]), 1)
        self.assertAlmostEqual(fixture.habitat.growth_loss_phases["prey"], (0.5 + LOSS_PHASE_STEP) % 1)

    def test_group_hunt_uses_same_phase_for_carcass_and_subtraction(self):
        import test_group_predation
        fixture = test_group_predation.TestGroupPredation()
        fixture.setUp()
        fixture.habitat.growth_cohorts["prey"] = (GrowthCohort(2, 0.2),)
        result = fixture.commit()
        self.assertEqual(result.meal.death.body_mass_kg, 2)
        self.assertEqual((result.meal.death.adult_count, result.meal.death.juvenile_count), (0, 1))
        self.assertEqual(fixture.habitat.growth_cohorts["prey"], (GrowthCohort(1, 0.2),))
        phase = fixture.habitat.growth_loss_phases["prey"]
        self.assertAlmostEqual(phase, (0.5 + LOSS_PHASE_STEP) % 1)
        with self.assertRaises(ValueError):
            fixture.commit()
        self.assertEqual(fixture.habitat.growth_loss_phases["prey"], phase)

    def test_starvation_records_selected_age_and_saved_phase(self):
        import test_growth
        from simulation.daily_demographics import DemographicCarry
        region, registry = test_growth.TestGrowth().setup_region(population=3, food=0)
        habitat = region.habitats["local"]
        habitat.growth_cohorts["animal"] = (GrowthCohort(2, 0.2),)
        habitat.demographic_carry["animal"] = DemographicCarry(starvation=0.99)
        world = WorldState(7, regions={"region": region})
        result = run_day(world, registry).region_results["region"]
        self.assertEqual(result.demographics.starvation_death_records["local"][0].body_mass_kg, 2)
        self.assertEqual(result.demographics.starvation_death_records["local"][0].juvenile_count, 1)
        self.assertEqual(habitat.growth_cohorts["animal"], (GrowthCohort(1, 0.2),))
        self.assertAlmostEqual(result.ending_state.growth_loss_phases["local"]["animal"], (0.5 + LOSS_PHASE_STEP) % 1)
        self.assertEqual(result.starting_state.growth_loss_phases["local"], {})

    def test_removal_clears_phase_at_extinction_and_introduction_starts_fresh(self):
        import test_population_introduction
        from simulation.interventions import remove_population, introduce_population
        world, registry = test_population_introduction.TestPopulationIntroduction().setup_world()
        habitat = world.regions["region"].habitats["local"]
        habitat.growth_cohorts["animal"] = (GrowthCohort(2, 0.2),)
        habitat.growth_loss_phases["animal"] = 0.25
        remove_population(world, registry, "region", "local", "animal", 4)
        self.assertNotIn("animal", habitat.growth_loss_phases)
        self.assertNotIn("animal", habitat.growth_cohorts)
        self.assertEqual(habitat.carrion_deposits, [])
        introduce_population(world, registry, "region", "local", "animal", 2)
        self.assertNotIn("animal", habitat.growth_loss_phases)

    def test_phase_survives_maturation_and_failed_day_replays(self):
        import test_growth_feeding
        world, registry, habitat = test_growth_feeding.TestGrowthFeeding().setup_world()
        habitat.growth_cohorts["animal"] = (GrowthCohort(1, 0.99),)
        habitat.growth_loss_phases["animal"] = 0.25
        replay = deepcopy(world)
        self.assertEqual(run_day(world, registry), run_day(replay, registry))
        self.assertEqual(habitat.growth_cohorts, {})
        self.assertEqual(habitat.growth_loss_phases["animal"], 0.25)
        habitat.growth_loss_phases["animal"] = 1.0
        before = deepcopy(world)
        with self.assertRaisesRegex(ValueError, "loss phase"):
            run_day(world, registry)
        self.assertEqual(world.regions, before.regions)
        self.assertEqual(world.daily_history, before.daily_history)
        self.assertEqual(world.random_generator.getstate(), before.random_generator.getstate())

    def test_actual_scenario_age_counts_and_live_biomass_reconcile_and_replay(self):
        from pathlib import Path
        from scripts.investigate_capacity import Factors, run_case
        root = Path(__file__).resolve().parents[1]
        factors = Factors(300, 2000, "small", 8, True, 60, True, 0.9, 30, 0.9, 90, separate_growth_food=True)
        first = run_case(root, factors, 7, 3)
        self.assertEqual(first, run_case(root, factors, 7, 3))
        for month in first["monthly"]:
            for values in month["regions"]["redgrass_savanna"]["species"].values():
                for cause in ("predation", "starvation"):
                    self.assertEqual(values[f"{cause}_deaths"], values[f"adult_{cause}_deaths"]
                        + values[f"juvenile_{cause}_deaths"] + values[f"unclassified_{cause}_deaths"])

    def test_death_age_metadata_cannot_invent_or_omit_animals(self):
        from simulation.deaths import DeathRecord, DeathCause
        for adults, juveniles in ((0, None), (True, 0), (0, -1), (1, 1)):
            with self.subTest(adults=adults, juveniles=juveniles), self.assertRaises(ValueError):
                DeathRecord("animal", DeathCause.PREDATION, 1, 2.0, adults, juveniles)

    def test_surviving_group_condition_changes_do_not_advance_age_phase(self):
        import test_group_predation
        from simulation.group_conditions import apply_group_condition_changes
        fixture = test_group_predation.TestGroupPredation()
        fixture.setUp()
        fixture.habitat.growth_cohorts["predator"] = (GrowthCohort(2, 0.2),)
        fixture.habitat.growth_loss_phases["predator"] = 0.35
        apply_group_condition_changes(fixture.region, (fixture.hunter_change,))
        self.assertEqual(fixture.habitat.growth_cohorts["predator"], (GrowthCohort(2, 0.2),))
        self.assertEqual(fixture.habitat.growth_loss_phases["predator"], 0.35)

    def test_healthy_introduction_preserves_existing_phase_and_juveniles(self):
        import test_population_introduction
        from simulation.interventions import introduce_population
        world, registry = test_population_introduction.TestPopulationIntroduction().setup_world()
        habitat = world.regions["region"].habitats["local"]
        habitat.growth_cohorts["animal"] = (GrowthCohort(2, 0.2),)
        habitat.growth_loss_phases["animal"] = 0.25
        introduce_population(world, registry, "region", "local", "animal", 2)
        self.assertEqual(habitat.growth_loss_phases["animal"], 0.25)
        self.assertEqual(habitat.growth_cohorts["animal"], (GrowthCohort(2, 0.2),))
        self.assertEqual(adult_count(6, habitat.growth_cohorts["animal"]), 4)
