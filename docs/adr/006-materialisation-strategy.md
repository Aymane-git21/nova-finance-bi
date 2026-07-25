# ADR-006: Materialise the monthly aggregate; do not partition

- **Status:** Accepted
- **Date:** 2026-07-26
- **Related:** [ADR-005](005-published-interface-layer.md), [`../performance-report.md`](../performance-report.md)
- **Deciders:** Solution architect (project author)

## Context

Reporting queries re-aggregated all 1,122,588 journal lines on every execution. Two were slow enough to notice: budget variance at 295 ms warm and FX impact at 200 ms.

Three optimisations were planned before measuring: materialise a monthly aggregate, range-partition by fiscal year, and prune unused columns and joins. All three are standard, all three are defensible on paper, and **two of them made the system slower**.

## Decision

**Materialise a monthly aggregate. Do not partition. Do not hand-prune views.**

`NOVASPACE_L3.AGG_JOURNAL_MONTHLY` holds entity × period × account group × programme × cost centre × special-period flag — 143,668 rows against 1,122,588, rebuilt in full on load. `CV_PL_ACTUALS`, `CV_FX_IMPACT` and `CV_BUDGET_VARIANCE` read it. View signatures are unchanged, so no consumer knows.

Range partitioning was applied, measured, and reverted. Column pruning was applied, measured, and reverted.

## Consequences

**Gained.** 52–96 % on the four queries that matter; 66 % of server-side execution for a full dashboard load. Freed compute of roughly 24 CPU-hours a year on this workload.

**Paid.** 9.2 MB resident (+14 % column store), and a freshness constraint: the aggregate is as old as its last refresh. Acceptable for a cockpit read all day against overnight data, and it must be stated on the report. **The line-item views are kept, not replaced**, so intraday questions remain answerable.

**Two correctness defects were introduced and caught**, neither visible on review:

- Rate-multiplied measures stored at `DECIMAL(18,2)` rounded at the aggregate grain — FX impact off by €1.20 on €650 m.
- Keying on *reporting* period collapsed special periods 13–16 onto period 12, so budget variance silently began including year-end adjustments it must exclude.

Both were found by `verify_against_python.py`. Generalised into two rules now recorded in the golden rules: **an aggregate must preserve the precision of the measures it aggregates**, and **it must preserve every distinction its consumers filter on**.

**Residual damage.** Reverting the partitioning via `MERGE PARTITIONS` did not fully restore the prior state: `programme_runrate` sits ~21 % above baseline. Recorded rather than hidden. A rebuild from the loader would clear it and was not judged worth the churn.

**Revisit if.** The journal exceeds roughly 100 M rows, at which point partitioning becomes worth re-measuring — the reason it failed here is scale, not principle. Or if concurrency arrives: every figure was measured single-user, and materialisation pays *more* under contention, so the current numbers understate it.

## Why this ADR exists at all

The decision is unremarkable — materialise the hot aggregate. What is worth recording is that **two thirds of the plan was wrong, and only measuring revealed it**.

Partitioning failed because 1.12 M rows is about two orders of magnitude below where it pays. Pruning failed because HANA's optimiser was already doing it, and hand-narrowing cost a join order it had got right.

Both were reverted on evidence. The temptation in a portfolio project is to keep an optimisation that sounded sophisticated and quietly not mention that it did not help.
