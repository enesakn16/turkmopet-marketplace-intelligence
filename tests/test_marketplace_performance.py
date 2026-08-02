from __future__ import annotations

import csv
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from turkmopet_marketplace import performance_cli
from turkmopet_marketplace.performance import (
    SalesRecord,
    aggregate_marketplace_performance,
    read_sales_csv,
)
from turkmopet_marketplace.pipeline import MarketplaceImportError


class MarketplacePerformanceTests(unittest.TestCase):
    def test_ranks_channels_by_total_contribution_not_single_sale_margin(self) -> None:
        records = [
            SalesRecord("Trendyol", "SKU-1", 100, Decimal("100000"), Decimal("12000")),
            SalesRecord("N11", "SKU-2", 1, Decimal("2000"), Decimal("500")),
        ]

        performance = aggregate_marketplace_performance(records)

        self.assertEqual(performance[0].marketplace, "Trendyol")
        self.assertEqual(performance[0].units_sold, 100)
        self.assertEqual(performance[0].contribution_profit, Decimal("12000.00"))
        self.assertEqual(performance[0].profit_per_unit, Decimal("120.00"))
        self.assertEqual(performance[1].contribution_margin, Decimal("0.2500"))

    def test_aggregates_marketplace_case_insensitively_and_counts_distinct_skus(self) -> None:
        records = [
            SalesRecord("Hepsiburada", "SKU-1", 2, Decimal("2000"), Decimal("300")),
            SalesRecord("hepsiburada", "sku-1", 3, Decimal("3000"), Decimal("450")),
            SalesRecord("Hepsiburada", "SKU-2", 1, Decimal("1000"), Decimal("100")),
        ]

        item = aggregate_marketplace_performance(records)[0]

        self.assertEqual(item.units_sold, 6)
        self.assertEqual(item.revenue, Decimal("6000.00"))
        self.assertEqual(item.contribution_profit, Decimal("850.00"))
        self.assertEqual(item.sku_count, 2)

    def test_reads_turkish_formatted_money(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sales.csv"
            source.write_text(
                "marketplace,sku,units_sold,revenue,contribution_profit\n"
                'Trendyol,TVS-001,4,"4.000,50","600,25"\n',
                encoding="utf-8-sig",
            )

            record = read_sales_csv(source)[0]

            self.assertEqual(record.revenue, Decimal("4000.50"))
            self.assertEqual(record.contribution_profit, Decimal("600.25"))

    def test_rejects_missing_columns_and_negative_units(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            missing = root / "missing.csv"
            missing.write_text("marketplace,sku\nN11,SKU-1\n", encoding="utf-8")
            with self.assertRaisesRegex(MarketplaceImportError, "Eksik satış CSV kolonları"):
                read_sales_csv(missing)

            invalid = root / "invalid.csv"
            invalid.write_text(
                "marketplace,sku,units_sold,revenue,contribution_profit\n"
                "N11,SKU-1,-1,1000,100\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(MarketplaceImportError, "units_sold"):
                read_sales_csv(invalid)

    def test_cli_writes_ranked_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "sales.csv"
            output = root / "performance.csv"
            source.write_text(
                "marketplace,sku,units_sold,revenue,contribution_profit\n"
                "Trendyol,SKU-1,10,10000,1400\n"
                "N11,SKU-2,2,3000,700\n",
                encoding="utf-8-sig",
            )
            with patch(
                "sys.argv",
                ["marketplace-performance", "--input", str(source), "--output", str(output)],
            ):
                exit_code = performance_cli.main()

            self.assertEqual(exit_code, 0)
            with output.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["rank"], "1")
            self.assertEqual(rows[0]["marketplace"], "Trendyol")
            self.assertEqual(rows[0]["units_sold"], "10")


if __name__ == "__main__":
    unittest.main()
