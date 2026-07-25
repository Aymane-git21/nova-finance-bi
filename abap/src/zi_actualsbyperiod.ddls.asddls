// ===========================================================================
// NOT ACTIVATED - no ABAP system was available. See docs/adr/003-abap-evidence-strategy.md
// ===========================================================================
// ZI_ActualsByPeriod - actuals aggregated to the grain budget is set at.
//
// Exists so ZI_BudgetVariance joins two sides that are already on the same
// grain. Aggregating inside the join would work and would also be the reason
// the variance is wrong the first time somebody adds a column to the SELECT.
// ===========================================================================

@AbapCatalog.viewEnhancementCategory: [#NONE]
@AccessControl.authorizationCheck: #CHECK
@EndUserText.label: 'Actuals by period - cost centre grain'
@Metadata.ignorePropagatedAnnotations: true
@ObjectModel.usageType: {
  serviceQuality: #X,
  sizeCategory  : #L,
  dataClass     : #TRANSACTIONAL
}
define view entity ZI_ActualsByPeriod
  as select from ZI_JournalEntry as Journal

  association [0..1] to ZI_GLAccount as _GLAccount on $projection.GLAccount = _GLAccount.GLAccount

{
  key Journal.CompanyCode                              as CompanyCode,
  key Journal.FiscalYear                               as FiscalYear,
  key Journal.ReportingPeriod                          as FiscalPeriod,
  key Journal.CostCenter                               as CostCenter,
  key Journal._GLAccount.AccountGroup                  as AccountGroup,
      // Non-programme cost is a real category, not a null to be dropped. It is
      // roughly 30% of the dataset and it has a budget.
  key coalesce( Journal.ProgrammeId, '(none)' )        as ProgrammeId,

      @Semantics.amount.currencyCode: 'Currency'
      sum( Journal.SignedAmountInGroupCurrency )       as ActualAmount,

      @Semantics.currencyCode: true
      Journal.GroupCurrency                            as Currency
}
// Revenue carries no cost centre and no cost-centre budget. Special periods
// carry no budget either and are excluded rather than folded into period 12,
// which would make December look like an overrun every year.
where Journal.CostCenter   is not initial
  and Journal.FiscalPeriod <= 12

group by
  Journal.CompanyCode,
  Journal.FiscalYear,
  Journal.ReportingPeriod,
  Journal.CostCenter,
  Journal._GLAccount.AccountGroup,
  Journal.ProgrammeId,
  Journal.GroupCurrency
