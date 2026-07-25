# Walkthrough video script

**Target: 8 minutes.** Unlisted on YouTube, linked from the README.

Recording notes: OBS Studio, 1920×1080, screen only — no webcam needed. Start HANA Express and the CAP service **before** recording so nothing is waiting on a container. Close Slack, mail and notifications. Do one silent dry run to get the scrolling right; the second take is always better.

**The one rule:** show the thing, then say why it was built that way. Not the reverse. A viewer who sees a dashboard first will listen to the reasoning; a viewer who hears three minutes of reasoning first has already closed the tab.

---

## 0:00 – 0:45 · The question

**Show:** the live dashboard, top of page.

> "This is a month-end close and programme-controlling cockpit for a fictional European space group — four entities, ten programmes, about 940 million euro of revenue. It answers two questions: why is the close slow, and which programmes are burning budget faster than planned.
>
> Everything behind it is synthetic and reproducible from a fixed seed. One-point-one million ledger lines, shaped like S/4HANA's Universal Journal.
>
> This page is a static snapshot on GitHub Pages. No database, no service — which matters, and I'll come back to why."

---

## 0:45 – 2:15 · The findings

**Show:** KPI tiles, then scroll slowly to the burn chart, then the close chart.

> "The group closes in six working days against a target of five. But the average hides the story — one entity takes 8.2 days while the others take about 5.2.
>
> The chart below shows why. Same entity: 22 % of its postings are entered by hand against 13 % elsewhere, and 9 % arrive after the reporting cut-off against 2 %. So it's not that they're slow — it's that a fifth of their ledger is typed manually during the close window. That's a process finding, not a performance one, and it's the difference between fixing something and blaming someone."

**Show:** the burn chart, point at the Kestrel bubble.

> "Programme burn. Horizontal is how far through the schedule a programme is; vertical is how far its spending is running *ahead* of that schedule. On plan is the zero line. Nine programmes sit on it. One doesn't — Kestrel, the launcher, is seven points above, and its estimate at completion is 127 % of budget.
>
> That EAC is deliberately naive: actuals to date plus a rolling three-month run rate times the periods remaining. It ignores commitments and ramp-down, so it's an early-warning indicator, not a forecast — and it's labelled that way in the model, in the view, and in the AMDP, because the fastest way to lose credibility is to let someone put it in a steering pack as a committed number."

---

## 2:15 – 3:30 · The model

**Show:** `hana/sql/02_l2_harmonised.sql`, then `03_l3_reporting.sql`.

> "Three layers on HANA. L1 is one-to-one with the loaded tables — projection and casting only, no joins. That restraint is the point: when a number is wrong, L1 is the layer you can rule out without reading it.
>
> L2 is where business logic lives. Signed amounts, the manual and late flags, currency translation at two rate types.
>
> One decision worth pausing on." **Show the `is_late_posting` comment.** "Late is measured against the date the cut-off was *due*, not the date it was achieved. Measured against the achieved date the KPI is self-cancelling — an entity that runs three days late also gains three days for postings to arrive in, so the slowest closer scores cleanest. I built it that way first. The slow entity scored 2.4 % against a group average of 2.3 %. Against the due date it's 9.1 % against 2.2 %. Same data, and one version tells you nothing.
>
> L3 is star-joined and aggregated. This is LSA++ on native HANA, and there's a document mapping every object to its BW/4HANA equivalent — ADSO, CompositeProvider, DTP — including the four things BW gives you that a native build has to reinvent badly."

---

## 3:30 – 4:30 · The pushdown

**Show:** `hana/sql/04_runrate_function.sql`, then `abap/src/zcl_amdp_runrate.clas.abap` side by side.

> "The run-rate calculation is a SQLScript table function with a window function — ranking each programme's periods by recency so the rolling window is a filter on a rank rather than a correlated subquery per programme.
>
> On the right is the same body inside an ABAP class as an AMDP. And here's the honest part: **that ABAP has never been activated.** I couldn't get an ABAP system — the Platform Trial needs 100 GB of disk and I had 62.
>
> But an AMDP's body *is* SQLScript, and HANA executes it. ABAP is the wrapper. So the logic on the left runs against 1.1 million rows, is benchmarked, and matches an independent Python implementation to within 28 cents on an 800-million-euro EAC. The computation is proven; the wrapper is source only. Every file in that directory says so in its header, and there's a linter that fails the build if one stops saying it."

