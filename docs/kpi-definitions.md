# KPI definitions

**NovaSpace Group — month-end close & programme controlling**

This document is written **before** the schema and before any code. The dimensional model exists to serve these eight KPIs; every table and column in [`data-dictionary.md`](data-dictionary.md) traces back to at least one of them. A column that serves no KPI does not get built.

Group currency is **EUR**. Fiscal year = calendar year (SAP fiscal year variant K4), periods 1–12 plus special periods 13–16 for year-end adjustments.

Every KPI here has a reference implementation in [`../data-generator/novaspace/harmonise.py`](../data-generator/novaspace/harmonise.py) and a test in [`../data-generator/tests/test_kpis.py`](../data-generator/tests/test_kpis.py), so a disagreement between this sheet and the code fails a commit rather than surfacing on a dashboard. Measured values on the published seed are in [`dataset-profile.md`](dataset-profile.md). Those same Python implementations are the specification the HANA L2/L3 views and the AMDP must reproduce.

---

## Conventions used throughout

| Term | Meaning here |
|---|---|
| **Grain** | The exact level of detail one row of the result represents. Stated for every KPI because a KPI without a grain is an argument waiting to happen. |
| **Working day** | Mon–Fri excluding the entity's public holidays. Working day *n* of a close = the *n*-th working day after the period-end date. |
| **Signed amount** | Expenses positive, revenue negative. Derived in L2 from the debit/credit indicator, never stored signed in L1. |
| **Actual / Budget / Forecast** | Version dimension values. Actuals come from `FACT_JOURNAL`; Budget and Forecast from their own fact tables. |
| **Owner** | The fictional NovaSpace role accountable for the number. Fictional, but the role names are the ones these KPIs really sit with. |

---

## KPI-01 · Days to close

| | |
|---|---|
| **Business question** | How long does each entity actually take to finish its books, and is it getting better or worse? |
| **Formula** | `working_days(period_end_date → actual_completion_date of the "Hard close / period lock" task)` |
| **Grain** | One value per company code × fiscal year × fiscal period |
| **Target** | ≤ 5 working days. 6–7 amber, ≥ 8 red |
| **Source** | `FACT_CLOSE_TASKS` filtered to `task_id = 'T12'`, joined to `DIM_DATE` for the working-day count |
| **Owner** | Group Close Manager |
| **Notes** | Measured on task completion, not on the last posting — a late posting after the lock is a control failure, which is what KPI-03 is for. If the hard-close task has no completion date the period is *not closed*; it must be reported as open, never as zero and never as null-suppressed. |
| **Story it should reveal** | One entity is consistently 3–4 days slower than the rest. The dashboard should make that visible without a caption saying so. |

## KPI-02 · % manual journal entries

| | |
|---|---|
| **Business question** | How much of the ledger is typed in by hand rather than produced by a process? |
| **Formula** | `count(manual lines) / count(all lines)` where manual = `document_type IN ('SA','SB')`. Also reported by value: `Σ abs(amount_group_currency)` on the same filter |
| **Grain** | One value per company code × fiscal year × fiscal period. Drillable to cost centre and document type |
| **Target** | ≤ 12 % by count. > 20 % red |
| **Source** | `FACT_JOURNAL` → `is_manual_posting` derived in L2 |
| **Owner** | Entity Finance Manager |
| **Notes** | Count and value tell different stories and both are needed: a handful of very large manual entries is a different risk from hundreds of small ones. Report both, never blend them into one number. |
| **Story it should reveal** | Manual share correlates with days to close. It is the *mechanism* behind KPI-01, not an independent problem. |

## KPI-03 · Late postings

