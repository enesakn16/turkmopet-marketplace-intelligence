from __future__ import annotations

import sqlite3
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from turkmopet_marketplace.decline_tasks import synchronize_decline_tasks
from turkmopet_marketplace.performance_compare import PerformanceChange
from turkmopet_marketplace.task_lifecycle import AUTO_RESOLUTION_NOTE


class DeclineTaskLifecycleTests(unittest.TestCase):
    def change(self, alert_level: str, profit: str) -> PerformanceChange:
        current = Decimal(profit)
        return PerformanceChange(
            marketplace="Trendyol",
            previous_units_sold=10,
            current_units_sold=10,
            units_delta=0,
            previous_revenue=Decimal("5000"),
            current_revenue=Decimal("5000"),
            revenue_delta=Decimal("0"),
            previous_profit=Decimal("1000"),
            current_profit=current,
            profit_delta=current - Decimal("1000"),
            profit_change_rate=Decimal("-0.3000") if alert_level == "critical" else Decimal("-0.0200"),
            previous_margin=Decimal("0.2000"),
            current_margin=Decimal("0.1400"),
            margin_delta=Decimal("-0.0600"),
            movement="declined" if alert_level == "critical" else "stable",
            alert_level=alert_level,
        )

    def test_recovered_channel_auto_resolves_open_task(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "tasks.db"
            synchronize_decline_tasks([self.change("critical", "700")], database)
            synchronize_decline_tasks([self.change("stable", "980")], database)

            with sqlite3.connect(database) as connection:
                status, note = connection.execute(
                    "SELECT status, resolution_note FROM marketplace_decline_tasks"
                ).fetchone()

            self.assertEqual("AUTO_RESOLVED", status)
            self.assertEqual(AUTO_RESOLUTION_NOTE, note)

    def test_recovery_preserves_existing_operator_note(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "tasks.db"
            synchronize_decline_tasks([self.change("critical", "700")], database)
            with sqlite3.connect(database) as connection:
                connection.execute(
                    "UPDATE marketplace_decline_tasks SET status = 'IN_PROGRESS', resolution_note = 'Komisyon düzeltildi'"
                )
            synchronize_decline_tasks([self.change("warning", "900")], database)

            with sqlite3.connect(database) as connection:
                status, note = connection.execute(
                    "SELECT status, resolution_note FROM marketplace_decline_tasks"
                ).fetchone()

            self.assertEqual("AUTO_RESOLVED", status)
            self.assertEqual("Komisyon düzeltildi", note)

    def test_manual_resolution_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "tasks.db"
            synchronize_decline_tasks([self.change("critical", "700")], database)
            with sqlite3.connect(database) as connection:
                connection.execute(
                    "UPDATE marketplace_decline_tasks SET status = 'RESOLVED', resolution_note = 'Operatör kapattı'"
                )
            synchronize_decline_tasks([self.change("stable", "980")], database)

            with sqlite3.connect(database) as connection:
                status, note = connection.execute(
                    "SELECT status, resolution_note FROM marketplace_decline_tasks"
                ).fetchone()

            self.assertEqual("RESOLVED", status)
            self.assertEqual("Operatör kapattı", note)


if __name__ == "__main__":
    unittest.main()
