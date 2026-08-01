# Trendyol CSV içe aktarma

Trendyol dışa aktarımına operasyonel maliyet kolonları eklendikten sonra dosya ortak şemaya elle çevrilmeden analiz edilebilir.

```bash
marketplace-analyze \
  --input trendyol-listings.csv \
  --input-format trendyol \
  --output reports/trendyol-analysis.csv
```

## Desteklenen kolon adları

Adaptör Türkçe karakter, boşluk ve alt çizgi farklarını normalize eder.

| Ortak alan | Kabul edilen örnek başlıklar |
| --- | --- |
| SKU | `Stok Kodu`, `Barkod`, `SKU` |
| Satış fiyatı | `Satış Fiyatı`, `Satis Fiyati` |
| Komisyon oranı | `Komisyon Oranı`, `Komisyon Orani` |
| Kargo maliyeti | `Kargo Maliyeti` |
| Ürün maliyeti | `Ürün Maliyeti`, `Urun Maliyeti` |
| Stok | `Stok`, `Stok Adedi` |
| Hizmet bedeli | `Hizmet Bedeli` |
| Satıcı indirimi | `Satıcı İndirimi` |

İlk altı alan zorunludur. Hizmet bedeli ve satıcı indirimi bulunmazsa `0` kabul edilir.

## Sayı biçimleri

Aşağıdaki biçimler desteklenir:

- `1000.50`
- `1000,50`
- `1.000,50`
- `1,000.50`

Aynı SKU dosyada birden fazla kez bulunursa analiz durdurulur. Pazaryeri alanı adaptör tarafından sabit olarak `Trendyol` atanır.
