-- ===========================================================================
-- L2 - HARMONISED / propagation layer
--
-- BW/4HANA analogue: standard ADSO with transformations.
--
-- This is where business logic lives, and it is the SQL counterpart of
-- data-generator/novaspace/harmonise.py. The two must agree: the Python is the
-- reference implementation with a test suite behind it, and any divergence here
-- is a defect in this file, not a difference of opinion.
--
-- What L2 adds:
--   * signed amounts from the debit/credit indicator
--   * the manual-posting and late-posting flags
--   * currency translation at both the actual and the frozen budget rate
--   * master-data attributes joined on
--   * working-day arithmetic for the close
-- ===========================================================================

CREATE SCHEMA "NOVASPACE_L2";

-- ---------------------------------------------------------------------------
-- Working-day sequence.
--
-- A running count of working days across the whole calendar. With it, "working
-- days between two dates" becomes one subtraction instead of a correlated
-- count over DIM_DATE per row - the difference between a view that returns and
-- one that does not.
--
-- seq(to) - seq(from) counts working days in the half-open interval (from, to],
-- which is exactly the definition KPI-01 and KPI-03 use: a task completed on
-- the period-end date itself took zero working days.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW "NOVASPACE_L2"."V_DATE" AS
SELECT
  d."date_id",
  d."calendar_year",
  d."calendar_quarter",
  d."calendar_month",
  d."day_of_week",
  d."day_name",
  d."is_weekend",
  d."is_working_day",
  d."fiscal_year",
  d."fiscal_period",
  d."period_end_date",
  d."working_day_of_period",
  d."working_days_after_period_end",
  -- "= TRUE" is not redundant: HANA will not accept a bare BOOLEAN column as a
  -- CASE predicate and rejects it with a syntax error pointing at THEN.
  SUM(CASE WHEN d."is_working_day" = TRUE THEN 1 ELSE 0 END)
    OVER (ORDER BY d."date_id" ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
    AS "working_day_seq"
FROM "NOVASPACE_L1"."V_DATE" d;

-- ---------------------------------------------------------------------------
-- FX rates, actual and budget side by side.
--
-- KPI-06 is the difference between these two columns. Held as separate rows in
-- the source, they would have to be self-joined at every point of use.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW "NOVASPACE_L2"."V_FX_RATE_PAIR" AS
SELECT
  r."from_currency",
  r."to_currency",
  r."fiscal_year",
  r."fiscal_period",
  MAX(CASE WHEN r."rate_type" = 'M' THEN r."exchange_rate" END) AS "rate_actual",
  MAX(CASE WHEN r."rate_type" = 'B' THEN r."exchange_rate" END) AS "rate_budget"
FROM "NOVASPACE_L1"."V_RATES" r
GROUP BY r."from_currency", r."to_currency", r."fiscal_year", r."fiscal_period";

-- ---------------------------------------------------------------------------
-- Close tasks, with days-to-close on the hard-close milestone.
--
-- days_to_close is NULL where the task has not completed. An open period is
-- open; rendering it as a zero-day close would be the single most misleading
-- number this model could produce, so the NULL is deliberate and must survive
-- all the way to the story.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW "NOVASPACE_L2"."V_CLOSE_TASKS" AS
SELECT
  c."close_task_id",
  c."company_code",
  c."fiscal_year",
  c."fiscal_period",
  c."task_id",
  t."task_name",
  t."task_sequence",
  t."target_working_day",
  t."is_milestone",
  c."period_end_date",
  c."due_date",
  c."actual_completion_date",
  c."completed_by_user_id",
  c."delay_working_days",
  CASE WHEN c."actual_completion_date" IS NULL THEN TRUE ELSE FALSE END AS "is_open",
  CASE
    WHEN c."task_id" = 'T12' AND c."actual_completion_date" IS NOT NULL
    THEN da."working_day_seq" - dp."working_day_seq"
  END AS "days_to_close"
FROM "NOVASPACE_L1"."V_CLOSE_TASKS" c
INNER JOIN "NOVASPACE_L1"."V_CLOSE_TASK" t
        ON t."task_id" = c."task_id"
LEFT  JOIN "NOVASPACE_L2"."V_DATE" dp
        ON dp."date_id" = c."period_end_date"
LEFT  JOIN "NOVASPACE_L2"."V_DATE" da
        ON da."date_id" = c."actual_completion_date";

-- ---------------------------------------------------------------------------
-- The harmonised journal. Everything downstream reads this, not L1.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW "NOVASPACE_L2"."V_JOURNAL" AS
SELECT
  j."journal_id",
  j."company_code",
  co."company_name",
  co."country_key",
  j."document_number",
  j."document_line",
  j."document_type",
  j."posting_date",
  j."document_date",
  j."entry_date",
  j."fiscal_year",
  j."fiscal_period",
  -- Special periods 13-16 have no calendar month of their own. Clamping to 12
  -- gives them the rate and the close cycle of the period they adjust, which is
  -- how a year-end adjustment is actually translated and reported.
  LEAST(j."fiscal_period", 12) AS "reporting_period",
  j."gl_account",
  a."gl_account_name",
  a."account_group",
  a."account_group_name",
  a."pl_section",
  j."cost_center",
  cc."cost_center_name",
  cc."division_id",
  cc."division_name",
  cc."department_id",
  cc."department_name",
  cc."is_overhead",
  j."programme_id",
  p."programme_name",
  p."programme_type",
  j."debit_credit_ind",
  j."doc_currency",
  j."amount_doc_currency",
  j."local_currency",
  j."amount_local_currency",
  j."group_currency",
  j."amount_group_currency",

  -- Expenses positive, revenue negative. Applied once, here.
  CASE WHEN j."debit_credit_ind" = 'S'
       THEN j."amount_group_currency" ELSE -j."amount_group_currency" END
    AS "signed_amount_group",
  CASE WHEN j."debit_credit_ind" = 'S'
       THEN j."amount_local_currency" ELSE -j."amount_local_currency" END
    AS "signed_amount_local",

  -- The same local amount translated twice: once at the period's actual rate,
  -- once at the fiscal year's frozen budget rate. KPI-06 is the difference.
  --
  -- The actual-rate figure is RECOMPUTED from the local amount rather than
  -- taken from the booked group amount, and the distinction is not academic.
  -- A reversal carries the original document's group amount into the next
  -- period (FB08 behaviour), so for reversals the booked figure reflects the
  -- *previous* period's rate. Differencing that against a budget-rate figure
  -- would attribute the reversal's rate carry-over to FX impact - worth about
  -- EUR 6,900 on this dataset, all of it spurious.
  --
  -- Both are exposed: signed_amount_group is what the ledger says, and
  -- signed_amount_at_actual_rate is what a pure rate comparison needs.
  CASE WHEN j."debit_credit_ind" = 'S'
       THEN j."amount_local_currency" ELSE -j."amount_local_currency" END
    * fx."rate_actual"
    AS "signed_amount_at_actual_rate",
  CASE WHEN j."debit_credit_ind" = 'S'
       THEN j."amount_local_currency" ELSE -j."amount_local_currency" END
    * fx."rate_budget"
    AS "signed_amount_at_budget_rate",
  fx."rate_actual",
  fx."rate_budget",

  CASE WHEN j."document_type" IN ('SA', 'SB') THEN TRUE ELSE FALSE END
    AS "is_manual_posting",

  -- Late against the date the cut-off was DUE, never the date it was achieved.
  -- Measured against the achieved cut-off the KPI is self-cancelling: an entity
  -- that runs late also gains the extra days for postings to arrive in, so the
  -- slowest closer scores cleanest. Special periods are excluded - a year-end
  -- adjustment is not a late period-12 posting.
  CASE
    WHEN j."fiscal_period" <= 12 AND j."entry_date" > sc."due_date" THEN TRUE
    ELSE FALSE
  END AS "is_late_posting",

  j."is_intercompany",
  j."ic_partner_company",
  -- Unordered pair key: "who is out" is meaningless without "with whom", and
  -- keying it ordered would count one open item twice.
  CASE
    WHEN j."is_intercompany" = TRUE AND j."company_code" < j."ic_partner_company"
      THEN j."company_code" || '|' || j."ic_partner_company"
    WHEN j."is_intercompany" = TRUE
      THEN j."ic_partner_company" || '|' || j."company_code"
  END AS "ic_pair",

  j."posting_user_id",
  j."is_reversal",
  j."reversed_document"
FROM "NOVASPACE_L1"."V_JOURNAL" j
INNER JOIN "NOVASPACE_L1"."V_COMPANY_CODE" co
        ON co."company_code" = j."company_code"
INNER JOIN "NOVASPACE_L1"."V_GL_ACCOUNT" a
        ON a."gl_account" = j."gl_account"
LEFT  JOIN "NOVASPACE_L1"."V_COST_CENTER" cc
        ON cc."cost_center" = j."cost_center"
LEFT  JOIN "NOVASPACE_L1"."V_PROGRAMME" p
        ON p."programme_id" = j."programme_id"
LEFT  JOIN "NOVASPACE_L2"."V_FX_RATE_PAIR" fx
        ON fx."from_currency" = j."local_currency"
       AND fx."to_currency"   = j."group_currency"
       AND fx."fiscal_year"   = j."fiscal_year"
       AND fx."fiscal_period" = LEAST(j."fiscal_period", 12)
LEFT  JOIN "NOVASPACE_L1"."V_CLOSE_TASKS" sc
        ON sc."company_code"  = j."company_code"
       AND sc."fiscal_year"   = j."fiscal_year"
       AND sc."fiscal_period" = LEAST(j."fiscal_period", 12)
       AND sc."task_id"       = 'T10';

-- ---------------------------------------------------------------------------
-- Budget, phased.
--
-- Budget is annual and actuals are periodic, so a phasing rule is unavoidable.
-- NovaSpace phases evenly across twelve periods. Applying it once here means
-- every consumer works off the same rule instead of each reinventing it.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW "NOVASPACE_L2"."V_BUDGET_PHASED" AS
SELECT
  b."company_code",
  b."fiscal_year",
  p."fiscal_period",
  b."cost_center",
  cc."division_id",
  b."account_group",
  b."programme_id",
  b."version",
  b."amount_group_currency"        AS "amount_annual",
  b."amount_group_currency" / 12   AS "amount_period"
FROM "NOVASPACE_L1"."V_BUDGET" b
LEFT JOIN "NOVASPACE_L1"."V_COST_CENTER" cc
       ON cc."cost_center" = b."cost_center"
CROSS JOIN (
  SELECT 1 AS "fiscal_period" FROM DUMMY UNION ALL SELECT 2  FROM DUMMY
  UNION ALL SELECT 3  FROM DUMMY UNION ALL SELECT 4  FROM DUMMY
  UNION ALL SELECT 5  FROM DUMMY UNION ALL SELECT 6  FROM DUMMY
  UNION ALL SELECT 7  FROM DUMMY UNION ALL SELECT 8  FROM DUMMY
  UNION ALL SELECT 9  FROM DUMMY UNION ALL SELECT 10 FROM DUMMY
  UNION ALL SELECT 11 FROM DUMMY UNION ALL SELECT 12 FROM DUMMY
) p;
