# NovaSpace Finance Cockpit — End-to-End SAP BI Portfolio Project
### Complete roadmap: from a fresh desktop to a finished, demonstrable product

**Target role:** SAP BI HANA Technology Expert (Airbus DS / future Space JV, Toulouse)
**Goal:** one coherent project that produces evidence for every technical bullet in the posting — BW/4HANA-style modeling, ABAP, CDS, OData, UI5/Fiori, SAC (reporting *and* planning), performance/eco-design — plus the "Digital focal point" artifacts (backlog, KPI sheet, golden rules, roadmap, change-management plan) that almost no other candidate will have.

**Business story:** *"Why is the period close slow, and which space programmes are burning budget faster than planned?"* — synthetic month-end-close and programme-controlling analytics for the fictional *NovaSpace Group* (4 European entities).

**Why finance as the domain:** it is the daily reality of an SAP BI team inside an ERP delivery centre — monthly closing support, budget vs actual, finance user populations on WebI/AfO — so the demo data feels immediately familiar to the people evaluating it, while the space-programme angle still fits the target company.

**Total effort:** ~5–6 weekends (realistic), all on free tiers / trials. No real or client data anywhere.

---

## How to read this document

- Phases are strictly ordered — later phases depend on earlier ones, and **Phase 6 (SAC) is deliberately last-but-one** because the SAC trial clock (30 days, extendable to 90) starts the moment you register. Do not register early.
- Every phase ends with a **"Deliverable"** line: the concrete artifact that goes into your GitHub repo. If a phase produces no artifact, it didn't happen.
- Checkboxes are meant to be used — copy this file into your repo as `ROADMAP.md` and tick as you go. It becomes part of the portfolio itself (it demonstrates the project-management side of the role).
- The glossary at the end explains **every abbreviation and technical term** used in this document and in the job posting.

---

## Target architecture (what "final product" means)

```
                          ┌──────────────────────────────────────────┐
                          │              CONSUMPTION                 │
                          │                                          │
   ┌───────────────┐      │  SAC Story + Planning model (trial,      │
   │  Synthetic     │     │  captured as video/screenshots)          │
   │  data generator│     │                                          │
   │  (Python)      │     │  Fiori Elements Analytical List Page     │
   └──────┬────────┘      │  + freestyle SAPUI5 chart (permanent)    │
          │ CSV           └──────────────▲───────────────────────────┘
          ▼                              │ OData V4
   ┌───────────────────────┐   ┌─────────┴─────────────────────┐
   │  SAP HANA Cloud       │   │  ABAP environment             │
   │  (BTP free/trial)     │   │  (BTP ABAP trial OR Docker)   │
   │                       │   │                               │
   │  L1 RAW (inbound)     │   │  CDS view stack:              │
   │  L2 HARMONIZED        │   │  ZI_* basic → ZC_* consumption │
   │  L3 REPORTING         │   │  @Analytics annotations       │
   │  (calculation views,  │   │  1× AMDP class (SQLScript)    │
   │   documented as       │   │  Service definition + binding │
   │   BW/4HANA mapping)   │   └───────────────────────────────┘
   └───────────────────────┘
          +
   ┌─────────────────────────────────────────────────────────┐
   │  FOCAL-POINT LAYER (documents, in repo):                │
   │  backlog · KPI sheet · golden rules · BI roadmap &      │
   │  migration decision matrix · change-mgmt plan · ADRs    │
   └─────────────────────────────────────────────────────────┘
```

Honest constraint, stated openly in the repo README: BO, Lumira and Analysis for Office cannot be self-hosted for free — those requirements are covered by professional experience, and the repo includes a *migration decision matrix* showing you understand where each legacy tool fits (which is worth more in 2026 than a BO install would be).

---

# PHASE 0 — Fresh desktop setup (½ day)

Assumes Windows 11; macOS/Linux notes inline. Everything here is free.

## 0.1 Base tooling
- [x] **Git** — install from git-scm.com (macOS: `xcode-select --install`; Linux: `apt install git`). Configure identity:
  `git config --global user.name "..."` / `git config --global user.email "..."` — *git 2.47.0, identity configured.*
- [x] **GitHub account** — create if needed. Enable 2FA. — *account active, repo pushed. **2FA: verify manually** at github.com/settings/security.*
- [x] **VS Code** — install, then extensions: *Python*, *SAP Fiori tools – Extension Pack*, *Markdown All in One*, *Mermaid preview* (for diagrams). — *VS Code 1.130.0; all four installed, plus UI5 Language Assistant, App Studio Toolkit, Yeoman UI and CDS language support.*
- [x] **Python 3.12+** — from python.org (tick "Add to PATH"). Then:
  `pip install pandas numpy faker` — *running **Python 3.11.9** (Microsoft Store build), not 3.12. Everything this project needs works on 3.11: pandas 3.0.5, numpy 2.2.6, faker 40.36.0, pytest 9.1.1. No reason to upgrade.*
- [x] **Node.js LTS** (20.x or 22.x) — from nodejs.org. Then the UI5/Fiori toolchain:
  `npm i -g @ui5/cli @sap/generator-fiori yo` — *running **Node 24.16.0**, newer than the roadmap's 20/22. UI5 CLI and the Fiori generator install and run clean on it.*
- [x] **SAP HANA client for Python** (lets you load data and query HANA Cloud from scripts):
  `pip install hdbcli` — *installed.*

## 0.2 Conditional tooling (decide in Phase 4, install then)
- [ ] **Eclipse + ADT (ABAP Development Tools)** — only needed once you have an ABAP environment. Eclipse IDE for Java Developers + ADT plugin from `tools.hana.ondemand.com`.
- [ ] **Docker Desktop** — only if you fall back to the local ABAP Platform trial image (Phase 4, option B). Requirements are heavy: ~32 GB RAM recommended (16 GB is painful), 100–150 GB free disk. If your desktop can't do this, use option A (cloud) and skip Docker entirely.

