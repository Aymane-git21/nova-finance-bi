-- ===========================================================================
-- Optimisation 3: prune the columns and joins the variance query never uses
--
-- CV_BUDGET_VARIANCE reads L2.V_JOURNAL, which is the fully harmonised view:
-- six joins (company code, G/L account, cost centre, programme, FX rate pair,
-- close task) and roughly forty columns, including the late-posting flag, all
-- three currency amounts, both rate types and every master-data description.
--
-- The variance query needs seven of those columns and one of the joins.
--
-- HANA's optimiser prunes unreferenced *columns* through a view well. It is far
-- more conservative about eliminating *joins*, because it must prove the join
-- cannot change row multiplicity - and with a LEFT JOIN to a table it cannot
-- prove is unique on the join key, it keeps the join. The close-task join in
-- particular exists only to compute is_late_posting, which this query never
-- reads, and it is carried on every one of 1.12M rows regardless.
--
-- So this is not "the optimiser will handle it". A lean projection states what
-- is needed, and the join that only served an unused column disappears.
--
-- The general rule: a fully harmonised view is the right thing to build and
-- the wrong thing to make everything read. Offer a narrow one alongside it.
-- ===========================================================================

CREATE OR REPLACE VIEW "NOVASPACE_L2"."V_JOURNAL_COSTS" AS
SELECT
  j."company_code",
  j."fiscal_year",
  LEAST(j."fiscal_period", 12)                AS "reporting_period",
  j."fiscal_period",
  j."cost_center",
  j."programme_id",
  a."account_group",
  CASE WHEN j."debit_credit_ind" = 'S'
       THEN j."amount_group_currency" ELSE -j."amount_group_currency" END
                                              AS "signed_amount_group",
  j."group_currency"
FROM "NOVASPACE_L1"."V_JOURNAL" j
-- The only join that survives. The account group is a genuine requirement -
-- budget is set at that grain - and DIM_GL_ACCOUNT is 150 rows, so the cost is
-- a dictionary lookup rather than a scan.
INNER JOIN "NOVASPACE_L1"."V_GL_ACCOUNT" a
        ON a."gl_account" = j."gl_account";

-- --------------------------------------------------------------------------
-- Repoint the variance view's actual side at the lean projection.
--
-- The view's own signature is unchanged, so the API layer, CAP, the dashboard
-- and the cross-check all carry on unaware - the same property that made
-- optimisation 1 safe.
-- --------------------------------------------------------------------------
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
  FROM "NOVASPACE_L2"."V_JOURNAL_COSTS" j
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
