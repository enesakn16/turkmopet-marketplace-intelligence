from __future__ import annotations

import argparse

from .performance import (
    aggregate_marketplace_performance,
    read_sales_csv,
    write_performance_csv,
)
from .pipeline import MarketplaceImportError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pazaryeri performansını satış adedi ve gerçekleşen katkı kârıyla sıralar."
    )
    parser.add_argument("--input", required=True, help="Dönemsel satış CSV dosyası")
    parser.add_argument("--output", required=True, help="Kanal performans raporu CSV dosyası")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        records = read_sales_csv(args.input)
        performance = aggregate_marketplace_performance(records)
        write_performance_csv(performance, args.output)
    except (MarketplaceImportError, ValueError) as exc:
        print(f"Hata: {exc}")
        return 2

    print(
        f"{len(records)} satış kaydı işlendi; "
        f"{len(performance)} pazaryeri performansı üretildi."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
