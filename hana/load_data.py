#!/usr/bin/env python
"""Load the generated CSVs into SAP HANA, express edition.

    python hana/load_data.py                 # create schema, tables, load
    python hana/load_data.py --recreate      # drop and rebuild everything first
    python hana/load_data.py --only FACT_JOURNAL

Reads credentials from hana/.hxe-credentials (written by ``hxe.sh init``) or
from the environment. Nothing is hardcoded and nothing is committed.

Types are declared here explicitly rather than inferred from the CSVs. An
inferred load turns ``company_code`` into an integer the moment every value
happens to be numeric, silently drops leading zeros, and stores money as a
float - and the first two only surface much later, as a join that returns no
rows. The column widths below were measured against the generated data, not
guessed: see the note on DIM_COST_CENTER.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from decimal import Decimal
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DEFAULT_INPUT = REPO / "data-generator" / "output"
SCHEMA = "NOVASPACE_RAW"
BATCH_SIZE = 20_000

# --------------------------------------------------------------------------
# Table definitions
# --------------------------------------------------------------------------
# (column, HANA type). Order here is the insert order; the CSV is reindexed to
# match, so column order in the file is irrelevant.

TABLES: dict[str, dict] = {
    "DIM_COMPANY_CODE": {
        "columns": [
            ("company_code", "NVARCHAR(4) NOT NULL"),
            ("company_name", "NVARCHAR(80) NOT NULL"),
            ("country_key", "NVARCHAR(2) NOT NULL"),
            ("local_currency", "NVARCHAR(3) NOT NULL"),
            ("group_currency", "NVARCHAR(3) NOT NULL"),
            ("soft_close_working_day", "INTEGER NOT NULL"),
            ("hard_close_target_wd", "INTEGER NOT NULL"),
        ],
        "primary_key": ["company_code"],
    },
    "DIM_COST_CENTER": {
        "columns": [
            ("cost_center", "NVARCHAR(10) NOT NULL"),
            ("cost_center_name", "NVARCHAR(80) NOT NULL"),
            ("company_code", "NVARCHAR(4) NOT NULL"),
            ("division_id", "NVARCHAR(12) NOT NULL"),
            ("division_name", "NVARCHAR(60) NOT NULL"),
            # 11 characters in the data ("NS30-ENG-02"). Declared as 10 in an
            # earlier draft of the data dictionary, which would have truncated
            # every department key on load.
            ("department_id", "NVARCHAR(12) NOT NULL"),
            ("department_name", "NVARCHAR(60) NOT NULL"),
            ("parent_id", "NVARCHAR(12) NOT NULL"),
            ("hierarchy_level", "INTEGER NOT NULL"),
            ("is_overhead", "BOOLEAN NOT NULL"),
            ("valid_from", "DATE NOT NULL"),
            ("valid_to", "DATE NOT NULL"),
            ("manager_user_id", "NVARCHAR(12) NOT NULL"),
        ],
        "primary_key": ["cost_center"],
    },
    "DIM_PROGRAMME": {
        "columns": [
            ("programme_id", "NVARCHAR(12) NOT NULL"),
            ("programme_name", "NVARCHAR(80) NOT NULL"),
            ("programme_type", "NVARCHAR(20) NOT NULL"),
            ("lead_company_code", "NVARCHAR(4) NOT NULL"),
            ("start_date", "DATE NOT NULL"),
            ("end_date", "DATE NOT NULL"),
            ("total_budget_eur", "DECIMAL(15,2) NOT NULL"),
            ("status", "NVARCHAR(20) NOT NULL"),
        ],
        "primary_key": ["programme_id"],
    },
    "DIM_GL_ACCOUNT": {
        "columns": [
            ("gl_account", "NVARCHAR(10) NOT NULL"),
            ("gl_account_name", "NVARCHAR(80) NOT NULL"),
            ("account_group", "NVARCHAR(3) NOT NULL"),
            ("account_group_name", "NVARCHAR(40) NOT NULL"),
            ("pl_section", "NVARCHAR(20) NOT NULL"),
            ("is_pl_account", "BOOLEAN NOT NULL"),
            ("normal_balance", "NVARCHAR(1) NOT NULL"),
        ],
        "primary_key": ["gl_account"],
    },
    "DIM_DATE": {
        "columns": [
            ("date_id", "DATE NOT NULL"),
            ("calendar_year", "INTEGER NOT NULL"),
            ("calendar_quarter", "INTEGER NOT NULL"),
            ("calendar_month", "INTEGER NOT NULL"),
            ("day_of_month", "INTEGER NOT NULL"),
            ("day_of_week", "INTEGER NOT NULL"),
            ("day_name", "NVARCHAR(10) NOT NULL"),
            ("is_weekend", "BOOLEAN NOT NULL"),
            ("is_working_day", "BOOLEAN NOT NULL"),
            ("fiscal_year", "INTEGER NOT NULL"),
            ("fiscal_period", "INTEGER NOT NULL"),
            ("period_end_date", "DATE NOT NULL"),
            ("working_days_after_period_end", "INTEGER NOT NULL"),
            ("working_day_of_period", "INTEGER NOT NULL"),
        ],
        "primary_key": ["date_id"],
    },
    "DIM_CLOSE_TASK": {
        "columns": [
            ("task_id", "NVARCHAR(4) NOT NULL"),
            ("task_name", "NVARCHAR(80) NOT NULL"),
            ("task_sequence", "INTEGER NOT NULL"),
            ("target_working_day", "INTEGER NOT NULL"),
            ("is_milestone", "BOOLEAN NOT NULL"),
        ],
        "primary_key": ["task_id"],
    },
    "RATES": {
        "columns": [
            ("from_currency", "NVARCHAR(3) NOT NULL"),
            ("to_currency", "NVARCHAR(3) NOT NULL"),
            ("fiscal_year", "INTEGER NOT NULL"),
            ("fiscal_period", "INTEGER NOT NULL"),
            ("rate_type", "NVARCHAR(1) NOT NULL"),
            ("exchange_rate", "DECIMAL(15,6) NOT NULL"),
        ],
        "primary_key": [
            "from_currency", "to_currency", "fiscal_year", "fiscal_period", "rate_type",
        ],
    },
    "FACT_JOURNAL": {
        "columns": [
            ("journal_id", "BIGINT NOT NULL"),
            ("company_code", "NVARCHAR(4) NOT NULL"),
            ("document_number", "NVARCHAR(12) NOT NULL"),
            ("document_line", "INTEGER NOT NULL"),
            ("document_type", "NVARCHAR(2) NOT NULL"),
            ("posting_date", "DATE NOT NULL"),
            ("document_date", "DATE NOT NULL"),
            ("entry_date", "DATE NOT NULL"),
            ("fiscal_year", "INTEGER NOT NULL"),
            ("fiscal_period", "INTEGER NOT NULL"),
            ("gl_account", "NVARCHAR(10) NOT NULL"),
            ("cost_center", "NVARCHAR(10)"),
            ("programme_id", "NVARCHAR(12)"),
            ("debit_credit_ind", "NVARCHAR(1) NOT NULL"),
            ("amount_doc_currency", "DECIMAL(15,2) NOT NULL"),
            ("doc_currency", "NVARCHAR(3) NOT NULL"),
            ("amount_local_currency", "DECIMAL(15,2) NOT NULL"),
            ("local_currency", "NVARCHAR(3) NOT NULL"),
            ("amount_group_currency", "DECIMAL(15,2) NOT NULL"),
            ("group_currency", "NVARCHAR(3) NOT NULL"),
            ("is_intercompany", "BOOLEAN NOT NULL"),
            ("ic_partner_company", "NVARCHAR(4)"),
            ("posting_user_id", "NVARCHAR(12) NOT NULL"),
            ("is_reversal", "BOOLEAN NOT NULL"),
            ("reversed_document", "NVARCHAR(12)"),
        ],
        "primary_key": ["journal_id"],
    },
    "FACT_BUDGET": {
        "columns": [
            ("budget_id", "BIGINT NOT NULL"),
            ("company_code", "NVARCHAR(4) NOT NULL"),
            ("fiscal_year", "INTEGER NOT NULL"),
            ("cost_center", "NVARCHAR(10) NOT NULL"),
            ("account_group", "NVARCHAR(3) NOT NULL"),
            ("programme_id", "NVARCHAR(12)"),
            ("version", "NVARCHAR(10) NOT NULL"),
            ("amount_group_currency", "DECIMAL(15,2) NOT NULL"),
        ],
        "primary_key": ["budget_id"],
    },
    "FACT_FORECAST": {
        "columns": [
            ("forecast_id", "BIGINT NOT NULL"),
            ("company_code", "NVARCHAR(4) NOT NULL"),
            ("cost_center", "NVARCHAR(10) NOT NULL"),
            ("programme_id", "NVARCHAR(12)"),
            ("fiscal_year", "INTEGER NOT NULL"),
            ("fiscal_period", "INTEGER NOT NULL"),
            ("version", "NVARCHAR(10) NOT NULL"),
            ("snapshot_date", "DATE NOT NULL"),
            ("horizon_periods", "INTEGER NOT NULL"),
            ("amount_group_currency", "DECIMAL(15,2) NOT NULL"),
        ],
        "primary_key": ["forecast_id"],
    },
    "FACT_CLOSE_TASKS": {
        "columns": [
            ("close_task_id", "BIGINT NOT NULL"),
            ("company_code", "NVARCHAR(4) NOT NULL"),
            ("fiscal_year", "INTEGER NOT NULL"),
            ("fiscal_period", "INTEGER NOT NULL"),
            ("task_id", "NVARCHAR(4) NOT NULL"),
            ("period_end_date", "DATE NOT NULL"),
            ("due_date", "DATE NOT NULL"),
            # Null means the period is still open. Not zero, not back-filled.
            ("actual_completion_date", "DATE"),
            ("completed_by_user_id", "NVARCHAR(12)"),
            ("delay_working_days", "INTEGER"),
        ],
        "primary_key": ["close_task_id"],
    },
}

#: Load order matters only for readability - no foreign keys are declared on the
#: RAW layer, deliberately. Constraints belong on the harmonised layer; RAW is
#: an inbound staging area and should accept whatever the source sent so that
#: bad data is diagnosable rather than rejected at the door.
LOAD_ORDER = [
    "DIM_COMPANY_CODE", "DIM_COST_CENTER", "DIM_PROGRAMME", "DIM_GL_ACCOUNT",
    "DIM_DATE", "DIM_CLOSE_TASK", "RATES",
    "FACT_JOURNAL", "FACT_BUDGET", "FACT_FORECAST", "FACT_CLOSE_TASKS",
]


# --------------------------------------------------------------------------
# Connection
# --------------------------------------------------------------------------

def read_credentials() -> dict[str, str]:
    """Environment first, then hana/.hxe-credentials. Never a literal in code."""
    settings = {
        "host": os.environ.get("HXE_HOST", "localhost"),
        "port": os.environ.get("HXE_PORT", "39017"),
        "user": os.environ.get("HXE_USER", "SYSTEM"),
        "password": os.environ.get("HXE_MASTER_PASSWORD", ""),
    }

    credentials_file = HERE / ".hxe-credentials"
    if not settings["password"] and credentials_file.exists():
        for line in credentials_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip().strip("'\"")
            if key == "HXE_MASTER_PASSWORD":
                settings["password"] = value
            elif key == "HXE_HOST":
                settings["host"] = value
            elif key == "HXE_PORT":
                settings["port"] = value

    if not settings["password"]:
        raise SystemExit(
            "No HANA password found.\n"
            "  Run:  ./hana/hxe.sh init && ./hana/hxe.sh start\n"
            "  Or:   export HXE_MASTER_PASSWORD=..."
        )
    return settings


def connect(settings: dict[str, str]):
    try:
        from hdbcli import dbapi
    except ImportError:
        raise SystemExit("hdbcli is not installed. Run: pip install hdbcli")

    return dbapi.connect(
        address=settings["host"],
        port=int(settings["port"]),
        user=settings["user"],
        password=settings["password"],
        autocommit=False,
    )


# --------------------------------------------------------------------------
# DDL
# --------------------------------------------------------------------------

def ensure_schema(cursor) -> None:
    cursor.execute(
        f"SELECT COUNT(*) FROM SCHEMAS WHERE SCHEMA_NAME = '{SCHEMA}'"
    )
    if cursor.fetchone()[0] == 0:
        cursor.execute(f'CREATE SCHEMA "{SCHEMA}"')


def create_table(cursor, name: str, *, recreate: bool) -> None:
    if recreate:
        cursor.execute(f'DROP TABLE "{SCHEMA}"."{name}" CASCADE')

    spec = TABLES[name]
    columns = ",\n  ".join(f'"{c}" {t}' for c, t in spec["columns"])
    key = ", ".join(f'"{c}"' for c in spec["primary_key"])
    # COLUMN table: this is an analytical workload, and the column store is the
    # entire reason HANA is fast at it. Defaulting to ROW here would make every
    # Phase 7 benchmark meaningless.
    cursor.execute(
        f'CREATE COLUMN TABLE "{SCHEMA}"."{name}" (\n  {columns},\n'
        f"  PRIMARY KEY ({key})\n)"
    )


def table_exists(cursor, name: str) -> bool:
    cursor.execute(
        "SELECT COUNT(*) FROM TABLES WHERE SCHEMA_NAME = ? AND TABLE_NAME = ?",
        (SCHEMA, name),
    )
    return cursor.fetchone()[0] > 0


# --------------------------------------------------------------------------
# Load
# --------------------------------------------------------------------------

def prepare_frame(name: str, path: Path) -> pd.DataFrame:
    """Read one CSV and coerce every column to the type the DDL declares."""
    spec = TABLES[name]
    ordered = [column for column, _ in spec["columns"]]

    frame = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])
    missing = set(ordered) - set(frame.columns)
    if missing:
        raise SystemExit(f"{path.name} is missing columns: {sorted(missing)}")
    frame = frame[ordered]

    for column, declared in spec["columns"]:
        series = frame[column]
        if declared.startswith("DATE"):
            frame[column] = pd.to_datetime(series, format="%Y-%m-%d").dt.date
        elif declared.startswith("BOOLEAN"):
            frame[column] = series.map({"true": True, "false": False})
        elif declared.startswith(("INTEGER", "BIGINT")):
            frame[column] = pd.to_numeric(series).astype("Int64")
        elif declared.startswith("DECIMAL"):
            # Decimal, not float. Money in binary floating point is how a
            # reconciliation ends up out by a cent that nobody can explain.
            frame[column] = series.map(lambda v: None if pd.isna(v) else Decimal(v))

    return frame.astype(object).where(pd.notna(frame), None)


def load_table(connection, name: str, path: Path) -> tuple[int, float]:
    started = time.perf_counter()
    frame = prepare_frame(name, path)
    columns = [column for column, _ in TABLES[name]["columns"]]
    placeholders = ", ".join(["?"] * len(columns))
    quoted = ", ".join(f'"{c}"' for c in columns)
    statement = f'INSERT INTO "{SCHEMA}"."{name}" ({quoted}) VALUES ({placeholders})'

    cursor = connection.cursor()
    rows = frame.itertuples(index=False, name=None)
    total = 0
    batch: list[tuple] = []
    for row in rows:
        batch.append(row)
        if len(batch) >= BATCH_SIZE:
            cursor.executemany(statement, batch)
            total += len(batch)
            batch.clear()
    if batch:
        cursor.executemany(statement, batch)
        total += len(batch)
    connection.commit()
    cursor.close()
    return total, time.perf_counter() - started


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument(
        "--recreate", action="store_true",
        help="drop and rebuild every table before loading",
    )
    parser.add_argument(
        "--only", action="append", metavar="TABLE",
        help="load only these tables (repeatable)",
    )
    args = parser.parse_args(argv)

    wanted = args.only or LOAD_ORDER
    unknown = set(wanted) - set(TABLES)
    if unknown:
        raise SystemExit(f"unknown table(s): {sorted(unknown)}")

    if not args.input_dir.exists():
        raise SystemExit(
            f"{args.input_dir} does not exist.\n"
            "Run: python data-generator/generate.py"
        )

    settings = read_credentials()
    print(f"connecting to {settings['host']}:{settings['port']} as {settings['user']}")
    connection = connect(settings)
    cursor = connection.cursor()

    ensure_schema(cursor)
    connection.commit()

    print(f"\n{'table':<22} {'rows':>12} {'seconds':>9} {'rows/s':>10}")
    print("-" * 56)

    grand_total = 0
    started = time.perf_counter()
    for name in LOAD_ORDER:
        if name not in wanted:
            continue
        path = args.input_dir / f"{name}.csv"
        if not path.exists():
            raise SystemExit(f"missing input file: {path}")

        exists = table_exists(cursor, name)
        if args.recreate or not exists:
            create_table(cursor, name, recreate=args.recreate and exists)
            connection.commit()
        else:
            cursor.execute(f'TRUNCATE TABLE "{SCHEMA}"."{name}"')
            connection.commit()

        rows, seconds = load_table(connection, name, path)
        grand_total += rows
        print(f"{name:<22} {rows:>12,} {seconds:>9.1f} {rows / max(seconds, 0.01):>10,.0f}")

    elapsed = time.perf_counter() - started
    print("-" * 56)
    print(f"{'TOTAL':<22} {grand_total:>12,} {elapsed:>9.1f}")

    # Read the counts back rather than trusting the insert loop's arithmetic.
    print("\nverifying row counts from the database:")
    for name in LOAD_ORDER:
        if name not in wanted:
            continue
        cursor.execute(f'SELECT COUNT(*) FROM "{SCHEMA}"."{name}"')
        print(f"  {name:<22} {cursor.fetchone()[0]:>12,}")

    cursor.close()
    connection.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
