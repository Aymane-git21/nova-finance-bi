# SAC build guide

Step by step, in order. Every design decision is already made — follow it and you will not have to stop and think about grain, sign or phasing halfway through.

**Menu paths are guidance, not gospel.** SAC's UI wording shifts between releases; the *intent* of each step is what matters, and it is stated with every one.

---

## ⏰ Before anything

| | Date | Days from today (2026-07-26) |
|---|---|---:|
| Registered | 2026-07-25 | — |
| **Extend by** | **2026-08-14** | **+19** |
| Ends if not extended | 2026-08-24 | +29 |
| Ends if extended | 2026-10-23 | +89 |

**Put a calendar reminder on 2026-08-12**, not the 14th. Two days of slack for the extension flow to misbehave. Missing it costs 60 days and cannot be undone.

**Screenshot as you go, not at the end.** Every page, every model definition, the moment it looks right. The tenant will eventually vanish and `sac/` is what survives it.

---

## The four files

All in [`extracts/`](extracts/), regenerated with a proper date column. If you already uploaded the older versions, **replace them** — the old ones had no `period_date` and SAC cannot build a time dimension without it.

| File | Rows | Model | Purpose |
|---|---:|---|---|
| `sac_pl_actuals.csv` | 1,296 | Analytic | CFO overview — P&L by entity, period, account group |
| `sac_programme_costs.csv` | 8,986 | Analytic | Programme controlling |
| `sac_close_tasks.csv` | 2,016 | Analytic | Close monitor |
| `sac_budget_actual.csv` | 20,798 | **Planning** | Actual / Budget / Forecast on a Version |

Everything is pre-aggregated, pre-joined, signs applied (**expenses positive, revenue negative**) and budget already phased evenly across twelve periods. You should not need to compute anything in SAC.

---

## Step 1 — Import and model each analytic file

*Modeler → New Model → import a CSV.* Repeat for the first three files.

For each, the only thing that needs care is **which columns are dimensions and which are measures**. SAC guesses, and it guesses wrong on anything numeric that is really an identifier.

### `sac_pl_actuals` → model **NS_PL_Actuals**

| Column | Type | Notes |
|---|---|---|
| `company_code` | Dimension | |
| `company_name` | Dimension | Set as the **description** of `company_code`, not a separate dimension |
| `fiscal_year` | Dimension | **Force to dimension.** SAC will offer to make it a measure |
| `fiscal_period` | Dimension | Same |
| **`period_date`** | **Date dimension** | **Granularity: Month.** This is the one that matters |
| `fiscal_period_label` | Dimension | Readable axis labels |
| `pl_section`, `account_group` | Dimension | |
| `account_group_name` | Dimension | Description of `account_group` |
| `amount_group_currency` | **Measure** | Currency EUR, aggregation SUM |
| `line_count`, `manual_line_count` | **Measure** | SUM |

**Add one calculated measure:** `Manual share` = `manual_line_count` / `line_count`, formatted as a percentage. Do not pre-compute this in the CSV — a ratio that has been averaged over aggregated rows is wrong, and letting SAC divide the two sums after aggregation is the only way it stays right at every level.

### `sac_programme_costs` → model **NS_Programme_Costs**

Same pattern. `programme_id` dimension with `programme_name` as description, `programme_type` dimension, `period_date` as the Date dimension at Month granularity, `amount_group_currency` and `total_budget_eur` as measures.

`total_budget_eur` is a **programme attribute repeated on every row**, so summing it across periods gives nonsense. Set its aggregation to **MIN** (or MAX — same result, it is constant per programme). This is the classic non-additive-measure trap and it is worth knowing you avoided it deliberately.

### `sac_close_tasks` → model **NS_Close_Monitor**

| Column | Type | Notes |
|---|---|---|
| `days_to_close` | **Measure**, aggregation **AVERAGE** | Not SUM. Summing days-to-close across periods is meaningless |
| `delay_working_days` | Measure, AVERAGE | Same |
| `is_period_open` | Dimension | |
| `actual_completion_date` | Date | **Will be blank for one row.** Leave it blank |
| `period_end_date`, `due_date` | Date | |

**Do not fill the blank `actual_completion_date`.** One period is genuinely still open — the slow entity's most recent hard close has not happened. `days_to_close` is empty there, not zero. If SAC offers to replace nulls with 0, **decline**. A zero-day close is the single most misleading number this model can produce, and that row is in the data specifically to prove the pipeline handles it.

---

## Step 2 — Build the story

*Stories → New Story → Canvas.* One story, three pages. Name it **NovaSpace Finance Cockpit**.

**Design rule for all three pages:** restraint beats variety. One question per page, answered above the fold. A CFO reads this in thirty seconds.

### Page 1 — CFO overview

| Element | Type | Configuration |
|---|---|---|
| Days to close | Numeric point | `days_to_close`, filtered to `task_id = T12`, AVERAGE. Target 5 |
| Manual JE share | Numeric point | The calculated measure. Threshold: green ≤12 %, amber ≤20 %, red above |
| Group P&L | Numeric point | `amount_group_currency` from NS_PL_Actuals, current year |
| Open IC items | Numeric point | Hard-code 5 with a text note, or omit — the extract does not carry it |
| P&L trend | Line chart | X = `period_date`, measure = `amount_group_currency`, colour = `pl_section` |
| Days to close by entity | Bar chart | X = `company_code`, measure = avg `days_to_close`, **sorted descending** |

