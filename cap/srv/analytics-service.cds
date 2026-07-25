using novaspace from '../db/schema';

/**
 * The analytics service. OData V4.
 *
 * The UI annotations below are the point of this file: Fiori Elements reads
 * them from $metadata and renders a full Analytical List Page with no UI code
 * at all. Where a chart's measure, a column's order or a value's criticality
 * lives is a modelling decision, not a front-end one - which is exactly the
 * argument for annotation-driven UIs, and the same argument BW makes when a
 * restricted key figure defined once shows up identically in every client.
 */
service AnalyticsService @(path: '/analytics') {

  @readonly
  @title: 'Budget variance'
  entity BudgetVariance as projection on novaspace.V_BUDGET_VARIANCE;

  @readonly
  @title: 'Programme burn'
  entity ProgrammeBurn   as projection on novaspace.V_PROGRAMME_BURN;

  @readonly
  @title: 'Close monitor'
  entity CloseMonitor    as projection on novaspace.V_CLOSE_MONITOR;

  @readonly
  @title: 'P&L actuals'
  entity PlActuals       as projection on novaspace.V_PL_ACTUALS;

  @readonly
  @title: 'Intercompany reconciliation'
  entity IcReconciliation as projection on novaspace.V_IC_RECONCILIATION;
}

// ---------------------------------------------------------------------------
// Budget variance - the Analytical List Page
// ---------------------------------------------------------------------------

annotate AnalyticsService.BudgetVariance with @(
  Aggregation.ApplySupported: {
    Transformations       : ['aggregate', 'topcount', 'bottomcount', 'identity',
                             'concat', 'groupby', 'filter', 'orderby', 'skip', 'top'],
    GroupableProperties   : [
      COMPANY_CODE, COMPANY_NAME, FISCAL_YEAR, FISCAL_PERIOD,
      FISCAL_PERIOD_LABEL, PROGRAMME_ID, PROGRAMME_NAME, ACCOUNT_GROUP,
      ACCOUNT_GROUP_NAME, COST_CENTER, COST_CENTER_NAME, DIVISION_NAME
    ],
    AggregatableProperties: [
      { Property: ACTUAL_AMOUNT }, { Property: BUDGET_AMOUNT }, { Property: VARIANCE }
    ]
  },

  UI: {
    SelectionFields: [ FISCAL_YEAR, COMPANY_CODE, PROGRAMME_ID, ACCOUNT_GROUP ],

    // The KPI header of the Analytical List Page.
    Chart          : {
      $Type              : 'UI.ChartDefinitionType',
      ChartType          : #Column,
      Title              : 'Actual vs budget by period',
      Dimensions         : [ FISCAL_PERIOD_LABEL ],
      DimensionAttributes: [{
        $Type    : 'UI.ChartDimensionAttributeType',
        Dimension: FISCAL_PERIOD_LABEL,
        Role     : #Category
      }],
      Measures           : [ ACTUAL_AMOUNT, BUDGET_AMOUNT ],
      MeasureAttributes  : [
        { $Type: 'UI.ChartMeasureAttributeType', Measure: ACTUAL_AMOUNT, Role: #Axis1 },
        { $Type: 'UI.ChartMeasureAttributeType', Measure: BUDGET_AMOUNT, Role: #Axis1 }
      ]
    },

    PresentationVariant: {
      // Worst variance first. A variance table sorted by cost centre is a list;
      // sorted by variance it is a finding.
      SortOrder     : [{ Property: VARIANCE, Descending: true }],
      GroupBy       : [ PROGRAMME_ID ],
      Visualizations: ['@UI.Chart', '@UI.LineItem']
    },

    LineItem: [
      { Value: PROGRAMME_NAME,     Label: 'Programme' },
      { Value: COMPANY_CODE,       Label: 'Entity' },
      { Value: FISCAL_PERIOD_LABEL,Label: 'Period' },
      { Value: ACCOUNT_GROUP_NAME, Label: 'Account group' },
      { Value: ACTUAL_AMOUNT,      Label: 'Actual' },
      { Value: BUDGET_AMOUNT,      Label: 'Budget' },
      {
        Value      : VARIANCE,
        Label      : 'Variance',
        // Thresholds live in the model, so every client colours identically.
        Criticality: VARIANCE_CRITICALITY
      },
      { Value: VARIANCE_PCT,       Label: 'Variance %' }
    ]
  }
);

annotate AnalyticsService.BudgetVariance with {
  ACTUAL_AMOUNT @Measures.ISOCurrency: CURRENCY;
  BUDGET_AMOUNT @Measures.ISOCurrency: CURRENCY;
  VARIANCE      @Measures.ISOCurrency: CURRENCY;
  VARIANCE_PCT  @Measures.Unit       : '%';
};

// ---------------------------------------------------------------------------
// Programme burn - consumed by the freestyle UI5 bubble chart
// ---------------------------------------------------------------------------

annotate AnalyticsService.ProgrammeBurn with @(
  UI: {
    HeaderInfo: {
      $Type         : 'UI.HeaderInfoType',
      TypeName      : 'Programme',
      TypeNamePlural: 'Programmes',
      Title         : { Value: PROGRAMME_NAME },
      Description   : { Value: PROGRAMME_TYPE }
    },
    LineItem  : [
      { Value: PROGRAMME_NAME,      Label: 'Programme' },
      { Value: PROGRAMME_TYPE,      Label: 'Type' },
      { Value: PCT_TIME_ELAPSED,    Label: 'Schedule elapsed' },
      { Value: PCT_BUDGET_CONSUMED, Label: 'Budget consumed' },
      { Value: ACTUALS_TO_DATE,     Label: 'Actuals to date' },
      { Value: EAC,                 Label: 'EAC' },
      { Value: TOTAL_BUDGET,        Label: 'Budget' },
      { Value: EAC_VS_BUDGET_PCT,   Label: 'EAC / budget', Criticality: EAC_CRITICALITY }
    ]
  }
);

annotate AnalyticsService.ProgrammeBurn with {
  ACTUALS_TO_DATE @Measures.ISOCurrency: CURRENCY;
  EAC             @Measures.ISOCurrency: CURRENCY;
  TOTAL_BUDGET    @Measures.ISOCurrency: CURRENCY;
  RUN_RATE        @Measures.ISOCurrency: CURRENCY;
};

// ---------------------------------------------------------------------------
// Close monitor
// ---------------------------------------------------------------------------

annotate AnalyticsService.CloseMonitor with @(
  UI: {
    SelectionFields: [ FISCAL_YEAR, COMPANY_CODE ],
    LineItem       : [
      { Value: COMPANY_NAME,        Label: 'Entity' },
      { Value: FISCAL_PERIOD_LABEL, Label: 'Period' },
      { Value: TASK_NAME,           Label: 'Task' },
      { Value: DUE_DATE,            Label: 'Due' },
      { Value: ACTUAL_COMPLETION_DATE, Label: 'Completed' },
      { Value: DELAY_WORKING_DAYS,  Label: 'Delay (wd)' },
      { Value: DAYS_TO_CLOSE,       Label: 'Days to close', Criticality: CLOSE_CRITICALITY },
      { Value: MANUAL_SHARE,        Label: 'Manual share' },
      { Value: LATE_SHARE,          Label: 'Late share' }
    ]
  }
);
