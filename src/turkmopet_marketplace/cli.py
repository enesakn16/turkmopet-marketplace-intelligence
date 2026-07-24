from __future__ import annotations

import argparse
from decimal import Decimal

from .pipeline import (
    MarketplaceImportError,
    read_listings_csv,
    run_marketplace_pipeline,
    write_channel_recommendations_csv,
    write_report_csv,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pazaryeri listelemelerini kârlılık ve fiyat hedefleri açısından analiz eder."
    )
    parser.add_argument("--input", required=True, help="Listeleme CSV dosyası")
    parser.add_argument("--output", required=True, help="Analiz raporu CSV dosyası")
    parser.add_argument(
        "--recommendations-output",
        help="SKU bazlı önerilen pazaryeri raporu CSV dosyası",
    )
    parser.add_argument("--minimum-margin", default="0.10")
    parser.add_argument("--target-margin", default="0.10")
    parser.add_argument("--price-gap-threshold", default="0.12")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        listings = read_listings_csv(args.input)
        result = run_marketplace_pipeline(
            listings,
            minimum_margin=Decimal(args.minimum_margin),
            target_margin=Decimal(args.target_margin),
            price_gap_threshold=Decimal(args.price_gap_threshold),
        )
        write_report_csv(result, args.output)
        if args.recommendations_output:
            write_channel_recommendations_csv(
                result,
                args.recommendations_output,
            )
    except (MarketplaceImportError, ValueError) as exc:
        print(f"Hata: {exc}")
        return 2

    print(
        f"{len(result.listings)} listeleme analiz edildi; "
        f"{len(result.analysis.issues)} uyarı ve "
        f"{len(result.channel_recommendations)} kanal önerisi üretildi."
    )
    return 1 if result.analysis.issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
