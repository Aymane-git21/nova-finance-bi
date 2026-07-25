# BI roadmap & legacy migration decision matrix

**NovaSpace Group — analytics landscape strategy**
Written 2026-07-26. Maintenance dates verified against SAP's Analytics BI Statement of Direction (July 2025 update).

---

## The deadline that shapes everything

**SAP BusinessObjects BI 4.3 mainstream maintenance ends 31 December 2026 — five months from now.** Security fixes continue for one further year; from the end of 2027 the only option is Customer-Specific Maintenance, which is a commercial arrangement rather than a product strategy.

The widely-repeated "BO is supported until 2031" is true and is routinely misapplied. That commitment attaches to the **BusinessObjects BI platform via the 2025 / 2027 / 2029 release line**, not to 4.3. An organisation sitting on 4.3 does not have until 2031; it has until this December, and then a year of security-only.

This single distinction is the difference between a roadmap that is five years out and one that is five months out. Anyone presenting a migration plan that assumes 2031 without checking which release the estate is actually on has mis-scoped the problem.

**Consequence for NovaSpace:** the first decision is not *whether* to move to SAC. It is **upgrade the BO platform to the 2025 line first**, which buys maintenance to 2031 and converts a deadline into a runway. Migration of individual tools then proceeds on merit rather than under duress.

---

## Current state

| Layer | Today | Population | Notes |
|---|---|---|---|
| Warehouse | BW on HANA | — | Feeds everything below |
| Ad-hoc reporting | Web Intelligence on `.unx` universes | Largest by far | SAP's stated ongoing investment target |
| Pixel-perfect output | Crystal Reports | Small, operational | Also an ongoing investment target |
| Excel-based analysis | Analysis for Office | Finance and controlling — the population in this project | Maintained, **no new features** |
| Dashboards | Lumira Designer | Small, IT-built | Maintained, **no new features** |
| Cloud analytics | — | — | Not yet present |

## Target state

| Layer | Target | Rationale |
|---|---|---|
| Warehouse | BW/4HANA, or HANA-native marts where BW's governance is not needed | See [`bw4hana-mapping.md`](bw4hana-mapping.md) for what BW actually provides that a native build must reinvent |
| Ad-hoc reporting | **Web Intelligence, retained** | Named in the Statement of Direction as an ongoing investment. Migrating the largest report population away from a product SAP is still investing in is cost without benefit |
| Pixel-perfect output | **Crystal Reports, retained** | Same reasoning. Nothing in SAC replaces a print-oriented invoice |
| Excel-based analysis | AfO retained near-term, SAC-with-Excel-add-in evaluated | The hardest population to move. See below |
| Dashboards | **SAC stories** | Lumira is feature-frozen and SAC is where dashboarding went |
| Embedded analytics | Fiori Elements on CDS | New build, not migration |

---

## Migration decision matrix

| Tool | Verdict | Maintenance reality | Criteria driving the verdict | Sequencing |
|---|---|---|---|---|
| **BO BI platform** | **Upgrade** to 2025 line | 4.3 mainstream ends 2026-12-31; 2025 line maintained ≥ 2031 | Non-negotiable — it is a deadline, not a preference. Everything else depends on it | **Now.** Blocks every other decision |
| **Web Intelligence** | **Keep** | Ongoing SAP investment | Largest user population; strong ad-hoc self-service; `.unx` semantic layer is an asset, not debt. No SAC feature makes this migration pay for itself | Re-evaluate 2029 |
| **Crystal Reports** | **Keep** | Ongoing SAP investment | Print-oriented operational documents. SAC has no equivalent and is not trying to have one | Re-evaluate 2029 |
| **`.unv` universes** | **Migrate** to `.unx` | Only single-source `.unx` is in SAP's investment scope | Prerequisite for the platform upgrade. Mechanical but not trivial at volume | With the platform upgrade |
| **Lumira Designer** | **Migrate** to SAC | Maintained, **no new features** | Small population, IT-built, so migration cost is bounded and lands on a team rather than on end users. Feature-frozen means the gap widens every year | 2027, after the platform upgrade lands |
| **Analysis for Office** | **Keep near-term, plan the exit** | Maintained, **no new features** | The hard one. See below | Evaluate 2027, decide 2028 |
| **SAC** | **Adopt** for dashboarding and planning | Strategic | New capability, not a replacement | Pilot alongside the Lumira migration |

