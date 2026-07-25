// ===========================================================================
// NOT ACTIVATED - no ABAP system was available. See docs/adr/003-abap-evidence-strategy.md
// ===========================================================================
// ZI_Programme - master data interface view for the space programmes.
//
// The WBS-element analogue: the account-assignment object programme cost is
// booked to. In a real landscape this comes from PS with its own hierarchy and
// status management; here it is a flat master-data table.
//
// TotalBudget is derived from actual burn rather than declared - see
// data-generator/novaspace/programme_budget.py for why a declared figure made
// the smallest programme rank as the worst overrun.
// ===========================================================================

@AbapCatalog.viewEnhancementCategory: [#NONE]
@AccessControl.authorizationCheck: #NOT_REQUIRED
@EndUserText.label: 'Programme - interface view'
@Metadata.ignorePropagatedAnnotations: true
@ObjectModel.usageType: {
  serviceQuality: #A,
  sizeCategory  : #S,
  dataClass     : #MASTER
}
@ObjectModel.representativeKey: 'ProgrammeId'
define view entity ZI_Programme
  as select from ztns_programme as Programme
{
      @ObjectModel.text.element: ['ProgrammeName']
  key Programme.programme_id      as ProgrammeId,

      @Semantics.text: true
      Programme.programme_name    as ProgrammeName,

      Programme.programme_type    as ProgrammeType,
      Programme.lead_company_code as LeadCompanyCode,

      Programme.start_date        as StartDate,
      // Drives RemainingPeriods in the EAC. A programme past its end date gets
      // no extrapolation at all.
      Programme.end_date          as EndDate,

      @Semantics.amount.currencyCode: 'Currency'
      Programme.total_budget      as TotalBudget,
      Programme.currency          as Currency,

      Programme.status            as Status
}
