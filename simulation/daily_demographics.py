from dataclasses import dataclass, field
from math import floor, fsum, isclose, isfinite

from core.content_registry import ContentRegistry
from simulation.calendar import Month, days_in_month
from simulation.carrion import create_carrion_from_death
from simulation.condition_cohorts import cohorts_after_population_loss
from simulation.daily_feeding import DailyFeedingResult
from simulation.deaths import DeathRecord, create_starvation_death, with_age_loss
from simulation.feeding import calculate_population_food_requirement
from simulation.world_state import RegionState
from simulation.nutrition import NutritionalState, reconcile_nutrition, update_condition
from simulation.growth import GrowthCohort, GrowthChange, adult_count, mass_units, grow_cohorts, plan_growth_loss, commit_growth_loss


def _finite_number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field} must be numeric.")
    if not isfinite(value):
        raise ValueError(f"{field} must be finite.")


@dataclass(frozen=True)
class DemographicCarry:
    """Retain population-level fractional changes across dates and months."""

    births: float = 0.0
    starvation: float = 0.0

    def __post_init__(self):
        for field, value in (("birth carry", self.births), ("starvation carry", self.starvation)):
            _finite_number(value, field)
            if not 0 <= value < 1:
                raise ValueError(f"{field} must be between zero inclusive and one exclusive.")


@dataclass(frozen=True)
class PopulationDailyDemographics:
    starting_population: int
    starvation_deaths: int
    births: int
    ending_population: int
    carry: DemographicCarry


def _split_expected_change(expected: float, carry: float) -> tuple[int, float]:
    total = fsum((expected, carry))
    _finite_number(total, "Accumulated change")
    nearest = round(total)
    # Avoid postponing a whole animal due solely to repeated floating-point
    # division, while retaining even very small positive fractional changes.
    if nearest >= 1 and isclose(total, nearest, rel_tol=0.0, abs_tol=1e-12):
        total = float(nearest)
    whole = floor(total)
    return whole, total - whole


