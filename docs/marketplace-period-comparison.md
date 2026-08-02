# Pazaryeri dönem karşılaştırması

Aylık veya haftalık `marketplace-performance` raporlarını karşılaştırarak kanal bazında satış, gelir, katkı kârı ve marj değişimini gösterir.

```bash
marketplace-performance-compare \
  --previous reports/2026-06-marketplace-performance.csv \
  --current reports/2026-07-marketplace-performance.csv \
  --output reports/2026-07-marketplace-change.csv
```

## Hareket sınıfları

- `declined`: Güncel katkı kârı önceki dönemden düşük.
- `missing`: Önceki dönemde bulunan kanal güncel raporda yok.
- `improved`: Güncel katkı kârı arttı.
- `new`: Kanal güncel dönemde ilk kez göründü.
- `stable`: Katkı kârı değişmedi.

Rapor, inceleme sırasını kolaylaştırmak için önce gerileyen ve kaybolan kanalları gösterir. Her kanal için satış adedi, gelir, katkı kârı ve marjın önceki değerini, güncel değerini ve farkını yazar.

## Güvenlik

Aynı pazaryerinin büyük-küçük harf farkıyla iki kez bulunması reddedilir. Eksik zorunlu kolonlar, negatif satış adetleri ve geçersiz sayılar kontrollü hata üretir.
