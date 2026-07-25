-- ===========================================================================
-- Optimisation 4: serve budget variance from the aggregate
--
-- Optimisation 3 (pruning the joins the variance query never uses) was
-- measured and made the target query ~15% SLOWER, consistently, across three
-- runs against a measured noise band of +/-8%. It is reverted, and the result
-- is reported rather than quietly dropped - see docs/performance-report.md.
--
-- The reason it failed is the useful part. HANA's optimiser was already
-- pruning the unreferenced columns; the joins that remained were to small
-- dimension tables it resolves as dictionary lookups. Replacing a well-planned
-- view with a hand-narrowed one removed nothing real and cost a join order the
-- optimiser had got right on its own.
--
-- The measurement said the win was elsewhere: the aggregate built in
-- optimisation 1 already holds every column budget variance needs, at 138,045
-- rows instead of 1,122,588. The actual side should read it.
--
-- The lesson is the one that keeps repeating in this phase: optimise where the
-- measurement points, not where intuition does. Two of the three optimisations
-- planned up front were wrong, and only measuring found that out.
-- ===========================================================================

CREATE OR REPLACE VIEW "NOVASPACE_L3"."CV_BUDGET_VARIANCE" AS
WITH "actual" AS (
  SELECT
    a."company_code",
    a."fiscal_year",
    a."fiscal_period",
    a."cost_center",
    a."account_group",
    COALESCE(a."programme_id", '(none)') AS "programme_key",
    SUM(a."signed_amount_group") AS "actual_amount"
  FROM "NOVASPACE_L3"."AGG_JOURNAL_MONTHLY" a
  -- Revenue carries no cost centre and no cost-centre budget. Special periods
  -- carry no budget and are excluded rather than folded into period 12.
  WHERE a."cost_center" IS NOT NULL
    AND a."is_special_period" = FALSE
  GROUP BY a."company_code", a."fiscal_year", a."fiscal_period",
           a."cost_center", a."account_group", COALESCE(a."programme_id", '(none)')
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

-- The lean projection from optimisation 3 is dropped. It measured worse and
-- kept nothing alive.
DROP VIEW "NOVASPACE_L2"."V_JOURNAL_COSTS";
