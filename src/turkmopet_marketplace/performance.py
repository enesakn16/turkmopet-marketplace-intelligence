from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable

from .pipeline import MarketplaceImportError

MONEY = Decimal("0.01")
RATE = Decimal("0.0001")


@dataclass(frozen=True, slots=True)
class SalesRecord:
    marketplace: str
    sku: str
    units_sold: int
    revenue: Decimal
    contribution_profit: Decimal

    def __post_init__(self) -> None:
        if not self.marketplace.strip():
            raise ValueError("marketplace must not be empty")
        if not self.sku.strip():
            raise ValueError("sku must not be empty")
        if self.units_sold < 0:
            raise ValueError("units_sold must not be negative")
        if self.revenue < 0:
            raise ValueError("revenue must not be negative")


@dataclass(frozen=True, slots=True)
class MarketplacePerformance:
    marketplace: str
    units_sold: int
    revenue: Decimal
    contribution_profit: Decimal
    contribution_margin: Decimal
    profit_per_unit: Decimal
    sku_count: int


def _decimal(value: str, *, field: str, row_number: int) -> Decimal:
    normalized = value.strip().replace(" ", "")
    if "," in normalized and "." in normalized:
        normalized = (
            normalized.replace(".", "").replace(",", ".")
            if normalized.rfind(",") > normalized.rfind(".")
            else normalized.replace(",", "")
        )
    elif "," in normalized:
        normalized = normalized.replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise MarketplaceImportError(
            f"Satır {row_number}: {field} geçerli bir sayı değil: {value!r}"
        ) from exc


def read_sales_csv(path: str | Path) -> tuple[SalesRecord, ...]:
    source = Path(path)
    try:
        handle = source.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise MarketplaceImportError(f"Satış CSV dosyası açılamadı: {source}") from exc

    required = {"marketplace", "sku", "units_sold", "revenue", "contribution_profit"}
    records: list[SalesRecord] = []
    with handle:
        reader = csv.DictReader(handle)
        missing = sorted(required - set(reader.fieldnames or ()))
        if missing:
            raise MarketplaceImportError("Eksik satış CSV kolonları: " + ", ".join(missing))
        for row_number, row in enumerate(reader, start=2):
            try:
                units_sold = int((row.get("units_sold") or "").strip())
                record = SalesRecord(
                    marketplace=(row.get("marketplace") or "").strip(),
                    sku=(row.get("sku") or "").strip(),
                    units_sold=units_sold,
                    revenue=_decimal(row.get("revenue") or "", field="revenue", row_number=row_number),
                    contribution_profit=_decimal(
                        row.get("contribution_profit") or "",
                        field="contribution_profit",
                        row_number=row_number,
                    ),
                )
            except ValueError as exc:
                raise MarketplaceImportError(f"Satır {row_number}: {exc}") from exc
            records.append(record)
    return tuple(records)


def aggregate_marketplace_performance(
    records: Iterable[SalesRecord],
) -> tuple[MarketplacePerformance, ...]:
    grouped: dict[str, list[SalesRecord]] = defaultdict(list)
    names: dict[str, str] = {}
    for record in records:
        key = record.marketplace.casefold()
        grouped[key].append(record)
        names.setdefault(key, record.marketplace)

    results: list[MarketplacePerformance] = []
    for key, channel_records in grouped.items():
        units = sum(item.units_sold for item in channel_records)
        revenue = sum((item.revenue for item in channel_records), Decimal("0"))
        profit = sum((item.contribution_profit for item in channel_records), Decimal("0"))
        margin = Decimal("0") if revenue == 0 else profit / revenue
        profit_per_unit = Decimal("0") if units == 0 else profit / units
        results.append(
            MarketplacePerformance(
                marketplace=names[key],
                units_sold=units,
                revenue=revenue.quantize(MONEY, rounding=ROUND_HALF_UP),
                contribution_profit=profit.quantize(MONEY, rounding=ROUND_HALF_UP),
                contribution_margin=margin.quantize(RATE, rounding=ROUND_HALF_UP),
                profit_per_unit=profit_per_unit.quantize(MONEY, rounding=ROUND_HALF_UP),
                sku_count=len({item.sku.casefold() for item in channel_records}),
            )
        )

    return tuple(
        sorted(
            results,
            key=lambda item: (
                -item.contribution_profit,
                -item.units_sold,
                -item.contribution_margin,
                item.marketplace.casefold(),
            ),
        )
    )


def write_performance_csv(
    performance: Iterable[MarketplacePerformance],
    path: str | Path,
) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "rank",
                "marketplace",
                "units_sold",
                "revenue",
                "contribution_profit",
                "contribution_margin",
                "profit_per_unit",
                "sku_count",
            ],
        )
        writer.writeheader()
        for rank, item in enumerate(performance, start=1):
            writer.writerow(
                {
                    "rank": rank,
                    "marketplace": item.marketplace,
                    "units_sold": item.units_sold,
                    "revenue": item.revenue,
                    "contribution_profit": item.contribution_profit,
                    "contribution_margin": item.contribution_margin,
                    "profit_per_unit": item.profit_per_unit,
                    "sku_count": item.sku_count,
                }
            )
