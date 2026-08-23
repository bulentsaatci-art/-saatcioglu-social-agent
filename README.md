# Saatcioglu Social Agent

Saatcioglu Supermarket icin ayri ve izole sosyal medya otomasyon projesi.

## Degismez kurallar
- PharmaPilot ve diger projelerden tamamen bagimsizdir.
- Eve teslimat hizmeti yoktur.
- Su anda web sitesi yoktur.
- Meyve/sebze reyonu yoktur.
- Fiyat, stok, kampanya, calisma saati veya urun bulunurlugu uydurulmaz.
- Alkol ve tutun urunleri sosyal medyada tanitilmaz, onerilmez veya bilerek one cikarilmaz.
- Buffer API anahtari kodda tutulmaz; GitHub Actions Secret olarak `BUFFER_API_KEY` adiyla saklanir.

## Otonom yonetim yetkisi
Kullanici 23 Agustos 2026 itibariyla rutin sosyal medya yonetimini ajana devretmistir. Ajan dusuk riskli, dogrulanmis ve marka kurallarina uygun normal icerikleri tekrar tekrar onay istemeden hazirlayabilir, planlayabilir ve yayinlayabilir.

Fiyat/indirim/stok/calisma saati/cekilis/odeme/sozlesme/ortaklik gibi yuksek riskli veya dogrulama gerektiren iddialar uydurulmaz. Dogrulanamayan bilgi yayinlanmaz.

Eski feed temizliginde guncelligini yitirmis, yaniltici (ornegin eski web sitesi/eve teslimat/online siparis), mukerrer veya marka gorunumunu belirgin bozan icerikler temizleme adayi kabul edilir. Teknik olarak mumkun oldugunda arsiv silmeye tercih edilir.

## Calisan akis
ChatGPT Market Agent -> GitHub Actions -> Buffer -> @saatcioglusupermarket Instagram

Bu akis test edilmis ve hem Reel hem de normal feed postu basariyla yayinlamistir.
