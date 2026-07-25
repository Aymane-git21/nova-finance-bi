"""Working-day arithmetic.

KPI-01 and KPI-03 are both defined in working days after period end. If this
module is wrong, both KPIs are wrong by a constant nobody would ever notice by
looking at a dashboard - so it gets tested against dates verifiable by hand
rather than against its own output.
"""

from __future__ import annotations

import datetime as dt

import pytest

from novaspace import config
from novaspace.calendar_ import (
    WorkingDays,
    covered_periods,
    easter_sunday,
    holidays,
    period_end_date,
)


@pytest.mark.parametrize(
    "year,expected",
    [
        (2023, dt.date(2023, 4, 9)),
        (2024, dt.date(2024, 3, 31)),
        (2025, dt.date(2025, 4, 20)),
        (2026, dt.date(2026, 4, 5)),
        (2027, dt.date(2027, 3, 28)),
    ],
)
def test_easter_sunday_matches_published_dates(year, expected):
    assert easter_sunday(year) == expected


def test_good_friday_and_easter_monday_are_holidays():
    holiday_set = holidays(2025, 2025)
    assert dt.date(2025, 4, 18) in holiday_set  # Good Friday
    assert dt.date(2025, 4, 21) in holiday_set  # Easter Monday


@pytest.mark.parametrize(
    "year,period,expected",
    [
        (2024, 2, dt.date(2024, 2, 29)),   # leap year
        (2023, 2, dt.date(2023, 2, 28)),
        (2025, 12, dt.date(2025, 12, 31)),
        (2025, 13, dt.date(2025, 12, 31)),  # special periods share year end
        (2025, 14, dt.date(2025, 12, 31)),
    ],
)
def test_period_end_date(year, period, expected):
    assert period_end_date(year, period) == expected


@pytest.fixture(scope="module")
def working_days():
    return WorkingDays(dt.date(2023, 1, 1), dt.date(2027, 12, 31), holidays(2023, 2027))


def test_weekends_are_not_working_days(working_days):
    assert not working_days.is_working_day(dt.date(2025, 3, 1))  # Saturday
    assert not working_days.is_working_day(dt.date(2025, 3, 2))  # Sunday
    assert working_days.is_working_day(dt.date(2025, 3, 3))      # Monday


def test_nth_after_skips_a_weekend():
    """31 Jan 2025 is a Friday, so working day 1 of the close is Monday 3 Feb."""
    wd = WorkingDays(dt.date(2025, 1, 1), dt.date(2025, 12, 31), holidays(2025, 2025))
    period_end = dt.date(2025, 1, 31)
    assert wd.nth_after(period_end, 1) == dt.date(2025, 2, 3)
    assert wd.nth_after(period_end, 2) == dt.date(2025, 2, 4)
    assert wd.nth_after(period_end, 5) == dt.date(2025, 2, 7)


def test_nth_after_skips_a_holiday():
    """April 2025 ends Wednesday 30th; 1 May is a holiday, so WD1 is Friday 2nd."""
    wd = WorkingDays(dt.date(2025, 1, 1), dt.date(2025, 12, 31), holidays(2025, 2025))
    assert wd.nth_after(dt.date(2025, 4, 30), 1) == dt.date(2025, 5, 2)


def test_count_after_is_zero_on_the_period_end_itself(working_days):
    period_end = dt.date(2025, 1, 31)
    assert working_days.count_after(period_end, period_end) == 0


def test_count_after_and_nth_after_are_inverse(working_days):
    period_end = dt.date(2025, 6, 30)
    for n in range(1, 15):
        day = working_days.nth_after(period_end, n)
        assert working_days.count_after(period_end, day) == n


def test_nth_after_rejects_zero(working_days):
    with pytest.raises(ValueError):
        working_days.nth_after(dt.date(2025, 1, 31), 0)


def test_in_period_returns_only_that_month(working_days):
    days = working_days.in_period(2025, 2)
    assert days[0] >= dt.date(2025, 2, 1)
    assert days[-1] <= dt.date(2025, 2, 28)
    assert all(d.weekday() < 5 for d in days)


def test_covered_periods_stops_mid_year_in_the_final_year():
    periods = covered_periods()
    assert periods[0] == (config.FIRST_FISCAL_YEAR, 1)
    assert periods[-1] == (
        config.LAST_FISCAL_YEAR,
        config.LAST_CLOSED_PERIOD_IN_FINAL_YEAR,
    )
    # Three complete years plus the partial one.
    assert len(periods) == 36 + config.LAST_CLOSED_PERIOD_IN_FINAL_YEAR


def test_dim_date_working_day_counter_restarts_each_period(dataset):
    frame = dataset.dim_date
    january = frame[(frame["fiscal_year"] == 2025) & (frame["fiscal_period"] == 1)]
    february = frame[(frame["fiscal_year"] == 2025) & (frame["fiscal_period"] == 2)]
    assert january["working_days_after_period_end"].max() >= 20
    assert february["working_days_after_period_end"].min() <= 1
    # Non-working days carry 0 in working_day_of_period but keep the running count.
    weekend = frame[~frame["is_working_day"]]
    assert (weekend["working_day_of_period"] == 0).all()
