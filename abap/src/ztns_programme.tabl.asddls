// ===========================================================================
// NOT ACTIVATED - no ABAP system was available. See docs/adr/003-abap-evidence-strategy.md
// ===========================================================================
// Programme master data. WBS-element analogue.
// ===========================================================================

@EndUserText.label: 'NovaSpace programmes'
@AbapCatalog.enhancement.category: #NOT_EXTENSIBLE
@AbapCatalog.tableCategory: #TRANSPARENT
@AbapCatalog.deliveryClass: #A
@AbapCatalog.dataMaintenance: #RESTRICTED
define table ztns_programme {
  key client         : abap.clnt not null;
  key programme_id   : abap.char(12) not null;
  programme_name     : abap.char(80);
  programme_type     : abap.char(20);
  lead_company_code  : bukrs;
  start_date         : abap.dats;
  // Drives RemainingPeriods in the EAC. A programme past this date gets no
  // extrapolation at all.
  end_date           : abap.dats;
  @Semantics.amount.currencyCode: 'CURRENCY'
  total_budget       : abap.curr(18,2);
  currency           : waers;
  status             : abap.char(20);
}
