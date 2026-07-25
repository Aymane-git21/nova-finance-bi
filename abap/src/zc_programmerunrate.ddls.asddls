// ===========================================================================
// NOT ACTIVATED - no ABAP system was available. See docs/adr/003-abap-evidence-strategy.md
// ===========================================================================
// ZC_ProgrammeRunRate - analytical consumption view over the AMDP.
//
// This is where the table function surfaces to a consumer. The parameters
// pass straight through, so a caller chooses the as-of point and the rolling
// window rather than being handed one somebody hardcoded.
//
// The bubble chart annotation is the interesting one: two ratios and a
// magnitude on one picture. A programme on plan sits on the diagonal where
// budget consumed equals schedule elapsed, and distance above it is the
// finding. The same chart is hand-built in fiori/webapp against the CAP
// service, and it is the artifact that makes the overrun visible in one look.
// ===========================================================================

@AccessControl.authorizationCheck: #CHECK
@EndUserText.label: 'Programme run-rate and EAC - analytical query'
@Metadata.allowExtensions: true

@Analytics.query: true
@Aggregation.default: #SUM

@UI.headerInfo: {
  typeName      : 'Programme',
  typeNamePlural: 'Programmes',
  title         : { value: 'ProgrammeName' },
  description   : { value: 'ProgrammeType' }
}

@UI.chart: [{
  qualifier          : 'BurnChart',
  chartType          : #BUBBLE,
  title              : 'Programme burn: spending against schedule',
  description        : 'On plan sits on the diagonal. Above it is burning faster than the calendar.',
  dimensions         : ['ProgrammeName'],
  measures           : ['PctTimeElapsed', 'PctBudgetConsumed', 'TotalBudget'],
  measureAttributes  : [
    { measure: 'PctTimeElapsed',    role: #AXIS_1 },
    { measure: 'PctBudgetConsumed', role: #AXIS_2 },
    { measure: 'TotalBudget',       role: #AXIS_3 }
  ]
}]

define view entity ZC_ProgrammeRunRate
  with parameters
    @Consumption.defaultValue: '2026'
    p_fiscal_year   : gjahr,
    @Consumption.defaultValue: '6'
    p_fiscal_period : poper,
    @Consumption.defaultValue: '3'
    p_window        : abap.int4

  as select from ZI_ProgrammeRunRate(
                   p_fiscal_year   : $parameters.p_fiscal_year,
                   p_fiscal_period : $parameters.p_fiscal_period,
                   p_window        : $parameters.p_window ) as RunRate

  association [0..1] to ZI_Programme as _Programme on $projection.ProgrammeId = _Programme.ProgrammeId

{
      @UI.lineItem: [{ position: 10, label: 'Programme' }]
  key RunRate.programme_id                       as ProgrammeId,

      RunRate.programme_name                     as ProgrammeName,
      @UI.lineItem: [{ position: 20, label: 'Type' }]
      RunRate.programme_type                     as ProgrammeType,

      RunRate.as_of_fiscal_year                  as AsOfFiscalYear,
      RunRate.as_of_fiscal_period                as AsOfFiscalPeriod,

      @UI.lineItem: [{ position: 30, label: 'Actuals to date' }]
      @Semantics.amount.currencyCode: 'Currency'
      RunRate.actuals_to_date                    as ActualsToDate,

      @UI.lineItem: [{ position: 40, label: 'Run-rate / period' }]
      @Semantics.amount.currencyCode: 'Currency'
      RunRate.run_rate                           as RunRate,

      RunRate.remaining_periods                  as RemainingPeriods,

      @UI.lineItem: [{ position: 50, label: 'EAC' }]
      @Semantics.amount.currencyCode: 'Currency'
      RunRate.eac                                as EAC,

      @UI.lineItem: [{ position: 60, label: 'Budget' }]
      @Semantics.amount.currencyCode: 'Currency'
      RunRate.total_budget                       as TotalBudget,

      @UI.lineItem: [{ position: 70, label: 'EAC / budget',
                       criticality: 'EACCriticality' }]
      RunRate.eac_vs_budget_pct                  as EACVsBudgetPct,

      // Share of the lifetime budget already spent.
      cast( division( RunRate.actuals_to_date, RunRate.total_budget, 4 )
            as abap.dec(12,4) )                  as PctBudgetConsumed,

      // 1 red above 110% of budget, 2 amber above 100%, 3 green. Thresholds in
      // the model, so every client colours identically.
      case when RunRate.eac_vs_budget_pct > cast( '1.10' as abap.dec(12,4) ) then 1
           when RunRate.eac_vs_budget_pct > cast( '1.00' as abap.dec(12,4) ) then 2
           else 3
      end                                        as EACCriticality,

      @Semantics.currencyCode: true
      RunRate.currency                           as Currency,

      _Programme
}
