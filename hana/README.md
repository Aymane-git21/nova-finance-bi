# SAP HANA Cloud layer

Layered modeling on HANA Cloud (BTP free tier). **Built in Phase 3.**

## Layers (LSA++ on native HANA)

| Layer | Contents | BW/4HANA analogue |
|---|---|---|
| **L1 RAW** | 1:1 views on loaded tables, type casting only | Staging / inbound ADSO |
| **L2 HARMONIZED** | Master-data joins, currency translation to group currency, derived flags (`is_manual_posting`, `is_late_posting`), signed amounts, fiscal-period logic | Standard ADSO with transformations |
| **L3 REPORTING** | Star-join calculation views with cube semantics: `CV_PL_ACTUALS`, `CV_BUDGET_VARIANCE`, `CV_CLOSE_MONITOR`, `CV_FX_IMPACT` — measures, restricted/calculated columns, input parameters | CompositeProvider + BEx query elements |

Full object-by-object mapping: [`../docs/bw4hana-mapping.md`](../docs/bw4hana-mapping.md).

## Operational note

Free-tier HANA Cloud instances are **stopped nightly**, and a stopped instance is **deleted after 30 days** unless restarted (warning email at day 15). `start-instance.sh` restarts it via the BTP CLI — run it at the start of every session. All sources live in Git, so a full rebuild is under an hour if the worst happens.

## Planned contents

- `start-instance.sh` — BTP CLI one-liner to restart the instance
- `load_data.py` — `hdbcli` loader, batched `executemany`
- `src/` — HDI calculation-view artifacts (or SQL view sources if HDI is bypassed)
