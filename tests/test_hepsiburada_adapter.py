from __future__ import annotations

import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from turkmopet_marketplace import cli
from turkmopet_marketplace.adapters import read_hepsiburada_csv
from turkmopet_marketplace.pipeline import MarketplaceImportError


class HepsiburadaAdapterTests(unittest.TestCase):
    def test_normalizes_hepsiburada_headers_and_costs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "hepsiburada.csv"
            source.write_text(
                "Satıcı Stok Kodu,Fiyat,Komisyon Oranı,Kargo Bedeli,Ürün Maliyeti,Satılabilir Stok,İşlem Bedeli,Kampanya İndirimi\n"
                'TVS-001,"1.250,50","0,19",95,700,4,20,35\n',
                encoding="utf-8-sig",
            )

            listings = read_hepsiburada_csv(source)

            self.assertEqual(len(listings), 1)
            listing = listings[0]
            self.assertEqual(listing.marketplace, "Hepsiburada")
            self.assertEqual(listing.sku, "TVS-001")
            self.assertEqual(listing.sale_price, Decimal("1250.50"))
            self.assertEqual(listing.commission_rate, Decimal("0.19"))
            self.assertEqual(listing.shipping_cost, Decimal("95"))
            self.assertEqual(listing.service_fee, Decimal("20"))
            self.assertEqual(listing.seller_discount, Decimal("35"))

    def test_accepts_merchant_sku_and_defaults_optional_costs_to_zero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "hepsiburada.csv"
            source.write_text(
                "Merchant SKU,Sale Price,Commission Rate,Shipping Cost,Product Cost,Available Stock\n"
                "8690001,900,0.18,90,700,3\n",
                encoding="utf-8",
            )

            listing = read_hepsiburada_csv(source)[0]

            self.assertEqual(listing.sku, "8690001")
            self.assertEqual(listing.service_fee, Decimal("0"))
            self.assertEqual(listing.seller_discount, Decimal("0"))

    def test_rejects_unmapped_required_columns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "hepsiburada.csv"
            source.write_text("Satıcı Stok Kodu,Fiyat\nTVS-001,900\n", encoding="utf-8")

            with self.assertRaisesRegex(MarketplaceImportError, "Hepsiburada CSV kolonları"):
                read_hepsiburada_csv(source)

    def test_rejects_duplicate_sku_case_insensitively(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "hepsiburada.csv"
            source.write_text(
                "Satıcı Stok Kodu,Fiyat,Komisyon Oranı,Kargo Bedeli,Maliyet,Stok\n"
                "TVS-001,900,0.18,90,700,3\n"
                "tvs-001,950,0.18,90,700,4\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(MarketplaceImportError, "birden fazla"):
                read_hepsiburada_csv(source)

    def test_cli_uses_hepsiburada_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "hepsiburada.csv"
            report = root / "report.csv"
            source.write_text(
                "Satıcı Stok Kodu,Fiyat,Komisyon Oranı,Kargo Bedeli,Maliyet,Stok\n"
                "TVS-001,1200,0.18,90,700,3\n",
                encoding="utf-8-sig",
            )
            argv = [
                "marketplace-analyze",
                "--input",
                str(source),
                "--input-format",
                "hepsiburada",
                "--output",
                str(report),
            ]

            with patch("sys.argv", argv):
                exit_code = cli.main()

            self.assertEqual(exit_code, 0)
            self.assertTrue(report.exists())


if __name__ == "__main__":
    unittest.main()
