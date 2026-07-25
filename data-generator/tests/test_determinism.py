"""The seed is a promise.

Every figure this repository quotes - in the KPI sheet, the data dictionary, the
performance report, the SAC story - traces back to one seeded run. If the
generator is not reproducible, none of those numbers can be checked by anyone,
including its author, and the claim that they are reproducible becomes the most
damaging thing in the repository.

These tests build the dataset more than once, so they run at a smaller scale
than the rest of the suite. Reproducibility is a property of the RNG plumbing,
not of the volume.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from novaspace import config
from novaspace.build import build_dataset
from novaspace.writer import write_csv

TINY = 0.02


@pytest.fixture(scope="module")
def first():
    return build_dataset(seed=config.SEED, scale=TINY)


@pytest.fixture(scope="module")
def second():
    return build_dataset(seed=config.SEED, scale=TINY)


def test_the_same_seed_reproduces_every_table_exactly(first, second):
    for name in first.tables:
        pd.testing.assert_frame_equal(
            first.tables[name],
            second.tables[name],
            check_exact=True,
            obj=name,
        )


def test_the_same_seed_reproduces_the_sac_extracts(first, second):
    left, right = first.sac_tables(), second.sac_tables()
    assert left.keys() == right.keys()
    for name in left:
        pd.testing.assert_frame_equal(left[name], right[name], obj=name)


def test_a_different_seed_produces_different_data(first):
    other = build_dataset(seed=config.SEED + 1, scale=TINY)
    assert not np.allclose(
        first.fact_journal["amount_group_currency"].head(1000).to_numpy(),
        other.fact_journal["amount_group_currency"].head(1000).to_numpy(),
    )
    # Structure must survive the seed change even though values do not.
    assert list(first.fact_journal.columns) == list(other.fact_journal.columns)


def test_the_stories_survive_a_change_of_seed(first):
    """A story that only exists under seed 42 is a coincidence, not a design.

    This is the test that distinguishes "the generator builds this in" from
    "this run happened to look like that".
    """
    from novaspace.harmonise import days_to_close, is_manual_posting

    for seed in (config.SEED, config.SEED + 1, config.SEED + 7):
        data = build_dataset(seed=seed, scale=TINY)

        closes = days_to_close(data.fact_close_tasks, data.working_days)
        by_entity = closes.groupby("company_code")["days_to_close"].mean()
        assert by_entity.idxmax() == config.SLOW_CLOSE_ENTITY, seed

        frame = data.fact_journal[data.fact_journal["fiscal_period"] <= 12].copy()
        frame["manual"] = is_manual_posting(frame)
        assert frame.groupby("company_code")["manual"].mean().idxmax() == (
            config.SLOW_CLOSE_ENTITY
        ), seed


def test_csv_output_is_byte_identical_across_runs(first, second, tmp_path):
    """Reproducibility has to survive serialisation, not just stay in memory."""
    left = tmp_path / "left.csv"
    right = tmp_path / "right.csv"
    write_csv(first.fact_journal, left)
    write_csv(second.fact_journal, right)
    assert left.read_bytes() == right.read_bytes()


def test_csv_output_uses_the_documented_text_format(first, tmp_path):
    path = tmp_path / "journal.csv"
    write_csv(first.fact_journal.head(500), path)
    text = path.read_text(encoding="utf-8")
    header, *rows = text.strip().split("\n")

    assert header.startswith("journal_id,company_code,document_number")
    # Lowercase booleans, ISO dates, empty string for null.
    assert ",true," in text or ",false," in text
    assert "True" not in text and "False" not in text
    # Nulls serialise as empty, never as "None" or "nan".
    assert "None" not in text
    assert "nan" not in text
    sample = rows[0].split(",")
    assert len(sample) == len(first.fact_journal.columns)
