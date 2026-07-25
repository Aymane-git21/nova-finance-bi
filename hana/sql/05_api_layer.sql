-- ===========================================================================
-- API - the published service interface
--
-- L3 is the reporting layer; this is the *contract* the service layer binds to.
-- Two reasons it exists rather than pointing CAP straight at L3:
--
--   1. Practical. Every identifier in L1-L3 is quoted lower case, because that
--      is how the source CSVs are shaped and keeping them consistent made the
--      loader and the harmonised layer readable. CAP and CDS emit unquoted
--      identifiers, which HANA folds to upper case, so they cannot see a column
--      called "company_code". This layer aliases them.
--
--   2. Architectural, and the reason it is worth keeping even after the
--      practical problem is solved. A consuming application should bind to a
--      published contract, not to internal modelling. L3 can be refactored -
--      views split, columns renamed, grains changed - and as long as these
--      projections still resolve, no consumer breaks. That is the same job an
--      Open ODS View or a published BW query does in a BW landscape.
--
-- Nothing here contains logic. If a calculation appears in this file, it is in
-- the wrong layer.
-- ===========================================================================

CREATE SCHEMA NOVASPACE_API;

-- ---------------------------------------------------------------------------
-- Budget variance - the Analytical List Page's main entity.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW NOVASPACE_API.V_BUDGET_VARIANCE AS
SELECT
  v."company_code"                                   AS COMPANY_CODE,
  co."company_name"                                  AS COMPANY_NAME,
  v."fiscal_year"                                    AS FISCAL_YEAR,
  v."fiscal_period"                                  AS FISCAL_PERIOD,
  TO_NVARCHAR(v."fiscal_year") || '-'
    || LPAD(TO_NVARCHAR(v."fiscal_period"), 2, '0')  AS FISCAL_PERIOD_LABEL,
  v."cost_center"                                    AS COST_CENTER,
  cc."cost_center_name"                              AS COST_CENTER_NAME,
  cc."division_name"                                 AS DIVISION_NAME,
  v."programme_id"                                   AS PROGRAMME_ID,
  COALESCE(p."programme_name", 'Not programme-related') AS PROGRAMME_NAME,
  v."account_group"                                  AS ACCOUNT_GROUP,
  a."account_group_name"                             AS ACCOUNT_GROUP_NAME,
  CAST(v."actual_amount" AS DECIMAL(18,2))           AS ACTUAL_AMOUNT,
  CAST(v."budget_amount" AS DECIMAL(18,2))           AS BUDGET_AMOUNT,
  CAST(v."variance"      AS DECIMAL(18,2))           AS VARIANCE,
  CAST(v."variance_pct"  AS DECIMAL(12,4))           AS VARIANCE_PCT,
  'EUR'                                              AS CURRENCY,
  -- Criticality for the Fiori annotation: 1 red, 2 amber, 3 green. Computed
  -- here so every consumer shows the same thresholds rather than each
  -- inventing its own.
  CASE
    WHEN v."variance_pct" IS NULL          THEN 0
    WHEN v."variance_pct" >  0.10          THEN 1
    WHEN v."variance_pct" >  0.05          THEN 2
    ELSE 3
  END                                                AS VARIANCE_CRITICALITY
FROM "NOVASPACE_L3"."CV_BUDGET_VARIANCE" v
LEFT JOIN "NOVASPACE_L1"."V_COMPANY_CODE" co ON co."company_code" = v."company_code"
LEFT JOIN "NOVASPACE_L1"."V_COST_CENTER"  cc ON cc."cost_center"  = v."cost_center"
LEFT JOIN "NOVASPACE_L1"."V_PROGRAMME"    p  ON p."programme_id"  = v."programme_id"
LEFT JOIN (
  SELECT DISTINCT "account_group", "account_group_name"
  FROM "NOVASPACE_L1"."V_GL_ACCOUNT"
) a ON a."account_group" = v."account_group";

-- ---------------------------------------------------------------------------
-- Programme burn - the freestyle bubble chart.
--
-- x = share of the planned schedule elapsed, y = share of budget consumed,
-- bubble size = budget. Anything above the diagonal is spending faster than it
-- is progressing, which is the entire point of the chart: one glance, one
-- diagonal, and the programme in trouble is the one above the line.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW NOVASPACE_API.V_PROGRAMME_BURN AS
SELECT
  r."programme_id"                                    AS PROGRAMME_ID,
  r."programme_name"                                  AS PROGRAMME_NAME,
  r."programme_type"                                  AS PROGRAMME_TYPE,
  p."lead_company_code"                               AS LEAD_COMPANY_CODE,
  p."status"                                          AS STATUS,
  p."start_date"                                      AS START_DATE,
  p."end_date"                                        AS END_DATE,
  CAST(r."actuals_to_date"   AS DECIMAL(18,2))        AS ACTUALS_TO_DATE,
  CAST(r."run_rate"          AS DECIMAL(18,2))        AS RUN_RATE,
  r."remaining_periods"                               AS REMAINING_PERIODS,
  CAST(r."eac"               AS DECIMAL(18,2))        AS EAC,
  CAST(p."total_budget_eur"  AS DECIMAL(18,2))        AS TOTAL_BUDGET,
  CAST(r."eac_vs_budget_pct" AS DECIMAL(12,4))        AS EAC_VS_BUDGET_PCT,
  'EUR'                                               AS CURRENCY,
  CAST(r."actuals_to_date" / NULLIF(p."total_budget_eur", 0)
       AS DECIMAL(12,4))                              AS PCT_BUDGET_CONSUMED,
  CAST(
    GREATEST(0, LEAST(1,
      MONTHS_BETWEEN(p."start_date", DATE'2026-06-30')
      / NULLIF(MONTHS_BETWEEN(p."start_date", p."end_date"), 0)
    )) AS DECIMAL(12,4))                              AS PCT_TIME_ELAPSED,
  CASE
    WHEN r."eac_vs_budget_pct" > 1.10 THEN 1
    WHEN r."eac_vs_budget_pct" > 1.00 THEN 2
    ELSE 3
  END                                                 AS EAC_CRITICALITY
