-- ===========================================================================
-- Optimisation 1: materialise the monthly aggregate
--
-- Every reporting query re-aggregates 1,122,588 journal lines on every
-- execution. No report asks a question at line-item grain: the dashboard, the
-- variance analysis and the FX bridge all group to entity x period x account
-- group x programme x cost centre. That grain is 172k rows, not 1.1M.
--
-- So the line-item scan is repeated work, done per query, per user, per day,
-- to produce a result that changes once per load.
--
-- The trade is storage and freshness for compute. It is worth recording that
-- this is exactly the BW conversation about persisting a standard ADSO versus
-- leaving a CompositeProvider virtual - the same decision with different
-- vocabulary, and the same answer: virtual until the read volume justifies
-- persisting, then persist and accept a refresh cycle.
--
-- Freshness cost: the aggregate is as old as its last refresh. For a close
-- cockpit read all day against data loaded overnight, that is acceptable and
-- must be stated on the report. For intraday close monitoring it would not be,
-- which is why the line-item views are kept rather than replaced.
-- ===========================================================================

CREATE COLUMN TABLE "NOVASPACE_L3"."AGG_JOURNAL_MONTHLY" (
  "company_code"                NVARCHAR(4)   NOT NULL,
  "fiscal_year"                 INTEGER       NOT NULL,
  "fiscal_period"               INTEGER       NOT NULL,
  "account_group"               NVARCHAR(3)   NOT NULL,
  "pl_section"                  NVARCHAR(20)  NOT NULL,
  "programme_id"                NVARCHAR(12),
  "cost_center"                 NVARCHAR(10),

  -- Kept in the grain, not collapsed. fiscal_period here is the REPORTING
  -- period, so periods 13-16 land on 12 - and a consumer that must exclude
  -- year-end adjustments can no longer tell them apart.
  --
  -- Caught by the cross-check, not by review: budget variance excludes special
  -- periods (they carry no budget), and after the first version of this table
  -- it silently started including them in period 12.
  --
  -- The general rule: an aggregate must preserve every distinction its
  -- consumers filter on. Collapsing one is not a loss of detail, it is a
  -- change of answer.
  "is_special_period"           BOOLEAN       NOT NULL,
  "local_currency"              NVARCHAR(3)   NOT NULL,

  "signed_amount_group"         DECIMAL(18,2) NOT NULL,

  -- These three are amounts multiplied by a six-decimal exchange rate, so the
  -- products carry up to eight decimals. Stored at DECIMAL(18,2) they round at
  -- the aggregate grain, and 138,045 intermediate roundings do not cancel.
  --
  -- Caught by hana/verify_against_python.py, not by inspection: after the first
  -- version of this table, FX impact disagreed with the Python reference by
  -- EUR 1.20 on a EUR 650m base. Immaterial as a number and disqualifying as a
  -- principle - an optimisation that changes the answer is a defect, and the
  -- only reason to know is that something independent recomputes it.
  --
  -- The general rule: a materialised aggregate must preserve the precision of
  -- the measures it aggregates. Round at the point of presentation, never at
  -- an intermediate grain nobody reads.
  "signed_amount_at_actual"     DECIMAL(28,6) NOT NULL,
  "signed_amount_at_budget"     DECIMAL(28,6) NOT NULL,
  "gross_amount_at_budget"      DECIMAL(28,6) NOT NULL,

  "amount_manual"               DECIMAL(18,2) NOT NULL,

  "line_count"                  INTEGER       NOT NULL,
  "line_count_manual"           INTEGER       NOT NULL,
  "line_count_late"             INTEGER       NOT NULL,
  "line_count_special_period"   INTEGER       NOT NULL
);

-- Refresh is a full rebuild rather than a delta. At this volume it takes a few
-- seconds and a full rebuild cannot drift; a delta can, and a silently drifted
-- aggregate is worse than no aggregate. A production version at 100x the
-- volume would need a delta and would need reconciliation to go with it.
TRUNCATE TABLE "NOVASPACE_L3"."AGG_JOURNAL_MONTHLY";

