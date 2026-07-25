# Performance & eco-design report

> **Placeholder — filled in Phase 7.**
> Before/after benchmarks on the heaviest calculation view (runtime, records scanned, peak memory) across three measured optimisations: monthly pre-aggregation, partition/filter pushdown, column pruning. Plus the eco-design section: data scanned avoided per query × query frequency, a retention proposal, and a refresh-scheduling recommendation.

Measurement tools: `EXPLAIN PLAN`, PlanViz. Numbers are measured, never estimated.
