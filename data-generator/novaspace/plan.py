"""FACT_BUDGET and FACT_FORECAST - plan data derived from the actuals.

Plan data is generated *from* the actuals rather than independently, because
that is how it works in reality: a budget is last year's outturn plus an
argument, and a forecast is this year's actuals plus a guess about the rest.
Generating them independently would produce variances that are pure noise, and
a variance chart made of noise teaches nothing.

Nothing here is rigged against the overspending programme. Its budget is built
by exactly the same rule as every other programme's. The overrun shows up as
variance because the actuals ramp away from a budget that was set honestly -
which is the only version of that story worth putting on a dashboard.

``programme_id`` is nullable, and pandas silently drops null group keys and
refuses to match them in joins. Every grouping and merge in this module routes
programme through a sentinel to avoid losing the non-programme rows, which are
roughly 30% of the dataset.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from . import config
from .calendar_ import WorkingDays, period_end_date
from .harmonise import signed_amount

NO_PROGRAMME = "__NONE__"

__all__ = ["build_fact_budget", "build_fact_forecast", "signed_amount"]


def _actuals_by_period(
    journal: pd.DataFrame, dim_gl_account: pd.DataFrame
) -> pd.DataFrame:
    """Signed actuals at (entity, cost centre, account group, programme, period)."""
    regular = journal[journal["fiscal_period"] <= 12].copy()
    regular["signed"] = signed_amount(regular)

    groups = dim_gl_account.set_index("gl_account")["account_group"]
    regular["account_group"] = regular["gl_account"].map(groups)

    # Revenue lines carry no cost centre; they belong to no cost-centre budget.
    regular = regular[regular["cost_center"].notna()]
    regular["programme_key"] = regular["programme_id"].fillna(NO_PROGRAMME)

    return (
        regular.groupby(
            ["company_code", "fiscal_year", "fiscal_period", "cost_center",
             "account_group", "programme_key"],
            observed=True,
        )["signed"]
        .sum()
        .reset_index()
    )


def build_fact_budget(
    rng: np.random.Generator, journal: pd.DataFrame, dim_gl_account: pd.DataFrame
) -> pd.DataFrame:
    """Annual budget per entity x cost centre x account group x programme.

    Anchored on the prior year's actuals plus a growth assumption. The first
    covered year has no prior year, so it anchors on itself - which is why
    FY2023 variances are small and FY2025's are not.
    """
    by_period = _actuals_by_period(journal, dim_gl_account)
    annual = (
        by_period.groupby(
            ["company_code", "fiscal_year", "cost_center", "account_group", "programme_key"],
            observed=True,
        )["signed"]
        .sum()
        .reset_index()
        .rename(columns={"signed": "actual_annual"})
    )

    # FY2026 is only closed through P6. Annualising it would understate the
    # anchor by half, so budget years always anchor on a *complete* prior year.
    complete_years = [
        y for y in range(config.FIRST_FISCAL_YEAR, config.LAST_FISCAL_YEAR + 1)
        if y != config.LAST_FISCAL_YEAR
    ]

    rows = []
    for fiscal_year in range(config.FIRST_FISCAL_YEAR, config.LAST_FISCAL_YEAR + 1):
        if fiscal_year - 1 in complete_years:
            anchor_year = fiscal_year - 1
            growth = 1.0 + config.BUDGET_GROWTH_RATE
        else:
            anchor_year = fiscal_year
            growth = 1.0

        anchor = annual[annual["fiscal_year"] == anchor_year]
        if anchor.empty:
            continue

        amounts = anchor["actual_annual"].to_numpy()
        noise = rng.normal(1.0, config.BUDGET_NOISE_SIGMA, size=len(anchor))
        budget = np.round(amounts * growth * noise, 2)

        frame = pd.DataFrame({
            "company_code": anchor["company_code"].to_numpy(),
            "fiscal_year": fiscal_year,
            "cost_center": anchor["cost_center"].to_numpy(),
            "account_group": anchor["account_group"].to_numpy(),
            "programme_key": anchor["programme_key"].to_numpy(),
            "version": config.BUDGET_VERSION,
            "amount_group_currency": budget,
        })
        rows.append(frame)

    budget_frame = pd.concat(rows, ignore_index=True)
    budget_frame = budget_frame[
        budget_frame["amount_group_currency"].abs() >= config.BUDGET_MIN_ANNUAL_EUR
    ].reset_index(drop=True)

    budget_frame["programme_id"] = budget_frame["programme_key"].replace(
        {NO_PROGRAMME: None}
    )
    budget_frame = budget_frame.drop(columns=["programme_key"])
    budget_frame.insert(0, "budget_id", np.arange(1, len(budget_frame) + 1, dtype=np.int64))

    return budget_frame[[
        "budget_id", "company_code", "fiscal_year", "cost_center", "account_group",
        "programme_id", "version", "amount_group_currency",
    ]]


def build_fact_forecast(
    rng: np.random.Generator,
    journal: pd.DataFrame,
    dim_gl_account: pd.DataFrame,
    working_days: WorkingDays,
    min_annual_eur: float = 50_000.0,
) -> pd.DataFrame:
    """Quarterly rolling forecast snapshots.

    Each snapshot forecasts every remaining period of its fiscal year. Error
    widens with horizon by construction, and widens fastest on the programme
    that is running away - because a programme nobody has understood yet is
    exactly the one nobody forecasts correctly.
    """
    by_period = _actuals_by_period(journal, dim_gl_account)

    # Forecasting is done at cost-centre x programme level, not per account
    # group: KPI-07 reports accuracy by cost centre and horizon, and a forecast
    # split finer than the decision it supports is wasted rows.
    actuals = (
        by_period.groupby(
            ["company_code", "fiscal_year", "fiscal_period", "cost_center", "programme_key"],
            observed=True,
        )["signed"]
        .sum()
        .reset_index()
    )

    annual = (
        actuals.groupby(
            ["company_code", "fiscal_year", "cost_center", "programme_key"], observed=True
        )["signed"]
        .agg(total="sum", mean_period="mean")
        .reset_index()
    )
    combos = annual[annual["total"].abs() >= min_annual_eur]

    last_closed = {
        year: (config.LAST_CLOSED_PERIOD_IN_FINAL_YEAR
               if year == config.LAST_FISCAL_YEAR else 12)
        for year in range(config.FIRST_FISCAL_YEAR, config.LAST_FISCAL_YEAR + 1)
    }

    frames = []
    for fiscal_year in range(config.FIRST_FISCAL_YEAR, config.LAST_FISCAL_YEAR + 1):
        year_combos = combos[combos["fiscal_year"] == fiscal_year]
        if year_combos.empty:
            continue
        year_actuals = actuals[actuals["fiscal_year"] == fiscal_year]

        for version in config.FORECAST_VERSIONS:
            snapshot_after = config.FORECAST_SNAPSHOT_AFTER_PERIOD[version]
            # A snapshot cannot be taken before its base period has closed.
            if snapshot_after > last_closed[fiscal_year]:
                continue

            targets = pd.DataFrame({"fiscal_period": range(snapshot_after + 1, 13)})
            if targets.empty:
                continue

            grid = year_combos.merge(targets, how="cross")
            grid = grid.merge(
                year_actuals,
                on=["company_code", "fiscal_year", "cost_center", "programme_key",
                    "fiscal_period"],
                how="left",
            )

            # Where the period has not happened yet, the forecaster only has a
            # run-rate to go on. That is the honest base for an open period.
            base = grid["signed"].to_numpy(dtype=float, na_value=np.nan)
            base = np.where(np.isnan(base), grid["mean_period"].to_numpy(), base)

            horizon = grid["fiscal_period"].to_numpy() - snapshot_after
            sigma = (
                config.FORECAST_ERROR_BASE + config.FORECAST_ERROR_SLOPE * horizon
            )
            sigma = np.where(
                grid["programme_key"].to_numpy() == config.OVERSPEND_PROGRAMME,
                sigma * config.FORECAST_ERROR_OVERSPEND_MULTIPLIER,
                sigma,
            )
            error = rng.normal(0.0, sigma)

            snapshot_date = working_days.nth_after(
                period_end_date(fiscal_year, snapshot_after), 5
            )

            frames.append(pd.DataFrame({
                "company_code": grid["company_code"].to_numpy(),
                "cost_center": grid["cost_center"].to_numpy(),
                "programme_key": grid["programme_key"].to_numpy(),
                "fiscal_year": fiscal_year,
                "fiscal_period": grid["fiscal_period"].to_numpy(),
                "version": version,
                "snapshot_date": snapshot_date,
                "horizon_periods": horizon.astype(np.int32),
                "amount_group_currency": np.round(base * (1.0 + error), 2),
            }))

    forecast = pd.concat(frames, ignore_index=True)
    forecast["programme_id"] = forecast["programme_key"].replace({NO_PROGRAMME: None})
    forecast = forecast.drop(columns=["programme_key"])
    forecast.insert(0, "forecast_id", np.arange(1, len(forecast) + 1, dtype=np.int64))

    return forecast[[
        "forecast_id", "company_code", "cost_center", "programme_id", "fiscal_year",
        "fiscal_period", "version", "snapshot_date", "horizon_periods",
        "amount_group_currency",
    ]]
