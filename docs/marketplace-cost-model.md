# Pazaryeri maliyet modeli

Listeleme CSV dosyası temel kolonlara ek olarak iki isteğe bağlı maliyet kolonu kabul eder:

```text
service_fee,seller_discount
```

- `service_fee`: Sipariş başına pazaryerinin tahsil ettiği sabit hizmet, işlem veya operasyon bedeli.
- `seller_discount`: Kupon ya da kampanyanın satıcı tarafından karşılanan sipariş başına tutarı.

Kolonlar yoksa veya hücre boşsa değer güvenli biçimde `0` kabul edilir; eski CSV dosyaları çalışmaya devam eder. Negatif tutarlar reddedilir.

## Hesap

```text
komisyon = satış_fiyatı × komisyon_oranı
net_gelir = satış_fiyatı - komisyon - kargo - hizmet_bedeli - satıcı_indirimi
katkı_kârı = net_gelir - ürün_maliyeti
```

Başabaş ve hedef fiyat hesaplarında da hizmet bedeli ile satıcı indirimi sabit maliyetlere eklenir. Böylece kampanyalı bir listeleme, gerçekte zarar ettiği hâlde kârlı görünmez.

## Örnek CSV

```csv
sku,marketplace,sale_price,commission_rate,shipping_cost,product_cost,stock,service_fee,seller_discount
TVS-001,Trendyol,1000,0.20,60,500,3,25,40
```

Bu örnekte katkı kârı `175,00 TL` olur.
