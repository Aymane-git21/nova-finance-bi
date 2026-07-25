// ===========================================================================
// NOT ACTIVATED - no ABAP system was available. See docs/adr/003-abap-evidence-strategy.md
// ===========================================================================
// Annual budget. One version. Phased to periods by ZI_BudgetPhased.
// ===========================================================================

@EndUserText.label: 'NovaSpace budget'
@AbapCatalog.enhancement.category: #NOT_EXTENSIBLE
@AbapCatalog.tableCategory: #TRANSPARENT
@AbapCatalog.deliveryClass: #A
@AbapCatalog.dataMaintenance: #RESTRICTED
define table ztns_budget {
  key client       : abap.clnt not null;
  key budget_id    : abap.int8 not null;
  company_code     : bukrs;
  fiscal_year      : gjahr;
  cost_center      : kostl;
  account_group    : abap.char(3);
  programme_id     : abap.char(12);
  // Version dimension: the BPC 'category' concept. See docs/sac-and-bpc.md.
  version          : abap.char(10);
  @Semantics.amount.currencyCode: 'CURRENCY'
  amount           : abap.curr(18,2);
  currency         : waers;
}
