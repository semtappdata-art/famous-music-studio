# Kulis #1 — Bir kapak nasıl seçiliyor? (Kırık Zincir) (YouTube Topluluk, insan emeği)

- **Yayın:** Pazar 20 Eylül 2026, **13:00** (golden-hour). Takvim kaydı:
  `KNL-2026-09-20-kulis_topluluk`, bağlı TikTok kaydı `KNL-2026-09-19-kulis`.
  Kesin an: yayın günü `python turev_takvimi.py takvim --gun 2`. TikTok sürümü kayarsa bu
  gönderi de en az 24 saat arkasına kayar.
- **Elle, Studio'dan.** YouTube Data API Topluluk gönderisini desteklemiyor.
- **Önce doğrula:** Studio → Oluştur → "Gönderi oluştur" görünüyor mu? Görünmüyorsa yapma, deftere
  `kontrol_etti` notu düş (Söz Defteri Topluluk paketindeki komut).
- **Kural:** TikTok sürümünden en az 24 saat sonra; haftalık insan emeği tavanı dışı; yeni şarkı
  yayınının ±24 saatine düşmez (TikTok şarkı kesiti günü kuralı Topluluk'a uygulanmaz).
- **Gerçek hikâye (CLAUDE.md, "art.jpg gerçek fotoğraf" maddesi):** "Kırık Zincir" için ilk aramada
  "zincir" kelimesi gitti ve bisiklet zinciri fotoğrafı geldi. O günden beri aramaya nesne
  kelimeleri girmiyor; mekân, hava ve ışık kelimeleri giriyor. Kapak fotoğrafında yazı olmaması da
  kural.

## 1. Görsel

İki kare yan yana tek bir görsel (kolaj) ya da Studio izin veriyorsa iki görsel:
1. `projects/Kırık Zincir/art.jpg` (metinsiz fotoğraf),
2. `projects/Kırık Zincir/cover_vertical.png` (başlıklı son kapak).

Bisiklet zinciri görselini BURADA kullanma: başkasının fotoğrafı, TikTok'ta 1 sn bulanık yeterliydi.
Ekran görüntüsünde dosya listesi, token, e-posta, bildirim görünmesin.

## 2. Gönderi metni

```
Kulis #1 — Bir kapak nasıl seçiliyor? 🎨

"Kırık Zincir"in kapağı ilk denemede bir bisiklet zinciriydi. Arama şarkının adındaki "zincir" kelimesini okumuş, gerçekten zincir bulmuştu.

O günden sonra kapağı sözlerdeki eşyadan değil, sözlerin geçtiği yerden arıyoruz: sokak, ışık, hava.

Bir kural daha: fotoğrafın içinde yazı olmuyor. Başlığı en son biz koyuyoruz.

Solda fotoğrafın kendisi, sağda son kapak. Sence şarkıya uydu mu? 👇
```

## 3. Anket (isteğe bağlı)

- Soru: **Sıradaki Kulis ne olsun?**
- Seçenek 1: `Başka bir kapağın hikâyesi`
- Seçenek 2: `Bir şarkının hangi versiyonu neden seçildi`

(TikTok ilk yorumundaki soruyla aynı; iki platformdaki yanıtlar Kulis #2'nin konusunu belirler.)

## 4. Kurallar

- Dış link, site ya da araç adı YOK; "yapay zeka" vurgusu ve AI hashtag'i YOK.
- **AI beyan satırı: GEREKMEZ** — gönderide AI müzik/ses yok; kapak fotoğrafı stok fotoğraf,
  üstündeki başlık bizim tipografimiz. Şarkının videosunu gönderiye bağlarsan sona ekle:
  `Söz: Famous Music Studio · Müzik ve vokal: AI destekli`
- Yorumlara ilk 24 saatte elle yanıt.

## 5. Yayından sonra

```
python elle_islem.py ekle --platform youtube --islem yayinladi --ayrinti "Topluluk: Kulis #1 — kapak seçimi (KNL-2026-09-20-kulis_topluluk)"
```
