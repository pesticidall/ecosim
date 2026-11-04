"""Audit the game's configured ration against its juvenile biomass rule.

These are model consistency calculations, not biological feeding recommendations.
"""

from math import isclose, isfinite


def growth_budget(definition, month_length=31):
    """Return a fully-fed, no-mortality bound for one juvenile in a fixed month.

    Zero intake has no finite maturation bound and is represented by None so the
    evidence remains strict JSON. Partial nutrition and real competition can only
    delay growth beyond this optimistic bound.
    """
    if isinstance(month_length, bool) or not isinstance(month_length, int) or month_length <= 0:
        raise ValueError("Growth budget month length must be a positive integer.")
    config = definition["growth"]
    mass = definition["typical_adult_mass_kg"]
    fraction = config["newborn_mass_fraction"]
    days = config["days_to_adult"]
    efficiency = config.get("biomass_gain_per_food_kg", 0.25)
    monthly_food = definition["food_requirement_per_animal_per_cycle"]
    for value in (mass, fraction, efficiency, monthly_food):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            raise ValueError("Growth budget values must be finite numbers.")
    if mass <= 0 or not 0 < fraction < 1 or not 0 < efficiency <= 1 or monthly_food < 0:
        raise ValueError("Growth budget values are outside their supported ranges.")
    if isinstance(days, bool) or not isinstance(days, int) or days <= 0:
        raise ValueError("Growth budget maturation days must be a positive integer.")
    gain = mass * (1 - fraction)
    needed_daily_food = gain / days / efficiency
    available_daily_food = monthly_food / month_length
    food_limited_days = gain / (available_daily_food * efficiency) if available_daily_food else None
    feasible = available_daily_food >= needed_daily_food or isclose(available_daily_food, needed_daily_food, rel_tol=1e-12)
    separate = config.get("feeding_model", "shared") == "separate"
    if separate:
        # Full feeding now means maintenance plus the separately requested meal.
        food_limited_days, feasible = days, True
    return {
        "month_length": month_length,
        "declared_minimum_days": days,
        "biomass_to_gain_kg": gain,
        "daily_food_kg": available_daily_food,
        "feeding_model": config.get("feeding_model", "shared"),
        "additional_growth_food_kg_per_day": needed_daily_food if separate else 0.0,
        "daily_food_for_target_kg": needed_daily_food,
        "monthly_food_for_target_kg": needed_daily_food * month_length,
        "food_limited_days": food_limited_days,
        "effective_minimum_days": max(days, food_limited_days) if food_limited_days is not None else None,
        "target_feasible_when_fully_fed": feasible,
    }
