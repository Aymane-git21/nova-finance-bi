# Fiori / UI5 consumption layer

**Built in Phase 5.**

## Planned contents

- **Fiori Elements Analytical List Page** on `ZC_BudgetVariance` — zero-code first version driven purely by CDS annotations, then one extension-point customisation.
- **One freestyle SAPUI5 view** with a `sap.viz` VizFrame: the programme burn bubble chart — % budget consumed (y) × % time elapsed (x), bubble size = programme budget. Anything above the diagonal is overspending. Hand-coded, not generated.

## Permanence

Trials die; demos should not. The app is built with `ui5 build` against a **mock server** holding a frozen JSON snapshot of the OData responses, and the static build is hosted on GitHub Pages. The demo stays clickable after every backend trial expires, clearly labelled as a mock-data snapshot.
