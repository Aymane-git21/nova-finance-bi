# Architecture decision records

One file per significant decision. Terse by design: context, decision, consequences.

Naming: `NNN-short-slug.md`, numbered in the order decisions were taken. Superseded ADRs are never deleted — they get a `Superseded by ADR-NNN` line in their status field, because the reasoning that was later overturned is itself part of the record.

Use [`000-template.md`](000-template.md) as the starting point.

| ADR | Decision | Status |
|---|---|---|
| [001](001-landscape-choice.md) | BTP landscape: PAYG free-tier vs trial | Proposed (Phase 1) |
| 002 | ABAP environment: BTP trial vs local Docker | Planned (Phase 4) |
| 003 | SAC data acquisition: import vs live | Planned (Phase 6) |
| 004 | Materialisation strategy for reporting aggregates | Planned (Phase 7) |
