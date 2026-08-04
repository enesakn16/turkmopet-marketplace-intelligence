# Pazaryeri gerileme alarmları

`marketplace-performance-compare`, iki dönem arasındaki katkı kârı değişimini yüzdesel olarak hesaplar ve kanalları operasyon önceliğine göre sınıflandırır.

## Varsayılan eşikler

- `critical`: katkı kârı en az %20 düştü, kanal güncel dönemde kayboldu veya sıfır kârdan zarara geçti.
- `warning`: katkı kârı %5 ile %20 arasında düştü.
- `stable`: düşüş %5'in altında kaldı ya da kanal gerilemedi.

## Kullanım

```bash
marketplace-performance-compare \
  --previous reports/2026-06-marketplace-performance.csv \
  --current reports/2026-07-marketplace-performance.csv \
  --output reports/2026-07-marketplace-change.csv
```

Eşikler gerektiğinde değiştirilebilir:

```bash
marketplace-performance-compare \
  --previous previous.csv \
  --current current.csv \
  --output alerts.csv \
  --critical-decline 0.25 \
  --warning-decline 0.10
```

Uyarı eşiği kritik eşikten küçük olmalıdır. Oranlar `0` ile `1` arasında verilir.

## Çıktı alanları

Karşılaştırma raporuna iki alan eklenir:

- `profit_change_rate`: önceki döneme göre katkı kârı değişim oranı.
- `alert_level`: `critical`, `warning` veya `stable`.

Önceki katkı kârı sıfırsa yüzdesel değişim matematiksel olarak tanımsızdır. Bu durumda alan boş bırakılır; güncel dönem zarar gösteriyorsa alarm doğrudan `critical` olur.

## Otomasyon davranışı

- Kritik alarm yoksa komut `0` döner.
- En az bir kritik alarm varsa komut `1` döner.
- Girdi veya eşik hatasında komut `2` döner.

Araç fiyat, stok veya pazaryeri ayarlarını otomatik değiştirmez. Çıktı yalnızca inceleme ve aksiyon önceliklendirmesi içindir.
