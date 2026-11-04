"""Aggregate juvenile growth; adults are the untracked remainder of a population."""

from dataclasses import dataclass
from bisect import bisect_right
from math import floor, fsum, isfinite


@dataclass(frozen=True)
class GrowthCohort:
    count: int
    mass_fraction: float

    def __post_init__(self):
        if isinstance(self.count, bool) or not isinstance(self.count, int) or self.count <= 0:
            raise ValueError("Growth cohort count must be a positive integer.")
        if isinstance(self.mass_fraction, bool) or not isinstance(self.mass_fraction, (int, float)) or not isfinite(self.mass_fraction) or not 0 < self.mass_fraction < 1:
            raise ValueError("Juvenile mass fraction must be finite and between zero and one exclusive.")


def adult_count(population, cohorts):
    if isinstance(population, bool) or not isinstance(population, int) or population < 0:
        raise ValueError("Growth population must be a nonnegative integer.")
    adults = population - sum(c.count for c in cohorts)
    if adults < 0:
        raise ValueError("Juvenile count exceeds population.")
    return adults


def mass_units(population, cohorts):
    return adult_count(population, cohorts) + fsum(c.count * c.mass_fraction for c in cohorts)


LOSS_PHASE_STEP = 0.6180339887498949


def validate_loss_phase(phase):
    if isinstance(phase, bool) or not isinstance(phase, (int, float)) or not isfinite(phase) or not 0 <= phase < 1:
        raise ValueError("Growth loss phase must be finite and between zero inclusive and one exclusive.")


def remove_members(population, cohorts, count, *, phase=0.5):
    """Take size-weighted systematic samples without replacement.

    Age and injury membership are independent aggregate marginals. This does not
    claim to identify an individual juvenile in the hunt's injury participant pool.
    Returns survivors and removed biomass in adult-mass units, without mutation.
    """
    adults = adult_count(population, cohorts)
    validate_loss_phase(phase)
    if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= population:
        raise ValueError("Growth loss must be an available integer population count.")
    if not count:
        return cohorts, 0.0
    if not cohorts:
        return (), float(count)
    # Canonical mass bins make equivalent cohort splitting and ordering irrelevant.
    bins = {}
    for cohort in cohorts:
        bins[cohort.mass_fraction] = bins.get(cohort.mass_fraction, 0) + cohort.count
    fractions = [1.0] + sorted(bins)
    sizes = [adults] + [bins[fraction] for fraction in fractions[1:]]
    cumulative, total = [], 0
    for size in sizes:
        total += size
        cumulative.append(total)
    losses = [0] * len(sizes)
    for index in range(count):
        rank = min(population - 1, floor((index + phase) * population / count))
        losses[bisect_right(cumulative, rank)] += 1
    survivors = tuple(GrowthCohort(size - loss, fraction)
                      for size, loss, fraction in zip(sizes[1:], losses[1:], fractions[1:]) if size > loss)
    removed = fsum(loss * fraction for loss, fraction in zip(losses, fractions))
    return survivors, removed


@dataclass(frozen=True)
class GrowthLossPlan:
    cohorts: tuple[GrowthCohort, ...]
    removed_mass_units: float
    next_phase: float
    count: int
    adults: int
    juveniles: int


def plan_growth_loss(state, animal, count):
    """Preview one age loss without advancing state or consuming randomness."""
    population = state.animal_populations.get(animal, 0)
    cohorts = state.growth_cohorts.get(animal, ())
    phase = state.growth_loss_phases.get(animal, 0.5)
    remaining, removed = remove_members(population, cohorts, count, phase=phase)
    adults = adult_count(population, cohorts) - adult_count(population - count, remaining)
    return GrowthLossPlan(remaining, removed, (phase + count * LOSS_PHASE_STEP) % 1.0,
                          count, adults, count - adults)


def commit_growth_loss(state, animal, plan):
    """Commit the already-previewed cohorts and advance the phase exactly once."""
    tracked = animal in state.growth_cohorts or animal in state.growth_loss_phases
    if state.animal_populations.get(animal, 0) == plan.count:
        state.growth_cohorts.pop(animal, None)
        state.growth_loss_phases.pop(animal, None)
    elif tracked and plan.count:
        state.growth_cohorts[animal] = plan.cohorts
        state.growth_loss_phases[animal] = plan.next_phase


def grow_cohorts(cohorts, config, coverage, food_growth_units):
    """Use a day's existing full food ration; unfed juveniles do not grow."""
    if isinstance(coverage, bool) or not isinstance(coverage, (int, float)) or not isfinite(coverage) or not 0 <= coverage <= 1:
        raise ValueError("Growth food coverage must be normalized and finite.")
    if isinstance(food_growth_units, bool) or not isinstance(food_growth_units, (int, float)) or not isfinite(food_growth_units) or food_growth_units < 0:
        raise ValueError("Growth food budget must be finite and nonnegative.")
    increment = (1 - config["newborn_mass_fraction"]) / config["days_to_adult"] * coverage
    juvenile_count = sum(c.count for c in cohorts)
    # Allocate equal absolute growth per juvenile before capping at adulthood.
    # Scaling each cohort's remaining growth instead makes near-adult animals
    # approach maturity asymptotically while younger cohorts keep arriving.
    increment = min(increment, food_growth_units / juvenile_count) if juvenile_count else 0.0
    resulting, gain = [], 0.0
    for cohort in cohorts:
        fraction = min(1.0, cohort.mass_fraction + increment)
        if increment > 0 and 1 - fraction < 1e-12:
            fraction = 1.0
        gain += cohort.count * (fraction - cohort.mass_fraction)
        if fraction < 1:
            resulting.append(GrowthCohort(cohort.count, fraction))
    return tuple(resulting), gain


@dataclass(frozen=True)
class GrowthChange:
    starting_biomass_kg: float
    starvation_biomass_kg: float
    growth_biomass_kg: float
    newborn_biomass_kg: float
    ending_biomass_kg: float
