-- ===========================================================================
-- L3 - REPORTING / virtual data mart
--
-- BW/4HANA analogue: CompositeProvider plus BEx query elements. Star-joined,
-- aggregated, cube semantics. This is the only layer a report should touch.
--
-- Restricted key figures (BW: a measure filtered by a characteristic) appear
-- here as conditional SUMs - "personnel cost, manual postings only" is a column,
-- not something every consumer re-derives with its own WHERE clause.
-- ===========================================================================

CREATE SCHEMA "NOVASPACE_L3";

-- ---------------------------------------------------------------------------
-- CV_PL_ACTUALS - group P&L. Serves KPI-02.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW "NOVASPACE_L3"."CV_PL_ACTUALS" AS
SELECT
  j."company_code",
  j."company_name",
  j."fiscal_year",
  j."reporting_period"                        AS "fiscal_period",
  j."pl_section",
  j."account_group",
  j."account_group_name",

  SUM(j."signed_amount_group")                AS "amount_group_currency",
  COUNT(*)                                    AS "line_count",

  -- Restricted key figures.
  SUM(CASE WHEN j."is_manual_posting" = TRUE THEN j."signed_amount_group" ELSE 0 END)
                                              AS "amount_manual",
  SUM(CASE WHEN j."is_manual_posting" = TRUE THEN 1 ELSE 0 END)
                                              AS "line_count_manual",
  SUM(CASE WHEN j."is_late_posting" = TRUE THEN 1 ELSE 0 END)
                                              AS "line_count_late",
  SUM(CASE WHEN j."fiscal_period" > 12 THEN 1 ELSE 0 END)
                                              AS "line_count_year_end_adjustment"
FROM "NOVASPACE_L2"."V_JOURNAL" j
GROUP BY
  j."company_code", j."company_name", j."fiscal_year", j."reporting_period",
  j."pl_section", j."account_group", j."account_group_name";

-- ---------------------------------------------------------------------------
-- CV_BUDGET_VARIANCE - KPI-04.
--
-- Revenue is excluded on both sides. Budgets here are set on cost centres and
-- revenue lines carry no cost centre, so including revenue in the actual would
-- compare it against a budget that never contained any - the classic way a
-- variance report comes out favourable for no reason.
--
-- FULL OUTER JOIN, not INNER: a cost centre that spent with no budget and one
-- that was budgeted and spent nothing are both real findings, and an inner join
-- hides exactly those two cases.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW "NOVASPACE_L3"."CV_BUDGET_VARIANCE" AS
WITH "actual" AS (
  SELECT
    j."company_code",
    j."fiscal_year",
    j."reporting_period" AS "fiscal_period",
    j."cost_center",
    j."account_group",
    COALESCE(j."programme_id", '(none)') AS "programme_key",
    SUM(j."signed_amount_group") AS "actual_amount"
  FROM "NOVASPACE_L2"."V_JOURNAL" j
  WHERE j."cost_center" IS NOT NULL
    AND j."fiscal_period" <= 12
  GROUP BY j."company_code", j."fiscal_year", j."reporting_period",
           j."cost_center", j."account_group", COALESCE(j."programme_id", '(none)')
),
"budget" AS (
  SELECT
    b."company_code",
    b."fiscal_year",
    b."fiscal_period",
    b."cost_center",
    b."account_group",
    COALESCE(b."programme_id", '(none)') AS "programme_key",
    SUM(b."amount_period") AS "budget_amount"
  FROM "NOVASPACE_L2"."V_BUDGET_PHASED" b
  GROUP BY b."company_code", b."fiscal_year", b."fiscal_period",
           b."cost_center", b."account_group", COALESCE(b."programme_id", '(none)')
)
SELECT
  COALESCE(a."company_code",   b."company_code")   AS "company_code",
  COALESCE(a."fiscal_year",    b."fiscal_year")    AS "fiscal_year",
  COALESCE(a."fiscal_period",  b."fiscal_period")  AS "fiscal_period",
  COALESCE(a."cost_center",    b."cost_center")    AS "cost_center",
  COALESCE(a."account_group",  b."account_group")  AS "account_group",
  COALESCE(a."programme_key",  b."programme_key")  AS "programme_id",
  COALESCE(a."actual_amount", 0) AS "actual_amount",
  COALESCE(b."budget_amount", 0) AS "budget_amount",
  COALESCE(a."actual_amount", 0) - COALESCE(b."budget_amount", 0) AS "variance",
  -- Undefined, not zero, where there is no budget to vary from. A zero here
  -- would average into a portfolio figure and quietly flatter it.
  CASE
    WHEN COALESCE(b."budget_amount", 0) <> 0
    THEN (COALESCE(a."actual_amount", 0) - b."budget_amount") / ABS(b."budget_amount")
  END AS "variance_pct"
FROM "actual" a
FULL OUTER JOIN "budget" b
  ON  a."company_code"  = b."company_code"
  AND a."fiscal_year"   = b."fiscal_year"
  AND a."fiscal_period" = b."fiscal_period"
  AND a."cost_center"   = b."cost_center"
  AND a."account_group" = b."account_group"
  AND a."programme_key" = b."programme_key";

