from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from .performance_compare import PerformanceChange
from .task_lifecycle import (
    AUTO_RESOLUTION_NOTE,
    ensure_task_event_schema,
    reconcile_recovered_tasks,
    record_task_event,
    task_key_for_marketplace,
)


@dataclass(frozen=True, slots=True)
class DeclineTask:
    task_key: str
    marketplace: str
    alert_level: str
    movement: str
    profit_delta: str
    profit_change_rate: str | None
    recommended_action: str


def _task_key(change: PerformanceChange) -> str:
    return task_key_for_marketplace(change.marketplace)


def _recommended_action(change: PerformanceChange) -> str:
    if change.movement == "missing":
        return "Kanalın güncel dönem verisini, entegrasyon akışını ve satış görünürlüğünü kontrol et."
    if change.previous_profit == 0 and change.current_profit < 0:
        return "Komisyon, kargo, iskonto ve ürün maliyeti kalemlerini kontrol ederek zarar nedenini belirle."
    return "Satış adedi, fiyat, komisyon, kargo ve ürün maliyeti değişimlerini karşılaştır; kaybın ana nedenini kaydet."


def build_decline_tasks(changes: Iterable[PerformanceChange]) -> tuple[DeclineTask, ...]:
    tasks = []
    for change in changes:
        if change.alert_level != "critical":
            continue
        tasks.append(
            DeclineTask(
                task_key=_task_key(change),
                marketplace=change.marketplace,
                alert_level=change.alert_level,
                movement=change.movement,
                profit_delta=str(change.profit_delta),
                profit_change_rate=(
                    None if change.profit_change_rate is None else str(change.profit_change_rate)
                ),
                recommended_action=_recommended_action(change),
            )
        )
    return tuple(tasks)


def synchronize_decline_tasks(
    changes: Iterable[PerformanceChange], database: str | Path
) -> tuple[DeclineTask, ...]:
    destination = Path(database)
    destination.parent.mkdir(parents=True, exist_ok=True)
    change_list = tuple(changes)
    tasks = build_decline_tasks(change_list)
    now = datetime.now(UTC).isoformat()

    with sqlite3.connect(destination) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS marketplace_decline_tasks (
                task_key TEXT PRIMARY KEY,
                marketplace TEXT NOT NULL,
                alert_level TEXT NOT NULL,
                movement TEXT NOT NULL,
                profit_delta TEXT NOT NULL,
                profit_change_rate TEXT,
                recommended_action TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'OPEN',
                assignee TEXT NOT NULL DEFAULT '',
                resolution_note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_marketplace_decline_tasks_queue
            ON marketplace_decline_tasks(status, alert_level, marketplace)
            """
        )
        ensure_task_event_schema(connection)
        reconcile_recovered_tasks(connection, change_list)
        for task in tasks:
            existing = connection.execute(
                "SELECT status FROM marketplace_decline_tasks WHERE task_key = ?",
                (task.task_key,),
            ).fetchone()
            previous_status = None if existing is None else str(existing[0])
            connection.execute(
                """
                INSERT INTO marketplace_decline_tasks (
                    task_key, marketplace, alert_level, movement,
                    profit_delta, profit_change_rate, recommended_action,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_key) DO UPDATE SET
                    marketplace = excluded.marketplace,
                    alert_level = excluded.alert_level,
                    movement = excluded.movement,
                    profit_delta = excluded.profit_delta,
                    profit_change_rate = excluded.profit_change_rate,
                    recommended_action = excluded.recommended_action,
                    status = CASE
                        WHEN marketplace_decline_tasks.status = 'AUTO_RESOLVED' THEN 'OPEN'
                        ELSE marketplace_decline_tasks.status
                    END,
                    resolution_note = CASE
                        WHEN marketplace_decline_tasks.status = 'AUTO_RESOLVED'
                         AND marketplace_decline_tasks.resolution_note = ? THEN ''
                        ELSE marketplace_decline_tasks.resolution_note
                    END,
                    updated_at = excluded.updated_at
                """,
                (
                    task.task_key,
                    task.marketplace,
                    task.alert_level,
                    task.movement,
                    task.profit_delta,
                    task.profit_change_rate,
                    task.recommended_action,
                    now,
                    now,
                    AUTO_RESOLUTION_NOTE,
                ),
            )
            if previous_status is None:
                record_task_event(
                    connection,
                    task_key=task.task_key,
                    event_type="CREATED_CRITICAL",
                    previous_status="ABSENT",
                    new_status="OPEN",
                    note="Kritik alarm için operasyon görevi oluşturuldu.",
                    created_at=now,
                )
            elif previous_status == "AUTO_RESOLVED":
                record_task_event(
                    connection,
                    task_key=task.task_key,
                    event_type="REOPENED_CRITICAL",
                    previous_status="AUTO_RESOLVED",
                    new_status="OPEN",
                    note="Kanal yeniden kritik alarm seviyesine geldi.",
                    created_at=now,
                )
    return tasks
