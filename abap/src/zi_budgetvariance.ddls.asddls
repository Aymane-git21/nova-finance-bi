// ===========================================================================
// NOT ACTIVATED - no ABAP system was available. See docs/adr/003-abap-evidence-strategy.md
// ===========================================================================
// ZI_BudgetVariance - composite interface view: actuals against phased budget.
//
// The ABAP counterpart of NOVASPACE_L3.CV_BUDGET_VARIANCE, and it makes the
// same three decisions, for the same reasons:
//
//   1. Revenue is excluded on both sides. Budgets are set on cost centres and
//      revenue lines carry no cost centre, so including revenue in the actual
//      compares it against a budget that never contained any - the classic way
//      a variance report comes out favourable for no reason.
//
//   2. Budget is annual and actuals are periodic, so a phasing rule is
//      unavoidable. NovaSpace phases evenly across twelve periods and says so.
//      Applying it once here means no consumer reinvents it.
//
//   3. FULL OUTER, not INNER. A cost centre that spent with no budget and one
//      that was budgeted and spent nothing are both real findings, and an
//      inner join hides exactly those two cases.
// ===========================================================================

@AbapCatalog.viewEnhancementCategory: [#NONE]
@AccessControl.authorizationCheck: #CHECK
@EndUserText.label: 'Budget variance - composite view'
@Metadata.ignorePropagatedAnnotations: true
@ObjectModel.usageType: {
  serviceQuality: #X,
  sizeCategory  : #L,
  dataClass     : #MIXED
}
define view entity ZI_BudgetVariance
  as select from ZI_ActualsByPeriod as Actual

  full outer join ZI_BudgetPhased as Budget
    on  Actual.CompanyCode  = Budget.CompanyCode
    and Actual.FiscalYear   = Budget.FiscalYear
    and Actual.FiscalPeriod = Budget.FiscalPeriod
    and Actual.CostCenter   = Budget.CostCenter
    and Actual.AccountGroup = Budget.AccountGroup
    and Actual.ProgrammeId  = Budget.ProgrammeId

  association [0..1] to ZI_CostCenter as _CostCenter on $projection.CostCenter  = _CostCenter.CostCenter
  association [0..1] to ZI_Programme  as _Programme  on $projection.ProgrammeId = _Programme.ProgrammeId

{
  key coalesce( Actual.CompanyCode,  Budget.CompanyCode )  as CompanyCode,
  key coalesce( Actual.FiscalYear,   Budget.FiscalYear )   as FiscalYear,
  key coalesce( Actual.FiscalPeriod, Budget.FiscalPeriod ) as FiscalPeriod,
  key coalesce( Actual.CostCenter,   Budget.CostCenter )   as CostCenter,
  key coalesce( Actual.AccountGroup, Budget.AccountGroup ) as AccountGroup,
  key coalesce( Actual.ProgrammeId,  Budget.ProgrammeId )  as ProgrammeId,

      concat( concat( cast( coalesce( Actual.FiscalYear, Budget.FiscalYear ) as abap.char(4) ), '-' ),
              lpad( cast( coalesce( Actual.FiscalPeriod, Budget.FiscalPeriod ) as abap.char(2) ), 2, '0' ) )
                                                           as FiscalPeriodLabel,

      _CostCenter.CostCenterName                           as CostCenterName,
      _CostCenter.DivisionName                             as DivisionName,
      _Programme.ProgrammeName                             as ProgrammeName,

      @Semantics.amount.currencyCode: 'Currency'
      coalesce( Actual.ActualAmount, cast( 0 as abap.curr(18,2) ) ) as ActualAmount,

      @Semantics.amount.currencyCode: 'Currency'
      coalesce( Budget.BudgetAmount, cast( 0 as abap.curr(18,2) ) ) as BudgetAmount,

      @Semantics.amount.currencyCode: 'Currency'
      cast( coalesce( Actual.ActualAmount, cast( 0 as abap.curr(18,2) ) )
          - coalesce( Budget.BudgetAmount, cast( 0 as abap.curr(18,2) ) )
            as abap.curr(18,2) )                           as Variance,

      // Undefined, not zero, where there is no budget to vary from. A zero
      // here averages into a portfolio figure and quietly flatters it.
      case when coalesce( Budget.BudgetAmount, cast( 0 as abap.curr(18,2) ) ) <> 0
           then cast( ( coalesce( Actual.ActualAmount, cast( 0 as abap.curr(18,2) ) )
                      - Budget.BudgetAmount )
                      / abs( Budget.BudgetAmount ) as abap.dec(12,4) )
      end                                                  as VariancePct,

      // 1 red, 2 amber, 3 green, 0 no value. In the model, not in a formatter.
      case when coalesce( Budget.BudgetAmount, cast( 0 as abap.curr(18,2) ) ) = 0 then 0
           when ( coalesce( Actual.ActualAmount, cast( 0 as abap.curr(18,2) ) )
                - Budget.BudgetAmount ) / abs( Budget.BudgetAmount ) > cast( '0.10' as abap.dec(12,4) ) then 1
           when ( coalesce( Actual.ActualAmount, cast( 0 as abap.curr(18,2) ) )
                - Budget.BudgetAmount ) / abs( Budget.BudgetAmount ) > cast( '0.05' as abap.dec(12,4) ) then 2
           else 3
      end                                                  as VarianceCriticality,

      @Semantics.currencyCode: true
      coalesce( Actual.Currency, Budget.Currency )         as Currency,

      _CostCenter,
      _Programme
}
