import unittest

from simulation.condition_cohorts import InjuryCohort, healthy_population, transition_injury_cohorts
from simulation.injuries import calculate_injury_modifiers, create_injury_from_trauma
from simulation.world_state import HabitatState


class TestConditionCohorts(unittest.TestCase):
    def test_population_losses_preserve_valid_proportional_cohort_counts(self) -> None:
        from simulation.condition_cohorts import cohorts_after_population_loss

        original = (InjuryCohort((self.minor,), 2), InjuryCohort((self.major,), 1))
        for deaths in range(7):
            with self.subTest(deaths=deaths):
                updated = cohorts_after_population_loss(6, original, deaths)
                survivors = 6 - deaths
                healthy = healthy_population(survivors, updated)
                self.assertEqual(healthy + sum(c.count for c in updated), survivors)
                self.assertEqual(updated, cohorts_after_population_loss(6, original, deaths))
                self.assertEqual(original[0].count, 2)
                for cohort in updated:
                    self.assertLessEqual(cohort.count, 2 if cohort.injuries == (self.minor,) else 1)
        self.assertEqual(cohorts_after_population_loss(6, original, 3), (InjuryCohort((self.minor,), 1),))
        self.assertEqual(cohorts_after_population_loss(6, original, 6), ())
        self.assertEqual(cohorts_after_population_loss(0, (), 0), ())

    def test_population_losses_reject_invalid_death_counts(self) -> None:
        from simulation.condition_cohorts import cohorts_after_population_loss

        for deaths, error in ((True, TypeError), (1.5, TypeError), (-1, ValueError), (4, ValueError)):
            with self.subTest(deaths=deaths), self.assertRaises(error):
                cohorts_after_population_loss(3, (), deaths)
    def test_samples_condition_by_count_and_skips_uniform_group_rolls(self) -> None:
        from random import Random
        from simulation.condition_cohorts import select_participant_injuries

        cohorts = (InjuryCohort((self.minor,), 1),)
        for seed, expected in ((1, ()), (2, (self.minor,))):
            with self.subTest(seed=seed):
                random_source = Random(seed)
                reference = Random(seed)
                reference.random()
                self.assertEqual(select_participant_injuries(3, cohorts, random_source), expected)
                self.assertEqual(random_source.getstate(), reference.getstate())
        for population, groups, expected in ((3, (), ()), (1, cohorts, (self.minor,))):
            random_source = Random(1)
            before = random_source.getstate()
            self.assertEqual(select_participant_injuries(population, groups, random_source), expected)
            self.assertEqual(random_source.getstate(), before)

    def setUp(self) -> None:
        self.minor = create_injury_from_trauma("attack", 1.0)
        self.major = create_injury_from_trauma("counterattack", 4.0)

    def test_preserves_healthy_and_injured_members_in_habitat_state(self) -> None:
        habitat = HabitatState("local", animal_populations={"prey": 5})
        original = (InjuryCohort((self.minor,), 1),)
        updated = transition_injury_cohorts(5, original, (), (self.minor,))
        habitat.injury_cohorts["prey"] = updated
        self.assertEqual(updated, (InjuryCohort((self.minor,), 2),))
        self.assertEqual(healthy_population(5, habitat.injury_cohorts["prey"]), 3)
        self.assertEqual(original[0].count, 1)
        self.assertEqual(calculate_injury_modifiers(updated[0].injuries).mobility_modifier, 0.9)

    def test_cumulative_injury_moves_only_one_member(self) -> None:
        original = (InjuryCohort((self.minor,), 2),)
        updated = transition_injury_cohorts(5, original, (self.minor,), (self.minor, self.major))
        self.assertEqual(updated, (
            InjuryCohort((self.minor,), 1), InjuryCohort((self.minor, self.major), 1),
        ))
        self.assertEqual(healthy_population(5, updated), 3)
        self.assertAlmostEqual(calculate_injury_modifiers(updated[1].injuries).power_modifier, 0.45)

    def test_death_removes_injured_or_healthy_participant(self) -> None:
        original = (InjuryCohort((self.minor,), 1),)
        updated = transition_injury_cohorts(2, original, (self.minor,), (self.minor, self.major), survived=False)
        self.assertEqual(updated, ())
        self.assertEqual(healthy_population(1, updated), 1)
        updated = transition_injury_cohorts(2, original, (), (self.major,), survived=False)
        self.assertEqual(updated, original)
        self.assertEqual(healthy_population(1, updated), 0)

    def test_rejects_impossible_counts_and_missing_participants(self) -> None:
        for count in (0, -1):
            with self.subTest(count=count), self.assertRaises(ValueError):
                InjuryCohort((self.minor,), count)
        with self.assertRaises(TypeError):
            InjuryCohort((self.minor,), True)
        with self.assertRaises(ValueError):
            healthy_population(1, (InjuryCohort((self.minor,), 2),))
        with self.assertRaisesRegex(ValueError, "No healthy animal"):
            transition_injury_cohorts(1, (InjuryCohort((self.minor,), 1),), (), (self.major,))
        with self.assertRaisesRegex(ValueError, "starting injury cohort"):
            transition_injury_cohorts(1, (), (self.minor,), (self.major,))
        with self.assertRaises(ValueError):
            transition_injury_cohorts(0, (), (), (self.major,))
