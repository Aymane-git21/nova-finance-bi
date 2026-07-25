# Data dictionary

> **Placeholder — filled in Phase 2.2.**
> Every table, every column: name, type, nullability, description, sample values, and the KPI(s) it serves.

Planned star schema — dimensions: `DIM_COMPANY_CODE` · `DIM_COST_CENTER` (3-level hierarchy) · `DIM_PROGRAMME` · `DIM_GL_ACCOUNT` · `DIM_DATE` (fiscal calendar incl. special periods 13–16) · `RATES`.
Facts: `FACT_JOURNAL` (ACDOCA-shaped, ~1M lines) · `FACT_BUDGET` · `FACT_FORECAST` · `FACT_CLOSE_TASKS`.
