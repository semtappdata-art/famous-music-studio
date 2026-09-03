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

   İsteğe bağlı `"character": "Kerem Ateşi"` alanı eklersen (bkz.
   [karakter_roster.md](karakter_roster.md)) ve `characters/` klasöründe o karaktere ait
   bir portre varsa, `cover.jpg`/`art.jpg` eksikse otomatik olarak o portreden üretilir —
   yoksa (portre henüz hazırlanmadıysa) sessizce tema rengine göre procedural üretime döner.

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
YouTube uzun format + YouTube Shorts + TikTok + Instagram yükleme + tema playlist'i)
otomatikleştiren asıl script bu — Windows Görev Zamanlayıcı ile periyodik çalıştırılmak
üzere tasarlandı.

**Otomatik kademeleme (varsayılan):** `--count` verilmezse, kaç proje bekliyorsa (audio
hazır ama henüz 3 platforma da yüklenmemiş) script 24 saati o sayıya eşit aralıklara
böler (ör. 9 proje bekliyorsa ~2.7 saatte bir 1 tane, 2 proje bekliyorsa 12 saatte bir
1 tane) ve son yüklemeden bu kadar süre geçtiyse SADECE O ZAMAN bir proje işler —
geçmediyse o koşuda hiçbir şey yapmadan çıkar. Amaç: aynı anda birden fazla şarkı
paylaşmanın aynı takipçi kitlesinin aynı taramasında birbiriyle yarışmasını önlemek,
kaç dosya biriktiği önemli olmadan gün içine dengeli yaymak.

**Bunun işlemesi için Görev Zamanlayıcı'yı SIK çalıştır** — tek bir tetikleyici, ör.
saatte bir yeterli (birden fazla tetikleyici kurmana gerek yok, script kendi kendine
"sırası geldi mi" diye karar veriyor).

**Kurulum elle Görev Zamanlayıcı arayüzünde tıklamayı gerektirmez** —
[setup_task_scheduler.ps1](setup_task_scheduler.ps1) bunu tek komutla yapar: eski
(ör. günde 2 kez 13:00/19:00 çalışan) `auto_process.py` görevlerini otomatik bulup
siler, yerine saatte bir çalışan TEK bir görev kurar.

```powershell
powershell -ExecutionPolicy Bypass -File setup_task_scheduler.ps1
```

Tekrar çalıştırmak güvenlidir (idempotent) — script değiştiğinde ya da tekrar
doğrulamak istediğinde aynen yeniden çalıştırabilirsin.

```bash
python auto_process.py
python auto_process.py --privacy unlisted
python auto_process.py --count 2         # otomatik kademeyi devre dışı bırakıp tam 2'sini hemen işler
python auto_process.py --no-schedule     # YouTube'u golden-hour beklemeden hemen public yükler
```

**YouTube golden-hour zamanlaması (varsayılan):** otomatik kademeleme, render/upload anını
günün her saatine denk getirebildiği için (eskiden sabit 13:00/19:00 iken artık saatte bir
kontrol var), `privacy=public` olan YouTube yüklemeleri artık `private` + YouTube'un
`publishAt` alanıyla yükleniyor — video hemen değil, bir sonraki golden-hour penceresinde
(12:00-14:00 veya 18:00-22:00, TR yerel saat — bkz. `config.GOLDEN_HOURS`,
[trend_hashtag_notlari.md](trend_hashtag_notlari.md)) otomatik public oluyor; bunu YouTube
kendisi yapıyor, script'in o anda tekrar çalışması gerekmiyor. Zaten bir golden-hour
penceresinin içindeysek zamanlamasız, hemen public yüklenir. `--no-schedule` ile bu
davranış tamamen kapatılabilir. Instagram/TikTok için aynı şey API üzerinden mümkün değil
(bkz. aşağıdaki "Zamanlama neden sadece YouTube'da var" notu) — bu iki platform, script
o an çalıştığında hemen yayınlanır/taslağa düşer.

**Zamanlama neden sadece YouTube'da var:** YouTube Data API `videos.insert`, resmi olarak
`status.privacyStatus="private"` + gelecekteki bir `status.publishAt` ile yüklenip
otomatik public'e geçen zamanlanmış yayını destekliyor. Instagram Graph API'de üçüncü
parti uygulamalar için böyle bir "ileri tarihli yayın" parametresi yok (yalnızca Facebook
Sayfa gönderilerinde var) — tek yol, `media_publish` çağrısını hedeflenen ana kadar kendi
altyapınızda bekletmek, ki bu zaten `auto_process.py`'nin kendi kademeleme mantığının
yaptığı şey. TikTok'un Content Posting API'si hiç zamanlama desteklemiyor (native
zamanlayıcı sadece TikTok'un kendi uygulamasında, onaylı İşletme hesapları için var,
API'den erişilemiyor) — zaten bu projede kullanılan Inbox/Draft akışı da yayınlamayı
elle yapılması gereken bir adım olarak bırakıyor.

**YouTube günlük quota uyarısı:** her şarkı YouTube'a 2 ayrı video olarak gidiyor (uzun
format + Shorts), her `video.insert` çağrısı ~1600 unit'lik varsayılan günlük kotanın
(10.000 unit) bir kısmını tüketiyor (thumbnail + playlist çağrıları dahil biraz daha
fazla) — yani günde ~6 projeden fazlası teorik olarak kotayı aşabilir. Otomatik
kademeleme bekleyen proje sayısı arttıkça aralığı kendiliğinden kısaltır (ör. çok
sayıda proje birikirse günde 6'dan fazlasını da işlemeye çalışır) — bekleyen proje
sayın sürekli yüksekse veya `--count` ile elle yüksek bir sayı verirsen (ör. bir
kerelik toplu çalıştırma) 10.000 unit'i aşmadığından kendin emin ol — aşarsan o günün
geri kalanında YouTube yüklemeleri başarısız olur (TikTok/Instagram etkilenmez, kendi
kotalarına tabidir).

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
