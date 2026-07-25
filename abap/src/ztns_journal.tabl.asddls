// ===========================================================================
// NOT ACTIVATED - no ABAP system was available. See docs/adr/003-abap-evidence-strategy.md
// ===========================================================================
// Journal line items in the ABAP stack.
//
// In a real Airbus landscape BW/4HANA and the ABAP stack share one system and
// this would be ACDOCA itself, or a CDS view over it. Here they are two
// separate systems, so a subset of the generated data is loaded into
// ABAP-managed tables and this is its definition.
//
// Column names, types and semantics match docs/data-dictionary.md exactly. The
// amounts stay unsigned with direction in DEBIT_CREDIT_IND, as SAP stores them
// - the sign convention is applied once, in the interface view.
// ===========================================================================

@EndUserText.label: 'NovaSpace journal entries'
@AbapCatalog.enhancement.category: #NOT_EXTENSIBLE
@AbapCatalog.tableCategory: #TRANSPARENT
@AbapCatalog.deliveryClass: #A
@AbapCatalog.dataMaintenance: #RESTRICTED
define table ztns_journal {

  key client                : abap.clnt not null;
  key journal_id            : abap.int8 not null;

  company_code              : bukrs;
  document_number           : belnr_d;
  document_line             : buzei;
  document_type             : blart;

  posting_date              : budat;
  document_date             : bldat;
  // The reason the late-posting flag can exist at all. A posting can be dated
  // inside the period and entered days after the cut-off; that gap is the
  // whole measurement, and a model carrying only BUDAT cannot compute it.
  entry_date                : cpudt;

  fiscal_year               : gjahr;
  // 1-16. Periods 13-16 carry year-end adjustments.
  fiscal_period             : poper;

  gl_account                : racct;
  cost_center               : kostl;
  // WBS-element analogue. Null on non-programme postings.
  programme_id              : abap.char(12);

  debit_credit_ind          : shkzg;

  @Semantics.amount.currencyCode: 'DOC_CURRENCY'
  amount_doc_currency       : abap.curr(15,2);
  doc_currency              : waers;

  @Semantics.amount.currencyCode: 'LOCAL_CURRENCY'
  amount_local_currency     : abap.curr(15,2);
  local_currency            : waers;

  @Semantics.amount.currencyCode: 'GROUP_CURRENCY'
  amount_group_currency     : abap.curr(15,2);
  group_currency            : waers;

  is_intercompany           : abap_boolean;
  ic_partner_company        : bukrs;

  // Pseudonymous token, generated. No name exists anywhere in the pipeline to
  // pseudonymise from, so there is no re-identification key. This column does
  // not reach the consumption layer - see docs/gdpr-and-data-protection.md.
  posting_user_id           : abap.char(12);

  is_reversal               : abap_boolean;
  reversed_document         : belnr_d;

}
