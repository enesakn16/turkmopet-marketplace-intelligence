from decimal import Decimal
import unittest

from turkmopet_marketplace import ListingSnapshot, recommend_best_channels


class ChannelRecommendationTests(unittest.TestCase):
    def test_selects_highest_contribution_profit_for_each_sku(self) -> None:
        listings = [
            ListingSnapshot(
                sku="SKU-1",
                marketplace="Trendyol",
                sale_price=Decimal("1200"),
                commission_rate=Decimal("0.20"),
                shipping_cost=Decimal("80"),
                product_cost=Decimal("700"),
                stock=8,
            ),
            ListingSnapshot(
                sku="SKU-1",
                marketplace="Hepsiburada",
                sale_price=Decimal("1180"),
                commission_rate=Decimal("0.15"),
                shipping_cost=Decimal("75"),
                product_cost=Decimal("700"),
                stock=5,
            ),
        ]

        recommendations = recommend_best_channels(listings)

        self.assertEqual(len(recommendations), 1)
        recommendation = recommendations[0]
        self.assertEqual(recommendation.marketplace, "Hepsiburada")
        self.assertEqual(recommendation.contribution_profit, Decimal("228.00"))
        self.assertEqual(recommendation.evaluated_channels, 2)

    def test_ignores_out_of_stock_channel_even_when_more_profitable(self) -> None:
        listings = [
            ListingSnapshot(
                sku="SKU-2",
                marketplace="N11",
                sale_price=Decimal("1400"),
                commission_rate=Decimal("0.10"),
                shipping_cost=Decimal("60"),
                product_cost=Decimal("700"),
                stock=0,
            ),
            ListingSnapshot(
                sku="SKU-2",
                marketplace="Trendyol",
                sale_price=Decimal("1100"),
                commission_rate=Decimal("0.18"),
                shipping_cost=Decimal("70"),
                product_cost=Decimal("700"),
                stock=3,
            ),
        ]

        recommendation = recommend_best_channels(listings)[0]

        self.assertEqual(recommendation.marketplace, "Trendyol")
        self.assertEqual(recommendation.evaluated_channels, 1)

    def test_omits_sku_when_all_channels_are_out_of_stock(self) -> None:
        listings = [
            ListingSnapshot(
                sku="SKU-3",
                marketplace="Trendyol",
                sale_price=Decimal("1000"),
                commission_rate=Decimal("0.18"),
                shipping_cost=Decimal("70"),
                product_cost=Decimal("650"),
                stock=0,
            )
        ]

        self.assertEqual(recommend_best_channels(listings), ())

    def test_returns_recommendations_in_sku_order(self) -> None:
        listings = [
            ListingSnapshot(
                sku="SKU-Z",
                marketplace="N11",
                sale_price=Decimal("1000"),
                commission_rate=Decimal("0.10"),
                shipping_cost=Decimal("50"),
                product_cost=Decimal("600"),
                stock=1,
            ),
            ListingSnapshot(
                sku="SKU-A",
                marketplace="Trendyol",
                sale_price=Decimal("1000"),
                commission_rate=Decimal("0.15"),
                shipping_cost=Decimal("50"),
                product_cost=Decimal("600"),
                stock=1,
            ),
        ]

        recommendations = recommend_best_channels(listings)

        self.assertEqual([item.sku for item in recommendations], ["SKU-A", "SKU-Z"])


if __name__ == "__main__":
    unittest.main()
