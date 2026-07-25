"""Shared pytest fixtures for the data generator.

The suite runs at reduced volume by default so it stays a gate test: the full
dataset takes tens of seconds to build, and a test nobody waits for is a test
nobody runs. Every structural property under test is a proportion or an
ordering, so it survives scaling.

    python -m pytest data-generator/tests -q           # fast, ~5s
    python -m pytest data-generator/tests -q --full    # the published dataset

Anything that only holds at full volume belongs behind ``--full`` and must say
so in its own docstring.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from novaspace.build import build_dataset  # noqa: E402


def pytest_addoption(parser):
    parser.addoption(
        "--full",
        action="store_true",
        default=False,
        help="build the full ~1M-line dataset instead of the fast reduced one",
    )


@pytest.fixture(scope="session")
def scale(request) -> float:
    return 1.0 if request.config.getoption("--full") else 0.05


@pytest.fixture(scope="session")
def dataset(scale):
    return build_dataset(scale=scale)


@pytest.fixture(scope="session")
def journal(dataset):
    return dataset.fact_journal
