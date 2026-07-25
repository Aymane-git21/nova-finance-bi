"""Dimension builders.

Every dimension is built once, up front, and the fact builders draw their
foreign keys from these frames rather than inventing values. That is what makes
the referential-integrity assertions in the test suite meaningful: they check a
guarantee the design provides, not a coincidence.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from . import config


def build_dim_company_code() -> pd.DataFrame:
    frame = pd.DataFrame(config.COMPANY_CODES)
    # size_weight is a generator knob, not part of the published dimension.
    return frame.drop(columns=["size_weight"])


def company_size_weights() -> dict[str, float]:
    return {c["company_code"]: c["size_weight"] for c in config.COMPANY_CODES}


def local_currencies() -> dict[str, str]:
    return {c["company_code"]: c["local_currency"] for c in config.COMPANY_CODES}


def soft_close_working_days() -> dict[str, int]:
    return {c["company_code"]: c["soft_close_working_day"] for c in config.COMPANY_CODES}


def build_users(rng: np.random.Generator) -> dict[str, list[str]]:
    """Pseudonymous posting users, per entity.

    These tokens are *generated*, not derived from any name. There is no source
    identity anywhere in the pipeline and therefore no re-identification key to
    protect - stricter than production pseudonymisation, and the reason
    docs/gdpr-and-data-protection.md can make an unqualified claim.
    """
    users: dict[str, list[str]] = {}
    seen: set[str] = set()
    for company in config.COMPANY_CODES:
        entity_users: list[str] = []
        while len(entity_users) < config.USERS_PER_ENTITY:
            token = f"USR-{rng.integers(0, 16**6):06X}"
            if token in seen:
                continue
            seen.add(token)
            entity_users.append(token)
        users[company["company_code"]] = entity_users
    return users


def build_dim_cost_center(
    rng: np.random.Generator, users: dict[str, list[str]]
) -> pd.DataFrame:
    """~200 leaf cost centres across a 3-level hierarchy.

    The hierarchy is stored both as a parent edge (``parent_id``) and as
    denormalised level attributes. Both access patterns are needed: recursive
    walking for a BW-style hierarchy, flat filtering inside a calculation view.
    """
    rows = []
    for company in config.COMPANY_CODES:
        entity = company["company_code"]
        entity_digits = entity[2:]
        entity_users = users[entity]
        sequence = 1001

        for division_code, division_name, division_is_overhead in config.DIVISIONS:
            division_id = f"{entity}-{division_code}"
            departments = config.DEPARTMENTS[division_code]
            name_pool = config.COST_CENTER_NAMES[division_code]
            name_cursor = 0

            for dept_index, department_name in enumerate(departments, start=1):
                department_id = f"{entity}-{division_code}-{dept_index:02d}"
                n_centres = int(rng.choice([3, 4, 5], p=[0.35, 0.45, 0.20]))

                for _ in range(n_centres):
                    base_name = name_pool[name_cursor % len(name_pool)]
                    repeat = name_cursor // len(name_pool)
                    centre_name = base_name if repeat == 0 else f"{base_name} {repeat + 1}"
                    name_cursor += 1

                    rows.append({
                        "cost_center": f"CC-{entity_digits}-{sequence}",
                        "cost_center_name": centre_name,
                        "company_code": entity,
                        "division_id": division_id,
                        "division_name": division_name,
                        "department_id": department_id,
                        "department_name": department_name,
                        "parent_id": department_id,
                        "hierarchy_level": 3,
                        "is_overhead": bool(division_is_overhead),
                        "valid_from": dt.date(config.FIRST_FISCAL_YEAR, 1, 1),
                        "valid_to": dt.date(9999, 12, 31),
                        "manager_user_id": entity_users[
                            int(rng.integers(0, len(entity_users)))
                        ],
                    })
                    sequence += 1

    return pd.DataFrame(rows)


def build_dim_programme() -> pd.DataFrame:
    return pd.DataFrame(config.PROGRAMMES)


def build_dim_gl_account() -> pd.DataFrame:
    """~150 P&L accounts under a 3-level hierarchy."""
    rows = []
    for group_code, group_name, pl_section, range_start, count, normal_balance in (
        config.ACCOUNT_GROUPS
    ):
        parts = config.ACCOUNT_NAME_PARTS[group_code]
        for index in range(count):
            base = parts[index % len(parts)]
            qualifier = config.ACCOUNT_QUALIFIERS[
                (index // len(parts)) % len(config.ACCOUNT_QUALIFIERS)
            ]
            rows.append({
                "gl_account": str(range_start + index * 10),
                "gl_account_name": f"{base} — {qualifier}",
                "account_group": group_code,
                "account_group_name": group_name,
                "pl_section": pl_section,
                "is_pl_account": True,
                "normal_balance": normal_balance,
            })
    return pd.DataFrame(rows)


def build_dim_close_task() -> pd.DataFrame:
    return pd.DataFrame(
        config.CLOSE_TASKS,
        columns=["task_id", "task_name", "task_sequence", "target_working_day", "is_milestone"],
    )
