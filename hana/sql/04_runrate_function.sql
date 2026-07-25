-- ===========================================================================
-- TF_PROGRAMME_RUNRATE - KPI-05, rolling run-rate and a naive EAC.
--
-- This is the most technically interesting object in the project and the
-- reason Phase 4 survives having no ABAP system at all.
--
-- An AMDP is an ABAP class method whose body is SQLScript, pushed down and
-- executed by HANA. The ABAP layer is the wrapper; HANA does the work. So this
-- body - the window function, the ranking, the aggregation - is the part that
-- actually computes, and it runs and is benchmarked here for real.
-- ZCL_AMDP_RUNRATE in ../../abap/ wraps this identical SQLScript and is
-- labelled NOT ACTIVATED, because it is. See ../../docs/adr/003-abap-evidence-strategy.md.
--
-- It must reproduce novaspace/harmonise.py::programme_run_rate exactly. The
-- Python has a test suite behind it; any disagreement is a defect here.
--
-- The EAC is deliberately naive: actuals to date plus run-rate times the
-- periods remaining before the planned end. It ignores the remaining work
-- profile, commitments and ramp-down, so it is an early-warning indicator and
-- not a forecast. Programmes past their end date get no extrapolation at all.
-- ===========================================================================

CREATE OR REPLACE FUNCTION "NOVASPACE_L3"."TF_PROGRAMME_RUNRATE" (
  IN in_fiscal_year   INTEGER,
  IN in_fiscal_period INTEGER,
  IN in_window        INTEGER
)
RETURNS TABLE (
  "programme_id"        NVARCHAR(12),
  "programme_name"      NVARCHAR(80),
  "programme_type"      NVARCHAR(20),
  "as_of_fiscal_year"   INTEGER,
  "as_of_fiscal_period" INTEGER,
  "actuals_to_date"     DECIMAL(18,2),
  "run_rate"            DECIMAL(18,2),
  "remaining_periods"   INTEGER,
  "eac"                 DECIMAL(18,2),
  "total_budget_eur"    DECIMAL(15,2),
  "eac_vs_budget_pct"   DECIMAL(12,4)
)
LANGUAGE SQLSCRIPT
READS SQL DATA AS
BEGIN
  DECLARE lv_as_of INTEGER := :in_fiscal_year * 100 + :in_fiscal_period;

  -- Programme cost per period, up to the as-of point. Special periods are
  -- excluded: a year-end adjustment is not part of a monthly burn rate and
  -- including it would spike the run-rate every December.
  lt_monthly =
    SELECT
      j."programme_id",
      j."fiscal_year" * 100 + j."fiscal_period" AS "period_key",
      SUM(j."signed_amount_group")              AS "period_cost"
    FROM "NOVASPACE_L2"."V_JOURNAL" j
    WHERE j."programme_id" IS NOT NULL
      AND j."fiscal_period" <= 12
      AND j."fiscal_year" * 100 + j."fiscal_period" <= :lv_as_of
    GROUP BY j."programme_id", j."fiscal_year" * 100 + j."fiscal_period";

  -- The window function that makes this worth pushing down: rank each
  -- programme's periods by recency so the rolling window is a filter on a rank
  -- rather than a correlated subquery per programme.
  lt_ranked =
    SELECT
      m."programme_id",
      m."period_key",
      m."period_cost",
      ROW_NUMBER() OVER (
        PARTITION BY m."programme_id" ORDER BY m."period_key" DESC
      ) AS "recency"
    FROM :lt_monthly m;

  lt_run_rate =
    SELECT
      r."programme_id",
      AVG(r."period_cost") AS "run_rate"
    FROM :lt_ranked r
    WHERE r."recency" <= :in_window
    GROUP BY r."programme_id";

  lt_to_date =
    SELECT
      m."programme_id",
      SUM(m."period_cost") AS "actuals_to_date"
    FROM :lt_monthly m
    GROUP BY m."programme_id";

  RETURN
    SELECT
      p."programme_id",
      p."programme_name",
      p."programme_type",
      :in_fiscal_year   AS "as_of_fiscal_year",
      :in_fiscal_period AS "as_of_fiscal_period",
      CAST(d."actuals_to_date" AS DECIMAL(18,2)) AS "actuals_to_date",
      CAST(rr."run_rate"       AS DECIMAL(18,2)) AS "run_rate",
      CAST(GREATEST(
        0,
        (YEAR(p."end_date")  - :in_fiscal_year) * 12
        + (MONTH(p."end_date") - :in_fiscal_period)
      ) AS INTEGER) AS "remaining_periods",
      CAST(
        d."actuals_to_date"
        + rr."run_rate" * GREATEST(
            0,
            (YEAR(p."end_date")  - :in_fiscal_year) * 12
            + (MONTH(p."end_date") - :in_fiscal_period)
          )
        AS DECIMAL(18,2)
      ) AS "eac",
      p."total_budget_eur",
      CAST(
        (
          d."actuals_to_date"
          + rr."run_rate" * GREATEST(
              0,
              (YEAR(p."end_date")  - :in_fiscal_year) * 12
              + (MONTH(p."end_date") - :in_fiscal_period)
            )
        ) / NULLIF(p."total_budget_eur", 0)
        AS DECIMAL(12,4)
      ) AS "eac_vs_budget_pct"
    FROM "NOVASPACE_L1"."V_PROGRAMME" p
    INNER JOIN :lt_to_date  d  ON d."programme_id"  = p."programme_id"
    INNER JOIN :lt_run_rate rr ON rr."programme_id" = p."programme_id";
END;
