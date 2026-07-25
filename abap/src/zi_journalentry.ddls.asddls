// ===========================================================================
// NOT ACTIVATED - no ABAP system was available. See docs/adr/003-abap-evidence-strategy.md
// ===========================================================================
// ZI_JournalEntry - basic interface view over the journal.
//
// The ABAP-stack counterpart of NOVASPACE_L2.V_JOURNAL, and it does the same
// job: apply the sign convention once, derive the flags, expose master data
// through associations rather than joins.
//
// Associations rather than joins is the point of an interface view. A consumer
// that needs the account group writes _GLAccount.AccountGroup and pays for one
// join; a consumer that does not, pays for nothing. A view built with joins
// makes every consumer pay for every attribute anybody might want.
// ===========================================================================

@AbapCatalog.viewEnhancementCategory: [#NONE]
@AccessControl.authorizationCheck: #CHECK
@EndUserText.label: 'Journal entry - interface view'
@Metadata.ignorePropagatedAnnotations: true
@ObjectModel.usageType: {
  serviceQuality: #X,
  sizeCategory  : #XXL,
  dataClass     : #TRANSACTIONAL
}
define view entity ZI_JournalEntry
  as select from ztns_journal as Journal

  association [0..1] to ZI_GLAccount  as _GLAccount  on  $projection.GLAccount   = _GLAccount.GLAccount
  association [0..1] to ZI_CostCenter as _CostCenter on  $projection.CostCenter  = _CostCenter.CostCenter
  association [0..1] to ZI_Programme  as _Programme  on  $projection.ProgrammeId = _Programme.ProgrammeId

{
      key Journal.journal_id                       as JournalId,

          Journal.company_code                     as CompanyCode,
          Journal.document_number                  as DocumentNumber,
          Journal.document_line                    as DocumentLine,
          Journal.document_type                    as DocumentType,

          Journal.posting_date                     as PostingDate,
          Journal.document_date                    as DocumentDate,
          Journal.entry_date                       as EntryDate,

          Journal.fiscal_year                      as FiscalYear,
          Journal.fiscal_period                    as FiscalPeriod,

          // Special periods 13-16 have no calendar month. Clamped so they are
          // reported against the period they adjust, which is how a year-end
          // adjustment is actually translated and presented.
          case when Journal.fiscal_period > 12
               then cast( 12 as poper )
               else Journal.fiscal_period
          end                                      as ReportingPeriod,

          @ObjectModel.foreignKey.association: '_GLAccount'
          Journal.gl_account                       as GLAccount,
          @ObjectModel.foreignKey.association: '_CostCenter'
          Journal.cost_center                      as CostCenter,
          @ObjectModel.foreignKey.association: '_Programme'
          Journal.programme_id                     as ProgrammeId,

          Journal.debit_credit_ind                 as DebitCreditInd,

          @Semantics.amount.currencyCode: 'DocCurrency'
          Journal.amount_doc_currency              as AmountInDocCurrency,
          Journal.doc_currency                     as DocCurrency,

          @Semantics.amount.currencyCode: 'LocalCurrency'
          Journal.amount_local_currency            as AmountInLocalCurrency,
          Journal.local_currency                   as LocalCurrency,

          @Semantics.amount.currencyCode: 'GroupCurrency'
          Journal.amount_group_currency            as AmountInGroupCurrency,
          Journal.group_currency                   as GroupCurrency,

          // Expenses positive, revenue negative. Applied once, here, so no
          // consumer re-derives it and gets the sign backwards on revenue.
          @Semantics.amount.currencyCode: 'GroupCurrency'
          case Journal.debit_credit_ind
               when 'S' then Journal.amount_group_currency
               else          Journal.amount_group_currency * -1
          end                                      as SignedAmountInGroupCurrency,

          @Semantics.amount.currencyCode: 'LocalCurrency'
          case Journal.debit_credit_ind
               when 'S' then Journal.amount_local_currency
               else          Journal.amount_local_currency * -1
          end                                      as SignedAmountInLocalCurrency,

          // Manual means somebody typed it. SA is a G/L document, SB an
          // accrual; everything else is emitted by a process.
          case when Journal.document_type in ( 'SA', 'SB' )
               then cast( 'X' as abap_boolean preserving type )
               else cast( ''  as abap_boolean preserving type )
          end                                      as IsManualPosting,

          Journal.is_intercompany                  as IsIntercompany,
          Journal.ic_partner_company               as ICPartnerCompany,

          Journal.is_reversal                      as IsReversal,
          Journal.reversed_document                as ReversedDocument,

          // Deliberately NOT exposed: posting_user_id. User-level attribution
          // is an audit function, not a management-reporting one, and it has
          // no business reaching an analytical consumption view.

          _GLAccount,
          _CostCenter,
          _Programme
}
