// ===========================================================================
// NOT ACTIVATED - no ABAP system was available. See docs/adr/003-abap-evidence-strategy.md
// ===========================================================================
// ZI_FiscalPeriodRange - the twelve regular posting periods, as rows.
//
// A helper for the cross join in ZI_BudgetPhased. Special periods 13-16 are
// excluded deliberately: they carry year-end adjustments and no budget.
//
// Reads from the fiscal-period catalogue rather than generating a literal
// union, so a non-calendar fiscal year variant would need one filter changed
// here rather than a rewrite in every consumer.
// ===========================================================================

@AbapCatalog.viewEnhancementCategory: [#NONE]
@AccessControl.authorizationCheck: #NOT_REQUIRED
@EndUserText.label: 'Regular fiscal periods 1-12'
@Metadata.ignorePropagatedAnnotations: true
@ObjectModel.usageType: {
  serviceQuality: #A,
  sizeCategory  : #S,
  dataClass     : #CUSTOMIZING
}
define view entity ZI_FiscalPeriodRange
  as select distinct from ztns_fiscalperiod as Period
{
  key Period.fiscal_period as FiscalPeriod
}
where Period.fiscal_period <= 12
