from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

from .analysis import analyze_marketplaces, recommend_best_channels, recommend_sale_price
from .models import (
    ChannelRecommendation,
    ListingSnapshot,
    MarketplaceAnalysis,
    PricingRecommendation,
)

REQUIRED_COLUMNS = {
    "sku",
    "marketplace",
    "sale_price",
    "commission_rate",
    "shipping_cost",
    "product_cost",
    "stock",
}
OPTIONAL_COST_COLUMNS = {"service_fee", "seller_discount"}


class MarketplaceImportError(ValueError):
    """Raised when a marketplace export cannot be parsed safely."""


@dataclass(frozen=True, slots=True)
class MarketplacePipelineResult:
    listings: tuple[ListingSnapshot, ...]
    analysis: MarketplaceAnalysis
    recommendations: tuple[PricingRecommendation, ...]
    channel_recommendations: tuple[ChannelRecommendation, ...]


def _normalize_decimal(value: str) -> str:
    normalized = value.strip().replace(" ", "")
    if "," in normalized and "." in normalized:
        if normalized.rfind(",") > normalized.rfind("."):
            return normalized.replace(".", "").replace(",", ".")
        return normalized.replace(",", "")
    if "," in normalized:
        return normalized.replace(",", ".")
    return normalized


def _decimal(value: str, *, field: str, row_number: int) -> Decimal:
    normalized = _normalize_decimal(value)
    try:
        return Decimal(normalized)
    except (InvalidOperation, ValueError) as exc:
        raise MarketplaceImportError(
            f"Satır {row_number}: {field} geçerli bir sayı değil: {value!r}"
        ) from exc


def _optional_decimal(value: str | None, *, field: str, row_number: int) -> Decimal:
    if value is None or not value.strip():
        return Decimal("0")
    return _decimal(value, field=field, row_number=row_number)


def _integer(value: str, *, field: str, row_number: int) -> int:
    try:
        return int(value.strip())
    except ValueError as exc:
        raise MarketplaceImportError(
            f"Satır {row_number}: {field} geçerli bir tam sayı değil: {value!r}"
        ) from exc


def read_listings_csv(path: str | Path) -> tuple[ListingSnapshot, ...]:
    source = Path(path)
    try:
        handle = source.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise MarketplaceImportError(f"CSV dosyası açılamadı: {source}") from exc
    listings: list[ListingSnapshot] = []
    seen: set[tuple[str, str]] = set()
    with handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or ())
        missing = sorted(REQUIRED_COLUMNS - columns)
        if missing:
            raise MarketplaceImportError("Eksik CSV kolonları: " + ", ".join(missing))
        for row_number, row in enumerate(reader, start=2):
            sku = (row.get("sku") or "").strip()
            marketplace = (row.get("marketplace") or "").strip()
            key = (sku.casefold(), marketplace.casefold())
            if key in seen:
                raise MarketplaceImportError(
                    f"Satır {row_number}: aynı SKU ve pazaryeri birden fazla kez tanımlanmış"
                )
            try:
                listing = ListingSnapshot(
                    sku=sku,
                    marketplace=marketplace,
                    sale_price=_decimal(row.get("sale_price") or "", field="sale_price", row_number=row_number),
                    commission_rate=_decimal(row.get("commission_rate") or "", field="commission_rate", row_number=row_number),
                    shipping_cost=_decimal(row.get("shipping_cost") or "", field="shipping_cost", row_number=row_number),
                    product_cost=_decimal(row.get("product_cost") or "", field="product_cost", row_number=row_number),
                    stock=_integer(row.get("stock") or "", field="stock", row_number=row_number),
                    service_fee=_optional_decimal(row.get("service_fee"), field="service_fee", row_number=row_number),
                    seller_discount=_optional_decimal(row.get("seller_discount"), field="seller_discount", row_number=row_number),
                )
            except ValueError as exc:
                raise MarketplaceImportError(f"Satır {row_number}: {exc}") from exc
            seen.add(key)
            listings.append(listing)
    return tuple(listings)


def run_marketplace_pipeline(
    listings: Iterable[ListingSnapshot],
    *,
    minimum_margin: Decimal = Decimal("0.10"),
    price_gap_threshold: Decimal = Decimal("0.12"),
    target_margin: Decimal = Decimal("0.10"),
) -> MarketplacePipelineResult:
    normalized = tuple(listings)
    analysis = analyze_marketplaces(normalized, minimum_margin=minimum_margin, price_gap_threshold=price_gap_threshold)
    recommendations = tuple(recommend_sale_price(item, target_margin=target_margin) for item in normalized)
    return MarketplacePipelineResult(
        listings=normalized,
        analysis=analysis,
        recommendations=recommendations,
        channel_recommendations=recommend_best_channels(normalized),
    )


def write_report_csv(result: MarketplacePipelineResult, path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    issues_by_key: dict[tuple[str, str], list[str]] = {}
    for issue in result.analysis.issues:
        key = (issue.sku, issue.marketplace)
        issues_by_key.setdefault(key, []).append(f"{issue.severity}:{issue.code}")
    recommendation_by_key = {(item.sku, item.marketplace): item for item in result.recommendations}
    economics_by_key = {(item.sku, item.marketplace): item for item in result.analysis.economics}
    best_channel_by_sku = {item.sku: item.marketplace for item in result.channel_recommendations}
    with destination.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "sku", "marketplace", "sale_price", "commission_rate", "shipping_cost",
                "product_cost", "service_fee", "seller_discount", "net_revenue",
                "contribution_profit", "contribution_margin", "break_even_price",
                "target_price", "required_increase", "is_recommended_channel", "issues",
            ],
        )
        writer.writeheader()
        for listing in result.listings:
            key = (listing.sku, listing.marketplace)
            economics = economics_by_key[key]
            recommendation = recommendation_by_key[key]
            writer.writerow(
                {
                    "sku": listing.sku,
                    "marketplace": listing.marketplace,
                    "sale_price": listing.sale_price,
                    "commission_rate": listing.commission_rate,
                    "shipping_cost": listing.shipping_cost,
                    "product_cost": listing.product_cost,
                    "service_fee": listing.service_fee,
                    "seller_discount": listing.seller_discount,
                    "net_revenue": economics.net_revenue,
                    "contribution_profit": economics.contribution_profit,
                    "contribution_margin": economics.contribution_margin,
                    "break_even_price": recommendation.break_even_price,
                    "target_price": recommendation.target_price,
                    "required_increase": recommendation.required_increase,
                    "is_recommended_channel": "yes" if best_channel_by_sku.get(listing.sku) == listing.marketplace else "no",
                    "issues": "|".join(issues_by_key.get(key, ())),
                }
            )


def write_channel_recommendations_csv(result: MarketplacePipelineResult, path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["sku", "recommended_marketplace", "contribution_profit", "contribution_margin", "stock", "evaluated_channels"],
        )
        writer.writeheader()
        for recommendation in result.channel_recommendations:
            writer.writerow(
                {
                    "sku": recommendation.sku,
                    "recommended_marketplace": recommendation.marketplace,
                    "contribution_profit": recommendation.contribution_profit,
                    "contribution_margin": recommendation.contribution_margin,
                    "stock": recommendation.stock,
                    "evaluated_channels": recommendation.evaluated_channels,
                }
            )
