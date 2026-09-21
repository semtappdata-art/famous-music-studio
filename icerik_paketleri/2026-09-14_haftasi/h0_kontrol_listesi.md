# H0 kontrol listesi — telefonda ~10 dk (13–14 Eylül 2026)

TikTok uygulaması ya da TikTok Studio. **Otomasyon yok, API yok:** hepsini sen okursun.
Takipçi sayısı API'den okunmaz (karar 5).

## 1. Analizler (4 dk)

1. Profil → ☰ → **TikTok Studio → Analizler → Takipçiler**.
2. Oku ve not al:
   - toplam takipçi
   - son 28 günde net takipçi (+/−)
   - **"Takipçilerin etkin olduğu saatler"**: her gün için en yoğun saati yaz (en az en yoğun 3 gün)
3. Ekranın görüntüsünü al (saklamak için).

**Telegram'dan Hermes'e ya da Claude'a gönderilecek tek satır** (boşlukları doldur):

```
TT-H0 13.09 | takipçi 0000 | 28g +00 | etkin: Pzt 00, Sal 00, Çar 00, Prş 00, Cum 00, Cmt 00, Paz 00 | 18+ evet | hesap temiz | LIVE düğmesi yok
```

- `etkin`: gün kısaltması + en yoğun saat (24 saat biçimi, yalnız saat). Bilinmeyen günü sil.
- `hesap`: `temiz` ya da `uyarı: <kısa>`.
- `LIVE düğmesi`: `+` → LIVE ekranında düğme görünüyor mu (`var` / `yok`).

Bu satır gelince Söz Defteri (Salı 20:30), Kulis (Cumartesi 13:00) ve LIVE yuvası (Pazar 21:00)
saatleri etkin saatlere göre güncellenir.

## 2. Yaş ve hesap durumu (2 dk)

- [ ] Ayarlar ve gizlilik → Hesap → **Kullanıcı bilgileri → Doğum tarihi**: 18+ (LIVE sunmak için
      güvenli varsayım 18).
- [ ] Ayarlar ve gizlilik → **Hesap durumu** (ya da Studio → Hesap durumu): ihlal/uyarı yok.
      Varsa ekran görüntüsü al, satırda `hesap uyarı: ...` yaz.
- [ ] Ayarlar → Gizlilik → Düet / Stitch / Yorum: **Herkes**.

## 3. Bio (2 dk)

**Mevcut bio 135 karakter; sınır 80.** Öneri (55 karakter):

```
Sözler bizden, müzik AI destekli · her hafta yeni şarkı
```

Alternatif (54 karakter, seriyi duyurur): `Sözler bizden, müzik AI destekli · Salı Söz Defteri ✍️`

- Araç adı YOK, hashtag YOK. İnsan emeğini öne alıyor ve beyanı dürüstçe veriyor.
- **Link alanı:** `famousmusicstudio.com/latest.html`. Profili düzenle → Web sitesi. Alan görünmüyorsa
  (takipçi eşiğine bağlı olabilir) boş bırak ve satıra `link alanı yok` ekle.

## 4. Profile sabitlenecek 3 gönderi (2 dk)

Kaynak: `tiktok_envanteri_2026-09-12.md` (görünürlükler 13 Eyl 01:15 sonrası). Sıralama: son
sabitlenen en solda görünür, **o yüzden 3 → 2 → 1 sırasıyla sabitle.**

| Sıra | Gönderi | İzlenme | Neden |
|---|---|---|---|
| 1 | **Beni Bırakma** abart videosu, 6 Eyl 18:00, 29 sn: https://www.tiktok.com/@famousmusicstudio/video/7682100132795518228 | **616** (hesabın en yükseği) | Kanıtlanmış çekiş ve 30 sn altı abart formatı. **Kusur:** başlıkta "Yeniden Doğacağım" yazıyor ve 7 gün sınırı dolduğu için düzeltilemiyor. Bu yüzden **geçici**: 16 Eyl'de Söz Defteri #1 ile değiştir |
| 2 | **Gece Sürüşü**, 5 Eyl 19:36, 30 sn: https://www.tiktok.com/@famousmusicstudio/video/7682090856102300949 | 288 | Başlığı içerikle **uyuşan** en çok izlenen herkese açık gönderi, golden-hour'da ve abart formatında. Profili ziyaret eden ne gördüğünü doğru okur |
| 3 | **Küllerimden Geç**, 9 Eyl 09:31: https://www.tiktok.com/@famousmusicstudio/video/7683419315344887061 | 151 | Kullanıcı kararıyla bu sesin **asıl kaydı** (yeni görsel). Başlık içerikle uyuşuyor; tür çeşitliliği sağlıyor |

**Sabitlenmeyecekler:** `#FamousMusicStudio` başlıklı 397/357/347'lik gönderiler. Şarkısı bilinmiyor
ve 5 Eyl 03:29–03:34 toplu yükleme kümesinden geliyorlar (inauthentic desen). Kırık Zincir (153) ve
Just Relax (142) de sabitlenmez, çünkü başlıkları yanlış ("Yeniden Doğacağım").

**16 Eylül (Çarşamba):** 1. sıradaki Beni Bırakma sabitini kaldır, **Söz Defteri #1**'i sabitle.

## 5. Deftere yaz (1 dk, bilgisayarda ya da Hermes'e)

```
python elle_islem.py ekle --platform tiktok --islem kontrol_etti --ayrinti "H0: takipçi ..., 28g ..., etkin ..., 18+ ..., hesap ..."
python elle_islem.py ekle --platform tiktok --islem duzenledi --ayrinti "bio 135 → 55 karakter: Sözler bizden, müzik AI destekli · her hafta yeni şarkı"
python elle_islem.py ekle --platform tiktok --islem profil_linki --ayrinti "bio link famousmusicstudio.com/latest.html"
python elle_islem.py ekle --platform tiktok --islem duzenledi --ayrinti "sabitlendi: 7682100132795518228, 7682090856102300949, 7683419315344887061"
```

İşlem adları `python elle_islem.py sozluk` çıktısından (`kontrol_etti`, `duzenledi`, `profil_linki`).
