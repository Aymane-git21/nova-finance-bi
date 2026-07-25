"""Curated aggregate extracts for SAP Analytics Cloud.

The SAC trial acquires data by file import only - there is no live connection -
so the story runs on pre-aggregated, pre-joined CSVs rather than on the journal.
Producing them here rather than exporting them from HANA removes HANA from
SAC's critical path entirely, and because both are computed from the same seeded
dataset the numbers are identical either way.

Each extract is shaped for a specific SAC model: flat, one row per grain, all
dimensions resolved to their descriptions, measures already signed. SAC's
modeller is not the place to discover that revenue needed a sign flip.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .calendar_ import WorkingDays
from .plan import signed_amount


def pl_actuals(
    journal: pd.DataFrame,
    dim_company: pd.DataFrame,
    dim_gl_account: pd.DataFrame,
) -> pd.DataFrame:
    """Group P&L at (entity, period, account group) grain."""
    frame = journal.copy()
    frame["amount"] = signed_amount(frame)

    accounts = dim_gl_account.set_index("gl_account")
    frame["account_group"] = frame["gl_account"].map(accounts["account_group"])
    frame["account_group_name"] = frame["gl_account"].map(accounts["account_group_name"])
    frame["pl_section"] = frame["gl_account"].map(accounts["pl_section"])

    grouped = (
        frame.groupby(
            ["company_code", "fiscal_year", "fiscal_period", "pl_section",
             "account_group", "account_group_name"],
            observed=True,
        )
        .agg(
            amount_group_currency=("amount", "sum"),
            line_count=("journal_id", "count"),
            manual_line_count=(
                "document_type",
                lambda s: int(s.isin(config.MANUAL_DOCUMENT_TYPES).sum()),
            ),
        )
        .reset_index()
    )

    names = dim_company.set_index("company_code")["company_name"]
    grouped.insert(1, "company_name", grouped["company_code"].map(names))
    grouped["amount_group_currency"] = grouped["amount_group_currency"].round(2)
    return grouped


def programme_costs(
    journal: pd.DataFrame,
    dim_programme: pd.DataFrame,
    dim_gl_account: pd.DataFrame,
) -> pd.DataFrame:
    """Programme cost at (programme, entity, period, account group) grain."""
    frame = journal[journal["programme_id"].notna()].copy()
    frame["amount"] = signed_amount(frame)
    frame["account_group"] = frame["gl_account"].map(
        dim_gl_account.set_index("gl_account")["account_group"]
    )

    grouped = (
        frame.groupby(
            ["programme_id", "company_code", "fiscal_year", "fiscal_period", "account_group"],
            observed=True,
        )["amount"]
        .sum()
        .round(2)
        .reset_index()
        .rename(columns={"amount": "amount_group_currency"})
    )

    programmes = dim_programme.set_index("programme_id")
    grouped.insert(1, "programme_name", grouped["programme_id"].map(programmes["programme_name"]))
    grouped.insert(2, "programme_type", grouped["programme_id"].map(programmes["programme_type"]))
    grouped["total_budget_eur"] = grouped["programme_id"].map(programmes["total_budget_eur"])
    return grouped


def close_tasks(
    fact_close_tasks: pd.DataFrame,
    dim_close_task: pd.DataFrame,
    dim_company: pd.DataFrame,
    working_days: WorkingDays,
) -> pd.DataFrame:
    """Close monitor: every task, plus days-to-close on the hard-close milestone."""
    frame = fact_close_tasks.copy()
    tasks = dim_close_task.set_index("task_id")
    frame["task_name"] = frame["task_id"].map(tasks["task_name"])
    frame["task_sequence"] = frame["task_id"].map(tasks["task_sequence"])
    frame["target_working_day"] = frame["task_id"].map(tasks["target_working_day"])
    frame["company_name"] = frame["company_code"].map(
        dim_company.set_index("company_code")["company_name"]
    )

    # Days to close is defined only on the hard-close task, and only where that
    # task actually completed. An open period reports as open, never as zero.
    days = []
    for period_end, actual, task_id in zip(
        frame["period_end_date"], frame["actual_completion_date"], frame["task_id"]
    ):
        if task_id != config.HARD_CLOSE_TASK or actual is None or pd.isna(actual):
            days.append(None)
        else:
            days.append(working_days.count_after(period_end, actual))
    frame["days_to_close"] = days
    frame["is_period_open"] = frame["actual_completion_date"].isna()

    return frame[[
        "close_task_id", "company_code", "company_name", "fiscal_year", "fiscal_period",
        "task_id", "task_name", "task_sequence", "target_working_day",
        "period_end_date", "due_date", "actual_completion_date",
        "delay_working_days", "days_to_close", "is_period_open",
    ]]


def budget_actual(
    journal: pd.DataFrame,
    fact_budget: pd.DataFrame,
    fact_forecast: pd.DataFrame,
    dim_gl_account: pd.DataFrame,
) -> pd.DataFrame:
    """The planning model source: Actual, Budget and Forecast stacked on a Version.

    Budget is annual and is phased evenly across twelve periods here, which is
    the rule stated in docs/kpi-definitions.md. Applying it once, at extract
    time, keeps every consumer working off the same phasing instead of each
    reinventing it.
    """
    actual = journal[journal["fiscal_period"] <= 12].copy()
    actual["amount"] = signed_amount(actual)
    actual["account_group"] = actual["gl_account"].map(
        dim_gl_account.set_index("gl_account")["account_group"]
    )
    actual["programme_key"] = actual["programme_id"].fillna("(none)")
    actual_rows = (
        actual.groupby(
            ["company_code", "programme_key", "account_group", "fiscal_year", "fiscal_period"],
            observed=True,
        )["amount"]
        .sum()
        .reset_index()
        .rename(columns={"amount": "amount_group_currency"})
    )
    actual_rows["version"] = "ACTUAL"

    budget = fact_budget.copy()
    budget["programme_key"] = budget["programme_id"].fillna("(none)")
    budget_annual = (
        budget.groupby(
            ["company_code", "programme_key", "account_group", "fiscal_year"],
            observed=True,
        )["amount_group_currency"]
        .sum()
        .reset_index()
    )
    periods = pd.DataFrame({"fiscal_period": range(1, 13)})
    budget_rows = budget_annual.merge(periods, how="cross")
    budget_rows["amount_group_currency"] = (
        budget_rows["amount_group_currency"] / 12.0
    ).round(2)
    budget_rows["version"] = "BUDGET"

    # Only the most recent snapshot per (year, period) reaches the story - a
    # planning model showing four overlapping forecasts of the same period is a
    # model nobody can read.
    forecast = fact_forecast.copy()
    forecast["programme_key"] = forecast["programme_id"].fillna("(none)")
    latest = (
        forecast.sort_values("horizon_periods")
        .groupby(
            ["company_code", "programme_key", "fiscal_year", "fiscal_period", "cost_center"],
            observed=True,
        )
        .first()
        .reset_index()
    )
    forecast_rows = (
        latest.groupby(
            ["company_code", "programme_key", "fiscal_year", "fiscal_period"], observed=True
        )["amount_group_currency"]
        .sum()
        .round(2)
        .reset_index()
    )
    forecast_rows["account_group"] = "(all)"
    forecast_rows["version"] = "FORECAST"

    columns = [
        "company_code", "programme_key", "account_group", "fiscal_year",
        "fiscal_period", "version", "amount_group_currency",
    ]
    stacked = pd.concat(
        [actual_rows[columns], budget_rows[columns], forecast_rows[columns]],
        ignore_index=True,
    )
    return stacked.rename(columns={"programme_key": "programme_id"})
