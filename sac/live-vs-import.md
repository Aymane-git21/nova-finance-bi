# Live connection vs import: when each is right

Written without a tenant. SAC became unavailable before the story was built ([ADR-004](../docs/adr/004-consumption-layer-without-sac.md)), but the decision this note describes is an architecture decision, not a product feature, and it does not need a tenant to reason about.

**The short version:** live is the default for anything reporting on governed enterprise data. Import is a legitimate choice for a bounded set of cases, and picking it by accident — because the trial only offered import — is how a demo architecture quietly becomes a production one.

---

## The two models

| | **Live connection** | **Import (acquired data)** |
|---|---|---|
| Where the data sits | Stays in the source. SAC issues queries | Copied into SAC's own store |
| Freshness | Whatever the source has, now | As of the last load |
| Security | **Inherited from the source** | Re-implemented in SAC |
| Volume ceiling | The source's | SAC's model limits |
| Offline / scheduled | Not applicable | Works |
| Planning | Limited | **Required** for full planning |
| Blending across sources | Constrained | Flexible |

---

## Why live wins for this cockpit

**1. Security is inherited rather than rebuilt.** This is the argument that matters most and gets the least attention. On a live connection, a user authorised for company code NS20 in BW sees NS20 rows, because the source evaluates the authorisation. On import, that model is **rebuilt inside SAC** — and now there are two definitions of who may see what, maintained by two teams, drifting.

For NovaSpace this is not hypothetical. The Space JV carve-out re-cuts entity authorisations, and export-control classification governs who may see programme-level cost detail ([`../docs/gdpr-and-data-protection.md`](../docs/gdpr-and-data-protection.md)). A second copy of that model is a second place to get it wrong, and the failure is silent: nobody notices they can see too much.

**2. No replication means no reconciliation.** Every import introduces the question "why does SAC say something different from the source?", and the answer is almost always load timing. That question consumes real analyst hours and erodes trust in the tool faster than any missing feature.

**3. Freshness matches the use case.** A close cockpit is used *during* the close, when the numbers change hourly. A dashboard refreshed at 06:00 is answering yesterday's question at exactly the moment it matters most.

**4. No volume ceiling.** 1.12 M journal lines is small for HANA and large for an import model. The aggregate extracts in [`extracts/`](extracts/) are ~50 KB precisely because they were pre-aggregated to fit — which means the drill-down stops where the aggregation stopped.

---

## When import is genuinely right

Not a fallback. There are cases where it is the correct choice:

- **Planning.** SAC Planning needs writeback, versions and data actions against its own store. This is the big one, and it is why a real landscape usually runs **both**: live models for reporting, an import model for planning, with actuals loaded into the planning model on a cycle.
- **Sources that cannot serve interactive queries.** A flat file, a survey export, a partner's monthly submission.
- **Blending across systems** with no common semantic layer, where doing the join in SAC beats building a warehouse object for a one-off.
- **A source that cannot take the load.** An ERP already at capacity does not need an analytics workload on top.
- **Point-in-time snapshots** that must not change — a board pack that has to show what was known on the day.

---

## What this project actually did, and why it is not the recommendation

The extracts in [`extracts/`](extracts/) are import-shaped: pre-aggregated, pre-joined, signs applied, budget already phased. That was forced — the SAC trial offers no live connection to a local HANA Express instance, and there is no route around it.

**So the architecture here is import-only for a reason that would not apply in production**, and that is worth being explicit about rather than presenting the constraint as a design.

If NovaSpace ran this for real:

| Layer | Acquisition | Why |
|---|---|---|
| Close monitor, P&L, programme controlling | **Live** to BW/4HANA or HANA | Freshness during the close, inherited security, no reconciliation |
| Planning model | **Import**, with actuals loaded on a cycle | Writeback requires it |
| Board snapshots | **Import**, deliberately frozen | Must not change after the fact |

---

## The question to ask

When someone proposes an import model for enterprise reporting, one question settles most of it:

> **Who maintains the authorisation model, and how do we know the two copies agree?**

If the answer is "we'll replicate the roles", the follow-up is what happens when the source's roles change. If there is no answer, the model should be live.
