---
name: tiktok-yayin-onayi
description: "TikTok yayın onayını Telegram yanıtından işaretler."
version: 1.0.0
author: Famous Music Studio
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [tiktok, telegram, famous-music-studio]
triggers:
  - yayınladım
  - yayinladim
  - tiktok'ta yayınladım
  - paylaştım
---

# TikTok Yayın Onayı (Famous Music Studio)

Boru hattı TikTok'a yalnız TASLAK yüklüyor; kullanıcı taslağı TikTok uygulamasından
elle yayınlıyor. Golden-hour'da bu sohbete bir hatırlatma düşer:
"Yayınladıysan bu sohbete yaz: yayınladım <şarkı adı>" (ya da kısa kod, ör. T3F2A).
Kullanıcı öyle yanıt verdiğinde bu beceri TEK bir şey yapar: yayını depoya işaretleyen
betiği çalıştırıp çıktısını kullanıcıya iletir.

## When to Use

- Kullanıcı "yayınladım <şarkı adı>", "yayınladım T3F2A", "<şarkı adı> yayınladım" gibi,
  bir TikTok taslağını yayınladığını söyleyen kısa bir mesaj yazdı.
- Mesajda şarkı adı ya da kod YOKSA komut çalıştırma; kullanıcıya hangi şarkıyı
  yayınladığını sor. Ad belirsizse (birden çok şarkıya uyabilir) de önce sor.

## Procedure

1. Mesajdan şarkı adını ya da kodu çıkar ("yayınladım" kelimesini at).
2. Addan harf (Türkçe harfler dahil), rakam, boşluk, nokta ve tire DIŞINDAKİ bütün
   karakterleri sil (tırnak, `$`, ters tırnak, `;`, `|`, `&`, `<`, `>` vb.). Ad boş
   kalırsa komut çalıştırma, kullanıcıya sor.
3. Yalnız şu komutu, adı tek tırnak içine koyarak çalıştır (depo yolu mutlak, çalışma
   dizini önemli değil):

```bash
python C:/Users/ACER/Desktop/ilk-projem/upload/tiktok_yayin_onayi.py '<ad>'
```

4. Betiğin çıktısını kullanıcıya olduğu gibi, kısaca ilet. Çıktının ilk kelimesi sonucu
   söyler:
   - `TAMAM` — işaretlendi.
   - `ZATEN İŞARETLİ` — daha önce işaretlenmiş, değişiklik yok.
   - `BELİRSİZ` ya da `BULUNAMADI` — işaretleme YAPILMADI. Çıktıdaki adayları kullanıcıya
     göster ve hangisi olduğunu sor; kullanıcı netleştirince komutu o ad ya da kodla
     BİR kez daha çalıştır. Kendin tahmin edip seçme.
   - `İŞARETLENMEDİ` — sebep çıktıda (ör. ikiz kayıt, telif, bekletme). Sebebi ilet;
     başka bir yolla işaretlemeye ÇALIŞMA.

## Kesin sınırlar

- Başka komut YOK: yukarıdaki tek komut dışında hiçbir terminal komutu, betik ya da
  argüman kullanma. Betiğe bayrak ekleme.
- Dosya düzenleme YOK: `state.json`, `meta.json` ya da depodaki başka hiçbir dosyayı
  okuma/yazma araçlarıyla değiştirme; işareti yalnız betik yazar.
- git YOK: hiçbir git işlemi yapma.
- Telegram'dan güncelleme okuyan kod (getUpdates, webhook) kurma ya da çalıştırma:
  bot bu gateway ile paylaşılıyor, ikinci bir okuyucu mesajları çalar.
- Betik ağa çıkmaz, TikTok'a istek atmaz; "gerçekten yayında mı" diye TikTok'u kontrol
  etmeye çalışma. İşaret kullanıcının beyanıdır.
- Çıktı `BELİRSİZ`/`BULUNAMADI`/`İŞARETLENMEDİ` ise kullanıcı ısrar etse bile başka bir
  yoldan işaretleme yapma; ayrıntı bu deponun `CLAUDE.md`'sinde (TikTok maddesi).
