from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Iterable

from .performance_compare import PerformanceChange

AUTO_RESOLUTION_NOTE = "Kritik alarm güncel karşılaştırmada sona erdi."


def task_key_for_marketplace(marketplace: str) -> str:
    normalized = "-".join(marketplace.casefold().split())
    return f"marketplace-decline:{normalized}"


def ensure_task_event_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS marketplace_decline_task_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_key TEXT NOT NULL,
            event_type TEXT NOT NULL,
            previous_status TEXT NOT NULL,
            new_status TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_marketplace_decline_task_events_task
        ON marketplace_decline_task_events(task_key, created_at, event_id)
        """
    )


def record_task_event(
    connection: sqlite3.Connection,
    *,
    task_key: str,
    event_type: str,
    previous_status: str,
    new_status: str,
    note: str = "",
    created_at: str | None = None,
) -> None:
    ensure_task_event_schema(connection)
    connection.execute(
        """
        INSERT INTO marketplace_decline_task_events (
            task_key, event_type, previous_status, new_status, note, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            task_key,
            event_type,
            previous_status,
            new_status,
            note,
            created_at or datetime.now(UTC).isoformat(),
        ),
    )


def reconcile_recovered_tasks(
    connection: sqlite3.Connection, changes: Iterable[PerformanceChange]
) -> int:
    ensure_task_event_schema(connection)
    now = datetime.now(UTC).isoformat()
    updated = 0
    for change in changes:
        if change.alert_level == "critical":
            continue
        task_key = task_key_for_marketplace(change.marketplace)
        existing = connection.execute(
            "SELECT status FROM marketplace_decline_tasks WHERE task_key = ?",
            (task_key,),
        ).fetchone()
        if existing is None or existing[0] not in ("OPEN", "IN_PROGRESS"):
            continue
        previous_status = str(existing[0])
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
            (AUTO_RESOLUTION_NOTE, now, task_key),
        )
        if cursor.rowcount:
            record_task_event(
                connection,
                task_key=task_key,
                event_type="AUTO_RESOLVED",
                previous_status=previous_status,
                new_status="AUTO_RESOLVED",
                note=AUTO_RESOLUTION_NOTE,
                created_at=now,
            )
            updated += cursor.rowcount
    return updated
