# ABAP / CDS layer

> ## ⚠️ NOT ACTIVATED
>
> **Every ABAP source in this directory is authored but has never been activated on a running system, and is not claimed to be.** No ABAP system was reachable: SAP BTP was unavailable ([ADR-002](../docs/adr/002-fully-local-landscape.md)) and the ABAP Platform Trial container needs 100 GB of disk against 62.7 GB free. Every file carries the same warning in its header. There are no screenshots here and no claim of a running service.
>
> What *is* proven: the SQLScript body inside `ZCL_AMDP_RUNRATE` is deployed to HANA Express as a table function, unit-tested and benchmarked in Phase 7. An AMDP's body is SQLScript and HANA executes it — ABAP is the wrapper. So the pushdown logic is real; the wrapper is source-only. Full reasoning: [ADR-003](../docs/adr/003-abap-evidence-strategy.md).
>
> The working OData V4 service that the Fiori app consumes is **CAP**, not this. It lives in [`../cap/`](../cap/) and is never presented as ABAP.

**Built in Phase 4.** Structured as an abapGit export so it activates directly the day a system becomes available.

## Planned objects

| Object | Type | Purpose |
|---|---|---|
| `ZI_GLAccount`, `ZI_CostCenter`, `ZI_Programme`, `ZI_JournalEntry` | Basic / interface CDS views | Associations + semantic annotations (`@Semantics.amount`) |
| `ZI_ProgrammeRunRate` | Composite CDS view | Joins actuals to budget |
| `ZCL_AMDP_RUNRATE` | AMDP class (SQLScript) | Rolling-3-month run-rate and simple EAC via window function, exposed as a CDS table function — code pushdown, proven |
| `ZC_BudgetVariance`, `ZC_CloseMonitor` | Consumption CDS views | `@Analytics.query` + `@UI` annotations so Fiori Elements renders without custom code |
| Service definition + binding | OData V4 | The service the Fiori app consumes |

## Environment

Neither ABAP environment the roadmap anticipated was reachable. The decision on what to build instead, and how to label it honestly, is [ADR-003](../docs/adr/003-abap-evidence-strategy.md).
