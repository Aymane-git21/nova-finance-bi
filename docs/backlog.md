# Product backlog — NovaSpace Finance Cockpit

MoSCoW-prioritised, grouped into three sprints. **The "Implemented" column is honest**: it records what this repository actually built, not what was planned. A backlog where everything is green is a backlog written after the fact.

**Personas**

| Persona | Role | What they need |
|---|---|---|
| **Claire** | Group Close Manager | To know which entity is going to be late, before it is late |
| **Marco** | Head of Programme Controlling | To find the programme in trouble while there is still time to act |
| **Sofia** | Entity Finance Manager (NS30) | To know *why* her entity is slow, in terms she can act on |
| **Tom** | Group Financial Controller | To trust the forecast enough to commit to it |
| **Priya** | Group Consolidation Accountant | To clear intercompany differences before they block the close |

---

## Sprint 1 — See the close

| # | Story | MoSCoW | Implemented |
|---|---|---|---|
| 1 | As **Claire**, I need days-to-close per entity and period, so that I can see which entities miss the target and whether it is getting worse. | Must | ✅ `CV_CLOSE_MONITOR`, dashboard |
| 2 | As **Claire**, I need periods where the close has not completed shown as open rather than as zero days, so that I do not report an unfinished close as an excellent one. | Must | ✅ NULL preserved through every layer to the UI |
| 3 | As **Sofia**, I need the manual-posting share for my entity per period, so that I can see the mechanism behind my close time rather than just the symptom. | Must | ✅ `CV_PL_ACTUALS`, restricted key figure |
| 4 | As **Claire**, I need postings entered after the reporting cut-off counted and valued, so that I can quantify what late arrivals cost us. | Must | ✅ `is_late_posting`, measured against the **due** date |
| 5 | As **Sofia**, I need late postings broken down by document type, so that I know which process to fix. | Should | ✅ available in `CV_CLOSE_MONITOR`, not surfaced on the dashboard |
| 6 | As **Claire**, I need the close checklist with due and actual dates per task, so that I can see where in the close the time is lost. | Should | ✅ `FACT_CLOSE_TASKS`, `CV_CLOSE_MONITOR` |
| 7 | As **Claire**, I need an alert when an entity's soft close slips, so that I can intervene during the close rather than review it afterwards. | Could | ❌ Not built — needs scheduling and notification infrastructure |

### Acceptance criteria — story 1

- Days to close = working days from period end to completion of task `T12`, per entity and fiscal period.
- Working days exclude weekends and group holidays.
- A period whose `T12` has not completed returns **null**, never `0`.
- Reconciles to the Python reference implementation to the day. *(Verified: 167 rows, zero variance.)*

### Acceptance criteria — story 4

- Late = `entry_date` later than the **due date** of the `T10` soft-close task for that entity and period.
- Measured against the due date, **not** the achieved date. Against the achieved date the measure is self-cancelling — an entity that runs late gains the extra days and scores clean. *(Measured both ways: 2.4 % vs 2.3 % group average using achieved; 9.1 % vs 2.2 % using due.)*
- Special periods 13–16 are excluded. A year-end adjustment is not a late period-12 posting.
- Reported by count and by value; the two are not assumed equal.

---

## Sprint 2 — Find the programme in trouble

| # | Story | MoSCoW | Implemented |
|---|---|---|---|
| 8 | As **Marco**, I need actual against budget by programme, cost centre and account group, so that I can locate a variance rather than just observe one. | Must | ✅ `CV_BUDGET_VARIANCE` |
| 9 | As **Marco**, I need cost centres that spent with no budget, and budgets with no spend, to appear rather than be silently dropped by a join. | Must | ✅ `FULL OUTER JOIN`, both sides survive |
| 10 | As **Marco**, I need a rolling run-rate and an estimate at completion per programme, so that I am warned before the period variance looks alarming. | Must | ✅ `TF_PROGRAMME_RUNRATE` (SQLScript, window function) |
| 11 | As **Marco**, I need budget consumption plotted against schedule elapsed, so that one glance tells me which programme is burning faster than it is progressing. | Must | ✅ Bubble chart, `sap.viz` |
| 12 | As **Marco**, I need the EAC labelled as an early-warning indicator and not as a forecast, so that I do not commit to a number that ignores commitments and ramp-down. | Should | ✅ Stated in the KPI sheet, the AMDP and the view headers |
| 13 | As **Tom**, I need group-currency variance split between spending and FX movement, so that an entity is not blamed for the pound moving. | Should | ✅ `CV_FX_IMPACT`, dual rate types |
| 14 | As **Marco**, I need commitments and open purchase orders included in the EAC, so that it reflects money already promised. | Won't | ❌ **Deliberately out of scope.** Needs a purchasing source this model does not carry. Its absence is the stated limitation of KPI-05 |

