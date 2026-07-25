# ABAP / CDS layer

> ## ⚠️ NOT ACTIVATED
>
> **Every source in this directory is authored but has never been activated on a running system, and nothing here claims otherwise.** No ABAP system was reachable: SAP BTP was unavailable ([ADR-002](../docs/adr/002-fully-local-landscape.md)) and the ABAP Platform Trial container needs 100 GB of disk against 62.7 GB free. Every file carries the marker in its header, and [`check_sources.py`](check_sources.py) fails if one loses it. There are no screenshots here and no claim of a running service.
>
> What **is** proven: the SQLScript inside `ZCL_AMDP_RUNRATE` is deployed as `NOVASPACE_L3.TF_PROGRAMME_RUNRATE`, runs against 1,122,588 journal lines, and matches an independent Python implementation to within €0.28 on an €800 m EAC. An AMDP's body *is* SQLScript and HANA executes it — ABAP is the wrapper. So the computation is real; the wrapper is source only.
>
> The working OData V4 service the Fiori app consumes is **CAP**, in [`../cap/`](../cap/), and is never presented as ABAP. Full reasoning: [ADR-003](../docs/adr/003-abap-evidence-strategy.md).

Structured as an abapGit export, so it imports directly the day a system exists.

## Check it

```bash
python abap/check_sources.py
```

106 checks across 21 sources. "It compiles" is unavailable as evidence here, and unverified code in a portfolio is worth close to nothing — so this checks what can be checked without a system:

- every `Z*` object referenced by another source exists
- every file carries the `NOT ACTIVATED` marker
- every object's declared name matches its filename, as abapGit requires
- the AMDP's table function exists, delegates correctly, carries `IF_AMDP_MARKER_HDB` and `OPTIONS READ-ONLY`, and its `returns` clause matches the columns the method actually selects, column for column
- no pseudonymous user column reaches an interface or consumption view

It is a linter, not a compiler. It rules out the embarrassing class of error — a view referencing something renamed, a file that quietly lost its label — and it is verified to fail on all four when they are injected deliberately.

## Objects

| Object | Type | Purpose |
|---|---|---|
| `ZTNS_JOURNAL` and five others | Tables | ACDOCA-shaped journal, programme, cost centre, G/L account, budget, fiscal periods |
| `ZI_GLAccount`, `ZI_CostCenter`, `ZI_Programme` | Interface views | Master data with texts, hierarchies and representative keys |
| `ZI_JournalEntry` | Interface view | Sign convention, manual flag, reporting period; master data via **associations, not joins** |
| `ZI_ActualsByPeriod` | Composite | Actuals aggregated to the grain budget is set at |
| `ZI_BudgetPhased` | Composite | Annual budget spread evenly across twelve periods |
| `ZI_BudgetVariance` | Composite | `FULL OUTER JOIN` of the two — spend without budget and budget without spend both survive |
| **`ZI_ProgrammeRunRate`** | **CDS table function** | Declares the AMDP's signature and result |
| **`ZCL_AMDP_RUNRATE`** | **AMDP class** | The SQLScript body: rolling run-rate and EAC, window function, code pushdown |
| `ZC_BudgetVariance`, `ZC_ProgrammeRunRate` | Analytical queries | `@Analytics.query` + `@UI` annotations for Fiori Elements |
| `ZSD_/ZSB_NOVASPACE_ANALYTICS` | Service definition + binding | OData **V4**, UI flavour |

## Three decisions worth defending

**Associations, not joins, in the interface views.** A consumer that needs the account group writes `_GLAccount.AccountGroup` and pays for one join; a consumer that does not, pays for nothing. A view built with joins makes every consumer pay for every attribute anybody might want.

**Criticality is computed in the model.** `VarianceCriticality` and `EACCriticality` are CDS expressions, not formatter logic. Thresholds live in one place and every client colours identically — the same argument BW makes when a restricted key figure renders the same way in every consumer. The CAP service and the UI5 dashboard both do this too, deliberately.

**Pseudonymous user IDs stop at the table.** `posting_user_id` and `manager_user_id` exist on the tables and are exposed by nothing above them. User-level attribution is an audit function, not a management-reporting one. The checker enforces it rather than trusting anyone to remember.

## What this is not

- Not activated, not compiled, not tested against a system.
- No RAP behaviour definitions, no transactional app — this is an analytical stack.
- No abapGit round-trip against a live system, so the XML serialisations (`.srvb.xml`, `.devc.xml`) are hand-written to the documented format rather than exported from one.

The defensible interview position is direct: the logic was proven where it actually executes, the ABAP was written correctly and is ready to activate, and the reason it was not activated is 62.7 GB of free disk against a 100 GB requirement — stated with the numbers, not hedged.