## 0.3 Repository skeleton
- [x] Create GitHub repo `nova-finance-bi` (public). Clone locally. — *[github.com/Aymane-git21/nova-finance-bi](https://github.com/Aymane-git21/nova-finance-bi), cloned to `~/Desktop/nova-finance-bi`.*
- [x] Create structure:

```
nova-finance-bi/
├── README.md                  ← architecture diagram + elevator pitch (Phase 9)
├── ROADMAP.md                 ← this file
├── docs/
│   ├── kpi-definitions.md
│   ├── data-dictionary.md
│   ├── bw4hana-mapping.md     ← calc-view ↔ ADSO/CompositeProvider mapping
│   ├── golden-rules.md
│   ├── bi-roadmap.md          ← incl. BO/Lumira/AfO migration decision matrix
│   ├── change-management.md
│   ├── performance-report.md  ← before/after benchmarks (eco-design)
│   ├── adr/                   ← architecture decision records, 1 file per decision
│   └── backlog.md
├── data-generator/            ← Python scripts + generated CSV samples
├── hana/                      ← calc view definitions, SQL, HDI artifacts
├── abap/                      ← CDS sources, AMDP class, service definition (abapGit export)
├── fiori/                     ← UI5 / Fiori Elements app
└── sac/                       ← screenshots, story exports, video link, tradeoff note
```

- [x] Add MIT license and a `.gitignore` (Python + Node templates). — *plus SAP/HDI, secrets and generated-data rules.*

**Deliverable:** initialized repo with skeleton, first commit pushed. ✅ **Done.**

*Deviation from the tree above: `docs/gdpr-and-data-protection.md` (Phase 8) and a `README.md` in each of `data-generator/`, `hana/`, `abap/`, `fiori/`, `sac/` were added. Each service directory documents its own contract — a directory with a README explains itself to an interviewer browsing GitHub; an empty one does not.*

---

# PHASE 1 — Accounts & cloud landscape (1–2 h, plus waiting for e-mails)

> ## ⏭️ DROPPED — 2026-07-25
>
> **SAP BTP proved unreachable by both routes.** PAYG registration does not self-serve (SAP directs you to contact support, open-ended wait); trial registration is blocked by an outage in SAP's phone-verification service — not a data-entry or browser problem, both eliminated first.
>
> Rather than block the whole build on an external party's uptime for an unbounded period, **the landscape moved local and permanent**: SAP HANA, express edition in Docker. See **[ADR-002](docs/adr/002-fully-local-landscape.md)**. The ABAP consequence is handled separately in **[ADR-003](docs/adr/003-abap-evidence-strategy.md)**.
>
> **Also changed: phase order.** The SAC trial was already registered when this was discovered, so its 30-day clock is running. SAC therefore moves up to directly after Phase 2 (it needs data, nothing else), and is extended to ~90 days around day 20. The original ordering existed precisely to avoid this; it is now handled by resequencing instead.
>
> Everything below is kept for the record. Only ADR-001 was actually produced.

- [ ] **SAP Universal ID** — register at account.sap.com with a personal e-mail. One ID serves BTP, the SAP Community, tutorials, and later the SAC trial.
- [ ] **SAP BTP account — use Pay-As-You-Go with free tier plans, not the trial.** Two reasons: (a) the trial's phone-verification service is chronically flaky and blocks registration for days at a time; (b) the trial dies after 90 days, while free tier plans inside a PAYG account have no expiry — so your demo survives the whole job hunt.
  - Sign in with the Universal ID → choose **Pay-As-You-Go** → provide billing info (credit card required even though free tier plans cost €0) → pick an **EU region** (EU10 AWS Frankfurt or EU20 Azure Netherlands) → accept terms. Provisions in minutes.
  - **Immediately set cost guardrails:** enable *Consumption Monitoring* in the cockpit and set an email alert at ~70 %. Free tier caps at 4 GB memory / 10 GB storage per account and scales into billable PAYG usage silently once exceeded. Your project stays far below this, but an accidental second instance would not.
- [ ] **Assign free tier entitlements before provisioning anything** — the step everyone misses. Subaccount → *Entitlements* → *Configure Entitlements* → add the **free** plan and quota for each of: **SAP HANA Cloud** (`hana-free`), **SAP HANA Schemas & HDI Containers** (`hdi-shared`), **Business Application Studio**. A service that looks unavailable at provisioning time is almost always a missing entitlement.
  - HANA Cloud free tier gives **16 GB memory, 1 vCPU, 80 GB storage** — more than the trial. Unsupported: document store, knowledge graph, triple store, script server, availability zones/replicas, private link. None of these matter for this project.
  - When creating the instance, confirm the plan selector reads **free**, not the default paid plan. This is the single click that could cost money.
- [ ] In the BTP subaccount, enable **Cloud Foundry** and note org/space (usually pre-created in trial).
- [ ] Subscribe to **SAP Business Application Studio** (BAS) — free plan. Create two dev spaces later as needed: *SAP HANA Native Application* (Phase 3) and *SAP Fiori* (Phase 5).
- [ ] **Do NOT register the SAC trial yet.** Its 30-day clock (extendable to ~90 around day 20) must not start before your data is ready. SAC registration happens in Phase 6.

**Deliverable:** `docs/adr/001-landscape-choice.md` — a half-page ADR recording the trial vs free-tier PAYG choice and why (expiry, entitlement model, cost guardrails) — a real decision with real tradeoffs, which is exactly what an ADR is for. (Yes, document even this. Interviewers love ADRs.) ✅ **Written in Phase 0** — the decision does not depend on executing the signup, so it is recorded up front. Revisit it only if the signup surfaces something the ADR did not anticipate.

---

# PHASE 2 — Business design & synthetic data (Weekend 1)

The order matters: **KPIs before schema, schema before code.** This is exactly the "analyze business requirements and translate them into Digital solutions" bullet.

> ## ✅ COMPLETE
>
> `docs/kpi-definitions.md` · `docs/data-dictionary.md` · `docs/dataset-profile.md` (generated) · `data-generator/` with **102 passing tests** at two scales · **1,122,588** journal lines · SAC extracts already shaped and exported.
>
> Additions beyond the phase as written:
> - **`novaspace/harmonise.py`** — the L2 layer written in Python: signed amounts, manual/late flags, and a reference implementation of all eight KPIs. This is the specification the HANA views and the AMDP must reproduce, so "does the SQLScript agree" becomes checkable rather than arguable.
> - **`profile_dataset.py`** — regenerates every measured figure the documentation quotes. Docs drift from data silently; a generated profile cannot.
> - **A `--full` test lane.** Two defects passed the fast suite and were caught only at full volume. Bugs whose symptoms scale with volume are invisible to a reduced-scale run by construction.

## 2.1 Business questions & KPI sheet (2–3 h)
- [x] Write `docs/kpi-definitions.md`. For each KPI: name, business question it answers, formula, grain, target/threshold, data source, owner (fictional role). Minimum set:

| KPI | Formula (summary) | Why it matters |
|---|---|---|
| Days to close | working days from period end to final close task / last relevant posting, per entity | The monthly race every ERP finance team runs |
| % manual journal entries | manual doc types ÷ all postings, per entity/period | Automation & data-quality proxy; drives close speed |
| Late postings | postings after the soft-close cut-off, count & value | Pinpoints *why* an entity closes slowly |
| Budget vs actual variance | actual − budget (€ and %), by programme / cost-centre hierarchy / account group | The core programme-controlling question |
| Programme run-rate & simple EAC | rolling-3M actuals annualised; EAC = actuals to date + run-rate × remaining periods | Early warning for overspending programmes |
| FX impact | group-currency variance at constant rates vs actual rates | Separates "we spent more" from "the pound moved" |
| Forecast accuracy (MAPE) | mean abs. % error, forecast vs actual per cost centre | Feeds the SAC planning story |
| Intercompany mismatches | IC pairs not netting to zero, count & value | The reconciliation grind of every close |

## 2.2 Dimensional model (2 h)
- [x] Design a **star schema** and document it in `docs/data-dictionary.md` (every table, every column, type, description, sample values):
  - **Dimensions:** `DIM_COMPANY_CODE` (4 entities of the fictional *NovaSpace Group* — ES/FR/DE/UK, each with its local currency), `DIM_COST_CENTER` (~200 centres with a **3-level standard hierarchy** — hierarchies are a BW classic, model them properly), `DIM_PROGRAMME` (8–10 fictional space programmes — satellites, one launcher, ground segment — as WBS-like elements with start/end dates and total budget), `DIM_GL_ACCOUNT` (~150 accounts under a P&L hierarchy: revenue, material, personnel, subcontracting, overhead), `DIM_DATE` (fiscal calendar with periods 1–12 **plus special periods 13–16** for year-end adjustments), `RATES` (monthly FX rates to group currency EUR)
  - **Facts:** `FACT_JOURNAL` — the big one, ≈1M lines, deliberately shaped like S/4HANA's **Universal Journal (ACDOCA)**: document number & type, posting date *and* fiscal period, account, cost centre, programme, debit/credit indicator, amounts in **document, local and group currency**, manual-posting flag, pseudonymised user ID; `FACT_BUDGET` (annual budget per cost centre × account group × programme, with a Version column); `FACT_FORECAST` (quarterly rolling-forecast snapshots); `FACT_CLOSE_TASKS` (entity × period × close task, with due and actual completion timestamps)

## 2.3 Python data generator (4–6 h)
- [x] Write `data-generator/generate.py`. Realism requirements — this is what makes the data feel like a real ERP to someone who lives in one:
  - 4 entities × 3 fiscal years × ~25k journal lines per month → ≈1M lines
  - **Posting-date clustering:** automatic postings (payroll, depreciation, allocations) land punctually and regularly; manual entries spike in the first 3–5 working days after period end — the close crunch — with a tail of genuinely *late* postings
  - One entity is **chronically slow to close** (more manual entries, later postings) — a story the dashboard should reveal, not state
  - One programme **overspends against budget from mid-year onward** — the second story to find
  - **FX drift** on GBP/EUR so group-currency variance ≠ local-currency variance (the FX-impact KPI needs this to be non-trivial)
  - Intercompany pairs that net to zero — except ~2 % mismatches (the reconciliation story)
  - **Special periods 13–14 actually used** for year-end adjustment entries — a small detail that instantly reads as "has done real finance BI"
  - User IDs **pseudonymised at generation time** (GDPR-aware by design — see Phase 8)
  - Deterministic seed (`numpy.random.default_rng(42)`) so everything is reproducible
- [x] Output: one CSV per table into `data-generator/output/` (commit only small samples + the script; full CSVs are regenerable).

**Deliverables:** KPI sheet, data dictionary, generator script, sample CSVs. ✅ **All delivered**, plus the dataset profile, the harmonised-layer reference implementation and a 102-test suite.

---
# PHASE 3 — SAP HANA Cloud modeling (Weekend 2)

> ## ✅ COMPLETE
>
> HANA Express running locally · **1,182,798 rows loaded in 35 s** · 21 views across L1/L2/L3 · `TF_PROGRAMME_RUNRATE` SQLScript table function deployed · [`docs/bw4hana-mapping.md`](docs/bw4hana-mapping.md) written.
>
> **All 24 cross-checks against the Python reference agree** (`hana/verify_against_python.py`). The table function reproduces the Python EAC to within €0.28 on €800 m.
>
> Three defects the cross-check caught, none of which would have been visible from a dashboard:
> - **FX impact was overstated by ~€6,900.** `CV_FX_IMPACT` differenced the *booked* group amount against a budget-rate figure. Reversals carry the original document's group amount into the next period (FB08 behaviour), so that difference silently attributed a reversal's rate carry-over to FX. Now recomputed from the local amount on both sides, with the booked figure kept alongside for reconciliation.
> - **Budget variance was computed at two different grains** in SQL and Python, with a `FULL OUTER` on one side and a left join on the other. They could never have agreed. Python corrected to match the SQL, which was the better design.
> - **A full-year budget flatters an open year.** FY2026 is closed through P6 but budget phases across 12, so the group looked to be at 57 % of plan and comfortably under. Now compared year-to-date, with a test pinning the trap so it stays visible.
>
> ### 🔄 REVISED — runs on SAP HANA, express edition (local Docker), not HANA Cloud. See [ADR-002](docs/adr/002-fully-local-landscape.md).
>
> Same database engine, so 3.2 and 3.3 are unchanged: same column store, same SQLScript, same calculation views, same HDI. Three differences:
> - **3.1 changes.** No BTP instance to create, no DBADMIN password from a cockpit, and **no nightly stop / 30-day deletion rule** — so `start-instance.sh` and that entire risk-register row disappear. Replaced by a `docker compose` setup and the same `hdbcli` loader.
> - **No BAS and no XS Advanced** (the full HXE image needs 16–24 GB RAM; this machine has 19.3 GB and also has to run everything else). So no graphical calculation-view editor.
> - **L3 views are therefore authored as `.hdbcalculationview` design-time artifacts** and deployed with `@sap/hdi-deploy`. This is the fallback the phase already sanctions, and it produces better evidence than the editor would: diffable XML in Git rather than clicks.

## 3.1 Instance & loading (2 h)
- [ ] In BTP cockpit: create a **SAP HANA Cloud** instance (smallest trial/free-tier size). Note the admin (DBADMIN) password in your password manager.
- [ ] **Operational reality — build the habit now:** free tier HANA Cloud instances are **stopped nightly**, and a stopped instance is **deleted after 30 days** unless restarted (alert at 15 days). Restart at the start of every session. Set up the BTP CLI and commit a one-line `hana/start-instance.sh` to the repo — small piece of ops competence, and it saves you from a rebuild.
- [ ] Create a technical user + schema `AERO_RAW`. Load the CSVs either via **Database Explorer** import (fine at this size) or a Python loader using `hdbcli` + batched `executemany` (nicer to show in the repo — commit it as `hana/load_data.py`).

## 3.2 Layered modeling (6–8 h) — the heart of the BW/4HANA evidence
Build three layers of **calculation views** in BAS (dev space *SAP HANA Native Application*, HDI container) — or, pragmatic fallback, plain SQL views + one documented HDI example if BAS fights you. Layers, mirroring LSA++:

- [ ] **L1 RAW / inbound** — 1:1 views on loaded tables, type casting only. *(BW/4HANA analogue: staging ADSO / inbound layer.)*
- [ ] **L2 HARMONIZED / propagation** — joins to master data, **currency translation to group currency** (via the rates table), derived flags (e.g. `is_manual_posting`, `is_late_posting`), signed amounts from the debit/credit indicator, fiscal-period logic. *(Analogue: standard ADSO with transformations.)*
- [ ] **L3 REPORTING / virtual data mart** — star-join calculation views (cube semantics): `CV_PL_ACTUALS`, `CV_BUDGET_VARIANCE`, `CV_CLOSE_MONITOR`, `CV_FX_IMPACT`, each with measures, restricted/calculated columns (e.g. “personnel cost, manual postings only”), input parameters for fiscal period, currency and plan version. *(Analogue: CompositeProvider + BW query elements: restricted key figures, variables.)*

## 3.3 The mapping document (2 h) — what makes it readable to a BW interviewer

> ✅ Written. Goes beyond the object table with four sections on what BW/4HANA actually gives you that a native build does not: persistence, delta handling, analysis authorizations and standard content — plus an honest section on where native wins.
- [x] Write `docs/bw4hana-mapping.md`: a table with one row per object — *native HANA object → BW/4HANA equivalent → why this layer exists → what would differ in a real BW/4 system* (e.g. delta handling via DTP, InfoObject-based master data governance, authorizations via analysis authorizations). This document lets you talk BW fluently in the interview even though the build is HANA-native.

**Deliverables:** HDI/SQL sources in `hana/`, loader script, `bw4hana-mapping.md`. ✅ **All delivered**, plus the container lifecycle script, the SQLScript table function and `verify_against_python.py` — 24 checks proving the SQL and the Python agree.

---

# PHASE 4 — ABAP + CDS + OData (Weekend 3)

> ### 🔄 REVISED — no ABAP system is reachable. Split by honesty level. See [ADR-003](docs/adr/003-abap-evidence-strategy.md).
>
> Option A (BTP ABAP Environment) died with Phase 1. Option B (ABAP Platform Trial in Docker) needs **100 GB disk minimum, 200 GB recommended**; this machine has **62.7 GB free**. Both are out.
>
> The phase is therefore rebuilt around what each layer can honestly claim:
>
> | Layer | Treatment | Why |
> |---|---|---|
> | Run-rate / EAC **SQLScript** | **Executed for real** — deployed to HANA Express as a table function, unit-tested, benchmarked in Phase 7 | An AMDP body *is* SQLScript, and HANA executes it. ABAP is only the wrapper. The most interesting artifact in this phase never needed ABAP to run. |
> | `ZCL_AMDP_RUNRATE` + `ZI_*` / `ZC_*` CDS stack | **Authored, not activated.** Committed under `abap/`, labelled `NOT ACTIVATED` in every file header. No screenshots, no claims. | Real ABAP, written correctly, ready to activate the day a system exists. Wrapping the identical SQLScript already proven above. |
> | OData V4 service | **CAP** (`@sap/cds`, local Node) | A genuine annotation-driven OData V4 service that Phase 5's Fiori Elements app consumes for real. Labelled as CAP throughout — never presented as ABAP. |
>
> Net effect: Phase 5 stays unblocked, the pushdown logic ends up *more* proven than the original plan (executed and benchmarked, not just activated in a trial that would later be reset), and the gap that remains is stated plainly rather than papered over.

## 4.1 Choose your ABAP environment (30 min decision, record as ADR)
- [ ] **Option A (recommended): SAP BTP ABAP Environment trial** — created inside the BTP trial via a booster. Cloud-hosted, nothing to install locally, works with ADT in Eclipse. Caveats: capacity is sometimes exhausted (retry off-peak / other region), and trial systems are periodically reset — keep all code in abapGit from day one.
- [ ] **Option B (fallback): ABAP Platform trial via Docker** — full local system, survives forever, but needs ~32 GB RAM and 100–150 GB disk, plus license acceptance on first run. Only choose this if your desktop is a workstation-class machine.
- [ ] Install **Eclipse + ADT** now; connect to the chosen system. Link the ABAP package to a new GitHub repo folder via **abapGit** immediately.

## 4.2 Data in the ABAP system (1–2 h)
Reality check to state in the docs: in a real Airbus landscape, BW/4HANA and the ABAP stack share one system; here you have two separate free systems, so you'll load a **subset** (e.g. the two smaller facts + dimensions) into ABAP-managed tables. Generate the tables from DDL in ADT and load via a small ABAP class (`cl_abap_...` CSV parse or hardcoded generator reusing your Python logic's seed rules).

