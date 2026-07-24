from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ListingSnapshot:
    """A normalized marketplace listing at a point in time."""

    sku: str
    marketplace: str
    sale_price: Decimal
    commission_rate: Decimal
    shipping_cost: Decimal
    product_cost: Decimal
    stock: int

    def __post_init__(self) -> None:
        if not self.sku.strip():
            raise ValueError("sku must not be empty")
        if not self.marketplace.strip():
            raise ValueError("marketplace must not be empty")
        if self.sale_price <= 0:
            raise ValueError("sale_price must be positive")
        if not Decimal("0") <= self.commission_rate <= Decimal("1"):
            raise ValueError("commission_rate must be between 0 and 1")
        if self.shipping_cost < 0:
            raise ValueError("shipping_cost must not be negative")
        if self.product_cost < 0:
            raise ValueError("product_cost must not be negative")
        if self.stock < 0:
            raise ValueError("stock must not be negative")


@dataclass(frozen=True, slots=True)
class ChannelEconomics:
    sku: str
    marketplace: str
    net_revenue: Decimal
    contribution_profit: Decimal
    contribution_margin: Decimal


@dataclass(frozen=True, slots=True)
class PricingRecommendation:
    sku: str
    marketplace: str
    break_even_price: Decimal
    target_price: Decimal
    target_margin: Decimal
    current_price: Decimal
    required_increase: Decimal


@dataclass(frozen=True, slots=True)
class ChannelRecommendation:
    """The strongest in-stock marketplace option for one SKU."""

    sku: str
    marketplace: str
    contribution_profit: Decimal
    contribution_margin: Decimal
    stock: int
    evaluated_channels: int


@dataclass(frozen=True, slots=True)
class MarketplaceIssue:
    sku: str
    marketplace: str
    code: str
    severity: str
    message: str


@dataclass(frozen=True, slots=True)
class MarketplaceAnalysis:
    economics: tuple[ChannelEconomics, ...]
    issues: tuple[MarketplaceIssue, ...]
