# SAC and BPC: the requirement, the gap, and the substitute

Both SAP Analytics Cloud and BPC are named requirements for the target role. **Neither is demonstrated hands-on in this repository.** This page says why, what was built instead, and what a reader should conclude.

## What happened

The SAC trial was registered on 2026-07-25 so that its 30-day clock would start only once the dataset was ready. The tenant then became unavailable. SAP BTP had already proved unreachable by both the pay-as-you-go and trial routes, and the ABAP Platform trial does not fit the available disk. Three of the four SAP-hosted services this project planned to use were unreachable inside the same weekend.

The decision not to make a fourth attempt is recorded in [ADR-004](adr/004-consumption-layer-without-sac.md). Short version: everything built locally has worked continuously; everything hosted has not.

## What SAC would have provided, and what covers it now

| SAC capability | Requirement it served | What covers it here | Honest verdict |
|---|---|---|---|
| Story with KPI tiles, charts, filters | "Experience on SAC" | Fiori Elements Analytical List Page + freestyle UI5 chart, on GitHub Pages | **Different product.** Covers the *reporting-design* skill — grain, restraint, labelling, what a CFO page should show — but is not SAC |
| Model definition (measures, dimensions, hierarchies, currency) | Semantic modelling | The L3 views and the CAP service: measures, restricted key figures, hierarchies, currency translation | **Equivalent in substance.** The modelling decisions are the same ones; the tool is not |
| Import vs live data acquisition | Architecture judgement | [`../sac/live-vs-import.md`](../sac/live-vs-import.md) | Written, not demonstrated |
| Planning model, Version dimension | "Experience on BPC projects" | `FACT_BUDGET` / `FACT_FORECAST` carry a Version dimension and are modelled through to the reporting layer | **Data model only.** No input, no spreading, no data actions |
| Data actions, input schedules, spreading | BPC equivalence | Nothing | **Not covered.** See below |

## The BPC concept mapping

This is what remains: being able to talk about it accurately. Worth considerably less than having built it, and stated as such.

| BPC concept | SAC equivalent | What it means | Where it appears in this project |
|---|---|---|---|
| **Category** | Version dimension | The axis separating Actual, Budget and Forecast so they coexist at the same grain | `version` on `FACT_BUDGET` (`BUDGET`) and `FACT_FORECAST` (`FC-Q1`…`FC-Q3`); stacked on a Version in `sac_budget_actual.csv` |
| **Planning function / script logic** | Data action | Server-side calculation over plan data: copy, revalue, allocate, distribute | Not built. The nearest thing here is the even 12-period budget phasing in `V_BUDGET_PHASED`, which is a distribution rule applied once in the model rather than a user-triggered action |
| **Input schedule** | Input form / input-enabled table | The grid a planner types into, bound to the model | Not built. This is the substantive gap |
| **Work status** | Locking | Preventing edits to a period once it is submitted | Not built. Conceptually the same job the `T12 Hard close / period lock` task does in the close model |
| **BADI / custom logic** | Advanced formulas | Escape hatch for rules the standard functions cannot express | Not applicable |
| **Consolidation** | SAC does not cover it | Intercompany elimination, ownership, currency translation for group reporting | Partially present: `CV_IC_RECONCILIATION` does the reconciliation step that *precedes* elimination, and currency translation to group currency is modelled |

The one thing worth saying in an interview beyond the mapping: **rolling forecast snapshots are modelled properly here**, which is where most planning demos are weakest. `FACT_FORECAST` stores each quarterly snapshot with the horizon it was made at, so forecast accuracy is measurable *by horizon* (KPI-07: MAPE widening from 6.1 % at one period out to 21.6 % at nine). A planning tool that cannot answer "were our forecasts any good" is a data-entry system, and that question needs snapshot history, which most demos do not keep.

## What a reader should conclude

- The **data model** for planning is real: versions, snapshots, horizons, and an accuracy measure computed over them.
- The **planning application** is absent. No input, no spreading, no data actions, no work status.
- The **reporting design skill** is demonstrated, in Fiori rather than in SAC.
- SAC and BPC **product experience** is not demonstrated by this repository and is not claimed by it.

The curated extracts in [`../sac/extracts/`](../sac/extracts/) are built, committed and unchanged — pre-aggregated, pre-joined, signs applied, budget phased. If the tenant becomes reachable with time left on the clock, the reporting story is roughly a weekend away.
