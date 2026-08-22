# Saatcioglu Social Agent

Saatcioglu Supermarket icin ayri ve izole sosyal medya otomasyon projesi.

## Degismez kurallar
- PharmaPilot ve diger projelerden tamamen bagimsizdir.
- Eve teslimat hizmeti yoktur.
- Su anda web sitesi yoktur.
- Fiyat, stok, kampanya, calisma saati veya urun bulunurlugu uydurulmaz.
- Kullanici acikca onaylamadan Instagram'a yayin/schedule yapilmaz.
- Buffer API anahtari kodda tutulmaz; GitHub Actions Secret olarak `BUFFER_API_KEY` adiyla saklanir.

## V1 akis
ChatGPT Market Agent -> onay -> `approved/*.json` -> GitHub Actions -> Buffer -> Instagram

Ilk testlerde guvenlik icin Buffer'a **draft** olusturulur. Akis dogrulandiktan sonra, yalnizca kullanicinin acik onayi sonrasinda kuyruga ekleme veya belirli saate planlama modu etkinlestirilebilir.

## Onay dosyasi ornegi
```json
{
  "approved": true,
  "text": "Paylasim metni",
  "saveToDraft": true
}
```
