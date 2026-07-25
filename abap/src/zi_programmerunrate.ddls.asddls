// ===========================================================================
// NOT ACTIVATED - no ABAP system was available. See docs/adr/003-abap-evidence-strategy.md
// ===========================================================================
// ZI_ProgrammeRunRate - CDS table function for KPI-05.
//
// A table function is the declarative half of an AMDP: it declares the
// signature and the result structure, and delegates the body to an ABAP class
// method whose implementation is SQLScript executed by HANA.
//
// This is the object that proves ABAP, SQLScript and performance thinking at
// once. It is also the reason Phase 4 survived having no ABAP system: an
// AMDP's body IS SQLScript, HANA executes it, and ABAP is only the wrapper.
// The identical body is deployed and running as
// NOVASPACE_L3.TF_PROGRAMME_RUNRATE (hana/sql/04_runrate_function.sql), where
// it is verified against the Python reference to within EUR 0.28 on an
// EUR 800m EAC, and benchmarked in Phase 7.
//
// So: the logic is proven, the wrapper is not activated. The repository does
// not claim otherwise.
//
// The client parameter is mandatory for a table function and must be bound to
// the system field - a CDS entity that ignores the client is a data leak
// between tenants, not a shortcut.
// ===========================================================================

@EndUserText.label: 'Programme run-rate and estimate at completion'
@ClientHandling.algorithm: #SESSION_VARIABLE
define table function ZI_ProgrammeRunRate

  with parameters
    @Environment.systemField: #CLIENT
    p_client        : abap.clnt,
    // As-of point. The run-rate window ends here and the remaining periods
    // are counted from here to the programme's planned end.
    p_fiscal_year   : gjahr,
    p_fiscal_period : poper,
    // Rolling window in periods. Three is the controller's default; the
    // parameter exists so the sensitivity of the EAC to it can be shown.
    p_window        : abap.int4

  returns {
    client              : abap.clnt;
    programme_id        : abap.char(12);
    programme_name      : abap.char(80);
    programme_type      : abap.char(20);
    as_of_fiscal_year   : gjahr;
    as_of_fiscal_period : poper;

    @Semantics.amount.currencyCode: 'currency'
    actuals_to_date     : abap.curr(18,2);
    @Semantics.amount.currencyCode: 'currency'
    run_rate            : abap.curr(18,2);

    remaining_periods   : abap.int4;

    @Semantics.amount.currencyCode: 'currency'
    eac                 : abap.curr(18,2);
    @Semantics.amount.currencyCode: 'currency'
    total_budget        : abap.curr(18,2);

    eac_vs_budget_pct   : abap.dec(12,4);
    currency            : waers;
  }

  implemented by method zcl_amdp_runrate=>get_run_rate;
