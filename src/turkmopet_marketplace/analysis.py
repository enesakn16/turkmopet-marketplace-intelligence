from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from .models import (
    ChannelEconomics,
    ListingSnapshot,
    MarketplaceAnalysis,
    MarketplaceIssue,
    PricingRecommendation,
)


MONEY = Decimal("0.01")
RATE = Decimal("0.0001")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def _rate(value: Decimal) -> Decimal:
    return value.quantize(RATE, rounding=ROUND_HALF_UP)


def calculate_channel_economics(listing: ListingSnapshot) -> ChannelEconomics:
    commission = listing.sale_price * listing.commission_rate
    net_revenue = listing.sale_price - commission - listing.shipping_cost
    contribution_profit = net_revenue - listing.product_cost
    contribution_margin = contribution_profit / listing.sale_price

    return ChannelEconomics(
        sku=listing.sku,
        marketplace=listing.marketplace,
        net_revenue=_money(net_revenue),
        contribution_profit=_money(contribution_profit),
        contribution_margin=_rate(contribution_margin),
    )


def recommend_sale_price(
    listing: ListingSnapshot,
    *,
    target_margin: Decimal = Decimal("0.10"),
) -> PricingRecommendation:
    if not Decimal("0") <= target_margin < Decimal("1"):
        raise ValueError("target_margin must be between 0 and 1")

    break_even_denominator = Decimal("1") - listing.commission_rate
    target_denominator = break_even_denominator - target_margin

    if break_even_denominator <= 0:
        raise ValueError("commission_rate leaves no revenue for costs")
    if target_denominator <= 0:
        raise ValueError("target_margin is not achievable with this commission_rate")

    fixed_costs = listing.product_cost + listing.shipping_cost
    break_even_price = _money(fixed_costs / break_even_denominator)
    target_price = _money(fixed_costs / target_denominator)
    required_increase = _money(max(Decimal("0"), target_price - listing.sale_price))

    return PricingRecommendation(
        sku=listing.sku,
        marketplace=listing.marketplace,
        break_even_price=break_even_price,
        target_price=target_price,
        target_margin=_rate(target_margin),
        current_price=_money(listing.sale_price),
        required_increase=required_increase,
    )


def analyze_marketplaces(
    listings: Iterable[ListingSnapshot],
    *,
    minimum_margin: Decimal = Decimal("0.10"),
    price_gap_threshold: Decimal = Decimal("0.12"),
) -> MarketplaceAnalysis:
    if not Decimal("-1") < minimum_margin < Decimal("1"):
        raise ValueError("minimum_margin must be between -1 and 1")
    if not Decimal("0") <= price_gap_threshold <= Decimal("1"):
        raise ValueError("price_gap_threshold must be between 0 and 1")

    normalized = tuple(listings)
    economics = tuple(calculate_channel_economics(item) for item in normalized)
    issues: list[MarketplaceIssue] = []

    for item, result in zip(normalized, economics, strict=True):
        if result.contribution_profit < 0:
            issues.append(
                MarketplaceIssue(
                    sku=item.sku,
                    marketplace=item.marketplace,
                    code="negative_contribution",
                    severity="error",
                    message=(
                        f"Satış, ürün maliyeti + komisyon + kargoyu karşılamıyor; "
                        f"katkı kârı {result.contribution_profit} TL."
                    ),
                )
            )
        elif result.contribution_margin < minimum_margin:
            issues.append(
                MarketplaceIssue(
                    sku=item.sku,
                    marketplace=item.marketplace,
                    code="low_margin",
                    severity="warning",
                    message=(
                        f"Katkı marjı %{result.contribution_margin * 100:.2f}; "
                        f"hedef %{minimum_margin * 100:.2f}."
                    ),
                )
            )

        if item.stock == 0:
            issues.append(
                MarketplaceIssue(
                    sku=item.sku,
                    marketplace=item.marketplace,
                    code="out_of_stock",
                    severity="warning",
                    message="Listeleme satışa açık olabilir ancak kanal stoğu sıfır.",
                )
            )

    by_sku: dict[str, list[ListingSnapshot]] = defaultdict(list)
    for item in normalized:
        by_sku[item.sku].append(item)

    for sku, sku_listings in by_sku.items():
        if len(sku_listings) < 2:
            continue
        highest = max(item.sale_price for item in sku_listings)
        lowest = min(item.sale_price for item in sku_listings)
        gap = (highest - lowest) / highest
        if gap > price_gap_threshold:
            for item in sku_listings:
                issues.append(
                    MarketplaceIssue(
                        sku=sku,
                        marketplace=item.marketplace,
                        code="cross_channel_price_gap",
                        severity="warning",
                        message=(
                            f"Kanallar arası fiyat farkı %{gap * 100:.2f}; "
                            f"eşik %{price_gap_threshold * 100:.2f}."
                        ),
                    )
                )

    ordered_issues = tuple(
        sorted(issues, key=lambda issue: (issue.sku, issue.marketplace, issue.code))
    )
    return MarketplaceAnalysis(economics=economics, issues=ordered_issues)
