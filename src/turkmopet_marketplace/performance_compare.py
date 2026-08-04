from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable

from .pipeline import MarketplaceImportError

MONEY = Decimal("0.01")
RATE = Decimal("0.0001")
DEFAULT_CRITICAL_DECLINE = Decimal("0.20")
DEFAULT_WARNING_DECLINE = Decimal("0.05")


@dataclass(frozen=True, slots=True)
class PerformanceSnapshot:
    marketplace: str
    units_sold: int
    revenue: Decimal
    contribution_profit: Decimal
    contribution_margin: Decimal


@dataclass(frozen=True, slots=True)
class PerformanceChange:
    marketplace: str
    previous_units_sold: int
    current_units_sold: int
    units_delta: int
    previous_revenue: Decimal
    current_revenue: Decimal
    revenue_delta: Decimal
    previous_profit: Decimal
    current_profit: Decimal
    profit_delta: Decimal
    profit_change_rate: Decimal | None
    previous_margin: Decimal
    current_margin: Decimal
    margin_delta: Decimal
    movement: str
    alert_level: str


def _decimal(value: str, *, field: str, row_number: int) -> Decimal:
    try:
        return Decimal(value.strip())
    except InvalidOperation as exc:
        raise MarketplaceImportError(
            f"Satır {row_number}: {field} geçerli bir sayı değil: {value!r}"
        ) from exc


def _validate_decline_thresholds(
    *, critical_decline: Decimal, warning_decline: Decimal
) -> None:
    if warning_decline <= 0 or critical_decline <= 0:
        raise ValueError("Gerileme eşikleri sıfırdan büyük olmalıdır")
    if warning_decline >= critical_decline:
        raise ValueError("Uyarı eşiği kritik eşikten küçük olmalıdır")
    if critical_decline > 1:
        raise ValueError("Kritik gerileme eşiği 1 değerini aşamaz")


def _profit_change_rate(previous: Decimal, current: Decimal) -> Decimal | None:
    delta = current - previous
    if previous > 0:
        return (delta / previous).quantize(RATE, rounding=ROUND_HALF_UP)
    if previous < 0:
        return (delta / abs(previous)).quantize(RATE, rounding=ROUND_HALF_UP)
    return None


def _alert_level(
    *,
    movement: str,
    previous_profit: Decimal,
    current_profit: Decimal,
    profit_change_rate: Decimal | None,
    critical_decline: Decimal,
    warning_decline: Decimal,
) -> str:
    if movement == "missing":
        return "critical"
    if movement != "declined":
        return "stable"
    if previous_profit == 0 and current_profit < 0:
        return "critical"
    if profit_change_rate is None:
        return "warning"
    decline = -profit_change_rate
    if decline >= critical_decline:
        return "critical"
    if decline >= warning_decline:
        return "warning"
    return "stable"


def read_performance_csv(path: str | Path) -> tuple[PerformanceSnapshot, ...]:
    source = Path(path)
    required = {
        "marketplace",
        "units_sold",
        "revenue",
        "contribution_profit",
        "contribution_margin",
    }
    try:
        handle = source.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise MarketplaceImportError(f"Performans CSV dosyası açılamadı: {source}") from exc

    snapshots: list[PerformanceSnapshot] = []
    seen: set[str] = set()
    with handle:
        reader = csv.DictReader(handle)
        missing = sorted(required - set(reader.fieldnames or ()))
        if missing:
            raise MarketplaceImportError("Eksik performans CSV kolonları: " + ", ".join(missing))
        for row_number, row in enumerate(reader, start=2):
            marketplace = (row.get("marketplace") or "").strip()
            if not marketplace:
                raise MarketplaceImportError(f"Satır {row_number}: marketplace boş olamaz")
            key = marketplace.casefold()
            if key in seen:
                raise MarketplaceImportError(
                    f"Satır {row_number}: tekrarlı pazaryeri: {marketplace}"
                )
            seen.add(key)
            try:
                units = int((row.get("units_sold") or "").strip())
            except ValueError as exc:
                raise MarketplaceImportError(
                    f"Satır {row_number}: units_sold geçerli bir tam sayı değil"
                ) from exc
            if units < 0:
                raise MarketplaceImportError(f"Satır {row_number}: units_sold negatif olamaz")
            snapshots.append(
                PerformanceSnapshot(
                    marketplace=marketplace,
                    units_sold=units,
                    revenue=_decimal(row.get("revenue") or "", field="revenue", row_number=row_number),
                    contribution_profit=_decimal(
                        row.get("contribution_profit") or "",
                        field="contribution_profit",
                        row_number=row_number,
                    ),
                    contribution_margin=_decimal(
                        row.get("contribution_margin") or "",
                        field="contribution_margin",
                        row_number=row_number,
                    ),
                )
            )
    return tuple(snapshots)


