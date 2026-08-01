from __future__ import annotations

import csv
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from turkmopet_marketplace import (
    ListingSnapshot,
    calculate_channel_economics,
    recommend_sale_price,
)
from turkmopet_marketplace.pipeline import read_listings_csv, run_marketplace_pipeline, write_report_csv


class MarketplaceCostTests(unittest.TestCase):
    def test_subtracts_service_fee_and_seller_discount_from_profit(self) -> None:
        listing = ListingSnapshot(
            sku="TVS-001",
            marketplace="Trendyol",
            sale_price=Decimal("1000"),
            commission_rate=Decimal("0.20"),
            shipping_cost=Decimal("60"),
            product_cost=Decimal("500"),
            stock=3,
            service_fee=Decimal("25"),
            seller_discount=Decimal("40"),
        )

        economics = calculate_channel_economics(listing)

        self.assertEqual(economics.net_revenue, Decimal("675.00"))
        self.assertEqual(economics.contribution_profit, Decimal("175.00"))
        self.assertEqual(economics.contribution_margin, Decimal("0.1750"))

    def test_includes_new_costs_in_target_price(self) -> None:
        listing = ListingSnapshot(
            sku="TVS-001",
            marketplace="Trendyol",
            sale_price=Decimal("800"),
            commission_rate=Decimal("0.20"),
            shipping_cost=Decimal("60"),
            product_cost=Decimal("500"),
            stock=3,
            service_fee=Decimal("25"),
            seller_discount=Decimal("45"),
        )

        recommendation = recommend_sale_price(listing, target_margin=Decimal("0.10"))

        self.assertEqual(recommendation.break_even_price, Decimal("787.50"))
        self.assertEqual(recommendation.target_price, Decimal("900.00"))
        self.assertEqual(recommendation.required_increase, Decimal("100.00"))

    def test_optional_csv_columns_default_to_zero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "legacy.csv"
            source.write_text(
                "sku,marketplace,sale_price,commission_rate,shipping_cost,product_cost,stock\n"
                "TVS-001,Trendyol,1000,0.20,60,500,3\n",
                encoding="utf-8",
            )

            listing = read_listings_csv(source)[0]

            self.assertEqual(listing.service_fee, Decimal("0"))
            self.assertEqual(listing.seller_discount, Decimal("0"))

    def test_reads_and_exports_marketplace_cost_columns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "costs.csv"
            report = root / "report.csv"
            source.write_text(
                "sku,marketplace,sale_price,commission_rate,shipping_cost,product_cost,stock,service_fee,seller_discount\n"
                "TVS-001,Trendyol,1000,0.20,60,500,3,25,40\n",
                encoding="utf-8-sig",
            )

            result = run_marketplace_pipeline(read_listings_csv(source))
            write_report_csv(result, report)

            with report.open(encoding="utf-8-sig", newline="") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["service_fee"], "25")
            self.assertEqual(row["seller_discount"], "40")
            self.assertEqual(row["contribution_profit"], "175.00")

    def test_rejects_negative_marketplace_costs(self) -> None:
        with self.assertRaisesRegex(ValueError, "service_fee"):
            ListingSnapshot(
                sku="TVS-001",
                marketplace="Trendyol",
                sale_price=Decimal("1000"),
                commission_rate=Decimal("0.20"),
                shipping_cost=Decimal("60"),
                product_cost=Decimal("500"),
                stock=3,
                service_fee=Decimal("-1"),
            )


if __name__ == "__main__":
    unittest.main()
