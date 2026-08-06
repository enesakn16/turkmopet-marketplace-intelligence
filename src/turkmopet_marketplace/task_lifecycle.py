from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Iterable

from .performance_compare import PerformanceChange

AUTO_RESOLUTION_NOTE = "Kritik alarm güncel karşılaştırmada sona erdi."


def task_key_for_marketplace(marketplace: str) -> str:
    normalized = "-".join(marketplace.casefold().split())
    return f"marketplace-decline:{normalized}"


def reconcile_recovered_tasks(
    connection: sqlite3.Connection, changes: Iterable[PerformanceChange]
) -> int:
    now = datetime.now(UTC).isoformat()
    updated = 0
    for change in changes:
        if change.alert_level == "critical":
            continue
        cursor = connection.execute(
            """
            UPDATE marketplace_decline_tasks
            SET status = 'AUTO_RESOLVED',
                resolution_note = CASE
                    WHEN resolution_note = '' THEN ?
                    ELSE resolution_note
                END,
                updated_at = ?
            WHERE task_key = ?
              AND status IN ('OPEN', 'IN_PROGRESS')
            """,
            (AUTO_RESOLUTION_NOTE, now, task_key_for_marketplace(change.marketplace)),
        )
        updated += cursor.rowcount
    return updated
