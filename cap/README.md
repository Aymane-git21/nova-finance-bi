# CAP analytics service

OData V4 over the HANA model, built with SAP Cloud Application Programming (`@sap/cds`). **Phase 4.**

This is the service the Fiori app consumes. It is CAP, and it is described as CAP everywhere — it is not, and is never presented as, an ABAP service. The reasoning is in [ADR-003](../docs/adr/003-abap-evidence-strategy.md); the authored-but-unactivated ABAP CDS stack lives in [`../abap/`](../abap/).

## Run it

```bash
python cap/configure.py && cd cap && npm install && npx cds serve --port 4004
```

`configure.py` derives `cap/.cdsrc-private.json` from the credentials `hana/hxe.sh init` generated, so the password exists in exactly one place and that place is git-ignored. HANA Express must be running (`./hana/hxe.sh start`).

Service root: `http://localhost:4004/analytics/` · metadata: `.../$metadata`

## Entities

| Entity | Bound to | Purpose |
|---|---|---|
| `BudgetVariance` | `NOVASPACE_API.V_BUDGET_VARIANCE` | The Analytical List Page's main entity |
| `ProgrammeBurn` | `NOVASPACE_API.V_PROGRAMME_BURN` | The freestyle bubble chart |
| `CloseMonitor` | `NOVASPACE_API.V_CLOSE_MONITOR` | Close timeline and KPI tiles |
| `PlActuals` | `NOVASPACE_API.V_PL_ACTUALS` | P&L trend |
| `IcReconciliation` | `NOVASPACE_API.V_IC_RECONCILIATION` | Open reconciliation items |

Every entity carries `@cds.persistence.exists`. CAP binds to these views; it does not own or deploy them. They were built in SQL and are verified against a Python reference by `hana/verify_against_python.py` — CAP is the consumer here, not the source of truth.

## Two things worth knowing

**1. The service views are created by hand.** CAP compiles each service entity to a database view and queries *that*, not the entity it projects from — visible in the generated SQL as `FROM AnalyticsService_ProgrammeBurn`. In the usual flow `cds deploy` creates those inside an HDI container. This project binds to a plain schema, so [`../hana/sql/06_cap_service_views.sql`](../hana/sql/06_cap_service_views.sql) provides them explicitly. They are pure aliases; the naming is dictated by CAP (`<Service>_<Entity>`, folded to upper case).

**2. `NOVASPACE_API` exists because of upper case, and stays for a better reason.** Every identifier in L1–L3 is quoted lower case, matching the source data; CDS emits unquoted identifiers that HANA folds to upper case, so it cannot see `"company_code"`. The API layer aliases them. Having built it, it earns its keep as a published contract: L3 can be refactored freely and no consumer breaks, which is the job an Open ODS View or a published BW query does in a BW landscape.

## Why annotations rather than UI code

The `@UI` and `@Aggregation` annotations in `srv/analytics-service.cds` are the substance of this layer. Fiori Elements reads them from `$metadata` and renders a full Analytical List Page with no UI code at all.

Where a chart's measures live, how a table is sorted, and what turns a variance red are modelling decisions, not front-end ones. Defining them once means every client renders identically — the same argument BW makes when a restricted key figure defined in a query shows up the same way in every consumer.

Criticality thresholds are computed in SQL (`VARIANCE_CRITICALITY`, `EAC_CRITICALITY`, `CLOSE_CRITICALITY`) rather than in the annotation, so the thresholds are in the model and cannot drift between clients.
