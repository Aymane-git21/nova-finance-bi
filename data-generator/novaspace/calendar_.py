"""Fiscal calendar and working-day arithmetic.

Purely deterministic: no randomness, no seed dependency. Same input, same
output, always. Working-day counting is the kind of thing that is easy to get
subtly wrong and impossible to eyeball afterwards, so it lives here on its own
with its own tests rather than inline in the generator.

KPI-01 (days to close) and KPI-03 (late postings) are both defined in working
days after period end. If this module is wrong, both KPIs are wrong and nothing
downstream will reveal it.
"""

from __future__ import annotations

import calendar as _calendar
import datetime as dt
from bisect import bisect_right

import pandas as pd

from . import config


def easter_sunday(year: int) -> dt.date:
    """Easter Sunday for a Gregorian year (anonymous Gregorian algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    lam = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * lam) // 451
    month, day = divmod(h + lam - 7 * m + 114, 31)
    return dt.date(year, month, day + 1)


def holidays(first_year: int, last_year: int) -> set[dt.date]:
    """The group-wide holiday set across the covered years.

    One calendar for all four entities. Per-country calendars are a documented
    simplification, not an oversight - see docs/data-dictionary.md.
    """
    result: set[dt.date] = set()
    for year in range(first_year, last_year + 1):
        for month, day in config.FIXED_HOLIDAYS:
            result.add(dt.date(year, month, day))
        easter = easter_sunday(year)
        for offset in config.EASTER_HOLIDAY_OFFSETS:
            result.add(easter + dt.timedelta(days=offset))
    return result


def period_end_date(fiscal_year: int, fiscal_period: int) -> dt.date:
    """Last calendar day of a fiscal period.

    Special periods 13-16 have no calendar existence of their own; they are
    year-end adjustment buckets and share the fiscal year's final day.
    """
    if fiscal_period > 12:
        return dt.date(fiscal_year, 12, 31)
    last_day = _calendar.monthrange(fiscal_year, fiscal_period)[1]
    return dt.date(fiscal_year, fiscal_period, last_day)


class WorkingDays:
    """Working-day arithmetic over a fixed calendar window.

    Backed by a sorted list of working days plus an index, so every lookup is a
    binary search rather than a day-by-day walk.
    """

    def __init__(self, start: dt.date, end: dt.date, holiday_set: set[dt.date]):
        self.start = start
        self.end = end
        self._holidays = holiday_set
        days: list[dt.date] = []
        current = start
        while current <= end:
            if current.weekday() < 5 and current not in holiday_set:
                days.append(current)
            current += dt.timedelta(days=1)
        self._working_days = days
        self._ordinals = [d.toordinal() for d in days]

    def __len__(self) -> int:
        return len(self._working_days)

    def is_working_day(self, day: dt.date) -> bool:
        return day.weekday() < 5 and day not in self._holidays

    def count_after(self, reference: dt.date, day: dt.date) -> int:
        """Working days in the half-open interval (reference, day].

        This is the definition both KPI-01 and KPI-03 use: how many working
        days have elapsed since a period ended. A completion on the period-end
        date itself counts as zero.
        """
        lo = bisect_right(self._ordinals, reference.toordinal())
        hi = bisect_right(self._ordinals, day.toordinal())
        return hi - lo

    def nth_after(self, reference: dt.date, n: int) -> dt.date:
        """The n-th working day strictly after ``reference`` (n is 1-based)."""
        if n < 1:
            raise ValueError(f"n must be 1-based and positive, got {n}")
        lo = bisect_right(self._ordinals, reference.toordinal())
        index = lo + n - 1
        if index >= len(self._working_days):
            raise IndexError(
                f"working day {n} after {reference} falls outside the calendar "
                f"window ending {self.end}"
            )
        return self._working_days[index]

    def in_period(self, fiscal_year: int, fiscal_period: int) -> list[dt.date]:
        """Every working day inside a fiscal period, in order."""
        if fiscal_period > 12:
            fiscal_period = 12
        first = dt.date(fiscal_year, fiscal_period, 1)
        last = period_end_date(fiscal_year, fiscal_period)
        lo = bisect_right(self._ordinals, first.toordinal() - 1)
        hi = bisect_right(self._ordinals, last.toordinal())
        return self._working_days[lo:hi]


def covered_periods() -> list[tuple[int, int]]:
    """Every regular (fiscal_year, fiscal_period) the dataset covers, in order.

    FY2026 stops at the last closed period - the dataset represents a group
    mid-year, which is what makes run-rate extrapolation and forecast accuracy
    meaningful at all.
    """
    periods: list[tuple[int, int]] = []
    for year in range(config.FIRST_FISCAL_YEAR, config.LAST_FISCAL_YEAR + 1):
        last = (
            config.LAST_CLOSED_PERIOD_IN_FINAL_YEAR
            if year == config.LAST_FISCAL_YEAR
            else 12
        )
        for period in range(1, last + 1):
            periods.append((year, period))
    return periods


def build_dim_date(working_days: WorkingDays) -> pd.DataFrame:
    """DIM_DATE at daily grain across the full calendar window."""
    dates = pd.date_range(config.CALENDAR_START, config.CALENDAR_END, freq="D")
    frame = pd.DataFrame({"date_id": dates})

    frame["calendar_year"] = frame["date_id"].dt.year
    frame["calendar_quarter"] = frame["date_id"].dt.quarter
    frame["calendar_month"] = frame["date_id"].dt.month
    frame["day_of_month"] = frame["date_id"].dt.day
    frame["day_of_week"] = frame["date_id"].dt.dayofweek + 1  # 1 = Monday
    frame["day_name"] = frame["date_id"].dt.day_name()
    frame["is_weekend"] = frame["day_of_week"] >= 6

    as_dates = [d.date() for d in dates]
    frame["is_working_day"] = [working_days.is_working_day(d) for d in as_dates]

    # Fiscal year variant K4: fiscal year = calendar year, period = month.
    frame["fiscal_year"] = frame["calendar_year"]
    frame["fiscal_period"] = frame["calendar_month"]
    frame["period_end_date"] = [
        period_end_date(d.year, d.month) for d in as_dates
    ]

    # Working-day counters within the period. working_day_of_period is 0 on
    # non-working days; working_days_after_period_end keeps counting so that a
    # weekend date still reports how far into the close it sits.
    running = frame.groupby(["fiscal_year", "fiscal_period"])["is_working_day"].cumsum()
    frame["working_days_after_period_end"] = running.astype(int)
    frame["working_day_of_period"] = (
        frame["working_days_after_period_end"].where(frame["is_working_day"], 0).astype(int)
    )

    return frame
