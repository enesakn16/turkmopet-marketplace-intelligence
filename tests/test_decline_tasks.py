from __future__ import annotations

import sqlite3
import tempfile
import unittest
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from turkmopet_marketplace.decline_tasks import (
    build_decline_tasks,
    synchronize_decline_tasks,
)
from turkmopet_marketplace.performance_compare import PerformanceChange


class DeclineTaskTests(unittest.TestCase):
    def change(
        self,
        *,
        marketplace: str = "Trendyol",
        alert_level: str = "critical",
        movement: str = "declined",
        previous_profit: str = "1000",
        current_profit: str = "700",
        profit_change_rate: str | None = "-0.3000",
    ) -> PerformanceChange:
        previous = Decimal(previous_profit)
        current = Decimal(current_profit)
        return PerformanceChange(
            marketplace=marketplace,
            previous_units_sold=10,
            current_units_sold=7,
            units_delta=-3,
            previous_revenue=Decimal("5000.00"),
            current_revenue=Decimal("4000.00"),
            revenue_delta=Decimal("-1000.00"),
            previous_profit=previous,
            current_profit=current,
            profit_delta=current - previous,
            profit_change_rate=(
                None if profit_change_rate is None else Decimal(profit_change_rate)
            ),
            previous_margin=Decimal("0.2000"),
            current_margin=Decimal("0.1750"),
            margin_delta=Decimal("-0.0250"),
            movement=movement,
            alert_level=alert_level,
        )

    def test_builds_tasks_only_for_critical_changes(self) -> None:
        tasks = build_decline_tasks(
            [self.change(), self.change(marketplace="N11", alert_level="warning")]
        )

        self.assertEqual(1, len(tasks))
        self.assertEqual("marketplace-decline:trendyol", tasks[0].task_key)
        self.assertEqual("-300", tasks[0].profit_delta)

    def test_missing_channel_gets_integration_action(self) -> None:
        task = build_decline_tasks(
            [
                self.change(
                    movement="missing",
                    current_profit="0",
                    profit_change_rate="-1.0000",
                )
            ]
        )[0]

        self.assertIn("entegrasyon", task.recommended_action)

    def test_repeat_sync_preserves_manual_workflow_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "tasks.db"
            original = self.change()
            synchronize_decline_tasks([original], database)

            with sqlite3.connect(database) as connection:
                connection.execute(
                    """
                    UPDATE marketplace_decline_tasks
                    SET status = 'IN_PROGRESS', assignee = 'enes',
                        resolution_note = 'Komisyon kontrol ediliyor'
                    WHERE task_key = ?
                    """,
                    ("marketplace-decline:trendyol",),
                )
                created_at = connection.execute(
                    "SELECT created_at FROM marketplace_decline_tasks WHERE task_key = ?",
                    ("marketplace-decline:trendyol",),
                ).fetchone()[0]

            updated = replace(
                original,
                current_profit=Decimal("600"),
                profit_delta=Decimal("-400"),
                profit_change_rate=Decimal("-0.4000"),
            )
            synchronize_decline_tasks([updated], database)

            with sqlite3.connect(database) as connection:
                row = connection.execute(
                    """
                    SELECT status, assignee, resolution_note, profit_delta, created_at
                    FROM marketplace_decline_tasks WHERE task_key = ?
                    """,
                    ("marketplace-decline:trendyol",),
                ).fetchone()

            self.assertEqual("IN_PROGRESS", row[0])
            self.assertEqual("enes", row[1])
            self.assertEqual("Komisyon kontrol ediliyor", row[2])
            self.assertEqual("-400", row[3])
            self.assertEqual(created_at, row[4])

    def test_different_marketplaces_create_distinct_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "tasks.db"
            synchronize_decline_tasks(
                [self.change(), self.change(marketplace="Hepsiburada")], database
            )

            with sqlite3.connect(database) as connection:
                count = connection.execute(
                    "SELECT COUNT(*) FROM marketplace_decline_tasks"
                ).fetchone()[0]

            self.assertEqual(2, count)


if __name__ == "__main__":
    unittest.main()
