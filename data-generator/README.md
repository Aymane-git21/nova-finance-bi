# Data generator

Seeded synthetic ERP data for the NovaSpace Group. **Built in Phase 2.3.**

## Contract

- `generate.py` writes one CSV per table into `output/` (git-ignored — regenerable).
- `samples/` holds a small committed slice of each table so the schema is readable on GitHub without running anything.
- Seed is fixed (`numpy.random.default_rng(42)`). Same seed → byte-identical output. Every number quoted anywhere in this repository traces back to this seed.
- No personal data: posting user IDs are pseudonymised at generation time, not afterwards.

## Realism requirements

The data has to feel like a real ERP to someone who lives in one. The generator deliberately builds in:

- 4 entities × 3 fiscal years × ~25k journal lines per month ≈ 1M lines
- Posting-date clustering: automatic postings (payroll, depreciation, allocations) land punctually; manual entries spike in the first 3–5 working days after period end, with a tail of genuinely late postings
- One entity chronically slow to close — a story the dashboard reveals rather than states
- One programme overspending against budget from mid-year onward
- FX drift on GBP/EUR, so group-currency variance ≠ local-currency variance
- Intercompany pairs netting to zero, except ~2 % deliberate mismatches
- Special periods 13–14 actually used for year-end adjustments

## Usage

```bash
python data-generator/generate.py
```

## Tests

Gate tests assert the invariants above — that the stories are actually present in the data, not just intended.

```bash
python -m pytest data-generator/tests -q
```