The bar chart sorted descending is the page. One entity is visibly taller and the reader finds it without being told.

### Page 2 — Programme controlling

| Element | Type | Configuration |
|---|---|---|
| Cost by programme | Bar chart | `programme_name` × `amount_group_currency`, descending |
| Burn trend | Line chart | X = `period_date`, colour = `programme_name`, filtered to the top 5 |
| Budget vs actual | Table | Rows `programme_name`, columns Version, measure `amount_group_currency` (uses the planning model) |
| Variance | Waterfall | From the planning model, Budget → Actual by account group |

**Filter the line chart to five programmes.** Ten series is a colour lookup, not a chart.

### Page 3 — Close monitor

| Element | Type | Configuration |
|---|---|---|
| Task completion | Table or heatmap | Rows `company_code`, columns `task_name`, measure avg `delay_working_days` |
| Days to close over time | Line chart | X = `period_date`, colour = `company_code`. **This is the money chart** |
| Open periods | Table | Filtered `is_period_open = true` |

The line chart is where the slow entity is unmistakable: one line consistently above the others for three years. If it does not jump out, the chart is wrong, not the data.

---

## Step 3 — The planning model

This is the part that answers BPC, and it is the reason `sac_budget_actual.csv` is separate.

*Modeler → New Model → import `sac_budget_actual.csv` → set model type to **Planning**.*

### Mapping the Version column

**Map `version` to SAC's built-in Version dimension, not to a generic dimension.** This is the single most important step in the whole guide.

SAC planning models have a native Version dimension with categories — Actual, Budget, Planning, Forecast. Our three values map onto it directly:

| CSV value | SAC category |
|---|---|
| `ACTUAL` | Actual |
| `BUDGET` | Budget |
| `FORECAST` | Forecast |

**That mapping is the BPC "Category" concept, one-for-one.** If you import `version` as an ordinary dimension the model still works and you lose every planning feature that depends on versions — which is all of them. It is also the answer to "what's a BPC category" in an interview, so getting it right is worth the extra two minutes.

`period_date` becomes the Date dimension at Month granularity — planning needs it for spreading.

### The five things to demonstrate

In this order. Screenshot each.

1. **Manual entry.** Create a private version from Forecast. Type a number into one cell. Show it turning yellow (unpublished), then publish it.
2. **Spreading.** Take an annual figure on a cost centre and distribute it across twelve periods. Show equal distribution, then weighted. *BPC equivalent: a distribution planning function.*
3. **Copy Actual → Forecast.** Copy actuals for closed periods into the forecast version as its starting point. *BPC equivalent: a copy function — the most-used one in any planning system.*
4. **One data action.** Simplest useful case: uplift Forecast by a percentage for one programme. Run it, show the before and after. *BPC equivalent: script logic.*
5. **Variance table.** Rows = programme, columns = Version, plus a calculated Actual − Budget in absolute and percent.

### What to say about it

The honest framing, and it is stronger than pretending otherwise:

> "This is a planning model with versions, spreading, a copy action and a data action. What it is not is a planning *implementation* — no work status, no approval workflow, no allocation hierarchy. Those are where BPC projects actually spend their time."

Say that before you are asked. Volunteering the boundary of what you built is the difference between a demo and a claim.

---

## Step 4 — Capture

Before the tenant expires:

- [ ] Screenshot every story page, full screen, no browser chrome
- [ ] Screenshot each model's dimension/measure definition
- [ ] Screenshot the Version dimension mapping specifically — it is the BPC evidence
- [ ] Screenshot each of the five planning steps, before and after
- [ ] **3–4 minute screen recording**: story walkthrough then planning demo
- [ ] Upload unlisted to YouTube, put the link in `sac/README.md` and the root README
- [ ] Drop all screenshots into `sac/screenshots/`

**Then update the honest bits**, which currently say SAC was not demonstrated:

- [ ] [`../docs/sac-and-bpc.md`](../docs/sac-and-bpc.md) — the verdict table and "what a reader should conclude"
- [ ] [`../docs/adr/004-consumption-layer-without-sac.md`](../docs/adr/004-consumption-layer-without-sac.md) — add the revisit note
- [ ] [`../README.md`](../README.md) — the SAC and BPC rows in the requirements table

Tell me when the screenshots are in and I will rewrite those three.

---

## If something looks wrong

The numbers in SAC must match [`../docs/dataset-profile.md`](../docs/dataset-profile.md). Spot-check three:

| Check | Expected |
|---|---|
| Days to close, NS30, average | **8.17** |
| Days to close, other three | **5.1 – 5.4** |
| Manual share, NS30 | **22.4 %** |

If NS30's days-to-close comes out near 5, the aggregation is set to SUM instead of AVERAGE, or the `task_id = T12` filter is missing. Those two account for almost every discrepancy you are likely to hit.
