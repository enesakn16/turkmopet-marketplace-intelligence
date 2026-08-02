from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path
from typing import Mapping

from .models import ListingSnapshot
from .pipeline import MarketplaceImportError, _decimal, _integer, _optional_decimal

_TRENDYOL_ALIASES = {
    "sku": ("stok kodu", "stok_kodu", "sku", "barkod", "barcode"),
    "sale_price": ("satis fiyati", "satış fiyatı", "satis_fiyati", "sale price", "sale_price"),
    "commission_rate": ("komisyon orani", "komisyon oranı", "komisyon_orani", "commission rate", "commission_rate"),
    "shipping_cost": ("kargo maliyeti", "kargo_maliyeti", "shipping cost", "shipping_cost"),
    "product_cost": ("urun maliyeti", "ürün maliyeti", "urun_maliyeti", "product cost", "product_cost"),
    "stock": ("stok", "stok adedi", "stok_adedi", "stock"),
    "service_fee": ("hizmet bedeli", "hizmet_bedeli", "service fee", "service_fee"),
    "seller_discount": ("satici indirimi", "satıcı indirimi", "satici_indirimi", "seller discount", "seller_discount"),
}

_HEPSIBURADA_ALIASES = {
    "sku": ("satici stok kodu", "satıcı stok kodu", "merchant sku", "merchant_sku", "stok kodu", "sku", "barkod", "barcode"),
    "sale_price": ("satis fiyati", "satış fiyatı", "fiyat", "listing price", "sale price", "sale_price"),
    "commission_rate": ("komisyon orani", "komisyon oranı", "commission rate", "commission_rate"),
    "shipping_cost": ("kargo bedeli", "kargo maliyeti", "shipping cost", "shipping_cost"),
    "product_cost": ("urun maliyeti", "ürün maliyeti", "maliyet", "product cost", "product_cost"),
    "stock": ("satilabilir stok", "satılabilir stok", "stok adedi", "stok", "available stock", "stock"),
    "service_fee": ("hizmet bedeli", "islem bedeli", "işlem bedeli", "service fee", "service_fee"),
    "seller_discount": ("satici indirimi", "satıcı indirimi", "kampanya indirimi", "seller discount", "seller_discount"),
}

_N11_ALIASES = {
    "sku": (
        "magaza urun kodu",
        "mağaza ürün kodu",
        "seller product code",
        "seller sku",
        "stok kodu",
        "sku",
        "barkod",
        "barcode",
    ),
    "sale_price": (
        "satis fiyati",
        "satış fiyatı",
        "magaza satis fiyati",
        "mağaza satış fiyatı",
        "fiyat",
        "price",
        "sale price",
    ),
    "commission_rate": (
        "komisyon orani",
        "komisyon oranı",
        "komisyon",
        "commission rate",
        "commission",
    ),
    "shipping_cost": (
        "kargo bedeli",
        "kargo maliyeti",
        "shipping cost",
        "cargo cost",
    ),
    "product_cost": (
        "urun maliyeti",
        "ürün maliyeti",
        "maliyet",
        "product cost",
        "cost",
    ),
    "stock": (
        "stok miktari",
        "stok miktarı",
        "stok adedi",
        "stok",
        "quantity",
        "stock",
    ),
    "service_fee": (
        "hizmet bedeli",
        "islem bedeli",
        "işlem bedeli",
        "service fee",
        "transaction fee",
    ),
    "seller_discount": (
        "magaza indirimi",
        "mağaza indirimi",
        "satici indirimi",
        "satıcı indirimi",
        "kampanya indirimi",
        "seller discount",
    ),
}

_REQUIRED = {"sku", "sale_price", "commission_rate", "shipping_cost", "product_cost", "stock"}


def _normalize_header(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.strip().casefold())
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", ascii_text).strip()


def _resolve_columns(
    fieldnames: list[str] | None,
    *,
    aliases: Mapping[str, tuple[str, ...]],
    marketplace: str,
) -> dict[str, str]:
    normalized = {_normalize_header(name): name for name in fieldnames or []}
    resolved: dict[str, str] = {}
    for target, candidates in aliases.items():
        for alias in candidates:
            source = normalized.get(_normalize_header(alias))
            if source is not None:
                resolved[target] = source
                break
    missing = sorted(_REQUIRED - resolved.keys())
    if missing:
        raise MarketplaceImportError(
            f"{marketplace} CSV kolonları eşleştirilemedi: " + ", ".join(missing)
        )
    return resolved


def _read_marketplace_csv(
    path: str | Path,
    *,
    marketplace: str,
    aliases: Mapping[str, tuple[str, ...]],
) -> tuple[ListingSnapshot, ...]:
    source = Path(path)
    try:
        handle = source.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise MarketplaceImportError(f"{marketplace} CSV dosyası açılamadı: {source}") from exc

    listings: list[ListingSnapshot] = []
    seen: set[str] = set()
    with handle:
        reader = csv.DictReader(handle)
        columns = _resolve_columns(reader.fieldnames, aliases=aliases, marketplace=marketplace)
        for row_number, row in enumerate(reader, start=2):
            sku = (row.get(columns["sku"]) or "").strip()
            key = sku.casefold()
            if key in seen:
                raise MarketplaceImportError(
                    f"Satır {row_number}: aynı {marketplace} SKU birden fazla kez tanımlanmış"
                )
            try:
                listing = ListingSnapshot(
                    sku=sku,
                    marketplace=marketplace,
                    sale_price=_decimal(row.get(columns["sale_price"]) or "", field="sale_price", row_number=row_number),
                    commission_rate=_decimal(row.get(columns["commission_rate"]) or "", field="commission_rate", row_number=row_number),
                    shipping_cost=_decimal(row.get(columns["shipping_cost"]) or "", field="shipping_cost", row_number=row_number),
                    product_cost=_decimal(row.get(columns["product_cost"]) or "", field="product_cost", row_number=row_number),
                    stock=_integer(row.get(columns["stock"]) or "", field="stock", row_number=row_number),
                    service_fee=_optional_decimal(row.get(columns["service_fee"]) if "service_fee" in columns else None, field="service_fee", row_number=row_number),
                    seller_discount=_optional_decimal(row.get(columns["seller_discount"]) if "seller_discount" in columns else None, field="seller_discount", row_number=row_number),
                )
            except ValueError as exc:
                raise MarketplaceImportError(f"Satır {row_number}: {exc}") from exc
            seen.add(key)
            listings.append(listing)
    return tuple(listings)


def read_trendyol_csv(path: str | Path) -> tuple[ListingSnapshot, ...]:
    return _read_marketplace_csv(path, marketplace="Trendyol", aliases=_TRENDYOL_ALIASES)


def read_hepsiburada_csv(path: str | Path) -> tuple[ListingSnapshot, ...]:
    return _read_marketplace_csv(path, marketplace="Hepsiburada", aliases=_HEPSIBURADA_ALIASES)


def read_n11_csv(path: str | Path) -> tuple[ListingSnapshot, ...]:
    return _read_marketplace_csv(path, marketplace="N11", aliases=_N11_ALIASES)
