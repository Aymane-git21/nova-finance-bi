# Development golden rules

The standards this project actually follows. Every rule below is one this repository obeys — where a rule was broken, the deviation is recorded rather than the rule quietly softened.

---

## 1. Naming

| Prefix | Object | Layer |
|---|---|---|
| `NOVASPACE_RAW` | Loaded tables | Inbound |
| `NOVASPACE_L1.V_*` | 1:1 views | Staging |
| `NOVASPACE_L2.V_*` | Harmonised views | Propagation |
| `NOVASPACE_L3.CV_*` | Reporting views | Virtual mart |
| `NOVASPACE_L3.TF_*` | Table functions | Virtual mart |
| `NOVASPACE_API.V_*` | Interface views | Published contract |
| `ZTNS_*` | ABAP tables | ABAP stack |
| `ZI_*` | Interface / composite CDS views | ABAP stack |
| `ZC_*` | Consumption CDS views | ABAP stack |
| `ZCL_*` | ABAP classes | ABAP stack |
| `ZSD_` / `ZSB_` | Service definition / binding | ABAP stack |

The prefix says which layer an object belongs to, so a reviewer knows what rules apply to it before opening it.

---

## 2. Layer rules

- **No joins in L1.** Projection and type casting only. The restraint is the payoff: when a number is wrong, L1 is the layer you can eliminate without reading it, because there is nothing in it capable of being wrong.
- **All business logic in L2.** Signed amounts, derived flags, currency translation, master-data joins. One place, one definition.
- **L3 aggregates; it does not invent.** A calculation appearing for the first time in L3 belongs in L2.
- **The API layer contains no logic at all.** If a calculation appears there, the layering has broken down.
- **No business logic in the UI.** Criticality thresholds are computed in `NOVASPACE_API`, not in a JavaScript formatter. The formatter maps a number to a colour and does nothing else.
- **Consumers bind to the published contract**, never to internal modelling. L3 can be refactored freely; `NOVASPACE_API` is the promise.

---

## 3. One definition per concept

Every KPI has exactly one authoritative implementation, and everything else must reproduce it.

The reference implementation is [`data-generator/novaspace/harmonise.py`](../data-generator/novaspace/harmonise.py), because it has a test suite behind it. The SQL must agree with it, and `hana/verify_against_python.py` proves that on every run — 24 checks over the same seeded dataset.

**This is the rule that has paid for itself most.** Two independent implementations of the same eight KPIs caught three defects that no dashboard would ever have contradicted: FX impact overstated by €6 900, budget variance computed at two different grains, and a full-year budget flattering an open year by 43 %.

A number that only one implementation produces is a number nobody has checked.

---

## 4. Definition of done

A change is done when **all** of these are true:

- [ ] Tests in the same commit, not the next one.
- [ ] A bug fix ships with a test that would have caught it.
- [ ] The full-scale test lane passes, not only the fast one.
- [ ] Docs updated in the same commit if behaviour changed.
- [ ] Generated figures regenerated, never hand-edited.
- [ ] The commit message states what was **not** done and why, if anything was cut.

### Two test lanes, different budgets

| Lane | Command | Time | Runs |
|---|---|---|---|
| Fast | `pytest data-generator/tests -q` | ~10 s | Every commit |
| Full | `pytest data-generator/tests -q --full` | ~45 s | Before every commit touching the generator |

**The full lane is not optional.** Two defects passed the fast lane and were caught only at full volume: intercompany mismatches injected per line rather than per pair (89 % of pairs failed to reconcile at scale), and a perturbation magnitude that fell below the materiality threshold once amounts were realistic. Bugs whose symptoms scale with volume are invisible to a reduced-scale run **by construction**.

---

## 5. Numbers in documentation are generated

Documentation drifts from data silently. Measured figures come from [`data-generator/profile_dataset.py`](../data-generator/profile_dataset.py) into [`dataset-profile.md`](dataset-profile.md), and other documents cite that file rather than restating numbers.

A figure typed into a document by hand is correct exactly once.

---

## 6. Reproducibility

- One fixed seed. Same seed, byte-identical CSVs — asserted, not assumed.
- **RNG call order is the contract.** New builders go at the *end* of `build_dataset`. Reordering existing ones invalidates every number ever published.
- A story that only exists under seed 42 is a coincidence, not a design. Asserted across three seeds.

---

## 7. Honesty rules

The ones that matter most in a portfolio, because the incentive runs the other way.

- **Unactivated code is labelled in every file.** All 21 ABAP sources carry `NOT ACTIVATED`, and `abap/check_sources.py` fails if one loses it.
- **A substitute is named as a substitute.** The OData service is CAP and is called CAP, never ABAP.
- **Cut scope is recorded, not omitted.** Excel and planning write-back have an ADR explaining why they do not exist.
- **A constraint gets one short document, paired with what shipped instead.** Three "blocked by" records could read as excuses; each is one page and each names a delivered artifact.
- **Null is not zero.** An open period reports as open, at every layer including the screen. Reporting an unfinished close as a zero-day close is the single most misleading number this model could produce.

---

## 8. Security and data protection

- No credential in the repository. Generated at setup, written mode 600, git-ignored — `hana/.hxe-credentials`, `cap/.cdsrc-private.json`.
- One source of truth for credentials; other configs derive from it rather than duplicating.
- **Pseudonymous user IDs stop at the table layer.** Enforced by `check_sources.py`, not left to memory.
- No personal data anywhere: user tokens are generated, never mapped from a name, so no re-identification key exists.

---

## 9. Where these rules were broken

Recorded because a standards document with no exceptions is not being applied.

| Rule | Deviation | Why |
|---|---|---|
| Consumers bind to the published contract | `hana/sql/06_cap_service_views.sql` creates views named `ANALYTICSSERVICE_*` | CAP compiles service entities to database views and queries those. The naming is dictated by CAP, not chosen. Pure aliases, no logic |
| No hand-written serialisation | `.srvb.xml` and `.devc.xml` are hand-written | abapGit serialises these as XML and there was no system to export from. The deviation is stated in `abap/README.md` |
| Docs cite generated figures | `bi-roadmap.md` cites SAP maintenance dates from the vendor | External facts, verified against SAP's Statement of Direction and dated in the document |
