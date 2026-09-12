# Suno Ses → Çoklu Platform Video Otomasyonu

Suno'da ürettiğin şarkılardan tüm platformlar için otomatik video üretir:

- **YouTube (uzun format)** (16:9) → `output/youtube_16x9.mp4`
- **YouTube Shorts / TikTok / Instagram Reels** (9:16) → `output/shorts_9x16.mp4` — bu dosya
  hem TikTok/Instagram'a hem de AYRI bir yükleme olarak YouTube'a (Short olarak) gidiyor;
  aynı şarkı için iki ayrı YouTube video'su (uzun format + Short) oluşuyor.
- **Facebook Reels / Telegram / Bluesky** — opsiyonel (opt-in) ek platformlar, aynı
  render çıktılarını kullanıyor; kurulum için aşağıdaki "Kimlik doğrulama" bölümüne bak.
  Telegram'a ana katalogda 16:9 uzun video gidiyor, diğer ikisine dikey sürüm.

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

Tüm proje klasörlerini tek seferde render etmek için — ÜÇ içerik kökünün de altındakiler
(`projects/`, `dj_sets/`, `derlemeler/`; tek kanonik liste `uyumluluk.KOK_ADLARI`, `.` ya da
`_` ile başlayan klasörler atlanır):
```bash
python render.py --all
```

## Ayarları değiştirmek

Çözünürlükler, kart/marquee/ilerleme çubuğu boyutları, backdrop pan/hue hızları, font gibi
tüm görünüm ayarları [config.py](config.py) dosyasında — kodun geri kalanına dokunmadan
oradan değiştirebilirsin.

