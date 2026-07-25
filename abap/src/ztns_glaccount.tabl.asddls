// ===========================================================================
// NOT ACTIVATED - no ABAP system was available. See docs/adr/003-abap-evidence-strategy.md
// ===========================================================================
// P&L account master data with a three-level hierarchy.
// ===========================================================================

@EndUserText.label: 'NovaSpace G/L accounts'
@AbapCatalog.enhancement.category: #NOT_EXTENSIBLE
@AbapCatalog.tableCategory: #TRANSPARENT
@AbapCatalog.deliveryClass: #A
@AbapCatalog.dataMaintenance: #RESTRICTED
define table ztns_glaccount {
  key client         : abap.clnt not null;
  key gl_account     : racct not null;
  gl_account_name    : abap.char(80);
  // Hierarchy level 2 - the grain most KPIs report at.
  account_group      : abap.char(3);
  account_group_name : abap.char(40);
  // Hierarchy level 1.
  pl_section         : abap.char(20);
  is_pl_account      : abap_boolean;
  // 'S' debit, 'H' credit. The journal sign convention derives from it.
  normal_balance     : abap.char(1);
}
