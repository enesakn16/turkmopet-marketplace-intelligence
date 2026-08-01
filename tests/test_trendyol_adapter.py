from __future__ import annotations

import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from turkmopet_marketplace import cli
from turkmopet_marketplace.adapters import read_trendyol_csv
from turkmopet_marketplace.pipeline import MarketplaceImportError


class TrendyolAdapterTests(unittest.TestCase):
    def test_normalizes_turkish_headers_and_optional_costs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "trendyol.csv"
            source.write_text(
                "Stok Kodu,Satış Fiyatı,Komisyon Oranı,Kargo Maliyeti,Ürün Maliyeti,Stok Adedi,Hizmet Bedeli,Satıcı İndirimi\n"
                'TVS-001,"1.000,50","0,18",90,700,3,25,40\n',
                encoding="utf-8-sig",
            )

            listings = read_trendyol_csv(source)

            self.assertEqual(len(listings), 1)
            self.assertEqual(listings[0].marketplace, "Trendyol")
            self.assertEqual(listings[0].sale_price, Decimal("1000.50"))
            self.assertEqual(listings[0].commission_rate, Decimal("0.18"))
            self.assertEqual(listings[0].service_fee, Decimal("25"))
            self.assertEqual(listings[0].seller_discount, Decimal("40"))

    def test_accepts_barcode_as_sku_and_defaults_optional_costs_to_zero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "trendyol.csv"
            source.write_text(
                "Barkod,Satis Fiyati,Komisyon Orani,Kargo Maliyeti,Urun Maliyeti,Stok\n"
                "8690001,900,0.18,90,700,3\n",
                encoding="utf-8",
            )

            listing = read_trendyol_csv(source)[0]

            self.assertEqual(listing.sku, "8690001")
            self.assertEqual(listing.service_fee, Decimal("0"))
            self.assertEqual(listing.seller_discount, Decimal("0"))

    def test_rejects_unmapped_required_columns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "trendyol.csv"
            source.write_text("Barkod,Satış Fiyatı\n8690001,900\n", encoding="utf-8")

            with self.assertRaisesRegex(MarketplaceImportError, "eşleştirilemedi"):
                read_trendyol_csv(source)

    def test_rejects_duplicate_sku(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "trendyol.csv"
            source.write_text(
                "Barkod,Satış Fiyatı,Komisyon Oranı,Kargo Maliyeti,Ürün Maliyeti,Stok\n"
                "8690001,900,0.18,90,700,3\n"
                "8690001,950,0.18,90,700,4\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(MarketplaceImportError, "birden fazla"):
                read_trendyol_csv(source)

    def test_cli_uses_trendyol_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "trendyol.csv"
            report = root / "report.csv"
            source.write_text(
                "Stok Kodu,Satış Fiyatı,Komisyon Oranı,Kargo Maliyeti,Ürün Maliyeti,Stok\n"
                "TVS-001,1200,0.18,90,700,3\n",
                encoding="utf-8-sig",
            )
            argv = [
                "marketplace-analyze",
                "--input", str(source),
                "--input-format", "trendyol",
                "--output", str(report),
            ]

            with patch("sys.argv", argv):
                exit_code = cli.main()

            self.assertEqual(exit_code, 0)
            self.assertTrue(report.exists())


if __name__ == "__main__":
    unittest.main()
