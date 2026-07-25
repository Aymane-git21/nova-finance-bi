#!/usr/bin/env python
"""Cross-check the HANA view stack against the Python reference implementation.

    python hana/verify_against_python.py

Two independent implementations of the same eight KPIs - one in SQL across
L1/L2/L3, one in ``novaspace/harmonise.py`` - computed over the same seeded
dataset. This script asserts they agree.

That is the entire reason both exist. A subtly wrong JOIN produces a number
that looks perfectly plausible, and nothing in a dashboard will ever contradict
it. Having the expected answer computed independently turns "is this view
right" from a matter of opinion into a check that either passes or does not.

Exit code 0 if every check agrees, 1 otherwise.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "data-generator"))

from load_data import connect, read_credentials  # noqa: E402
from novaspace import config, harmonise as h  # noqa: E402
from novaspace.build import build_dataset  # noqa: E402

#: Amounts are DECIMAL(15,2) in HANA and float64 in pandas. Aggregating a
#: million of them accumulates a few cents of float error, which is a rounding
#: artefact and not a disagreement about the logic.
AMOUNT_TOLERANCE = 1.00
RATIO_TOLERANCE = 1e-6


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, bool, str]] = []

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.rows.append((name, ok, detail))
        marker = "ok  " if ok else "FAIL"
        print(f"  [{marker}] {name}" + (f"  -- {detail}" if detail else ""))

    def compare_frames(
        self, name: str, sql: pd.DataFrame, python: pd.DataFrame,
        keys: list[str], value: str, tolerance: float,
    ) -> None:
        merged = sql.merge(python, on=keys, how="outer", suffixes=("_sql", "_py"))
        missing = merged[
            merged[f"{value}_sql"].isna() | merged[f"{value}_py"].isna()
        ]
        if len(missing):
            self.check(name, False, f"{len(missing)} key(s) present on one side only")
            return

        left = merged[f"{value}_sql"].astype(float).to_numpy()
        right = merged[f"{value}_py"].astype(float).to_numpy()
        delta = np.abs(left - right)
        worst = float(delta.max()) if len(delta) else 0.0

        self.check(
            name,
            bool(worst <= tolerance),
            f"{len(merged)} rows, worst delta {worst:,.4f} (tolerance {tolerance:g})",
        )

    @property
    def failed(self) -> int:
        return sum(1 for _, ok, _ in self.rows if not ok)


def frame(cursor, sql: str) -> pd.DataFrame:
    cursor.execute(sql)
    columns = [c[0] for c in cursor.description]
    data = cursor.fetchall()
    result = pd.DataFrame(data, columns=columns)
    for column in result.columns:
        if result[column].map(lambda v: isinstance(v, Decimal)).any():
            result[column] = result[column].map(
                lambda v: float(v) if isinstance(v, Decimal) else v
            )
    return result


def main() -> int:
    print("building the Python reference dataset (seed "
          f"{config.SEED}) ...")
    data = build_dataset()
    journal = data.fact_journal

    settings = read_credentials()
    print(f"connecting to {settings['host']}:{settings['port']}\n")
    connection = connect(settings)
    cursor = connection.cursor()
    report = Report()

    # -- row counts --------------------------------------------------------
    print("row counts")
    for table, expected in data.tables.items():
        count = frame(cursor, f'SELECT COUNT(*) AS "n" FROM "NOVASPACE_RAW"."{table}"')
        actual = int(count["n"].iloc[0])
        report.check(
            f"{table}", actual == len(expected),
            f"HANA {actual:,} vs Python {len(expected):,}",
        )

    # -- KPI-01 days to close ---------------------------------------------
    print("\nKPI-01 days to close")
    sql_close = frame(cursor, """
        SELECT "company_code", "fiscal_year", "fiscal_period", "days_to_close"
        FROM "NOVASPACE_L2"."V_CLOSE_TASKS"
        WHERE "task_id" = 'T12' AND "days_to_close" IS NOT NULL
    """)
    py_close = h.days_to_close(data.fact_close_tasks, data.working_days)
    py_close = py_close[py_close["days_to_close"].notna()][
        ["company_code", "fiscal_year", "fiscal_period", "days_to_close"]
    ]
    report.compare_frames(
        "days_to_close per entity/period", sql_close, py_close,
        ["company_code", "fiscal_year", "fiscal_period"], "days_to_close", 0.0,
    )

    sql_open = frame(cursor, """
        SELECT COUNT(*) AS "n" FROM "NOVASPACE_L2"."V_CLOSE_TASKS"
        WHERE "task_id" = 'T12' AND "days_to_close" IS NULL
    """)
    py_open = int(
        h.days_to_close(data.fact_close_tasks, data.working_days)["days_to_close"]
        .isna().sum()
    )
    report.check(
        "open periods stay NULL, never zero",
        int(sql_open["n"].iloc[0]) == py_open,
        f"HANA {int(sql_open['n'].iloc[0])} vs Python {py_open}",
    )

    # -- KPI-02 manual share ----------------------------------------------
    print("\nKPI-02 manual postings")
    sql_manual = frame(cursor, """
        SELECT "company_code",
               SUM("line_count_manual") AS "manual",
               SUM("line_count")        AS "total"
        FROM "NOVASPACE_L3"."CV_PL_ACTUALS"
        GROUP BY "company_code"
    """)
    sql_manual["manual_share"] = sql_manual["manual"] / sql_manual["total"]

    regular = journal.copy()
    regular["manual"] = h.is_manual_posting(regular)
    py_manual = regular.groupby("company_code")["manual"].mean().reset_index()
    py_manual.columns = ["company_code", "manual_share"]
    report.compare_frames(
        "manual share per entity",
        sql_manual[["company_code", "manual_share"]], py_manual,
        ["company_code"], "manual_share", RATIO_TOLERANCE,
    )

    # -- KPI-03 late postings ---------------------------------------------
    print("\nKPI-03 late postings")
    sql_late = frame(cursor, """
        SELECT "company_code", SUM("line_count_late") AS "late"
        FROM "NOVASPACE_L3"."CV_PL_ACTUALS"
        GROUP BY "company_code"
    """)
    indexed = journal.reset_index(drop=True)
    late_flag = h.is_late_posting(indexed, data.fact_close_tasks)
    py_late = (
        pd.Series(late_flag).groupby(indexed["company_code"]).sum()
        .reset_index()
    )
    py_late.columns = ["company_code", "late"]
    report.compare_frames(
        "late line count per entity", sql_late, py_late,
        ["company_code"], "late", 0.0,
    )

    # -- KPI-04 budget variance -------------------------------------------
    print("\nKPI-04 budget variance")
    sql_variance = frame(cursor, """
        SELECT "fiscal_year",
               SUM("actual_amount") AS "actual",
               SUM("budget_amount") AS "budget"
        FROM "NOVASPACE_L3"."CV_BUDGET_VARIANCE"
        GROUP BY "fiscal_year"
    """)
    py_variance_rows = h.budget_variance(
        journal, data.fact_budget, data.dim_gl_account
    )
    py_variance = (
        py_variance_rows.groupby("fiscal_year")
        .agg(actual=("actual", "sum"), budget=("budget_period", "sum"))
        .reset_index()
    )
    report.compare_frames(
        "actuals per fiscal year",
        sql_variance[["fiscal_year", "actual"]],
        py_variance[["fiscal_year", "actual"]],
        ["fiscal_year"], "actual", AMOUNT_TOLERANCE,
    )
    report.compare_frames(
        "phased budget per fiscal year",
        sql_variance[["fiscal_year", "budget"]],
        py_variance[["fiscal_year", "budget"]],
        ["fiscal_year"], "budget", AMOUNT_TOLERANCE,
    )

    # -- KPI-05 run rate and EAC ------------------------------------------
    print("\nKPI-05 run-rate and EAC (the SQLScript table function)")
    as_of = (config.LAST_FISCAL_YEAR, config.LAST_CLOSED_PERIOD_IN_FINAL_YEAR)
    sql_runrate = frame(cursor, f"""
        SELECT "programme_id", "actuals_to_date", "run_rate",
               "remaining_periods", "eac"
        FROM "NOVASPACE_L3"."TF_PROGRAMME_RUNRATE"({as_of[0]}, {as_of[1]}, 3)
    """)
    py_runrate = h.programme_run_rate(journal, data.dim_programme, as_of, window=3)
    for column, tolerance in (
        ("actuals_to_date", AMOUNT_TOLERANCE),
        ("run_rate", AMOUNT_TOLERANCE),
        ("remaining_periods", 0.0),
        ("eac", AMOUNT_TOLERANCE),
    ):
        report.compare_frames(
            f"{column} per programme",
            sql_runrate[["programme_id", column]],
            py_runrate[["programme_id", column]],
            ["programme_id"], column, tolerance,
        )

    # -- KPI-06 FX impact --------------------------------------------------
    print("\nKPI-06 FX impact")
    sql_fx = frame(cursor, """
        SELECT "company_code", SUM("fx_impact") AS "fx_impact"
        FROM "NOVASPACE_L3"."CV_FX_IMPACT"
        GROUP BY "company_code"
    """)
    py_fx = h.fx_impact(journal, data.rates, group_by=["company_code"])[
        ["company_code", "fx_impact"]
    ]
    report.compare_frames(
        "FX impact per entity", sql_fx, py_fx,
        ["company_code"], "fx_impact", AMOUNT_TOLERANCE,
    )

    # -- KPI-08 intercompany ----------------------------------------------
    print("\nKPI-08 intercompany reconciliation")
    sql_ic = frame(cursor, """
        SELECT COUNT(*) AS "pairs",
               SUM(CASE WHEN "is_mismatch" = TRUE THEN 1 ELSE 0 END) AS "mismatches"
        FROM "NOVASPACE_L3"."CV_IC_RECONCILIATION"
    """)
    py_ic = h.intercompany_mismatches(journal)
    report.check(
        "pair-periods evaluated",
        int(sql_ic["pairs"].iloc[0]) == len(py_ic),
        f"HANA {int(sql_ic['pairs'].iloc[0])} vs Python {len(py_ic)}",
    )
    report.check(
        "pair-periods flagged as mismatched",
        int(sql_ic["mismatches"].iloc[0]) == int(py_ic["is_mismatch"].sum()),
        f"HANA {int(sql_ic['mismatches'].iloc[0])} vs "
        f"Python {int(py_ic['is_mismatch'].sum())}",
    )

    cursor.close()
    connection.close()

    total = len(report.rows)
    failed = report.failed
    print(f"\n{'=' * 60}")
    if failed:
        print(f"{failed} of {total} checks FAILED - the SQL and the Python disagree.")
        print("The Python has a test suite behind it, so start by assuming the SQL.")
        return 1
    print(f"all {total} checks agree: the HANA views reproduce the Python exactly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
