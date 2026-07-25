"""The six data stories docs/data-dictionary.md claims are built in.

A synthetic dataset that was *intended* to contain a story but does not is worse
than one that never claimed to: the dashboard comes out flat, and the cause is
invisible because the generator ran without error. Each test here asserts that a
story a human is supposed to find is actually present and strong enough to see.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from novaspace import config
from novaspace.harmonise import (
    days_to_close,
    fx_impact,
    intercompany_mismatches,
    is_late_posting,
    is_manual_posting,
    signed_amount,
)


# -- story 1: one entity is chronically slow to close ----------------------

def test_the_slow_entity_takes_visibly_longer_to_close(dataset):
    closes = days_to_close(dataset.fact_close_tasks, dataset.working_days)
    by_entity = closes.groupby("company_code")["days_to_close"].mean()

    slow = by_entity[config.SLOW_CLOSE_ENTITY]
    others = by_entity.drop(config.SLOW_CLOSE_ENTITY)

    assert slow > others.max() + 1.5, (
        f"{config.SLOW_CLOSE_ENTITY} closes in {slow:.1f} days against "
        f"{others.max():.1f} for the next slowest - not a visible gap"
    )
    # The other three should look broadly alike, or the story is about noise.
    assert others.max() - others.min() < 1.0


def test_the_slow_entity_misses_its_target_and_the_others_mostly_do_not(dataset):
    closes = days_to_close(dataset.fact_close_tasks, dataset.working_days)
    target = config.COMPANY_CODES[0]["hard_close_target_wd"]
    missed = closes.assign(missed=closes["days_to_close"] > target).groupby(
        "company_code"
    )["missed"].mean()

    assert missed[config.SLOW_CLOSE_ENTITY] > 0.80
    assert missed.drop(config.SLOW_CLOSE_ENTITY).max() < 0.45


# -- story 2: one programme overspends from mid-year ------------------------

def test_the_overspending_programme_burn_rate_accelerates(journal):
    frame = journal[journal["programme_id"].notna()].copy()
    frame["signed"] = signed_amount(frame)

    monthly = (
        frame.groupby(["programme_id", "fiscal_year", "fiscal_period"], observed=True)[
            "signed"
        ]
        .sum()
        .reset_index()
    )

    def mean_burn(programme, year, periods=None):
        rows = monthly[
            (monthly["programme_id"] == programme) & (monthly["fiscal_year"] == year)
        ]
        if periods is not None:
            rows = rows[rows["fiscal_period"].isin(periods)]
        return rows["signed"].mean()

    overspend = config.OVERSPEND_PROGRAMME
    ratio = mean_burn(overspend, 2026) / mean_burn(overspend, 2024)
    assert ratio > 1.20, f"{overspend} burn ratio 2026 vs 2024 is only {ratio:.2f}"

    # A control programme running the whole time should be roughly flat, so the
    # acceleration is specific rather than an artefact of group-wide growth.
    control = "PRG-HELIOS"
    control_ratio = mean_burn(control, 2026) / mean_burn(control, 2024)
    assert control_ratio < ratio - 0.15


def test_the_overspend_starts_when_it_is_supposed_to(journal):
    frame = journal[journal["programme_id"] == config.OVERSPEND_PROGRAMME].copy()
    frame["signed"] = signed_amount(frame)
    monthly = frame.groupby(["fiscal_year", "fiscal_period"], observed=True)[
        "signed"
    ].sum()

    start_year, start_period = config.OVERSPEND_START
    before = monthly[
        [k for k in monthly.index if k < (start_year, start_period)]
    ].mean()
    after = monthly[
        [k for k in monthly.index if k >= (start_year, start_period)]
    ].mean()
    assert after > before * 1.15


def test_the_overspending_programme_exceeds_its_budget(dataset, journal):
    """The overrun must show against a budget nobody rigged - see plan.py."""
    frame = journal.copy()
    frame["signed"] = signed_amount(frame)
    actual = frame[
        (frame["programme_id"] == config.OVERSPEND_PROGRAMME)
        & (frame["fiscal_year"] == 2025)
    ]["signed"].sum()

    budget = dataset.fact_budget[
        (dataset.fact_budget["programme_id"] == config.OVERSPEND_PROGRAMME)
        & (dataset.fact_budget["fiscal_year"] == 2025)
    ]["amount_group_currency"].sum()

    assert budget > 0
    assert actual > budget, "the runaway programme should be over its FY2025 budget"


# -- story 3: FX distorts the non-euro entity -------------------------------

def test_only_the_non_euro_entity_generates_fx_impact(dataset, journal):
    impact = fx_impact(journal, dataset.rates, group_by=["company_code"])
    by_entity = impact.set_index("company_code")["fx_impact"]

    euro_entities = [
        c["company_code"] for c in config.COMPANY_CODES if c["local_currency"] == "EUR"
    ]
    assert np.allclose(by_entity[euro_entities].to_numpy(), 0.0, atol=0.01)
    assert abs(by_entity[config.FX_ENTITY]) > 0.0


def test_fx_impact_is_material_on_the_cost_base(dataset, journal):
    """If FX is a rounding error, the variance bridge on page 2 has no reason to exist.

    Measured on cost, not on the net P&L. A GBP entity earning and spending in
    GBP is naturally hedged, so FX impact on *net profit* is small by
    construction - and dividing by that thin margin produces a ratio that
    swings on nothing. The controller's question is "did we spend more, or did
    the pound move", and that question is about the cost base.
    """
    revenue_accounts = set(
        dataset.dim_gl_account[dataset.dim_gl_account["account_group"] == "REV"][
            "gl_account"
        ]
    )
    cost_lines = journal[~journal["gl_account"].isin(revenue_accounts)]
    impact = fx_impact(cost_lines, dataset.rates, group_by=["company_code"])
    row = impact[impact["company_code"] == config.FX_ENTITY].iloc[0]

    share = abs(row["fx_impact"]) / abs(row["at_budget_rate"])
    assert 0.005 < share < 0.25, f"FX impact is {share:.2%} of the entity's cost base"


def test_fx_impact_nets_out_across_revenue_and_cost_in_the_same_currency(dataset, journal):
    """A GBP entity earning and spending in GBP is largely self-hedged.

    This is not a defect to correct - it is the reason the FX story has to be
    told on the cost base rather than on the bottom line, and worth asserting so
    that nobody later "fixes" the model to make the headline number bigger.
    """
    impact = fx_impact(journal, dataset.rates, group_by=["company_code"])
    row = impact[impact["company_code"] == config.FX_ENTITY].iloc[0]
    net_share = abs(row["fx_impact"]) / abs(row["gross_at_budget_rate"])
    assert net_share < 0.01


def test_the_gbp_rate_actually_moves(dataset):
    actual = dataset.rates[
        (dataset.rates["from_currency"] == "GBP")
        & (dataset.rates["rate_type"] == config.RATE_TYPE_ACTUAL)
    ]["exchange_rate"]
    assert actual.max() / actual.min() > 1.05


def test_the_budget_rate_is_frozen_within_each_fiscal_year(dataset):
    budget = dataset.rates[dataset.rates["rate_type"] == config.RATE_TYPE_BUDGET]
    distinct = budget.groupby(["from_currency", "fiscal_year"])["exchange_rate"].nunique()
    assert (distinct == 1).all()


# -- story 4: intercompany pairs that do not net ----------------------------

def test_intercompany_mismatch_rate_is_small_but_real(journal):
    netted = intercompany_mismatches(journal)
    rate = netted["is_mismatch"].mean()
    assert 0.005 < rate < 0.15, f"mismatch rate {rate:.1%} is not a plausible close problem"


def test_most_intercompany_pairs_do_net_to_zero(journal):
    """The point of the story is the exception, so the rule has to hold."""
    netted = intercompany_mismatches(journal)
    assert (~netted["is_mismatch"]).mean() > 0.85


def test_every_intercompany_charge_has_a_partner_entity(journal):
    ic = journal[journal["is_intercompany"]]
    assert len(ic) > 0
    assert ic["ic_partner_company"].notna().all()


# -- story 5: special periods are actually used -----------------------------

def test_year_end_adjustments_land_in_special_periods(journal):
    special = journal[journal["fiscal_period"] > 12]
    assert len(special) > 0
    assert set(special["fiscal_period"]) == set(config.SPECIAL_PERIODS)
    assert set(special["fiscal_year"]) == set(config.YEARS_WITH_SPECIAL_PERIODS)


def test_year_end_adjustments_are_manual_and_dated_at_year_end(journal):
    special = journal[journal["fiscal_period"] > 12]
    assert set(special["document_type"]) <= set(config.MANUAL_DOCUMENT_TYPES)
    assert (special["posting_date"].dt.month == 12).all()
    assert (special["posting_date"].dt.day == 31).all()


def test_year_end_adjustments_are_entered_the_following_year(journal):
    """Dated 31 December, typed in January - which is the whole point of a special period."""
    special = journal[journal["fiscal_period"] > 12]
    assert (special["entry_date"].dt.year == special["fiscal_year"] + 1).all()
    assert (special["entry_date"] > special["posting_date"]).all()


def test_special_periods_stay_a_small_share_of_the_year(journal):
    special = journal[journal["fiscal_period"] > 12]
    complete_years = journal[journal["fiscal_year"].isin(config.YEARS_WITH_SPECIAL_PERIODS)]
    assert len(special) / len(complete_years) < 0.05


# -- story 6: manual entries spike at close ---------------------------------

def test_manual_entries_cluster_in_the_first_days_after_period_end(dataset, journal):
    """Reversals are excluded: they are start-of-period postings by definition.

    An accrual reversal carries a manual document type but is posted on working
    day 1 of the *following* period, before that period has even ended. Counting
    it as a close-window entry would measure the opposite of what this checks.
    """
    regular = journal[
        (journal["fiscal_period"] <= 12) & (~journal["is_reversal"])
    ].copy()
    manual = regular[is_manual_posting(regular)]

    period_end = (
        pd.to_datetime(
            dict(year=manual["fiscal_year"], month=manual["fiscal_period"], day=1)
        )
        + pd.offsets.MonthEnd(0)
    )
    working = dataset.working_days
    offsets = np.array([
        working.count_after(end.date(), entry.date())
        for end, entry in zip(period_end, manual["entry_date"])
    ])
    within_five = (offsets >= 1) & (offsets <= 5)
    assert within_five.mean() > 0.70, (
        f"only {within_five.mean():.0%} of manual entries land in the close window"
    )


def test_the_slow_entity_posts_more_by_hand(journal):
    frame = journal[journal["fiscal_period"] <= 12].copy()
    frame["manual"] = is_manual_posting(frame)
    share = frame.groupby("company_code")["manual"].mean()

    slow = share[config.SLOW_CLOSE_ENTITY]
    others = share.drop(config.SLOW_CLOSE_ENTITY)
    assert slow > others.max() * 1.4
    assert 0.05 < others.mean() < 0.20


def test_late_postings_are_concentrated_in_the_slow_entity(dataset, journal):
    frame = journal.reset_index(drop=True)
    late = is_late_posting(frame, dataset.fact_close_tasks)
    share = pd.Series(late).groupby(frame["company_code"]).mean()

    assert share[config.SLOW_CLOSE_ENTITY] > share.drop(config.SLOW_CLOSE_ENTITY).max() * 1.5
    # Baseline should sit in amber territory, not green and not absurd.
    assert 0.005 < share.drop(config.SLOW_CLOSE_ENTITY).mean() < 0.06


def test_automatic_postings_are_punctual(journal):
    """Payroll and depreciation land on the same working day every period.

    If automatic postings were as noisy as manual ones, the manual-versus-
    automatic contrast that KPI-02 rests on would not exist.
    """
    regular = journal[journal["fiscal_period"] <= 12]
    payroll = regular[regular["document_type"] == "ML"]
    per_period = payroll.groupby(
        ["company_code", "fiscal_year", "fiscal_period"], observed=True
    )["entry_date"].nunique()
    assert (per_period == 1).all()
