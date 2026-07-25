# ABAP / CDS / OData layer

abapGit-exported sources from the ABAP environment. **Built in Phase 4.**

Everything here is exported through abapGit from the first object onward, because trial ABAP systems are periodically reset. The repository is the system of record, not the trial.

## Planned objects

| Object | Type | Purpose |
|---|---|---|
| `ZI_GLAccount`, `ZI_CostCenter`, `ZI_Programme`, `ZI_JournalEntry` | Basic / interface CDS views | Associations + semantic annotations (`@Semantics.amount`) |
| `ZI_ProgrammeRunRate` | Composite CDS view | Joins actuals to budget |
| `ZCL_AMDP_RUNRATE` | AMDP class (SQLScript) | Rolling-3-month run-rate and simple EAC via window function, exposed as a CDS table function — code pushdown, proven |
| `ZC_BudgetVariance`, `ZC_CloseMonitor` | Consumption CDS views | `@Analytics.query` + `@UI` annotations so Fiori Elements renders without custom code |
| Service definition + binding | OData V4 | The service the Fiori app consumes |

## Environment

The choice between the BTP ABAP Environment trial and a local Docker ABAP Platform trial is recorded in [`../docs/adr/002-abap-environment.md`](../docs/adr/).
