from __future__ import annotations

import csv
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from turkmopet_marketplace.pipeline import (
    MarketplaceImportError,
    read_listings_csv,
    run_marketplace_pipeline,
    write_report_csv,
)


class MarketplacePipelineTests(unittest.TestCase):
    def test_reads_excel_compatible_csv_and_builds_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "listings.csv"
            report = root / "report.csv"
            source.write_text(
                "sku,marketplace,sale_price,commission_rate,shipping_cost,product_cost,stock\n"
                "TVS-001,Trendyol,900,0.18,90,700,3\n",
                encoding="utf-8-sig",
            )

            listings = read_listings_csv(source)
            result = run_marketplace_pipeline(listings, target_margin=Decimal("0.10"))
            write_report_csv(result, report)

            self.assertEqual(len(listings), 1)
            self.assertEqual(result.recommendations[0].target_price, Decimal("1097.22"))
            with report.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["required_increase"], "197.22")
            self.assertIn("error:negative_contribution", rows[0]["issues"])

    def test_rejects_missing_columns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "listings.csv"
            source.write_text("sku,marketplace\nTVS-001,Trendyol\n", encoding="utf-8")

            with self.assertRaisesRegex(MarketplaceImportError, "Eksik CSV kolonları"):
                read_listings_csv(source)

    def test_rejects_duplicate_sku_marketplace_pair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "listings.csv"
            source.write_text(
                "sku,marketplace,sale_price,commission_rate,shipping_cost,product_cost,stock\n"
                "TVS-001,Trendyol,900,0.18,90,700,3\n"
                "TVS-001,Trendyol,950,0.18,90,700,4\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(MarketplaceImportError, "birden fazla"):
                read_listings_csv(source)

    def test_accepts_decimal_comma(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "listings.csv"
            source.write_text(
                "sku,marketplace,sale_price,commission_rate,shipping_cost,product_cost,stock\n"
                'TVS-001,Trendyol,"900,50","0,18",90,700,3\n',
                encoding="utf-8",
            )

            listings = read_listings_csv(source)
            self.assertEqual(listings[0].sale_price, Decimal("900.50"))
            self.assertEqual(listings[0].commission_rate, Decimal("0.18"))


if __name__ == "__main__":
    unittest.main()
