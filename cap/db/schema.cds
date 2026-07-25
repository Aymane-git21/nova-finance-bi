namespace novaspace;

/**
 * Bindings to the published HANA interface views in NOVASPACE_API.
 *
 * Every entity carries @cds.persistence.exists: CAP must bind to these, never
 * try to deploy them. The objects already exist, were built by
 * hana/sql/*.sql, and are verified against the Python reference by
 * hana/verify_against_python.py. CAP's job here is to expose them, not to own
 * them.
 *
 * Names match the HANA views exactly and the connection runs with
 * NOVASPACE_API as its current schema, so no qualification is needed and no
 * mapping layer can drift.
 */

@cds.persistence.exists
entity V_BUDGET_VARIANCE {
  key COMPANY_CODE         : String(4);
  key FISCAL_YEAR          : Integer;
  key FISCAL_PERIOD        : Integer;
  key COST_CENTER          : String(10);
  key ACCOUNT_GROUP        : String(3);
  key PROGRAMME_ID         : String(12);
      COMPANY_NAME         : String(80);
      FISCAL_PERIOD_LABEL  : String(8);
      COST_CENTER_NAME     : String(80);
      DIVISION_NAME        : String(60);
      PROGRAMME_NAME       : String(80);
      ACCOUNT_GROUP_NAME   : String(40);
      ACTUAL_AMOUNT        : Decimal(18, 2);
      BUDGET_AMOUNT        : Decimal(18, 2);
      VARIANCE             : Decimal(18, 2);
      VARIANCE_PCT         : Decimal(12, 4);
      CURRENCY             : String(3);
      VARIANCE_CRITICALITY : Integer;
}

@cds.persistence.exists
entity V_PROGRAMME_BURN {
  key PROGRAMME_ID        : String(12);
      PROGRAMME_NAME      : String(80);
      PROGRAMME_TYPE      : String(20);
      LEAD_COMPANY_CODE   : String(4);
      STATUS              : String(20);
      START_DATE          : Date;
      END_DATE            : Date;
      ACTUALS_TO_DATE     : Decimal(18, 2);
      RUN_RATE            : Decimal(18, 2);
      REMAINING_PERIODS   : Integer;
      EAC                 : Decimal(18, 2);
      TOTAL_BUDGET        : Decimal(18, 2);
      EAC_VS_BUDGET_PCT   : Decimal(12, 4);
      CURRENCY            : String(3);
      PCT_BUDGET_CONSUMED : Decimal(12, 4);
      PCT_TIME_ELAPSED    : Decimal(12, 4);
      EAC_CRITICALITY     : Integer;
}

@cds.persistence.exists
entity V_CLOSE_MONITOR {
  key COMPANY_CODE           : String(4);
  key FISCAL_YEAR            : Integer;
  key FISCAL_PERIOD          : Integer;
  key TASK_ID                : String(4);
      COMPANY_NAME           : String(80);
      FISCAL_PERIOD_LABEL    : String(8);
      TASK_NAME              : String(80);
      TASK_SEQUENCE          : Integer;
      IS_MILESTONE           : Boolean;
      PERIOD_END_DATE        : Date;
      DUE_DATE               : Date;
      // Null when the period has not closed. Must stay nullable all the way to
      // the UI: an open period is open, never a zero-day close.
      ACTUAL_COMPLETION_DATE : Date;
      DELAY_WORKING_DAYS     : Integer;
      IS_OPEN                : Boolean;
      DAYS_TO_CLOSE          : Integer;
      LINE_COUNT             : Integer;
      MANUAL_LINE_COUNT      : Integer;
      LATE_LINE_COUNT        : Integer;
      LATE_VALUE             : Decimal(18, 2);
      MANUAL_SHARE           : Decimal(12, 4);
      LATE_SHARE             : Decimal(12, 4);
      CLOSE_CRITICALITY      : Integer;
}

@cds.persistence.exists
entity V_PL_ACTUALS {
  key COMPANY_CODE       : String(4);
  key FISCAL_YEAR        : Integer;
  key FISCAL_PERIOD      : Integer;
  key PL_SECTION         : String(20);
  key ACCOUNT_GROUP      : String(3);
      COMPANY_NAME       : String(80);
      FISCAL_PERIOD_LABEL: String(8);
      ACCOUNT_GROUP_NAME : String(40);
      AMOUNT             : Decimal(18, 2);
      AMOUNT_MANUAL      : Decimal(18, 2);
      LINE_COUNT         : Integer;
      LINE_COUNT_MANUAL  : Integer;
      LINE_COUNT_LATE    : Integer;
      CURRENCY           : String(3);
}

@cds.persistence.exists
entity V_IC_RECONCILIATION {
  key IC_PAIR       : String(9);
  key FISCAL_YEAR   : Integer;
  key FISCAL_PERIOD : Integer;
      NET_AMOUNT    : Decimal(18, 2);
      LINE_COUNT    : Integer;
      IS_MISMATCH   : Boolean;
      CURRENCY      : String(3);
}
