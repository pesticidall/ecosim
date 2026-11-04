from dataclasses import dataclass
from random import Random

from simulation.injuries import Injury


@dataclass(frozen=True)
class InjuryCohort:
    """Count living animals sharing the same cumulative injury set."""

    injuries: tuple[Injury, ...]
    count: int

    def __post_init__(self) -> None:
        if isinstance(self.count, bool) or not isinstance(self.count, int):
            raise TypeError("Injury cohort count must be an integer.")
        if self.count <= 0:
            raise ValueError("Injury cohort count must be positive.")
        if not isinstance(self.injuries, tuple) or not all(isinstance(i, Injury) for i in self.injuries):
            raise TypeError("Injury cohort injuries must be a tuple of Injury records.")
        if not self.injuries:
            raise ValueError("Healthy animals are implicit, not injury cohorts.")


def healthy_population(population: int, cohorts: tuple[InjuryCohort, ...]) -> int:
    """Validate cohort totals and return the number of healthy animals."""
    if isinstance(population, bool) or not isinstance(population, int):
        raise TypeError("Population must be an integer.")
    if population < 0:
        raise ValueError("Population must not be negative.")
    injured = sum(cohort.count for cohort in cohorts)
    if injured > population:
        raise ValueError("Injured animal count cannot exceed population.")
    return population - injured


def transition_injury_cohorts(
    population: int,
    cohorts: tuple[InjuryCohort, ...],
    previous_injuries: tuple[Injury, ...],
    resulting_injuries: tuple[Injury, ...],
    survived: bool = True,
) -> tuple[InjuryCohort, ...]:
    """Move one participant between conditions, or remove it after death.

    Population is the count before the event. The caller commits the returned
    cohorts alongside the population change; input records remain unchanged.
    """
    healthy = healthy_population(population, cohorts)
    counts: dict[tuple[Injury, ...], int] = {}
    for cohort in cohorts:
        counts[cohort.injuries] = counts.get(cohort.injuries, 0) + cohort.count
    if previous_injuries:
        if counts.get(previous_injuries, 0) <= 0:
            raise ValueError("No animal exists in the starting injury cohort.")
        counts[previous_injuries] -= 1
    elif healthy <= 0:
        raise ValueError("No healthy animal is available for this transition.")
    if survived and resulting_injuries:
        counts[resulting_injuries] = counts.get(resulting_injuries, 0) + 1
    updated = tuple(InjuryCohort(injuries, count) for injuries, count in counts.items() if count)
    healthy_population(population if survived else population - 1, updated)
    return updated


def select_participant_injuries(
    population: int, cohorts: tuple[InjuryCohort, ...], random_source: Random,
) -> tuple[Injury, ...]:
    """Sample a condition group by animal count, avoiding uniform-group rolls."""
    healthy = healthy_population(population, cohorts)
    if population <= 0:
        raise ValueError("No living participant is available.")
    options = [((), healthy)] if healthy else []
    options.extend((cohort.injuries, cohort.count) for cohort in cohorts)
    if len(options) == 1:
        return options[0][0]
    threshold = random_source.random() * population
    cumulative = 0
    for injuries, count in options:
        cumulative += count
        if threshold < cumulative:
            return injuries
    return options[-1][0]


def cohorts_after_population_loss(
    population: int, cohorts: tuple[InjuryCohort, ...], deaths: int,
) -> tuple[InjuryCohort, ...]:
    """Allocate aggregate survivors proportionally across condition groups.

    Largest remainders resolve integer rounding, with stable group-order ties
    (healthy first). This does not introduce injury-dependent mortality.
    """
    healthy = healthy_population(population, cohorts)
    if isinstance(deaths, bool) or not isinstance(deaths, int):
        raise TypeError("Population deaths must be an integer.")
    if not 0 <= deaths <= population:
        raise ValueError("Population deaths must be between zero and population.")
    if deaths == 0:
        return cohorts
    survivors = population - deaths
    if survivors == 0:
        return ()
    groups: dict[tuple[Injury, ...], int] = {(): healthy}
    for cohort in cohorts:
        groups[cohort.injuries] = groups.get(cohort.injuries, 0) + cohort.count
    entries = tuple(groups.items())
    counts = [count * survivors // population for _, count in entries]
    remaining = survivors - sum(counts)
    order = sorted(range(len(entries)),
                   key=lambda index: -(entries[index][1] * survivors % population))
    for index in order[:remaining]:
        counts[index] += 1
    updated = tuple(
        InjuryCohort(injuries, count)
        for (injuries, _), count in zip(entries, counts) if injuries and count
    )
    healthy_population(survivors, updated)
    return updated
