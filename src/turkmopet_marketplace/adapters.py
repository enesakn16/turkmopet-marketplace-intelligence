from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

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
_REQUIRED = {"sku", "sale_price", "commission_rate", "shipping_cost", "product_cost", "stock"}


def _normalize_header(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.strip().casefold())
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", ascii_text).strip()


def _resolve_columns(fieldnames: list[str] | None) -> dict[str, str]:
    normalized = {_normalize_header(name): name for name in fieldnames or []}
    resolved: dict[str, str] = {}
    for target, aliases in _TRENDYOL_ALIASES.items():
        for alias in aliases:
            source = normalized.get(_normalize_header(alias))
            if source is not None:
                resolved[target] = source
                break
    missing = sorted(_REQUIRED - resolved.keys())
    if missing:
        raise MarketplaceImportError(
            "Trendyol CSV kolonları eşleştirilemedi: " + ", ".join(missing)
        )
    return resolved


def read_trendyol_csv(path: str | Path) -> tuple[ListingSnapshot, ...]:
    source = Path(path)
    try:
        handle = source.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise MarketplaceImportError(f"Trendyol CSV dosyası açılamadı: {source}") from exc

    listings: list[ListingSnapshot] = []
    seen: set[str] = set()
    with handle:
        reader = csv.DictReader(handle)
        columns = _resolve_columns(reader.fieldnames)
        for row_number, row in enumerate(reader, start=2):
            sku = (row.get(columns["sku"]) or "").strip()
            key = sku.casefold()
            if key in seen:
                raise MarketplaceImportError(
                    f"Satır {row_number}: aynı Trendyol SKU birden fazla kez tanımlanmış"
                )
            try:
                listing = ListingSnapshot(
                    sku=sku,
                    marketplace="Trendyol",
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
