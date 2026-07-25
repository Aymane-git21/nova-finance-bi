# ADR-003: ABAP evidence strategy — executed SQLScript, authored ABAP, CAP for the service layer

- **Status:** Accepted
- **Date:** 2026-07-25
- **Related:** [ADR-002](002-fully-local-landscape.md)
- **Deciders:** Solution architect (project author)

## Context

[ADR-002](002-fully-local-landscape.md) removed BTP from the architecture, which also removed the BTP ABAP Environment. ABAP is the harder loss of the two, because the target role lists ABAP as highly recommended and CDS/OData as desirable — this is the phase carrying the most weight per hour invested.

The local ABAP fallback the roadmap anticipated does not fit this machine:

| | Requirement | This machine |
|---|---|---|
| ABAP Platform Trial (Docker) | ~50 GB image, **100 GB minimum** total, 200 GB recommended | **62.7 GB free** of 475.9 GB |

Freeing 40–60 GB is conceivable but leaves no headroom, and the container would then contend for RAM with HANA Express, which the same machine also has to host. Two SAP systems on 19.3 GB is not a working setup.

So no ABAP system is reachable. The question is what honest evidence can still be produced, and the answer turns on decomposing what "ABAP evidence" actually consists of:

1. **The pushdown logic** — the rolling-3-month run-rate and EAC. In an AMDP this is a SQLScript body with a window function, executed by HANA. *The ABAP system never executes it; HANA does.*
2. **The ABAP wrapper** — the class, the method signature, `BY DATABASE PROCEDURE FOR HDB`, the CDS table function binding. This genuinely needs an ABAP system to activate.
3. **The CDS view stack** — associations, `@Semantics`, `@Analytics.query`, `@UI` annotations. Needs an ABAP system to activate, but the *modeling concepts* have a working equivalent elsewhere.
4. **The OData V4 service** — a service definition and binding. Needs an ABAP system, but OData V4 is a protocol, not an ABAP feature.

Point 1 is the insight that shapes this decision. **An AMDP's body is SQLScript, and SQLScript runs on HANA Express.** The most technically interesting artifact in Phase 4 does not actually require ABAP to execute — only to wrap.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A — Park Phase 4 until an ABAP system appears** | Nothing misleading gets published. | Leaves the highest-weight requirement with zero evidence for an unbounded period. Also strands Phase 5, which needs an OData V4 service to consume. |
| **B — Commit unactivated ABAP source only** | Cheap. The ABAP is real ABAP. | Code that has never been activated is weak evidence and any competent interviewer will ask whether it compiles. Produces no working service, so Phase 5 still has nothing to consume. |
| **C — Substitute CAP entirely and drop ABAP** | Clean, fully working, locally runnable. | CAP CDS is a different dialect with a different runtime. Presenting it as ABAP evidence would be dishonest, and dropping ABAP concedes the posting's strongest requirement. |
| **D — Split by layer: execute what can execute, author what cannot** | Every component sits at the strongest honesty level available to it. Produces a working OData V4 service today, so Phase 5 is unblocked. | Three artifacts to keep synchronised. Requires disciplined labelling so nothing reads as more proven than it is. |

## Decision

Take option D, splitting Phase 4 by what each layer can honestly claim:

1. **The run-rate/EAC SQLScript is executed for real.** It is deployed to HANA Express as a table function, is unit-tested against expected values, and is benchmarked in Phase 7. The pushdown logic is genuinely proven, not asserted.
2. **The ABAP layer is authored, not activated.** `ZCL_AMDP_RUNRATE` wraps the *identical* SQLScript body already proven in step 1. The `ZI_*` / `ZC_*` CDS stack is written with its full annotation set. All of it is committed under [`abap/`](../../abap/) and labelled **`NOT ACTIVATED — no ABAP system available, see ADR-003`** in a header comment in every file and in `abap/README.md`. No screenshot, no claim of a running service.
3. **The consumable service layer is CAP.** `@sap/cds` runs locally on Node with no meaningful footprint and produces a genuine OData V4 service with annotation-driven metadata, which Phase 5's Fiori Elements app consumes for real. It is labelled as CAP throughout and never described as ABAP.

The mapping between the CAP CDS and the ABAP CDS — what transfers and what does not — is documented alongside the sources, in the same spirit as [`docs/bw4hana-mapping.md`](../bw4hana-mapping.md). That document is itself the evidence of understanding both stacks rather than one.

## Consequences

**Easier.** Phase 5 is unblocked immediately: there is a real OData V4 service to build against, so the Fiori Elements app and the GitHub Pages demo proceed on schedule. The most interesting piece of Phase 4 — SQLScript pushdown with a window function — becomes *more* proven than the original plan, because it is executed and benchmarked on HANA rather than merely activated in a trial system that would later be reset.

**Harder.** Three representations of the same model must stay consistent: HANA views, CAP CDS, ABAP CDS. Drift between them is the obvious failure mode, and the mapping document is the control against it. The labelling discipline is non-negotiable — one unlabelled ABAP file that reads as activated would undermine the credibility of everything else in the repository.

**Honestly lost.** No activated ABAP, no RAP, no running ABAP OData binding, no abapGit round-trip against a live system. The repository says exactly this rather than implying otherwise. The defensible position in an interview is direct: the logic was proven where it actually executes, the ABAP was written correctly and is ready to activate, and the reason it was not activated was hardware, not capability — stated plainly, with the disk numbers.

**Revisit if.** An ABAP system becomes reachable — BTP support opening the account, or a machine with 200 GB free and more RAM. Activation is then a short task rather than a rewrite, because the source already exists and the SQLScript inside it is already proven. That is the entire point of authoring it now.
