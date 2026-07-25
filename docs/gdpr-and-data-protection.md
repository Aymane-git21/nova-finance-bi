# GDPR & data protection

**All data in this repository is synthetic. Nothing here is personal data.** This document is about the design, because the design is what would matter if it were.

---

## Where personal data enters finance BI

Finance reporting feels impersonal and is not. Three routes in:

| Source | Example | Risk |
|---|---|---|
| **Posting user** | Who entered a journal line | The main one. Every posting carries an author |
| **Approver / workflow** | Who released a document | Same shape, plus a hierarchy |
| **Cost-centre manager** | Master-data responsibility | Small volume, long retention |

The risk is not that a name is stored. It is that a report which was built to measure a *process* becomes a report that measures a *person*, without anyone deciding to make it one. "Late postings by user" is one drill-down away from "which of my staff is slow", and nobody has to intend it.

---

## How this design avoids it

**1. Pseudonymised at generation, not afterwards.** User identifiers are opaque tokens (`USR-4A91C3`) drawn directly from the seeded RNG. No name is ever generated, mapped or stored, so **no re-identification key exists** — not held elsewhere, not held securely, not held at all.

This is stricter than production pseudonymisation, where a reversible mapping is kept by design so authorised users can resolve an identity. That is a legitimate pattern; it is also a key that can leak. Worth being explicit that a real deployment would have one, and would have to protect it.

**2. Personal identifiers stop at the table layer.** `posting_user_id`, `manager_user_id` and `completed_by_user_id` exist on the base tables and are exposed by **nothing above them** — not L1, not L2, not L3, not the API layer, not the CDS views, not the service.

**3. Enforced in code, not by policy.** [`abap/check_sources.py`](../abap/check_sources.py) fails the build if any interface or consumption view references a pseudonymous column. A rule that depends on everyone remembering it is a rule that will be broken during the sprint when someone needs "just one drill-down".

**4. No user-level drill exists.** Not restricted by authorisation — absent from the model. The distinction matters: an authorisation can be granted under pressure by someone who does not understand why it was restricted. A column that was never modelled cannot be.

**5. The analytical unit is the entity and the process.** Every KPI in [`kpi-definitions.md`](kpi-definitions.md) reports at entity, period, cost centre or programme grain. None reports at user grain, and that is a design constraint rather than an oversight — see [`change-management.md`](change-management.md) for why it is also the thing that keeps the data honest.

---

## Retention

Aligned with the eco-design policy in [`performance-report.md`](performance-report.md), because they want the same thing for different reasons: keep less data.

| Tier | Retention | Rationale |
|---|---|---|
| Line-item grain with user attribution | 24 months | Audit and dispute window |
| Line-item grain without user attribution | 7 years | Statutory retention for accounting records |
| Period aggregates | Indefinite | Carry no personal data at any point |

**The important line:** user attribution ages out *before* the accounting record does. Statutory retention applies to the transaction, not to who typed it. Keeping the two on one clock is the common mistake, and it retains personal data for seven years for no legal reason.

---

## What a real deployment would have to add

Stated because their absence here is a property of a synthetic dataset, not a claim that they are unnecessary:

- **DPO involvement before go-live.** Not a review at the end — a design input. Any deployment touching real posting data goes through them.
- **A record of processing activity** naming purpose, legal basis, categories, recipients and retention.
- **Legal basis.** Most likely legitimate interest for process monitoring, which requires a balancing test that has to be written down.
- **Data subject rights.** Access and erasure requests reaching a warehouse are harder than reaching a source system, because the data has been copied, aggregated and cached. Design for it or discover it under a deadline.
- **Cross-border transfer assessment.** Four entities in four countries; a group warehouse is a transfer.
- **Works council consultation.** In Germany and France, monitoring that could measure employee performance is a co-determination matter. NS30 is the German entity and is also the one this cockpit shows as slowest — that is exactly the case a works council exists to scrutinise.

---

## Interaction with export control

Distinct from GDPR and lands on the same reports. Aerospace technical data is regulated under EU dual-use rules and, where US content is involved, ITAR/EAR. Programme-level cost detail can carry classified technical information — a cost breakdown can reveal capability.

Two consequences for this design:

- **Who may see which programme's data becomes a compliance control**, not a preference. It sits on the same mechanism as row-level security, which is why analysis authorisations matter beyond convenience ([`bw4hana-mapping.md`](bw4hana-mapping.md)).
- **The JV carve-out re-cuts it.** Programmes moving to the joint venture change who is permitted to see what, and the classification question has to be answered before the authorisation model is rebuilt, not after.

Not legal advice, and not a judgement any BI team should make alone. Real cases go to the export-control officer. The BI team's job is to know the question exists and raise it early enough to matter.
