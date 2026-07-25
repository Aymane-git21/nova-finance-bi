# Native HANA ↔ BW/4HANA mapping

This project is built natively on SAP HANA, not on BW/4HANA. The architecture is nevertheless **LSA++ transplanted onto native HANA**, deliberately, so that every object has a BW/4HANA counterpart and the design conversation can happen in either vocabulary.

This document is the translation table. It also states, honestly, what BW/4HANA would give you here that a native build does not — because the interesting part of the comparison is the gap, not the similarity.

---

## Why layers at all

LSA++ (Layered Scalable Architecture) exists because a warehouse with one layer becomes unmaintainable at the first change of source. Its answer is a lean staging layer, a harmonisation/propagation layer, and virtual reporting marts on top.

That reasoning does not depend on BW. It applies to any warehouse, which is why the same three layers appear here on plain HANA with the same names and the same rules.

| Layer here | Schema | BW/4HANA analogue | Rule |
|---|---|---|---|
| **L1 RAW** | `NOVASPACE_L1` | Staging / inbound ADSO (write-optimised) | Projection and typing only. No joins, no filters, no derived columns |
| **L2 HARMONISED** | `NOVASPACE_L2` | Standard ADSO with transformations | All business logic. Master-data joins, currency translation, derived flags |
| **L3 REPORTING** | `NOVASPACE_L3` | CompositeProvider + BEx query elements | Star-joined, aggregated, cube semantics. The only layer a report touches |

The L1 restraint is the part worth defending in an interview: **when a number is wrong, L1 is the layer you can eliminate without reading it**, because there is nothing in it capable of being wrong. Every hour that discipline saves during an incident is an hour it earns back.

---

## Object-by-object

### Storage and staging

| This project | BW/4HANA equivalent | Why the layer exists | What differs in a real BW/4 system |
|---|---|---|---|
| `NOVASPACE_RAW.*` column tables | **Write-optimised ADSO** (inbound) | Landing zone for inbound data, unchanged from source | BW manages activation, request handling and an error stack. A failed load is a *request* you can roll back; here a failed load is a table you truncate and re-run |
| `NOVASPACE_L1.V_*` views | **Inbound ADSO** exposed for reporting | Stable column contract so a source change is absorbed in one place | In BW the ADSO *is* both the persistence and the interface; here persistence and interface are separated, which costs an object and buys a rename-safe boundary |
| `NOVASPACE_L2.V_JOURNAL` | **Standard ADSO** fed by a transformation | Business logic in exactly one place | BW would persist this. Here it is virtual — recomputed on every query. See *Persistence* below, which is the single biggest architectural difference |
| `NOVASPACE_L3.CV_*` | **CompositeProvider** | The query-facing object; joins and unions the layer below | A CompositeProvider is modelled graphically over InfoProviders and inherits their metadata; a SQL view inherits nothing and re-declares everything |

### Master data and hierarchies

| This project | BW/4HANA equivalent | Why | What differs |
|---|---|---|---|
| `DIM_COST_CENTER` with `parent_id` + denormalised levels | **InfoObject** with a *standard hierarchy* | Cost-centre rollup is the backbone of management reporting | BW hierarchies are versioned, time-dependent, and understood natively by the query engine — a BEx query can aggregate to any node without SQL. Here, recursion is the consumer's problem |
| `DIM_GL_ACCOUNT` with `account_group` / `pl_section` | **InfoObject** with attributes and a hierarchy | P&L structure | BW enforces master-data governance: an attribute change is a versioned master-data load, not an `UPDATE` |
| `DIM_PROGRAMME` | **InfoObject**, WBS-element-like | Programme is the account-assignment object | Real WBS elements come from PS with their own hierarchy and status management |
| `DIM_DATE` | **Time characteristics** (`0FISCPER`, `0CALDAY`, …) | Fiscal calendar and working-day arithmetic | BW ships time characteristics and fiscal year variants as standard content. Building `DIM_DATE` by hand is work BW would simply have done — including per-country factory calendars, which this model simplifies to one group-wide calendar |
| `NOVASPACE_L2.V_DATE.working_day_seq` | A **factory calendar** in the ABAP stack | Turns "working days between" into a subtraction | BW/ABAP would call `FACTORYCALENDAR_GET`. The window-function trick here is an honest substitute, not an improvement |
| — | **SID** (surrogate ID) tables | — | BW converts characteristic values to integer SIDs, which is why its joins are fast and its master data is governed. There is no equivalent here; joins go on the natural keys |

### Transformation and loading