def resolve_population_daily_demographics(
    population: int, monthly_birth_rate: float, nutrition_ratio: float,
    month_length: int, carry: DemographicCarry = DemographicCarry(),
    *, starvation_deficit: float | None = None,
    reproduction_food_threshold: float = 0.0,
    breeding_population: int | None = None,
) -> PopulationDailyDemographics:
    """Accumulate daily changes, applying starvation before reproduction.

    Starvation expectation is current population times food deficit divided by
    month length. Birth expectation uses surviving population, monthly birth
    rate, and current nutrition. Populations evolve daily; this is not a replay
    of the legacy monthly rounding rule. Extinction discards pending fractions.
    """
    for field, value, minimum in (("population", population, 0), ("month_length", month_length, 1)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{field} must be an integer.")
        if value < minimum:
            raise ValueError(f"{field} must be at least {minimum}.")
    _finite_number(monthly_birth_rate, "monthly_birth_rate")
    _finite_number(nutrition_ratio, "nutrition_ratio")
    if monthly_birth_rate < 0:
        raise ValueError("monthly_birth_rate must be nonnegative.")
    if not 0 <= nutrition_ratio <= 1:
        raise ValueError("nutrition_ratio must be between zero and one.")
    _finite_number(reproduction_food_threshold, "reproduction_food_threshold")
    if not 0 <= reproduction_food_threshold < 1:
        raise ValueError("reproduction_food_threshold must be between zero inclusive and one exclusive.")
    deficit = 1 - nutrition_ratio if starvation_deficit is None else starvation_deficit
    _finite_number(deficit, "starvation_deficit")
    if not 0 <= deficit <= 1:
        raise ValueError("starvation_deficit must be normalized.")
    if population == 0:
        return PopulationDailyDemographics(0, 0, 0, 0, DemographicCarry())
    deaths, death_carry = _split_expected_change(population * deficit / month_length, carry.starvation)
    deaths = min(deaths, population)
    survivors = population - deaths
    if breeding_population is not None and (isinstance(breeding_population, bool) or not isinstance(breeding_population, int) or not 0 <= breeding_population <= survivors):
        raise ValueError("Breeding population must be an available surviving adult count.")
    if survivors == 0:
        return PopulationDailyDemographics(population, deaths, 0, 0, DemographicCarry())
    births, birth_carry = _split_expected_change(
        (survivors if breeding_population is None else breeding_population) * monthly_birth_rate * max(0.0, (nutrition_ratio - reproduction_food_threshold) / (1 - reproduction_food_threshold)) / month_length, carry.births,
    )
    return PopulationDailyDemographics(
        population, deaths, births, survivors + births, DemographicCarry(birth_carry, death_carry),
    )


@dataclass(frozen=True)
class RegionDailyDemographicsResult:
    year: int
    month: Month
    day: int
    births: dict[str, int]
    starvation_deaths: dict[str, int]
    starvation_death_records: dict[str, tuple[DeathRecord, ...]]
    condition_recovery_kg: dict[str, float] = field(default_factory=dict)
    growth_changes: dict[str | None, dict[str, GrowthChange]] = field(default_factory=dict)


def apply_region_daily_demographics(
    region: RegionState, registry: ContentRegistry, feeding: DailyFeedingResult,
) -> RegionDailyDemographicsResult:
    """Commit validated local daily changes after feeding and carrion decay.

    Remainders live in world state so pause/resume preserves fractional changes.
    New starvation carrion is unreserved and first becomes available tomorrow.
    Missing mass in legacy definitions does not invent carcass biomass.
    """
    length = days_in_month(feeding.year, feeding.month)
    collections = (
        [(habitat_id, habitat, feeding.habitat_feeding[habitat_id])
         for habitat_id, habitat in sorted(region.habitats.items())]
        if region.habitats else [(None, region, feeding.regional_feeding)]
    )
    plans = []
    births = {animal_id: 0 for animal_id in region.animal_populations}
    deaths = dict(births)
    death_records, recovery_costs, growth_changes = {}, {}, {}
    for habitat_id, state, local_feeding in collections:
        if set(local_feeding) != set(state.animal_populations):
            raise ValueError("Daily demographic feeding must cover the current local populations.")
        for animal_id, population in sorted(state.animal_populations.items()):
            definition = registry.get(animal_id)
            nutrition = local_feeding[animal_id]
            required = calculate_population_food_requirement(population, definition, period_fraction=1.0 / length)
            if not isclose(required, nutrition.required_amount):
                raise ValueError("Daily feeding demand must match the current surviving population.")
            nutritional_state, pressure = None, None
            if habitat_id is not None and "nutrition" in definition:
                nutritional_state = reconcile_nutrition(
                    state.nutritional_states.get(animal_id, NutritionalState(population)), population)
                reserve_before = nutritional_state.reserve_kg
                nutritional_state, pressure = update_condition(nutritional_state, nutrition.nutrition_ratio, definition["nutrition"], required)
                recovery_costs[animal_id] = recovery_costs.get(animal_id, 0.0) + reserve_before - nutritional_state.reserve_kg
            change = resolve_population_daily_demographics(
                population, definition.get("birth_rate_per_animal_per_cycle", 0.0),
                nutrition.nutrition_ratio, length, state.demographic_carry.get(animal_id, DemographicCarry()),
                starvation_deficit=pressure,
                reproduction_food_threshold=definition.get("reproduction_food_threshold", 0.0),
            )
            growth_cohorts = None
            growth_loss = None
            removed_units = float(change.starvation_deaths)
            if "growth" in definition:
                previous = state.growth_cohorts.get(animal_id, ())
                growth_loss = plan_growth_loss(state, animal_id, change.starvation_deaths)
                surviving_cohorts, removed_units = growth_loss.cohorts, growth_loss.removed_mass_units
                survivors = population - change.starvation_deaths
                change = resolve_population_daily_demographics(
                    population, definition.get("birth_rate_per_animal_per_cycle", 0.0), nutrition.nutrition_ratio,
                    length, state.demographic_carry.get(animal_id, DemographicCarry()),
                    starvation_deficit=pressure, reproduction_food_threshold=definition.get("reproduction_food_threshold", 0.0),
                    breeding_population=adult_count(survivors, surviving_cohorts),
                )
                mass = definition["typical_adult_mass_kg"]
                # Equal per-capita allocation: deaths' and adults' intake cannot
                # be reassigned as juvenile growth. This caps retained biomass,
                # not a full energy/maintenance or maternal gestation model.
                if definition["growth"].get("feeding_model", "shared") == "separate":
                    meal = getattr(feeding, "growth_meals", {}).get(habitat_id, {}).get(animal_id)
                    if meal is None:
                        raise ValueError("Separate juvenile growth requires recorded growth feeding.")
                    previous_juveniles = sum(c.count for c in previous)
                    if meal.juvenile_count != previous_juveniles:
                        raise ValueError("Growth feeding must match the current juvenile count.")
                    juvenile_food = (meal.feeding.consumed_amount * sum(c.count for c in surviving_cohorts) / previous_juveniles
                                     if previous_juveniles else 0.0)
                else:
                    juvenile_food = nutrition.consumed_amount * sum(c.count for c in surviving_cohorts) / population if population else 0.0
                food_growth_units = juvenile_food * definition["growth"].get("biomass_gain_per_food_kg", 0.25) / mass
                growth_cohorts, gained = grow_cohorts(surviving_cohorts, definition["growth"], nutrition.nutrition_ratio, food_growth_units)
                newborn_units = change.births * definition["growth"]["newborn_mass_fraction"]
                if change.births:
                    growth_cohorts += (GrowthCohort(change.births, definition["growth"]["newborn_mass_fraction"]),)
                growth_changes.setdefault(habitat_id, {})[animal_id] = GrowthChange(
                    mass_units(population, previous) * mass, removed_units * mass, gained * mass,
                    newborn_units * mass, mass_units(change.ending_population, growth_cohorts) * mass,
                )
            cohorts = None
            deposit = None
            if habitat_id is not None:
                cohorts = cohorts_after_population_loss(
                    population, state.injury_cohorts.get(animal_id, ()), change.starvation_deaths,
                )
                if change.starvation_deaths and "typical_adult_mass_kg" in definition:
                    death = create_starvation_death(
                        {**definition, "typical_adult_mass_kg": definition["typical_adult_mass_kg"] * removed_units / change.starvation_deaths},
                        change.starvation_deaths,
                    )
                    death = with_age_loss(death, growth_loss)
                    deposit = create_carrion_from_death(death, habitat_id)
                    death_records.setdefault(habitat_id, []).append(death)
            plans.append((state, animal_id, change, cohorts, deposit, nutritional_state, growth_cohorts, growth_loss))
            births[animal_id] = births.get(animal_id, 0) + change.births
            deaths[animal_id] = deaths.get(animal_id, 0) + change.starvation_deaths
    # No population, carry, injury, or carrion mutations until all plans pass.
    for state, animal_id, change, cohorts, deposit, nutritional_state, growth_cohorts, growth_loss in plans:
        if growth_loss is not None:
            commit_growth_loss(state, animal_id, growth_loss)
        if growth_cohorts is not None:
            if growth_cohorts:
                state.growth_cohorts[animal_id] = growth_cohorts
            else:
                state.growth_cohorts.pop(animal_id, None)
        state.animal_populations[animal_id] = change.ending_population
        if change.ending_population:
            state.demographic_carry[animal_id] = change.carry
        else:
            state.demographic_carry.pop(animal_id, None)
        if cohorts is not None and animal_id in state.injury_cohorts:
            state.injury_cohorts[animal_id] = cohorts
        if deposit is not None:
            state.carrion_deposits.append(deposit)
        if nutritional_state is not None:
            if change.ending_population:
                state.nutritional_states[animal_id] = reconcile_nutrition(nutritional_state, change.ending_population)
            else:
                state.nutritional_states.pop(animal_id, None)
    if region.habitats:
        for animal_id in births:
            region.animal_populations[animal_id] = sum(
                habitat.animal_populations.get(animal_id, 0) for habitat in region.habitats.values()
            )
    return RegionDailyDemographicsResult(
        feeding.year, feeding.month, feeding.day, births, deaths,
        {habitat_id: tuple(records) for habitat_id, records in death_records.items()},
        recovery_costs, growth_changes,
    )
