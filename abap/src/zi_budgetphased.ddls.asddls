// ===========================================================================
// NOT ACTIVATED - no ABAP system was available. See docs/adr/003-abap-evidence-strategy.md
// ===========================================================================
// ZI_BudgetPhased - annual budget spread evenly across twelve periods.
//
// The phasing rule stated in docs/kpi-definitions.md, applied once. Real
// budgets are phased on an activity profile; the even rule is a documented
// simplification, and the important part is that it is declared in the model
// rather than reinvented by each consumer with a slightly different answer.
//
// The cross join against a twelve-row period list is the standard way to turn
// one annual row into twelve periodic ones. ZI_FiscalPeriodRange is a helper
// entity over the fiscal-period catalogue, filtered to 1-12: special periods
// carry no budget.
// ===========================================================================

@AbapCatalog.viewEnhancementCategory: [#NONE]
@AccessControl.authorizationCheck: #CHECK
@EndUserText.label: 'Budget phased to periods'
@Metadata.ignorePropagatedAnnotations: true
@ObjectModel.usageType: {
  serviceQuality: #X,
  sizeCategory  : #M,
  dataClass     : #MIXED
}
define view entity ZI_BudgetPhased
  as select from ztns_budget         as Budget
  cross join      ZI_FiscalPeriodRange as Period
{
  key Budget.company_code                               as CompanyCode,
  key Budget.fiscal_year                                as FiscalYear,
  key Period.FiscalPeriod                               as FiscalPeriod,
  key Budget.cost_center                                as CostCenter,
  key Budget.account_group                              as AccountGroup,
  key coalesce( Budget.programme_id, '(none)' )         as ProgrammeId,

      Budget.version                                    as Version,

      @Semantics.amount.currencyCode: 'Currency'
      Budget.amount                                     as AmountAnnual,

      @Semantics.amount.currencyCode: 'Currency'
      cast( Budget.amount / 12 as abap.curr(18,2) )     as BudgetAmount,

      @Semantics.currencyCode: true
      Budget.currency                                   as Currency
}