| | |
|---|---|
| **Business question** | Which postings arrived after the reporting cut-off, and what were they worth? |
| **Formula** | Count and `Σ abs(amount_group_currency)` where `entry_date > due_date` of the T10 cut-off for that entity/period |
| **Grain** | Company code × fiscal year × fiscal period, drillable to document type and cost centre |
| **Target** | ≤ 2 % of period line count. > 5 % red |
| **Source** | `FACT_JOURNAL.entry_date` vs the **due date** of the `T10 Soft close / reporting cut-off` task in `FACT_CLOSE_TASKS` |
| **Owner** | Group Close Manager |
| **Notes** | **This KPI is the reason `entry_date` exists separately from `posting_date`.** A posting can be dated inside the period and still be entered days after the cut-off — that gap is the whole measurement. Any model that carries only `posting_date` cannot compute this, which is exactly the modelling point worth making about ACDOCA.<br><br>**Measured against the date the cut-off was *due*, not the date it was achieved.** This looks like a detail and decides whether the KPI measures anything. Against the achieved cut-off the measure is self-cancelling: an entity running three days late also gains three extra days for postings to arrive in, so its late-posting rate collapses to the group average and the slowest closer scores cleanest. Built that way here, the chronically late entity scored 2.4 % against a group average of 2.3 % — the problem was real in the data and invisible in the measure. Against the due date it scores 9.1 % against 2.2 %. A cut-off an entity sets for itself after the fact is not a control. |
| **Measured** | 2.1–2.2 % across three entities, **9.1 %** for the slow closer. See [`dataset-profile.md`](dataset-profile.md) |
| **Story it should reveal** | Late postings cluster in the same entity and the same document types that drive KPI-02. |

## KPI-04 · Budget vs actual variance

| | |
|---|---|
| **Business question** | Where are we against plan, in euros and in percent? |
| **Formula** | `variance = actual − budget`; `variance_pct = (actual − budget) / abs(budget)` (undefined, not zero, where budget = 0) |
| **Grain** | Programme × cost-centre hierarchy node × account group × fiscal year × fiscal period |
| **Target** | Within ±5 % at programme level. > +10 % red |
| **Source** | `FACT_JOURNAL` (actuals, signed, group currency) vs `FACT_BUDGET` version `BUDGET` |
| **Owner** | Head of Programme Controlling |
| **Notes** | Budget is annual; actuals are periodic. Comparing them requires an explicit **phasing rule** — NovaSpace phases budget evenly across 12 periods and states it. Any other rule is defensible; leaving it implicit is not. Special periods 13–16 carry no budget and must be shown separately rather than silently inflating period 12. |
| **Story it should reveal** | One programme crosses from favourable to unfavourable at mid-year and never comes back. |

## KPI-05 · Programme run-rate & simple EAC

| | |
|---|---|
| **Business question** | If the last three months are the new normal, what does this programme cost by the time it ends? |
| **Formula** | `run_rate = Σ(actuals in last 3 closed periods) / 3`; `EAC = actuals_to_date + run_rate × remaining_periods_to_programme_end` |
| **Grain** | One row per programme × as-of fiscal period |
| **Target** | `EAC ≤ total_budget`. `EAC > 110 % of budget` red |
| **Source** | `FACT_JOURNAL` + `DIM_PROGRAMME.end_date` and `.total_budget_eur`. Implemented as a **SQLScript table function with a window function** (`hana/runrate.sql`), wrapped by `ZCL_AMDP_RUNRATE` |
| **Owner** | Head of Programme Controlling |
| **Notes** | Deliberately the naive EAC. It ignores the remaining work profile, commitments and ramp-down — a real EAC uses ETC from the programme plan. Stating that limitation is the point: this is an *early-warning indicator*, not a forecast, and it should be labelled that way on the dashboard. Programmes past their end date return `EAC = actuals_to_date` and no run-rate extrapolation. |
| **Story it should reveal** | The overspending programme trips this well before its budget-vs-actual variance looks alarming in any single period. |

## KPI-06 · FX impact

| | |
|---|---|
| **Business question** | How much of the group-currency variance is spending, and how much is just the pound moving? |
| **Formula** | `fx_impact = Σ(amount_local × actual_rate) − Σ(amount_local × constant_rate)`, where constant rate = the FY budget rate held flat all year |
| **Grain** | Company code × fiscal year × fiscal period × account group |
| **Target** | Informational — no threshold. Reported as a variance-bridge component |
| **Source** | `FACT_JOURNAL.amount_local_currency` × `RATES` at both `rate_type = 'M'` (monthly average actual) and `rate_type = 'B'` (budget/constant) |
| **Owner** | Group Treasury |
| **Notes** | Only NS40 (UK, GBP) generates meaningful FX impact; the other three entities are EUR and net to zero by construction. That is realistic and it also keeps the FX story visually separable from the slow-close story, which sits in a different entity on purpose. Document currency ≠ local currency on some postings, so the model carries all three currency types as SAP does.<br><br>**Report on the cost base, not on net profit.** An entity that earns and spends in the same currency is largely self-hedged, so FX impact on its bottom line is small by construction — and expressing it as a share of a thin margin divides by something near zero and produces a ratio that swings on nothing. The controller's question is "did we spend more, or did the pound move", and that is a question about cost. |
| **Measured** | **−€4.4 m** on NS40, 0.67 % of its cost base. Euro entities: exactly €0.00 |
| **Story it should reveal** | Part of NS40's apparent cost growth is rate movement, not behaviour. The waterfall must separate them or the entity gets blamed for the wrong thing. |

