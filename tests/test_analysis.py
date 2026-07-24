from decimal import Decimal
import unittest

from turkmopet_marketplace import (
    ListingSnapshot,
    analyze_marketplaces,
    calculate_channel_economics,
    recommend_sale_price,
)


class MarketplaceAnalysisTests(unittest.TestCase):
    def test_calculates_explainable_channel_profitability(self) -> None:
        listing = ListingSnapshot(
            sku="TVS-JUPITER-CAM",
            marketplace="Trendyol",
            sale_price=Decimal("1000"),
            commission_rate=Decimal("0.20"),
            shipping_cost=Decimal("60"),
            product_cost=Decimal("500"),
            stock=4,
        )

        economics = calculate_channel_economics(listing)

        self.assertEqual(economics.net_revenue, Decimal("740.00"))
        self.assertEqual(economics.contribution_profit, Decimal("240.00"))
        self.assertEqual(economics.contribution_margin, Decimal("0.2400"))

    def test_recommends_break_even_and_target_price(self) -> None:
        listing = ListingSnapshot(
            sku="MOTUL-5100-10W40",
            marketplace="Trendyol",
            sale_price=Decimal("800"),
            commission_rate=Decimal("0.20"),
            shipping_cost=Decimal("60"),
            product_cost=Decimal("500"),
            stock=8,
        )

        recommendation = recommend_sale_price(
            listing,
            target_margin=Decimal("0.10"),
        )

        self.assertEqual(recommendation.break_even_price, Decimal("700.00"))
        self.assertEqual(recommendation.target_price, Decimal("800.00"))
        self.assertEqual(recommendation.required_increase, Decimal("0.00"))

    def test_recommends_required_price_increase(self) -> None:
        listing = ListingSnapshot(
            sku="CFMOTO-450SR-DEBRIYAJ",
            marketplace="N11",
            sale_price=Decimal("900"),
            commission_rate=Decimal("0.18"),
            shipping_cost=Decimal("90"),
            product_cost=Decimal("700"),
            stock=2,
        )

        recommendation = recommend_sale_price(
            listing,
            target_margin=Decimal("0.10"),
        )

        self.assertEqual(recommendation.break_even_price, Decimal("963.41"))
        self.assertEqual(recommendation.target_price, Decimal("1097.22"))
        self.assertEqual(recommendation.required_increase, Decimal("197.22"))

    def test_rejects_unachievable_target_margin(self) -> None:
        listing = ListingSnapshot(
            sku="SKU-1",
            marketplace="Trendyol",
            sale_price=Decimal("100"),
            commission_rate=Decimal("0.90"),
            shipping_cost=Decimal("0"),
            product_cost=Decimal("20"),
            stock=1,
        )

        with self.assertRaisesRegex(ValueError, "not achievable"):
            recommend_sale_price(listing, target_margin=Decimal("0.10"))

    def test_flags_negative_contribution_and_zero_stock(self) -> None:
        listing = ListingSnapshot(
            sku="CFMOTO-450SR-DEBRIYAJ",
            marketplace="N11",
            sale_price=Decimal("900"),
            commission_rate=Decimal("0.18"),
            shipping_cost=Decimal("90"),
            product_cost=Decimal("700"),
            stock=0,
        )

        result = analyze_marketplaces([listing])
        codes = {issue.code for issue in result.issues}

        self.assertEqual(
            codes,
            {"negative_contribution", "out_of_stock"},
        )

    def test_flags_cross_channel_price_gap_for_same_sku(self) -> None:
        listings = [
            ListingSnapshot(
                sku="MOTUL-5100-10W40",
                marketplace="Trendyol",
                sale_price=Decimal("1000"),
                commission_rate=Decimal("0.15"),
                shipping_cost=Decimal("50"),
                product_cost=Decimal("650"),
                stock=10,
            ),
            ListingSnapshot(
                sku="MOTUL-5100-10W40",
                marketplace="Hepsiburada",
                sale_price=Decimal("800"),
                commission_rate=Decimal("0.15"),
                shipping_cost=Decimal("50"),
                product_cost=Decimal("650"),
                stock=8,
            ),
        ]

        result = analyze_marketplaces(
            listings,
            price_gap_threshold=Decimal("0.12"),
        )

        gap_issues = [
            issue for issue in result.issues
            if issue.code == "cross_channel_price_gap"
        ]
        self.assertEqual(len(gap_issues), 2)

    def test_rejects_invalid_listing_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "commission_rate"):
            ListingSnapshot(
                sku="SKU-1",
                marketplace="Trendyol",
                sale_price=Decimal("100"),
                commission_rate=Decimal("1.20"),
                shipping_cost=Decimal("0"),
                product_cost=Decimal("20"),
                stock=1,
            )

    def test_rejects_invalid_analysis_threshold(self) -> None:
        with self.assertRaisesRegex(ValueError, "price_gap_threshold"):
            analyze_marketplaces([], price_gap_threshold=Decimal("1.01"))


if __name__ == "__main__":
    unittest.main()
