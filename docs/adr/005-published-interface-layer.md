# ADR-005: A published interface layer between the model and its consumers

- **Status:** Accepted
- **Date:** 2026-07-25
- **Related:** [ADR-004](004-consumption-layer-without-sac.md)
- **Deciders:** Solution architect (project author)

## Context

The CAP service needed to read the L3 reporting views. It could not.

Every identifier in L1–L3 is **quoted lower case** — `"company_code"` — because the source CSVs are lower case and keeping the loader, the harmonised layer and the reporting layer consistent with them made all three readable. CDS emits **unquoted** identifiers, which HANA folds to upper case, so a CAP entity looking for `COMPANY_CODE` cannot see `"company_code"`.

A purely mechanical problem, with a purely mechanical fix: alias the columns somewhere. The question was *where*, and that turned out to be an architectural decision rather than a formatting one.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A — Rewrite L1–L3 in upper case** | No extra layer. One naming convention throughout | Touches every view and the loader, and re-verification of all 24 cross-checks. Solves the mechanical problem and adds nothing else |
| **B — Alias inside the CAP model** | No database change | Puts the mapping in the consumer. A second consumer repeats it, and the two drift. Exactly the duplication the layering exists to prevent |
| **C — A published interface layer in the database** | Fixes the mechanics once, in one place. Gives consumers a contract to bind to that is decoupled from internal modelling | One more layer to keep in step. Risks becoming a dumping ground for logic that belongs in L2 |

## Decision

Option C. **`NOVASPACE_API` holds one interface view per consumable entity, containing aliasing and presentation-support columns only.**

Consumers bind to `NOVASPACE_API`. Nothing binds to L3 directly.

The layer also carries the **criticality columns** — `VARIANCE_CRITICALITY`, `EAC_CRITICALITY`, `CLOSE_CRITICALITY`. These are not aliases, and putting them here was deliberate: a threshold is a business rule, and a business rule computed in a JavaScript formatter is a business rule that differs between clients. Computed once in the database, the Fiori dashboard, the CAP annotations and any future consumer all colour identically.

## Consequences

**Easier.** L3 can be refactored — views split, columns renamed, grains changed — and as long as the interface projections still resolve, no consumer breaks. That is the same job an Open ODS View or a published BW query does in a BW landscape, and having the boundary makes the refactoring conversation possible at all.

Colour thresholds live in one place. The UI formatter maps a number to a `ValueState` and contains no judgement.

**Harder.** One more layer to keep in step, and a real risk of becoming a junk drawer. The guard is the rule in [`../golden-rules.md`](../golden-rules.md): *if a calculation appears in the API layer, it is in the wrong layer*. Criticality is the sole deliberate exception, and it is named as an exception rather than allowed to set a precedent.

**Honest note.** This layer exists because of an upper-case/lower-case mismatch. It would be neater to claim it was designed as a contract from the start; it was not. It earns its place on the second reason, having been created for the first — which is a fair description of how a lot of good architecture actually arrives, and worth saying rather than retrofitting a cleaner story.

**Unresolved.** The service views in `06_cap_service_views.sql` (`ANALYTICSSERVICE_*`) sit in the same schema and are not part of the contract — they exist because CAP compiles service entities to database views and queries those. They are pure aliases with names dictated by CAP. Mixing them into `NOVASPACE_API` is untidy; a separate schema would be cleaner and was not worth the churn.
