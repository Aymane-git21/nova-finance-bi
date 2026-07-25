"""Referential integrity and the invariants docs/data-dictionary.md promises.

Every assertion here corresponds to a line in that document. If one fails,
either the generator broke or the documentation is lying - and both are worth
failing a commit over.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from novaspace import config
from novaspace.rates import rate as fx_rate


# -- keys ------------------------------------------------------------------

def test_journal_primary_key_is_unique(journal):
    assert journal["journal_id"].is_unique


def test_document_number_and_line_are_unique_together(journal):
    assert not journal.duplicated(["document_number", "document_line"]).any()


def test_document_lines_are_numbered_from_one_without_gaps(journal):
    sizes = journal.groupby("document_number")["document_line"].agg(["min", "max", "count"])
    assert (sizes["min"] == 1).all()
    assert (sizes["max"] == sizes["count"]).all()


def test_a_document_belongs_to_exactly_one_entity_and_period(journal):
    grouped = journal.groupby("document_number").agg(
        entities=("company_code", "nunique"),
        years=("fiscal_year", "nunique"),
        periods=("fiscal_period", "nunique"),
        types=("document_type", "nunique"),
    )
    assert (grouped["entities"] == 1).all()
    assert (grouped["years"] == 1).all()
    assert (grouped["periods"] == 1).all()
    assert (grouped["types"] == 1).all()


# -- foreign keys ----------------------------------------------------------

def test_every_company_code_exists(dataset, journal):
    valid = set(dataset.dim_company_code["company_code"])
    assert set(journal["company_code"]) <= valid


def test_every_gl_account_exists(dataset, journal):
    valid = set(dataset.dim_gl_account["gl_account"])
    assert set(journal["gl_account"]) <= valid


def test_every_cost_center_exists_and_belongs_to_the_posting_entity(dataset, journal):
    owner = dataset.dim_cost_center.set_index("cost_center")["company_code"]
    lines = journal[journal["cost_center"].notna()]
    assert set(lines["cost_center"]) <= set(owner.index)
    assert (lines["cost_center"].map(owner).to_numpy() == lines["company_code"].to_numpy()).all()


def test_programme_is_null_or_valid_never_empty_string(dataset, journal):
    valid = set(dataset.dim_programme["programme_id"])
    present = journal["programme_id"].dropna()
    assert set(present) <= valid
    assert not (present == "").any()


def test_revenue_lines_carry_no_cost_centre(dataset, journal):
    revenue_accounts = set(
        dataset.dim_gl_account[dataset.dim_gl_account["account_group"] == "REV"]["gl_account"]
    )
    revenue_lines = journal[journal["gl_account"].isin(revenue_accounts)]
    assert revenue_lines["cost_center"].isna().all()


def _programme_window(dataset, lines):
    programmes = dataset.dim_programme.set_index("programme_id")
    starts = pd.to_datetime(lines["programme_id"].map(programmes["start_date"]))
    ends = pd.to_datetime(lines["programme_id"].map(programmes["end_date"]))
    period_start = pd.to_datetime(
        dict(
            year=lines["fiscal_year"],
            month=lines["fiscal_period"].clip(upper=12),
            day=1,
        )
    )
    period_end = period_start + pd.offsets.MonthEnd(0)
    return (starts <= period_end) & (ends >= period_start)


def test_original_postings_only_hit_programmes_that_are_running(dataset, journal):
    """A cost booked to a programme that has not started is an obvious tell."""
    lines = journal[journal["programme_id"].notna() & ~journal["is_reversal"]]
    assert _programme_window(dataset, lines).all()


def test_only_reversals_may_fall_outside_a_programme_window(dataset, journal):
    """A reversal inherits the account assignment of the accrual it reverses.

    An accrual booked in December to a programme that ends on 31 December
    reverses in January, when that programme is closed. Real ledgers contain
    exactly this, so it is allowed - but only for reversals, and this test is
    what stops it becoming a licence for ordinary postings to drift outside
    their programme's dates.
    """
    lines = journal[journal["programme_id"].notna()]
    outside = lines[~_programme_window(dataset, lines)]
    assert outside["is_reversal"].all()
    # It should stay a rounding error on the portfolio, not a visible effect.
    assert len(outside) / len(lines) < 0.01


# -- dates -----------------------------------------------------------------

def test_document_date_never_follows_the_posting_or_entry_date(journal):
    assert (journal["document_date"] <= journal["posting_date"]).all()
    assert (journal["document_date"] <= journal["entry_date"]).all()


def test_entry_never_precedes_the_posting(journal):
    assert (journal["entry_date"] >= journal["posting_date"]).all()


def test_fiscal_period_is_in_range(journal):
    assert journal["fiscal_period"].between(1, 16).all()


def test_special_periods_only_exist_for_complete_fiscal_years(journal):
    special = journal[journal["fiscal_period"] > 12]
    assert set(special["fiscal_year"]) == set(config.YEARS_WITH_SPECIAL_PERIODS)
    assert set(special["fiscal_period"]) == set(config.SPECIAL_PERIODS)
    assert config.LAST_FISCAL_YEAR not in set(special["fiscal_year"])


def test_regular_postings_fall_inside_their_own_fiscal_period(journal):
    regular = journal[
        (journal["fiscal_period"] <= 12) & (~journal["is_reversal"])
    ]
    assert (regular["posting_date"].dt.year == regular["fiscal_year"]).all()
    assert (regular["posting_date"].dt.month == regular["fiscal_period"]).all()


# -- amounts ---------------------------------------------------------------

def test_amounts_are_stored_unsigned(journal):
    """Direction lives in debit_credit_ind, exactly as SAP stores it."""
    for column in (
        "amount_doc_currency", "amount_local_currency", "amount_group_currency"
    ):
        assert (journal[column] >= 0).all(), column


def test_group_amount_reconciles_to_local_amount_at_the_period_rate(dataset, journal):
    """The document -> local -> group translation chain must be internally consistent.

    Reversals are excluded, and the exclusion is the point: see
    ``test_reversals_keep_the_original_documents_translated_amounts``.
    """
    lookup = {
        (row.from_currency, row.fiscal_year, row.fiscal_period, row.rate_type):
            row.exchange_rate
        for row in dataset.rates.itertuples()
    }
    original = journal[~journal["is_reversal"]]
    sample = original.sample(n=min(5000, len(original)), random_state=7)
    rates = np.array([
        fx_rate(lookup, ccy, int(year), int(period))
        for ccy, year, period in zip(
            sample["local_currency"], sample["fiscal_year"], sample["fiscal_period"]
        )
    ])
    expected = np.round(sample["amount_local_currency"].to_numpy() * rates, 2)
    assert np.allclose(expected, sample["amount_group_currency"].to_numpy(), atol=0.01)


def test_reversals_keep_the_original_documents_translated_amounts(journal):
    """A reversal posts the amounts of the document it reverses, not new ones.

    That is how FB08 behaves: all three currency amounts are carried over, so a
    reversal landing in the next period does *not* reconcile at the new period's
    rate. For the GBP entity the difference is visible, and it is precisely the
    exposure that the FX revaluation task (T09) exists to deal with. Silently
    re-translating reversals would erase a real effect and make the FX story
    cleaner than the world is.
    """
    reversals = journal[journal["is_reversal"]]
    assert len(reversals) > 0

    originals = journal[~journal["is_reversal"]].set_index(
        ["document_number", "document_line"]
    )
    keys = list(zip(reversals["reversed_document"], reversals["document_line"]))
    source = originals.loc[keys]

    for column in (
        "amount_doc_currency", "amount_local_currency", "amount_group_currency"
    ):
        assert np.allclose(
            reversals[column].to_numpy(), source[column].to_numpy(), atol=0.001
        ), column

    # And the direction is flipped, which is what makes it a reversal at all.
    assert (
        reversals["debit_credit_ind"].to_numpy() != source["debit_credit_ind"].to_numpy()
    ).all()


def test_euro_entities_have_identical_local_and_group_amounts(journal):
    euro = journal[journal["local_currency"] == "EUR"]
    assert np.allclose(
        euro["amount_local_currency"].to_numpy(),
        euro["amount_group_currency"].to_numpy(),
        atol=0.01,
    )


def test_debit_credit_follows_the_account_group_normal_balance(dataset, journal):
    balances = dataset.dim_gl_account.set_index("gl_account")["normal_balance"]
    non_reversal = journal[~journal["is_reversal"]]
    expected = non_reversal["gl_account"].map(balances)
    # Intercompany mirrors are credits by construction, being the partner side.
    mirrors = non_reversal["is_intercompany"] & (non_reversal["debit_credit_ind"] == "H")
    mismatched = (non_reversal["debit_credit_ind"] != expected) & ~mirrors
    assert not mismatched.any()


# -- intercompany ----------------------------------------------------------

def test_intercompany_lines_always_name_a_different_partner(journal):
    ic = journal[journal["is_intercompany"]]
    assert ic["ic_partner_company"].notna().all()
    assert (ic["ic_partner_company"] != ic["company_code"]).all()


def test_non_intercompany_lines_have_no_partner(journal):
    assert journal[~journal["is_intercompany"]]["ic_partner_company"].isna().all()


# -- reversals -------------------------------------------------------------

def test_reversals_point_at_a_real_accrual_document(journal):
    reversals = journal[journal["is_reversal"]]
    assert reversals["reversed_document"].notna().all()
    assert set(reversals["reversed_document"]) <= set(journal["document_number"])


def test_non_reversals_reference_nothing(journal):
    assert journal[~journal["is_reversal"]]["reversed_document"].isna().all()


def test_a_reversal_lands_after_the_document_it_reverses(journal):
    originals = (
        journal[~journal["is_reversal"]]
        .groupby("document_number")["posting_date"]
        .first()
    )
    reversals = journal[journal["is_reversal"]]
    original_dates = reversals["reversed_document"].map(originals)
    assert (reversals["posting_date"].to_numpy() > original_dates.to_numpy()).all()


# -- personal data ---------------------------------------------------------

def test_user_ids_are_opaque_tokens(dataset, journal):
    """No name is ever generated, so no re-identification key can exist."""
    pattern = r"^USR-[0-9A-F]{6}$"
    assert journal["posting_user_id"].str.match(pattern).all()
    assert dataset.dim_cost_center["manager_user_id"].str.match(pattern).all()
    completed = dataset.fact_close_tasks["completed_by_user_id"].dropna()
    assert completed.str.match(pattern).all()


def test_users_never_post_outside_their_own_entity(dataset, journal):
    per_user = journal.groupby("posting_user_id")["company_code"].nunique()
    assert (per_user == 1).all()


# -- plan data -------------------------------------------------------------

def test_budget_keys_are_valid(dataset):
    budget = dataset.fact_budget
    assert budget["budget_id"].is_unique
    assert set(budget["cost_center"]) <= set(dataset.dim_cost_center["cost_center"])
    assert set(budget["programme_id"].dropna()) <= set(dataset.dim_programme["programme_id"])
    assert set(budget["version"]) == {config.BUDGET_VERSION}
    assert budget["fiscal_year"].between(
        config.FIRST_FISCAL_YEAR, config.LAST_FISCAL_YEAR
    ).all()


def test_forecast_horizons_are_positive_and_consistent(dataset):
    forecast = dataset.fact_forecast
    assert forecast["forecast_id"].is_unique
    assert (forecast["horizon_periods"] >= 1).all()
    snapshot_period = forecast["version"].map(config.FORECAST_SNAPSHOT_AFTER_PERIOD)
    assert (
        forecast["fiscal_period"] - snapshot_period == forecast["horizon_periods"]
    ).all()


def test_forecast_never_covers_an_already_closed_period(dataset):
    """A forecast of a period that had already closed would be a hindcast."""
    forecast = dataset.fact_forecast
    snapshot_period = forecast["version"].map(config.FORECAST_SNAPSHOT_AFTER_PERIOD)
    assert (forecast["fiscal_period"] > snapshot_period).all()


def test_close_tasks_cover_every_entity_period_and_task(dataset):
    tasks = dataset.fact_close_tasks
    expected = (
        len(config.COMPANY_CODES)
        * (36 + config.LAST_CLOSED_PERIOD_IN_FINAL_YEAR)
        * len(config.CLOSE_TASKS)
    )
    assert len(tasks) == expected
    assert not tasks.duplicated(
        ["company_code", "fiscal_year", "fiscal_period", "task_id"]
    ).any()


def test_close_task_due_dates_are_working_days(dataset):
    working = dataset.working_days
    assert all(working.is_working_day(d) for d in dataset.fact_close_tasks["due_date"])


def test_incomplete_close_tasks_carry_no_completion_data(dataset):
    """An open period reports as open - never as zero, never back-filled."""
    tasks = dataset.fact_close_tasks
    open_tasks = tasks[tasks["actual_completion_date"].isna()]
    assert len(open_tasks) > 0, "the dataset must contain at least one open period"
    assert open_tasks["delay_working_days"].isna().all()
    assert open_tasks["completed_by_user_id"].isna().all()
