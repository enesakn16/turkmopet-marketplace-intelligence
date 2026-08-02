from __future__ import annotations

import csv
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from turkmopet_marketplace.performance_compare import (
    PerformanceSnapshot,
    compare_performance_periods,
    read_performance_csv,
    write_performance_changes,
)
from turkmopet_marketplace.pipeline import MarketplaceImportError


class MarketplacePerformanceComparisonTests(unittest.TestCase):
    def snapshot(self, marketplace: str, units: int, revenue: str, profit: str, margin: str) -> PerformanceSnapshot:
        return PerformanceSnapshot(
            marketplace=marketplace,
            units_sold=units,
            revenue=Decimal(revenue),
            contribution_profit=Decimal(profit),
            contribution_margin=Decimal(margin),
        )

    def test_prioritizes_declines_and_detects_new_missing_channels(self) -> None:
        previous = (
            self.snapshot("Trendyol", 100, "100000", "12000", "0.12"),
            self.snapshot("N11", 20, "10000", "1500", "0.15"),
            self.snapshot("Amazon", 5, "3000", "300", "0.10"),
        )
        current = (
            self.snapshot("Trendyol", 80, "85000", "8000", "0.0941"),
            self.snapshot("N11", 30, "18000", "2700", "0.15"),
            self.snapshot("Hepsiburada", 10, "7000", "700", "0.10"),
        )

        changes = compare_performance_periods(previous, current)

        self.assertEqual([item.marketplace for item in changes], ["Trendyol", "Amazon", "N11", "Hepsiburada"])
        self.assertEqual([item.movement for item in changes], ["declined", "missing", "improved", "new"])
        self.assertEqual(changes[0].profit_delta, Decimal("-4000.00"))
        self.assertEqual(changes[0].units_delta, -20)
        self.assertEqual(changes[0].margin_delta, Decimal("-0.0259"))

    def test_rejects_duplicate_marketplace_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "performance.csv"
            source.write_text(
                "marketplace,units_sold,revenue,contribution_profit,contribution_margin\n"
                "N11,1,100,20,0.2\n"
                "n11,2,200,30,0.15\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(MarketplaceImportError, "tekrarlı pazaryeri"):
                read_performance_csv(source)

    def test_writes_excel_compatible_comparison_csv(self) -> None:
        changes = compare_performance_periods(
            (self.snapshot("Trendyol", 10, "1000", "100", "0.10"),),
            (self.snapshot("Trendyol", 12, "1300", "150", "0.1154"),),
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "comparison.csv"
            write_performance_changes(changes, output)
            self.assertTrue(output.read_bytes().startswith(b"\xef\xbb\xbf"))
            with output.open("r", encoding="utf-8-sig", newline="") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["movement"], "improved")
            self.assertEqual(row["profit_delta"], "50.00")
            self.assertEqual(row["units_delta"], "2")


if __name__ == "__main__":
    unittest.main()
