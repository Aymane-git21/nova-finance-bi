# Optimisations

Applied **after** the base view stack, deliberately kept out of `hana/sql/` so that `deploy_views.py` reproduces the un-optimised baseline. A performance report you cannot re-measure from scratch is a performance report you cannot check.

## Apply

```bash
python hana/deploy_views.py --drop        # baseline
python hana/benchmark.py --label baseline
```

```bash
python hana/apply_optimisations.py
python hana/benchmark.py --label final --compare baseline
python hana/verify_against_python.py
```

The last command is not optional. An optimisation that changes a result is a defect, and this phase produced two that no dashboard would have contradicted.

## Contents

| File | Verdict | Effect |
|---|---|---|
| `01_monthly_aggregate.sql` | ✅ **Kept** | 143,668-row aggregate. `fx_impact` −96 %, `pl_actuals` −69 % |
| `02_partitioning.sql` | ❌ **Reverted** | Range partitioning by fiscal year. +20 % slower, +23 % memory at this volume |
| `03_column_pruning.sql` | ❌ **Reverted** | Lean projection. +15 % slower — the optimiser was already pruning |
| `04_variance_from_aggregate.sql` | ✅ **Kept** | Budget variance off the aggregate. −52 % |

**Files 02 and 03 are kept in the repository despite being reverted.** They are the evidence for two of the report's findings, and deleting a failed experiment leaves a report that only ever succeeds. Neither is applied by `apply_optimisations.py`; both are runnable if you want to reproduce the negative result.

Full measurements and reasoning: [`../../docs/performance-report.md`](../../docs/performance-report.md) and [ADR-006](../../docs/adr/006-materialisation-strategy.md).