## 4.3 The CDS stack (5–6 h) — the "ABAP is highly recommended + CDS/OData desirable" evidence
- [ ] **Basic/interface views** `ZI_GLAccount`, `ZI_CostCenter`, `ZI_Programme`, `ZI_JournalEntry` — with associations, semantic annotations (`@Semantics.amount`, `@Semantics.quantity`).
- [ ] **Composite view** `ZI_ProgrammeRunRate` — joins journal actuals to budget. Implement the rolling-3-month run-rate and simple EAC as an **AMDP** (`ZCL_AMDP_RUNRATE`, SQLScript with a window function) exposed as a CDS table function — this single object proves ABAP + SQLScript + performance thinking at once.
- [ ] **Consumption views** `ZC_BudgetVariance`, `ZC_CloseMonitor` with `@Analytics.query` and UI annotations (`@UI.chart`, `@UI.lineItem`, selection fields) so Fiori Elements can render them without custom code.
- [ ] **Service definition + OData V4 service binding**; test in the ADT preview and note the service URL.

**Deliverables:** abapGit-exported sources in `abap/`, ADR `002-abap-environment.md`, screenshot of OData metadata in `docs/`.

---

# PHASE 5 — Fiori / UI5 consumption layer (Weekend 4, part 1)

- [ ] In BAS (*SAP Fiori* dev space) or VS Code with Fiori tools: generate a **Fiori Elements Analytical List Page** on `ZC_BudgetVariance` (or List Report + Object Page if ALP fights the trial service). Zero-code first version; then add one extension point customisation to show you can.
- [ ] Add **one freestyle SAPUI5 view** with a `sap.viz`/VizFrame chart (e.g. programme burn bubble chart: % budget consumed × % time elapsed, bubble size = programme budget — anything above the diagonal is overspending) — proves hand-coded UI5, not just generators.
- [ ] Permanence plan (trials die, demos shouldn't): build the app with `ui5 build`, add a small **mock server** (Fiori tools generates one) with a frozen JSON snapshot of your OData data, and host the static build on **GitHub Pages**. Result: a clickable demo URL that works even after every trial expires. Keep it clearly labelled "mock data snapshot".
- [ ] Screenshots into `docs/`.

**Deliverables:** `fiori/` app source, live GitHub Pages demo URL in README.

---

# PHASE 6 — SAC sprint (Weekends 4–5, strictly time-boxed)

> ### ⏫ MOVED UP — runs directly after Phase 2. The trial was already registered, so the clock is running.
>
> The "only now register" instruction below was overtaken by events: registration happened before Phase 2 was built. Two consequences:
> - **SAC runs on generator output directly.** 6.1 said to export curated aggregates from HANA; those same aggregates are produced in pandas by the generator instead, at identical numbers from the same seed. This removes HANA from the SAC critical path entirely, so SAC no longer waits on Phase 3.
> - **Set a calendar reminder for the day-20 extension.** Missing that window drops the tenant from ~90 days to 30. This is the one deadline in the project that cannot be recovered.

**Only now** register the SAC trial: 30 days, and around day 20 you can extend to ~90 total. Trials run on a shared tenant and — critical constraint — **data gets in by file import (CSV/XLSX) or Google Drive only; no live connection to your HANA Cloud**. Your architecture note (below) turns this limitation into interview material.

## 6.1 Prepare curated extracts (1–2 h, before registering)
- [ ] From HANA, export aggregate CSVs shaped for SAC (fiscal-period grain, pre-joined dimensions): `sac_pl_actuals.csv`, `sac_programme_costs.csv`, `sac_close_tasks.csv`, `sac_budget_actual.csv`. Keep each < 100 MB.

## 6.2 Reporting story (6–8 h)
- [ ] Register trial → build a **model** per extract (define measures vs dimensions, date dimension, currency as measure attribute).
- [ ] One **story**, three pages: **(1) CFO overview** — KPI tiles (days to close, % manual JEs, group P&L variance vs budget, IC mismatch value) + trend; **(2) Programme controlling** — budget vs actual by programme and cost-centre hierarchy, run-rate/EAC table, waterfall of variance drivers incl. FX impact; **(3) Close monitor** — task completion timeline per entity, late postings by entity and document type, the chronically-slow entity emerging from the data. Restraint and labelling matter more than chart variety — design one page like you'd ship it to a CFO.

## 6.3 Planning scenario (4–6 h) — your honest BPC answer
- [ ] Create a **planning-enabled model** on `sac_budget_actual` with a **Version dimension** (Actual / Budget / Forecast).
- [ ] Demonstrate: manual data entry on Forecast, **spreading** an annual cost-centre budget down to fiscal periods, copy Actual→Forecast, one simple **data action**, and a variance table (Actual − Budget, absolute and %).
- [ ] In docs, one paragraph mapping this to BPC concepts (versions ≈ categories, data actions ≈ planning functions/script logic, input forms ≈ input schedules) — that's the bridge to "Experience on BPC projects".

## 6.4 Capture everything before the tenant dies
- [ ] 3–4 min screen recording (OBS Studio, free): story walkthrough + planning demo. Upload unlisted to YouTube; link in README.
- [ ] Screenshots of every page and the model definitions → `sac/`.
- [ ] Write `sac/live-vs-import.md`: why a live connection (to BW/4HANA or HANA) beats import in production — data freshness, no replication, security inherited from the source, no volume ceiling — and when import acquisition is still legitimate. One page.

**Deliverables:** video link, screenshots, tradeoff note, planning-concept mapping.

---

# PHASE 7 — Performance & eco-design (Weekend 5, part 2)

The posting explicitly lists *Eco-design of Digital services* — almost no candidate will show evidence for it. You will.

- [ ] Pick your heaviest calculation view (P&L actuals at journal-line grain). Run it cold via SQL, capture runtime and **EXPLAIN PLAN** (and PlanViz if using the full tooling).
- [ ] Apply three optimisations, measuring after each: **(1)** pre-aggregated monthly table (materialisation) for the story-level queries; **(2)** partition/filter pushdown — ensure date filters prune before joins; **(3)** column pruning — remove unused columns from L3 views.
- [ ] Write `docs/performance-report.md`: before/after table (runtime, records scanned, peak memory if visible), and an **eco-design section**: reduced data scanned per query × query frequency = compute avoided; retention policy proposal (keep line-item grain 24 months, period aggregates beyond — the HANA-native analogue of classic BW cube compression + archiving/NLS); scheduling recommendation (refresh aggregates nightly, not per-query). Frame it as CO₂/cost proxy honestly — order-of-magnitude reasoning, not fake precision.

**Deliverable:** performance & eco-design report with real measured numbers.

---

# PHASE 8 — The focal-point layer (Weekend 6, part 1) — the differentiator

This phase is why you get *this* job rather than a developer job. Each document is 1–2 pages, written like an internal Airbus artifact, all in `docs/`:

- [ ] **`backlog.md`** — 15–20 user stories ("As a programme controller, I need cost centres past 90 % budget consumption before period 10 flagged, so that..."), MoSCoW-prioritised, grouped into 3 sprints, with acceptance criteria on the top 5. Mark which stories the build actually implemented.
- [ ] **`golden-rules.md`** — your development standards: naming conventions (ZI_/ZC_, CV_ prefixes, layer suffixes), layer rules ("no joins in L1", "no business logic in the UI"), versioning (everything in Git/abapGit), definition-of-done (peer review, runtime budget, documented in data dictionary). This answers "following the development golden rules" *literally*.
- [ ] **`bi-roadmap.md`** — one-page strategy: current state (BO/WebI + AfO + Lumira + BW) → target (BW/4HANA or HANA + SAC, Fiori embedded analytics), with a **migration decision matrix**: for each legacy tool — keep / migrate / retire, criteria (user population, interactivity needs, Excel dependency, licence cost, maintenance dates), and honest sequencing. Cite the real support timelines (BO maintained ≥ 2031; Lumira → SAC stories; AfO maintained, no new features). This is your strongest interview prop.
- [ ] **`change-management.md`** — adoption plan for the close-cockpit rollout: stakeholder map, comms plan, training approach (a champion inside each entity's closing team), hypercare across the first two period closes, adoption KPIs (weekly active users, report-request deflection). Answers "Lead the change management activities after the deployment".
- [ ] **`gdpr-and-data-protection.md`** — half a page: what personal data can appear in finance BI (posting user IDs, approver names), how this design avoids it (pseudonymisation at generation, no personal data in the L3/reporting layer), retention aligned with the eco-design policy, and the rule that any real deployment goes through the DPO. Small document, outsized signal.
- [ ] **ADRs** — you should have 4–6 by now (landscape, ABAP env, import-vs-live SAC, materialisation strategy...). Keep them terse: context / decision / consequences.

**Deliverables:** five documents + ADR set.

---

# PHASE 9 — Packaging & presentation (Weekend 6, part 2)

- [ ] **README.md** — the 90-second pitch: problem statement, architecture diagram (Mermaid), tech list mapped explicitly to the job requirements ("BW4HANA developments → L1/L2/L3 modeling + mapping doc", "ABAP → AMDP + CDS stack", ...), demo links (GitHub Pages app, SAC video), and the honest-constraints paragraph (BO/AfO from professional experience; SAC trial = import-only, see tradeoff note).
- [ ] Record a **7–10 min full walkthrough video** (architecture → data → HANA → CDS/OData → Fiori → SAC → docs). Unlisted YouTube. This is what you send with applications.
- [ ] **CV/LinkedIn bullet** drafted, e.g.: *"Built an end-to-end SAP analytics product (HANA Cloud, ABAP CDS/AMDP, OData V4, Fiori Elements, SAC reporting & planning) for space-programme financial controlling and month-end close monitoring, incl. performance/eco-design benchmarking and full BI governance documentation."*
- [ ] **Interview prep sheet** (private, not in repo): 5 stories in STAR format hung on project artifacts, incl. one on the JV angle — carving a BI landscape out of a parent company (system separation, authorizations, data ownership, export-control classification of reports) — directly relevant to the September 2026 Space JV context of this position.
- [ ] Final pass: every doc linked from README, dead trials labelled, licence present, repo public.

**Deliverable:** the finished, sendable portfolio.

---

## Timeline summary

| Weekend | Phases | Output |
|---|---|---|
| Prep evenings | 0 + 1 | Desktop ready, BTP account, repo skeleton |
| 1 | 2 | KPIs, star schema, 1M-row synthetic dataset |
| 2 | 3 | HANA layered models + BW/4HANA mapping doc |
| 3 | 4 | CDS stack, AMDP, OData V4 service |
| 4 | 5 + 6.1–6.2 | Fiori app + GitHub Pages demo; SAC trial starts, reporting story |
| 5 | 6.3–6.4 + 7 | SAC planning scenario, captures; performance & eco-design report |
| 6 | 8 + 9 | Focal-point documents; packaging, videos, pitch |

## Risk & gotcha register

| Risk | Impact | Mitigation |
|---|---|---|
| ~~HANA Cloud free tier instance deleted (nightly stop + 30-day rule)~~ | ~~Lose all modeling~~ | ✅ **Eliminated.** HANA Express is local and permanent — no nightly stop, no deletion rule, no clock. [ADR-002](docs/adr/002-fully-local-landscape.md) |
| **SAC trial expires mid-build** ⚠️ **LIVE RISK** | Lose stories | ~~Register only at Phase 6~~ — already registered, clock running. Mitigation is now: build Phase 2 first and fast, run Phase 6 immediately after, **extend at day ~20**, capture screenshots/video continuously. This is the only unrecoverable deadline left in the project. |
| ~~BTP ABAP capacity unavailable / system reset~~ | ~~Delay; lose code~~ | Overtaken: there is no ABAP system at all. Handled by [ADR-003](docs/adr/003-abap-evidence-strategy.md) — SQLScript executed for real, ABAP authored and labelled, CAP for the service layer |
| ~~BTP trial phone verification broken at signup~~ | ~~Blocks all cloud phases~~ | ❗ **This risk materialised**, and the PAYG route it was supposed to be mitigated by was *also* blocked (support ticket required). Resolved by removing the dependency: fully local landscape, [ADR-002](docs/adr/002-fully-local-landscape.md) |
| ~~Docker ABAP trial exceeds desktop specs~~ | ~~Phase 4 blocked~~ | ❗ **Also materialised** — 100 GB needed, 62.7 GB free. Resolved as above; the "deliver HANA-side SQLScript equivalents and say so honestly" mitigation is exactly what [ADR-003](docs/adr/003-abap-evidence-strategy.md) does |
| **Three representations of the model drift apart** (HANA views, CAP CDS, authored ABAP CDS) ⚠️ **NEW** | Inconsistent evidence; an interviewer finds the mismatch before you do | Single source of truth is the data dictionary; the CAP↔ABAP mapping document is the control; the generator's fixed seed means every number in every layer is checkable against the same dataset |
| Scope creep (adding ML, more dashboards…) | Never finishing | The backlog is the contract: MoSCoW "Won't have this release" section exists precisely for your good ideas |
| Data resembling any real company's figures or programmes | Credibility/compliance | Fictional group (NovaSpace), invented programme names, seeded generator; README states all data is synthetic and reproducible |

---

# GLOSSARY — every abbreviation & technical term, explained

Organised by category. The third column tells you *why the term matters for this job/project* — that's the part to internalise for the interview.

## A. SAP platforms & products

| Term | Stands for | Explanation & relevance |
|---|---|---|
| SAP | Systeme, Anwendungen und Produkte (Systems, Applications and Products) | The German enterprise-software company whose ecosystem this entire role lives in. |
| ERP | Enterprise Resource Planning | The core business system (finance, logistics, procurement…). SAP's ERP is the source of most BI data. |
| ECC | ERP Central Component | SAP's classic ERP (pre-2015 era). Many companies, incl. large aerospace players, still run it alongside newer systems; its data feeds BW. |
| S/4HANA | SAP Business Suite 4 SAP HANA | The current-generation ERP, rebuilt to run only on the HANA database. Successor to ECC. Ships "embedded analytics" built on CDS views — one reason CDS skills are listed as desirable. |
| HANA | High-performance Analytic Appliance | SAP's in-memory, column-oriented database. Stores data in RAM in columnar form, making analytical aggregations dramatically faster than disk-based row stores. The technical foundation of everything in this posting. |
| SAP HANA Cloud | — | The managed cloud edition of HANA on BTP. What this project uses (free tier). |
| BTP | Business Technology Platform | SAP's cloud platform (PaaS): hosts HANA Cloud, the ABAP Environment, Business Application Studio, integration services, etc. Your entire free landscape lives here. |
| CF | Cloud Foundry | The open-source PaaS runtime used inside BTP where apps and service instances are deployed, organised into orgs and spaces. |
| BAS | Business Application Studio | SAP's browser-based IDE on BTP; the standard tool for building HANA HDI artifacts and Fiori apps. |
| BW | Business Warehouse | SAP's data-warehousing product: manages extraction, staging, transformation, master data, and analytic queries with prebuilt governance. "Technical knowledge in BW" is mandatory in the posting. |
| BW/4HANA | Business Warehouse for HANA | The current-generation BW, rewritten to run only on HANA with a simplified object model (ADSOs, CompositeProviders, Open ODS views). "Deep experience in BW4HANA developments" is the posting's #1 mandatory skill; this project mirrors its architecture natively on HANA and documents the mapping. |
| BO / BObj | (SAP) BusinessObjects | SAP's on-premise BI suite (acquired 2008): the BI Platform server plus client tools — Web Intelligence, Crystal Reports, Analysis for Office, Lumira. Actively maintained (releases BI 2025/2027/2029, maintenance ≥ 2031). "Experience in BO reporting tools" is mandatory. |
| BI Platform / BIP | BusinessObjects BI Platform | The server backbone of BO: user/security management, scheduling, publishing, the CMC and BI Launchpad. "BO administrative skills desirable" refers to running this. |
| CMC | Central Management Console | BO's web admin console — users, groups, rights, servers, scheduling. Core of BO administration. |
| BI Launchpad | — | The BO end-user web portal where reports and documents are accessed. |
| WebI | Web Intelligence | BO's flagship ad-hoc query & reporting tool, built on semantic-layer universes. The largest report population to migrate or keep in most BO landscapes. |
| Universe (UNX/UNV) | — | BO's semantic layer: a governed business view (dimensions, measures, joins) over source databases that WebI queries. UNV is the legacy format, UNX the current one. |
| Crystal Reports | — | BO's pixel-perfect, print-oriented reporting tool (invoices, certificates, operational documents). |
| Lumira | — | BO's self-service visualisation family: **Discovery** (business-user exploration) and **Designer** (IT-built dashboards/applications, successor of Design Studio). SAP's direction: new dashboarding goes to SAC, though Lumira still receives platform-aligned releases (Lumira 2025). Mandatory in the posting because Airbus DS still runs it. |
| AfO / AO | Analysis for (Microsoft) Office | Excel/PowerPoint add-in for OLAP-style analysis directly on BW queries and HANA views. Beloved by finance/controlling users. Maintained, but receives no new features — its users are a key population in any migration plan. |
| SAC | SAP Analytics Cloud | SAP's strategic cloud analytics SaaS: BI stories, planning, and predictive in one product. "Experience on SAC" required. This project uses the 30→90-day trial (import-only data acquisition). |
| SAC story | — | SAC's report/dashboard document: pages of charts, tables, filters, input controls on top of models. |
| SAC model | — | The dataset definition in SAC (measures, dimensions, hierarchies, currency), either imported or live-connected. Planning features are enabled at model level. |
| BPC | Business Planning and Consolidation | SAP's classic planning/budgeting/consolidation product (standard and BW-embedded flavours): input schedules, planning functions, script logic. "Experience on BPC projects" required — this project answers it with SAC Planning + an explicit BPC-concept mapping. |
| Datasphere | SAP Datasphere (ex Data Warehouse Cloud/DWC) | SAP's cloud data-warehousing service, increasingly positioned beside/after BW/4HANA. Worth knowing for roadmap discussions. |
| BDC | SAP Business Data Cloud | SAP's newer umbrella offering bundling Datasphere, SAC and data products. Roadmap-conversation material. |
| SoD | Statement of Direction | SAP's official document announcing product strategy/maintenance commitments (e.g. the analytics SoD guaranteeing BO maintenance ≥ 2031). Citing it is how you argue roadmaps credibly. |

## B. Data-warehousing & BW concepts

| Term | Stands for | Explanation & relevance |
|---|---|---|
| DWH | Data Warehouse | A system integrating data from operational sources into a structure optimised for analysis and history-keeping. |
| ETL / ELT | Extract, Transform, Load / Extract, Load, Transform | The two orderings of data integration. Classic BW is ETL-ish (transformations in the load path); HANA-native designs push toward ELT (load raw, transform in views on the fly). Your L1→L3 design is ELT. |
| Star schema | — | Modeling pattern: a central fact table (events/measures) surrounded by dimension tables (descriptive context). The shape of Phase 2 and the basis of "star-join" calculation views. |
| Fact table | — | Table of measurable events at a defined grain (e.g. one row = one journal line: entity × account × cost centre × posting date). |
| Dimension | — | Descriptive master data used to slice facts (material, plant, supplier, date). |
| Grain | — | The exact level of detail of one fact row. Getting KPIs' grain explicit (Phase 2.1) is what separates clean BI from chaos. |
| Master data / transactional data | — | Relatively stable descriptive entities vs. event records. BW manages master data via InfoObjects with governance most SQL shops lack. |
| OLTP | Online Transaction Processing | Workload of operational systems: many small reads/writes (ERP). Row-store friendly. |
| OLAP | Online Analytical Processing | Workload of analytics: few queries scanning millions of rows with aggregations. Column-store friendly — HANA's home turf. |
| LSA++ | Layered Scalable Architecture (++) | SAP's reference layer architecture for BW on HANA/BW/4HANA: lean staging → propagation/harmonisation → virtual reporting marts. Phase 3's L1/L2/L3 is LSA++ transplanted to native HANA — say exactly that in interviews. |
| InfoObject | — | BW's atomic metadata unit: a characteristic (dimension field, possibly with master data, texts, hierarchies) or key figure (measure). |
| InfoProvider | — | Umbrella term for BW objects you can query (ADSOs, CompositeProviders, …). |
| ADSO | Advanced DataStore Object | BW/4HANA's universal persistence object, replacing the zoo of classic cubes/DSOs. Configurable to act as staging, standard EDW layer, or cube-like reporting store. Your L1/L2 tables map to it. |
| CompositeProvider | — | BW/4HANA's virtual join/union layer combining ADSOs and HANA views for reporting — the query-facing object. Your L3 star-join views map to it. |
| Open ODS View | — | BW/4HANA object exposing external tables/views (e.g. native HANA schemas) to BW's query world with field-based (no InfoObject) modeling — the standard bridge in mixed landscapes like the one you're simulating. |
| DTP | Data Transfer Process | BW's load-execution object moving data between objects with filtering, delta handling and error stack. In your HANA-native build its role is played by the loader script — a difference to name in the mapping doc. |
| Transformation | — | BW's mapping/logic layer between source and target (rules, routines in ABAP/AMDP). Equivalent of your L2 logic. |
| Delta / full load | — | Loading only changes vs. everything. Delta management is a BW strength; note in docs that production would replace your full CSV loads with delta DTPs or replication. |
| BW query / BEx query | Business Explorer query | The analytic query definition on an InfoProvider: restricted/calculated key figures, variables, hierarchies. Consumed by AfO, SAC live, WebI. Your L3 input-parameterised views imitate it. |
| Restricted / calculated key figure | — | Measure filtered by characteristics (e.g. "personnel cost, manual postings only") / measure computed from others. You implement both as restricted & calculated columns in calc views. |
| Variable | — | Query-time prompt (date, plant…) in BW; analogue = input parameters on your calculation views. |
| Analysis authorization | — | BW's row-level security concept (who may see which characteristic values). Mention in mapping doc as a production-delta; relevant to the JV separation story. |
| SID | Surrogate ID | BW's internal integer keys linking master data to facts — why BW joins fast and stays governed. Trivia-level, but shows depth. |
| NLS | Near-Line Storage | BW's cold-data tier: aged data moved out of hot memory yet still queryable — the standard companion of cube compression in classic performance projects. Your Phase 7 retention/aggregation proposal is its HANA-native analogue. |

## C. HANA & development technology

| Term | Stands for | Explanation & relevance |
|---|---|---|
| Column store | — | Storing tables column-wise with compression; scans/aggregations touch only needed columns. Why HANA is fast for OLAP and why "column pruning" (Phase 7) works. |
| In-memory | — | Primary data residence in RAM rather than disk. HANA's defining trait; memory footprint is also why eco-design/pruning matters. |
| Calculation view | — | HANA's modeled, layered analytic view (projections, joins, star joins, aggregations, input parameters), executed in the engine. Your L1–L3 objects. |
| Star join | — | Calculation-view join type optimised for fact-to-dimensions patterns; gives the view cube semantics. |
| HDI | HANA Deployment Infrastructure | Container-based deployment system for HANA design-time artifacts (views, tables, roles) with build/versioning — the "Git-able" way to develop HANA, used via BAS. |
| SQLScript | — | HANA's SQL-based procedural language (procedures, table functions, window functions). Used in your AMDP. |
| AMDP | ABAP-Managed Database Procedure | An ABAP class method whose body is SQLScript pushed down to HANA — the canonical "code pushdown" pattern proving ABAP + HANA together. Your `ZCL_AMDP_COVERAGE`. |
| Code pushdown | — | The HANA-era principle: compute where the data lives (database) instead of looping in the application server. The philosophy behind CDS + AMDP. |
| CDS | Core Data Services | SAP's declarative data-modeling language in the ABAP stack: views with associations, annotations, access control — the semantic backbone of S/4 embedded analytics and RAP. "Technical knowledge in CDS desirable" — your Phase 4 delivers a full stack. |
| Annotation | — | `@`-metadata on CDS views (semantics, analytics, UI) that downstream frameworks interpret — how your Fiori Elements app renders without UI code. |
| RAP | ABAP RESTful Application Programming model | The modern ABAP framework (CDS + behavior definitions + OData) for building services/apps, standard in BTP ABAP Environment. |
| ABAP | Advanced Business Application Programming | SAP's server-side language. "Highly recommended" in the posting; evidenced by your AMDP class, CDS stack and loader class. |
| ADT | ABAP Development Tools | The Eclipse-based IDE for modern ABAP/CDS development (mandatory for CDS — SE80 can't do it). |
| abapGit | — | Open-source Git client for ABAP; how your ABAP sources reach GitHub and survive trial resets. |
| OData | Open Data Protocol | REST-based standard for data APIs with metadata ($metadata), filtering, paging. V2 is legacy-common; **V4** is current — your service binding. "ODATA desirable" in the posting. |
| REST / API | Representational State Transfer / Application Programming Interface | General web-service style / general term for programmatic interfaces. OData is a REST-flavoured API standard. |
| UI5 / SAPUI5 | — | SAP's JavaScript UI framework (MVC, data binding, Fiori design language). Open-source sibling: OpenUI5. "UI5 desirable". |
| Fiori | — | SAP's UX design system and app strategy (role-based, responsive). "Fiori desirable". |
| Fiori Elements | — | Framework generating full Fiori apps from OData + CDS annotations (List Report, ALP, Object Page) with near-zero UI code — the productivity story you demo. |
| ALP | Analytical List Page | Fiori Elements floorplan combining KPI header, interactive chart and table — ideal for your budget-variance use case. |
| VizFrame / sap.viz | — | UI5's charting library, used in your freestyle view. |
| Mock server | — | Local stub serving frozen OData responses so the UI runs without a backend — how your GitHub Pages demo survives trial expiry. |
| SDA / SDI | Smart Data Access / Smart Data Integration | HANA's virtual-access and replication/transformation frameworks for remote sources — production alternatives to your CSV loads; name them in the mapping doc. |
| SLT | SAP Landscape Transformation (Replication Server) | Trigger-based real-time replication from SAP systems into HANA/BW — the classic real-time feed in Airbus-scale landscapes. |
| PlanViz | Plan Visualization | HANA's graphical execution-plan analyzer — your Phase 7 evidence tool alongside EXPLAIN PLAN. |
| Partition pruning | — | The optimiser skipping table partitions excluded by filters (e.g. date) — one of your three measured optimisations. |
| Materialisation / aggregate | — | Persisting pre-computed summary data to trade storage for query speed — optimisation #1 in Phase 7, with the freshness tradeoff recorded as an ADR. |

## D. Delivery method & project vocabulary

| Term | Stands for | Explanation & relevance |
|---|---|---|
| Agile | — | Iterative delivery in short increments with continuous feedback (posting: "agile or waterfall"). Your sprint-grouped backlog is the evidence. |
| Scrum | — | The most common agile framework: sprints, product owner, backlog, reviews. |
| Waterfall | — | Sequential phased delivery (requirements → build → test → deploy); still used for fixed-scope regulated projects — aerospace included. |
| Backlog / user story | — | Ordered list of desired outcomes / one requirement in "As a ⟨role⟩ I need ⟨capability⟩ so that ⟨benefit⟩" form. Phase 8. |
| MoSCoW | Must/Should/Could/Won't have | Prioritisation scheme; the "Won't" bucket is your official scope-creep defence. |
| Acceptance criteria | — | Testable conditions defining a story as done. |
| MVP | Minimum Viable Product | Smallest version delivering real value — your Phase 5 zero-code ALP before enhancements. |
| DoD | Definition of Done | Team checklist for "finished" (reviewed, documented, performant) — part of your golden rules. |
| UAT | User Acceptance Testing | Business-side validation before go-live; appears in your change-management plan. |
| Hypercare | — | Intensified support window right after go-live; also in the change plan. |
| ADR | Architecture Decision Record | Short document per significant decision (context/decision/consequences). Your `docs/adr/` folder — cheap to write, disproportionately impressive. |
| CI/CD | Continuous Integration / Continuous Delivery | Automated build-test-deploy pipelines; mention as the production-grade extension of your Git/abapGit setup. |
| STAR | Situation, Task, Action, Result | Interview answer structure for behavioural questions (Phase 9 prep sheet). |
| RACI | Responsible, Accountable, Consulted, Informed | Responsibility matrix; optional addition to the change-management plan. |
| Design Thinking | — | User-centred problem-framing method (empathise→define→ideate→prototype→test), listed as a required competency; your KPI-before-schema, persona-based backlog approach is the demonstration. |
| Change management | — | Structured handling of the *people* side of a new tool: communication, training, adoption tracking. Explicit responsibility in the posting; Phase 8 document. |
| JV / carve-out | Joint Venture / — | New jointly-owned company / extracting part of a company (systems included) into a separate entity. This position moves into the Space JV ~Sept 2026 — expect separation topics (system split, authorizations, data ownership) in interviews. |
| Export control classification | — | Regulatory classification of goods *and technical data* under regimes like EU dual-use rules or US ITAR/EAR. In aerospace BI this governs who may see which data in which country — listed as a required competency; acknowledge it in your change/security notes. Not legal advice; real cases go to the export-control officer. |
| Eco-design (of digital services) | — | Designing IT services to minimise resource/energy footprint (data volumes, compute, retention, scheduling). Required competency; Phase 7 report is your evidence. |

## E. Business-domain terms (finance, controlling & the month-end close)

| Term | Stands for | Explanation & relevance |
|---|---|---|
| FI | Financial Accounting | SAP module for the legal books: general ledger, payables, receivables, assets. The origin of most journal data in your model. |
| CO | Controlling | SAP module for internal/management accounting: cost centres, internal orders, allocations. FI answers "is it legal", CO answers "who caused it". |
| CO-PA | Controlling – Profitability Analysis | CO submodule analysing margin by market segment (customer, product, region). A classic BW extraction source in finance landscapes. |
| PS / WBS | Project System / Work Breakdown Structure (element) | How long-running engineering programmes are structured and costed in SAP; the WBS element is the account-assignment object for programme costs — the natural controlling object in aerospace. Your `DIM_PROGRAMME` imitates it. |
| GL / G/L account | General Ledger (account) | The account structure of the legal books; your `DIM_GL_ACCOUNT`. |
| Chart of accounts | — | The governed catalogue of G/L accounts an entity may post to. |
| P&L | Profit & Loss (statement) | The income statement; your account hierarchy (revenue → cost categories → result) reproduces its structure for reporting. |
| ACDOCA / Universal Journal | table ACDOCA | S/4HANA's single line-item table merging FI and CO into one journal. Your `FACT_JOURNAL` is deliberately shaped like it — instantly recognisable to anyone in an S/4-era finance BI team. |
| JE | Journal Entry | A posted accounting document (header + line items). Manual JEs at close are a data-quality and audit focal point — hence your KPI. |
| Document type | — | Classifies postings (e.g. SA = manual G/L entry, vs automatic payroll/depreciation/allocation types). The basis of the manual-vs-automatic analysis. |
| Fiscal year variant / posting period | — | Defines how a company's fiscal year maps to periods. Posting date ≠ fiscal period is precisely why "late postings" is measurable at all. |
| Special periods (13–16) | — | Extra periods after period 12 reserved for year-end adjustments and audit corrections. Modeling them correctly is a small detail with a big credibility payoff. |
| Month-end close / fast close | — | The monthly process of finalising the books; "fast close" initiatives aim to cut days-to-close. The central drama of your dashboard. |
| Soft close / hard close | — | Preliminary cut-off (reporting-ready) vs final locking of the period. Your late-postings KPI measures breaches of the soft-close cut-off. |
| Accrual | — | An expense recognised before the invoice exists — the typical manual JE at close, reversed the next period. |
| Allocation / assessment | — | CO mechanisms distributing overhead from support cost centres to consuming ones — the punctual "automatic postings" in your generator. |
| Cost centre (hierarchy) | — | Organisational unit collecting costs; the standard hierarchy is the backbone of management reporting and a BW hierarchy classic. |
| Internal order | — | A lightweight CO object collecting costs of a bounded activity — the small sibling of a WBS element. |
| Budget / forecast / version | — | Plan data coexisting in versions (Budget, Forecast, Actual). Version handling is the conceptual bridge between your SAC planning model and BPC. |
| Variance analysis | — | Decomposing actual-vs-plan differences into drivers (price, volume, FX, scope). What page 2 of your SAC story performs. |
| Run-rate | — | Recent actuals extrapolated forward (e.g. rolling 3 months, annualised) — the controller's quick health check, and your AMDP's job. |
| EAC / ETC | Estimate At Completion / Estimate To Complete | Programme-controlling staples: projected total cost at programme end / cost still to come. Your simple EAC = actuals to date + run-rate × remaining periods. |
| POC | Percentage Of Completion | Revenue-recognition method for long-term contracts. Mention-level in your docs; genuinely deep water beyond that — say so if asked. |
| Currency types | — | SAP amounts exist in parallel: document, local (company-code) and group currency. Your journal carries all three — and currency translation is a perennial BW/HANA interview topic. |
| FX impact | Foreign eXchange impact | The share of group-currency variance caused by rate movements rather than spending behaviour, isolated via a constant-rate comparison in `CV_FX_IMPACT`. |
| IC reconciliation | Intercompany reconciliation | Ensuring transactions between group entities net to zero before consolidation; unmatched pairs are the close team's grind and your data-quality KPI. |
| Days to close | — | Working days from period end until the books are final — the headline KPI of every fast-close initiative. |
| GDPR | General Data Protection Regulation | EU data-protection law. Finance BI touches it through posting user IDs and approver names; your design pseudonymises at source. A live topic in SAP landscape programmes. |
| Pseudonymisation | — | Replacing identifying values with tokens reversible only via a separately-held key, so analytics work without exposing persons. Applied to user IDs in `FACT_JOURNAL`. |
| DPO | Data Protection Officer | The role any real (non-synthetic) deployment touching personal data must involve. |

---

*End of roadmap. Copy into the repo as `ROADMAP.md`, tick boxes as you go, and let the document itself be part of the evidence.*
