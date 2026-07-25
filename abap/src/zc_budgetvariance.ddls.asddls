// ===========================================================================
// NOT ACTIVATED - no ABAP system was available. See docs/adr/003-abap-evidence-strategy.md
// ===========================================================================
// ZC_BudgetVariance - analytical consumption view for KPI-04.
//
// @Analytics.query: true makes this an analytical query in the S/4 embedded
// analytics sense - the CDS equivalent of a BEx query. The @UI annotations
// below are what let Fiori Elements render a full Analytical List Page with
// no UI code: the framework reads them from $metadata and builds the KPI
// header, the chart, the filter bar and the table.
//
// The same annotation set is implemented for real in the CAP service
// (cap/srv/analytics-service.cds), where it drives a working ALP against the
// live OData V4 endpoint. This file is the ABAP form of the same model.
//
// Where a chart's measures live and what turns a variance red are modelling
// decisions, not front-end ones. Declaring them once here is the same
// argument BW makes when a restricted key figure defined in a query renders
// identically in every client that consumes it.
// ===========================================================================

@AccessControl.authorizationCheck: #CHECK
@EndUserText.label: 'Budget variance - analytical query'
@Metadata.allowExtensions: true

@Analytics.query: true
@Aggregation.default: #SUM

@UI.headerInfo: {
  typeName      : 'Budget variance',
  typeNamePlural: 'Budget variances'
}

@UI.chart: [{
  qualifier      : 'VarianceChart',
  chartType      : #COLUMN,
  title          : 'Actual against budget by period',
  dimensions     : ['FiscalPeriodLabel'],
  measures       : ['ActualAmount', 'BudgetAmount'],
  dimensionAttributes: [{ dimension: 'FiscalPeriodLabel', role: #CATEGORY }],
  measureAttributes  : [
    { measure: 'ActualAmount', role: #AXIS_1 },
    { measure: 'BudgetAmount', role: #AXIS_1 }
  ]
}]

@UI.presentationVariant: [{
  // Worst variance first. A variance table sorted by cost centre is a list;
  // sorted by variance it is a finding.
  sortOrder     : [{ by: 'Variance', direction: #DESC }],
  visualizations: [{ type: #AS_CHART, qualifier: 'VarianceChart' },
                   { type: #AS_LINEITEM }]
}]

define view entity ZC_BudgetVariance
  as select from ZI_BudgetVariance
{
      @UI.selectionField: [{ position: 10 }]
      @EndUserText.label: 'Fiscal year'
  key FiscalYear,

      @UI.selectionField: [{ position: 20 }]
      @UI.lineItem      : [{ position: 20, label: 'Entity' }]
  key CompanyCode,

      @UI.lineItem      : [{ position: 30, label: 'Period' }]
  key FiscalPeriod,

      @UI.selectionField: [{ position: 30 }]
      @UI.lineItem      : [{ position: 10, label: 'Programme' }]
  key ProgrammeId,

      @UI.selectionField: [{ position: 40 }]
      @UI.lineItem      : [{ position: 40, label: 'Account group' }]
  key AccountGroup,

  key CostCenter,

      FiscalPeriodLabel,
      CompanyName,
      ProgrammeName,
      AccountGroupName,
      CostCenterName,

      @UI.lineItem: [{ position: 50, label: 'Actual' }]
      @Semantics.amount.currencyCode: 'Currency'
      ActualAmount,

      @UI.lineItem: [{ position: 60, label: 'Budget' }]
      @Semantics.amount.currencyCode: 'Currency'
      BudgetAmount,

      // Criticality is a model element, not a UI decision. Computed in the
      // interface view so every consumer applies identical thresholds and
      // nobody re-invents them in a formatter.
      @UI.lineItem: [{ position: 70, label: 'Variance',
                       criticality: 'VarianceCriticality' }]
      @Semantics.amount.currencyCode: 'Currency'
      Variance,

      @UI.lineItem: [{ position: 80, label: 'Variance %' }]
      VariancePct,

      VarianceCriticality,

      @Semantics.currencyCode: true
      Currency
}
