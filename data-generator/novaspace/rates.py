"""FX rates to group currency.

Two rate types, and the whole of KPI-06 is the gap between them:

* ``M`` - the monthly average actual rate, which drifts.
* ``B`` - the budget rate, frozen at each fiscal year's opening rate.

Translating the same local amount at both and differencing isolates how much of
a group-currency variance is rate movement rather than spending behaviour. With
only one rate type in the model that KPI cannot be computed at all, which is why
both are generated here rather than derived later.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def build_rates(rng: np.random.Generator) -> tuple[pd.DataFrame, dict]:
    """Return the RATES table and a ``(currency, fy, period, type) -> rate`` lookup.

    The lookup exists because the journal builder needs a rate per line and a
    DataFrame merge per period would dominate the runtime.
    """
    rows = []
    lookup: dict[tuple[str, int, int, str], float] = {}

    years = range(config.FIRST_FISCAL_YEAR, config.LAST_FISCAL_YEAR + 1)

    for currency in config.TRANSACTION_CURRENCIES:
        rate = config.FX_OPENING_RATE[currency]
        drift = config.FX_DRIFT[currency]
        volatility = config.FX_VOLATILITY[currency]

        for year in years:
            # The budget rate is set at the start of the fiscal year and held
            # flat for all twelve periods, exactly as a planning rate behaves.
            budget_rate = round(rate, 6)

            for period in range(1, 13):
                if currency == config.GROUP_CURRENCY:
                    actual_rate = 1.0
                else:
                    shock = rng.normal(drift, volatility)
                    rate = rate * (1.0 + shock)
                    actual_rate = round(rate, 6)

                for rate_type, value in (
                    (config.RATE_TYPE_ACTUAL, actual_rate),
                    (config.RATE_TYPE_BUDGET, 1.0 if currency == config.GROUP_CURRENCY else budget_rate),
                ):
                    rows.append({
                        "from_currency": currency,
                        "to_currency": config.GROUP_CURRENCY,
                        "fiscal_year": year,
                        "fiscal_period": period,
                        "rate_type": rate_type,
                        "exchange_rate": value,
                    })
                    lookup[(currency, year, period, rate_type)] = value

    frame = pd.DataFrame(rows)
    return frame, lookup


def rate(lookup: dict, currency: str, fiscal_year: int, fiscal_period: int,
         rate_type: str = config.RATE_TYPE_ACTUAL) -> float:
    """Rate from ``currency`` to group currency.

    Special periods 13-16 have no rate of their own and fall back to period 12,
    which is what a year-end adjustment would be translated at in practice.
    """
    period = min(fiscal_period, 12)
    return lookup[(currency, fiscal_year, period, rate_type)]
