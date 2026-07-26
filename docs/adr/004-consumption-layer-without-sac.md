# ADR-004: The consumption layer is Fiori/UI5, not SAP Analytics Cloud

- **Status:** Accepted; **partially revisited 2026-07-26** — see the note at the end
- **Date:** 2026-07-25
- **Related:** [ADR-002](002-fully-local-landscape.md), [ADR-003](003-abap-evidence-strategy.md)
- **Deciders:** Solution architect (project author)

## Context

SAC was to be the reporting and planning layer: a three-page story and a planning-enabled model, captured as screenshots and video before the trial expired. The trial was registered on 2026-07-25 specifically so the clock would start once the data was ready.

**The tenant then became unavailable.** This follows SAP BTP being unreachable by both routes ([ADR-002](002-fully-local-landscape.md)) and no ABAP system being obtainable ([ADR-003](003-abap-evidence-strategy.md)). Three of the four SAP-hosted services this project planned to use were unavailable within the same weekend.

At that point the pattern is the signal. The problem is not any individual outage — it is that **the demonstrable parts of this project kept being the parts that depended on somebody else's uptime**. Everything built locally has worked continuously: HANA Express, 1.12 M rows, 21 views, 103 tests, 24 cross-checks. Everything hosted has not.

A fourth attempt to route around a hosted service would be repeating a strategy that has now failed three times.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A — Wait for SAC to return** | Delivers the requirement as written; SAC is named explicitly in the posting | Unbounded wait, and the trial clock keeps running while the tenant is unreachable. Betting the most visible deliverable on the same class of dependency that has already failed three times |
| **B — Excel on the OData service** | Fast; Power Query and Power Pivot are already installed; closest analogue to the Analysis-for-Office population the posting names | An Excel workbook is hard to show in a portfolio — it needs opening, it needs the service running, and it screenshots badly. Strong as a second artifact, weak as the headline |
| **C — Fiori Elements + freestyle UI5, hosted** | Permanent, clickable URL that outlives every trial. Exercises Fiori, UI5, OData V4 and CDS annotations, all named in the posting. Self-contained: nothing to spin up before a demo | Does not evidence SAC or BPC, both explicitly required. More build effort than B |
| **D — C plus Excel plus planning write-back** | Widest requirement coverage | Three half-finished artifacts is a worse portfolio than one finished one, and the effort is not available |

## Decision

**Option C. The consumption layer is a Fiori Elements Analytical List Page plus one freestyle SAPUI5 chart, served by a CAP OData V4 service over HANA Express, and deployed to GitHub Pages against a frozen mock-data snapshot.**

Excel and planning write-back are explicitly *not* built. One finished artifact beats three unfinished ones, and the scope that was cut is recorded here rather than left as a silent gap.

The SAC and BPC requirements are addressed in [`../sac-and-bpc.md`](../sac-and-bpc.md): what each would have provided, which substitute meets which requirement, and the concept mapping needed to hold the conversation in an interview.

## Consequences

**Easier.** The headline demo becomes a URL that works forever, with no tenant to provision, no clock, and nothing to start before showing it. That is a better artifact than a screen recording of a trial that has since expired — it can be opened during an interview, and it will still open in a year.

**Harder.** Fiori Elements and a hand-written VizFrame are more work than assembling an SAC story from a model. The annotation-driven approach only pays off if the CDS annotations are right, so effort moves from designing a story to modelling a service.

**Honestly lost.** No hands-on SAC, and therefore no SAC Planning, and therefore no live BPC-equivalent. Both are named requirements. There is no substitute that makes this untrue, and the repository says so plainly rather than implying a near-equivalent. What remains is the ability to talk about both accurately — which is what the concept mapping is for, and which is worth considerably less than having built them.

**On the pattern.** Three constraint records in one project could read as a list of excuses. The guard against that is that each one is paired with something that was actually delivered and verified, and that the repository leads with the built and tested work rather than with what blocked it. A reader who only looks at outcomes sees a loaded database, a verified view stack and a hosted demo; the constraint records explain the shape of what they are looking at, and are deliberately short.

**Revisit if.** SAC returns and more than three weeks remain on the trial. The curated extracts in [`../../sac/extracts/`](../../sac/extracts/) are already built and unchanged, so the reporting story remains roughly a weekend's work whenever the tenant is reachable.

---

## Revisit note — 2026-07-26

**The tenant came back on day 1 of the trial, so the condition above is met with 29 days on the base clock and 89 if extended.** The SAC work proceeds.

What this does *not* change: the decision itself stands. The Fiori/UI5 dashboard remains the headline artifact, because the reason for choosing it was never that SAC was unavailable — it was that a hosted static page cannot expire and an SAC trial always will. SAC is now an addition, not a replacement.

What it does change: the "not demonstrated" verdicts in [`../sac-and-bpc.md`](../sac-and-bpc.md) and the requirements table in the README become wrong once the story is built, and both are flagged for rewrite in [`../../sac/build-guide.md`](../../sac/build-guide.md). They stay as they are until there are screenshots to back the change — a requirements table updated on the strength of an intention is exactly the kind of claim this project has avoided.

Excel and planning write-back **stay cut**. SAC returning does not create time, and the reasoning in this ADR about three unfinished artifacts is unaffected.
