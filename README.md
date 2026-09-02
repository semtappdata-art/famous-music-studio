# Suno Ses → Çoklu Platform Video Otomasyonu

Suno'da ürettiğin şarkılardan tüm platformlar için otomatik video üretir:

- **YouTube (uzun format)** (16:9) → `output/youtube_16x9.mp4`
- **YouTube Shorts / TikTok / Instagram Reels** (9:16) → `output/shorts_9x16.mp4` — bu dosya
  hem TikTok/Instagram'a hem de AYRI bir yükleme olarak YouTube'a (Short olarak) gidiyor;
  aynı şarkı için iki ayrı YouTube video'su (uzun format + Short) oluşuyor.

Videolar: ortada yuvarlak köşeli, Spotify "Now Playing" tarzı bir albüm kartı (kartın içeriği
şarkının kendi `art.jpg`'si) + kartın altında kayan künye yazısı + sabit marka satırı +
ilerleme çubuğu + kartın kendi görselinden türetilmiş, yavaşça kayan ve renk değiştiren
(pan + hue akışı) bir arka plan içerir. `art.jpg` yoksa (veya `meta.json`'da eksikse)
`generate_cover.py` otomatik olarak tema rengine uygun, deterministik bir görsel üretir —
elle görsel hazırlamak zorunlu değil, sadece ses dosyası yeterli. Tamamen otomatik, elle
video düzenleme gerekmez.

## Kurulum

```bash
pip install -r requirements.txt
```

(`requirements.txt`'teki sürümler kasıtlı sabitlenmedi — istersen kendi ortamında bir kere
`pip freeze > requirements.txt` çalıştırıp tam sürümleri kaydedebilirsin.)

## Adım Adım Kullanım

1. **Ses dosyasını ekle** — Suno'dan indirdiğin şarkıyı şu klasöre kaydet:
   ```
   projects/<sarki-adi>/audio.wav
   ```
   (`.mp3` veya `.m4a` da olur — `.wav` sıkıştırmasız olduğu için kalite açısından önerilir,
   script otomatik algılar.)

2. **Kapak görseli ekle** — Suno'nun ürettiği kapak veya kendi görselin:
   ```
   projects/<sarki-adi>/cover.jpg
   ```
   (`.jpeg` veya `.png` da olur)

3. **(Opsiyonel) Başlık ve tür ekle** — videoya başlık metni ve türe göre renk teması
   bindirmek istersen:
   ```
   projects/<sarki-adi>/meta.json
   ```
   içeriği:
   ```json
   {"title": "Şarkı Adı", "theme": "pop"}
   ```
   `theme` seçenekleri: `pop`, `rock`, `elektronik`, `akustik`, `hiphop`, `arabesk` — kartın
   arka planı zaten şarkının kendi `art.jpg`'sinden geliyor, `theme` bunun rengini/paletini
   değil, kayan yazının rengini ve hashtag'lerin tür etiketini belirler. Belirtilmezse
   varsayılan `hiphop` kullanılır.

4. **Render et:**
   ```bash
   python render.py --project projects/<sarki-adi>
   ```

5. **Çıktıları al** — `projects/<sarki-adi>/output/` klasöründe 2 hazır video seni bekliyor
   (`youtube_16x9.mp4`, `shorts_9x16.mp4`), ilgili platforma yükleyebilirsin.

### Birden fazla şarkı

Tüm proje klasörlerini tek seferde render etmek için:
```bash
python render.py --all
```

## Ayarları değiştirmek

Çözünürlükler, kart/marquee/ilerleme çubuğu boyutları, backdrop pan/hue hızları, font gibi
tüm görünüm ayarları [config.py](config.py) dosyasında — kodun geri kalanına dokunmadan
oradan değiştirebilirsin.

## Tam Otomasyon: `auto_process.py` (asıl production giriş noktası)

`audio.wav` bir proje klasörüne konduktan sonraki HER ŞEYİ (kapak/kart üretimi + render +
YouTube uzun format + YouTube Shorts + TikTok + Instagram yükleme) otomatikleştiren asıl
script bu — Windows Görev Zamanlayıcı ile periyodik (günde 2 farklı tetikleyici, örn. 13:00
ve 19:00) çalıştırılmak üzere tasarlandı. Her çalıştırmada en fazla 1 proje işler (en eski
bekleyen), zaten tamamlanmış adımları atlar.

```bash
python auto_process.py
python auto_process.py --privacy unlisted
```

Kimlik doğrulama (her platform için bir kerelik, ilgili script'in kendisiyle):

1. **YouTube** — Google Cloud Console'da bir proje aç, YouTube Data API v3'ü etkinleştir,
   OAuth consent screen kur, bir Desktop app OAuth Client ID oluştur ve
   `upload/client_secrets.json` olarak kaydet, sonra:
   ```bash
   python upload/youtube_auth.py
   ```
2. **TikTok** — TikTok Developer Portal'da bir app oluştur, `upload/tiktok_client_secrets.json`
   doldur, sonra `python upload/tiktok_auth.py --print-url` ve `--code KOD` ile iki adımlı
   girişi tamamla. Uygulama henüz TikTok'un içerik yayınlama (video.publish) audit/review
   sürecinden geçmediyse, video sadece TikTok'un gelen kutusuna TASLAK olarak düşer —
   yayınlamayı TikTok uygulamasından elle tamamlaman gerekir.
3. **Instagram** — Meta for Developers'ta Instagram API kurulumu yapıp
   `upload/instagram_client_secrets.json` doldur, `python upload/instagram_auth.py
   --print-url` ve `--code KOD` ile tamamla. Instagram Graph API dosya upload'ı değil,
   herkese açık bir video URL'i beklediği için ayrıca `upload/netlify_client_secrets.json`
   (geçici video barındırma için) doldurulmalı — detay: `upload/instagram_upload.py`
   dosyasının başındaki not.

Hiçbir platform için token yoksa `auto_process.py` o platformu sessizce atlar (hata vermez) —
istediğin platformlar için sırayla kimlik doğrulaması ekleyebilirsin.

Tek başına, tek bir platforma yükleme (render zaten yapılmışsa):
```bash
python upload/youtube_upload.py --project "projects/sarki-adi"
python upload/youtube_upload.py --project "projects/sarki-adi" --shorts
python upload/tiktok_upload.py --project "projects/sarki-adi"
python upload/instagram_upload.py --project "projects/sarki-adi"
```

### Tarz/tema playlist'leri

`auto_process.py`, her YouTube (uzun format) yüklemesinden sonra şarkıyı otomatik olarak
kendi temasının (`meta.json`'daki `theme`) YouTube playlist'ine ekler — kanal içinde
"Rap/Hip-Hop", "Pop", "Arabesk" gibi ayrı tarz alanları oluşur, playlist yoksa otomatik
oluşturulur. Daha önce yüklenmiş kataloğu bir kerede gruplamak için:
```bash
python upload/youtube_playlists.py --sync-all
```
Hangi türlere öncelik verileceği için (kanalın kendi verisi yerine Türkiye geneli dinleme
trendlerine göre) bkz. [turkiye_muzik_trend_arastirmasi.md](turkiye_muzik_trend_arastirmasi.md).

### Sadece render + YouTube (eski/basit akış)

`auto_process.py`'nin tüm platformları kapsayan sürümüne ihtiyacın yoksa, sadece render +
YouTube uzun format için `run_pipeline.py` da kullanılabilir:
```bash
python run_pipeline.py --project "projects/sarki-adi"
```
Varsayılan görünürlük `private`. `--privacy public`/`--privacy unlisted` ile değiştirilebilir,
`--skip-upload` ile sadece render (upload olmadan) yapılabilir.

## Büyüme / Paylaşım Stratejisi

Otomasyon yayınlama hızını çözüyor, ama izlenme/takipçi sayısını tek başına artırmıyor —
keşfedilebilirlik için ayrıca şunlara dikkat et. Detaylı, elle yapılan adımlar için
[buyume_kontrol_listesi.md](buyume_kontrol_listesi.md); hashtag/saat araştırması için
[trend_hashtag_notlari.md](trend_hashtag_notlari.md); vokal/tarz çeşitliliği takibi için
[ses_ve_tarz_takibi.md](ses_ve_tarz_takibi.md).

- **Paylaşım sıklığı/hacmi:** Hazır şarkıları teker teker, seyrek yerine hızlıca sırayla
  yayınlamak algoritmaya "aktif hesap" sinyali verir.
- **Açılış kancası + hashtag + etkileşim sorusu:** `upload/social_text.py`'deki
  `build_caption()` her caption'a otomatik olarak `config.HOOK_LINES`'tan bir açılış
  cümlesi, `config.BRAND_HASHTAGS`/`DISCOVERY_HASHTAGS`/tema hashtag'lerini, ve
  `config.ENGAGEMENT_QUESTIONS`'tan bir etkileşim sorusu ekliyor — hepsi şarkı başlığından
  türetilen deterministik bir seçimle (aynı şarkı her zaman aynı satırları alır, farklı
  şarkılar farklı kombinasyon alır).
- **YouTube linki caption'da DEĞİL:** Instagram/TikTok caption'larında dış link
  bulundurmamak bilinçli bir karar — off-platform link, Explore/For You gibi algoritmik
  dağıtımı olumsuz etkileyebiliyor. YouTube linki bunun yerine paylaşım SONRASI bir yorum
  olarak ekleniyor (`build_youtube_comment()`).
- **Yorumlara hızlı yanıt:** İlk yorumlara hızlı dönüş etkileşim sinyalini güçlendirir —
  şu an otomatikleştirilmiş değil, elle takip gerekiyor.
