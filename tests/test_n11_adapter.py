from __future__ import annotations

import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from turkmopet_marketplace.adapters import read_n11_csv
from turkmopet_marketplace.pipeline import MarketplaceImportError


class N11AdapterTests(unittest.TestCase):
    def _write(self, content: str) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "n11.csv"
        path.write_text(content, encoding="utf-8-sig")
        return path

    def test_reads_turkish_n11_headers_and_optional_costs(self) -> None:
        path = self._write(
            "Mağaza Ürün Kodu,Mağaza Satış Fiyatı,Komisyon Oranı,Kargo Bedeli,Ürün Maliyeti,Stok Miktarı,İşlem Bedeli,Mağaza İndirimi\n"
            'TVS-001,"1.250,50","0,18","79,90","800,00",7,"12,50","25,00"\n'
        )

        listings = read_n11_csv(path)

        self.assertEqual(len(listings), 1)
        listing = listings[0]
        self.assertEqual(listing.sku, "TVS-001")
        self.assertEqual(listing.marketplace, "N11")
        self.assertEqual(listing.sale_price, Decimal("1250.50"))
        self.assertEqual(listing.commission_rate, Decimal("0.18"))
        self.assertEqual(listing.shipping_cost, Decimal("79.90"))
        self.assertEqual(listing.product_cost, Decimal("800.00"))
        self.assertEqual(listing.stock, 7)
        self.assertEqual(listing.service_fee, Decimal("12.50"))
        self.assertEqual(listing.seller_discount, Decimal("25.00"))

    def test_optional_costs_default_to_zero(self) -> None:
        path = self._write(
            "Seller SKU,Price,Commission,Shipping Cost,Product Cost,Quantity\n"
            "CG-125,1000,0.15,60,650,4\n"
        )

        listing = read_n11_csv(path)[0]

        self.assertEqual(listing.service_fee, Decimal("0"))
        self.assertEqual(listing.seller_discount, Decimal("0"))

    def test_rejects_case_insensitive_duplicate_sku(self) -> None:
        path = self._write(
            "Stok Kodu,Fiyat,Komisyon,Kargo Maliyeti,Maliyet,Stok\n"
            "ABC-1,1000,0.15,60,650,4\n"
            "abc-1,1100,0.15,60,650,3\n"
        )

        with self.assertRaisesRegex(MarketplaceImportError, "birden fazla"):
            read_n11_csv(path)

    def test_rejects_missing_required_columns(self) -> None:
        path = self._write("Mağaza Ürün Kodu,Fiyat,Stok\nTVS-001,1000,2\n")

        with self.assertRaisesRegex(MarketplaceImportError, "kolonları eşleştirilemedi"):
            read_n11_csv(path)


if __name__ == "__main__":
    unittest.main()
