#!/usr/bin/env python
"""Freeze the OData service into static JSON for the hosted demo.

    python fiori/snapshot.py

Pulls from the running CAP service - not from HANA directly - so the snapshot
is provably what the OData layer returns, aggregations included. The hosted
demo then needs no database, no service and no network: it is the same numbers,
served as files.

That is the whole permanence strategy. Trials expire, containers get stopped,
laptops get rebuilt; a JSON file on GitHub Pages opens in an interview two years
from now. Every payload here is an aggregate, so the largest is a few hundred
rows rather than the 1.12M-line journal underneath it.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "webapp" / "localData"
SERVICE = "http://localhost:4004/analytics"


def get(path: str, **params) -> list[dict]:
    # quote, not quote_plus: urlencode's default turns spaces into "+", and
    # OData rejects "$orderby=X+desc" with a 400. Spaces must be %20.
    query = urllib.parse.urlencode(
        params, safe="(),/", quote_via=urllib.parse.quote
    )
    url = f"{SERVICE}/{path}" + (f"?{query}" if query else "")
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))["value"]
    except urllib.error.URLError as error:
        raise SystemExit(
            f"cannot reach {url}\n  {error}\n\n"
            "Start the service first:\n"
            "  ./hana/hxe.sh start\n"
            "  cd cap && npx cds serve --port 4004"
        )


def number(value):
    """OData serialises Decimal as a string to avoid float loss. Undo that."""
    return None if value is None else float(value)


def write(name: str, payload) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.json"
    path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    rows = len(payload) if isinstance(payload, list) else 1
    print(f"  {name:<22} {rows:>6} rows  {path.stat().st_size / 1024:>7.1f} KB")


def main() -> int:
    print(f"reading {SERVICE}\n")

    # -- programme burn: the bubble chart ---------------------------------
    burn = [
        {
            "id": r["PROGRAMME_ID"],
            "name": r["PROGRAMME_NAME"],
            "type": r["PROGRAMME_TYPE"],
            "status": r["STATUS"],
            "lead": r["LEAD_COMPANY_CODE"],
            "timeElapsed": number(r["PCT_TIME_ELAPSED"]),
            "budgetConsumed": number(r["PCT_BUDGET_CONSUMED"]),
            "budget": number(r["TOTAL_BUDGET"]),
            "actuals": number(r["ACTUALS_TO_DATE"]),
            "eac": number(r["EAC"]),
            "eacVsBudget": number(r["EAC_VS_BUDGET_PCT"]),
            "runRate": number(r["RUN_RATE"]),
            "remainingPeriods": r["REMAINING_PERIODS"],
            "criticality": r["EAC_CRITICALITY"],
        }
        for r in get("ProgrammeBurn", **{"$orderby": "EAC_VS_BUDGET_PCT desc"})
    ]
    write("programmeBurn", burn)

    # -- days to close per entity and period -------------------------------
    close_rows = get(
        "CloseMonitor",
        **{
            "$filter": "TASK_ID eq 'T12'",
            "$select": "COMPANY_CODE,COMPANY_NAME,FISCAL_YEAR,FISCAL_PERIOD,"
                       "FISCAL_PERIOD_LABEL,DAYS_TO_CLOSE,MANUAL_SHARE,LATE_SHARE,"
                       "IS_OPEN,CLOSE_CRITICALITY",
            "$orderby": "FISCAL_YEAR,FISCAL_PERIOD,COMPANY_CODE",
            "$top": "5000",
        },
    )
    close = [
        {
            "entity": r["COMPANY_CODE"],
            "entityName": r["COMPANY_NAME"],
            "period": r["FISCAL_PERIOD_LABEL"],
            "year": r["FISCAL_YEAR"],
            # Null where the period has not closed. Carried through as null,
            # never coerced to zero - the UI has to render "open", not "0 days".
            "daysToClose": r["DAYS_TO_CLOSE"],
            "manualShare": number(r["MANUAL_SHARE"]),
            "lateShare": number(r["LATE_SHARE"]),
            "isOpen": r["IS_OPEN"],
            "criticality": r["CLOSE_CRITICALITY"],
        }
        for r in close_rows
    ]
    write("closeMonitor", close)

    # -- actual vs budget by period ----------------------------------------
    variance = get(
        "BudgetVariance",
        **{
            "$apply": "groupby((FISCAL_YEAR,FISCAL_PERIOD,FISCAL_PERIOD_LABEL),"
                      "aggregate(ACTUAL_AMOUNT with sum as actual,"
                      "BUDGET_AMOUNT with sum as budget))",
            "$orderby": "FISCAL_YEAR,FISCAL_PERIOD",
        },
    )
    write("varianceByPeriod", [
        {
            "period": r["FISCAL_PERIOD_LABEL"],
            "year": r["FISCAL_YEAR"],
            "actual": number(r["actual"]),
            "budget": number(r["budget"]),
            "variance": number(r["actual"]) - number(r["budget"]),
        }
        for r in variance
    ])

    # -- variance by programme, current year --------------------------------
    by_programme = get(
        "BudgetVariance",
        **{
            "$apply": "filter(FISCAL_YEAR eq 2026)/"
                      "groupby((PROGRAMME_ID,PROGRAMME_NAME),"
                      "aggregate(ACTUAL_AMOUNT with sum as actual,"
                      "BUDGET_AMOUNT with sum as budget))",
            "$orderby": "actual desc",
        },
    )
    write("varianceByProgramme", [
        {
            "id": r["PROGRAMME_ID"],
            "name": r["PROGRAMME_NAME"],
            "actual": number(r["actual"]),
            "budget": number(r["budget"]),
            "variance": number(r["actual"]) - number(r["budget"]),
        }
        for r in by_programme
    ])

    # -- open intercompany items --------------------------------------------
    ic = get(
        "IcReconciliation",
        **{"$filter": "IS_MISMATCH eq true", "$orderby": "FISCAL_YEAR desc,FISCAL_PERIOD desc"},
    )
    write("icOpenItems", [
        {
            "pair": r["IC_PAIR"].replace("|", " ↔ "),
            "period": f"{r['FISCAL_YEAR']}-{r['FISCAL_PERIOD']:02d}",
            "netAmount": number(r["NET_AMOUNT"]),
            "lineCount": r["LINE_COUNT"],
        }
        for r in ic
    ])

    # -- headline KPIs -------------------------------------------------------
    closed = [c for c in close if c["daysToClose"] is not None]
    by_entity: dict[str, list] = {}
    for row in closed:
        by_entity.setdefault(row["entity"], []).append(row)

    entities = sorted(
        (
            {
                "entity": entity,
                "entityName": rows[0]["entityName"],
                "avgDaysToClose": round(
                    sum(r["daysToClose"] for r in rows) / len(rows), 2
                ),
                "avgManualShare": round(
                    sum(r["manualShare"] for r in rows) / len(rows), 4
                ),
                "avgLateShare": round(
                    sum(r["lateShare"] for r in rows) / len(rows), 4
                ),
            }
            for entity, rows in by_entity.items()
        ),
        key=lambda r: -r["avgDaysToClose"],
    )
    write("entitySummary", entities)

    over_budget = [p for p in burn if p["eacVsBudget"] and p["eacVsBudget"] > 1.0]
    write("kpi", {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "groupAvgDaysToClose": round(
            sum(r["daysToClose"] for r in closed) / len(closed), 1
        ),
        "slowestEntity": entities[0]["entity"],
        "slowestEntityDays": entities[0]["avgDaysToClose"],
        "groupManualShare": round(
            sum(r["manualShare"] for r in closed) / len(closed), 4
        ),
        "programmesOverBudget": len(over_budget),
        "programmeCount": len(burn),
        "worstProgramme": burn[0]["name"] if burn else None,
        "worstProgrammeEac": burn[0]["eacVsBudget"] if burn else None,
        "openIcItems": len(ic),
        "openPeriods": sum(1 for c in close if c["isOpen"]),
    })

    print(f"\nwritten to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
