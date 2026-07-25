# Performance & eco-design report

Measured on SAP HANA, express edition 2.00.088, 1,122,588 journal lines, 9.4 GB allocated to the container. Every figure here comes from [`hana/benchmark.py`](../hana/benchmark.py) and the raw runs are committed under [`hana/benchmarks/`](../hana/benchmarks/).

**Headline: 52–96 % faster on the four queries that matter, for 14 % more memory. Two of the three optimisations planned up front were wrong, and only measuring found that out.**

---

## Method

Getting this wrong is easy and the easy version flatters you.

- **Cold and warm reported separately.** The plan cache is cleared before each cold run. Quoting only warm figures hides what a user pays for the first query of the morning; quoting only cold ones overstates steady-state load.
- **Median of nine runs**, not a single timing. A single measurement on a laptop running Docker is noise.
- **Noise band measured, not assumed.** Three identical back-to-back runs established run-to-run variation of **±5–8 %** ([`noise-1..3.json`](../hana/benchmarks/)). Nothing below 10 % is claimed as a result.
- **Client wall-clock and server execution time both captured.** Wall-clock includes fetch and is the honest end-to-end figure; server time comes from `M_SQL_PLAN_CACHE`. Where they diverge the bottleneck is transfer, not the database.
- **The benchmarked queries are the ones the dashboard actually issues.** Benchmarking something nobody runs produces a number nobody needs.

**Correctness gate:** [`hana/verify_against_python.py`](../hana/verify_against_python.py) ran after every change. An optimisation that alters a result is a defect, not a trade-off — and this gate caught two, described below.

---

## Baseline

| Query | Cold ms | Warm ms | Rows |
|---|---:|---:|---:|
| `pl_actuals_full` | 178.6 | 40.4 | 1,176 |
| `pl_actuals_one_year` | 74.1 | 17.3 | 336 |
| **`budget_variance_one_year`** | 646.3 | **295.3** | 11 |
| `programme_runrate` | 191.8 | 47.6 | 10 |
| `close_monitor` | 39.8 | 2.6 | 4 |
| **`fx_impact`** | 289.0 | **199.9** | 4 |

Column store: **53.2 MB**, of which `FACT_JOURNAL` 50.5 MB.

The two slow queries both re-aggregate all 1.12 M lines on every execution.

---

## What was tried

### ✅ 1. Materialise the monthly aggregate — kept

No report asks a question at line-item grain. The dashboard, the variance analysis and the FX bridge all group to entity × period × account group × programme × cost centre. That grain is **143,668 rows, not 1,122,588** — a 7.8× reduction — and it changes once per load, not once per query.

`AGG_JOURNAL_MONTHLY` is a real column table rebuilt from L2, and `CV_PL_ACTUALS` and `CV_FX_IMPACT` were repointed at it. **View names did not change**, so the API layer, CAP, the dashboard and the cross-check carried on unaware — the payoff of having a published interface ([ADR-005](adr/005-published-interface-layer.md)).

This is the BW conversation about persisting a standard ADSO versus leaving a CompositeProvider virtual, in different vocabulary and with the same answer: virtual until read volume justifies persisting.

**Two defects it introduced, both caught by the cross-check and neither visible on inspection:**

| Defect | Symptom | Cause | Fix |
|---|---|---|---|
| Precision loss | FX impact off by **€1.20** on a €650 m base | Amounts multiplied by a 6-decimal rate stored at `DECIMAL(18,2)`; 143k intermediate roundings do not cancel | Store rate-multiplied measures at `DECIMAL(28,6)` |
| Collapsed distinction | Budget variance silently began including year-end adjustments | The aggregate keys on *reporting* period, so periods 13–16 land on 12 and become indistinguishable | Keep `is_special_period` in the grain |

Two rules worth carrying: **an aggregate must preserve the precision of the measures it aggregates**, and **it must preserve every distinction its consumers filter on**. Collapsing one is not a loss of detail, it is a change of answer.

### ❌ 2. Range partitioning on fiscal year — reverted

Partition `FACT_JOURNAL` by fiscal year so year-bounded queries prune. Two levels were needed: HANA will not range-partition on a column outside a unique constraint, so level 1 is a hash on `journal_id` and level 2 the range that prunes.

It worked, and it made things worse.

| | Before | After | Change |
|---|---:|---:|---:|
| `budget_variance_one_year` | 217.1 ms | 260.4 ms | **+20 %** |
| `pl_actuals_full` | 14.3 ms | 14.9 ms | +4 % |
| Column store | 61.8 MB | 76.0 MB | **+23 %** |

**At 1.12 M rows the dataset is roughly two orders of magnitude below where partitioning pays.** The column store already dictionary-compresses and scans this volume in milliseconds; 20 partitions added per-partition overhead and duplicated dictionaries. SAP's own guidance points at partitioning for the 2-billion-row-per-partition limit and for very large tables — not for this.

Reverted with `MERGE PARTITIONS`. One residual cost: `FACT_JOURNAL` settled at 49.1 MB and `programme_runrate` at ~57 ms against 47.6 ms baseline — a **+21 % regression that the round-trip did not fully give back**. Reported rather than quietly dropped.

### ❌ 3. Prune unused columns and joins — reverted

`CV_BUDGET_VARIANCE` read the fully harmonised `L2.V_JOURNAL`: six joins, ~40 columns. The query needs seven columns and one join. A lean projection was built to drop the rest — notably the close-task join, which exists only for `is_late_posting`, a column this query never reads.

| | Baseline | After pruning | Change |
|---|---:|---:|---:|
| `budget_variance_one_year` | 295.3 ms | 332–378 ms | **+15 % (slower)** |

