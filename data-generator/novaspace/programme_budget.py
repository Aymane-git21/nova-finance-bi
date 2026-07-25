"""Derive each programme's lifetime budget from what it actually spends.

The programme budgets in ``config.PROGRAMMES`` are *relative* sizings - they say
Helios is bigger than Pharos, and they drive how much cost each programme
attracts. They are not, and cannot be, absolute euro figures that happen to
match generated spend: total spend is set by posting volume and amount medians,
which have nothing to do with a number typed into a config file.

Leaving the two disconnected produced a dataset where every programme sat at
several times its lifetime budget and the *smallest* programme looked like the
worst overrun - so KPI-05 ranked a perfectly healthy programme as the problem
and the runaway one second. A programme dimension that disagrees with its own
facts is worse than no budget column at all.

So the published ``total_budget_eur`` is derived here, after the journal exists:
baseline monthly burn x planned duration x a small cushion. For every programme
except the runaway one, "baseline" is its whole history. For the runaway one it
is the period *before* the overrun began - which is exactly what its budget
would have been built from in reality, and what makes the overrun show up as an
overrun rather than as a plan that was always going to be met.
"""

from __future__ import annotations

import pandas as pd

from . import config
from .harmonise import signed_amount

#: Plans carry a little headroom over the run-rate they were built from.
BUDGET_CUSHION = 1.05


def duration_in_months(start, end) -> int:
    return max(1, (end.year - start.year) * 12 + (end.month - start.month) + 1)


def derive_programme_budgets(
    dim_programme: pd.DataFrame, journal: pd.DataFrame
) -> pd.DataFrame:
    """Return DIM_PROGRAMME with ``total_budget_eur`` replaced by a derived figure."""
    cost = journal[
        journal["programme_id"].notna() & (journal["fiscal_period"] <= 12)
    ].copy()
    cost["signed"] = signed_amount(cost)
    cost["period_key"] = cost["fiscal_year"] * 100 + cost["fiscal_period"]

    monthly = (
        cost.groupby(["programme_id", "period_key"], observed=True)["signed"]
        .sum()
        .reset_index()
    )

    overspend_key = config.OVERSPEND_START[0] * 100 + config.OVERSPEND_START[1]

    budgets = {}
    for programme in dim_programme.itertuples():
        history = monthly[monthly["programme_id"] == programme.programme_id]
        if history.empty:
            budgets[programme.programme_id] = 0.0
            continue

        if programme.programme_id == config.OVERSPEND_PROGRAMME:
            baseline_rows = history[history["period_key"] < overspend_key]
            if baseline_rows.empty:
                baseline_rows = history
        else:
            baseline_rows = history

        baseline_monthly = float(baseline_rows["signed"].mean())
        months = duration_in_months(programme.start_date, programme.end_date)
        budgets[programme.programme_id] = round(
            baseline_monthly * months * BUDGET_CUSHION, 2
        )

    result = dim_programme.copy()
    result["total_budget_eur"] = result["programme_id"].map(budgets)
    return result
