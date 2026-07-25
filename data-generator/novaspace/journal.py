"""FACT_JOURNAL - the ACDOCA-shaped line-item fact.

Generation runs per (entity, fiscal year, fiscal period). Within each slice the
work is vectorised: documents are drawn first, then exploded into lines, so that
lines belonging to one document genuinely share a header - date, type, user,
currency - the way they do in a real ledger. Generating lines independently
would produce documents whose lines were posted on different days by different
users, which is the tell that synthetic finance data was built by someone who
has not looked at a real one.

Three passes:

1. Regular periods 1-12, per entity.
2. Special periods 13-14 for complete fiscal years - year-end adjustments,
   dated 31 December, entered the following January.
3. Derived lines: intercompany mirrors in the partner entity, and reversals of
   the accrual documents raised at close.

Passes 2 and 3 are separate because they depend on pass 1 having happened.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from . import config
from .calendar_ import WorkingDays, covered_periods, period_end_date
from .rates import rate as fx_rate

MAX_CLOSE_WORKING_DAY = 25


def translate_amounts(
    base_eur: np.ndarray, rate_doc: np.ndarray, rate_local: float | np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Run an economic amount out through the document -> local -> group chain.

    Rounding happens at each hop, in that order, because that is the order a
    real posting is translated in. Deriving the group amount from the *rounded*
    local amount is what makes ``group == round(local * rate)`` exactly true for
    every line, which the harmonised layer relies on when it re-derives group
    currency independently.

    Doing it the obvious way instead - rounding each currency off the same
    unrounded base - leaves sub-cent inconsistencies that only surface as a
    reconciliation difference much later.
    """
    amount_doc = np.round(base_eur / rate_doc, 2)
    amount_local = np.round(amount_doc * rate_doc / rate_local, 2)
    amount_group = np.round(amount_local * rate_local, 2)
    return amount_doc, amount_local, amount_group


class PeriodClock:
    """Precomputed date arithmetic for one fiscal period.

    Doing this per period rather than per row turns a million date calculations
    into a few hundred.
    """

    __slots__ = ("working_days", "period_end", "close_wd", "late_weights")

    def __init__(self, working_days: WorkingDays, fiscal_year: int, fiscal_period: int):
        days = working_days.in_period(fiscal_year, fiscal_period)
        self.working_days = np.array([d.toordinal() for d in days], dtype=np.int64)
        end = period_end_date(fiscal_year, fiscal_period)
        self.period_end = end.toordinal()

        # close_wd[n] is the n-th working day after period end. Index 0 unused.
        close = np.zeros(MAX_CLOSE_WORKING_DAY + 1, dtype=np.int64)
        for n in range(1, MAX_CLOSE_WORKING_DAY + 1):
            close[n] = working_days.nth_after(end, n).toordinal()
        self.close_wd = close

        # Weights ramping toward the end of the period, for document types that
        # cluster late (billing, intercompany charges, manual entries).
        ramp = np.linspace(0.5, 2.0, len(self.working_days))
        self.late_weights = ramp / ramp.sum()


def _build_next_working_day_map(working_days: WorkingDays) -> tuple[int, np.ndarray]:
    """Map every calendar ordinal to the next working day on or after it.

    Returned as (base_ordinal, array) so a lookup is one array index.
    """
    base = working_days.start.toordinal()
    span = working_days.end.toordinal() - base + 1
    result = np.zeros(span, dtype=np.int64)
    nxt = 0
    for offset in range(span - 1, -1, -1):
        day = dt.date.fromordinal(base + offset)
        if working_days.is_working_day(day):
            nxt = base + offset
        result[offset] = nxt if nxt else base + offset
    return base, result


