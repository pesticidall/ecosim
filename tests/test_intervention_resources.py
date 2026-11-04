import unittest
from copy import deepcopy
from unittest.mock import patch

from core.content_registry import ContentRegistry
from simulation.calendar import CalendarState, Month
from simulation.daily_cycle import run_day
from simulation.intervention_resources import (
    FeedType, InterventionResources, recover_intervention_resources,
    reserve_supplementary_food, spend_intervention_resources, supplementary_food_cost,
    reserve_population_introduction, reserve_population_removal,
)
from simulation.monthly_cycle import acknowledge_month_review, run_month
from simulation.world_state import WorldState


class TestInterventionResources(unittest.TestCase):
    def test_introduction_reserves_independent_charge_and_shared_ic(self):
        original = InterventionResources()
        introduced = reserve_population_introduction(original)
        self.assertEqual(introduced.ic, 6)
        self.assertEqual(introduced.introduction_cooldown_months, 3)
        self.assertEqual(introduced.removal_cooldown_months, 0)
        removed = reserve_population_removal(introduced)
        self.assertEqual(removed.ic, 3)
        self.assertEqual(removed.removal_cooldown_months, 2)
        self.assertEqual(removed.introduction_cooldown_months, 3)
        self.assertEqual((removed.herbivore_stock_kg, removed.carnivore_stock_kg), (1000, 500))
        reverse = reserve_population_introduction(reserve_population_removal(original))
        self.assertEqual(reverse, removed)
        self.assertEqual(original, InterventionResources())

    def test_introduction_rejects_unavailable_charge_or_ic_without_mutation(self):
        for resources in (InterventionResources(ic=3.5),
                          InterventionResources(introduction_cooldown_months=1)):
            before = deepcopy(resources)
            with self.subTest(resources=resources), self.assertRaises(ValueError):
                reserve_population_introduction(resources)
            self.assertEqual(resources, before)
        for value, error in ((True, TypeError), (1.5, TypeError), (-1, ValueError), (4, ValueError)):
            with self.subTest(value=value), self.assertRaises(error):
                InterventionResources(introduction_cooldown_months=value)

    def test_introduction_recovers_once_per_completed_month_across_year(self):
        resources = reserve_population_introduction(InterventionResources())
        for year, month, remaining in ((1, Month.NOVEMBER, 2), (1, Month.DECEMBER, 1),
                                       (2, Month.JANUARY, 0)):
            resources = recover_intervention_resources(resources, year, month)
            self.assertEqual(resources.introduction_cooldown_months, remaining)
            self.assertIs(recover_intervention_resources(resources, year, month), resources)
            if remaining:
                with self.assertRaises(ValueError):
                    reserve_population_introduction(resources)
        self.assertEqual(reserve_population_introduction(resources).introduction_cooldown_months, 3)

    def test_introduction_recovery_rolls_back_with_failed_month_completion(self):
        world, registry = WorldState(1), ContentRegistry()
        world.intervention_resources = reserve_population_introduction(world.intervention_resources)
        for _ in range(30):
            run_day(world, registry)
        self.assertEqual(world.intervention_resources.introduction_cooldown_months, 3)
        before = deepcopy(world)
        with patch("simulation.daily_cycle.summarize_month", side_effect=ValueError("summary failed")):
            with self.assertRaises(ValueError):
                run_day(world, registry)
        self.assertEqual(world, before)
        run_day(world, registry)
        self.assertEqual(world.intervention_resources.introduction_cooldown_months, 2)
        run_month(world, registry)
        acknowledge_month_review(world)
        run_day(world, registry)
        self.assertEqual(world.intervention_resources.introduction_cooldown_months, 2)

    def test_new_world_starts_with_global_full_balances(self):
        world = WorldState(1)
        self.assertEqual(world.intervention_resources, InterventionResources(10.0, 1000.0, 500.0))
        other = WorldState(1)
        world.intervention_resources = spend_intervention_resources(world.intervention_resources, 4.0)
        self.assertEqual(world.intervention_resources.ic, 6.0)
        self.assertEqual(other.intervention_resources.ic, 10.0)

    def test_food_cost_schedule_and_independent_stock_debits(self):
        full = InterventionResources()
        for amount, cost in ((50, 1), (100, 1), (150, 2), (200, 2), (500, 5), (1000, 10)):
            with self.subTest(amount=amount):
                self.assertEqual(supplementary_food_cost(amount), cost)
                result = reserve_supplementary_food(full, FeedType.HERBIVORE, amount)
                self.assertEqual(result.ic, 10 - cost)
                self.assertEqual(result.herbivore_stock_kg, 1000 - amount)
                self.assertEqual(result.carnivore_stock_kg, 500)
        meat = reserve_supplementary_food(full, FeedType.CARNIVORE, 500)
        self.assertEqual(meat, InterventionResources(5, 1000, 0))
        self.assertEqual(full, InterventionResources())

    def test_rejects_insufficient_ic_stock_and_invalid_quantities_atomically(self):
        for resources, feed_type, amount in (
            (InterventionResources(ic=0.5), FeedType.HERBIVORE, 50),
            (InterventionResources(herbivore_stock_kg=50), FeedType.HERBIVORE, 100),
            (InterventionResources(carnivore_stock_kg=0), FeedType.CARNIVORE, 50),
            (InterventionResources(), FeedType.CARNIVORE, 550),
        ):
            before = deepcopy(resources)
            with self.subTest(resources=resources, amount=amount), self.assertRaises(ValueError):
                reserve_supplementary_food(resources, feed_type, amount)
            self.assertEqual(resources, before)
        for amount, error in ((True, TypeError), ("50", TypeError), (0, ValueError), (25, ValueError),
                              (51, ValueError), (-50, ValueError), (1050, ValueError),
                              (float("inf"), ValueError), (float("nan"), ValueError)):
            with self.subTest(amount=amount), self.assertRaises(error):
                supplementary_food_cost(amount)
        with self.assertRaises(TypeError):
            reserve_supplementary_food(InterventionResources(), "herbivore", 50)

    def test_ic_and_stock_state_and_spending_enforce_caps_and_precision(self):
        for ic in (-0.5, 10.5, 0.25, float("nan"), float("inf")):
            with self.subTest(ic=ic), self.assertRaises(ValueError):
                InterventionResources(ic=ic)
        for kwargs in ({"herbivore_stock_kg": -1}, {"herbivore_stock_kg": 1001},
                       {"carnivore_stock_kg": 501}, {"carnivore_stock_kg": float("nan")}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                InterventionResources(**kwargs)
        with self.assertRaises(TypeError):
            InterventionResources(ic=True)
        for cost in (0, 0.25, -0.5, 10.5):
            with self.subTest(cost=cost), self.assertRaises(ValueError):
                spend_intervention_resources(InterventionResources(), cost)
        self.assertEqual(spend_intervention_resources(InterventionResources(), 0.5).ic, 9.5)

    def test_monthly_recovery_uses_confirmed_refills_and_clamps_to_caps(self):
        result = recover_intervention_resources(InterventionResources(6, 800, 400), 1, Month.JANUARY)
        self.assertEqual(result.ic, 8)
        self.assertEqual(result.herbivore_stock_kg, 900)
        self.assertEqual(result.carnivore_stock_kg, 450)
        capped = recover_intervention_resources(InterventionResources(10, 975, 475), 1, Month.JANUARY)
        self.assertEqual((capped.ic, capped.herbivore_stock_kg, capped.carnivore_stock_kg), (10, 1000, 500))
        self.assertEqual(capped.last_recovered_month, (1, Month.JANUARY))

    def test_same_month_cannot_recover_again_even_after_more_spending(self):
        recovered = recover_intervention_resources(InterventionResources(6, 800, 400), 1, Month.JANUARY)
        spent = reserve_supplementary_food(recovered, FeedType.HERBIVORE, 100)
        self.assertIs(recover_intervention_resources(spent, 1, Month.JANUARY), spent)
        february = recover_intervention_resources(spent, 1, Month.FEBRUARY)
        self.assertEqual(february.ic, min(10, spent.ic + 2))
        with self.assertRaises(ValueError):
            recover_intervention_resources(february, 1, Month.JANUARY)

    def test_four_ic_recovers_over_two_completed_months_and_stays_capped(self):
        resources = InterventionResources(ic=6)
        for number, month in enumerate(list(Month)[:8], 1):
            resources = recover_intervention_resources(resources, 1, month)
            self.assertEqual(resources.ic, min(10, 6 + number * 2))

    def test_daily_runner_recovers_at_completion_not_on_review_or_next_day(self):
        world, registry = WorldState(1), ContentRegistry()
        world.intervention_resources = InterventionResources(6, 800, 400)
        for _ in range(30):
            run_day(world, registry)
        self.assertEqual(world.intervention_resources, InterventionResources(6, 800, 400))
        last = run_day(world, registry)
        self.assertEqual(last.intervention_resources_before, InterventionResources(6, 800, 400))
        expected = InterventionResources(8, 900, 450, (1, Month.JANUARY))
        self.assertEqual(world.intervention_resources, expected)
        self.assertEqual(last.intervention_resources_after, expected)
        self.assertEqual(world.monthly_summaries[1][Month.JANUARY].days[-1].intervention_resources_after, expected)
        run_month(world, registry)
        acknowledge_month_review(world)
        random_before = world.random_generator.getstate()
        run_day(world, registry)
        self.assertEqual(world.intervention_resources, expected)
        self.assertEqual(world.random_generator.getstate(), random_before)

    def test_failed_month_end_rolls_back_recovery_and_retry_grants_it_once(self):
        world, registry = WorldState(1), ContentRegistry()
        world.intervention_resources = InterventionResources(6, 800, 400)
        for _ in range(30):
            run_day(world, registry)
        before, random_before = deepcopy(world), world.random_generator.getstate()
        with patch("simulation.daily_cycle.summarize_month", side_effect=ValueError("summary failed")):
            with self.assertRaises(ValueError):
                run_day(world, registry)
        self.assertEqual(world, before)
        self.assertEqual(world.random_generator.getstate(), random_before)
        run_day(world, registry)
        self.assertEqual(world.intervention_resources, InterventionResources(8, 900, 450, (1, Month.JANUARY)))

    def test_copy_resume_preserves_recovery_stamp_through_year_boundary(self):
        world = WorldState(1, calendar=CalendarState(1, Month.DECEMBER))
        world.intervention_resources = InterventionResources(6, 500, 100)
        registry = ContentRegistry()
        for _ in range(15):
            run_day(world, registry)
        resumed = deepcopy(world)
        for state in (world, resumed):
            run_month(state, registry)
            acknowledge_month_review(state)
            run_month(state, registry)
        self.assertEqual(world, resumed)
        self.assertEqual(world.intervention_resources, InterventionResources(10, 700, 200, (2, Month.JANUARY)))

    def test_initial_partial_month_does_not_grant_unearned_monthly_recovery(self):
        world = WorldState(1, calendar=CalendarState(1, Month.JANUARY, 31))
        world.intervention_resources = InterventionResources(ic=5)
        run_day(world, ContentRegistry())
        self.assertEqual(world.intervention_resources, InterventionResources(ic=5))
