# SAP Analytics Cloud

Screenshots, exports and notes from the SAC trial. **Built in Phase 6.**

**Do not register the SAC trial before Phase 6.** The 30-day clock starts at registration and extends to roughly 90 days only if extended around day 20. Everything in here is captured continuously during the sprint, not at the end, because the tenant will eventually go away and these artifacts are what survives.

## Planned contents

- **Reporting story**, three pages: CFO overview (KPI tiles + trend) · Programme controlling (budget vs actual, run-rate/EAC, variance waterfall including FX) · Close monitor (task timeline per entity, late postings, the chronically slow entity emerging from the data).
- **Planning model** on `sac_budget_actual` with a Version dimension (Actual / Budget / Forecast): manual entry on Forecast, spreading an annual budget down to periods, copy Actual→Forecast, one data action, variance table. Plus the BPC-concept mapping (versions ≈ categories, data actions ≈ planning functions, input forms ≈ input schedules).
- **`live-vs-import.md`** — why a live connection beats import in production (freshness, no replication, inherited source security, no volume ceiling) and when import acquisition is still legitimate.
- 3–4 minute screen recording, unlisted on YouTube, linked from the root README.