class JournalBuilder:
    def __init__(
        self,
        rng: np.random.Generator,
        working_days: WorkingDays,
        dim_cost_center: pd.DataFrame,
        dim_gl_account: pd.DataFrame,
        rates_lookup: dict,
        users: dict[str, list[str]],
        scale: float = 1.0,
    ):
        self.rng = rng
        self.working_days = working_days
        self.rates = rates_lookup
        self.users = users
        self.scale = scale

        self.entities = [c["company_code"] for c in config.COMPANY_CODES]
        self.local_currency = {
            c["company_code"]: c["local_currency"] for c in config.COMPANY_CODES
        }
        self.size_weight = {
            c["company_code"]: c["size_weight"] for c in config.COMPANY_CODES
        }

        # Cost centres per entity, plus the positions of the overhead ones.
        self.cost_centers: dict[str, np.ndarray] = {}
        self.overhead_positions: dict[str, np.ndarray] = {}
        for entity in self.entities:
            slice_ = dim_cost_center[dim_cost_center["company_code"] == entity].reset_index(
                drop=True
            )
            self.cost_centers[entity] = slice_["cost_center"].to_numpy()
            self.overhead_positions[entity] = np.flatnonzero(
                slice_["is_overhead"].to_numpy()
            )

        # Each cost centre gets a small, fixed portfolio of programmes it books
        # to, weighted toward its own entity's programmes. Sampling with
        # replacement means some centres end up on one programme and some on
        # three, which is what a real cost-centre-to-WBS map looks like.
        self.programme_ids = np.array(
            [p["programme_id"] for p in config.PROGRAMMES], dtype=object
        )
        # Programme size in config is a relative sizing, and it earns its keep
        # here: a bigger programme attracts more cost centres, so the generated
        # spend comes out roughly in the intended proportions.
        relative_size = np.array(
            [p["total_budget_eur"] for p in config.PROGRAMMES], dtype=float
        )
        relative_size = relative_size / relative_size.mean()

        self.cost_center_programmes: dict[str, np.ndarray] = {}
        for entity in self.entities:
            weights = np.array(
                [3.0 if p["lead_company_code"] == entity else 1.0
                 for p in config.PROGRAMMES],
                dtype=float,
            ) * relative_size
            weights = weights / weights.sum()
            self.cost_center_programmes[entity] = rng.choice(
                len(config.PROGRAMMES),
                size=(len(self.cost_centers[entity]), config.PROGRAMMES_PER_COST_CENTER),
                p=weights,
            )

        self._active_masks: dict[tuple[int, int], np.ndarray] = {}

        # G/L accounts per account group.
        self.accounts_by_group: dict[str, np.ndarray] = {
            group: dim_gl_account[dim_gl_account["account_group"] == group][
                "gl_account"
            ].to_numpy()
            for group, *_ in config.ACCOUNT_GROUPS
        }
        self.normal_balance = {
            group: balance for group, _, _, _, _, balance in config.ACCOUNT_GROUPS
        }

        self.doc_codes = [d[0] for d in config.DOCUMENT_TYPES]
        self.doc_spec = {d[0]: d for d in config.DOCUMENT_TYPES}

        self._next_wd_base, self._next_wd_map = _build_next_working_day_map(working_days)
        self._doc_counter = {entity: 0 for entity in self.entities}
        self._clocks: dict[tuple[int, int], PeriodClock] = {}

    # -- helpers ----------------------------------------------------------

    def clock(self, fiscal_year: int, fiscal_period: int) -> PeriodClock:
        key = (fiscal_year, min(fiscal_period, 12))
        if key not in self._clocks:
            self._clocks[key] = PeriodClock(self.working_days, *key)
        return self._clocks[key]

    def next_working_day(self, ordinals: np.ndarray) -> np.ndarray:
        return self._next_wd_map[ordinals - self._next_wd_base]

    def document_numbers(self, entity: str, count: int) -> np.ndarray:
        start = self._doc_counter[entity]
        self._doc_counter[entity] = start + count
        prefix = entity[2:]
        sequence = np.arange(start + 1, start + count + 1)
        return np.char.add(prefix, np.char.zfill(sequence.astype(str), 8))

    def document_type_shares(self, entity: str) -> np.ndarray:
        shares = np.array([spec[2] for spec in config.DOCUMENT_TYPES], dtype=float)
        if entity == config.SLOW_CLOSE_ENTITY:
            for index, spec in enumerate(config.DOCUMENT_TYPES):
                if spec[0] in config.MANUAL_DOCUMENT_TYPES:
                    shares[index] *= config.SLOW_ENTITY_MANUAL_UPLIFT
        return shares / shares.sum()

    def active_programme_mask(self, fiscal_year: int, fiscal_period: int) -> np.ndarray:
        """Boolean mask over PROGRAMMES: is each one running in this period?

        A programme that has not started or has already finished cannot receive
        cost. Without this check the dataset books to programmes outside their
        own start and end dates, which any controller would spot immediately.
        """
        key = (fiscal_year, min(fiscal_period, 12))
        if key not in self._active_masks:
            period_start = dt.date(key[0], key[1], 1)
            period_end = period_end_date(*key)
            self._active_masks[key] = np.array([
                not (p["start_date"] > period_end or p["end_date"] < period_start)
                for p in config.PROGRAMMES
            ])
        return self._active_masks[key]

    def overspend_multiplier(self, fiscal_year: int, fiscal_period: int) -> float:
        """Burn multiplier for the runaway programme. 1.0 before it starts."""
        start_year, start_period = config.OVERSPEND_START
        months = (fiscal_year - start_year) * 12 + (min(fiscal_period, 12) - start_period)
        if months < 0:
            return 1.0
        ramp = min(months / float(config.OVERSPEND_RAMP_MONTHS), 1.0)
        return 1.0 + (config.OVERSPEND_PEAK_MULTIPLIER - 1.0) * ramp

    # -- document-level generation ----------------------------------------

    def _posting_dates(self, timing: str, clock: PeriodClock, count: int) -> np.ndarray:
        if timing == "period_end":
            return np.full(count, clock.period_end, dtype=np.int64)
        if timing == "late_third":
            index = self.rng.choice(
                len(clock.working_days), size=count, p=clock.late_weights
            )
            return clock.working_days[index]
        index = self.rng.integers(0, len(clock.working_days), size=count)
        return clock.working_days[index]

    def _entry_dates(
        self, profile: str, clock: PeriodClock, posting: np.ndarray, entity: str
    ) -> np.ndarray:
        count = len(posting)
        if profile == "same_day":
            return posting
        if profile == "same_or_next":
            offset = self.rng.choice([0, 1, 2], size=count, p=[0.60, 0.30, 0.10])
            return self.next_working_day(posting + offset)
        if profile == "punctual_wd2":
            return np.full(count, clock.close_wd[2], dtype=np.int64)
        if profile == "punctual_wd3":
            return np.full(count, clock.close_wd[3], dtype=np.int64)
        if profile == "close_wd1_3":
            return clock.close_wd[self.rng.integers(1, 4, size=count)]
        if profile == "close_manual":
            weights = np.array(
                config.SLOW_MANUAL_CLOSE_ENTRY_WEIGHTS
                if entity == config.SLOW_CLOSE_ENTITY
                else config.MANUAL_CLOSE_ENTRY_WEIGHTS,
                dtype=float,
            )
            weights = weights / weights.sum()
            working_day = self.rng.choice(
                np.arange(1, len(weights) + 1), size=count, p=weights
            )
            return clock.close_wd[working_day]
        raise ValueError(f"unknown entry-date profile: {profile}")

    def _build_slice(
        self, entity: str, fiscal_year: int, fiscal_period: int, n_lines_target: int,
        force_types: tuple[str, ...] | None = None,
        entry_override: np.ndarray | None = None,
        posting_override: int | None = None,
    ) -> dict[str, np.ndarray] | None:
        """Generate one (entity, period) slice of documents, exploded to lines."""
        clock = self.clock(fiscal_year, fiscal_period)
        entity_users = np.array(self.users[entity], dtype=object)
        local_ccy = self.local_currency[entity]

        if force_types is None:
            codes = self.doc_codes
            shares = self.document_type_shares(entity)
        else:
            codes = list(force_types)
            shares = np.full(len(codes), 1.0 / len(codes))

        mean_lines = float(np.dot(config.DOC_LINE_COUNTS, config.DOC_LINE_WEIGHTS))
        n_docs = max(1, int(round(n_lines_target / mean_lines)))

        doc_type = self.rng.choice(codes, size=n_docs, p=shares)
        doc_lines = self.rng.choice(
            config.DOC_LINE_COUNTS, size=n_docs, p=config.DOC_LINE_WEIGHTS
        )

        posting = np.zeros(n_docs, dtype=np.int64)
        entry = np.zeros(n_docs, dtype=np.int64)
        for code in codes:
            mask = doc_type == code
            if not mask.any():
                continue
            _, _, _, _, timing, entry_profile, _ = self.doc_spec[code]
            if posting_override is not None:
                posting[mask] = posting_override
            else:
                posting[mask] = self._posting_dates(timing, clock, int(mask.sum()))
            if entry_override is not None:
                entry[mask] = entry_override[: int(mask.sum())]
            else:
                entry[mask] = self._entry_dates(
                    entry_profile, clock, posting[mask], entity
                )

        # Document date precedes the posting for externally-originated documents.
        document = posting.copy()
        external = np.isin(doc_type, ["KR", "RE", "RV"])
        if external.any():
            document[external] = posting[external] - self.rng.integers(
                0, 6, size=int(external.sum())
            )

        doc_numbers = self.document_numbers(entity, n_docs)
        doc_users = entity_users[self.rng.integers(0, len(entity_users), size=n_docs)]

        # Document currency: usually the entity's own, sometimes foreign.
        doc_currency = np.full(n_docs, local_ccy, dtype=object)
        foreign = self.rng.random(n_docs) < config.FOREIGN_CURRENCY_RATE
        if foreign.any():
            alternatives = [c for c in config.TRANSACTION_CURRENCIES if c != local_ccy]
            doc_currency[foreign] = self.rng.choice(
                alternatives, size=int(foreign.sum())
            )

        is_ic = doc_type == "IC"
        ic_partner = np.full(n_docs, None, dtype=object)
        if is_ic.any():
            others = [e for e in self.entities if e != entity]
            ic_partner[is_ic] = self.rng.choice(others, size=int(is_ic.sum()))

        # -- explode documents into lines --------------------------------
        line_of_doc = np.repeat(np.arange(n_docs), doc_lines)
        n = len(line_of_doc)
        document_line = (
            np.arange(n) - np.repeat(np.cumsum(doc_lines) - doc_lines, doc_lines) + 1
        )

        line_doc_type = doc_type[line_of_doc]

        # Account group per line, drawn from the document type's allowed set.
        account_group = np.empty(n, dtype=object)
        for code in codes:
            mask = line_doc_type == code
            if not mask.any():
                continue
            groups = self.doc_spec[code][6]
            account_group[mask] = self.rng.choice(groups, size=int(mask.sum()))

        gl_account = np.empty(n, dtype=object)
        for group in set(account_group):
            mask = account_group == group
            pool = self.accounts_by_group[group]
            gl_account[mask] = pool[self.rng.integers(0, len(pool), size=int(mask.sum()))]

        # Debit/credit follows the account group's normal balance.
        debit_credit = np.array(
            [self.normal_balance[g] for g in account_group], dtype=object
        )

        # Cost centre: null on revenue, overhead-weighted on overhead postings.
        centres = self.cost_centers[entity]
        overhead_positions = self.overhead_positions[entity]
        centre_index = self.rng.integers(0, len(centres), size=n)
        overhead_lines = account_group == "OVH"
        if overhead_lines.any() and len(overhead_positions):
            selected = overhead_lines & (self.rng.random(n) < 0.60)
            if selected.any():
                centre_index[selected] = overhead_positions[
                    self.rng.integers(0, len(overhead_positions), size=int(selected.sum()))
                ]
        revenue_lines = account_group == "REV"

        cost_center = centres[centre_index].astype(object)
        cost_center[revenue_lines] = None

        # Programme: drawn from the cost centre's own portfolio, and only if
        # that programme is actually running this period.
        portfolio = self.cost_center_programmes[entity]
        slot = self.rng.integers(0, config.PROGRAMMES_PER_COST_CENTER, size=n)
        programme_index = portfolio[centre_index, slot]
        active = self.active_programme_mask(fiscal_year, fiscal_period)

        assign = (
            (~revenue_lines)
            & (self.rng.random(n) < config.PROGRAMME_ASSIGNMENT_RATE)
            & active[programme_index]
        )
        programme = np.full(n, None, dtype=object)
        programme[assign] = self.programme_ids[programme_index[assign]]

        # Amounts: lognormal in EUR, then translated outward to document and
        # local currency the way a real posting chain runs.
        medians = np.array([config.AMOUNT_MEDIAN[g] for g in account_group])
        sigmas = np.array([config.AMOUNT_SIGMA[g] for g in account_group])
        base_eur = np.exp(self.rng.normal(np.log(medians), sigmas))

        multiplier = self.overspend_multiplier(fiscal_year, fiscal_period)
        if multiplier > 1.0:
            base_eur = np.where(
                programme == config.OVERSPEND_PROGRAMME, base_eur * multiplier, base_eur
            )

        line_currency = doc_currency[line_of_doc]
        rate_doc = np.array([
            fx_rate(self.rates, ccy, fiscal_year, fiscal_period) for ccy in line_currency
        ])
        rate_local = fx_rate(self.rates, local_ccy, fiscal_year, fiscal_period)

        amount_doc, amount_local, amount_group = translate_amounts(
            base_eur, rate_doc, rate_local
        )

        return {
            "company_code": np.full(n, entity, dtype=object),
            "document_number": doc_numbers[line_of_doc],
            "document_line": document_line.astype(np.int32),
            "document_type": line_doc_type,
            "posting_date": posting[line_of_doc],
            "document_date": document[line_of_doc],
            "entry_date": entry[line_of_doc],
            "fiscal_year": np.full(n, fiscal_year, dtype=np.int32),
            "fiscal_period": np.full(n, fiscal_period, dtype=np.int32),
            "gl_account": gl_account,
            "cost_center": cost_center,
            "programme_id": programme,
            "debit_credit_ind": debit_credit,
            "amount_doc_currency": amount_doc,
            "doc_currency": line_currency,
            "amount_local_currency": amount_local,
            "local_currency": np.full(n, local_ccy, dtype=object),
            "amount_group_currency": amount_group,
            "group_currency": np.full(n, config.GROUP_CURRENCY, dtype=object),
            "is_intercompany": is_ic[line_of_doc],
            "ic_partner_company": ic_partner[line_of_doc],
            "posting_user_id": doc_users[line_of_doc],
            "is_reversal": np.zeros(n, dtype=bool),
            "reversed_document": np.full(n, None, dtype=object),
        }

    # -- passes ------------------------------------------------------------

    def regular_periods(self) -> list[dict]:
        base = config.TARGET_LINES_PER_MONTH_TOTAL / sum(self.size_weight.values())
        slices = []
        for fiscal_year, fiscal_period in covered_periods():
            growth = config.VOLUME_GROWTH[fiscal_year]
            for entity in self.entities:
                noise = self.rng.normal(1.0, config.VOLUME_NOISE_SIGMA)
                target = int(round(
                    base * self.size_weight[entity] * growth * max(noise, 0.6) * self.scale
                ))
                slices.append(
                    self._build_slice(entity, fiscal_year, fiscal_period, target)
                )
        return slices

    def special_periods(self) -> list[dict]:
        """Year-end adjustments in special periods 13 and 14.

        Dated 31 December, entered the following January. Manual document types
        only - a year-end adjustment is by definition someone deciding something,
        not a process emitting it.
        """
        base = config.TARGET_LINES_PER_MONTH_TOTAL / sum(self.size_weight.values())
        slices = []
        for fiscal_year in config.YEARS_WITH_SPECIAL_PERIODS:
            year_end = dt.date(fiscal_year, 12, 31)
            for special_period in config.SPECIAL_PERIODS:
                for entity in self.entities:
                    annual = (
                        base * self.size_weight[entity]
                        * config.VOLUME_GROWTH[fiscal_year] * 12 * self.scale
                    )
                    target = max(
                        1,
                        int(round(annual * config.SPECIAL_PERIOD_VOLUME_SHARE
                                  / len(config.SPECIAL_PERIODS))),
                    )
                    mean_lines = float(
                        np.dot(config.DOC_LINE_COUNTS, config.DOC_LINE_WEIGHTS)
                    )
                    n_docs = max(1, int(round(target / mean_lines)))
                    low, high = config.SPECIAL_PERIOD_ENTRY_WD_RANGE
                    entry = np.array([
                        self.working_days.nth_after(year_end, int(n)).toordinal()
                        for n in self.rng.integers(low, high, size=n_docs)
                    ], dtype=np.int64)
                    slices.append(
                        self._build_slice(
                            entity, fiscal_year, special_period, target,
                            force_types=config.MANUAL_DOCUMENT_TYPES,
                            entry_override=entry,
                            posting_override=year_end.toordinal(),
                        )
                    )
        return slices

    def intercompany_mirrors(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Create the partner side of every intercompany charge.

        The issuing entity books a cost; the partner books the matching revenue,
        so the signed pair nets to zero. Roughly 2% are deliberately broken -
        either perturbed or missing entirely - because that is what the
        reconciliation team actually spends its close on.
        """
        source = frame[
            frame["is_intercompany"] & (frame["debit_credit_ind"] == "S")
        ].reset_index(drop=True)
        if source.empty:
            return frame.iloc[0:0]

        # Mismatches are injected per reconciling *pair-period*, not per line.
        #
        # Injecting them per line looks equivalent and is not: a pair-period
        # contains hundreds of intercompany documents at full volume, so a 2%
        # per-line rate leaves almost every pair containing at least one broken
        # line, and 89% of pairs fail to reconcile. The reduced-scale test suite
        # could not see this - few enough documents per pair that most escaped
        # untouched - and it only surfaced against the full dataset. The
        # published behaviour is 2% of *pairs*, so that is what gets sampled.
        left = source["company_code"].to_numpy()
        right = source["ic_partner_company"].to_numpy()
        pair = np.array([f"{a}|{b}" if a < b else f"{b}|{a}" for a, b in zip(left, right)])
        group_key = np.char.add(
            np.char.add(pair, "|"),
            np.char.add(
                source["fiscal_year"].to_numpy().astype(str),
                np.char.add("|", source["fiscal_period"].to_numpy().astype(str)),
            ),
        )

        groups = pd.unique(group_key)
        n_broken = max(1, int(round(len(groups) * config.IC_MISMATCH_RATE)))
        broken_groups = self.rng.choice(groups, size=n_broken, replace=False)

        perturb = np.zeros(len(source), dtype=bool)
        drop = np.zeros(len(source), dtype=bool)
        amounts = source["amount_group_currency"].to_numpy()
        for group in broken_groups:
            candidates = np.flatnonzero(group_key == group)
            # The disputed item is the big one. Breaking a trivial line would
            # leave the pair inside materiality and the mismatch invisible.
            victim = int(candidates[np.argmax(amounts[candidates])])
            # Either the partner booked a different amount, or never booked at
            # all. Both are things a close team actually chases.
            if self.rng.random() < 0.60:
                perturb[victim] = True
            else:
                drop[victim] = True

        keep = ~drop
        source = source[keep].reset_index(drop=True)
        perturb = perturb[keep]

        revenue_accounts = self.accounts_by_group["REV"]
        partners = source["ic_partner_company"].to_numpy()

        rows = {
            "company_code": partners,
            "document_line": np.ones(len(source), dtype=np.int32),
            "document_type": np.full(len(source), "IC", dtype=object),
            "posting_date": source["posting_date"].to_numpy(),
            "document_date": source["document_date"].to_numpy(),
            "fiscal_year": source["fiscal_year"].to_numpy(),
            "fiscal_period": source["fiscal_period"].to_numpy(),
            "gl_account": revenue_accounts[
                self.rng.integers(0, len(revenue_accounts), size=len(source))
            ],
            "cost_center": np.full(len(source), None, dtype=object),
            # The partner books this as revenue centrally, not against the
            # requesting entity's programme. Carrying the programme across
            # would net intercompany revenue into that programme's cost and
            # quietly understate its burn - the opposite of what KPI-05 needs.
            "programme_id": np.full(len(source), None, dtype=object),
            "debit_credit_ind": np.full(len(source), "H", dtype=object),
            "doc_currency": source["doc_currency"].to_numpy(),
            "is_intercompany": np.ones(len(source), dtype=bool),
            "ic_partner_company": source["company_code"].to_numpy(),
            "is_reversal": np.zeros(len(source), dtype=bool),
            "reversed_document": np.full(len(source), None, dtype=object),
        }

        # Document numbers and users belong to the partner entity, not the issuer.
        doc_numbers = np.empty(len(source), dtype=object)
        users = np.empty(len(source), dtype=object)
        entry = np.empty(len(source), dtype=np.int64)
        local_ccy = np.empty(len(source), dtype=object)
        rate_local = np.empty(len(source), dtype=float)

        for entity in self.entities:
            mask = partners == entity
            count = int(mask.sum())
            if not count:
                continue
            doc_numbers[mask] = self.document_numbers(entity, count)
            pool = np.array(self.users[entity], dtype=object)
            users[mask] = pool[self.rng.integers(0, len(pool), size=count)]
            local_ccy[mask] = self.local_currency[entity]
            years = source.loc[mask, "fiscal_year"].to_numpy()
            periods = source.loc[mask, "fiscal_period"].to_numpy()
            entry[mask] = [
                self.clock(int(y), int(p)).close_wd[int(self.rng.integers(1, 4))]
                for y, p in zip(years, periods)
            ]
            rate_local[mask] = [
                fx_rate(self.rates, self.local_currency[entity], int(y), int(p))
                for y, p in zip(years, periods)
            ]

        rows["document_number"] = doc_numbers
        rows["posting_user_id"] = users
        rows["entry_date"] = entry
        rows["local_currency"] = local_ccy
        rows["group_currency"] = np.full(len(source), config.GROUP_CURRENCY, dtype=object)

        target_eur = source["amount_group_currency"].to_numpy().astype(float)
        if perturb.any():
            drift = self.rng.uniform(*config.IC_PERTURBATION_RANGE, size=len(source))
            sign = self.rng.choice([-1.0, 1.0], size=len(source))
            target_eur = np.where(
                perturb, np.round(target_eur * (1.0 + sign * drift), 2), target_eur
            )

        rate_doc = np.array([
            fx_rate(self.rates, ccy, int(y), int(p))
            for ccy, y, p in zip(
                source["doc_currency"], source["fiscal_year"], source["fiscal_period"]
            )
        ])
        # Same translation chain as any other line. The mirror therefore lands
        # within a cent or two of the issuing side rather than exactly on it,
        # which is why KPI-08 carries a materiality threshold instead of testing
        # for a hard zero.
        amount_doc, amount_local, amount_group = translate_amounts(
            target_eur, rate_doc, rate_local
        )
        rows["amount_group_currency"] = amount_group
        rows["amount_local_currency"] = amount_local
        rows["amount_doc_currency"] = amount_doc

        return pd.DataFrame(rows)

    def accrual_reversals(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Reverse accrual documents in the following period.

        An accrual booked at close and never reversed is a misstatement, so the
        reversal is not decoration - its absence would be the anomaly.
        """
        accruals = frame[
            (frame["document_type"] == "SB") & (~frame["is_reversal"])
        ]
        if accruals.empty:
            return frame.iloc[0:0]

        # Reversal is decided per *document*, not per line. Choosing lines
        # independently would split a three-line accrual across three reversal
        # documents, each carrying a single line numbered 2 or 3 - a document
        # with no line 1, which no ledger contains.
        documents = accruals.drop_duplicates("document_number")[
            ["document_number", "company_code", "fiscal_year", "fiscal_period"]
        ].reset_index(drop=True)
        chosen = documents[
            self.rng.random(len(documents)) < config.ACCRUAL_REVERSAL_RATE
        ].reset_index(drop=True)
        if chosen.empty:
            return frame.iloc[0:0]

        periods = covered_periods()
        next_period = {periods[i]: periods[i + 1] for i in range(len(periods) - 1)}

        targets = [
            next_period.get((int(y), int(p)))
            for y, p in zip(chosen["fiscal_year"], chosen["fiscal_period"])
        ]
        keep = np.array([t is not None for t in targets])
        chosen = chosen[keep].reset_index(drop=True)
        targets = [t for t in targets if t is not None]
        if chosen.empty:
            return frame.iloc[0:0]

        # One new document number per reversed document, allocated from the
        # posting entity's own sequence.
        new_numbers = np.empty(len(chosen), dtype=object)
        entities = chosen["company_code"].to_numpy()
        for entity in self.entities:
            mask = entities == entity
            count = int(mask.sum())
            if count:
                new_numbers[mask] = self.document_numbers(entity, count)

        posting = np.array(
            [self.clock(year, period).working_days[0] for year, period in targets],
            dtype=np.int64,
        )
        header = pd.DataFrame({
            "source_document": chosen["document_number"].to_numpy(),
            "new_document": new_numbers,
            "target_year": np.array([t[0] for t in targets], dtype=np.int32),
            "target_period": np.array([t[1] for t in targets], dtype=np.int32),
            "target_posting": posting,
        }).set_index("source_document")

        reversal = accruals[
            accruals["document_number"].isin(header.index)
        ].copy().reset_index(drop=True)

        source_documents = reversal["document_number"].to_numpy()
        reversal["reversed_document"] = source_documents
        reversal["document_number"] = header.loc[source_documents, "new_document"].to_numpy()
        reversal["fiscal_year"] = header.loc[source_documents, "target_year"].to_numpy()
        reversal["fiscal_period"] = header.loc[source_documents, "target_period"].to_numpy()
        target_posting = header.loc[source_documents, "target_posting"].to_numpy()
        reversal["posting_date"] = target_posting
        reversal["document_date"] = target_posting
        reversal["entry_date"] = target_posting
        reversal["is_reversal"] = True
        reversal["debit_credit_ind"] = np.where(
            reversal["debit_credit_ind"].to_numpy() == "S", "H", "S"
        )

        return reversal

    # -- entry point -------------------------------------------------------

    def build(self) -> pd.DataFrame:
        slices = self.regular_periods() + self.special_periods()
        frame = pd.concat([pd.DataFrame(s) for s in slices], ignore_index=True)

        mirrors = self.intercompany_mirrors(frame)
        reversals = self.accrual_reversals(frame)
        frame = pd.concat([frame, mirrors, reversals], ignore_index=True)

        # Ordinals become real dates only at the end - date arithmetic on
        # integers is both faster and harder to get subtly wrong.
        for column in ("posting_date", "document_date", "entry_date"):
            frame[column] = pd.to_datetime(
                frame[column].astype("int64").map(dt.date.fromordinal)
            )

        frame = frame.sort_values(
            ["company_code", "fiscal_year", "fiscal_period", "document_number", "document_line"]
        ).reset_index(drop=True)
        frame.insert(0, "journal_id", np.arange(1, len(frame) + 1, dtype=np.int64))

        column_order = [
            "journal_id", "company_code", "document_number", "document_line",
            "document_type", "posting_date", "document_date", "entry_date",
            "fiscal_year", "fiscal_period", "gl_account", "cost_center",
            "programme_id", "debit_credit_ind", "amount_doc_currency", "doc_currency",
            "amount_local_currency", "local_currency", "amount_group_currency",
            "group_currency", "is_intercompany", "ic_partner_company",
            "posting_user_id", "is_reversal", "reversed_document",
        ]
        return frame[column_order]
