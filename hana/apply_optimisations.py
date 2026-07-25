#!/usr/bin/env python
"""Apply the optimisations that were measured and kept.

    python hana/apply_optimisations.py

Only the ones that worked. `02_partitioning.sql` and `03_column_pruning.sql`
stay in the repository as evidence for the two negative results in
docs/performance-report.md, and are not applied here - run them by hand if you
want to reproduce the regression.

Kept out of hana/sql/ on purpose, so `deploy_views.py` still reproduces the
un-optimised baseline and the before/after figures can be re-measured from
scratch rather than taken on trust.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from deploy_views import first_line, split_statements  # noqa: E402
from load_data import connect, read_credentials  # noqa: E402

APPLIED = ["01_monthly_aggregate.sql", "04_variance_from_aggregate.sql"]

# Rebuilt afterwards, and not optional.
#
# Dropping the aggregate with CASCADE takes every view that depends on it, and
# that chain runs further than it looks: L3 -> NOVASPACE_API -> the CAP service
# views. An earlier version of this script rebuilt only the L3 views, which
# left four of the ten API views missing and the OData service returning
# "Could not find table/view ANALYTICSSERVICE_BUDGETVARIANCE".
#
# Nothing caught it at the time, because the cross-check queries L3 directly
# and never touches the API layer. It surfaced only on restarting the service.
# The lesson is in docs/performance-report.md: a correctness gate only covers
# what it actually reads.
REBUILT = ["05_api_layer.sql", "06_cap_service_views.sql"]


def main() -> int:
    connection = connect(read_credentials())
    cursor = connection.cursor()

    # The aggregate is dropped first so a re-run is a clean rebuild rather than
    # an append onto whatever was there.
    try:
        cursor.execute('DROP TABLE "NOVASPACE_L3"."AGG_JOURNAL_MONTHLY" CASCADE')
        connection.commit()
        print("dropped the existing aggregate")
    except Exception:  # noqa: BLE001 - absent on a first run
        connection.rollback()

    started = time.perf_counter()
    for name in APPLIED:
        path = HERE / "optimisations" / name
        print(f"\n{name}")
        for statement in split_statements(path.read_text(encoding="utf-8")):
            # 03 created V_JOURNAL_COSTS; it is not applied, so its DROP fails.
            # first_line(), not strip(): the statement opens with a comment
            # block, so a raw startswith() sees "--" and never matches.
            if first_line(statement).upper().startswith("DROP VIEW"):
                continue
            began = time.perf_counter()
            cursor.execute(statement)
            print(f"  ok ({time.perf_counter() - began:.1f}s) {first_line(statement)[:66]}")
        connection.commit()

    for name in REBUILT:
        path = HERE / "sql" / name
        print(f"\n{name} (rebuilding what CASCADE removed)")
        for statement in split_statements(path.read_text(encoding="utf-8")):
            try:
                cursor.execute(statement)
            except Exception as error:  # noqa: BLE001
                if "duplicate schema name" in str(error).lower():
                    continue
                raise
            print(f"  ok     {first_line(statement)[:66]}")
        connection.commit()

    cursor.execute('SELECT COUNT(*) FROM "NOVASPACE_L3"."AGG_JOURNAL_MONTHLY"')
    rows = cursor.fetchone()[0]
    print(f"\naggregate: {rows:,} rows, built in {time.perf_counter() - started:.1f}s")

    cursor.execute(
        "SELECT SCHEMA_NAME, COUNT(*) FROM VIEWS WHERE SCHEMA_NAME LIKE 'NOVASPACE%' "
        "GROUP BY SCHEMA_NAME ORDER BY SCHEMA_NAME"
    )
    for schema, count in cursor.fetchall():
        print(f"  {schema:<16} {count:>3} views")
    print("\nNow verify. An optimisation that changes a result is a defect:")
    print("  python hana/verify_against_python.py")

    cursor.close()
    connection.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
