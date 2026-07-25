# Architecture decision records

One file per significant decision. Terse by design: context, decision, consequences.

Naming: `NNN-short-slug.md`, numbered in the order decisions were taken. Superseded ADRs are never deleted — they get a `Superseded by ADR-NNN` line in their status field, because the reasoning that was later overturned is itself part of the record.

Use [`000-template.md`](000-template.md) as the starting point.

| ADR | Decision | Status |
|---|---|---|
| [001](001-landscape-choice.md) | BTP landscape: PAYG free-tier over trial | **Superseded by 002** |
| [002](002-fully-local-landscape.md) | Fully local landscape: HANA Express, no BTP | Accepted |
| [003](003-abap-evidence-strategy.md) | ABAP evidence: executed SQLScript, authored ABAP, CAP service layer | Accepted |
| [004](004-consumption-layer-without-sac.md) | Consumption layer is Fiori/UI5, not SAC | Accepted |
| [005](005-published-interface-layer.md) | A published interface layer between the model and its consumers | Accepted |
| 006 | Materialisation strategy for reporting aggregates | Planned (Phase 7) |

ADR-001 was superseded within hours of being written. That is not a failure of the record — it is the record working. The decision it documents was sound on its own terms and was defeated by an external access barrier it could not have priced in. Keeping it, rather than editing it away, is what makes the pair readable: 001 shows the reasoning, 002 shows what the world did about it.
