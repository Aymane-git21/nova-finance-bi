// ===========================================================================
// NOT ACTIVATED - no ABAP system was available. See docs/adr/003-abap-evidence-strategy.md
// ===========================================================================
// Cost centre master data, three-level standard hierarchy.
//
// department_id is 11 characters in the data. An earlier draft of the data
// dictionary declared 10, which would have truncated every department key on
// load - caught by measuring the generated data rather than trusting the doc.
// ===========================================================================

@EndUserText.label: 'NovaSpace cost centres'
@AbapCatalog.enhancement.category: #NOT_EXTENSIBLE
@AbapCatalog.tableCategory: #TRANSPARENT
@AbapCatalog.deliveryClass: #A
@AbapCatalog.dataMaintenance: #RESTRICTED
define table ztns_costcenter {
  key client        : abap.clnt not null;
  key cost_center   : kostl not null;
  cost_center_name  : abap.char(80);
  company_code      : bukrs;
  division_id       : abap.char(12);
  division_name     : abap.char(60);
  department_id     : abap.char(12);
  department_name   : abap.char(60);
  // The recursive edge. Equals department_id for a leaf.
  parent_id         : abap.char(12);
  hierarchy_level   : abap.int4;
  is_overhead       : abap_boolean;
  valid_from        : abap.dats;
  valid_to          : abap.dats;
  // Pseudonymous token. Not exposed by any interface view.
  manager_user_id   : abap.char(12);
}
