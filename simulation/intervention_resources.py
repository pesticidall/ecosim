from dataclasses import dataclass, replace
from enum import Enum
from math import ceil, isfinite

from simulation.calendar import Month


# Provisional Playtest B balancing targets.
MAX_IC = 10.0
MONTHLY_IC_RECOVERY = 2.0
HERBIVORE_STOCK_CAPACITY_KG = 1000.0
CARNIVORE_STOCK_CAPACITY_KG = 500.0
HERBIVORE_MONTHLY_REFILL_KG = 100.0
CARNIVORE_MONTHLY_REFILL_KG = 50.0
REMOVAL_IC_COST = 3.0
REMOVAL_RECOVERY_MONTHS = 2
INTRODUCTION_IC_COST = 4.0
INTRODUCTION_RECOVERY_MONTHS = 3


class FeedType(Enum):
    HERBIVORE = "herbivore"
    CARNIVORE = "carnivore"


def _bounded_number(value, field, maximum):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field} must be numeric.")
    if not isfinite(value) or not 0 <= value <= maximum:
        raise ValueError(f"{field} must be finite and between zero and {maximum}.")


def _month_key(year, month):
    if isinstance(year, bool) or not isinstance(year, int):
        raise TypeError("Recovery year must be an integer.")
    if year < 1 or not isinstance(month, Month):
        raise ValueError("Recovery requires a positive year and a Month.")
    return year, month


@dataclass(frozen=True)
class InterventionResources:
    """Global player resources, independent of habitat stores and UI state."""

    ic: float = MAX_IC
    herbivore_stock_kg: float = HERBIVORE_STOCK_CAPACITY_KG
    carnivore_stock_kg: float = CARNIVORE_STOCK_CAPACITY_KG
    last_recovered_month: tuple[int, Month] | None = None
    removal_cooldown_months: int = 0
    introduction_cooldown_months: int = 0

    def __post_init__(self):
        _bounded_number(self.ic, "IC", MAX_IC)
        if self.ic * 2 != int(self.ic * 2):
            raise ValueError("IC must use half-point increments.")
        _bounded_number(self.herbivore_stock_kg, "Herbivore stock", HERBIVORE_STOCK_CAPACITY_KG)
        _bounded_number(self.carnivore_stock_kg, "Carnivore stock", CARNIVORE_STOCK_CAPACITY_KG)
        if isinstance(self.removal_cooldown_months, bool) or not isinstance(self.removal_cooldown_months, int):
            raise TypeError("Removal cooldown must be an integer.")
        if not 0 <= self.removal_cooldown_months <= REMOVAL_RECOVERY_MONTHS:
            raise ValueError("Removal cooldown is outside its recovery interval.")
        if isinstance(self.introduction_cooldown_months, bool) or not isinstance(self.introduction_cooldown_months, int):
            raise TypeError("Introduction cooldown must be an integer.")
        if not 0 <= self.introduction_cooldown_months <= INTRODUCTION_RECOVERY_MONTHS:
            raise ValueError("Introduction cooldown is outside its recovery interval.")
        if self.last_recovered_month is not None:
            if not isinstance(self.last_recovered_month, tuple) or len(self.last_recovered_month) != 2:
                raise ValueError("Last recovered month must be a year/month pair.")
            _month_key(*self.last_recovered_month)


def spend_intervention_resources(
    resources: InterventionResources, ic_cost: float, *,
    herbivore_kg: float = 0.0, carnivore_kg: float = 0.0,
) -> InterventionResources:
    """Return an atomic resource debit; invalid requests leave input untouched."""
    _bounded_number(ic_cost, "IC cost", MAX_IC)
    if ic_cost == 0 or ic_cost * 2 != int(ic_cost * 2):
        raise ValueError("IC cost must be positive and use half-point increments.")
    for amount, field, maximum in (
        (herbivore_kg, "Herbivore deployment", HERBIVORE_STOCK_CAPACITY_KG),
        (carnivore_kg, "Carnivore deployment", CARNIVORE_STOCK_CAPACITY_KG),
    ):
        _bounded_number(amount, field, maximum)
        if amount % 50 != 0:
            raise ValueError(f"{field} must use 50 kg increments.")
    if (ic_cost > resources.ic or herbivore_kg > resources.herbivore_stock_kg
            or carnivore_kg > resources.carnivore_stock_kg):
        raise ValueError("Insufficient intervention capacity or feed stock.")
    return replace(resources, ic=resources.ic - ic_cost,
                   herbivore_stock_kg=resources.herbivore_stock_kg - herbivore_kg,
                   carnivore_stock_kg=resources.carnivore_stock_kg - carnivore_kg)


def supplementary_food_cost(amount_kg: float) -> float:
    _bounded_number(amount_kg, "Food deployment", HERBIVORE_STOCK_CAPACITY_KG)
    if amount_kg == 0 or amount_kg % 50 != 0:
        raise ValueError("Food deployment must be positive and use 50 kg increments.")
    return float(ceil(amount_kg / 100))


def reserve_supplementary_food(resources: InterventionResources, feed_type: FeedType, amount_kg: float) -> InterventionResources:
    """Prepare a food debit without depositing it or inferring compatibility."""
    if not isinstance(feed_type, FeedType):
        raise TypeError("Food reserve type must be a FeedType.")
    return spend_intervention_resources(
        resources, supplementary_food_cost(amount_kg),
        herbivore_kg=amount_kg if feed_type is FeedType.HERBIVORE else 0.0,
        carnivore_kg=amount_kg if feed_type is FeedType.CARNIVORE else 0.0,
    )


def reserve_population_removal(resources: InterventionResources) -> InterventionResources:
    if resources.removal_cooldown_months:
        raise ValueError("Population removal is recovering; its single charge is unavailable.")
    spent = spend_intervention_resources(resources, REMOVAL_IC_COST)
    return replace(spent, removal_cooldown_months=REMOVAL_RECOVERY_MONTHS)


def reserve_population_introduction(resources: InterventionResources) -> InterventionResources:
    """Reserve introduction's independent charge and IC without changing populations."""
    if resources.introduction_cooldown_months:
        raise ValueError("Population introduction is recovering; its single charge is unavailable.")
    spent = spend_intervention_resources(resources, INTRODUCTION_IC_COST)
    return replace(spent, introduction_cooldown_months=INTRODUCTION_RECOVERY_MONTHS)


def recover_intervention_resources(resources: InterventionResources, year: int, month: Month) -> InterventionResources:
    """Recover once for a completed month, retaining unused balances up to caps."""
    completed_month = _month_key(year, month)
    if resources.last_recovered_month == completed_month:
        return resources
    if resources.last_recovered_month is not None and completed_month < resources.last_recovered_month:
        raise ValueError("Cannot recover resources for an earlier month.")
    return replace(
        resources, ic=min(MAX_IC, resources.ic + MONTHLY_IC_RECOVERY),
        herbivore_stock_kg=min(HERBIVORE_STOCK_CAPACITY_KG, resources.herbivore_stock_kg + HERBIVORE_MONTHLY_REFILL_KG),
        carnivore_stock_kg=min(CARNIVORE_STOCK_CAPACITY_KG, resources.carnivore_stock_kg + CARNIVORE_MONTHLY_REFILL_KG),
        last_recovered_month=completed_month,
        removal_cooldown_months=max(0, resources.removal_cooldown_months - 1),
        introduction_cooldown_months=max(0, resources.introduction_cooldown_months - 1),
    )