**Kapak başlık tipografisi (2026-09-11'de değişti, `generate_cover.py` içinde):** başlık
puntosu kapak kısa kenarının %7,5'inden **%14'üne** çıkarıldı. Sebep: kapak YouTube
feed'inde ~246 piksel genişlikte görünüyor; eski oran 1600x900'de 67 px'lik yazıya denk
geliyor, feed'de ~10 piksele düşüyor ve okunmuyordu (9/9 kapakta ölçüldü). Başlığa ayrıca
koyu bir gölge eklendi (`shadowcolor=black@0.75`, 3 px) — stok fotoğrafların bir kısmı
açık tonlu (deniz, gökyüzü, çiçek) ve beyaz yazı orada kayboluyordu.

Uzun başlıklar için sığdırma artık TAHMİNLE değil, ffmpeg'e tek bir kısa çağrı yapılıp
metnin GERÇEK piksel genişliği ölçülerek yapılıyor (karakter başına ortalama genişlik
harfe göre 0,43-0,50 em arasında değişiyor, Türkçe `ı/ğ/ş` dahil — %15'lik bir tahmin
hatası ya taşma ya gereksiz küçültme demek). Karar sırası: (1) tek satır, tavan puntoda;
(2) sığmıyorsa ve en az iki kelime varsa **iki satıra bölünür ve punto tavanı korunur**
(bölme noktası kelime sınırında, her aday gerçekten ölçülüp en dengelisi seçiliyor);
(3) tek kelimelik başlık bölünemez, sadece o durumda punto küçültülür; (4) iki satır da
sığmazsa punto ölçülen genişliğe göre küçültülür. En fazla 2 satır — üç satır kapağı blok
metne çevirip fotoğrafın üstünü kapatıyor. Ölçüm başarısız olursa (ffmpeg yok/zaman
aşımı) kaba tahmine düşülür; kapak üretimi hiçbir koşulda durmaz.

## Tam Otomasyon: `auto_process.py` (asıl production giriş noktası)

`audio.wav` bir proje klasörüne konduktan sonraki HER ŞEYİ (kapak/kart üretimi + render +
YouTube uzun format + YouTube Shorts + TikTok + Instagram + — açıksa — Facebook/Telegram/
Bluesky yükleme + tema playlist'i) otomatikleştiren asıl script bu — Windows Görev
Zamanlayıcı ile periyodik çalıştırılmak üzere tasarlandı.

Ayrıca her koşunun SONUNDA, işlenecek proje olmasa bile, birkaç arka plan işi çalışıyor:
istatistik/yorum tazeleme, Facebook ve Telegram/Bluesky geri doldurma, DJ setleri /
derlemeler için Content ID karantina kontrolü, sağlık kontrolleri ve izlenme süresi
raporu (bkz. aşağıdaki "Arka planda çalışan kapılar ve kontroller").

**Otomatik kademeleme (varsayılan):** `--count` verilmezse, kaç proje bekliyorsa (audio
hazır ama dört ana yükleme anahtarı — YouTube uzun format, YouTube Shorts, TikTok,
Instagram — henüz tamamlanmamış) script 24 saati o sayıya eşit aralıklara
böler (ör. 9 proje bekliyorsa ~2.7 saatte bir 1 tane, 2 proje bekliyorsa 12 saatte bir
1 tane) ve son yüklemeden bu kadar süre geçtiyse SADECE O ZAMAN bir proje işler —
geçmediyse o koşuda hiçbir şey yapmadan çıkar. Amaç: aynı anda birden fazla şarkı
paylaşmanın aynı takipçi kitlesinin aynı taramasında birbiriyle yarışmasını önlemek,
kaç dosya biriktiği önemli olmadan gün içine dengeli yaymak.

**YENİ yayınlar için 52 saatlik bir TABAN aralık var
(`auto_process.MIN_YAYIN_ARALIGI_SN`):** yukarıdaki 24 saatlik bölüşüm tek başına, bir
günde `projects/` altına 7 dosya düşerse yedisini de AYNI GÜN yayınlıyordu (24/7 ≈ 3,4
saat ara). Haftalık sayı doğru çıkıyor ama günlük desen YouTube'un "inauthentic content"
(toplu üretilmiş, tekrarlayıcı içerik) tarifinin ta kendisi — kanalın en büyük tekil
riski bu. 52 saat, haftada 3 şarkı hedefinden geliyor (7×24/3 = 56 saat, eksi golden-hour
kaymasının haftalık sürüklenme payı). Yani gerçek aralık
`max(52 saat, 24 saat / bekleyen proje sayısı)`.

**Geri doldurma projeleri bu tabandan MUAF:** state.json'ında zaten bir
`youtube_video_id` olan bir proje (ör. YouTube'a çıkmış ama Instagram'ı yarım kalmış bir
şarkı) yeni bir yayın değil, yarım kalmış bir işin tamamlanmasıdır — kanalın yükleme
desenini etkilemez, 52 saatlik tabana takılmaz. Log'a hangi kuralın beklettiği ("yeni
yayın tabanı" / "günlük pencere bölüşümü") yazılıyor.

**Bunun işlemesi için Görev Zamanlayıcı'yı SIK çalıştır** — tek bir tetikleyici, ör.
saatte bir yeterli (birden fazla tetikleyici kurmana gerek yok, script kendi kendine
"sırası geldi mi" diye karar veriyor).

**Kurulum elle Görev Zamanlayıcı arayüzünde tıklamayı gerektirmez** —
[setup_task_scheduler.ps1](setup_task_scheduler.ps1) bunu tek komutla yapar. Kurduğu
görev sayısı ÜÇ (kayıtlı olanların tamamı bunlar):

| Görev | Script | Sıklık |
|---|---|---|
| `FamousMusicStudio-AutoProcess` | `auto_process.py` | saatte bir |
| `FamousMusicStudio-DjFamousProcess` | `dj_famous_process.py` | haftada bir (varsayılan Cuma 18:00) |
| `FamousMusicStudio-Watcher` | `watch_projects.py` | dakikada bir |

Eski (ör. günde 2 kez 13:00/19:00 çalışan) `auto_process.py` görevlerini otomatik bulup
siler. **`derleme.py` / `dj_famous_process.py --base derlemeler` zamanlayıcıda BİLEREK
YOK** — gerekçe aşağıdaki "Derlemeler" bölümünde.

```powershell
powershell -ExecutionPolicy Bypass -File setup_task_scheduler.ps1
```

Tekrar çalıştırmak güvenlidir (idempotent) — script değiştiğinde ya da tekrar
doğrulamak istediğinde aynen yeniden çalıştırabilirsin.

**Klasör izleyici (`watch_projects.py`, opsiyonel hızlandırıcı):** saatlik tetikleyici
zaten yeterli ama tepki süresini (yeni Suno indirmesi -> fark edilme) saatlerden
dakikalara indirmek için `setup_task_scheduler.ps1` aynı zamanda 1 dakikada bir
tekrar eden bir görev de kurar — `projects/<isim>/` altına herhangi bir adla
(`.wav`/`.mp3`/`.m4a`) düşürülen yeni bir ses dosyasını yakalayıp `audio.wav`'a
çevirir ve `auto_process.py`'yi hemen tetikler. Kademeleme kararına karışmaz —
`auto_process.py` "sırası geldi mi" kontrolünü hâlâ kendisi yapar.

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

**Zamanlama neden sadece YouTube ve Facebook'ta var:** YouTube Data API `videos.insert`,
resmi olarak `status.privacyStatus="private"` + gelecekteki bir `status.publishAt` ile
yüklenip otomatik public'e geçen zamanlanmış yayını destekliyor. **Facebook'ta da VAR**
(Sayfa gönderilerinde): Reels'te `video_state=SCHEDULED` + `scheduled_publish_time`,
uzun formatta `published=false` + `scheduled_publish_time` — bu yüzden Facebook'ta da
kendi kuyruğumuza gerek yok, `--no-schedule` orada da geçerli. Instagram Graph API'de üçüncü
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
fazla) — yani günde ~6 projeden fazlası teorik olarak kotayı aşabilir. **Otomatik
kademeleme artık kotayı kendiliğinden zorlayamaz**: 52 saatlik yeni-yayın tabanı
yüzünden bekleyen proje sayısı ne kadar artarsa artsın günde en fazla bir YENİ yayın
çıkar (yukarıya bkz.). Kota riski geriye iki durumda kalıyor: `--count` ile elle yüksek
bir sayı verirsen (ör. bir kerelik toplu çalıştırma) ya da çok sayıda geri doldurma
projesi (`youtube_video_id`'si zaten olanlar) aynı gün sıraya girerse — o zaman 10.000
unit'i aşmadığından kendin emin ol; aşarsan o günün geri kalanında YouTube yüklemeleri
başarısız olur (TikTok/Instagram etkilenmez, kendi kotalarına tabidir).

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

   **Kapak (cover) görseli TikTok'ta API'den ayarlanamıyor** (WebSearch ile doğrulandı,
   Eylül 2026) — `video_cover_image_url` parametresi sadece audit'ten geçmiş uygulamaların
   kullanabildiği Direct Post akışında var, bu projenin kullandığı Taslak/Gelen Kutusu
   akışında yok. Elle düzeltme mümkün: TikTok uygulamasında taslağı yayınlarken (ya da
   yayınlandıktan sonra 7 gün içinde profil → video → ⋯ → "Gönderiyi düzenle" → "Kapağı
   düzenle") "Yükle" ile galeriden özel bir fotoğraf yükleyebiliyorsun — video karesi
   seçmek zorunda değilsin. `tiktok_upload.py` her yüklemede hangi `cover.jpg`'yi
   kullanman gerektiğini konsola basıp `state.json`'a kaydediyor (`tiktok_cover_hint`);
   `python upload/tiktok_upload.py --pending-covers` ile TikTok'a zaten yüklü TÜM
   projeler için bu listeyi tek seferde alabilirsin (eski, bu özellikten önce yüklenmiş
   videolar dahil).
3. **Instagram** — Meta for Developers'ta Instagram API kurulumu yapıp
   `upload/instagram_client_secrets.json` doldur, `python upload/instagram_auth.py
   --print-url` ve `--code KOD` ile tamamla. Instagram Graph API dosya upload'ı değil,
   herkese açık bir video URL'i beklediği için ayrıca `upload/netlify_client_secrets.json`
   (geçici video barındırma için) doldurulmalı — detay: `upload/instagram_upload.py`
   dosyasının başındaki not.

   **Instagram'ın gerçek yayın anı da golden-hour'a hizalı** (YouTube'daki gibi):
   Graph API'de native zamanlanmış yayın YOK, bu yüzden `instagram_upload.py`
   konteyneri hemen oluşturuyor ama `media_publish` çağrısını (gerçek canlıya
   çıkış) golden-hour penceresine kadar erteliyor — `auto_process.py`'nin bir
   sonraki çalıştırmasında (saatlik) otomatik tamamlanıyor, elle bir şey
   yapmana gerek yok.

   **Tek istisna — EXPIRED konteyner:** Instagram konteyneri 24 saatte doluyor.
   Otomasyon onu KENDİ BAŞINA yeniden oluşturmaz (bilinçli: yeniden paylaşım
   hacim etkisi olan bir karar) — bayat kaydı temizleyip konsola
   `python upload/instagram_upload.py --project "..."` komutunu basar, gerisi
   senin kararın.
4. **Facebook (Reels)** — Meta for Developers'ta uygulamayı açıp Facebook İşletme
   Girişi (Business Login) yapılandırması oluştur (`pages_show_list` +
   `pages_manage_posts` + `pages_read_engagement` izinleriyle), sonra
   `upload/facebook_client_secrets.json` dosyasını doldur:
   ```json
   {"app_id": "...", "app_secret": "...", "config_id": "...", "page_id": "..."}
   ```
   (`config_id` = oluşturduğun yapılandırmanın kimliği, `page_id` = yönetilecek
   Sayfanın ID'si.) Sonra Instagram/TikTok'takiyle aynı iki adımlı akış:
   ```bash
   python upload/facebook_auth.py --print-url
   python upload/facebook_auth.py --code KOPYALANAN_KOD
   ```
   Sonuç `upload/facebook_token.json`'a yazılır. Bu Sayfa Access Token'ı long-lived
   kullanıcı token'ından türediği için SÜRESİZ kabul edilir — Instagram'ın aksine
   periyodik yenileme gerekmez.
5. **Telegram** — OAuth yok, bot token yetiyor:
   1. Telegram'da **@BotFather** ile konuş: `/newbot` → bota ad + kullanıcı adı ver,
      sana bir token verir (`123456789:AAF...`).
   2. Kanalını aç → Kanal bilgisi → Yöneticiler → botu yönetici olarak ekle. Bota EN
      AZINDAN "Mesaj gönder" yetkisi verilmeli, yoksa `sendVideo` "chat not found" /
      "not enough rights" döner.
   3. `upload/telegram_client_secrets.json` oluştur (örnek şablon:
      `upload/telegram_client_secrets.json.example`):
      ```json
      {"bot_token": "123456789:AAF...", "chat_id": "@kanaladi"}
      ```
      Kanal gizliyse `chat_id` sayısal olmalı (`-100...` ile başlar).

   Telegram'da keşfet/For You algoritması olmadığı için kanal kalıcı bir ARŞİV gibi
   çalışıyor: ana katalogda asıl gönderilen 16:9 UZUN video, dikey sürüm isteğe bağlı
   (`--kind dikey` / `her-ikisi`). Link cezası da olmadığı için YouTube linki doğrudan
   caption'ın içine giriyor (Instagram/TikTok'ta olduğu gibi yoruma değil). Bot API
   dosya sınırı 50 MB — gönderimden önce ölçülüyor.

   **DJ setleri ve derlemeler İSTİSNA:** 41-81 dakikalık `output/youtube_16x9.mp4`
   130-540 MB, yani 50 MB sınırının kat kat üstünde. `ek_platform_backfill.KOK_SAPMALARI`
   bu iki kökü `kind="dikey"` ile gönderiyor ve damgayı `telegram_shorts_message_id`'ye
   yazıyor — `telegram_uploaded_at` boş kalır, "Telegram'a hiç gitmemiş" sanma.
6. **Bluesky** — OAuth çemberi yok, handle + "app password" yetiyor:
   1. bsky.app → Settings → Privacy and Security → App Passwords → "Add App Password",
      bir isim ver, üretilen `xxxx-xxxx-xxxx-xxxx` şifresini kopyala (bir daha
      gösterilmiyor).
   2. `upload/bluesky_client_secrets.json` oluştur (örnek şablon:
      `upload/bluesky_client_secrets.json.example`):
      ```json
      {"handle": "famousmusicstudio.bsky.social", "app_password": "xxxx-xxxx-xxxx-xxxx"}
      ```
      `handle` tam olmalı, başına `@` koyma. App password ASIL hesap şifresi değildir,
      istediğin an iptal edilebilir. Kendi PDS'inde barınıyorsan dosyaya
      `"service": "https://pds.example.com"` ekleyebilirsin.
   3. `pip install atproto` gerekiyor. Video gönderimi için hesabın **e-posta
      doğrulaması ŞART**.

Bu üçü (Facebook/Telegram/Bluesky) OPT-IN: `config.EK_PLATFORMLAR` (ana katalog) ve
`config.EK_PLATFORMLAR_DJ` (DJ Famous) sözlüklerindeki bayraklarla açılıp kapanıyor.
İki sözlük BİLEREK ayrı — DJ setleri gerçek, tanınabilir bir kişiyi konu aldığı için
her yeni platform ayrıca teyit gerektiriyor; tek sözlük olsaydı katalog için bir
platformu açmak DJ Famous'u da sessizce oraya taşırdı (bkz. `dj_sets/README.md`).

Hiçbir platform için token yoksa `auto_process.py` o platformu sessizce atlar (hata vermez) —
istediğin platformlar için sırayla kimlik doğrulaması ekleyebilirsin.

**İzlenme süresi ölçümü AYRI bir token kullanıyor** (`upload/analytics_token.json`):
izlenme SÜRESİ YouTube Data API'de yok, ayrı bir servis ve ayrı bir izin
(`yt-analytics.readonly`) gerekiyor. Bu izni mevcut `upload/token.json`'a eklemek EN
KOLAY yol olurdu ama YANLIŞ olurdu — `Credentials.from_authorized_user_file` istenen
izinlerle kayıtlı izinleri karşılaştırdığı için listeyi büyütmek mevcut token'ı
geçersiz kılar ve sen yeniden yetkilendirene kadar SAATLİK YÜKLEME HATTI DURUR. Bu
yüzden ayrı token:
```bash
python upload/youtube_analytics.py --auth     # bir kereye mahsus izin
python upload/youtube_analytics.py            # raporu yazdır
```
Aynı `upload/client_secrets.json` kullanılıyor, yeni bir Cloud projesi gerekmiyor.
Bu dosya yoksa modül sessizce boş sonuç döner, yükleme hattı hiç etkilenmez.

**Telefon bildirimleri (`notify.py`, opsiyonel — TikTok hatırlatması için önerilir):**
TikTok'un aksine Instagram/YouTube'da elle bir adım yok (yukarıya bkz.), ama TikTok'ta
taslağı uygulamadan yayınlamak hâlâ elle yapman gereken bir şey — golden-hour
penceresine girildiğinde telefonuna [ntfy](https://ntfy.sh) üzerinden ücretsiz bir
hatırlatma bildirimi gönderilebilir:
1. Telefonuna **ntfy** uygulamasını kur (App Store / Play Store), hesap gerekmez.
2. Rastgele, tahmin edilmesi zor bir konu (topic) adı seç (ör. `fms-bildirim-x7q2`) ve
   uygulamada o konuya abone ol.
3. Repo kökünde `notify_config.json` oluştur (gitignored):
   ```json
   {"ntfy_topic": "senin-sectigin-konu-adi"}
   ```

Bu dosya yoksa otomasyon normal çalışmaya devam eder, sadece bildirim gönderilmez.

Tek başına, tek bir platforma yükleme (render zaten yapılmışsa):
```bash
python upload/youtube_upload.py --project "projects/sarki-adi"
python upload/youtube_upload.py --project "projects/sarki-adi" --shorts
python upload/tiktok_upload.py --project "projects/sarki-adi"
python upload/instagram_upload.py --project "projects/sarki-adi"
python upload/facebook_upload.py --project "projects/sarki-adi"            # --kind reels (varsayılan)
python upload/telegram_upload.py --project "projects/sarki-adi"            # --dry-run destekler
python upload/bluesky_upload.py  --project "projects/sarki-adi"            # --dry-run destekler
```

Zaten yüklenmiş videoların YouTube thumbnail'ini (geriye dönük) düzeltmek için:
```bash
python upload/youtube_upload.py --project "projects/sarki-adi" --thumbnail-only  # tek proje (uzun format + varsa Shorts)
python upload/youtube_upload.py --thumbnail-only --all                          # ÜÇ kökün TÜMÜ (projects/dj_sets/derlemeler)
python upload/youtube_upload.py --description-only --all                        # aynı desen, açıklama metni için
```

## Arka planda çalışan kapılar ve kontroller

Bu modüllerin hiçbirini elle çalıştırman gerekmiyor — `auto_process.py`'nin saatlik
koşusundan (ya da render öncesi doğrulamadan) otomatik tetikleniyorlar. Elle
çalıştırma sadece hata ayıklama/geri doldurma için.

- **`uyumluluk.py` — politika kapısı.** Hem render'dan ÖNCE (`validate_project.py`
  içinden, `asama="render"`) hem YAYINDAN önce (`auto_process.py` ve
  `dj_famous_process.py`, `asama="yukleme"`) otomatik çalışır. Ağa ÇIKMAZ; bilinen
  kuralları üretilen dosyalara uygular: `state.json`'da telif eşleşmesi işaretli mi
  (varsa bu içerik yeniden yayınlanmaz), aynı ses başka bir projede de var mı (md5,
  önce boyut ön filtresi — 2026-09-11'den beri UYARI değil **HATA**, yani boru hattını
  durdurur; muafiyet yalnızca (a) bu projede kayıtlı bir `kopya_notu` + çiftin bir tarafının
  yayından çekilmiş olması, ya da (b) eşleşen klasörün henüz hiç yayınlanmamış olması),
  derlemede bölüm damgası/küratörlük notu var mı,
  `meta.json`'da AI beyanı kapatılmış mı, bugün zaten kaç yükleme yapıldı
  (`GUNLUK_YUKLEME_UYARI = 3`). **HATA bulursa o proje yayınlanmaz**, uyarı sadece
  log'a düşer. `.claude/agents/icerik-uyumluluk-ajani.md` ile karıştırma — o ajan elle
  çağrılıyor ve güncel politikaları web'den araştırıyor; bu modül hızlı, yerel,
  otomatik kontrol.
- **`dj_tarama_kontrol.py` — Content ID karantinası.** DJ setleri VE derlemeler için
  (`dj_sets/` + `derlemeler/`). `dj_famous_process.py` seti YouTube'a `private` yükleyip
  durur (`dj_tarama_bekliyor`), diğer platformlara HİÇ gitmez; bu modül saatlik koşudan
  çağrılır, süre dolduğunda (`config.DJ_TARAMA_BEKLEME_SN`, 2 saat) videoyu kontrol
  eder, temizse `public` yapar ve kalan platformlar (Shorts, TikTok, Instagram,
  Facebook, Telegram, Bluesky) devam eder. Engel varsa private kalır + telefona bildirim
  gider. Haftalık koşuya değil SAATLİK hatta bağlı olmasının sebebi: ikinci aşama aksi
  hâlde bir sonraki haftaya kalırdı. **Sınır (dürüstçe):** YouTube Data API normal
  kanallara Content ID itiraz listesini açmıyor; burada
  `contentDetails.regionRestriction.blocked` alanına bakılıyor ve bu bir VARSAYIM —
  bu yüzden süre dolduğunda sonuç ne olursa olsun telefona bildirim gidiyor,
  Studio'dan elle bakılması isteniyor.
- **`saglik_kontrol.py` — sessiz duruşları yakalar.** Saatlik koşudan çalışır, iki şeye
  bakar: `upload/instagram_token.json`'ın süresi (son 10 güne girdiyse uyarır — token
  ~60 günde sessizce doluyor) ve Netlify kimlik bilgilerinin hâlâ çalışıp çalışmadığı
  (`netlify_kontrol.py`; token dolduğunda Instagram yüklemeleri 401'le sessizce duruyor,
  2026-09-08'de tam olarak bu oldu ve 25+ koşu fark edilmedi). Bildirimler GÜNDE BİR
  gönderilir (`upload/saglik_durum.json` damgası). İki koruma da depoda zaten VARDI ama
  hiçbir zamanlayıcıya bağlı olmadığı için hiç çalışmıyordu — bu modül ikisini de hatta
  bağlıyor.
- **`upload/ek_platform_backfill.py` — Telegram/Bluesky geri doldurma.**
  `_is_fully_done()` yalnızca dört anahtara (YouTube uzun + Shorts + TikTok + Instagram)
  bakıyor, yani bu dördü dolan proje bekleyenler listesinden kalıcı olarak düşüyor ve
  Telegram/Bluesky'yı bir daha hiç görmüyordu (disk kanıtı, 18 şarkı: Telegram 1,
  Bluesky 1). **Bu dar tanım BİLEREK korunuyor, genişletilmeyecek** — yeni bir platform
  eklerken izlenecek iki seçenekli kural `auto_process._is_fully_done()`'ın docstring'inde
  ("YENİ BİR PLATFORM EKLERKEN — BURAYA EKLEME"): ucuz/idempotent tamamlama işi →
  `_drain_golden_hour_queue()` (`ready` ile gezer); kendi hız sınırı/tavanı olan iş → ayrı
  süpürge modülü + `main()`'in `finally` bloğu. Üçüncü seçenek yok. Bu modül saatlik koşudan çağrılıyor ve iki kapıdan geçiyor: golden-hour
  penceresi + GÜNLÜK tavan (aksi hâlde 6 saatlik golden-hour × saatlik koşu = günde 6+6
  gönderi, yani tam da önlemek için yazıldığı spam deseni). Facebook'un karşılığı ayrı
  bir modül: `upload/facebook_backfill.py`. Elle:
  ```bash
  python upload/ek_platform_backfill.py --dry-run
  python upload/ek_platform_backfill.py --limit 2 --ignore-golden
  ```
- **`upload/youtube_analytics.py` — izlenme SÜRESİ ölçümü.** Ayrı token kullanıyor
  (yukarıdaki "Kimlik doğrulama" notuna bkz.). Neden gerekli: DJ setlerinin asıl değeri
  izlenme sayısı değil izlenme süresi — 41 dakikalık bir set, 3 dakikalık bir şarkıyla
  aynı izlenmeyi alsa bile kat kat fazla watch-time üretiyor. "Haftada bir set değer mi"
  sorusu bu sayı olmadan tahminle cevaplanıyordu.
- **`state_io.py` — `state.json` için tek atomik yazıcı.** Üç ayrı yerde `state.json`
  doğrudan `open(..., "w")` ile üzerine yazılıyordu; `open` dosyayı önce SIFIRLADIĞI
  için yazım yarıda kesilirse (güç kesintisi, zamanlayıcı timeout'u, paralel koşu)
  diskte YARIM bir JSON kalıyordu. `uyumluluk._durum()` artık bozuk bir `state.json`'ı
  sessizce `{}` saymadığı (HATA üretip boru hattını durdurduğu) için bunun bedeli
  büyüdü. Bu modül önce komşu bir `.tmp` dosyasına yazıp `flush`+`fsync` sonrası
  `os.replace` ile taşıyor (Windows'ta da atomik) — ya tam eski hâli ya tam yeni hâli
  kalır.

## DJ Famous (haftalık özel üretim)

Ana kataloktan (kurgusal temalar) tamamen AYRI, haftada bir kez yayınlanan,
**gerçek, tanınabilir bir kişiyi** konu alan özel bir format — `auto_process.py`
DEĞİL, `dj_famous_process.py` işler, `projects/` DEĞİL, `dj_sets/` klasörünü
kullanır. Görev Zamanlayıcı'da kendi haftalık görevi var (yukarıdaki tabloya bkz.).
Yayın öncesi **Content ID karantinası zorunlu**: set önce YouTube'a `private`
yüklenir, tarama beklenir, ancak temiz çıkarsa public olup diğer platformlara gider
(`dj_tarama_kontrol.py`, yukarıya bkz.). Detay, kurulum ve AI-içerik açıklama
kuralları için [dj_sets/README.md](dj_sets/README.md).

```bash
python dj_famous_process.py
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

## Derlemeler (uzun format, ayda en fazla bir tane, ELLE)

`derleme.py` yayınlanmış şarkılardan uzun format bir derleme üretir — **Suno kotasına
hiç dokunmadan**, malzeme zaten üretilmiş ve yayınlanmış olduğu için. Çıktı
`derlemeler/<ad>/` altına düşer ve `dj_famous_process.py --base derlemeler` ile DJ
setleriyle AYNI hattan (Content ID karantinası → YouTube → Shorts → TikTok →
Instagram → Facebook/Telegram/Bluesky) yayınlanır; ayrı bir işleyici gerekmedi.

```bash
python derleme.py --ad "Arabesk Gece" --tema arabesk --dry-run
python derleme.py --ad "En Çok Dinlenenler" --en-iyi --hedef-dk 40
python dj_famous_process.py --base derlemeler      # render + yayın
```

**Zamanlayıcıda BİLEREK yok, olmayacak da.** Derleme, YouTube'un "inauthentic content"
kuralına karşı bir KÜRATÖRLÜK hamlesi (seçim, sıralama, bölüm başlıkları), bir üretim
hattı değil — haftalık bir tetikleyiciye bağlanırsa kendisi o maddenin tarifine girer.
Kural: **ayda en fazla bir derleme** ve **her biri farklı bir konseptle** (tema, dönem,
"en çok dinlenenler" gibi); aynı havuzdan aynı mantıkla üretilen ikinci bir derleme,
birincinin tekrarıdır. Kurallar ve tasarım kararlarının tamamı:
[derlemeler/README.md](derlemeler/README.md).

## Büyüme / Paylaşım Stratejisi

Otomasyon yayınlama hızını çözüyor, ama izlenme/takipçi sayısını tek başına artırmıyor —
keşfedilebilirlik için ayrıca şunlara dikkat et. Detaylı, elle yapılan adımlar için
[buyume_kontrol_listesi.md](buyume_kontrol_listesi.md); hashtag/saat araştırması için
[trend_hashtag_notlari.md](trend_hashtag_notlari.md); vokal/tarz çeşitliliği takibi için
[ses_ve_tarz_takibi.md](ses_ve_tarz_takibi.md).

- **Paylaşım sıklığı/hacmi — bu tavsiye 2026-09-11'de TERSİNE ÇEVRİLDİ.** Eskiden burada
  "hazır şarkıları hızlıca sırayla yayınlamak algoritmaya 'aktif hesap' sinyali verir"
  yazıyordu; **artık geçerli değil.** YouTube 15 Temmuz 2025'te "repetitious content"
  politikasını "inauthentic content" olarak yeniden adlandırdı: toplu üretilmiş, jenerik,
  küratörlük eklenmemiş AI içeriği para kazanmaya uygun değil ve yaptırım kanal kapatmaya
  kadar gidiyor. Günde çok sayıda şarkı yayınlamak bu tanıma en çok benzeyen desen — ve
  kanalın en büyük tekil riski telif değil, tam olarak bu. Hedef artık **haftada 3-4
  şarkı**; `auto_process.MIN_YAYIN_ARALIGI_SN` (52 saat) bunu kodda zorluyor. Uzun format
  hacmi gerekiyorsa yol derleme (bkz. "Derlemeler"), daha sık şarkı değil.
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
- **Yorumlara hızlı yanıt:** İlk yorumlara hızlı dönüş etkileşim sinyalini güçlendirir.
  Yorumları GÖRMEK artık otomatik: `upload/youtube_comments.py` saatlik koşudan çağrılıp
  yanıt bekleyenleri `comments_cache.json`'a yazıyor (tüm kanal yorumları tek istekte,
  sayfa başına 1 birim). **YANIT GÖNDERMEK bilerek otomatikleştirilmedi** — şablon yanıt,
  YouTube'un "high-volume, repetitive" spam tanımına giren şeyin ta kendisi; yanıtlar tek
  tek, elle onaylanarak gönderiliyor.