-- ---------------------------------------------------------------------------
-- CV_CLOSE_MONITOR - KPI-01 and KPI-03 on one grain.
--
-- Joins the close checklist to the postings of the same period, so the
-- dashboard can show that the entity closing late is also the one posting by
-- hand - the mechanism, not just the symptom.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW "NOVASPACE_L3"."CV_CLOSE_MONITOR" AS
WITH "postings" AS (
  SELECT
    j."company_code",
    j."fiscal_year",
    j."reporting_period" AS "fiscal_period",
    COUNT(*) AS "line_count",
    SUM(CASE WHEN j."is_manual_posting" = TRUE THEN 1 ELSE 0 END) AS "manual_line_count",
    SUM(CASE WHEN j."is_late_posting" = TRUE THEN 1 ELSE 0 END) AS "late_line_count",
    SUM(CASE WHEN j."is_late_posting" = TRUE
             THEN ABS(j."amount_group_currency") ELSE 0 END) AS "late_value"
  FROM "NOVASPACE_L2"."V_JOURNAL" j
  GROUP BY j."company_code", j."fiscal_year", j."reporting_period"
)
SELECT
  c."company_code",
  c."fiscal_year",
  c."fiscal_period",
  c."task_id",
  c."task_name",
  c."task_sequence",
  c."is_milestone",
  c."period_end_date",
  c."due_date",
  c."actual_completion_date",
  c."delay_working_days",
  c."is_open",
  c."days_to_close",
  p."line_count",
  p."manual_line_count",
  p."late_line_count",
  p."late_value",
  CASE WHEN p."line_count" > 0
       THEN CAST(p."manual_line_count" AS DECIMAL(18,6)) / p."line_count" END
    AS "manual_share",
  CASE WHEN p."line_count" > 0
       THEN CAST(p."late_line_count" AS DECIMAL(18,6)) / p."line_count" END
    AS "late_share"
FROM "NOVASPACE_L2"."V_CLOSE_TASKS" c
LEFT JOIN "postings" p
       ON  p."company_code"  = c."company_code"
       AND p."fiscal_year"   = c."fiscal_year"
       AND p."fiscal_period" = c."fiscal_period";

-- ---------------------------------------------------------------------------
-- CV_FX_IMPACT - KPI-06.
--
-- Carries gross exposure alongside the net figures. An entity earning and
-- spending in the same currency is largely self-hedged, so FX impact expressed
-- as a share of its thin net margin divides by something near zero. The gross
-- flow is what a rate move actually acts on.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW "NOVASPACE_L3"."CV_FX_IMPACT" AS
SELECT
  j."company_code",
  j."company_name",
  j."local_currency",
  j."fiscal_year",
  j."reporting_period"                       AS "fiscal_period",
  j."account_group",
  -- Booked vs recomputed. They differ only on reversals, which carry the
  -- original document's group amount into a later period - see the note in
  -- L2.V_JOURNAL. fx_impact must be built from the recomputed figure, or the
  -- reversal carry-over is misreported as a rate effect.
  SUM(j."signed_amount_group")               AS "amount_group_booked",
  SUM(j."signed_amount_at_actual_rate")      AS "amount_at_actual_rate",
  SUM(j."signed_amount_at_budget_rate")      AS "amount_at_budget_rate",
  SUM(j."signed_amount_at_actual_rate")
    - SUM(j."signed_amount_at_budget_rate")  AS "fx_impact",
  SUM(j."amount_local_currency" * j."rate_budget") AS "gross_at_budget_rate",
  MIN(j."rate_actual")                       AS "rate_actual",
  MIN(j."rate_budget")                       AS "rate_budget"
FROM "NOVASPACE_L2"."V_JOURNAL" j
GROUP BY
  j."company_code", j."company_name", j."local_currency",
  j."fiscal_year", j."reporting_period", j."account_group";

-- ---------------------------------------------------------------------------
-- CV_IC_RECONCILIATION - KPI-08.
--
-- Keyed on the unordered entity pair. Materiality is applied here rather than
-- left to the report: without a threshold, sub-cent translation rounding makes
-- pairs look broken, and every consumer would have to invent its own tolerance.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW "NOVASPACE_L3"."CV_IC_RECONCILIATION" AS
SELECT
  j."ic_pair",
  j."fiscal_year",
  j."reporting_period"          AS "fiscal_period",
  SUM(j."signed_amount_group")  AS "net_amount",
  COUNT(*)                      AS "line_count",
  CASE WHEN ABS(SUM(j."signed_amount_group")) > 1000
       THEN TRUE ELSE FALSE END AS "is_mismatch"
FROM "NOVASPACE_L2"."V_JOURNAL" j
WHERE j."is_intercompany" = TRUE
GROUP BY j."ic_pair", j."fiscal_year", j."reporting_period";