## KPI-07 · Forecast accuracy (MAPE)

| | |
|---|---|
| **Business question** | Are our forecasts worth acting on? |
| **Formula** | `MAPE = mean( abs(actual − forecast) / abs(actual) )` over the periods a given forecast snapshot covered, excluding periods where `actual = 0` |
| **Grain** | Cost centre × forecast snapshot version (`FC-Q1`…`FC-Q4`) × horizon in periods |
| **Target** | ≤ 10 % at 1-period horizon, ≤ 20 % at 3-period horizon |
| **Source** | `FACT_FORECAST` (quarterly rolling snapshots) vs `FACT_JOURNAL` actuals |
| **Owner** | Group Financial Controller |
| **Notes** | Must be reported **by horizon**. A forecast made one month out and one made nine months out are not the same claim, and averaging them together produces a number that means nothing. The `actual = 0` exclusion is mandatory — MAPE is undefined there and silently dropping to zero flatters the result. |
| **Story it should reveal** | Accuracy degrades predictably with horizon, and degrades faster for the programme that is running away. |

## KPI-08 · Intercompany mismatches

| | |
|---|---|
| **Business question** | Which intercompany pairs do not net to zero before consolidation? |
| **Formula** | For each `(company_code, ic_partner_company, fiscal_year, fiscal_period)` pair: `mismatch = Σ amount_group_currency(A→B) + Σ amount_group_currency(B→A)`. Flagged where `abs(mismatch) > 1 000 EUR` |
| **Grain** | Ordered entity pair × fiscal year × fiscal period |
| **Target** | Zero flagged pairs. Any flagged pair is an open item for the close team |
| **Source** | `FACT_JOURNAL` where `is_intercompany = true`, self-joined on the partner |
| **Owner** | Group Consolidation Accountant |
| **Notes** | The 1 000 EUR tolerance is deliberate and must be stated on the report — without a materiality threshold, translation rounding alone makes pairs look broken. Mismatches are reported by pair, not by entity, because "who is out" is meaningless without "with whom", and the pair is keyed unordered so one open item is not counted twice. |
| **Measured** | **5 of 252** pair-periods flagged (2.0 %); largest difference €37,065.61; reconciling pairs net to **€0.00** exactly |
| **Story it should reveal** | Roughly 2 % of pairs break, concentrated in periods where the slow entity was still posting after its partner had closed. The reconciliation problem is a *timing* problem. |

---

## Coverage check

Every KPI resolves against the model, and every fact table earns its place:

| Source object | KPIs served |
|---|---|
| `FACT_JOURNAL` | 02, 03, 04, 05, 06, 07, 08 |
| `FACT_CLOSE_TASKS` | 01, 03 |
| `FACT_BUDGET` | 04 |
| `FACT_FORECAST` | 07 |
| `RATES` | 06 |
| `DIM_PROGRAMME` | 04, 05 |
| `DIM_COST_CENTER` | 04, 07 |
| `DIM_GL_ACCOUNT` | 02, 04, 06 |
| `DIM_DATE` | 01, 03 |
| `DIM_COMPANY_CODE` | all |

## What is deliberately not measured

Named here so the omissions read as decisions rather than oversights:

- **Percentage of completion / revenue recognition.** Genuinely deep water for long-term contracts, and faking it convincingly is worse than not doing it. Mentioned in the glossary, not modelled.
- **Headcount and FTE-based metrics.** Would need an HR data source; that means personal data, which [`gdpr-and-data-protection.md`](gdpr-and-data-protection.md) explicitly keeps out of this model.
- **Cash and working capital.** A different fact table and a different audience. Out of scope for a close-and-programme cockpit; a candidate for the backlog's "Won't have this release" bucket.
- **Commitments and open purchase orders.** These would materially improve the EAC in KPI-05, which is exactly why their absence is called out in that KPI's notes rather than hidden.