Consistently slower across three runs against a ±8 % noise band, so not noise.

**Why it failed is the useful part.** HANA's optimiser was already pruning the unreferenced columns; the remaining joins were to dimension tables of 4–200 rows, which it resolves as dictionary lookups. There was nothing real left to remove, and hand-narrowing the view cost a join order the optimiser had got right on its own.

### ✅ 4. Serve budget variance from the aggregate — kept

The measurement pointed where intuition had not: the aggregate already held every column budget variance needed. Repointing its actual side took it from 295.3 ms to **142.1 ms**.

---

## Final results

| Query | Baseline warm | Final warm | Change |
|---|---:|---:|---:|
| `fx_impact` | 199.9 ms | **8.7 ms** | **−96 %** |
| `pl_actuals_full` | 40.4 ms | **12.7 ms** | **−69 %** |
| `pl_actuals_one_year` | 17.3 ms | **7.5 ms** | **−57 %** |
| `budget_variance_one_year` | 295.3 ms | **142.1 ms** | **−52 %** |
| `close_monitor` | 2.6 ms | 2.7 ms | +4 % (noise) |
| `programme_runrate` | 47.6 ms | 57.5 ms | +21 % (partitioning residue) |

| | Baseline | Final | Change |
|---|---:|---:|---:|
| Column store total | 53.2 MB | 60.7 MB | **+14 %** |
| `AGG_JOURNAL_MONTHLY` | — | 9.2 MB / 143,668 rows | new |

**Server-side execution for one full dashboard load: 667.6 ms → 229.6 ms, a 66 % reduction.**

All 24 cross-checks against the Python reference pass in the final state.

---

## Eco-design

The requirement is to design digital services to minimise resource footprint. The mechanism here is simple and it is the same one that made the queries fast: **work not done**.

### Compute avoided

Order-of-magnitude reasoning, stated as such. The inputs are assumptions and are labelled.

| Input | Value | Basis |
|---|---|---|
| Server time per dashboard load, before | 667.6 ms | Measured |
| Server time per dashboard load, after | 229.6 ms | Measured |
| Saving per load | **438 ms** | Measured |
| Loads per day | 800 | **Assumed**: 40 users × 20 refreshes |
| Working days per year | 250 | Assumed |

**≈ 350 s of CPU per day, ≈ 24 CPU-hours per year**, on a workload whose baseline was ~37 CPU-hours. Roughly two thirds of the compute for this cockpit stops being spent.

Deliberately not converted to kWh or CO₂. That conversion needs the PUE and carbon intensity of a specific data centre, and multiplying a laptop measurement by a published grid average produces a number with four significant figures and no meaning. The defensible claim is the ratio, not a gram count.

The memory cost is real and is counted: **+7.5 MB resident, permanently, to avoid ~24 CPU-hours a year.** At this scale that trade is obviously right. It would not be if the aggregate were 10× the base table.

### Retention policy

The largest eco-design lever is not query tuning, it is **not keeping data you do not read**. This aligns with [`gdpr-and-data-protection.md`](gdpr-and-data-protection.md), which wants the same thing for a different reason.

| Tier | Retention | Rationale |
|---|---|---|
| Line item with user attribution | 24 months | Audit and dispute window. Personal data ages out first |
| Line item without user attribution | 7 years | Statutory retention for accounting records |
| Monthly aggregate | Indefinite | 9.2 MB for 3.5 years. Keeping it forever costs almost nothing |

This is the HANA-native analogue of BW cube compression plus archiving to Near-Line Storage. The aggregate is what NLS leaves queryable after the line items are aged out — the pattern is identical, only the vocabulary differs.

**Applied to this dataset:** ageing line items beyond 24 months would drop `FACT_JOURNAL` from 1.12 M rows to roughly 340 k, about 15 MB reclaimed, with every KPI in this report still answerable from the aggregate. The reporting layer would not notice.

### Scheduling

- **Refresh the aggregate on load, nightly** — not per query, and not on a timer that fires when nothing has changed. It is derived data; recomputing it when its source has not moved is pure waste.
- **Full rebuild, not delta, at this volume.** It takes under a second and cannot drift. A delta at 100× the volume would be necessary and would need reconciliation to go with it — a silently drifted aggregate is worse than no aggregate.
- **Do not schedule report bursts.** The cockpit is read interactively during the close. Pre-generating and mailing PDFs to people who may not open them is the classic way a reporting estate burns compute producing artefacts nobody reads.

---

## Honest limitations

- **Laptop, not a server.** Docker on Windows with 9.4 GB. Ratios transfer; absolute milliseconds do not.
- **Single user, no concurrency.** Every result here is uncontended. Concurrency is where materialisation pays *more* — the aggregate is read many times and built once — so these figures understate the benefit under load, but that is an argument, not a measurement.
- **No PlanViz.** `EXPLAIN PLAN` and `M_SQL_PLAN_CACHE` were used. PlanViz needs Eclipse with SAP HANA Tools, which was not set up.
- **1.12 M rows is small.** It is precisely why partitioning failed. Conclusions about partitioning here should not be carried to a 500 M-row table; the conclusion that *you must measure before assuming* should be.
- **Assumed query frequency.** The 800 loads/day figure is invented. The measured saving per load is not.

---

## What this phase actually demonstrates

Two of three planned optimisations were wrong. The one that worked introduced two correctness defects that no dashboard would ever have contradicted, and both were caught only because an independent implementation recomputes every number.

That is the finding worth carrying: **performance work without a correctness gate is how you make a system fast and wrong**, and the difference is invisible until someone reconciles a figure by hand months later.
