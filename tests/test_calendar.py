import unittest


class TestCalendar(unittest.TestCase):
    def test_identifies_gregorian_leap_years(self) -> None:
        from simulation.calendar import is_leap_year

        examples = (
            (1, False),
            (4, True),
            (100, False),
            (400, True),
            (2024, True),
            (2025, False),
        )
        for year, expected_result in examples:
            with self.subTest(year=year):
                self.assertEqual(is_leap_year(year), expected_result)

    def test_defines_twelve_months_in_calendar_order(self) -> None:
        from simulation.calendar import Month

        self.assertEqual(
            tuple(month.display_name for month in Month),
            (
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
            ),
        )
        self.assertEqual(
            tuple(month.value for month in Month),
            tuple(range(1, 13)),
        )

    def test_defines_day_and_night_activity_phases(self) -> None:
        from simulation.calendar import ActivityPhase

        self.assertEqual(
            [phase.value for phase in ActivityPhase],
            ["day", "night"],
        )

    def test_returns_days_in_month(self) -> None:
        from simulation.calendar import Month, days_in_month

        examples = (
            (1, Month.JANUARY, 31),
            (1, Month.APRIL, 30),
            (1, Month.FEBRUARY, 28),
            (4, Month.FEBRUARY, 29),
            (100, Month.FEBRUARY, 28),
            (400, Month.FEBRUARY, 29),
        )
        for year, month, expected_days in examples:
            with self.subTest(year=year, month=month):
                self.assertEqual(days_in_month(year, month), expected_days)

    def test_calendar_starts_in_january_of_year_one(self) -> None:
        from simulation.calendar import CalendarState, Month

        calendar = CalendarState()

        self.assertIs(calendar.month, Month.JANUARY)
        self.assertEqual(calendar.year, 1)
        self.assertEqual(calendar.day, 1)

    def test_advances_one_calendar_day_across_boundaries(self) -> None:
        from simulation.calendar import CalendarState, Month

        examples = (
            ((1, Month.JANUARY, 1), (1, Month.JANUARY, 2)),
            ((1, Month.JANUARY, 31), (1, Month.FEBRUARY, 1)),
            ((1, Month.APRIL, 30), (1, Month.MAY, 1)),
            ((1, Month.FEBRUARY, 28), (1, Month.MARCH, 1)),
            ((4, Month.FEBRUARY, 28), (4, Month.FEBRUARY, 29)),
            ((4, Month.FEBRUARY, 29), (4, Month.MARCH, 1)),
            ((100, Month.FEBRUARY, 28), (100, Month.MARCH, 1)),
            ((400, Month.FEBRUARY, 28), (400, Month.FEBRUARY, 29)),
            ((1, Month.DECEMBER, 31), (2, Month.JANUARY, 1)),
        )
        for starting_date, expected_date in examples:
            with self.subTest(date=starting_date):
                calendar = CalendarState(*starting_date)
                calendar.advance_day()
                self.assertEqual(
                    (calendar.year, calendar.month, calendar.day),
                    expected_date,
                )

    def test_rejects_invalid_calendar_day(self) -> None:
        from simulation.calendar import CalendarState, Month

        for day in (True, False, 1.5, "1", None):
            with self.subTest(day=day):
                with self.assertRaisesRegex(TypeError, "day.*integer"):
                    CalendarState(day=day)
        for month, day in (
            (Month.JANUARY, 0),
            (Month.JANUARY, -1),
            (Month.JANUARY, 32),
            (Month.APRIL, 31),
            (Month.FEBRUARY, 29),
        ):
            with self.subTest(month=month, day=day):
                with self.assertRaisesRegex(ValueError, "day.*selected month"):
                    CalendarState(year=1, month=month, day=day)

    def test_month_advance_resets_day(self) -> None:
        from simulation.calendar import CalendarState, Month

        calendar = CalendarState(year=4, month=Month.JANUARY, day=31)
        calendar.advance_month()
        self.assertEqual((calendar.year, calendar.month, calendar.day),
                         (4, Month.FEBRUARY, 1))

    def test_daily_advances_cover_complete_common_and_leap_years(self) -> None:
        from simulation.calendar import CalendarState, Month

        for year, expected_days in ((1, 365), (4, 366), (100, 365), (400, 366)):
            with self.subTest(year=year):
                calendar = CalendarState(year=year)
                dates = set()
                for _ in range(expected_days):
                    dates.add((calendar.year, calendar.month, calendar.day))
                    calendar.advance_day()
                self.assertEqual(len(dates), expected_days)
                self.assertEqual(
                    (calendar.year, calendar.month, calendar.day),
                    (year + 1, Month.JANUARY, 1),
                )

    def test_advances_to_the_next_month_and_year(self) -> None:
        from simulation.calendar import CalendarState, Month

        examples = (
            (
                CalendarState(year=1, month=Month.JANUARY),
                Month.FEBRUARY,
                1,
            ),
            (
                CalendarState(year=1, month=Month.DECEMBER),
                Month.JANUARY,
                2,
            ),
        )
        for calendar, expected_month, expected_year in examples:
            with self.subTest(month=calendar.month, year=calendar.year):
                calendar.advance_month()
                self.assertIs(calendar.month, expected_month)
                self.assertEqual(calendar.year, expected_year)


if __name__ == "__main__":
    unittest.main()