FROM "NOVASPACE_L3"."TF_PROGRAMME_RUNRATE"(2026, 6, 3) r
INNER JOIN "NOVASPACE_L1"."V_PROGRAMME" p ON p."programme_id" = r."programme_id";

-- ---------------------------------------------------------------------------
-- Close monitor - the KPI header tiles and the close-timeline page.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW NOVASPACE_API.V_CLOSE_MONITOR AS
SELECT
  m."company_code"                                    AS COMPANY_CODE,
  co."company_name"                                   AS COMPANY_NAME,
  m."fiscal_year"                                     AS FISCAL_YEAR,
  m."fiscal_period"                                   AS FISCAL_PERIOD,
  TO_NVARCHAR(m."fiscal_year") || '-'
    || LPAD(TO_NVARCHAR(m."fiscal_period"), 2, '0')   AS FISCAL_PERIOD_LABEL,
  m."task_id"                                         AS TASK_ID,
  m."task_name"                                       AS TASK_NAME,
  m."task_sequence"                                   AS TASK_SEQUENCE,
  m."is_milestone"                                    AS IS_MILESTONE,
  m."period_end_date"                                 AS PERIOD_END_DATE,
  m."due_date"                                        AS DUE_DATE,
  m."actual_completion_date"                          AS ACTUAL_COMPLETION_DATE,
  m."delay_working_days"                              AS DELAY_WORKING_DAYS,
  m."is_open"                                         AS IS_OPEN,
  m."days_to_close"                                   AS DAYS_TO_CLOSE,
  m."line_count"                                      AS LINE_COUNT,
  m."manual_line_count"                               AS MANUAL_LINE_COUNT,
  m."late_line_count"                                 AS LATE_LINE_COUNT,
  CAST(m."late_value"   AS DECIMAL(18,2))             AS LATE_VALUE,
  CAST(m."manual_share" AS DECIMAL(12,4))             AS MANUAL_SHARE,
  CAST(m."late_share"   AS DECIMAL(12,4))             AS LATE_SHARE,
  -- Target is working day 5. An open period is not "on time" and not "late":
  -- it is unknown, and gets its own value rather than being folded into either.
  CASE
    WHEN m."days_to_close" IS NULL THEN 0
    WHEN m."days_to_close" > 7     THEN 1
    WHEN m."days_to_close" > 5     THEN 2
    ELSE 3
  END                                                 AS CLOSE_CRITICALITY
FROM "NOVASPACE_L3"."CV_CLOSE_MONITOR" m
LEFT JOIN "NOVASPACE_L1"."V_COMPANY_CODE" co ON co."company_code" = m."company_code";

-- ---------------------------------------------------------------------------
-- P&L actuals - the trend and the account-group breakdown.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW NOVASPACE_API.V_PL_ACTUALS AS
SELECT
  "company_code"                                      AS COMPANY_CODE,
  "company_name"                                      AS COMPANY_NAME,
  "fiscal_year"                                       AS FISCAL_YEAR,
  "fiscal_period"                                     AS FISCAL_PERIOD,
  TO_NVARCHAR("fiscal_year") || '-'
    || LPAD(TO_NVARCHAR("fiscal_period"), 2, '0')     AS FISCAL_PERIOD_LABEL,
  "pl_section"                                        AS PL_SECTION,
  "account_group"                                     AS ACCOUNT_GROUP,
  "account_group_name"                                AS ACCOUNT_GROUP_NAME,
  CAST("amount_group_currency" AS DECIMAL(18,2))      AS AMOUNT,
  CAST("amount_manual"         AS DECIMAL(18,2))      AS AMOUNT_MANUAL,
  "line_count"                                        AS LINE_COUNT,
  "line_count_manual"                                 AS LINE_COUNT_MANUAL,
  "line_count_late"                                   AS LINE_COUNT_LATE,
  'EUR'                                               AS CURRENCY
FROM "NOVASPACE_L3"."CV_PL_ACTUALS";

-- ---------------------------------------------------------------------------
-- Intercompany reconciliation - the open items the close team chases.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW NOVASPACE_API.V_IC_RECONCILIATION AS
SELECT
  "ic_pair"                                           AS IC_PAIR,
  "fiscal_year"                                       AS FISCAL_YEAR,
  "fiscal_period"                                     AS FISCAL_PERIOD,
  CAST("net_amount" AS DECIMAL(18,2))                 AS NET_AMOUNT,
  "line_count"                                        AS LINE_COUNT,
  "is_mismatch"                                       AS IS_MISMATCH,
  'EUR'                                               AS CURRENCY
FROM "NOVASPACE_L3"."CV_IC_RECONCILIATION";