### Acceptance criteria — story 10

- Run-rate = mean of the last *N* closed periods, *N* a parameter, default 3.
- EAC = actuals to date + run-rate × periods remaining to planned end.
- A programme past its end date gets **no extrapolation**: EAC equals actuals to date.
- Special periods excluded from the run-rate — a year-end adjustment is not monthly burn.
- Implemented as pushdown, not as an application-server loop.
- Reproduces the Python reference. *(Verified: within €0.28 on an €800 m EAC.)*

### Acceptance criteria — story 13

- FX impact = Σ(local × actual rate) − Σ(local × budget rate), the budget rate frozen per fiscal year.
- Entities whose local currency is the group currency return **exactly zero**. *(Verified: €0.00 for all three EUR entities.)*
- Reported on the cost base, not net profit — an entity earning and spending in one currency is self-hedged, and a ratio over a thin margin is meaningless.

---

## Sprint 3 — Close the loop

| # | Story | MoSCoW | Implemented |
|---|---|---|---|
| 15 | As **Priya**, I need intercompany pairs that do not net to zero, above a stated materiality threshold, so that I chase real differences and not rounding. | Must | ✅ `CV_IC_RECONCILIATION`, €1 000 threshold |
| 16 | As **Priya**, I need pairs keyed unordered, so that one open item is not counted twice. | Must | ✅ `ic_pair` |
| 17 | As **Tom**, I need forecast accuracy by horizon, so that I know how much to trust a forecast made nine periods out. | Must | ✅ KPI-07, MAPE 6.1 % → 21.6 % |
| 18 | As **Tom**, I need periods with zero actuals excluded from MAPE, so that an undefined value does not silently flatter the result. | Should | ✅ Excluded and asserted by test |
| 19 | As **Claire**, I need the cockpit to open without a database or a running service, so that I can show it in a meeting. | Should | ✅ Frozen snapshot, GitHub Pages |
| 20 | As **Tom**, I need to enter a forecast and see variance recalculate, so that planning and reporting are one tool. | Won't | ❌ **Cut in [ADR-004](adr/004-consumption-layer-without-sac.md).** One finished artifact beats three unfinished ones |
| 21 | As **Sofia**, I need my cost centres in Excel against the same governed model, so that I keep my working method. | Won't | ❌ Cut in ADR-004. The service supports it; the workbook was not built |

---

## Won't have this release

The scope-creep defence, and it is expected to be non-empty:

| Item | Why not |
|---|---|
| Commitments and open POs in the EAC (14) | No purchasing source. Its absence is why KPI-05 is labelled early-warning |
| Planning write-back (20) | ADR-004 |
| Excel workbook (21) | ADR-004 |
| Close-slippage alerting (7) | Needs scheduling and notification infrastructure |
| Per-country holiday calendars | One group calendar. Documented in the data dictionary as a known simplification |
| Balance sheet | P&L only. A close cockpit ignoring the balance sheet is incomplete in reality |
| Percentage-of-completion revenue recognition | Genuinely deep water. Faking it convincingly is worse than omitting it |
| Cash and working capital | Different fact table, different audience |

---

## Score

**21 stories: 11 Must, 6 Should, 1 Could, 3 Won't.**
**17 implemented, 4 not** — the one Could and all three Won't, each with a recorded reason.

| | Must | Should | Could | Won't | Total |
|---|---:|---:|---:|---:|---:|
| Implemented | 11 | 6 | 0 | 0 | **17** |
| Not implemented | 0 | 0 | 1 | 3 | **4** |

Every Must is delivered. That is the only row here that would be a problem if it were not true.
