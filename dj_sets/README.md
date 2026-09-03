# DJ Famous — haftalık özel üretim

Bu klasör, kanalın **ana kataloğundan (günlük 6 üretim, `projects/`) tamamen ayrı**,
haftada bir kez yayınlanan "DJ Famous" setleri içindir. Otomasyonu `auto_process.py`
DEĞİL, `dj_famous_process.py` işler — ikisi birbirine hiç karışmaz, ayrı kilit
dosyaları ve log dosyaları kullanırlar.

## DJ Famous nedir, ana katalogdan farkı ne

- **Ana katalog** (`projects/`): kurgusal temalar/karakterler, Suno ile üretilen
  şarkılar — kimse gerçek bir kişiyi temsil etmiyor.
- **DJ Famous**: **gerçek, tanınabilir bir kişiyi** (kendi rızasıyla, "DJ Famous"
  sahne adıyla) konu alıyor. Set içeriğinin **tamamı AI ile üretiliyor** — bu
  bilinçli bir tasarım kararı ve **hiçbir şekilde gizlenmiyor**:
  - YouTube: her yüklemede otomatik `containsSyntheticMedia=True` (ana katalogla
    aynı, kod tarafında zaten var).
  - TikTok: yüklerken script "AI-generated content" etiketini uygulamadan elle
    açman gerektiğini hatırlatıyor (TikTok'un Taslak/Gelen Kutusu akışında API'den
    ayarlanamıyor — bkz. `upload/tiktok_upload.py`).
  - Instagram: caption'ın sonuna otomatik olarak tek, göze az batan bir satır
    ekleniyor ("Bu içerik yapay zeka ile üretilmiştir.") — Meta'nın resmi API
    alanı (`is_ai_generated`) doğrulanamadığı için bu, en güvenilir yöntem
    (bkz. `upload/social_text.py::build_ai_disclosure_line`).

  Bu üçü de **sadece zorunlu olanı, mümkün olduğunca küçük/göze batmayan** şekilde
  yapıyor — videonun üzerine ekstra bir "AI" yazısı/filigranı EKLENMİYOR, platformların
  kendi resmi, standart mekanizmaları kullanılıyor.

## Görsel/kimlik — ÖNEMLİ

Gerçek bir kişinin fotoğrafından/görüntüsünden AI ile içerik üretmek **o kişinin
kendi açık onayını** gerektirir (aile içi bir karar olsa bile — bu onun kimliği).
Bu proje için onay zaten alındı; yeni bir kullanım/platform eklenecekse tekrar
teyit edilmeli.

## Klasör yapısı

Ana kataloktaki `projects/<isim>/` ile AYNI kurala göre çalışır — render.py,
generate_cover.py, validate_project.py hepsi buradaki klasörleri de tanır:

```
dj_sets/<hafta-etiketi>/
    audio.wav          # set kaydı (uzun olabilir, ör. ~1 saat — render süresi/sıkıştırılmış
                        # dosya boyutu buna göre artar, bu normal)
    art.jpg             # Arda'nın (AI ile üretilmiş/işlenmiş) fotoğrafı — kartın içeriği +
                        # arka plan blur kaynağı olarak kullanılır
    meta.json           # {"title": "Hafta 1 Seti", "theme": "dj", "static_label": "DJ Famous"}
```

`static_label` — ana katalogda videonun altındaki SABİT (kaymayan) satır her zaman
"Famous Music Studio" (`config.STATIC_LABEL_TEXT`). DJ Famous'ta bunun yerine "DJ Famous"
sabit dursun, `title` (ör. "Hafta 1 Seti") KAYSIN isteniyor — `meta.json`'a
`"static_label": "DJ Famous"` eklemek yeterli, `render.py` bunu otomatik okuyup
`ffmpeg_utils.render_video()`'ya geçiriyor. Belirtilmezse ana kataloktaki varsayılana
(`config.STATIC_LABEL_TEXT`) düşer.

`cover.jpg` elle sağlanmazsa `generate_cover.py` otomatik üretir — artık `art.jpg`
elle sağlanmışsa (karakter roster'ından değil) o görselin üstüne başlık metni
ekleyerek üretir (önceden ilgisiz bir procedural gradyan kullanıyordu, bu düzeltildi).

`theme: "dj"` — ana kataloğun 6 tarzından ayrı, sadece hashtag/etiket üretimi için
yeni bir `config.THEMES` girdisi (`config.py`).

## Kullanım

```bash
python dj_famous_process.py                 # dj_sets/ altında bekleyen HER seti işler
python dj_famous_process.py --privacy unlisted
python dj_famous_process.py --no-schedule    # YouTube golden-hour zamanlamasını kapatır
```

Haftalık çalıştırma için Görev Zamanlayıcı'da AYRI bir haftalık tetikleyici gerekir
(ana kataloğun saatlik tetikleyicisinden farklı) — `setup_task_scheduler.ps1` bunu
da kuruyor (varsayılan: her Cuma 18:00, `-DjFamousDayOfWeek`/`-DjFamousTime` ile
değiştirilebilir).

## Render süresi/boyutu notu

Ana katalog şarkıları 2-4 dakika, DJ Famous setleri çok daha uzun (referans: ~1 saat)
olabilir — render süresi ve çıktı dosya boyutu buna orantılı artar. `dj_famous_process.py`
bu yüzden ana kataloktan (2 saat) çok daha yüksek bir kilit-bayatlama süresi (8 saat)
kullanıyor, render sırasında ikinci bir çalıştırma "önceki çökmüş" sanıp üstüne
binmesin diye.
