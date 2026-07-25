"""CSV output with a stable, HANA-friendly text format.

The loader on the other side of these files types every column explicitly, so
the text form has to be unambiguous: ISO dates, lowercase booleans, empty string
for null, dot decimal separator, no thousands separator, UTF-8 without BOM.

Getting this wrong is the classic way a synthetic dataset loads fine locally and
then fails on import - so the formatting is centralised here rather than being
re-decided at every call site.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd


def _formatted(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for column in out.columns:
        series = out[column]

        if pd.api.types.is_bool_dtype(series):
            out[column] = series.map({True: "true", False: "false"})
            continue

        if pd.api.types.is_datetime64_any_dtype(series):
            out[column] = series.dt.strftime("%Y-%m-%d")
            continue

        if series.dtype == object:
            sample = series.dropna()
            if len(sample) and isinstance(sample.iloc[0], dt.date):
                out[column] = series.map(
                    lambda value: value.isoformat() if isinstance(value, dt.date) else value
                )
            elif len(sample) and isinstance(sample.iloc[0], bool):
                out[column] = series.map(
                    lambda value: {True: "true", False: "false"}.get(value, value)
                )
    return out


def write_csv(frame: pd.DataFrame, path: Path) -> int:
    """Write one table. Returns the row count."""
    path.parent.mkdir(parents=True, exist_ok=True)
    _formatted(frame).to_csv(
        path, index=False, encoding="utf-8", na_rep="", lineterminator="\n"
    )
    return len(frame)


def write_sample(frame: pd.DataFrame, path: Path, rows: int) -> int:
    """Write a small committed slice so the schema is readable on GitHub.

    Taken from the head rather than sampled at random: a contiguous slice keeps
    a document's lines together, which is what makes the sample legible.
    """
    return write_csv(frame.head(rows), path)
