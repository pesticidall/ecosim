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
    """Track the next unresolved calendar date."""

    year: int = 1
    month: Month = Month.JANUARY
    day: int = 1

    def __post_init__(self) -> None:
        """Require the initial day to exist in the selected month."""
        if isinstance(self.day, bool) or not isinstance(self.day, int):
            raise TypeError("Calendar day must be an integer.")
        if not 1 <= self.day <= days_in_month(self.year, self.month):
            raise ValueError("Calendar day must exist in the selected month.")

    def advance_day(self) -> None:
        """Mark one date complete and move to the next calendar day."""
        if self.day == days_in_month(self.year, self.month):
            self.advance_month()
        else:
            self.day += 1

    def advance_month(self) -> None:
        """Move to the first day of next month, rolling over the year."""
        if self.month is Month.DECEMBER:
            self.month = Month.JANUARY
            self.year += 1
        else:
            self.month = Month(self.month.value + 1)
        self.day = 1
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
