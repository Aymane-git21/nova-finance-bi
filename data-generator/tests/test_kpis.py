"""Every KPI in docs/kpi-definitions.md computes, and lands somewhere sane.

This file doubles as executable documentation: if the KPI sheet and the code
ever disagree about what "late posting" or "EAC" means, one of these breaks.

"Sane" here means the ranges the KPI sheet publishes as targets and thresholds.
A KPI that silently returns NaN, zero or something absurd is worse than one that
fails loudly, because it will be believed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from novaspace import config
from novaspace.harmonise import (
    budget_variance,
    days_to_close,
    forecast_accuracy,
    fx_impact,
    intercompany_mismatches,
    is_late_posting,
    is_manual_posting,
    programme_run_rate,
    signed_amount,
)


# -- KPI-01 days to close ---------------------------------------------------

def test_days_to_close_is_computed_for_every_entity_and_period(dataset):
    closes = days_to_close(dataset.fact_close_tasks, dataset.working_days)
    expected = len(config.COMPANY_CODES) * (36 + config.LAST_CLOSED_PERIOD_IN_FINAL_YEAR)
    assert len(closes) == expected


def test_days_to_close_is_a_plausible_number_of_working_days(dataset):
    closes = days_to_close(dataset.fact_close_tasks, dataset.working_days)
    values = closes["days_to_close"].dropna()
    assert (values >= 1).all()
    assert values.max() <= 15
    assert 4 <= values.mean() <= 9


def test_an_open_period_yields_nan_not_zero(dataset):
    """The single most misleading number this dataset could produce."""
    closes = days_to_close(dataset.fact_close_tasks, dataset.working_days)
    assert closes["days_to_close"].isna().any()
    open_rows = closes[closes["days_to_close"].isna()]
    assert open_rows["actual_completion_date"].isna().all()


# -- KPI-02 manual journal entries -----------------------------------------

def test_manual_share_by_count_and_by_value_are_both_available(journal):
    frame = journal[journal["fiscal_period"] <= 12].copy()
    manual = is_manual_posting(frame)

    by_count = manual.mean()
    by_value = (
        frame.loc[manual, "amount_group_currency"].sum()
        / frame["amount_group_currency"].sum()
    )
    assert 0.05 < by_count < 0.30
    assert 0.02 < by_value < 0.35
    # The two must not be assumed equal - that is the whole reason both exist.
    assert by_count != by_value


# -- KPI-03 late postings ---------------------------------------------------

def test_late_posting_rate_is_small_but_non_zero(dataset, journal):
    frame = journal.reset_index(drop=True)
    late = is_late_posting(frame, dataset.fact_close_tasks)
    assert 0.005 < late.mean() < 0.12


def test_special_periods_are_not_counted_as_late(dataset, journal):
    """A year-end adjustment is not a late period-12 posting."""
    frame = journal.reset_index(drop=True)
    late = is_late_posting(frame, dataset.fact_close_tasks)
    assert not late[(frame["fiscal_period"] > 12).to_numpy()].any()


def test_late_postings_really_were_entered_after_the_cut_off(dataset, journal):
    frame = journal.reset_index(drop=True)
    late = is_late_posting(frame, dataset.fact_close_tasks)
    flagged = frame[late]
    due = dataset.fact_close_tasks[
        dataset.fact_close_tasks["task_id"] == config.SOFT_CLOSE_TASK
    ].set_index(["company_code", "fiscal_year", "fiscal_period"])["due_date"]
    keys = pd.MultiIndex.from_arrays([
        flagged["company_code"], flagged["fiscal_year"], flagged["fiscal_period"]
    ])
    cutoffs = pd.to_datetime(pd.Series(due.reindex(keys).to_numpy()))
    assert (flagged["entry_date"].to_numpy() > cutoffs.to_numpy()).all()


# -- KPI-04 budget vs actual ------------------------------------------------

def test_budget_variance_computes_and_carries_a_percentage(dataset, journal):
    variance = budget_variance(journal, dataset.fact_budget, dataset.dim_gl_account)
    assert len(variance) > 0
    assert {"actual", "budget_period", "variance", "variance_pct"} <= set(variance.columns)
    assert np.isclose(
        (variance["actual"] - variance["budget_period"]).sum(),
        variance["variance"].sum(),
        atol=1.0,
    )


def test_variance_percentage_is_undefined_where_there_is_no_budget(dataset, journal):
    variance = budget_variance(journal, dataset.fact_budget, dataset.dim_gl_account)
    unbudgeted = variance[variance["budget_period"] == 0]
    if len(unbudgeted):
        assert unbudgeted["variance_pct"].isna().all()


def test_group_level_variance_stays_within_a_believable_band(dataset, journal):
    """A group running 300% over budget would mean the plan data is nonsense."""
    variance = budget_variance(journal, dataset.fact_budget, dataset.dim_gl_account)
    totals = variance.groupby("fiscal_year")[["actual", "budget_period"]].sum()
    ratio = (totals["actual"] / totals["budget_period"]).dropna()
    assert ratio.between(0.75, 1.35).all(), ratio.to_dict()


# -- KPI-05 run rate and EAC ------------------------------------------------

def test_run_rate_and_eac_compute_for_every_active_programme(dataset, journal):
    as_of = (config.LAST_FISCAL_YEAR, config.LAST_CLOSED_PERIOD_IN_FINAL_YEAR)
    result = programme_run_rate(journal, dataset.dim_programme, as_of)
    assert len(result) == len(dataset.dim_programme)
    assert result["run_rate"].notna().all()
    assert (result["actuals_to_date"] > 0).all()


def test_a_finished_programme_gets_no_extrapolation(dataset, journal):
    """PRG-PHAROS ended in 2025, so by mid-2026 its EAC is just its actuals."""
    as_of = (config.LAST_FISCAL_YEAR, config.LAST_CLOSED_PERIOD_IN_FINAL_YEAR)
    result = programme_run_rate(journal, dataset.dim_programme, as_of).set_index(
        "programme_id"
    )
    finished = result.loc["PRG-PHAROS"]
    assert finished["remaining_periods"] == 0
    assert np.isclose(finished["eac"], finished["actuals_to_date"])


def test_the_runaway_programme_has_the_worst_eac_against_budget(dataset, journal):
    """KPI-05 is meant to trip before the period variance looks alarming."""
    as_of = (config.LAST_FISCAL_YEAR, config.LAST_CLOSED_PERIOD_IN_FINAL_YEAR)
    result = programme_run_rate(journal, dataset.dim_programme, as_of).set_index(
        "programme_id"
    )
    active = result[result["remaining_periods"] > 0]
    worst = active["eac_vs_budget_pct"].idxmax()
    assert worst == config.OVERSPEND_PROGRAMME, (
        f"expected {config.OVERSPEND_PROGRAMME} to have the worst EAC, got {worst}"
    )


def test_run_rate_uses_only_the_window_requested(dataset, journal):
    as_of = (2025, 12)
    narrow = programme_run_rate(journal, dataset.dim_programme, as_of, window=1)
    wide = programme_run_rate(journal, dataset.dim_programme, as_of, window=12)
    assert not np.allclose(narrow["run_rate"], wide["run_rate"])


# -- KPI-06 FX impact -------------------------------------------------------

def test_fx_impact_decomposes_the_group_amount(dataset, journal):
    impact = fx_impact(journal, dataset.rates)
    assert len(impact) > 0
    assert np.allclose(
        impact["at_actual_rate"] - impact["at_budget_rate"],
        impact["fx_impact"],
        atol=0.05,
    )


# -- KPI-07 forecast accuracy ----------------------------------------------

def test_forecast_accuracy_is_reported_by_horizon(dataset, journal):
    accuracy = forecast_accuracy(journal, dataset.fact_forecast)
    assert len(accuracy) > 0
    assert set(accuracy["version"]) <= set(config.FORECAST_VERSIONS)
    assert (accuracy["horizon_periods"] >= 1).all()
    assert (accuracy["mape"] > 0).all()
    assert accuracy["mape"].max() < 3.0


def test_forecast_error_grows_with_horizon(dataset, journal):
    """A forecast nine periods out must not look as good as one a month out."""
    accuracy = forecast_accuracy(journal, dataset.fact_forecast)
    by_horizon = accuracy.groupby("horizon_periods")["mape"].mean()
    near = by_horizon.loc[by_horizon.index <= 2].mean()
    far = by_horizon.loc[by_horizon.index >= 6]
    if len(far):
        assert far.mean() > near


# -- KPI-08 intercompany mismatches ----------------------------------------

def test_mismatches_are_reported_per_unordered_entity_pair(journal):
    netted = intercompany_mismatches(journal)
    assert len(netted) > 0
    for pair in netted["pair"].unique():
        left, right = pair.split("|")
        assert left < right, "pairs must be ordered so A|B and B|A cannot both exist"


def test_the_materiality_threshold_actually_filters_something(journal):
    """Without a threshold, sub-cent translation rounding flags every pair."""
    strict = intercompany_mismatches(journal, materiality=0.0)
    normal = intercompany_mismatches(journal, materiality=config.IC_MATERIALITY_EUR)
    assert strict["is_mismatch"].mean() > normal["is_mismatch"].mean()


def test_mismatch_values_are_material_when_flagged(journal):
    netted = intercompany_mismatches(journal)
    flagged = netted[netted["is_mismatch"]]
    assert (flagged["net_amount"].abs() > config.IC_MATERIALITY_EUR).all()


# -- cross-cutting ----------------------------------------------------------

def test_signed_amounts_make_revenue_negative_and_cost_positive(dataset, journal):
    frame = journal.copy()
    frame["signed"] = signed_amount(frame)
    frame["account_group"] = frame["gl_account"].map(
        dataset.dim_gl_account.set_index("gl_account")["account_group"]
    )
    revenue = frame[(frame["account_group"] == "REV") & (~frame["is_reversal"])]
    personnel = frame[(frame["account_group"] == "PER") & (~frame["is_reversal"])]
    assert (revenue["signed"] <= 0).all()
    assert (personnel["signed"] >= 0).all()
