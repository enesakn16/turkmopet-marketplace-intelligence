from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation

from .decline_tasks import synchronize_decline_tasks
from .performance_compare import (
    DEFAULT_CRITICAL_DECLINE,
    DEFAULT_WARNING_DECLINE,
    compare_performance_periods,
    read_performance_csv,
    write_performance_changes,
)
from .pipeline import MarketplaceImportError


def _rate(value: str) -> Decimal:
    try:
        rate = Decimal(value)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError("Geçerli bir ondalık oran girilmelidir") from exc
    if rate <= 0 or rate > 1:
        raise argparse.ArgumentTypeError("Oran 0 ile 1 arasında olmalıdır")
    return rate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="İki dönem pazaryeri performansını karşılaştırır ve gerileme alarmı üretir."
    )
    parser.add_argument("--previous", required=True, help="Önceki dönem performans CSV dosyası")
    parser.add_argument("--current", required=True, help="Güncel dönem performans CSV dosyası")
    parser.add_argument("--output", required=True, help="Dönem karşılaştırma CSV dosyası")
    parser.add_argument(
        "--task-database",
        help="Kritik gerilemeleri kalıcı operasyon görevlerine yazacak SQLite dosyası",
    )
    parser.add_argument(
        "--critical-decline",
        type=_rate,
        default=DEFAULT_CRITICAL_DECLINE,
        help="Kritik katkı kârı düşüş oranı (varsayılan: 0.20)",
    )
    parser.add_argument(
        "--warning-decline",
        type=_rate,
        default=DEFAULT_WARNING_DECLINE,
        help="Uyarı katkı kârı düşüş oranı (varsayılan: 0.05)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        previous = read_performance_csv(args.previous)
        current = read_performance_csv(args.current)
        changes = compare_performance_periods(
            previous,
            current,
            critical_decline=args.critical_decline,
            warning_decline=args.warning_decline,
        )
        write_performance_changes(changes, args.output)
        tasks = (
            synchronize_decline_tasks(changes, args.task_database)
            if args.task_database
            else ()
        )
    except (MarketplaceImportError, OSError, ValueError) as exc:
        print(f"Hata: {exc}")
        return 2

    critical = sum(item.alert_level == "critical" for item in changes)
    warning = sum(item.alert_level == "warning" for item in changes)
    task_summary = f"; {len(tasks)} görev senkronize edildi" if args.task_database else ""
    print(
        f"{len(changes)} pazaryeri karşılaştırıldı; "
        f"{critical} kritik, {warning} uyarı seviyesi bulundu{task_summary}."
    )
    return 1 if critical else 0


if __name__ == "__main__":
    raise SystemExit(main())
