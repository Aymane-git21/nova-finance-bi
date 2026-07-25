# Fiori / UI5 consumption layer

**Phase 5.** The headline demo: a freestyle SAPUI5 dashboard reading a frozen snapshot of the live OData V4 service.

## The demo

Deployed to GitHub Pages by [`.github/workflows/pages.yml`](../.github/workflows/pages.yml) on every push that touches `webapp/`. It opens with **no database, no service, no container and no network beyond the UI5 CDN** — which is the whole point. Trials expire, containers get stopped, laptops get rebuilt. A static page opens in an interview two years from now.

## Run it locally

```bash
cd fiori/webapp && python -m http.server 8099
```

Then open `http://localhost:8099/index.html`. Nothing else needs to be running.

To refresh the data from a live service (needs HANA Express and the CAP service up):

```bash
python fiori/snapshot.py
```

## What it shows

| Section | What a viewer should notice without being told |
|---|---|
| KPI tiles | The group closes in 6 working days against a target of 5, and one entity is dragging that average |
| **Programme burn** (bubble) | Nine programmes sit on the diagonal. One does not |
| Days to close (line) | The same entity is above the working-day-5 reference line, period after period, for three years |
| Actual vs budget (column) | Where the group is against plan, phased evenly |
| Intercompany table | Five pairs that do not reconcile above materiality |

The bubble chart is the one worth defending in an interview. Two ratios and a magnitude on one picture: horizontal is share of schedule elapsed, vertical is share of budget consumed, size is total budget. A programme on plan sits on the diagonal, and distance above it is the finding. `PRG-KESTREL` sits at **76 % of budget against 69 % of schedule**, and its EAC is 127 % of budget.

## Design notes

- **`sap.viz` VizFrame, hand-written.** Three charts configured in the controller rather than generated. Chart properties live in the controller, not the XML: forty lines of `vizProperties` in a view makes it unreadable for no benefit.
- **Criticality comes from the database.** `VARIANCE_CRITICALITY`, `EAC_CRITICALITY` and `CLOSE_CRITICALITY` are computed in `NOVASPACE_API`, so thresholds live in the model and every client colours identically. The formatter maps them to `ValueState` and nothing more.
- **`0` means "no value", not "good".** An open period has no days-to-close, and the UI renders it as absent rather than as a zero-day close. That case is in the data on purpose.
- **UI5 pinned to the `1.120` LTS line.** Patch-level CDN paths such as `/1.120.27/` return 404 — only the minor is served — so this is the most specific pin available. Resolves to 1.120.47 today.
- **Restrained on purpose.** One accent colour, generous whitespace, colour reserved for status. This is a page read in thirty seconds; the design job is hierarchy, not decoration.

## What is deliberately not here

Recorded so the omissions read as decisions:

- **No Fiori Elements Analytical List Page.** The CAP service carries the full `@UI` and `@Aggregation` annotation set to drive one ([`../cap/srv/analytics-service.cds`](../cap/srv/analytics-service.cds)), and it renders against the live service — but an ALP needs a running OData backend and cannot be frozen to static files. Hosting one artifact that always works beat hosting two where the better-looking one is usually broken.
- **No Excel workbook, no planning write-back.** Cut explicitly in [ADR-004](../docs/adr/004-consumption-layer-without-sac.md). One finished artifact beats three unfinished ones.

## Layout

| Path | Contents |
|---|---|
| `snapshot.py` | Freezes the OData service into `webapp/localData/*.json` |
| `webapp/index.html` | Standalone bootstrap, UI5 from CDN |
| `webapp/Component.js` | Loads one named JSON model per snapshot file |
| `webapp/manifest.json` | App descriptor |
| `webapp/view/Dashboard.view.xml` | The single view |
| `webapp/controller/Dashboard.controller.js` | Chart configuration and formatters |
| `webapp/i18n/i18n.properties` | All user-facing text |
| `webapp/css/style.css` | Theme overrides |
