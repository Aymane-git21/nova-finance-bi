# Data generator

Seeded synthetic ERP data for the NovaSpace Group. **Phase 2 — complete.**

Produces ~1.12 M ACDOCA-shaped journal lines plus plan data, close-task history and curated SAC extracts, for a fictional four-entity space group of roughly €940 m annual revenue. All data is synthetic and reproducible; no real or client data is used, referenced or approximated.

## Usage

```bash
python data-generator/generate.py
```

Writes full CSVs to `output/` (git-ignored, regenerable in ~25 s), SAC extracts to `output/sac/`, and 200-row slices of every table to `samples/` so the schema is readable on GitHub without running anything.

```bash
python data-generator/profile_dataset.py > docs/dataset-profile.md
```

Regenerates [`docs/dataset-profile.md`](../docs/dataset-profile.md) — every measured figure the documentation quotes. Read-only.

Useful flags: `--scale 0.05` for a fast partial build, `--seed N` to vary the run, `--no-samples` to skip the committed slices.

## Contract

- **Fixed seed** (`numpy.random.default_rng(42)`). Same seed, byte-identical CSVs — asserted, not assumed.
- **RNG call order is the reproducibility contract.** New builders go at the *end* of `build_dataset`. Reordering existing ones invalidates every number this repository has published.
- **No personal data.** Posting users are opaque `USR-XXXXXX` tokens generated directly. No name is ever produced, mapped or stored, so no re-identification key exists — stricter than production pseudonymisation.
- **No derived flags in the facts.** `is_manual_posting`, `is_late_posting` and signed amounts are L2 concerns and live in `novaspace/harmonise.py`.

## Layout

| Module | Responsibility |
|---|---|
| `config.py` | Every constant, with the reasoning for each calibration |
| `calendar_.py` | Fiscal calendar and working-day arithmetic |
| `dimensions.py` | Entities, cost-centre hierarchy, programmes, accounts, users |
| `rates.py` | Monthly FX at actual and frozen budget rates |
| `journal.py` | `FACT_JOURNAL`: documents, intercompany mirrors, accrual reversals |
| `close.py` | `FACT_CLOSE_TASKS` |
| `plan.py` | `FACT_BUDGET` and `FACT_FORECAST`, derived from actuals |
| `programme_budget.py` | Lifetime programme budgets, derived after the journal exists |
| `harmonise.py` | **The L2 layer in Python** — the reference implementation of all eight KPIs |
| `sac_extracts.py` | Curated aggregates for the import-only SAC tenant |
| `writer.py` | CSV format: ISO dates, lowercase booleans, empty-string nulls |

`harmonise.py` is the one worth knowing about: it is the specification the HANA L2/L3 views and the AMDP must reproduce. Having the expected answer in Python first makes "does the SQLScript agree" a checkable question rather than a matter of opinion.

## Tests

```bash
python -m pytest data-generator/tests -q
```

102 tests, ~9 s. Runs at 5 % volume by default — every property under test is a proportion or an ordering, so it survives scaling.

```bash
python -m pytest data-generator/tests -q --full
```

Same 102 tests against the full ~1.12 M-line dataset, ~45 s. **Run this before committing generator changes.** Two defects reached the fast suite untouched and were caught only here: intercompany mismatches injected per line rather than per pair (89 % of pairs failed to reconcile at full volume), and a perturbation magnitude that fell below the materiality threshold once amounts were scaled to a realistic group size. Bugs whose symptoms scale with volume are invisible to a reduced-scale run by construction.

The suite covers four things:

- **`test_calendar.py`** — working-day arithmetic against dates verifiable by hand. Both KPI-01 and KPI-03 are defined in working days after period end; an off-by-one here would be wrong by a constant nobody would notice on a dashboard.
- **`test_integrity.py`** — every invariant [`../docs/data-dictionary.md`](../docs/data-dictionary.md) promises: keys, foreign keys, date ordering, the currency-translation chain, sign conventions, reversal semantics, pseudonymisation.
- **`test_stories.py`** — the six data stories are actually present and strong enough to see. A story that was intended but not generated is worse than none: the dashboard comes out flat and the generator ran without error.
- **`test_kpis.py`** — all eight KPIs compute and land inside their published ranges. Doubles as executable documentation of the formulas.
- **`test_determinism.py`** — same seed reproduces every table and every byte of CSV; different seeds change the values but keep the stories. A story that only exists under seed 42 is a coincidence, not a design.
