from __future__ import annotations

import argparse

from .performance_compare import (
    compare_performance_periods,
    read_performance_csv,
    write_performance_changes,
)
from .pipeline import MarketplaceImportError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="İki dönem pazaryeri performansını karşılaştırır."
    )
    parser.add_argument("--previous", required=True, help="Önceki dönem performans CSV dosyası")
    parser.add_argument("--current", required=True, help="Güncel dönem performans CSV dosyası")
    parser.add_argument("--output", required=True, help="Dönem karşılaştırma CSV dosyası")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        previous = read_performance_csv(args.previous)
        current = read_performance_csv(args.current)
        changes = compare_performance_periods(previous, current)
        write_performance_changes(changes, args.output)
    except (MarketplaceImportError, ValueError) as exc:
        print(f"Hata: {exc}")
        return 2

    declined = sum(item.movement in {"declined", "missing"} for item in changes)
    print(
        f"{len(changes)} pazaryeri karşılaştırıldı; "
        f"{declined} kanal gerileme veya kayıp gösterdi."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