---

## 4:30 – 5:30 · The check that earns the rest

**Show:** run `python hana/verify_against_python.py`, let it scroll.

> "This is the part I'd want to be asked about.
>
> Every KPI has two implementations: one in SQL across the view stack, one in Python with a test suite behind it. This reconciles them on every run — 35 checks over the same seeded dataset.
>
> It has caught five defects that no dashboard would ever have contradicted. FX impact overstated by six thousand nine hundred euro, because reversals carry the original document's translated amounts and differencing that against a budget rate attributed the carry-over to exchange movement. Budget variance computed at two different grains. A full-year budget flattering an open year by 43 %.
>
> And two from the performance work — which I'll come to — where an optimisation changed the answer by a euro twenty and, separately, silently started including year-end adjustments.
>
> None of those are visible by reading the code. A number only one implementation produces is a number nobody has checked."

---

## 5:30 – 6:45 · Performance, including what failed

**Show:** `docs/performance-report.md`, the results table.

> "Three optimisations planned up front. Two of them made the system slower.
>
> Materialising a monthly aggregate worked — 143,000 rows instead of 1.1 million. FX impact dropped 96 %, budget variance 52 %, for 14 % more memory.
>
> Range partitioning by fiscal year made the target query 20 % slower and cost 23 % more memory. At 1.1 million rows the dataset is two orders of magnitude below where partitioning pays; twenty partitions added overhead and duplicated dictionaries. Reverted.
>
> Hand-pruning columns and joins made it 15 % slower, because HANA's optimiser was already doing it and I'd cost it a join order it had got right on its own. Also reverted.
>
> Both failed experiments are still in the repository. Deleting them leaves a report that only ever succeeds.
>
> Before claiming any of this I measured the noise band — three identical runs, five to eight percent — so nothing under ten percent is called a result."

---

## 6:45 – 7:30 · The focal-point layer

**Show:** `docs/bi-roadmap.md`, then `docs/change-management.md`.

> "The documentation layer is the part that answers the non-technical half of the role.
>
> The migration matrix corrects something that gets repeated constantly: BusinessObjects is supported to 2031. That's true of the 2025 release line — but BI 4.3's mainstream maintenance ends 31 December 2026. An estate on 4.3 has five months, not five years, and that changes the first move from 'adopt SAC' to 'upgrade the platform'.
>
> And the change-management plan is built around the risk that actually matters: this cockpit makes one entity's underperformance visible to the group. Handled badly you get gaming — the checklist closes on time and the postings happen afterwards, every number improves, nothing changes. So the plan shows that entity its own data privately, before anyone else sees it, and states in writing that no individual is identifiable. That last part is enforced in code: user-level drill doesn't exist rather than being restricted, because an authorisation can be granted under pressure and a column that was never modelled can't be."

---

## 7:30 – 8:00 · Close

**Show:** the README requirements table.

> "Three of the four SAP-hosted services I planned to use were unreachable within one weekend — BTP, the ABAP environment, and SAC. Everything built locally has run continuously.
>
> So the requirements table has honest gaps in it. SAC and BPC are not demonstrated and I don't claim them. The ABAP is authored and not activated. Those rows could have been left out of the table.
>
> What's there instead is a database you can rebuild in an hour, a service you can start in one command, a dashboard that opens with nothing running, and 244 automated checks behind the numbers.
>
> Repository link is below. Thanks for watching."

---

## Shot list

| # | Screen | Have ready |
|---|---|---|
| 1 | Live dashboard, top | Hard-refreshed, scrolled to top |
| 2 | Dashboard, burn chart | — |
| 3 | `02_l2_harmonised.sql` | Scrolled to `is_late_posting` |
| 4 | `04_runrate_function.sql` + `zcl_amdp_runrate.clas.abap` | Split editor |
| 5 | Terminal | `verify_against_python.py` ready to run |
| 6 | `docs/performance-report.md` | Scrolled to the results table |
| 7 | `docs/bi-roadmap.md` | Scrolled to the deadline section |
| 8 | `README.md` | Scrolled to the requirements table |

## If you only have three minutes

Sections **0:00**, **0:45**, **4:30** and **7:30**. The findings, the cross-check, and the honest gaps. Everything else is supporting detail.
