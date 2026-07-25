"! ===========================================================================
"! NOT ACTIVATED - no ABAP system was available.
"! See docs/adr/003-abap-evidence-strategy.md
"! ===========================================================================
"! <p class="shorttext synchronized">Programme run-rate and EAC (AMDP)</p>
"!
"! ABAP-Managed Database Procedure implementing {@link ZI_ProgrammeRunRate}.
"!
"! The method body below is SQLScript. It is not executed by the ABAP server:
"! it is pushed down and run by HANA, which is the entire point of code
"! pushdown - compute where the data lives instead of dragging a million rows
"! into an application server to loop over them.
"!
"! That is also why this class being unactivated costs less than it appears.
"! The body is byte-for-byte the logic deployed as
"! NOVASPACE_L3.TF_PROGRAMME_RUNRATE in hana/sql/04_runrate_function.sql,
"! where it runs against 1,122,588 journal lines and is verified against an
"! independent Python implementation to within EUR 0.28 on an EUR 800m EAC
"! (hana/verify_against_python.py). The computation is proven. The ABAP
"! wrapper is source only, and is labelled as such.
"!
"! <h2>The EAC is deliberately naive</h2>
"! Actuals to date plus run-rate times the periods remaining before the
"! planned end. It ignores the remaining work profile, commitments and
"! ramp-down, so it is an early-warning indicator and not a forecast. A
"! programme past its end date gets no extrapolation at all. Presenting it as
"! a forecast would be the dishonest part, not the arithmetic.
CLASS zcl_amdp_runrate DEFINITION
  PUBLIC
  FINAL
  CREATE PUBLIC.

  PUBLIC SECTION.

    "! Marker interface. Without it the compiler will not accept a method
    "! implemented BY DATABASE FUNCTION FOR HDB.
    INTERFACES if_amdp_marker_hdb.

    "! Rolling run-rate and estimate at completion, per programme.
    CLASS-METHODS get_run_rate
      FOR TABLE FUNCTION zi_programmerunrate.

ENDCLASS.


CLASS zcl_amdp_runrate IMPLEMENTATION.

  METHOD get_run_rate
        BY DATABASE FUNCTION FOR HDB
        LANGUAGE SQLSCRIPT
        OPTIONS READ-ONLY
        USING ztns_journal ztns_programme.

    -- As-of point as a sortable integer. Comparing (year, period) pairs
    -- directly needs two predicates and gets the December/January boundary
    -- wrong often enough to be worth avoiding.
    DECLARE lv_as_of INTEGER := :p_fiscal_year * 100 + :p_fiscal_period;

    -- Programme cost per period, up to the as-of point.
    --
    -- Special periods (13-16) are excluded: a year-end adjustment is not part
    -- of a monthly burn rate, and including it would spike the run-rate every
    -- December for reasons that have nothing to do with how fast a programme
    -- is spending.
    --
    -- The sign convention is applied here rather than read from an interface
    -- view, because an AMDP reads database tables, not CDS view entities. It
    -- is the same rule ZI_JournalEntry applies: debit positive, credit
    -- negative, so expenses come out positive and revenue negative.
    lt_monthly =
      SELECT
        programme_id,
        fiscal_year * 100 + fiscal_period AS period_key,
        SUM( CASE debit_credit_ind
                  WHEN 'S' THEN amount_group_currency
                  ELSE          amount_group_currency * -1
             END ) AS period_cost
      FROM ztns_journal
      WHERE client        = :p_client
        AND programme_id IS NOT NULL
        AND programme_id <> ''
        AND fiscal_period <= 12
        AND fiscal_year * 100 + fiscal_period <= :lv_as_of
      GROUP BY programme_id, fiscal_year * 100 + fiscal_period;

    -- The window function this whole object exists to demonstrate. Ranking
    -- each programme's periods by recency turns "the last N periods" into a
    -- filter on a rank. The alternative is a correlated subquery per
    -- programme, which is the pattern that makes people believe HANA is slow.
    lt_ranked =
      SELECT
        programme_id,
        period_key,
        period_cost,
        ROW_NUMBER( ) OVER ( PARTITION BY programme_id
                             ORDER BY period_key DESC ) AS recency
      FROM :lt_monthly;

    lt_run_rate =
      SELECT programme_id,
             AVG( period_cost ) AS run_rate
      FROM :lt_ranked
      WHERE recency <= :p_window
      GROUP BY programme_id;

    lt_to_date =
      SELECT programme_id,
             SUM( period_cost ) AS actuals_to_date
      FROM :lt_monthly
      GROUP BY programme_id;

    -- GREATEST( 0, ... ) is what stops a finished programme extrapolating
    -- into the past and reporting an EAC below what it has already spent.
    RETURN
      SELECT
        p.client                                        AS client,
        p.programme_id                                  AS programme_id,
        p.programme_name                                AS programme_name,
        p.programme_type                                AS programme_type,
        :p_fiscal_year                                  AS as_of_fiscal_year,
        :p_fiscal_period                                AS as_of_fiscal_period,
        CAST( d.actuals_to_date AS DECIMAL(18,2) )      AS actuals_to_date,
        CAST( r.run_rate        AS DECIMAL(18,2) )      AS run_rate,
        CAST( GREATEST( 0,
                ( YEAR( p.end_date )  - :p_fiscal_year ) * 12
              + ( MONTH( p.end_date ) - :p_fiscal_period ) )
              AS INTEGER )                              AS remaining_periods,
        CAST( d.actuals_to_date
              + r.run_rate * GREATEST( 0,
                  ( YEAR( p.end_date )  - :p_fiscal_year ) * 12
                + ( MONTH( p.end_date ) - :p_fiscal_period ) )
              AS DECIMAL(18,2) )                        AS eac,
        CAST( p.total_budget AS DECIMAL(18,2) )         AS total_budget,
        CAST( ( d.actuals_to_date
                + r.run_rate * GREATEST( 0,
                    ( YEAR( p.end_date )  - :p_fiscal_year ) * 12
                  + ( MONTH( p.end_date ) - :p_fiscal_period ) )
              ) / NULLIF( p.total_budget, 0 )
              AS DECIMAL(12,4) )                        AS eac_vs_budget_pct,
        p.currency                                      AS currency
      FROM ztns_programme AS p
        INNER JOIN :lt_to_date  AS d ON d.programme_id = p.programme_id
        INNER JOIN :lt_run_rate AS r ON r.programme_id = p.programme_id
      WHERE p.client = :p_client;

  ENDMETHOD.

ENDCLASS.