def compare_performance_periods(
    previous: Iterable[PerformanceSnapshot],
    current: Iterable[PerformanceSnapshot],
    *,
    critical_decline: Decimal = DEFAULT_CRITICAL_DECLINE,
    warning_decline: Decimal = DEFAULT_WARNING_DECLINE,
) -> tuple[PerformanceChange, ...]:
    _validate_decline_thresholds(
        critical_decline=critical_decline, warning_decline=warning_decline
    )
    previous_map = {item.marketplace.casefold(): item for item in previous}
    current_map = {item.marketplace.casefold(): item for item in current}
    names = {key: item.marketplace for key, item in previous_map.items()}
    names.update({key: item.marketplace for key, item in current_map.items()})

    changes: list[PerformanceChange] = []
    for key in previous_map.keys() | current_map.keys():
        old = previous_map.get(key)
        new = current_map.get(key)
        previous_units = old.units_sold if old else 0
        current_units = new.units_sold if new else 0
        previous_revenue = old.revenue if old else Decimal("0")
        current_revenue = new.revenue if new else Decimal("0")
        previous_profit = old.contribution_profit if old else Decimal("0")
        current_profit = new.contribution_profit if new else Decimal("0")
        previous_margin = old.contribution_margin if old else Decimal("0")
        current_margin = new.contribution_margin if new else Decimal("0")
        if old is None:
            movement = "new"
        elif new is None:
            movement = "missing"
        elif current_profit > previous_profit:
            movement = "improved"
        elif current_profit < previous_profit:
            movement = "declined"
        else:
            movement = "stable"
        change_rate = _profit_change_rate(previous_profit, current_profit)
        changes.append(
            PerformanceChange(
                marketplace=names[key],
                previous_units_sold=previous_units,
                current_units_sold=current_units,
                units_delta=current_units - previous_units,
                previous_revenue=previous_revenue.quantize(MONEY, rounding=ROUND_HALF_UP),
                current_revenue=current_revenue.quantize(MONEY, rounding=ROUND_HALF_UP),
                revenue_delta=(current_revenue - previous_revenue).quantize(MONEY, rounding=ROUND_HALF_UP),
                previous_profit=previous_profit.quantize(MONEY, rounding=ROUND_HALF_UP),
                current_profit=current_profit.quantize(MONEY, rounding=ROUND_HALF_UP),
                profit_delta=(current_profit - previous_profit).quantize(MONEY, rounding=ROUND_HALF_UP),
                profit_change_rate=change_rate,
                previous_margin=previous_margin.quantize(RATE, rounding=ROUND_HALF_UP),
                current_margin=current_margin.quantize(RATE, rounding=ROUND_HALF_UP),
                margin_delta=(current_margin - previous_margin).quantize(RATE, rounding=ROUND_HALF_UP),
                movement=movement,
                alert_level=_alert_level(
                    movement=movement,
                    previous_profit=previous_profit,
                    current_profit=current_profit,
                    profit_change_rate=change_rate,
                    critical_decline=critical_decline,
                    warning_decline=warning_decline,
                ),
            )
        )
    alert_priority = {"critical": 0, "warning": 1, "stable": 2}
    movement_priority = {"declined": 0, "missing": 1, "improved": 2, "new": 3, "stable": 4}
    return tuple(
        sorted(
            changes,
            key=lambda item: (
                alert_priority[item.alert_level],
                movement_priority[item.movement],
                item.profit_delta,
                item.marketplace.casefold(),
            ),
        )
    )


def write_performance_changes(changes: Iterable[PerformanceChange], path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8-sig", newline="") as handle:
        fieldnames = [
            "marketplace",
            "previous_units_sold",
            "current_units_sold",
            "units_delta",
            "previous_revenue",
            "current_revenue",
            "revenue_delta",
            "previous_profit",
            "current_profit",
            "profit_delta",
            "profit_change_rate",
            "previous_margin",
            "current_margin",
            "margin_delta",
            "movement",
            "alert_level",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in changes:
            row = {field: getattr(item, field) for field in fieldnames}
            row["profit_change_rate"] = (
                "" if item.profit_change_rate is None else item.profit_change_rate
            )
            writer.writerow(row)
