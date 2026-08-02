# Türkmopet Marketplace Intelligence

Trendyol, Hepsiburada, N11 ve diğer pazaryerlerindeki ürün listelemelerini; fiyat, komisyon, kargo, ürün maliyeti ve stok sinyalleri üzerinden karşılaştıran açıklanabilir analiz çekirdeği.

## Problem

Aynı motosiklet parçası farklı pazaryerlerinde farklı komisyon ve kargo maliyetleriyle satılıyor. Yalnızca satış fiyatına bakmak, zarar eden veya hedef marjın altında kalan kanalları gizleyebilir. Bu proje her listelemeyi aynı finansal modele çevirerek kanal bazlı katkı kârını ve riskleri görünür hâle getirir.

## Kurulum

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
```

## CSV analizi

Normalize edilmiş ortak CSV:

```bash
marketplace-analyze \
  --input listings.csv \
  --input-format normalized \
  --output reports/analysis.csv
```

Trendyol dışa aktarımı:

```bash
marketplace-analyze \
  --input trendyol-listings.csv \
  --input-format trendyol \
  --output reports/trendyol-analysis.csv
```

Hepsiburada dışa aktarımı:

```bash
marketplace-analyze \
  --input hepsiburada-listings.csv \
  --input-format hepsiburada \
  --output reports/hepsiburada-analysis.csv
```

Hepsiburada adaptörü şu başlıkları otomatik eşler:

- SKU: `Satıcı Stok Kodu`, `Merchant SKU`, `Stok Kodu`, `SKU` veya `Barkod`
- Fiyat: `Fiyat`, `Satış Fiyatı`, `Listing Price` veya `Sale Price`
- Komisyon: `Komisyon Oranı` veya `Commission Rate`
- Kargo: `Kargo Bedeli`, `Kargo Maliyeti` veya `Shipping Cost`
- Maliyet: `Ürün Maliyeti`, `Maliyet` veya `Product Cost`
- Stok: `Satılabilir Stok`, `Stok Adedi`, `Stok` veya `Available Stock`
- İsteğe bağlı maliyetler: `İşlem Bedeli` / `Hizmet Bedeli` ve `Kampanya İndirimi` / `Satıcı İndirimi`

Başlıklar Türkçe karakter, boşluk ve alt çizgi farklılıklarına karşı normalize edilir. İsteğe bağlı maliyet kolonları yoksa `0` kabul edilir. Tekrarlı SKU satırları ve eksik zorunlu kolonlar kontrollü hata üretir.

## Python kullanımı

```python
from decimal import Decimal

from turkmopet_marketplace import ListingSnapshot, analyze_marketplaces

listings = [
    ListingSnapshot(
        sku="MOTUL-5100-10W40",
        marketplace="Trendyol",
        sale_price=Decimal("1000"),
        commission_rate=Decimal("0.15"),
        shipping_cost=Decimal("50"),
        product_cost=Decimal("650"),
        stock=10,
    ),
    ListingSnapshot(
        sku="MOTUL-5100-10W40",
        marketplace="Hepsiburada",
        sale_price=Decimal("800"),
        commission_rate=Decimal("0.15"),
        shipping_cost=Decimal("50"),
        product_cost=Decimal("650"),
        stock=8,
    ),
]

analysis = analyze_marketplaces(listings)

for channel in analysis.economics:
    print(channel.marketplace, channel.contribution_profit)

for issue in analysis.issues:
    print(issue.severity, issue.code, issue.message)
```

## Test

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

## Mimari

```text
CSV sağlayıcı adaptörü
      ↓
ListingSnapshot
      ↓
calculate_channel_economics
      ↓
MarketplaceAnalysis
      ↓
CSV analiz ve kanal önerisi raporları
```

- `adapters.py`: Trendyol ve Hepsiburada başlık normalizasyonu
- `models.py`: doğrulanan, değiştirilemez domain modelleri
- `analysis.py`: fiyat, kârlılık ve kanal tutarlılığı kuralları
- `pipeline.py`: CSV içe aktarma, analiz ve atomik rapor yayını
- `.github/workflows/ci.yml`: otomatik test ve derleme kontrolü

## Teknik kararlar

- Para hesabında kayan nokta hatalarını önlemek için `float` yerine `Decimal` kullanılır.
- Uyarılar kod, önem seviyesi ve Türkçe açıklama döndürür.
- Sağlayıcı CSV şemaları adaptör katmanında ortak modele çevrilir; finansal analiz sağlayıcıdan bağımsız kalır.

## Yol haritası

1. N11 CSV adaptörü
2. Satış adediyle ağırlıklandırılmış kanal performansı
3. Kampanya ve kupon etkisinin dönemsel karşılaştırılması
4. Excel/JSON raporu ve görsel yönetim paneli

## AI destekli geliştirme

Proje AI destekli geliştirme araçları kullanılarak hazırlanır; iş kuralları, testler ve çıktılar insan incelemesiyle doğrulanmadan üretim kararı olarak kullanılmamalıdır.
