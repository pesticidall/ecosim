from dataclasses import dataclass
from enum import Enum, IntEnum


class ActivityPhase(str, Enum):
    """Name the aggregated daily periods used by activity systems."""

    DAY = "day"
    NIGHT = "night"

class Month(IntEnum):
    """Represent calendar months in chronological numeric order."""

    JANUARY = 1
    FEBRUARY = 2
    MARCH = 3
    APRIL = 4
    MAY = 5
    JUNE = 6
    JULY = 7
    AUGUST = 8
    SEPTEMBER = 9
    OCTOBER = 10
    NOVEMBER = 11
    DECEMBER = 12

    @property
    def display_name(self) -> str:
        """Return the month name formatted for reports."""
        return self.name.title()

@dataclass
class CalendarState:
    """Track the month and year that the next cycle will simulate."""

    year: int = 1
    month: Month = Month.JANUARY
    def advance_month(self) -> None:
        """Advance to the next month and roll December into a new year."""
        if self.month is Month.DECEMBER:
            self.month = Month.JANUARY
            self.year += 1
        else:
            self.month = Month(self.month.value + 1)
MONTH_LENGTHS = (
    31,
    28,
    31,
    30,
    31,
    30,
    31,
    31,
    30,
    31,
    30,
    31,
)
def is_leap_year(year: int) -> bool:
    """Return whether a year follows the Gregorian leap-year rule."""
    return year % 400 == 0 or (
        year % 4 == 0 and year % 100 != 0
    )

def days_in_month(year: int, month: Month) -> int:
    """Return a month's length, including leap-day adjustment."""
    if month is Month.FEBRUARY and is_leap_year(year):
        return 29
    return MONTH_LENGTHS[month.value - 1]
