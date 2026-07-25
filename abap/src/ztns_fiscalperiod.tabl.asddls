// ===========================================================================
// NOT ACTIVATED - no ABAP system was available. See docs/adr/003-abap-evidence-strategy.md
// ===========================================================================
// Fiscal period catalogue. Periods 1-16: twelve regular plus four special.
// ===========================================================================

@EndUserText.label: 'NovaSpace fiscal periods'
@AbapCatalog.enhancement.category: #NOT_EXTENSIBLE
@AbapCatalog.tableCategory: #TRANSPARENT
@AbapCatalog.deliveryClass: #C
@AbapCatalog.dataMaintenance: #RESTRICTED
define table ztns_fiscalperiod {
  key client        : abap.clnt not null;
  key fiscal_period : poper not null;
  period_text       : abap.char(20);
  // Periods 13-16 exist for year-end adjustments and audit corrections.
  is_special        : abap_boolean;
}
