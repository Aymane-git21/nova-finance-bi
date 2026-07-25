#!/usr/bin/env python
"""Benchmark the reporting queries against HANA.

    python hana/benchmark.py --label baseline
    python hana/benchmark.py --label after-aggregate --compare baseline

Results are written to hana/benchmarks/<label>.json so runs can be compared
rather than remembered. Phase 7's whole claim is a before/after table, and a
before/after table built from numbers somebody wrote down by hand is not
evidence.

Measurement notes, because the easy version of this is misleading:

* Cold and warm are reported separately. The plan cache is cleared before each
  cold run, so the first execution pays for plan generation and for pulling
  columns into memory. Quoting only warm numbers hides the cost a user actually
  pays for the first query of the morning; quoting only cold ones overstates
  steady-state load.
* Wall-clock is measured client-side and therefore includes fetch. That is the
  honest end-to-end figure. Server-side execution time is read separately from
  M_SQL_PLAN_CACHE so the two can be compared - if they diverge, the bottleneck
  is transfer, not the database.
* Every query runs REPEATS times and the median warm run is reported. A single
  timing on a laptop running Docker is noise.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "benchmarks"
sys.path.insert(0, str(HERE))

from load_data import connect, read_credentials  # noqa: E402

REPEATS = 7

# The queries the dashboard and the story actually issue. Benchmarking
# something nobody runs produces a number nobody cares about.
QUERIES: dict[str, str] = {
    "pl_actuals_full": """
        SELECT "company_code", "fiscal_year", "fiscal_period",
               "account_group", SUM("amount_group_currency") AS "amount",
               SUM("line_count") AS "lines"
        FROM "NOVASPACE_L3"."CV_PL_ACTUALS"
        GROUP BY "company_code", "fiscal_year", "fiscal_period", "account_group"
    """,
    "pl_actuals_one_year": """
        SELECT "company_code", "fiscal_period", "account_group",
               SUM("amount_group_currency") AS "amount"
        FROM "NOVASPACE_L3"."CV_PL_ACTUALS"
        WHERE "fiscal_year" = 2025
        GROUP BY "company_code", "fiscal_period", "account_group"
    """,
    "budget_variance_one_year": """
        SELECT "programme_id", SUM("actual_amount") AS "actual",
               SUM("budget_amount") AS "budget"
        FROM "NOVASPACE_L3"."CV_BUDGET_VARIANCE"
        WHERE "fiscal_year" = 2026
        GROUP BY "programme_id"
    """,
    "programme_runrate": """
        SELECT * FROM "NOVASPACE_L3"."TF_PROGRAMME_RUNRATE"(2026, 6, 3)
    """,
    "close_monitor": """
        SELECT "company_code", AVG("days_to_close") AS "avg_days"
        FROM "NOVASPACE_L3"."CV_CLOSE_MONITOR"
        WHERE "task_id" = 'T12'
        GROUP BY "company_code"
    """,
    "fx_impact": """
        SELECT "company_code", SUM("fx_impact") AS "fx"
        FROM "NOVASPACE_L3"."CV_FX_IMPACT"
        GROUP BY "company_code"
    """,
}


def clear_plan_cache(cursor) -> None:
    try:
        cursor.execute("ALTER SYSTEM CLEAR SQL PLAN CACHE")
    except Exception as error:  # noqa: BLE001
        print(f"  (could not clear the plan cache: {error})")


def server_stats(cursor, fragment: str) -> dict:
    """Server-side execution figures for the most recent matching statement."""
    cursor.execute(
        """
        SELECT AVG_EXECUTION_TIME, EXECUTION_COUNT, TOTAL_RESULT_RECORD_COUNT,
               AVG_EXECUTION_MEMORY_SIZE
        FROM M_SQL_PLAN_CACHE
        WHERE STATEMENT_STRING LIKE ?
        ORDER BY LAST_EXECUTION_TIMESTAMP DESC LIMIT 1
        """,
        (f"%{fragment}%",),
    )
    row = cursor.fetchone()
    if not row:
        return {}
    return {
        "server_avg_ms": round((row[0] or 0) / 1000.0, 2),
        "executions": row[1],
        "result_rows": row[2],
        "avg_exec_memory_mb": round((row[3] or 0) / 1048576.0, 2),
    }


def table_memory(cursor) -> dict:
    cursor.execute(
        """
        SELECT SCHEMA_NAME, TABLE_NAME, RECORD_COUNT, MEMORY_SIZE_IN_TOTAL
        FROM M_CS_TABLES WHERE SCHEMA_NAME LIKE 'NOVASPACE%'
        """
    )
    tables = {}
    total = 0
    for schema, table, rows, memory in cursor.fetchall():
        tables[f"{schema}.{table}"] = {
            "rows": rows, "mb": round((memory or 0) / 1048576.0, 2)
        }
        total += memory or 0
    return {"tables": tables, "total_mb": round(total / 1048576.0, 2)}


def run_query(cursor, sql: str) -> tuple[float, int]:
    started = time.perf_counter()
    cursor.execute(sql)
    rows = cursor.fetchall()
    return (time.perf_counter() - started) * 1000.0, len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True, help="name for this run")
    parser.add_argument("--compare", help="an earlier label to diff against")
    parser.add_argument("--repeats", type=int, default=REPEATS)
    args = parser.parse_args()

    connection = connect(read_credentials())
    cursor = connection.cursor()

    print(f"benchmark '{args.label}' - {args.repeats} runs per query\n")
    print(f"{'query':<28}{'cold ms':>10}{'warm ms':>10}{'server ms':>11}{'rows':>9}")
    print("-" * 68)

    results = {}
    for name, sql in QUERIES.items():
        clear_plan_cache(cursor)
        cold_ms, rows = run_query(cursor, sql)

        warm = []
        for _ in range(args.repeats - 1):
            elapsed, _ = run_query(cursor, sql)
            warm.append(elapsed)
        warm_ms = statistics.median(warm) if warm else cold_ms

        fragment = sql.strip().split("\n")[0].strip()[:40]
        stats = server_stats(cursor, fragment)

        results[name] = {
            "cold_ms": round(cold_ms, 1),
            "warm_ms": round(warm_ms, 1),
            "warm_min_ms": round(min(warm), 1) if warm else None,
            "warm_max_ms": round(max(warm), 1) if warm else None,
            "rows": rows,
            **stats,
        }
        print(f"{name:<28}{cold_ms:>10.1f}{warm_ms:>10.1f}"
              f"{stats.get('server_avg_ms', 0):>11.1f}{rows:>9,}")

    memory = table_memory(cursor)
    print(f"\ncolumn store total: {memory['total_mb']} MB")

    RESULTS.mkdir(exist_ok=True)
    payload = {
        "label": args.label,
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "repeats": args.repeats,
        "queries": results,
        "memory": memory,
    }
    path = RESULTS / f"{args.label}.json"
    path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"written to {path}")

    if args.compare:
        base_path = RESULTS / f"{args.compare}.json"
        if not base_path.exists():
            print(f"\nno baseline named '{args.compare}' to compare against")
        else:
            base = json.loads(base_path.read_text(encoding="utf-8"))
            print(f"\nvs '{args.compare}':")
            print(f"{'query':<28}{'warm before':>13}{'warm after':>12}{'change':>10}")
            print("-" * 63)
            for name, after in results.items():
                before = base["queries"].get(name)
                if not before:
                    continue
                delta = (after["warm_ms"] - before["warm_ms"]) / before["warm_ms"] * 100
                print(f"{name:<28}{before['warm_ms']:>13.1f}"
                      f"{after['warm_ms']:>12.1f}{delta:>9.0f}%")
            mb_before = base["memory"]["total_mb"]
            mb_after = memory["total_mb"]
            print(f"{'column store MB':<28}{mb_before:>13.1f}{mb_after:>12.1f}"
                  f"{(mb_after - mb_before) / mb_before * 100:>9.0f}%")

    cursor.close()
    connection.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
