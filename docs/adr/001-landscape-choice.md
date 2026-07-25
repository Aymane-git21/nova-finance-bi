# ADR-001: BTP landscape — Pay-As-You-Go with free-tier plans, not the trial

- **Status:** **Superseded by [ADR-002](002-fully-local-landscape.md)** — SAP BTP proved unreachable in practice. The reasoning below is kept intact because it is still correct on its own terms; what defeated it was an access barrier neither option could clear.
- **Date:** 2026-07-25
- **Superseded:** 2026-07-25
- **Deciders:** Solution architect (project author)

## Context

The project needs a SAP BTP account hosting SAP HANA Cloud, Business Application Studio and (later) an ABAP environment. Two entry routes exist, both costing €0 for this workload:

1. **BTP Trial account** — no billing details, one-click signup, everything preconfigured.
2. **BTP Pay-As-You-Go (PAYG) account with free-tier service plans** — credit card required at registration, entitlements assigned manually, free-tier plans billed at €0 until their quota is exceeded.

Three constraints shape the choice:

- **Lifetime.** The demo has to stay alive across an entire job hunt, not a fixed number of weeks. A dead landscape mid-application is a worse outcome than a slower signup.
- **Signup reliability.** Trial registration depends on a phone-verification service that is chronically unreliable and has blocked registrations for days at a time. It sits on the critical path of every subsequent phase.
- **Cost exposure.** Free-tier plans inside a PAYG account scale into billable usage once quota is exceeded, silently. This is a real risk that the trial does not have.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A — Trial account** | No billing details. Fastest path when it works. Hard ceiling: cannot generate a bill. | Dies after 90 days, taking the demo with it. Phone verification is a single point of failure with no workaround. HANA Cloud trial sizing (smaller than free tier) and periodic system resets. |
| **B — PAYG + free-tier plans** | No expiry — free-tier plans persist as long as the account does. HANA Cloud free tier is larger than the trial: 16 GB memory, 1 vCPU, 80 GB storage. Signup avoids the phone-verification path entirely. Mirrors how a real customer landscape is entitled and governed. | Credit card required despite €0 cost. Entitlements must be assigned manually before provisioning. Exceeding free-tier quota bills silently. |

## Decision

Take option B: a **Pay-As-You-Go account in an EU region** (EU10 Frankfurt or EU20 Netherlands), with **free-tier plans** entitled explicitly for SAP HANA Cloud (`hana-free`), HANA Schemas & HDI Containers (`hdi-shared`) and Business Application Studio.

Cost exposure is handled rather than accepted: **Consumption Monitoring is enabled with an email alert at ~70 %** as the first action after provisioning, and the plan selector is verified to read **free** — not the default paid plan — at every instance creation.

## Consequences

**Easier.** The landscape outlives the trial clock, so the demo stays live throughout the job hunt. HANA Cloud gets more memory and storage than the trial would give. Signup no longer depends on a flaky verification service, removing the highest-probability blocker from the critical path. Assigning entitlements by hand is itself worth doing once — a service that "looks unavailable" at provisioning time is almost always a missing entitlement, and knowing that is operational competence.

**Harder.** A credit card is on file, so cost discipline is now a real responsibility rather than a structural guarantee. An accidental second HANA instance on a paid plan would bill. The 70 % consumption alert and the plan-selector check are the two controls that make this acceptable; both are cheap and both must actually be in place.

**Revisit if.** SAP changes free-tier quotas or withdraws the free plan for HANA Cloud, or if the account approaches the 4 GB memory / 10 GB storage free-tier ceiling — at which point the retention and aggregation policy from Phase 7 becomes a cost control, not only an eco-design measure.

**Unaffected by this decision.** Free-tier HANA Cloud instances are still stopped nightly and deleted after 30 days of being stopped. That is a property of the free plan, not of the account type, and is handled operationally by `hana/start-instance.sh` plus keeping every source artifact in Git.
