# ADR-002: Fully local landscape — SAP HANA Express, no BTP

- **Status:** Accepted
- **Date:** 2026-07-25
- **Supersedes:** [ADR-001](001-landscape-choice.md)
- **Deciders:** Solution architect (project author)

## Context

[ADR-001](001-landscape-choice.md) chose a BTP Pay-As-You-Go account with free-tier plans over the BTP trial, on the reasoning that the trial's phone verification was an unreliable single point of failure. That reasoning held. What it did not anticipate is that **both** routes would be closed at once:

- **PAYG route:** registration does not self-serve. SAP directs the applicant to contact support for account access — an open-ended wait with no committed turnaround.
- **Trial route:** blocked at phone verification. The verification service itself is down — not a data-entry problem, not a browser/cookie problem, both of which were eliminated before concluding this.

Neither is a defect in ADR-001's analysis; both are access barriers upstream of the decision it was making. The barrier landed on a weekend, so even the support path could not start moving for days.

The situation this creates is worth naming precisely: **the entire project was blocked on an external party's uptime, for an unbounded duration, at the start of the build.** That is a supply risk, and the correct response to a supply risk is to remove the dependency rather than to wait on it.

Two facts reframed the choice:

1. **The only genuinely BTP-bound phases were 3 (HANA) and 4 (ABAP).** Phases 2, 5, 6, 7, 8 and 9 never needed it. The blocker looked total but covered roughly a quarter of the build.
2. **SAP HANA, express edition is the same database.** Column store, SQLScript, table functions, calculation views, HDI — free, permanent, self-hosted. Measured against this machine (19.3 GB RAM, 6c/12t): the server-only Docker image needs 8 GB minimum and 12 GB recommended, which fits. The full image with XS Advanced needs 16–24 GB and does not.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A — Wait for SAP support** | Eventually yields the landscape ADR-001 specified. No rework. | Unbounded delay on the critical path, starting on a weekend. The SAC trial clock is already running, so waiting burns a resource that cannot be refilled. Bets the project on someone else's queue. |
| **B — Fully local: HANA Express + local consumption stack** | Available immediately. **Permanent** — no nightly stop, no 30-day deletion rule, no 90-day expiry, no credit card. Identical database engine, so every skill and artifact transfers. Removes the external dependency outright. | No XS Advanced at 19.3 GB RAM, so no browser calc-view editor: L3 views are authored as `.hdbcalculationview` design-time artifacts and deployed via `@sap/hdi-deploy`. Local ABAP is separately impossible on disk — see [ADR-003](003-abap-evidence-strategy.md). Setup friction is front-loaded. |
| **C — Hybrid: build local, migrate to BTP when it opens** | Keeps both doors open. | Pays option B's setup cost *and* option A's wait, then adds a migration. Two landscapes to keep honest in the documentation. The migration buys nothing: the artifacts are already portable. |

## Decision

Take option B. **The landscape is local and permanent: SAP HANA, express edition (server-only) in Docker, with the consumption layer built on local tooling.** BTP is dropped from the architecture rather than kept as a pending dependency.

L1 and L2 are SQL views and table functions. L3 is authored as genuine `.hdbcalculationview` HDI artifacts and deployed with `@sap/hdi-deploy`, so the calculation-view modeling evidence is real design-time source in Git rather than clicks in an editor that no longer exists in this setup.

## Consequences

**Easier.** The demo outlives every trial clock, including ones not yet started, because there is no clock. The nightly-restart babysitting that free-tier HANA Cloud would have required disappears, and with it the 30-day deletion risk that sat at the top of the roadmap's risk register. Nothing in the portfolio can expire while an application is in flight. Authoring calculation views as design-time XML rather than through a graphical editor produces stronger evidence, not weaker: the artifacts are diffable, reviewable and in Git.

**Harder.** No graphical modeling tools, so calculation views are hand-authored — slower, and a genuine learning curve. HANA Express must be running locally before any modeling work, competing for RAM with everything else on the machine. The container's data volume and its disk growth are now an operational concern that belongs to this project rather than to SAP.

**Lost.** No hands-on evidence of the BTP cockpit itself: entitlements, service instances, Cloud Foundry spaces, consumption monitoring. This is a real gap against a posting that lives on BTP. It is mitigated, not closed, by ADR-001 remaining in the repository — it documents the entitlement model, the free-tier quotas and the cost-guardrail reasoning in enough detail to hold a conversation about them, while being honest that the account was never provisioned.

**Revisit if.** SAP support opens the PAYG account, or phone verification recovers and the trial becomes reachable. At that point the migration is cheap by construction — HDI artifacts deploy to HANA Cloud unchanged, and the loader script only needs new connection parameters. The decision to drop BTP is therefore reversible at low cost, which is the main reason it is safe to take now.
