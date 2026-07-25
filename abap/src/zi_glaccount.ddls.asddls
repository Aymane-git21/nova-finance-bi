// ===========================================================================
// NOT ACTIVATED - no ABAP system was available. See docs/adr/003-abap-evidence-strategy.md
// ===========================================================================
// ZI_GLAccount - master data interface view for the P&L account structure.
//
// @ObjectModel.representativeKey and the text association are what let a
// consumption view show "Personnel" rather than "600120" without any consumer
// writing a join. In BW this is what an InfoObject with texts does.
// ===========================================================================

@AbapCatalog.viewEnhancementCategory: [#NONE]
@AccessControl.authorizationCheck: #NOT_REQUIRED
@EndUserText.label: 'G/L account - interface view'
@Metadata.ignorePropagatedAnnotations: true
@ObjectModel.usageType: {
  serviceQuality: #A,
  sizeCategory  : #S,
  dataClass     : #MASTER
}
@ObjectModel.representativeKey: 'GLAccount'
define view entity ZI_GLAccount
  as select from ztns_glaccount as Account
{
      @ObjectModel.text.element: ['GLAccountName']
  key Account.gl_account         as GLAccount,

      @Semantics.text: true
      Account.gl_account_name    as GLAccountName,

      // Hierarchy level 2. The grain every KPI in docs/kpi-definitions.md
      // that mentions "account group" actually reports at.
      Account.account_group      as AccountGroup,
      @Semantics.text: true
      Account.account_group_name as AccountGroupName,

      // Hierarchy level 1.
      Account.pl_section         as PLSection,

      Account.is_pl_account      as IsPLAccount,

      // 'S' debit, 'H' credit. The journal's sign convention derives from it.
      Account.normal_balance     as NormalBalance
}
