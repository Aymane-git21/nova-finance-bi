"""Assemble the complete dataset.

One entry point, one seed, one RNG threaded through every builder in a fixed
order. That ordering is what makes the output reproducible: change the sequence
of RNG calls and the data changes, even with the same seed. Any new builder goes
at the *end* of ``build_dataset`` unless the intent is to invalidate every number
already published.

``scale`` exists for the test suite. Gate tests run the same assertions against
a fraction of the volume so they stay fast; the structural stories - the ramp on
the overspending programme, the slow entity's manual share, special periods,
intercompany mismatch rate - are all proportional and survive scaling intact.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import (
    calendar_,
    close,
    config,
    dimensions,
    journal,
    plan,
    programme_budget,
    rates,
    sac_extracts,
)


@dataclass
class Dataset:
    dim_company_code: pd.DataFrame
    dim_cost_center: pd.DataFrame
    dim_programme: pd.DataFrame
    dim_gl_account: pd.DataFrame
    dim_date: pd.DataFrame
    dim_close_task: pd.DataFrame
    rates: pd.DataFrame
    fact_journal: pd.DataFrame
    fact_budget: pd.DataFrame
    fact_forecast: pd.DataFrame
    fact_close_tasks: pd.DataFrame
    working_days: calendar_.WorkingDays = field(repr=False)

    @property
    def tables(self) -> dict[str, pd.DataFrame]:
        return {
            "DIM_COMPANY_CODE": self.dim_company_code,
            "DIM_COST_CENTER": self.dim_cost_center,
            "DIM_PROGRAMME": self.dim_programme,
            "DIM_GL_ACCOUNT": self.dim_gl_account,
            "DIM_DATE": self.dim_date,
            "DIM_CLOSE_TASK": self.dim_close_task,
            "RATES": self.rates,
            "FACT_JOURNAL": self.fact_journal,
            "FACT_BUDGET": self.fact_budget,
            "FACT_FORECAST": self.fact_forecast,
            "FACT_CLOSE_TASKS": self.fact_close_tasks,
        }

    def sac_tables(self) -> dict[str, pd.DataFrame]:
        return {
            "sac_pl_actuals": sac_extracts.pl_actuals(
                self.fact_journal, self.dim_company_code, self.dim_gl_account
            ),
            "sac_programme_costs": sac_extracts.programme_costs(
                self.fact_journal, self.dim_programme, self.dim_gl_account
            ),
            "sac_close_tasks": sac_extracts.close_tasks(
                self.fact_close_tasks, self.dim_close_task, self.dim_company_code,
                self.working_days,
            ),
            "sac_budget_actual": sac_extracts.budget_actual(
                self.fact_journal, self.fact_budget, self.fact_forecast,
                self.dim_gl_account,
            ),
        }


def build_dataset(seed: int = config.SEED, scale: float = 1.0) -> Dataset:
    rng = np.random.default_rng(seed)

    holiday_set = calendar_.holidays(
        config.FIRST_FISCAL_YEAR, config.LAST_FISCAL_YEAR + 1
    )
    working_days = calendar_.WorkingDays(
        config.CALENDAR_START,
        # The window runs a year past the calendar so that close tasks and
        # year-end adjustments for the final period still have working days to
        # land on. Without the overhang, December's close falls off the end.
        config.CALENDAR_END.replace(year=config.CALENDAR_END.year + 1),
        holiday_set,
    )

    dim_company_code = dimensions.build_dim_company_code()
    dim_gl_account = dimensions.build_dim_gl_account()
    dim_programme = dimensions.build_dim_programme()
    dim_close_task = dimensions.build_dim_close_task()
    dim_date = calendar_.build_dim_date(working_days)

    users = dimensions.build_users(rng)
    dim_cost_center = dimensions.build_dim_cost_center(rng, users)

    rates_frame, rates_lookup = rates.build_rates(rng)

    builder = journal.JournalBuilder(
        rng=rng,
        working_days=working_days,
        dim_cost_center=dim_cost_center,
        dim_gl_account=dim_gl_account,
        rates_lookup=rates_lookup,
        users=users,
        scale=scale,
    )
    fact_journal = builder.build()

    # The programme dimension's lifetime budget can only be derived once the
    # actuals exist. See programme_budget.py for why it is not a config value.
    dim_programme = programme_budget.derive_programme_budgets(
        dim_programme, fact_journal
    )

    fact_close_tasks = close.build_fact_close_tasks(rng, working_days, users)
    fact_budget = plan.build_fact_budget(rng, fact_journal, dim_gl_account)
    fact_forecast = plan.build_fact_forecast(
        rng, fact_journal, dim_gl_account, working_days,
        min_annual_eur=50_000.0 * scale,
    )

    return Dataset(
        dim_company_code=dim_company_code,
        dim_cost_center=dim_cost_center,
        dim_programme=dim_programme,
        dim_gl_account=dim_gl_account,
        dim_date=dim_date,
        dim_close_task=dim_close_task,
        rates=rates_frame,
        fact_journal=fact_journal,
        fact_budget=fact_budget,
        fact_forecast=fact_forecast,
        fact_close_tasks=fact_close_tasks,
        working_days=working_days,
    )
