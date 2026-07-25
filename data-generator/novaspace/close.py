"""FACT_CLOSE_TASKS - the close checklist, entity by entity, period by period.

KPI-01 (days to close) reads the completion of T12 here, and KPI-03 reads the
completion of T10 to establish each entity's reporting cut-off. Those two tasks
are flagged ``is_milestone`` in the catalogue precisely so that the dependency
is visible in the model rather than buried in a WHERE clause.

The last period deliberately leaves the slow entity's final tasks incomplete.
A close cockpit whose data never contains an open period has never been tested
against the case it exists to show.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .calendar_ import WorkingDays, covered_periods, period_end_date


def build_fact_close_tasks(
    rng: np.random.Generator,
    working_days: WorkingDays,
    users: dict[str, list[str]],
) -> pd.DataFrame:
    periods = covered_periods()
    final_period = periods[-1]

    delay_choices = np.array(config.CLOSE_DELAY_CHOICES)
    delay_weights = np.array(config.CLOSE_DELAY_WEIGHTS, dtype=float)
    delay_weights = delay_weights / delay_weights.sum()

    rows = []
    for company in config.COMPANY_CODES:
        entity = company["company_code"]
        is_slow = entity == config.SLOW_CLOSE_ENTITY
        entity_users = users[entity]

        for fiscal_year, fiscal_period in periods:
            end = period_end_date(fiscal_year, fiscal_period)

            for task_id, _name, sequence, target_wd, _milestone in config.CLOSE_TASKS:
                due = working_days.nth_after(end, target_wd)

                delay = int(rng.choice(delay_choices, p=delay_weights))
                if is_slow:
                    delay += int(rng.integers(*config.SLOW_ENTITY_CLOSE_DELAY))

                actual_wd = max(1, target_wd + delay)

                # The most recent period is still open for the slow entity:
                # its reporting pack and period lock have not happened yet.
                still_open = (
                    is_slow
                    and (fiscal_year, fiscal_period) == final_period
                    and sequence >= 11
                )

                if still_open:
                    actual = None
                    delay_working_days = None
                    completed_by = None
                else:
                    actual = working_days.nth_after(end, actual_wd)
                    delay_working_days = actual_wd - target_wd
                    completed_by = entity_users[
                        int(rng.integers(0, len(entity_users)))
                    ]

                rows.append({
                    "company_code": entity,
                    "fiscal_year": fiscal_year,
                    "fiscal_period": fiscal_period,
                    "task_id": task_id,
                    "period_end_date": end,
                    "due_date": due,
                    "actual_completion_date": actual,
                    "completed_by_user_id": completed_by,
                    "delay_working_days": delay_working_days,
                })

    frame = pd.DataFrame(rows)
    frame.insert(0, "close_task_id", np.arange(1, len(frame) + 1, dtype=np.int64))
    return frame
