"""The L2 harmonised-layer derivations, in Python.

Nothing here is stored in the fact tables. These are exactly the transformations
the HANA L2 layer performs - signed amounts, the manual-posting flag, the
late-posting flag, days to close - and they live in one module so that there is
a single definition of each, shared by the test suite, the SAC extracts and
(later) the calculation views built to match.

The alternative is defining "late posting" three times in three languages and
finding out they disagree when a number on a dashboard cannot be traced. That
failure is silent, which is what makes it worth this module.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .calendar_ import WorkingDays


def signed_amount(journal: pd.DataFrame) -> np.ndarray:
    """Expenses positive, revenue negative.

    Amounts are stored unsigned with direction in ``debit_credit_ind``, as SAP
    stores them. This is the one place that convention is applied.
    """
    return np.where(
        journal["debit_credit_ind"].to_numpy() == "S",
        journal["amount_group_currency"].to_numpy(),
        -journal["amount_group_currency"].to_numpy(),
    )


def is_manual_posting(journal: pd.DataFrame) -> np.ndarray:
    """KPI-02. Manual means somebody typed it: document types SA and SB."""
    return journal["document_type"].isin(config.MANUAL_DOCUMENT_TYPES).to_numpy()


def soft_close_dates(fact_close_tasks: pd.DataFrame) -> pd.Series:
    """Reporting cut-off per (entity, fiscal year, period): the **due** date.

    This uses the date the cut-off was *due*, not the date it was achieved, and
    the distinction decides whether KPI-03 measures anything at all.

    Measuring against the achieved cut-off makes the KPI self-cancelling: an
    entity that runs three days late also gets three extra days for postings to
    arrive in, so its late-posting rate collapses to the group average and the
    slowest closer looks the cleanest. Measured that way here, the chronically
    late entity scored 2.4% against a group average of 2.3% - the story was
    real in the data and invisible in the measure.

    Against the due date, the same entity scores several times the group rate,
    which is the truth. A cut-off an entity sets for itself after the fact is
    not a control.
    """
    soft = fact_close_tasks[fact_close_tasks["task_id"] == config.SOFT_CLOSE_TASK]
    return soft.set_index(["company_code", "fiscal_year", "fiscal_period"])["due_date"]


def is_late_posting(
    journal: pd.DataFrame, fact_close_tasks: pd.DataFrame
) -> np.ndarray:
    """KPI-03. Entered after the entity's reporting cut-off for that period.

    This is the flag that requires ``entry_date`` to exist separately from
    ``posting_date``. A model carrying only the posting date cannot compute it,
    which is the whole modelling point about ACDOCA.

    Special periods are excluded: a year-end adjustment in period 13 is not a
    late period-12 posting, it is a different thing entirely, and counting it as
    late would inflate the KPI for every entity every December.
    """
    cutoff = soft_close_dates(fact_close_tasks)
    keys = pd.MultiIndex.from_arrays([
        journal["company_code"],
        journal["fiscal_year"],
        journal["fiscal_period"].clip(upper=12),
    ])
    cutoff_per_line = pd.to_datetime(pd.Series(cutoff.reindex(keys).to_numpy()))
    entry = pd.to_datetime(journal["entry_date"]).reset_index(drop=True)
    regular = (journal["fiscal_period"] <= 12).to_numpy()
    return (entry.to_numpy() > cutoff_per_line.to_numpy()) & regular


def days_to_close(
    fact_close_tasks: pd.DataFrame, working_days: WorkingDays
) -> pd.DataFrame:
    """KPI-01, per entity and period.

    Periods whose hard close has not completed return NaN, not zero. An open
    period is open; reporting it as a zero-day close would be the single most
    misleading number this dataset could produce.
    """
    hard = fact_close_tasks[
        fact_close_tasks["task_id"] == config.HARD_CLOSE_TASK
    ].copy()

    values = []
    for period_end, actual in zip(hard["period_end_date"], hard["actual_completion_date"]):
        if actual is None or pd.isna(actual):
            values.append(np.nan)
        else:
            values.append(working_days.count_after(period_end, actual))
    hard["days_to_close"] = values

    return hard[[
        "company_code", "fiscal_year", "fiscal_period", "period_end_date",
        "actual_completion_date", "days_to_close",
    ]]


def fx_impact(
    journal: pd.DataFrame, rates: pd.DataFrame, group_by: list[str] | None = None
) -> pd.DataFrame:
    """KPI-06. Group-currency variance caused by rate movement, not by spending.

    The local amount is translated twice - once at the period's actual rate,
    once at the fiscal year's frozen budget rate - and differenced. Entities
    whose local currency is already the group currency contribute exactly zero
    by construction, which is the correctness check built into the measure.
    """
    group_by = group_by or ["company_code", "fiscal_year", "fiscal_period"]

    actual = rates[rates["rate_type"] == config.RATE_TYPE_ACTUAL].set_index(
        ["from_currency", "fiscal_year", "fiscal_period"]
    )["exchange_rate"]
    budget = rates[rates["rate_type"] == config.RATE_TYPE_BUDGET].set_index(
        ["from_currency", "fiscal_year", "fiscal_period"]
    )["exchange_rate"]

    frame = journal.copy()
    keys = pd.MultiIndex.from_arrays([
        frame["local_currency"],
        frame["fiscal_year"],
        frame["fiscal_period"].clip(upper=12),
    ])
    sign = np.where(frame["debit_credit_ind"].to_numpy() == "S", 1.0, -1.0)
    local_signed = frame["amount_local_currency"].to_numpy() * sign

    actual_rate = actual.reindex(keys).to_numpy()
    budget_rate = budget.reindex(keys).to_numpy()

    frame["at_actual_rate"] = local_signed * actual_rate
    frame["at_budget_rate"] = local_signed * budget_rate
    frame["fx_impact"] = frame["at_actual_rate"] - frame["at_budget_rate"]

    # Gross exposure: the turnover the rate acts on, ignoring sign. The net P&L
    # is a thin margin between two large numbers, so expressing FX impact as a
    # share of it produces a meaningless ratio that swings wildly. What is
    # exposed to a rate move is the gross flow, not the profit.
    frame["gross_at_budget_rate"] = (
        frame["amount_local_currency"].to_numpy() * budget_rate
    )

    return (
        frame.groupby(group_by, observed=True)[
            ["at_actual_rate", "at_budget_rate", "fx_impact", "gross_at_budget_rate"]
        ]
        .sum()
        .round(2)
        .reset_index()
    )


def budget_variance(
    journal: pd.DataFrame,
    fact_budget: pd.DataFrame,
    dim_gl_account: pd.DataFrame,
) -> pd.DataFrame:
    """KPI-04. Actual against evenly-phased budget, per programme and period.

    Budget is annual and actuals are periodic, so a phasing rule is unavoidable.
    NovaSpace phases evenly across twelve periods and says so; any other rule is
    defensible, leaving it implicit is not.

    Special periods carry no budget and are excluded rather than folded into
    period 12, which would make December look like an overrun every year.

    Revenue is excluded too, and for the same reason: budgets here are set on
    cost centres, and revenue lines carry no cost centre. Comparing an actual
    that nets revenue against a budget that never contained any is the classic
    way a variance report comes out looking 20% favourable for no reason.
    """
    actual = journal[
        (journal["fiscal_period"] <= 12) & journal["cost_center"].notna()
    ].copy()
    actual["signed"] = signed_amount(actual)
    actual["account_group"] = actual["gl_account"].map(
        dim_gl_account.set_index("gl_account")["account_group"]
    )
    actual["programme_key"] = actual["programme_id"].fillna("(none)")

    grain = [
        "company_code", "fiscal_year", "fiscal_period", "cost_center",
        "account_group", "programme_key",
    ]

    actual_rows = (
        actual.groupby(grain, observed=True)["signed"]
        .sum()
        .reset_index()
        .rename(columns={"signed": "actual"})
    )

    # Budget is annual; phase it evenly across twelve periods so it lands on
    # the same grain as the actuals.
    budget = fact_budget.copy()
    budget["programme_key"] = budget["programme_id"].fillna("(none)")
    annual = (
        budget.groupby(
            ["company_code", "fiscal_year", "cost_center", "account_group",
             "programme_key"],
            observed=True,
        )["amount_group_currency"]
        .sum()
        .reset_index()
        .rename(columns={"amount_group_currency": "budget_annual"})
    )
    periods = pd.DataFrame({"fiscal_period": range(1, 13)})
    phased = annual.merge(periods, how="cross")
    phased["budget_period"] = phased["budget_annual"] / 12.0

    # Outer, not left. A cost centre that spent with no budget and one that was
    # budgeted and spent nothing are both real findings, and an inner or left
    # join hides exactly those two cases. This also has to match the
    # FULL OUTER JOIN in hana/sql/03_l3_reporting.sql, or the two
    # implementations disagree by construction rather than by defect.
    merged = actual_rows.merge(
        phased.drop(columns=["budget_annual"]), on=grain, how="outer"
    )
    merged["actual"] = merged["actual"].fillna(0.0)
    merged["budget_period"] = merged["budget_period"].fillna(0.0)

    merged["variance"] = (merged["actual"] - merged["budget_period"]).round(2)
    # Undefined, not zero, where there is no budget to vary from.
    merged["variance_pct"] = np.where(
        merged["budget_period"].abs() > 0,
        merged["variance"] / merged["budget_period"].abs(),
        np.nan,
    )
    return merged.rename(columns={"programme_key": "programme_id"})


def programme_run_rate(
    journal: pd.DataFrame,
    dim_programme: pd.DataFrame,
    as_of: tuple[int, int],
    window: int = 3,
) -> pd.DataFrame:
    """KPI-05. Rolling run-rate and a naive EAC, per programme.

    This is the reference implementation. The SQLScript table function in
    ``hana/`` and the AMDP that wraps it must reproduce these numbers exactly -
    having the expected answer in Python first is what makes that checkable
    rather than a matter of opinion.

    The EAC is deliberately naive: actuals to date plus run-rate times the
    periods left before the programme's planned end. It ignores the remaining
    work profile, commitments and ramp-down, so it is an early-warning
    indicator and not a forecast. Programmes already past their end date get no
    extrapolation at all.
    """
    as_of_key = as_of[0] * 100 + as_of[1]

    cost = journal[
        journal["programme_id"].notna() & (journal["fiscal_period"] <= 12)
    ].copy()
    cost["signed"] = signed_amount(cost)
    cost["period_key"] = cost["fiscal_year"] * 100 + cost["fiscal_period"]
    cost = cost[cost["period_key"] <= as_of_key]

    monthly = (
        cost.groupby(["programme_id", "period_key"], observed=True)["signed"]
        .sum()
        .reset_index()
    )

    rows = []
    for programme in dim_programme.itertuples():
        history = monthly[monthly["programme_id"] == programme.programme_id]
        if history.empty:
            continue
        recent = history.sort_values("period_key").tail(window)
        run_rate = float(recent["signed"].mean())
        actuals_to_date = float(history["signed"].sum())

        end = programme.end_date
        remaining = max(
            0, (end.year - as_of[0]) * 12 + (end.month - as_of[1])
        )
        eac = actuals_to_date + run_rate * remaining

        rows.append({
            "programme_id": programme.programme_id,
            "as_of_fiscal_year": as_of[0],
            "as_of_fiscal_period": as_of[1],
            "actuals_to_date": round(actuals_to_date, 2),
            "run_rate": round(run_rate, 2),
            "remaining_periods": remaining,
            "eac": round(eac, 2),
            "total_budget_eur": float(programme.total_budget_eur),
            "eac_vs_budget_pct": round(eac / float(programme.total_budget_eur), 4),
        })

    return pd.DataFrame(rows)


def forecast_accuracy(
    journal: pd.DataFrame, fact_forecast: pd.DataFrame
) -> pd.DataFrame:
    """KPI-07. MAPE of each forecast snapshot against what actually happened.

    Reported *by horizon*. A forecast made one period out and one made nine
    periods out are not the same claim, and averaging them produces a number
    that describes neither.

    Periods where the actual is zero are excluded: MAPE is undefined there, and
    silently treating them as zero error flatters the result.
    """
    actual = journal[journal["fiscal_period"] <= 12].copy()
    actual["signed"] = signed_amount(actual)
    actual["programme_key"] = actual["programme_id"].fillna("(none)")
    actual_rows = (
        actual.groupby(
            ["company_code", "cost_center", "programme_key", "fiscal_year",
             "fiscal_period"],
            observed=True,
        )["signed"]
        .sum()
        .reset_index()
        .rename(columns={"signed": "actual"})
    )

    forecast = fact_forecast.copy()
    forecast["programme_key"] = forecast["programme_id"].fillna("(none)")

    merged = forecast.merge(
        actual_rows,
        on=["company_code", "cost_center", "programme_key", "fiscal_year",
            "fiscal_period"],
        how="inner",
    )
    merged = merged[merged["actual"].abs() > 0]
    merged["abs_pct_error"] = (
        (merged["actual"] - merged["amount_group_currency"]).abs()
        / merged["actual"].abs()
    )

    return (
        merged.groupby(["version", "horizon_periods"], observed=True)
        .agg(mape=("abs_pct_error", "mean"), observations=("abs_pct_error", "size"))
        .reset_index()
    )


def intercompany_mismatches(
    journal: pd.DataFrame, materiality: float = config.IC_MATERIALITY_EUR
) -> pd.DataFrame:
    """KPI-08. Entity pairs that do not net to zero within materiality.

    Pairs are keyed on the *unordered* entity pair, because "NS10 is out with
    NS20" and "NS20 is out with NS10" are the same open item, and reporting them
    as two would double the count the close team has to work through.
    """
    ic = journal[journal["is_intercompany"]].copy()
    ic["signed"] = signed_amount(ic)

    left = ic["company_code"].to_numpy()
    right = ic["ic_partner_company"].to_numpy()
    ic["pair"] = [
        f"{a}|{b}" if a < b else f"{b}|{a}" for a, b in zip(left, right)
    ]

    netted = (
        ic.groupby(["pair", "fiscal_year", "fiscal_period"], observed=True)["signed"]
        .sum()
        .round(2)
        .reset_index()
        .rename(columns={"signed": "net_amount"})
    )
    netted["is_mismatch"] = netted["net_amount"].abs() > materiality
    return netted