INSERT INTO "NOVASPACE_L3"."AGG_JOURNAL_MONTHLY"
SELECT
  j."company_code",
  j."fiscal_year",
  j."reporting_period",
  j."account_group",
  j."pl_section",
  j."programme_id",
  j."cost_center",
  CASE WHEN j."fiscal_period" > 12 THEN TRUE ELSE FALSE END,
  j."local_currency",

  SUM(j."signed_amount_group"),
  SUM(j."signed_amount_at_actual_rate"),
  SUM(j."signed_amount_at_budget_rate"),
  SUM(j."amount_local_currency" * j."rate_budget"),
  SUM(CASE WHEN j."is_manual_posting" = TRUE
           THEN j."signed_amount_group" ELSE 0 END),

  COUNT(*),
  SUM(CASE WHEN j."is_manual_posting" = TRUE THEN 1 ELSE 0 END),
  SUM(CASE WHEN j."is_late_posting"   = TRUE THEN 1 ELSE 0 END),
  SUM(CASE WHEN j."fiscal_period" > 12 THEN 1 ELSE 0 END)
FROM "NOVASPACE_L2"."V_JOURNAL" j
GROUP BY
  j."company_code", j."fiscal_year", j."reporting_period",
  j."account_group", j."pl_section", j."programme_id", j."cost_center",
  CASE WHEN j."fiscal_period" > 12 THEN TRUE ELSE FALSE END,
  j."local_currency";

-- --------------------------------------------------------------------------
-- Repoint the reporting views at the aggregate.
--
-- The view names do not change, so nothing downstream knows this happened -
-- not the API layer, not CAP, not the dashboard. That is the payoff of having
-- a published interface: an optimisation this invasive is invisible to every
-- consumer. Without that boundary it would be a breaking change.
-- --------------------------------------------------------------------------

CREATE OR REPLACE VIEW "NOVASPACE_L3"."CV_PL_ACTUALS" AS
SELECT
  a."company_code",
  co."company_name",
  a."fiscal_year",
  a."fiscal_period",
  a."pl_section",
  a."account_group",
  g."account_group_name",
  SUM(a."signed_amount_group")       AS "amount_group_currency",
  SUM(a."line_count")                AS "line_count",
  SUM(a."amount_manual")             AS "amount_manual",
  SUM(a."line_count_manual")         AS "line_count_manual",
  SUM(a."line_count_late")           AS "line_count_late",
  SUM(a."line_count_special_period") AS "line_count_year_end_adjustment"
FROM "NOVASPACE_L3"."AGG_JOURNAL_MONTHLY" a
INNER JOIN "NOVASPACE_L1"."V_COMPANY_CODE" co ON co."company_code" = a."company_code"
LEFT  JOIN (
  SELECT DISTINCT "account_group", "account_group_name"
  FROM "NOVASPACE_L1"."V_GL_ACCOUNT"
) g ON g."account_group" = a."account_group"
GROUP BY
  a."company_code", co."company_name", a."fiscal_year", a."fiscal_period",
  a."pl_section", a."account_group", g."account_group_name";

CREATE OR REPLACE VIEW "NOVASPACE_L3"."CV_FX_IMPACT" AS
SELECT
  a."company_code",
  co."company_name",
  a."local_currency",
  a."fiscal_year",
  a."fiscal_period",
  a."account_group",
  SUM(a."signed_amount_group")     AS "amount_group_booked",
  SUM(a."signed_amount_at_actual") AS "amount_at_actual_rate",
  SUM(a."signed_amount_at_budget") AS "amount_at_budget_rate",
  SUM(a."signed_amount_at_actual")
    - SUM(a."signed_amount_at_budget") AS "fx_impact",
  SUM(a."gross_amount_at_budget")  AS "gross_at_budget_rate"
FROM "NOVASPACE_L3"."AGG_JOURNAL_MONTHLY" a
INNER JOIN "NOVASPACE_L1"."V_COMPANY_CODE" co ON co."company_code" = a."company_code"
GROUP BY
  a."company_code", co."company_name", a."local_currency",
  a."fiscal_year", a."fiscal_period", a."account_group";
