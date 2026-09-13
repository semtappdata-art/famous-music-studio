---
name: elle-islem-kaydi
description: "Elle yapılan işleri elle işlemler defterine yazar."
version: 1.0.0
author: Famous Music Studio
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [famous-music-studio, defter, telegram]
triggers:
  - elle yaptım
  - elle yaptim
  - Studio'dan değiştirdim
  - Studio'dan yaptım
  - telefondan yaptım
  - arşivledim
  - sildim
  - liste dışı yaptım
  - gizledim
  - kapağı değiştirdim
  - bekletmeye aldım
---

# Elle İşlem Kaydı (Famous Music Studio)

Kullanıcı otomasyonun DIŞINDA bir iş yaptığını söylediğinde (Instagram'da arşivleme,
YouTube Studio'dan gizlilik/kapak/oynatma listesi değişikliği, bir şarkıyı liste dışı
yapmak, telif itirazı, projeyi bekletmeye almak, Suno'da üretim/seçim, profil linki...)
bu beceri o cümleyi alanlara çevirir, kullanıcıya kısa bir onay özeti gösterir ve onay
gelirse TEK bir komutla deftere yazar. Raporlar, pano ve sesli asistan bu işleri bu
defterden görür.

## When to Use

- "Studio'dan Son Kez'i liste dışı yaptım", "Instagram'da eski Reels'i arşivledim",
  "Bu Gece Kazandık'ı bekletmeye aldım", "Suno'da Neon Kalp'i ürettim" gibi mesajlar.
- TikTok taslağını yayınladığını söyleyen "yayınladım <şarkı>" mesajı bu becerinin İŞİ
  DEĞİL: onu `tiktok-yayin-onayi` becerisi işaretler (o yol deftere zaten yazar).
  İkisini birden çalıştırma.

## Procedure

1. Mesajdan alanları çıkar:
   - platform (yalnız biri): youtube, youtube_shorts, tiktok, instagram, facebook,
     telegram, bluesky, suno, site, diger
   - islem (yalnız biri): yayinladi, gizlilik_degistirdi, liste_disi_yapti, arsivledi,
     sildi, kapak_degistirdi, oynatma_listesi, telif_itirazi, bekletmeye_aldi,
     bekletmeden_cikardi, uretti, secti, profil_linki, yorum_yaniti, duzenledi,
     kontrol_etti, diger
   - proje: şarkı/set/derleme KLASÖR adı (ör. Son Kez, Just Relax). Projeyle ilgisizse
     (ör. profil linki) boş bırak.
   - ayrinti: ne yapıldığını anlatan kısa Türkçe cümle.
   - zaman: kullanıcı söylediyse YYYY-MM-DDTHH:MM (Türkiye saati). "Dün akşam" gibi
     kesin değilse en yakın tahmini yaz ve `--yaklasik` ekle. Hiç söylemediyse zamanı
     verme (şimdi kaydedilir).
   - gizlilik (yalnız YouTube gizlilik değişikliğinde): public, unlisted ya da private.
2. Değerlerden tek tırnak, çift tırnak, kesme işareti, `$`, ters tırnak, `;`, `|`, `&`,
   `<`, `>` karakterlerini sil (kesme işaretini boşlukla değiştir: "Studio dan").
3. Kullanıcıya KISA bir onay özeti göster ve onay bekle, ör.:
   "Kaydedeyim mi? YouTube · Son Kez · liste dışı yaptı · 13.09 14:30 — Studio dan liste
   dışı yapıldı". Kullanıcı "evet/tamam" demeden komut çalıştırma. Platform, işlem ya da
   proje belirsizse önce sor; kendin tahmin edip seçme.
4. Onay gelince yalnız şu komutu çalıştır (yol mutlak; köşeli parantezli kısımlar
   yalnız gerekiyorsa eklenir, köşeli parantezleri yazma):

```bash
python C:/Users/ACER/Desktop/ilk-projem/elle_islem.py ekle --kaynak telegram --platform <platform> --islem <islem> --proje '<proje>' --ayrinti '<ayrinti>' [--zaman '<YYYY-MM-DDTHH:MM>'] [--yaklasik] [--gizlilik <deger>]
```

   Geçerli anahtarlardan emin değilsen önce bunu çalıştırıp listeye bak:

```bash
python C:/Users/ACER/Desktop/ilk-projem/elle_islem.py sozluk
```

5. Çıktıyı kullanıcıya kısaca ilet. İlk kelime sonucu söyler:
   - `EKLENDİ` — kaydedildi (ek not varsa hangi state alanının yazıldığını söyler).
   - `ZATEN KAYITLI` — aynı iş 10 dakika içinde zaten kayıtlı; değişiklik yok.
   - `HATA` — alanlardan biri geçersiz (ör. proje klasörü yok). Sebebi ilet, kullanıcıya
     doğru değeri sor, sonra komutu BİR kez daha çalıştır.
   - `HATA: REDDEDİLDİ` — TikTok yayını plana göre engelli (ikiz, telif, bekletme).
     Sebebi ilet; başka bir işlem anahtarıyla kaydetmeye ÇALIŞMA.

## Kesin sınırlar

- Başka komut YOK: yukarıdaki iki komut dışında hiçbir terminal komutu, betik ya da
  bayrak kullanma. `backfill` çalıştırma.
- Dosya düzenleme YOK: `elle_islemler.jsonl`, `state.json`, `meta.json` ya da depodaki
  başka bir dosyayı okuma/yazma araçlarıyla değiştirme; kaydı yalnız komut yazar.
- git YOK.
- Telegram'dan güncelleme okuyan kod (getUpdates, webhook) kurma ya da çalıştırma:
  bot bu gateway ile paylaşılıyor.
- Kayıt kullanıcının BEYANIDIR; YouTube/Instagram/TikTok'a bakıp "gerçekten yapılmış mı"
  diye doğrulamaya çalışma. Ayrıntı: deponun `CLAUDE.md` dosyası, "Elle işlemler defteri".
