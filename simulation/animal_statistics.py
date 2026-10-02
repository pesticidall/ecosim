from math import isfinite

WEIGHT_CLASS_UPPER_BOUNDS_KG = (
    ("very_light", 5.0),
    ("light", 20.0),
    ("medium", 75.0),
    ("heavy", 250.0),
)


def weight_class_for_mass(
    mass_kg: int | float,
) -> str:
    """Derive a coarse weight class from a positive finite mass."""
    if isinstance(mass_kg, bool) or not isinstance(
        mass_kg,
        (int, float),
    ):
        raise TypeError(
            "mass_kg must be a number."
        )
    if not isfinite(mass_kg):
        raise ValueError(
            "mass_kg must be finite."
        )
    if mass_kg <= 0:
        raise ValueError(
            "mass_kg must be greater than zero."
        )
    for weight_class, upper_bound_kg in (
        WEIGHT_CLASS_UPPER_BOUNDS_KG
    ):
        if mass_kg < upper_bound_kg:
            return weight_class

    return "very_heavy"
