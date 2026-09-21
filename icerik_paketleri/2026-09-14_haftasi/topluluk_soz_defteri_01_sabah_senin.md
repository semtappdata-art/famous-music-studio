# Söz Defteri #1 — Sabah Senin (YouTube Topluluk, insan emeği)

- **Yayın:** Çarşamba 16 Eylül 2026, **20:30** (golden-hour). Takvim kaydı:
  `KNL-2026-09-16-soz_defteri_topluluk`, bağlı TikTok kaydı `KNL-2026-09-15-soz_defteri`.
  Kesin an: yayın günü `python turev_takvimi.py takvim --gun 2`. TikTok sürümü kayarsa bu
  gönderi de kendiliğinden en az 24 saat arkasına kayar. **13 Eylül takvimine göre** TikTok sürümü
  15 Eylül'deki şarkı kesiti yüzünden 16 Eylül 12:00'ye kayıyor, bu gönderi de **17 Eylül 12:00**'ye.
- **Elle, Studio'dan.** YouTube Data API Topluluk gönderisi oluşturmayı desteklemiyor; otomasyon
  bunu yapamaz ve yapmaya çalışmaz.
- **Önce doğrula (tek seferlik):** YouTube Studio → Oluştur → "Gönderi oluştur" görünüyor mu?
  Kanal Topluluk sekmesi bu kanalda açık değilse gönderiyi yapma, deftere not düş
  (`python elle_islem.py ekle --platform youtube --islem kontrol_etti --ayrinti "Topluluk sekmesi kapalı"`).
- **Kural:** TikTok sürümünden en az 24 saat sonra. Haftalık 2 insan emeği tavanına sayılmaz
  (aynı içeriğin ikinci yüzeyi). Yeni şarkı yayınının ±24 saatine düşmez; TikTok şarkı kesiti
  günü kuralı Topluluk'a uygulanmaz (ayrı yüzey).
- **Kaynak:** `sabah_senin_sozler_eski_2026-09-13.md` → `sabah_senin_sozler.md` ve TikTok paketi
  `soz_defteri_01_sabah_senin.md`. Uydurma örnek yok.

> **Dürüstlük notu.** Yeni sürüm bir yazım yardımcısıyla hazırlandı; seçim ve onay senin. Metin
> "biz" diliyle yazıldı. "Hepsini tek başıma yazdım" deme.

## 1. Görsel

TikTok çekimindeki defter sayfasının **tek bir fotoğrafı**: üstü çizilmiş eski dize ve altına
farklı renkle yazılmış yeni dize okunur olsun. Kare ya da 4:5. Yüz, adres, ekran bildirimi yok.

## 2. Gönderi metni (olduğu gibi yapıştır)

```
Söz Defteri #1 — Sabah Senin ✍️

Bu şarkının sözleri iki kez yazıldı. İlk hâli dört buçuk dakika sürüyordu ve hikâye bir servisin camında, yolda başlıyordu.

İkinci yazımda hikâyeyi evin içine taşıdık:
Eski: "Servisin camında alnım, şehir akar"
Yeni: "Saat dört, demlik çoktan soğudu"

Nakaratın asıl cümlesi eskiden iki satıra bölünmüştü, şimdi tek satır ve en başta: "Gece benden, sabah senin."

Uzun kalan ve kafiyesi tutmayan bir dizeyi de çıkardık:
Eski: "Eşiği yalnız sabah geçsin, bir de ben"
Yeni: "Dönüp bakmam, bakarsam kalırım"

Sen hangisini seçerdin? 👇
```

## 3. Anket (isteğe bağlı, Studio'da "Anket" ekle)

- Soru: **Nakarat hangisiyle açılmalı?**
- Seçenek 1: `Gece benden, sabah senin`
- Seçenek 2: `Eski hâli daha iyiydi`

Anket eklersen görseli ayrı bir gönderiye bölme; Studio tek gönderide ya görsel ya anket
izin veriyorsa **anketi** seç, fotoğrafı TikTok'ta zaten gösterdik.

## 4. Kurallar

- Dış link YOK (YouTube linki, site, TikTok adresi yok). Hashtag en fazla 1: `#FamousMusicStudio`
  (isteğe bağlı).
- Üretim aracının adı, "yapay zeka" vurgusu, AI hashtag'i YOK.
- **AI beyan satırı: GEREKMEZ** — TikTok paketindeki mantık: gönderide AI müzik ya da ses yok,
  içerik senin defterin ve metnin. Gönderiye şarkının sesini/videosunu eklersen (Topluluk'ta
  video bağlama) açıklamanın sonuna şu satırı ekle:
  `Söz: Famous Music Studio · Müzik ve vokal: AI destekli`
- Yorumlara ilk 24 saatte elle yanıt ver (`yorum_yanit_rehberi.md`); aynı cümleyi iki kişiye yazma.

## 5. Yayından sonra

```
python elle_islem.py ekle --platform youtube --islem yayinladi --ayrinti "Topluluk: Söz Defteri #1 — Sabah Senin (KNL-2026-09-16-soz_defteri_topluluk)"
```

Not: bu defter kaydı kanal takvimindeki kaydı otomatik `yayinlandi` yapmaz (kanal kayıtları
`elle_islem` eşleşmesine bağlı değil); takvimde "planlı" görünmeye devam ederse
`python turev_takvimi.py iptal KNL-2026-09-16-soz_defteri_topluluk --sebep "elle yayınlandı"` KULLANMA —
kaydı olduğu gibi bırak, pencere geçince kendiliğinden düşer.