| This project | BW/4HANA equivalent | Why | What differs |
|---|---|---|---|
| `hana/load_data.py` (`hdbcli`, batched `executemany`) | **DTP** (Data Transfer Process) | Moves data from file into the warehouse | This is the biggest simplification in the project. A DTP has filtering, packet sizing, parallelism, error handling with a stack, and — the important one — **delta handling**. The loader here is full-load only |
| L2 view expressions | **Transformation** with rules and routines | Signed amounts, flags, currency translation | BW transformations are graphical with ABAP/AMDP routines for the hard parts, and are versioned as transport objects |
| Currency translation in `V_JOURNAL` | **Currency translation type** on the InfoObject/query | KPI-06 needs both rate types | BW has first-class currency translation: translation types reference `TCURR`, rate types and a reference date, and the query applies them. Here it is a join and a multiplication that has to be right in every view that does it |
| Full CSV reload | **Delta DTP**, or SLT / SDI replication | — | Production would never full-load a 1.1M-line journal daily. Real options: SLT for trigger-based real-time replication from the ERP, SDI for transform-on-replicate, SDA for pure virtual access. Named here because "how would this get its data for real" is the first question worth asking of any demo warehouse |

### Query semantics

| This project | BW/4HANA equivalent | Why | What differs |
|---|---|---|---|
| Conditional `SUM(CASE WHEN …)` in `CV_PL_ACTUALS` | **Restricted key figure** | "Personnel cost, manual postings only" as a column, not a consumer's `WHERE` clause | Identical in intent. BW defines it once in the query and every client inherits it; here every consumer must use the view rather than the layer below |
| `variance`, `variance_pct` in `CV_BUDGET_VARIANCE` | **Calculated key figure** | Derived measures | Same idea. BW computes after aggregation by default, with explicit control over aggregation order — a subtlety this SQL has to handle by hand, and the reason `variance_pct` is computed from summed components rather than averaged |
| `TF_PROGRAMME_RUNRATE(year, period, window)` input parameters | **Query variable** | Query-time prompts | BW variables have types (single, interval, hierarchy node), processing modes (user entry, SAP exit, authorisation) and default values. A table-function parameter has none of that |
| `NULL` `days_to_close` on an open period | **Null vs zero suppression** | An open period is open | BW distinguishes "no value" from "zero" in the query and can suppress either. Same discipline, enforced by convention here rather than by the tool |
| — | **Analysis authorizations** | — | See *Security* below |

---

## The four differences that actually matter

Everything above is mapping. These are the ones that change what the system can do.

### 1. Persistence — the biggest one

L2 here is **virtual**: a view, recomputed on every query. In BW/4HANA it would be a **persisted standard ADSO**, activated once per load.

- **Virtual wins** on freshness and storage: no duplicate data, no activation window, no staleness.
- **Persisted wins** on cost of repeated reads: the transformation runs once, not per query, and downstream queries hit a table rather than a join tree.

At this volume virtual is correct and the join tree resolves quickly. At production volume with dozens of concurrent users it inverts, and that is exactly the tradeoff Phase 7 measures with real numbers rather than asserting from a diagram. The materialisation decision belongs in an ADR precisely because it is not obvious in either direction.

### 2. Delta handling

This project full-loads. BW's delta machinery — request management, the ability to roll a bad load back, the change-log that makes a delta possible at all — has no counterpart here, and building one properly is a substantial project in its own right. Anyone who claims a native-HANA warehouse is simply "BW without the overhead" has not had to reload a failed request at 3am.

### 3. Security

BW has **analysis authorizations**: row-level security expressed in the same characteristic values the model already uses, evaluated by the query engine, and auditable as its own object. A user authorised for company code NS20 sees NS20 rows in every query, without any query being written differently.

Native HANA gives analytic privileges, which cover the same ground with far less governance around them. In a JV or carve-out — where "which entity's data may this person see, and can we prove it" becomes a legal question rather than a technical one — that governance is the entire point. This is worth flagging for the September 2026 Space JV context: system separation, data ownership and export-control classification all land on exactly this mechanism.

### 4. Standard content

BW/4HANA ships extractors, InfoObjects and transformations for SAP source systems. A finance warehouse over S/4HANA starts from working content, not from an empty schema. Everything in this repository — the fiscal calendar, the account hierarchy, the currency translation — is content BW would have supplied. Building it by hand is a good way to learn what it contains; it is not a good way to deliver it.

---

## Where a native build genuinely wins

Stated so the comparison is not one-sided:

- **No activation cycle.** A view change is live immediately. No request management, no activation queue, no waiting for a load window to test a fix.
- **Everything is diffable text in Git.** `.sql` files review like code. BW objects live in a metadata repository and transport through a landscape, which is stronger governance and much weaker code review.
- **SQL is a larger talent pool** than BW modelling, which matters for a team's bus factor.
- **Direct access to the full HANA feature set** — window functions, table functions, SQLScript — without waiting for BW to expose it.

The honest summary: for a greenfield mart over a well-understood source, native HANA is faster to build and easier to review. For an enterprise warehouse over SAP sources with delta loads, governed master data and row-level security as a compliance requirement, BW/4HANA is doing an enormous amount of work that a native build has to reinvent badly.

---

## Glossary cross-reference

Every term used here is defined in [`../ROADMAP.md`](../ROADMAP.md#glossary--every-abbreviation--technical-term-explained) — ADSO, CompositeProvider, DTP, LSA++, InfoObject, SID, NLS, SDA/SDI, SLT, analysis authorization, restricted and calculated key figures.
