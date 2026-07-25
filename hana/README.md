# SAP HANA layer

Layered modeling on **SAP HANA, express edition** — local Docker, permanent, no trial clock. **Built in Phase 3.** The landscape moved here from HANA Cloud after BTP proved unreachable; see [ADR-002](../docs/adr/002-fully-local-landscape.md).

## Layers (LSA++ on native HANA)

| Layer | Contents | BW/4HANA analogue |
|---|---|---|
| **L1 RAW** | 1:1 views on loaded tables, type casting only | Staging / inbound ADSO |
| **L2 HARMONIZED** | Master-data joins, currency translation to group currency, derived flags (`is_manual_posting`, `is_late_posting`), signed amounts, fiscal-period logic | Standard ADSO with transformations |
| **L3 REPORTING** | Star-join calculation views with cube semantics: `CV_PL_ACTUALS`, `CV_BUDGET_VARIANCE`, `CV_CLOSE_MONITOR`, `CV_FX_IMPACT` — measures, restricted/calculated columns, input parameters | CompositeProvider + BEx query elements |

Full object-by-object mapping: [`../docs/bw4hana-mapping.md`](../docs/bw4hana-mapping.md).

## Operational note

None of the HANA Cloud free-tier operational burden applies here: no nightly auto-stop, no 30-day deletion rule, no expiry. `docker compose up -d` and the database is there. The tradeoffs that come with that are RAM contention on the host and no XS Advanced — meaning no graphical calculation-view editor, so L3 views are authored as `.hdbcalculationview` design-time artifacts and deployed with `@sap/hdi-deploy`. Diffable XML in Git beats clicks in an editor for evidence purposes.

Sizing: the server-only image needs 8 GB RAM minimum, 12 GB recommended. The full image with XSA needs 16–24 GB and does not fit this machine.

## Planned contents

- `docker-compose.yml` + `hxe-password.json` template — bring the database up
- `load_data.py` — `hdbcli` loader, batched `executemany`
- `src/` — HDI calculation-view artifacts for L3; SQL view sources for L1/L2
- `runrate.sql` — the run-rate/EAC table function (SQLScript, window function). The same body is wrapped by `ZCL_AMDP_RUNRATE` in [`../abap/`](../abap/) — see [ADR-003](../docs/adr/003-abap-evidence-strategy.md)
