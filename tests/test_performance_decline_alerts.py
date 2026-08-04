from __future__ import annotations

import csv
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from turkmopet_marketplace.performance_compare import (
    PerformanceSnapshot,
    compare_performance_periods,
    write_performance_changes,
)


class PerformanceDeclineAlertTests(unittest.TestCase):
    def snapshot(self, name: str, profit: str) -> PerformanceSnapshot:
        amount = Decimal(profit)
        return PerformanceSnapshot(
            marketplace=name,
            units_sold=10,
            revenue=Decimal("1000"),
            contribution_profit=amount,
            contribution_margin=amount / Decimal("1000"),
        )

    def test_classifies_critical_warning_and_stable_declines(self) -> None:
        previous = (
            self.snapshot("Trendyol", "100"),
            self.snapshot("Hepsiburada", "100"),
            self.snapshot("N11", "100"),
        )
        current = (
            self.snapshot("Trendyol", "75"),
            self.snapshot("Hepsiburada", "90"),
            self.snapshot("N11", "97"),
        )

        changes = compare_performance_periods(previous, current)
        by_name = {item.marketplace: item for item in changes}

        self.assertEqual(by_name["Trendyol"].alert_level, "critical")
        self.assertEqual(by_name["Trendyol"].profit_change_rate, Decimal("-0.2500"))
        self.assertEqual(by_name["Hepsiburada"].alert_level, "warning")
        self.assertEqual(by_name["N11"].alert_level, "stable")
        self.assertEqual(changes[0].marketplace, "Trendyol")

    def test_missing_channel_and_new_loss_are_critical(self) -> None:
        previous = (
            self.snapshot("Trendyol", "100"),
            self.snapshot("N11", "0"),
        )
        current = (self.snapshot("N11", "-20"),)

        changes = compare_performance_periods(previous, current)
        by_name = {item.marketplace: item for item in changes}

        self.assertEqual(by_name["Trendyol"].movement, "missing")
        self.assertEqual(by_name["Trendyol"].alert_level, "critical")
        self.assertIsNone(by_name["N11"].profit_change_rate)
        self.assertEqual(by_name["N11"].alert_level, "critical")

    def test_custom_thresholds_are_validated_and_applied(self) -> None:
        previous = (self.snapshot("Trendyol", "100"),)
        current = (self.snapshot("Trendyol", "88"),)

        changes = compare_performance_periods(
            previous,
            current,
            critical_decline=Decimal("0.10"),
            warning_decline=Decimal("0.02"),
        )
        self.assertEqual(changes[0].alert_level, "critical")

        with self.assertRaisesRegex(ValueError, "Uyarı eşiği"):
            compare_performance_periods(
                previous,
                current,
                critical_decline=Decimal("0.05"),
                warning_decline=Decimal("0.10"),
            )

    def test_csv_contains_alert_fields_and_utf8_bom(self) -> None:
        changes = compare_performance_periods(
            (self.snapshot("Trendyol", "100"),),
            (self.snapshot("Trendyol", "75"),),
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "alerts.csv"
            write_performance_changes(changes, output)

            self.assertTrue(output.read_bytes().startswith(b"\xef\xbb\xbf"))
            with output.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(rows[0]["profit_change_rate"], "-0.2500")
        self.assertEqual(rows[0]["alert_level"], "critical")


if __name__ == "__main__":
    unittest.main()