### Why Analysis for Office is the hard one

It is the tool this project's user population actually lives in, and every instinct to "just migrate it to SAC" underestimates it:

- **The attachment is to Excel, not to AfO.** A controller who has built a personal reconciliation workbook over five years is not using a reporting tool; they are using a spreadsheet that happens to fetch data. Replacing the fetch mechanism is easy. Replacing the workbook is not, and is not yours to replace.
- **Feature-frozen is not the same as broken.** AfO is maintained. There is no forced date, so migration must be justified on value, and today it cannot be.
- **The honest position:** keep it, monitor SAC's Excel add-in maturity, and revisit in 2027 once the platform upgrade and Lumira migration are done. Moving three populations at once is how a migration programme fails.

Anyone proposing a hard AfO cutover should be asked what happens to the workbooks. If there is no answer, there is no plan.

---

## Sequencing

| When | What | Why in this order |
|---|---|---|
| **2026 H2** | BO platform 4.3 → 2025 line; `.unv` → `.unx` | Hard deadline. Everything else waits |
| **2027 H1** | SAC tenant, governance, first stories. Lumira Designer migration | Smallest, most contained population — proves the platform before touching end users |
| **2027 H2** | SAC Planning pilot on one entity's budget cycle | Planning is a process change, not a tool change. One entity, one cycle, real users |
| **2028** | AfO decision point | After two successful migrations and with SAC's Excel story matured |
| **Ongoing** | Fiori Elements embedded analytics for new build | Greenfield. No migration involved |

**The rule behind the order:** migrate the population that can absorb disruption before the population that cannot. IT-built dashboards first, finance's daily workbooks last.

---

## What this roadmap deliberately does not say

- **No "everything to the cloud by 20XX".** WebI and Crystal are named ongoing investments. A roadmap that retires them is following fashion, not the vendor's actual direction.
- **No business case attached.** The numbers depend on licence position, headcount and estate size, none of which are known here. A migration matrix with invented ROI is worse than one without.
- **No Datasphere / Business Data Cloud commitment.** Both are relevant to the warehouse conversation and neither is on the critical path for a five-month platform deadline. Worth a separate evaluation once 2026 H2 lands.
- **No claim of SAC hands-on.** This project could not demonstrate it — see [`sac-and-bpc.md`](sac-and-bpc.md).

---

## The JV angle

This position moves into a Space joint venture around September 2026, which lands **in the middle of the platform-upgrade window**. That is the most important interaction in this document and it cuts both ways:

- **Argument for moving first:** upgrading before separation means one estate to upgrade rather than two, and one project rather than two.
- **Argument against:** a carve-out will re-cut authorisations, data ownership and export-control classification anyway. Upgrading first means doing that work twice.
- **The resolution:** the platform upgrade is not optional and not deferrable, so it proceeds. What *is* deferrable is the SAC and Lumira work, and that should wait until the separation design is known — otherwise you build stories on an authorisation model that is about to change.

Carve-out considerations that land directly on this landscape:

| Concern | Why it lands here |
|---|---|
| **Authorisations** | BW analysis authorisations are expressed in characteristic values — company code, cost centre. A JV split re-cuts exactly those values, so the security model is rebuilt, not copied |
| **Data ownership** | Which entity owns historical actuals for a programme that transfers to the JV? A reporting question with legal consequences |
| **Export-control classification** | Aerospace technical data is regulated. Reports carrying programme-level detail may be classified, and who may see which report in which country becomes a compliance control, not a preference |
| **System separation** | Two tenants, or one with row-level separation? The second is cheaper and harder to defend to an auditor |

The right instinct is that none of these are BI problems that BI can solve alone. They are decided with the export-control officer, legal and the data owners, and the BI team's job is to make the consequences visible early enough to matter.
