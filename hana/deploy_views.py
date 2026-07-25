#!/usr/bin/env python
"""Deploy the L1/L2/L3 view stack and the run-rate table function.

    python hana/deploy_views.py            # deploy everything, in order
    python hana/deploy_views.py --drop     # drop the three schemas first

Statements run in file order, and file order is layer order: L1 before L2
before L3. Views bind to their sources at creation time, so deploying out of
order fails rather than producing something subtly wrong - which is the right
failure mode.

Splitting on semicolons is not good enough here: the run-rate function body is
full of them. The splitter below understands string literals and SQLScript
BEGIN/END blocks.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SQL_DIR = HERE / "sql"

sys.path.insert(0, str(HERE))
from load_data import connect, read_credentials  # noqa: E402

SCHEMAS = ["NOVASPACE_L1", "NOVASPACE_L2", "NOVASPACE_L3"]


def split_statements(sql: str) -> list[str]:
    """Split a script into statements, respecting literals and BEGIN/END.

    A naive split on ';' tears the table function in half at its first internal
    statement and reports a syntax error pointing at a line that is perfectly
    valid.
    """
    statements: list[str] = []
    current: list[str] = []
    depth = 0
    in_string = False
    in_line_comment = False

    tokens = re.split(r"(\n|--|'|\bBEGIN\b|\bEND\b|;)", sql, flags=re.IGNORECASE)

    for token in tokens:
        if token is None or token == "":
            continue

        if in_line_comment:
            current.append(token)
            if token == "\n":
                in_line_comment = False
            continue

        if in_string:
            current.append(token)
            if token == "'":
                in_string = False
            continue

        upper = token.upper()
        if token == "--":
            in_line_comment = True
            current.append(token)
        elif token == "'":
            in_string = True
            current.append(token)
        elif upper == "BEGIN":
            depth += 1
            current.append(token)
        elif upper == "END":
            depth = max(0, depth - 1)
            current.append(token)
        elif token == ";" and depth == 0:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(token)

    tail = "".join(current).strip()
    if tail:
        statements.append(tail)

    # Drop anything that is only comments and whitespace.
    return [
        s for s in statements
        if any(
            line.strip() and not line.strip().startswith("--")
            for line in s.splitlines()
        )
    ]


def first_line(statement: str) -> str:
    for line in statement.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("--"):
            return " ".join(stripped.split())[:78]
    return "(empty)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--drop", action="store_true",
        help="drop the L1/L2/L3 schemas before deploying",
    )
    args = parser.parse_args(argv)

    files = sorted(SQL_DIR.glob("*.sql"))
    if not files:
        raise SystemExit(f"no .sql files found in {SQL_DIR}")

    settings = read_credentials()
    print(f"connecting to {settings['host']}:{settings['port']} as {settings['user']}")
    connection = connect(settings)
    cursor = connection.cursor()

    if args.drop:
        for schema in reversed(SCHEMAS):
            try:
                cursor.execute(f'DROP SCHEMA "{schema}" CASCADE')
                print(f"dropped {schema}")
            except Exception as error:  # noqa: BLE001 - absent schema is fine
                if "invalid schema name" not in str(error).lower():
                    raise
        connection.commit()

    total = 0
    started = time.perf_counter()
    for path in files:
        print(f"\n{path.name}")
        statements = split_statements(path.read_text(encoding="utf-8"))
        for statement in statements:
            label = first_line(statement)
            try:
                cursor.execute(statement)
            except Exception as error:  # noqa: BLE001
                message = str(error)
                # Re-running a deploy should be boring, not an error.
                if "cannot use duplicate schema name" in message.lower():
                    print(f"  skip   {label}  (schema exists)")
                    continue
                print(f"  FAILED {label}\n         {message}", file=sys.stderr)
                connection.rollback()
                cursor.close()
                connection.close()
                return 1
            print(f"  ok     {label}")
            total += 1
        connection.commit()

    print(f"\n{total} statements in {time.perf_counter() - started:.1f}s")

    print("\nobjects now present:")
    cursor.execute(
        "SELECT SCHEMA_NAME, COUNT(*) FROM VIEWS "
        "WHERE SCHEMA_NAME IN ('NOVASPACE_L1','NOVASPACE_L2','NOVASPACE_L3') "
        "GROUP BY SCHEMA_NAME ORDER BY SCHEMA_NAME"
    )
    for schema, count in cursor.fetchall():
        print(f"  {schema:<16} {count:>3} views")
    cursor.execute(
        "SELECT SCHEMA_NAME, FUNCTION_NAME FROM FUNCTIONS "
        "WHERE SCHEMA_NAME LIKE 'NOVASPACE%'"
    )
    for schema, name in cursor.fetchall():
        print(f"  {schema:<16} function {name}")

    cursor.close()
    connection.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
