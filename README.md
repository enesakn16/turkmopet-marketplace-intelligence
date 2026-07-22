# Türkmopet Marketplace Intelligence

Trendyol, Hepsiburada, N11 ve diğer pazaryerlerindeki ürün listelemelerini; fiyat, komisyon, kargo, ürün maliyeti ve stok sinyalleri üzerinden karşılaştıran açıklanabilir analiz çekirdeği.

## Problem

Aynı motosiklet parçası farklı pazaryerlerinde farklı komisyon ve kargo maliyetleriyle satılıyor. Yalnızca satış fiyatına bakmak, zarar eden veya hedef marjın altında kalan kanalları gizleyebilir. Bu proje her listelemeyi aynı finansal modele çevirerek kanal bazlı katkı kârını ve riskleri görünür hâle getirir.

## İlk sürümde bulunanlar

- Komisyon sonrası net gelir hesabı
- Ürün maliyeti ve kargo sonrası katkı kârı
- Katkı marjı hesabı
- Zarar eden listeleme tespiti
- Hedef marjın altında kalan kanal uyarısı
- Sıfır stok uyarısı
- Aynı SKU için kanallar arası fiyat farkı denetimi
- `Decimal` tabanlı para hesabı
- Python 3.12 CI, test ve derleme kontrolü

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

## Kullanım

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
ListingSnapshot
      ↓
calculate_channel_economics
      ↓
ChannelEconomics
      ↓
analyze_marketplaces
      ↓
MarketplaceAnalysis (ekonomi + açıklanabilir sorunlar)
```

- `models.py`: doğrulanan, değiştirilemez domain modelleri
- `analysis.py`: fiyat, kârlılık ve kanal tutarlılığı kuralları
- `tests/test_analysis.py`: finansal hesap ve risk senaryoları
- `.github/workflows/ci.yml`: otomatik test ve derleme kontrolü

## Teknik kararlar

- Para hesabında kayan nokta hatalarını önlemek için `float` yerine `Decimal` kullanılır.
- Uyarılar yalnızca puan üretmez; kod, önem seviyesi ve Türkçe açıklama döndürür.
- Pazaryeri verisi henüz herhangi bir sağlayıcıya bağlanmamıştır. Çekirdek bağımsız tutulduğu için CSV, API veya panel adaptörleri sonradan eklenebilir.

## Yol haritası

1. Trendyol, Hepsiburada ve N11 CSV adaptörleri
2. Satış adediyle ağırlıklandırılmış kanal performansı
3. Minimum satış fiyatı önerisi
4. Kampanya ve kupon etkisi
5. Excel/JSON raporu ve görsel yönetim paneli

## AI destekli geliştirme

Proje AI destekli geliştirme araçları kullanılarak hazırlanır; iş kuralları, testler ve çıktılar insan incelemesiyle doğrulanmadan üretim kararı olarak kullanılmamalıdır.
