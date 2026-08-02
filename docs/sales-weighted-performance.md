# Satış adediyle ağırlıklandırılmış kanal performansı

Listeleme başına kâr marjı tek başına kanal başarısını göstermez. Bir pazaryeri ürün başına yüksek marj üretse bile çok az satış yapıyorsa toplam katkısı düşük kalabilir. Bu rapor gerçekleşen satışları kanal bazında birleştirir ve sıralamayı toplam katkı kârına göre yapar.

## Girdi

```csv
marketplace,sku,units_sold,revenue,contribution_profit
Trendyol,TVS-001,100,100000,12000
N11,CF-001,1,2000,500
```

- `units_sold`: Dönemde gerçekleşen satış adedi
- `revenue`: İade ve iptaller düşüldükten sonra rapora alınan satış geliri
- `contribution_profit`: Komisyon, kargo, ürün maliyeti, hizmet bedeli ve satıcı indirimi sonrası toplam katkı kârı

Türkçe sayı biçimleri (`1.250,50`) desteklenir. Negatif satış adedi ve negatif gelir reddedilir. Katkı kârının negatif olması zarar eden dönemleri göstermek için geçerlidir.

## Kullanım

```bash
marketplace-performance \
  --input reports/2026-07-sales.csv \
  --output reports/2026-07-marketplace-performance.csv
```

## Çıktı

Rapor şu metrikleri üretir:

- toplam satış adedi
- toplam gelir
- toplam katkı kârı
- gerçekleşen katkı marjı
- satış başına katkı kârı
- satılan benzersiz SKU sayısı

Kanallar önce toplam katkı kârına, eşitlikte satış adedine ve gerçekleşen marja göre sıralanır. Böylece tek bir yüksek marjlı satış, yüzlerce sipariş üreten kanalı yanlış biçimde geride bırakamaz.
