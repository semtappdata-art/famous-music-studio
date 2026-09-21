# Yayın sonrası takvim planı: türev içerikleri ilk render anında planlamak

> Yazıldığı an: **2026-09-13 (Pazar) ~03:30**. Bu belge **salt okunur** bir çalışmanın ürünü.
> Render, yükleme, API, Telegram, git ya da state yazımı yapılmadı; `auto_process` ve
> `dj_famous_process` çalıştırılmadı. Kanıtlar `dosya:satır` ya da log satırı olarak verildi.
> İnternetten doğrulananların kaynağı §9'da. **"doğrulanmadı"** yazan her madde ne ölçüldü ne de
> resmî kaynaktan teyit edildi.

## 0. Kısa sonuç

- **İstenen şey mümkün, ama çoğu türev "yükleme" değil, "hazırlık + elle adım" olmalı.** Kanalın
  en büyük riski "inauthentic content" ve bu risk **video sayısına** bakıyor
  (`haftalik_is_akisi.md` §1, kalıcı not). Bu yüzden önerilen set, YouTube'a yeni video yükleyen
  türevleri en aza indiriyor. Küratörlük ve insan emeği ekleyen türevleri öne alıyor: Topluluk
  gönderisi, kulis, Carousel söz kartları, derleme adaylığı.
- **Önerilen temel kural:** türevler 52 saatlik yeni yayın tabanına **sayılmaz** (backfill ve
  Shorts ile aynı mantık). Ama kendi tavanları var:
  - tüm platformlarda **günde en fazla 1 türev**, yalnız golden-hour içinde;
  - aynı şarkının iki türevi arasında **en az 48 saat**;
  - YouTube'a video yükleyen türev **haftada en fazla 1** (`dj_clips.KESIT_ARA_SN` ile ortak sayaç);
  - **yeni şarkının public anının ±24 saatinde türev yok**;
  - türev penceresi **T0 + 21 gün**, sonra kalan plan iptal.
- **Veri yeri:** proje `state.json`'ında `turev_plani` listesi. Takvim görünümü ondan türetilir,
  ayrı bir `yayin_takvimi.json` yok (§3).
- **Akış:** plan, ilk render'ın yapıldığı **aynı saatlik koşunun** `finally` bloğunda üretilir.
  Yeni süpürge `turev_takvimi.sirasi()` Kalıp B'dir ve `_is_fully_done`'a eklenmez. Türev
  render'ları golden-hour dışına ve prize ertelenir, ilk yayını bir saniye bile geciktirmez (§4).
- **Bugünkü kodda şimdiden tarihlenmiş bir türev var ve kimse onu takvimde görmüyor:**
  - `dj_sets/Just Relax` state'inde `dj_tarama_temiz: true` yazılı (2026-09-12).
  - Kesitlerde `enerji` alanı yok.
  - Sonuç: **18 Eylül Cuma 18:0x DJ koşusu** `clip_01.mp4`'ü (setin **5:32–6:17** anı) YouTube'a
    yükleyecek ve **≈21 Eylül Pazartesi 18:05**'e zamanlayacak (§5b).
  - `haftalik_is_akisi.md` §5 "Kapalı kalacaklar 4"te tam bu uyarı var. Karar sorusu 1.
- **Çalışma sırasında görülen, bu planın dışındaki üç canlı arıza** (düzeltilmedi, yalnız rapor):
  1. `Sabah Senin` 02:22'de **TikTok taslağı ve Facebook düşmüş**:
     `build_caption() got an unexpected keyword argument 'ai_beyani'` (`auto_process.log`).
     Canlı checkout'ta yarım bir düzenleme görünüyor. Aynı TypeError 02:23'te 6 TikTok işaretini
     de engelledi.
  2. **Yeni biçim render'ın ilk ölçümü:** 272 sn şarkı için 02:05:16 → 02:22:17 arası, yani
     **~17 dk (~3,7×)**. `uretim_hazirlik_suresi.md`'deki 1,41× varsayımının 2,6 katı. Tek örnek.
  3. Ortak kota tükenik: `thumbnails.set` ve `playlistItems` 403 aldı. `Sabah Senin` 12:00'de
     otomatik kareyle çıkacak (`youtube_giris_denetimi_2026-09-13.md` tuzak kutusu).

---

## 1. Türev içerik türleri

**Kısaltmalar:**

- **T0:** YouTube uzun formatın gerçek public anı (`youtube_publish_at`, yoksa `youtube_uploaded_at`).
- **Kota:** YouTube Data API ortak 10.000 birimlik günlük havuz. `videos.insert` 2026-06-01'den beri
  ayrı kovada, çağrı başına 1 birim, günde 100 çağrı (`onceden_render_plani.md` §0).
- **CPU:** bu makinede ölçülen ya da türetilen değer. Yeni biçimde 45 sn'lik bir dikey kesit, bugünkü
  17 dk / 272 sn ölçümüyle orantılanınca **~3 dk** tutar (türetilmiş, doğrulanmadı).

### 1a. Önerilen set (açılacaklar)

| # | Tür | Ne | Platform | Ne zaman | İlk render anında hazırlanan | Sonra hazırlanan | CPU / süre | Kota | Inauthentic riski | Riski düşüren kural |
|---|---|---|---|---|---|---|---|---|---|---|
| **E1** | **Yayın sonrası Studio işleri** | Shorts → İlgili video, sabitlenmiş yorum, kapak doğrulaması, DJ'de bölümler | YouTube Studio (elle) | T0 + 0-1 sa | Yorum metni (`youtube_giris_denetimi` (D) deseni), kapak yolu | — | 0 | 0 (Studio). Kapak CLI ile yapılırsa 2×50 = 100 | **düşük** (içerik eklemiyor, bağlıyor) | Tek tek, toplu düzenleme yok (denetim b-4). Sadece yeni video |
| **E2** | **Topluluk gönderisi — söz alıntısı + anket** | "Temiz Sözler"den bir beyit, 2-3 seçenekli anket ("hangi satır?"), 16:9 kapak | YouTube Posts (elle; Studio'da zamanlanabilir) | T0 + 1 gün | Metin (deterministik beyit seçimi, `social_text` deseni), anket seçenekleri, kapak kırpımı | — | ~1 sn | 0 (API yok, §9) | **düşük** (video değil, sohbet) | Şarkı başına 1; AI vurgulu ifade yok; "Suno" geçmez |
| **E3** | **Instagram Carousel — söz kartları** | 4-6 kart (1080×1350): nakarat + bir beyit + kapak; son kartta "Söz: Famous Music Studio" | Instagram (1. aşamada elle; API destekliyor, §9) | T0 + 4 gün (Perşembe dağıtım vardiyasına denk getirilir) | Kart PNG'leri (ffmpeg drawtext, `generate_cover` tipografisi), caption + `config.AI_BEYAN_SATIRLARI` vokalli satırı | — | ~10-20 sn | 0 (elle). API'de 1/100 gönderi (Carousel tek gönderi sayılıyor) | **düşük-orta** (aynı şarkı IG'de ikinci gönderi, ama biçim farklı ve metin insan yazımı) | Şarkı başına 1; Reels ile arasında ≥72 sa; hashtag bloğu Reels'ten farklı |
| **E4** | **Kulis / nasıl yapıldı** | Söz yazım sürecinden 3-5 madde ve bir "reddedilen taslak" hikâyesi (ör. *Vardiya* → *Sabah Senin*); nakarat kapısı tablosundan sade bir cümle | YouTube Posts (+ istenirse IG Carousel ikinci kart seti) | T0 + 7 gün | Taslak metin (`<slug>_sozler.md`'nin analiz bölümlerinden **aday** cümleler; yayından önce insan düzeltir) | İnsan onayı | ~1 sn | 0 | **düşük**: tam da politikanın istediği "yaratıcının özgün bakış açısı" | Üretim aracının adı geçmez; metin **elle onaylanmadan** gitmez; şarkı başına 1 |
| **E5** | **D+7 karar noktası** | Türev açılsın / iptal edilsin | — (rapor) | T0 + 7 gün | Kural ve eşikler | Ölçüm | 0 | 0 (`state.json`'daki `youtube_views` saatlik tazelemeden) | — | Tek video gürültü tabanı 21,2 puan: karar **yalnız düşük maliyetli** türevleri açar/kapar, tek başına yeni YouTube yüklemesi tetiklemez |
| **E6** | **Derleme adaylığı** | Şarkıyı bir sonraki derlemenin aday havuzuna not düşmek | YouTube uzun format (derleme olarak) | Ayın 3. Pazartesi'si (K-C), şarkı ≥7 gün public ise | Enerji değeri (`derleme._enerji`), telif/kopya kontrolü | Derleme kararı (elle, ayda ≤1) | Aday notu 0; derleme render'ı ayrı iş | Aday 0; derleme yüklemesi ≈ insert 1 + thumbnails 50 + playlist 50 | **düşük**: yükleme sayısını azaltan tek mekanizma | `derleme.py` kuralları aynen (yalnız public, telif/md5 eleme) |
| **E7** | **DJ seti: farklı kesit (tek)** | Setin ana Shorts'undan farklı **tek** an; başlıkta dakika damgası (`build_clip_snippet`) | YouTube Shorts (mevcut `dj_clips`) | T0 + ≥10 gün (Cuma koşusu → +3 gün yayın) | 3 kesit render'ı (`dj_famous_process._kesitleri_uret`, mevcut) | **Seçim D+7'de**: Analytics'te izlenmenin tepe yaptığı an (aşağıda) | 3 × ~3 dk (set render'ına ek) | insert 1 (ayrı kova) + playlist `list` 1 + `insert` 50 (+ kapak 50 ise) ≈ 101 | **orta** | Set başına 1 (yapısal, `tests/test_dj_kesit_yapisal_sinir.py`); haftada 1; **setin ilk 6 dakikasından kesit yok** (City Pulse'ta eşleşmelerin %65'i orada, `dj_sets/README.md`); telif aralığına değen elenir (mevcut) |
| **E8** | **TikTok ikinci kesit** (koşullu) | İkinci en enerjili 45 sn (nakarat dışı bölüm, ör. köprü) | TikTok (elle, kit) | T0 + 10-14 gün, ana TikTok gönderisinden ≥7 gün sonra | `output/turev_kesit_9x16.mp4` (aşağıda "Sonra" sütunu) | Render golden-hour dışında ve prizdeyken | ~3 dk | 0 | **orta** | Yalnız D+7 kararı **"aç"** ise; `TIKTOK_KIT_*` tavanlarına dahil (36 sa, haftada 4); ana taslak yayınlanmadıysa bekler |
| **E9** | **Telegram + Bluesky hatırlatma** (koşullu) | Video yeniden gönderilmez; metin + YouTube linki + soru | Telegram kanalı, Bluesky | T0 + 9 gün | Metin | — | 0 | 0; ama `ek_platform_backfill.GUNLUK_TAVAN = 1`'e **dahil** | **düşük-orta** (tekrar gönderi) | Yalnız D+7 "aç"; şarkı başına 1; o gün platformda başka gönderi yoksa |

**E7 — "en çok izlenen an" nasıl bulunur:**

- `upload/youtube_analytics.py`'nin ayrı `analytics_token.json`'u ile Analytics API
  `audienceWatchRatio` × `elapsedVideoTimeRatio` okunur. `olcum_temel_cizgi.py` aynı metriği
  %2/%3 noktalarında zaten okuyor.
- Tepe noktası 45 sn'lik pencereye çevrilir, `dj_clips.clip_uret`'in pencereleriyle kesiştirilir.
- Kota ayrı (Analytics), sayısı **doğrulanmadı**.
- 41 dk'lık bir sette 7 günlük izleyiciyle eğrinin anlamlı olup olmadığı da **doğrulanmadı**.
  Anlamlı değilse enerji sırası (mevcut) kullanılır.

### 1b. Elenen ya da ertelenen türler (gerekçeli)

| Tür | Karar | Gerekçe |
|---|---|---|
| **Şarkı "(Sözleri)" videosu** | **ELE** | Uzun format zaten `<ad> (Sözleri) \| …` başlığıyla çıkıyor ve sözlerle hizalanmış altyazı taşıyor (`caption_align`). İkinci video aynı sesin ikinci yüklemesi olur: `Yeniden Doğacağım`/`Küllerimden Geç` vakasının birebir aynısı. Değer hedefi yükleme değil, **açıklamaya "Temiz Sözler"** (denetim b-6). Bu da ilk yüklemede, 0 kota ile yapılır |
| **Tam set Shorts dizisi** (bir setten 5-10 Short) | **ELE** | "Tekrarlayıcı / toplu" tarifinin kendisi. `dj_clips` set başına 1'i bilerek **yapısal** kıldı. Resmî politika aynı videodan çoklu Shorts'u açıkça ele almıyor (§9); belirsizlikte fail-closed |
| **Nakarat Shorts'u** | **ELE (zaten var)** | `render.py` Shorts'u en yüksek enerjili 45 sn'den kesiyor (`HIGHLIGHT_PLATFORMS`). Nakarat çoğu şarkıda o pencere; ikinci bir "nakarat Short" mevcut Shorts'un kopyasına yakın olur (`dj_clips.clip_uret`'in `hepsi[1:]` notu) |
| **Şarkı için farklı dikey kesit — YouTube'a** | **ERTELE (09 Eki sonrası K-D)** | `haftalik_is_akisi.md` §5: Shorts'un kapatılması ölçümden sonra karara bağlanacak; "Shorts üretmeye devam etmek" kapalı listede. Aynı dosya **yalnız TikTok'a** (E8) koşullu gider |
| **Instagram Reels ikinci kesit** | **ERTELE** | Aynı sesin IG'de iki Reels'i, arşivlenmeyi bekleyen kopya Reels vakasının (E-9, A7) aynı sınıfı. Meta'nın özgünlük politikasının bu durumu nasıl gördüğü bu çalışmada **doğrulanmadı**. DJ seti için bile önce E7'nin YouTube sonucunu gör |
| **Akustik / yavaş versiyon** | **YALNIZ ÖNERİ** | Suno'da yeni üretim, Suno kotası ve yeni bir yayın, yani 52 saate sayılır; md5 farklı olduğu için kapıdan geçer. Otomatik üretim **yok**. D+14'te D+7 kararı "güçlü" ise haftalık raporun `SENİN İŞİN` bölümüne tek satır: "X için akustik sürüm düşünülebilir (K-A kota kararına bağlı)" |
| **Facebook türevi** | **ELE** | FB Reels'i IG ile aynı yüzey sınıfı; `facebook_backfill` tavanı 1 ve kazanç ölçülemiyor (`haftalik_is_akisi.md` §5 kapalı liste 2) |

---

## 2. Zamanlama kuralları

### 2a. 52 saat tabanı: sayılır mı?

**Öneri: SAYILMAZ, ama kendi tavanı olan AYRI bir sayaç var.** Mevcut kurallarla tutarlılık:

- 52 saat yalnız `YENI_YAYIN_TIMESTAMP_KEYS = ("youtube_uploaded_at",)` ve
  `YENI_YAYIN_PUBLIC_ANI_KEYS = ("youtube_publish_at",)` üzerinden ölçülüyor
  (`auto_process.py:125`, `:142`). Shorts (`youtube_shorts_publish_at`) ve geri doldurmalar zaten
  sayılmıyor. Görünürlük planında `tempo_sayilir: False` seçeneği var.
- Türev bir "yeni şarkı" değil, mevcut şarkının yeni bir yüzeyi. 52 saate saysaydık haftada 1-2
  şarkılık hat türevler yüzünden durur, kuyruk ters döner.
- **Sözleşme:** türev state anahtarları hiçbir zaman `UPLOAD_TIMESTAMP_KEYS` / `YENI_YAYIN_*`
  demetlerine girmez (`turev_plani[*].yayin.an` iç alanı). Bu bir `ast` testiyle kilitlenir.
  Aksi hâlde günlük pencere paydası bozulur.
- İstisna yok: **DJ kesiti** bugün `youtube_clip_uploaded_at` yazıyor. O anahtar da demetlerde
  değil, tutarlı.

### 2b. Tavanlar ve aralıklar

| Kural | Değer | Gerekçe / eş kural |
|---|---|---|
| Günlük türev tavanı (tüm platformlar, TR takvim günü) | **1** | `ek_platform_backfill.GUNLUK_TAVAN = 1`, `TIKTOK_KIT_GUNLUK_TAVAN = 1` ile aynı felsefe |
| Yayın saati | **Yalnız golden-hour** (12-14 / 18-22). Elle türevlerde kit pencerenin başında gider | `config.GOLDEN_HOURS` |
| YouTube'a video yükleyen türev | **Haftada en fazla 1** (kayan 7 gün) | `dj_clips.KESIT_ARA_SN = 7 gün`. **Aynı sayaç**: şarkı ve set kesitleri birlikte |
| Yeni şarkı koruma bandı | Kuyrukta sesi hazır (render'lı ya da `audio.*` var) yeni şarkının **tahmini public anı ±24 sa** içinde türev **yok** | "Yaklaşan yeni yayın öncelikli." Tahmin = `max(52 sa tabanı, günlük pencere)` + sonraki golden-hour, `_auto_pace_count` ile aynı aritmetik |
| Aynı şarkının türevleri arası | **≥48 sa** (herhangi platform) | Aynı şarkının aynı kitleye art arda düşmemesi |
| Aynı platformda aynı şarkı | **≥72 sa** (ör. IG Reels → IG Carousel) | IG konteyner/yayın deseni |
| Şarkı başına toplam | **≤4 türev** (E2, E3, E4 + koşullu E8 veya E9) | Hacim tavanı |
| Set başına kesit | **1** (yapısal, değişmez) | `dj_clips` modül notu |
| Türev penceresi | **T0 + 21 gün**. Sonra `planlandi`/`hazirlandi` → `iptal` ("süre doldu") | Bayat kuyruk birikmesin (`tiktok_yayin_kiti` bayatlık deseni) |
| Cuma | YouTube'a **yükleme** yapan türev Cuma yok (DJ koşusu). Public anı Cuma olabilir | `haftalik_is_akisi.md` Cuma kuralı |
| Kota | Türev YouTube yan çağrıları (playlist/kapak) koşu başına ≤1 proje. `quotaExceeded` görülen koşuda türev API adımı atlanır | 2026-09-06 kota tükenmesi dersi |

### 2c. Çakışma çözümü (kataloğun geri kalanıyla)

Öncelik sırası, **yüksekten düşüğe**:

1. **Yeni şarkının ilk yayını ve kendi platform zinciri** (YouTube, IG, TG/BS ilk gönderi, FB, TikTok taslağı).
2. **Mevcut geri doldurmalar ve tamamlama işleri** (IG konteyneri, altyazı, FB/TG/BS backfill,
   görünürlük planı, TikTok kiti).
3. **Türevler**: önce hedef tarihi en çok geçmiş olan; eşitlikte risk sırası (düşük önce); sonra T0'ı yeni olan.

Kaydırma kuralı:

- Çakışan türev **yalnız ileri** kayar: sonraki uygun golden-hour penceresi.
- Kayma türevin `en_gec` anını aşarsa `iptal` ("çakışma nedeniyle süre doldu").
- **Asla öne çekilmez.**
- TG/BS hatırlatması (E9), aynı gün backfill kuyruğunda bekleyen bir şarkı varsa **ona yol verir**.
  Günlük tavan 1 ortak.

---

## 3. Veri modeli

### 3a. Yer: `state.json` içinde `turev_plani` mı, kökte `yayin_takvimi.json` mı?

| | **`state.json` → `turev_plani` (önerilen)** | **Kökte `yayin_takvimi.json`** |
|---|---|---|
| Artı | Proje ile birlikte yaşar (klasör taşınır, silinir, kopya olur). `uyumluluk.kontrol`, `yayin_beklet`, `kopya_notu` **aynı dosyada**, kapı kararı tek okuma. Atomik yazıcı hazır (`state_io`). Pano `/takvim` zaten state katalogunu okuyor (`plugin_api.py` "1. Yayın takvimi"). `derleme.py`'nin HEDEF_KOK test koruması gibi mevcut test korumaları state için kurulu | Tek dosyada küresel görünüm; tempo sayacı tek okuma |
| Eksi | Küresel tempo için ~25 state okunur. Bu zaten her süpürgede yapılıyor ve ucuz. **Yazma yarışı:** `dj_sets/*/state.json` hem `auto_process` (`dj_tarama`) hem `dj_famous_process` tarafından yazılabilir ve iki sürecin kilitleri ayrı | İkinci doğruluk kaynağı: state ile ayrışır ("bayatlayan sabit liste" hata sınıfı). Proje silinince yetim kayıt kalır. Kopya/bekletme kapısı için yine state okumak gerekir. Git'e commit'li mi olacak kararı gerekir (state.json'larla aynı `reset --hard` riski). Test koruması (`conftest`) yeniden kurulmalı |
| Yarış önlemi | Plan yazımı **tek yazıcı**: yalnız saatlik süpürge. `.dj_famous_process.lock` tazeyse `dj_sets` kökü o koşuda atlanır. Yazım `state_io` ile "oku → yalnız `turev_plani` anahtarını birleştir → yaz" | Dosya kilidi (`elle_islem._kilit` deseni) |

**Seçim: `state.json` → `turev_plani`.** Takvim (pano, rapor, sesli asistan) bu listelerden
**türetilir**, saklanmaz.

### 3b. Kayıt biçimi

```json
"turev_plani_surumu": 1,
"turev_plani": [
  {
    "id": "TRV-sabah-senin-topluluk-1",
    "tur": "topluluk_soz_anket",
    "platform": "youtube_posts",
    "elle": true,
    "t0": "2026-09-13T12:00:00+03:00",
    "hedef_an": "2026-09-14T12:00:00+03:00",
    "en_erken": "2026-09-14T12:00:00+03:00",
    "en_gec": "2026-09-18T22:00:00+03:00",
    "durum": "planlandi",
    "dosyalar": ["output/turev/topluluk_1.txt", "cover.png"],
    "bagimliliklar": ["youtube_public", "!yayin_beklet", "!kopya_notu"],
    "iptal_kosulu": ["kopya_notu", "telif_isareti", "d7_karar=iptal", "en_gec_asildi"],
    "kosul": null,
    "risk": "dusuk",
    "kota": {"youtube_birim": 0, "ig_gonderi": 0},
    "tempo_sayilir": false,
    "yayin": null,
    "iptal_sebebi": null,
    "olusturuldu_at": "2026-09-13T03:05:30+03:00",
    "guncellendi_at": "2026-09-13T03:05:30+03:00"
  }
]
```

**Alanlar:**

- `durum`: yalnız **`planlandi` → `hazirlandi` → `onay_bekliyor` → `yayinlandi`**, ya da herhangi
  bir yerden **`iptal`**. Geri geçiş yok; yeniden planlama yeni `id` ile yapılır. Beşten farklı
  bir değer okunursa kayıt **fail-closed** atlanır ve bir kez log'a düşer.
- `kosul`: yalnız E8/E9 için, `"d7_karar=ac"`.
- `yayin`: yayınlanınca doldurulur:
  `{"an": ..., "kimlik": "<video_id|post_id|null>", "kaynak": "otomatik" | "elle:EI-…"}`.

### 3c. `yayin_beklet` ve `kopya_notu` türevleri de durdurur

- Süpürge, bir türevi `hazirlandi`'dan ileri taşımadan ve yayından/kitten önce **her seferinde**
  `uyumluluk.kontrol(proje, "yukleme")` çağırır. Bu tek çağrı bekletmeyi (HATA), md5 kopyasını ve
  telif işaretini kapsar. **Fail-closed:** kapı çökerse türev o koşuda ilerlemez (dj_clips deseni,
  `return` değil atlama ve log).
- **`yayin_beklet` → duraklatma, iptal değil.** Kayıt `durum`unu korur ama hedef anı geçse bile
  yayınlanmaz. `en_gec` aşılırsa `iptal` ("bekletme süresince pencere doldu"). Render
  aşamasındaki kural gibi **hazırlık** (render/kart üretimi) bekletmede de yapılabilir; yayın yapılamaz.
- **`kopya_notu` ya da telif işareti** (`telif_araliklari`/`telif_eser`, `derleme.TELIF_ISARETLERI`)
  → bekleyen **tüm** türevler kalıcı `iptal`. Karar geri alınırsa plan yeniden üretilmez; insan
  karar verir.
- **`youtube_privacy_gercek` public değilse** (gizlilik kayması) → duraklatma, çünkü türev linki
  gizli videoya gider (`ek_platform_backfill._public_ani` deseni).

### 3d. Elle işlemler defteri (`elle_islemler.jsonl`) ile ilişki

Defter henüz **diskte yok** (ilk `ekle` ile oluşur).

**Mevcut tuzak:** `elle_islem.ekle(platform="tiktok", islem="yayinladi", proje=…)` state'e
**`tiktok_publish_plan.isaretle_yayinlandi`** ile yansıyor. Bu, projenin **ana TikTok taslağını**
yayınlandı işaretler. İkinci kesiti (E8) elle yayınlayan kullanıcı bu komutu kullanırsa ana taslak
yanlışlıkla "yayında" sayılır ve kit/doğrulama bir daha ona bakmaz.

**Öneri (sözleşme değişikliği, pano da okuyor):**

1. `ISLEMLER` sözlüğüne **yeni anahtar** `"turev_yayinladi": "türevi yayınladı"`.
2. Kayıtta `kanit` alanı **türev id'si** (`"TRV-sabah-senin-carousel-1"`). Elle yol:
   ```
   python elle_islem.py ekle --platform instagram --proje "Sabah Senin" \
       --islem turev_yayinladi --kanit TRV-sabah-senin-carousel-1 --ayrinti "telefondan"
   ```
3. `_state_yansit` için yeni **güvenli eşleme**:
   - Yalnız `turev_yayinladi` + geçerli `kanit` id + o id `onay_bekliyor`/`hazirlandi` durumunda ise
     `turev_plani[id].durum = "yayinlandi"`,
     `yayin = {"an": zaman, "kimlik": null, "kaynak": "elle:<EI-id>"}`.
   - **`isaretle_yayinlandi` asla çağrılmaz.**
   - id bulunamazsa ya da iptal edilmişse **RED**: ne defter ne state yazılır (TikTok onayındaki kural).
4. Telegram onay kalıbı: `yayınladım <kısa kod>`. Kod `id`'den türetilir (`tiktok_upload.yayin_kodu`
   deseni). Hermes becerisi `tiktok-yayin-onayi` ile karışmasın diye ayrı beceri
   (`turev-yayin-onayi`) ve ayrı önek (`T-`).
5. Otomatik yayınlanan türevler (DJ kesiti) deftere **yazılmaz**. Defter "otomasyonun dışındaki işler" sözleşmesi.

---

## 4. Akış

### 4a. İlk render anında

**Plan üretimi `process_project`'in İÇİNE konmaz.** Gerekçe CLAUDE.md'nin "sessiz bağlantı" bölümü:
`process_project` pending'e bağlı ve tek atış. Plan üretimi orada patlarsa o proje bir daha hiç
planlanmaz ve log'a tek satır kalır. Bunun yerine:

```
auto_process.main()
  try:   … process_project(Sabah Senin)  → render + YouTube (T0 belli olur) …   [DEĞİŞMEZ]
  finally:
     … _ek_platform_backfill() … _tiktok_yayin_dogrulama() … _tiktok_kit_sirasi()
     _turev_takvimi()          ← YENİ, en sonda, _release_lock()'tan hemen önce
        └─ turev_takvimi.sirasi(log)
             1. PLAN: youtube_video_id VAR + turev_plani YOK + T0 son 72 saat içinde
                (ya da gelecekte) olan projeler → plan_uret()   [koşu başına ≤3 proje, yalnız yazma]
             2. HAZIRLIK: hedef_an − 48 sa'e girmiş, durum=planlandi, kaynağı hazır olan
                EN FAZLA 1 türev → dosya üret → hazirlandi
                  · render gerektirenler (E8 kesit, E3 kartları) YALNIZ golden-hour DIŞINDA
                    ve PRİZDEYKEN (en_gec'e <24 sa kaldıysa pilde de)
             3. YAYIN / KİT: golden-hour içinde, tüm kapılardan geçen EN FAZLA 1 türev
                  · otomatik türev → yükle → yayinlandi
                  · elle türev     → Telegram kiti → onay_bekliyor
             4. BAKIM: en_gec aşılanlar → iptal; D+7 kararı; 48 sa onaysız kite TEK hatırlatma
             5. ÖZET: her koşuda TEK log satırı ("türev: plan N, hazır N, kit N, iptal N" ya da sebep)
```

- **"İlk render dönemi" şartı karşılanıyor:** plan, render'ın yapıldığı **aynı koşunun** `finally`
  bloğunda, T0 kesinleştikten dakikalar sonra üretilir. Yeni bir proje için en geç ilk sonraki koşuda.
- **DJ setleri:**
  - Kesit render'ı bugünkü gibi `dj_famous_process.process_set` → `_kesitleri_uret` içinde kalır
    (set render'ı ile aynı koşu).
  - Plan ise saatlik süpürgeden üretilir; tek yazıcı. `dj_famous_process.py`'ye plan yazımı eklenmez.
  - Set T0'ı Content ID karantinası temizlenince oluşur (`dj_tarama_temiz`); plan ondan önce üretilmez.
- **İlk yayını geciktirmez mi?** Evet, üç sebeple:
  1. `finally` ilk yayından **sonra** koşuyor.
  2. Render gerektiren türevlerin en erkeni T0+4 gün (E3). Hazırlık `hedef_an − 48 sa`'e ertelenebilir.
  3. Golden-hour içinde **hiç render yok**. IG drain ve backfill pencere koşularında gecikmez.
- **CPU / süre bütçesi:**

  | İş | Maliyet (bu makine) | Kural |
  |---|---|---|
  | Plan üretimi | ~25 state okuması + yazım, <1 sn | Her koşu |
  | E2/E4 metni | <1 sn | Plan anında |
  | E3 kartları (4-6 PNG) | ~10-20 sn (drawtext + ölçümlü sığdırma; kapak üretimi ~25-35 sn ölçüldü) | Hazırlık adımı, koşu başına 1 |
  | E8 kesit (45 sn) | ~3 dk (bugünkü 17 dk / 272 sn ölçümünden orantı, **doğrulanmadı**) | Golden-hour dışı + priz |
  | E7 DJ kesitleri (3 adet) | ~9 dk + `find_highlights` taraması (41 dk ses, **ölçülmedi**) | Mevcut: set koşusunda. Değişmez |
  | Kilit | `LOCK_STALE_SECONDS` 4 sa; nabız `log()` içinde | Render sırasında log satırı basılmalı |

- **Pil:** Görevler artık pilde de koşuyor (`DisallowStartIfOnBatteries=False`, 2026-09-12). Bu
  yüzden "pilde görev durur" korumasına değil, **"pilde render yapma"** kararına ihtiyaç var.
  - Önerilen yardımcı: `guc_durumu.prizde_mi()`, ctypes `GetSystemPowerStatus` → `ACLineStatus`.
    Alt süreç yok, <1 ms.
  - **Bilinmiyorsa pil sayılır:** render ertelenir, plan etkilenmez.
  - Pilde `TerminateProcess` riski hâlâ var (kalıcı not); render yarıda kalırsa `render.video_butun_mu`
    yarım mp4'ü yakalar.

### 4b. Yayın günü gelince

- **Yayını yapan adım:** saatlik `auto_process.py` → `finally` → `_turev_takvimi()` →
  `turev_takvimi.sirasi()`, adım 3.
- **Kalıp B:** kendi tempo tavanı var (§2b). `_is_fully_done`'a **eklenmez**.
  `process_project`'e **bağlanmaz**.
- **Otomatik yayın yolları (aşamalı):**
  - E7 DJ kesiti bugünkü gibi haftalık `dj_clips.supur` ile yayınlanır. Süpürge takvimin
    **koruma bandını ve haftalık sayacı okur** (Aşama 4, varsayılanlı parametre).
  - E9 TG/BS hatırlatması `telegram_upload`/`bluesky_upload`'ın metin gönderimine bağlanır.
    `ek_platform_backfill.bugun_yuklenen` sayacına dahil edilmesi için damga `telegram_turev_uploaded_at`
    / `bluesky_turev_uploaded_at` ve `_damga_anahtarlari` listesine ekleme.
  - Diğerleri elle.
- **Kapı sırası** (her yayın/kit öncesi, ucuzdan pahalıya; dj_clips'teki gerekçe):
  1. durum ve `kosul`
  2. golden-hour
  3. günlük / haftalık / aynı şarkı tavanları
  4. koruma bandı
  5. `youtube_privacy_gercek`
  6. **en sonda** `uyumluluk.kontrol(…, "yukleme")`
  7. otomatik yüklemede ağa çıkan son noktada **ikinci kemer** (`kesit_yayinla` deseni, `raise`)

### 4c. Elle platformlar: Telegram kiti

`upload/tiktok_yayin_kiti.py` birebir desen: ayrı mesajlar, `parse_mode` yok, operatör sohbetine.
Yayın kanalı ile aynıysa `notify._telegram_ayari` kapatır.

| Türev | Mesajlar |
|---|---|
| E1 Studio işleri | (1) yapılacaklar listesi (ilgili video, sabit yorum metni, kapak dosyası yolu), (2) "yaptım T-xxxx" |
| E2 Topluluk | (1) kapak fotoğrafı `send_photo`, (2) YALNIZ gönderi metni, (3) YALNIZ anket seçenekleri, (4) "Studio'da *Zamanla* ile şu saate koy" + onay kalıbı |
| E3 Carousel | (1-6) kartlar sırayla `send_photo` (medya grubu desteği depoda **yok**, `onceden_render_plani.md` §7), (7) YALNIZ caption + AI beyan satırı + hashtag, (8) ayar listesi + onay kalıbı |
| E4 Kulis | (1) taslak metin — **"düzelt ve öyle yayınla"** uyarısıyla, (2) onay kalıbı |
| E8 TikTok kesit | (1) video dosyası (45 sn ≈ 2,5 MB; bot sınırı 50 MB). Telegram'da video gönderen fonksiyon `notify`'da var mı **doğrulanmadı**; yoksa `telegram_upload` deseniyle eklenir. (2) `build_tiktok_kit_caption`, (3) ayarlar, (4) onay |

Kit tempo kuralları:

- Önceki türev kiti onaylanmadan yenisi yok (kit modülüyle aynı gerekçe).
- 48 sa sonra tek hatırlatma, `en_gec`'te iptal.
- **E8, `TIKTOK_KIT_*` tavanlarına dahil**: `_tempo_engeli` türev kit damgasını da okur (varsayılanlı parametre).

### 4d. Görünürlük

- **Pano:** `plugin_api.py` `/takvim` (Hermes eklentisi, repo **dışında**,
  `%LOCALAPPDATA%\hermes\plugins\jarvis-hud\`). Bugün a) zamanlanmış YouTube/FB yayınlarını, b)
  görünürlük planı kuyruğunu, bekletilenleri gösteriyor. Yeni **c) türevler** bölümü:
  `turev_plani` → olay (`an = hedef_an`, rozet `planli` / `hazir` / `onay` / `iptal`, `elle` işareti).
  Kart zaten tasarlandığı için yalnız veri kaynağı eklenir; o dosyanın sahibi ayrı ajan.
- **Sesli asistan:** "Bu hafta ne yayınlanacak?" sorusu aynı `/takvim` uç noktasından cevaplanır.
  Ayrı veri yolu yok, iki kopya ayrışmasın. Cümle kalıbı: "Salı öğlen Sabah Senin için Topluluk
  gönderisi (senin işin), Perşembe akşam Carousel…".
- **Günlük rapor:** `weekly_report.gunluk_izlenme_raporu` mesajının sonuna tek blok
  `BUGÜN/YARIN TÜREV`. En fazla 4 satır, elle olanlar "senin işin" etiketli.
- **Haftalık özet:** `_haftalik_satirlar`'a `TÜREVLER` bloğu: bu hafta planlı / yayınlanan /
  iptal (sebep sayılarıyla). D+7 kararları da burada.
- **Sağlık:** `saglik_kontrol.kontrol_et()`'e **onuncu adım** `turev_takvimi_saglik()`. CLAUDE.md'deki
  "DOKUZ" sayısı ve listesi **birlikte** güncellenmeli. Neyi yakalar:
  - T0'ı 6 saatten eski olup `turev_plani` olmayan yeni proje: plan üretimi ölü.
  - Hedef anı 24 saatten fazla geçmiş `planlandi`/`hazirlandi`: hazırlık ölü.
  - `onay_bekliyor`'da 72 saati aşan: operatör kiti görmüyor.

  Günde en fazla bir bildirim.

### 4e. ÜÇ SORU

1. **Kim çağırıyor?**
   - `auto_process.main()` `finally` → `_turev_takvimi()` → `turev_takvimi.sirasi(log)`.
     Import sarmalayıcının **içinde**; modül yüklenemezse koşu devam eder ve log'a
     "türev takvimi YÜKLENEMEDİ" düşer.
   - Okuyanlar: `weekly_report` (günlük/haftalık), `saglik_kontrol.turev_takvimi_saglik`, pano
     `/takvim`, `elle_islem._state_yansit` (turev_yayinladi).
   - DJ tarafında `dj_famous_process.main()` `finally` → `_kesit_yayini` → `dj_clips.supur`,
     takvim kapılarını okur, plan yazmaz.
2. **Hangi zamanlanmış görevden?**
   - Saatlik `AutoProcess` (plan, hazırlık, kit, bakım).
   - Haftalık `DjFamousProcess` (yalnız DJ kesit yayını, bugünkü gibi).
   - Yeni görev **yok**.
3. **Bozulunca nasıl anlaşılır?**
   - Her koşuda tek özet log satırı; satır yoksa `_turev_takvimi` çağrılmıyor demektir.
     `ast` testi `finally` sırasını kilitler.
   - Sağlık adımı üç arıza biçimini ayırır (§4d).
   - Kit gönderilemezse `notify.uyar_bir_kez`.
   - Testler: `tests/test_turev_takvimi.py` (davranış) ve
     `tests/test_entegrasyon_duman.py` ekine çağrı sırası.

---

## 5. Somut örnek takvimler

**Okunan durum (2026-09-13 03:05 koşusu ve state'ler):**

- `Sabah Senin`:
  - YouTube `Ozn9WnPgdfk` + Shorts `iJC3RX89UXc`, ikisi de `publishAt 2026-09-13T09:00:00Z` (TR 12:00).
  - IG konteyneri 02:22:57'de açıldı.
  - **TikTok taslağı ve FB yok** (TypeError). Proje hâlâ `pending`.
- `Kader Ortakları`: IG golden-hour bekliyor (konteyner 12 Eyl 22:06, son makul koşu 13 Eyl 21:05).
- `Küllerimden Geç`: görünürlük planı (Shorts → public, golden-hour, pencere başına 1).
- `Bu Gece Kazandık`: `yayin_beklet` (yeniden render + yeni yükleme bekliyor).
- `Yükseliş`: ses yok. `Night Drive`: ses yok.
- `Just Relax`:
  - `dj_clips` 3 kesit (332,5 / 1491,4 / 2101,4 sn), **`enerji` alanı yok**.
  - `dj_tarama_temiz: true`, `youtube_clip_video_id` yok.
  - Shorts 07 Eyl 16:18.
- **Kuyrukta sesi hazır yeni şarkı: YOK.** Bu yüzden şu an koruma bandı yok.
  - Sabah Senin'den sonraki en erken yeni yayın: **15 Eyl 16:00 + kayma → 17:05 koşusu → 18:00 public**.
  - Ama pazartesi raporu `BEKLEYEN > 0` gösterecek (Sabah Senin TikTok'u eksik), yani Salı üretimi
    `haftalik_is_akisi.md` K-E gereği büyük olasılıkla atlanacak.
  - **Varsayım:** 20 Eylül'e kadar yeni şarkı public olmaz. Olursa §2c kaydırması uygulanır;
    satırlardaki "kayarsa" notu bunun için.
- Takvim gün adları: 13 Paz · 14 Pzt · 15 Sal · 16 Çar · 17 Prş · 18 Cum · 19 Cmt · 20 Paz · 21 Pzt · 22 Sal · 23 Çar · 24 Prş.

### 5a. Sabah Senin — T0 = 2026-09-13 12:00 (rock, 272 sn)

| # | Tarih | Saat | Platform | İçerik | Hazırlık durumu | Kota | Not / çakışma |
|---|---|---|---|---|---|---|---|
| 1 | 13 Eyl Paz | 10:00–12:00 | YouTube (CLI ya da Studio) | **E1a** Kapak telafisi: `thumbnails.set` 02:22'de 403 aldı → `cover.png` + `cover_vertical.png` | `onay_bekliyor` (elle, bugün) | Studio 0 · CLI `--thumbnail-only` 2×50 = **100** | Kota TR 10:00'da sıfırlanıyor; public'ten önce yapılmalı |
| 2 | 13 Eyl Paz | 12:00 | YouTube uzun + Shorts | İlk yayın (T0) | `yayinlandi` (zamanlı, YouTube kendisi açar) | Harcandı: 2 × insert (ayrı kova) | Türev değil; referans. Playlist eklemesi 403 aldı, `pending` sürdükçe yeniden denenir (**doğrulanmadı**) |
| 3 | 13 Eyl Paz | 12:05 (yedek 13:05) | Instagram Reels | İlk yayın (drain) | `hazirlandi` (konteyner 02:22:57, bayatlama 14 Eyl 01:22) | IG 1/100 | Aynı koşuda Kader IG + Küllerimden Shorts planı da var; drain proje başına |
| 4 | 13 Eyl Paz | 12:05–13:05 | Telegram, Bluesky | İlk gönderi (`ek_platform_backfill`, yeni public önde) | mevcut hat | Günlük tavan 1'er (13 Eyl'de ikisi de boş) | FB aynı pencerede `facebook_backfill`'e düşer; **TypeError sürerse FB tekrar düşer** |
| 5 | 13 Eyl Paz | 13:05–14:00 | YouTube Studio | **E1b** Shorts → İlgili video = uzun "Sabah Senin"; sabitlenmiş yorum (denetim (D) metni) | `onay_bekliyor` (elle) | 0 | İlgili video için hedef public/unlisted olmalı → 12:00 sonrası |
| 6 | 14 Eyl Pzt | 12:00 | YouTube Topluluk | **E2** Beyit: "Ayakkabım elimde, yerler serin / Uyuyorsun, yüzünde dünkü gülüş" + anket "Sabahını kime bırakıyorsun? · kendime · ona · işe" + `cover.png` | `hazirlandi` (plan 13 Eyl 03:05 koşusunda) → kit 12:05 → `onay_bekliyor` | 0 | T0+24 sa. Pazartesi 09:00 raporundan sonra, 10:15 kota işleriyle çakışmaz. Yeni şarkı 15 Eyl 18:00'e girerse bant 14 Eyl 18:00'de başlar; 12:00 bandın dışında |
| 7 | 17 Eyl Prş | 19:00 | Instagram Carousel (elle) | **E3** 5 kart: kapak · nakarat · Verse 1 beyit · Bridge beyit · "Söz: Famous Music Studio" | `planlandi` → **15 Eyl 03:05** koşusunda kartlar (golden dışı, priz) → `hazirlandi` → 17 Eyl 19:05 kit | 0 (elle) | Perşembe dağıtım vardiyası. IG Reels'ten (13 Eyl) ≥72 sa ✓, E2'den ≥48 sa ✓ |
| 8 | 18 Eyl Cum | — | — | *Türev yok* | — | — | Cuma: DJ koşusu (§5b satır 3) ve haftalık kesit sayacı Just Relax'te |
| 9 | 20 Eyl Paz | 12:05 | — (rapor) | **E5** D+7 kararı: `youtube_views` (uzun+Shorts), katalogdaki şarkıların D+7 medyanına göre → **aç** (≥ medyan) / **sınırlı** (medyanın %50'si ile medyan arası: E8/E9 kapalı) / **iptal** (< %50: E4 dahil kalan her şey kalır, yalnız E8/E9 iptal) | `planlandi` → karar | 0 | Tek videoda gürültü 21,2 puan; karar yalnız E8/E9'u açar/kapar. Günlük rapora satır |
| 10 | 20 Eyl Paz | 18:00 | YouTube Topluluk | **E4** Kulis: "Bu şarkının ilk adı *Vardiya*ydı; nakaratı 'sevgilisine söylenir mi?' sorusundan geçemedi, baştan yazıldı…" (taslak, insan düzeltir) | `hazirlandi` (taslak metin 13 Eyl) → kit 18:05 → `onay_bekliyor` | 0 | E3'ten 71 sa sonra (≥48 ✓). "Suno"/üretim aracı adı **geçmez** |
| 11 | 21 Eyl Pzt | 10:15 | Derleme (karar) | **E6** Derleme adaylığı: K-C, ayın 3. Pazartesi'si; Sabah Senin ≥7 gün public ✓, telif/kopya yok ✓, enerji değeri notu | `planlandi` → `yayinlandi` = "aday listesine girdi" | 0 (derleme yapılırsa ≈101 + insert 1) | Ayda ≤1 derleme kuralı elle |
| 12 | 22 Eyl Sal | 12:00 | Telegram + Bluesky | **E9** Hatırlatma (koşul: D+7 = aç): metin + youtu.be linki + "Eve döndüğünde ilk ne yaparsın?" | `planlandi` (koşullu) | 0; günlük tavan 1'e **dahil** | O gün backfill'de şarkı bekliyorsa ona yol verir → 23 Eyl'e kayar |
| 13 | 24 Eyl Prş | 19:00 | TikTok (elle) | **E8** İkinci kesit (koşul: D+7 = aç **ve** ana TikTok gönderisi ≥7 gün önce yayınlandı) | `planlandi` (koşullu); render 22-23 Eyl golden dışı + priz (~3 dk) | 0 | **Bugün bağımlılık kırık**: ana taslak hiç oluşmadı (TypeError). Ana gönderi 17 Eyl'den sonra çıkarsa E8 en erken +7 gün kayar; `en_gec` 04 Eki'yi aşarsa iptal |
| 14 | 28 Eyl Pzt | 09:00+ | Haftalık rapor | Akustik sürüm önerisi — yalnız D+7 "aç" ve izlenme medyanın 2 katı ise tek satır | öneri | 0 (Suno kotası K-A kararında) | Otomatik üretim yok |
| 15 | 04 Eki Paz | 22:00 | — | Pencere kapanır (T0+21 gün): kalan `planlandi`/`hazirlandi` → `iptal` | — | 0 | — |
| ✗ | — | — | YouTube Shorts (2. kesit) | Şarkı için ikinci YouTube kesiti | `iptal` ("K-D: Shorts kararı 09 Eki ölçümünden sonra") | — | §1b |
| ✗ | — | — | YouTube "(Sözleri)" videosu | — | `iptal` (§1b) | — | — |

**Toplam yeni yayın yüzeyi:**

- Kesin: 2 Topluluk gönderisi + 1 Carousel.
- Koşullu: 1 TikTok + 1 TG/BS metin.
- **YouTube'a yeni video: 0.**
- YouTube kotası: yalnız bugünkü kapak telafisi (100 birim, CLI seçilirse).

### 5b. Just Relax — mevcut DJ seti (T0 = 2026-09-07 16:18, deep house, 41:04)

Plan süpürgesi T0'ı 72 saatten eski projeleri **otomatik planlamaz** (geriye dönük dalga yok). Aşağıdaki
takvim **bugünkü kodun zaten yapacaklarını** ve önerilen elle eklemeleri gösteriyor.

| # | Tarih | Saat | Platform | İçerik | Hazırlık durumu | Kota | Not / çakışma |
|---|---|---|---|---|---|---|---|
| 1 | 14 Eyl Pzt | 10:15 | YouTube Studio | Ayın 2. Pazartesi'si **telif kontrolü** (Just Relax, City Pulse, Gece Seansı) → kesit yayınının **ön şartı** | `onay_bekliyor` (elle) | 0 | `haftalik_is_akisi.md` §3 |
| 2 | 16 Eyl Çar | 19:00 | YouTube Topluluk | **E2-DJ** "Setin 3 anı" metni: 5:32 · 24:51 · 35:01 dakika damgaları + anket "hangisi?" (EN, `theme: dj`) + `cover.png` | `planlandi` → elle kit | 0 | Günde 1 türev: 14 Eyl Sabah Senin E2, 17 Eyl E3 → 16 Eyl boş ✓. Anket sonucu satır 3'teki kesit seçimine **girdi** olur (küratörlük sinyali) |
| 3 | **18 Eyl Cum** | **18:0x** | YouTube Shorts | **BUGÜNKÜ KOD, OTOMATİK:** `dj_famous_process` → `finally` → `dj_clips.supur` → Just Relax uygun (tarama temiz, Shorts'tan 11 gün, önceki kesit yok) → `kesit_sec` enerji alanı olmadığı için **dosya adı sırası** → `clip_01.mp4` (**5:32–6:17**) → private yükleme, başlık "Just Relax — Set Highlight 5:32 #Shorts" | **Planlanmamış ama gerçekleşecek** | insert 1 (ayrı kova) + playlist `list` 1 + `insert` 50 ≈ **51+** | ⚠ Setin ilk 6 dakikası (City Pulse'ta eşleşmelerin %65'i orada). ⚠ Seçim küratörlük değil dosya adı. `haftalik_is_akisi.md` §5 "`dj_clips` kapalı kalacak" diyor. **Karar sorusu 1** |
| 4 | 21 Eyl Pzt | ≈18:05 | YouTube Shorts | Satır 3'teki kesitin public anı (`_golden_publish_at(3)`: 18 Eyl 18:0x + 3 gün = pencere içinde → o an) | otomatik | 0 | Önerilen kurallarda Pazartesi 18:05 serbest (Sabah Senin türevi yok) ✓ |
| 3′ | *(öneri)* 19 Eyl Cmt | 10:15 | YouTube Analytics (okuma) | Kesit **seçimi**: izlenmenin tepe yaptığı an (`audienceWatchRatio` × `elapsedVideoTimeRatio`), ilk 6 dk hariç, anket sonucu ile birlikte → `clip_02` (24:51) ya da `clip_03` (35:01) | `planlandi` | Analytics (ayrı kota, **doğrulanmadı**) | Satır 3 durdurulursa bu yol |
| 4′ | *(öneri)* 25 Eyl Cum | 18:0x yükleme → **28 Eyl Pzt 18:05** public | YouTube Shorts | Seçilen kesit | `hazirlandi` (dosya diskte) | ≈51+ | Haftalık sayaç ✓, ±24 sa bandı yeni şarkıya göre yeniden hesaplanır |
| 5 | 26 Eyl Cmt | 19:00 | YouTube Studio | **E1-DJ bölümler** (denetim b-5): Just Relax açıklamasına ≥3 bölüm; telif aralığı bölüm adına **yazılmaz**; `update_metadata` deseni, tam snippet | `onay_bekliyor` (elle) | `videos.update` **50** | Pazartesi 10:15 kota kuralı → **28 Eyl Pzt 10:15**'e al (Cuma yok) |
| 6 | 02 Eki Cum | 19:00 | TikTok (elle) | **E8-DJ** Aynı kesit dosyası TikTok'a (koşul: YouTube kesiti 7 günde medyan Shorts'un altında değil) | `planlandi` (koşullu) | 0 | Kit tavanları (36 sa, haftada 4) ortak |
| ✗ | — | — | IG Reels kesit | — | `iptal` (§1b ertele) | — | — |
| ✗ | — | — | Tam set Shorts dizisi | — | `iptal` (§1b) | — | — |

### 5c. Yeni bir DJ seti için şablon (ör. Night Drive; ses yok, indirme K-B'ye bağlı)

D0 = temiz taramadan sonraki public anı. Göreli takvim:

| Gün | Adım | Durum kaynağı |
|---|---|---|
| D−2 sa | Private yükleme + Content ID karantinası; **bölümler açıklamaya ilk yüklemede** yazılır (ek kota 0) | `dj_famous_process` (bölüm yazımı Aşama 4) |
| D0 | Public; aynı koşuda 3 kesit render'ı (`_kesitleri_uret`); ilk saatlik koşuda plan | mevcut + süpürge |
| D+0-1 | E1 Studio işleri | kit |
| D+2 | E2-DJ "setin 3 anı" + anket | kit |
| D+7 | E5 karar + Analytics tepe anı → kesit seçimi | süpürge |
| D+7-14 (ilk uygun Cuma) | Kesit yükleme → +3 gün public | `dj_clips.supur` |
| D+14-21 | E8-DJ TikTok (koşullu) | kit |
| Yok | E3 Carousel (sözsüz set), E4 kulis (gerçek kişi: DJ Famous'un **ayrı rızası** gerekir, `dj_sets/README.md`) | — |

---

## 6. Uygulama planı (aşamalı)

**Canlı checkout kuralları** (her aşamada):

- Dosya düzenlemeleri **:00-:25 dışında** (saatlik koşu :05'te başlıyor, ~7 sn–6 dk).
- Önce **yeni modül**, sonra sarmalayıcı, **en son** `finally`'deki çağrı satırı.
- Mevcut fonksiyonlara yalnız **varsayılanlı** parametre eklenir; imza sırası değişmez.
- `import turev_takvimi` sarmalayıcının içinde, `try` altında: import zinciri bozulursa ana hat etkilenmez.
- Her yazımdan sonra `ast.parse` + kontrol karakteri taraması (`tests/test_kaynak_bayt_muhafizi.py`).
- Test: `python -m pytest -q -p no:cacheprovider --basetemp=<scratchpad>/pytest_tmp`.
- `git reset --hard` / `clean -f` **yok**.

### Aşama 0 — Kod yok, bugün (≤30 dk, risk yok)

- Karar sorusu 1-3'ün cevapları.
- §5a satır 1 ve 5 (Studio işleri).
- Just Relax kesidi durdurulacaksa en ucuz, kod gerektirmeyen yol: `dj_sets/Just Relax/state.json`'a
  `yayin_beklet = {"sebep": "türev takvimi: kesit seçimi bekliyor", "istendi_at": …}`.
  - `dj_clips.uyumluluk_kapisi` → `uyumluluk.kontrol("yukleme")` HATA → kesit gitmez (fail-closed).
  - Yan etki: o setin TG/BS/FB/TikTok işleri zaten tamam; görünür etki yok.
  - Kaldırmak: alanı silmek.
  - **Bu bir state yazımıdır; kullanıcı onayıyla, 18 Eyl 18:00'den önce.**
- Planın dışında ama önce gelmesi gereken: `build_caption(ai_beyani=…)` TypeError'ının sahibine iletilmesi.
  Sabah Senin TikTok/FB ve 6 TikTok işareti buna bağlı.

### Aşama 1 — Salt plan ve görünürlük (en yüksek değer / en düşük risk)

Hiçbir şey yayınlamaz, render etmez, Telegram'a göndermez. Yalnız `turev_plani` yazar ve raporlar.

| | |
|---|---|
| **Dosyalar** | **Yeni** `turev_takvimi.py`: `TUR_TANIMLARI` (E1-E9 göreli gün, platform, risk, `en_gec`), `plan_uret(proje, simdi=None)`, `kapilar(proje, kayit, simdi=None)`, `koruma_bandi(klasorler, simdi=None)`, `takvim(gun=7, simdi=None)` (salt okuma; pano/rapor/sesli asistan için), `sirasi(log=print, simdi=None, yayinla=False)`. `yayinla=False` bu aşamada sabit; adım 3 hiç çalışmaz. **`auto_process.py`**: `_turev_takvimi()` sarmalayıcı (desen `_tiktok_kit_sirasi`) + `finally`'de `_tiktok_kit_sirasi()`'dan sonra tek satır. **`weekly_report.py`**: `BUGÜN/YARIN TÜREV` bloğu ve haftalık `TÜREVLER`. **`saglik_kontrol.py`**: `turev_takvimi_saglik()` (onuncu adım, CLAUDE.md sayısıyla birlikte) |
| **Testler** | `tests/test_turev_takvimi.py`: plan deterministik (aynı girdi → aynı id/tarih); `yayin_beklet` → yayın yok ama hazırlık serbest; `kopya_notu`/telif → hepsi iptal; ±24 sa bandı; günde 1; aynı şarkı 48 sa; `en_gec` → iptal; bozuk `durum` → fail-closed; `uyumluluk` çökerse ilerleme yok. `ast` testleri: (a) `finally`'de `_turev_takvimi` `_tiktok_kit_sirasi`'dan sonra ve `_release_lock`'tan önce; (b) `_is_fully_done` anahtar demeti **değişmedi**; (c) `UPLOAD_TIMESTAMP_KEYS` / `YENI_YAYIN_*` türev anahtarı içermiyor; (d) `process_project` gövdesinde `turev` geçmiyor. `conftest`: state yazımı `tmp_path`'e; gerçek `projects/` yazılmıyor (`PYTEST_CURRENT_TEST` koruması, `elle_islem` deseni) |
| **Risk** | Düşük. Tek yazım yeni bir state anahtarı, `state_io` ile. DJ kilidi tazeyken `dj_sets` atlanır |
| **Süre** | ~1 ajan günü (modül ~300 satır + 12-15 test) |
| **Canlı doğrulama** | Bir sonraki yeni şarkının ilk koşusunda log'da "türev: plan 1" satırı; ertesi gün günlük raporda blok |

### Aşama 2 — Elle türev kitleri ve defter (E1, E2, E3, E4)

| | |
|---|---|
| **Dosyalar** | **Yeni** `upload/turev_kiti.py` (`tiktok_yayin_kiti` deseni: `build_kit`, `kit_mesajlari`, `--onizle`; tempo `config.TUREV_KIT_*`; ana şalter `config.TUREV_KIT_AKTIF = False` ile başlar). **Yeni** `turev_kartlari.py`: Carousel PNG'leri (ffmpeg, `generate_cover._basligi_sigdir` ölçümlü sığdırma; drawtext satır sonu tuzağı `DRAWTEXT_SATIR_SONU`). `elle_islem.py`: `ISLEMLER["turev_yayinladi"]`, `_state_yansit` yeni eşleme (`kanit` id doğrulaması). `.hermes/skills/turev-yayin-onayi` (repo içi beceri). `turev_takvimi.sirasi(yayinla=…)` elle türevler için kit adımı |
| **Testler** | Kit mesajlarında "Suno" yok, AI vurgulu hashtag yok (`test_ai_beyan_satiri` deseni). Carousel caption'da `AI_BEYAN_SATIRLARI` var. `turev_yayinladi` **`isaretle_yayinlandi` çağırmıyor** (mock). Bilinmeyen id → RED, defter yazılmaz. Şalter kapalıyken hiç gönderim/yazım yok. Başlıklar `notify` JSON gövdesiyle (`test_notify_turkce_baslik` taraması yeni çağrıları da kapsar). Kart render'ı kontrol karakteri içermiyor |
| **Risk** | Orta: `elle_islem` sözlüğü panonun okuduğu sözleşme; pano sahibine haber verilmeli. Telegram yayın kanalına sızma → `_telegram_ayari` kapısı |
| **Süre** | ~1,5 gün |

### Aşama 3 — Render hazırlığı ve D+7 kararı (E5, E8 dosyası)

| | |
|---|---|
| **Dosyalar** | `turev_takvimi.py`: hazırlık adımı (golden dışı + priz + koşu başına 1). **Yeni** `guc_durumu.py` (`GetSystemPowerStatus`, bilinmiyor → pil). Şarkı kesiti için `dj_clips.clip_uret(set_dir, count=3, dry_run=False, cikti_adi="clip_%02d.mp4", state_anahtari="dj_clips")`: **varsayılanlı** iki parametre; şarkı için `"turev_kesit_%02d_9x16.mp4"` ve `"turev_kesitleri"`. Varsayılanlar bugünkü davranışı birebir korur. D+7 karar fonksiyonu (katalog D+7 medyanı, `weekly_report._izlenme_katalogu` okunur, kopyalanmaz) |
| **Testler** | Golden-hour içinde render çağrılmıyor; pil/bilinmiyor → render yok; `en_gec` <24 sa → pilde render; `clip_uret` varsayılan çağrısı eski state anahtarını/dosya adını üretiyor (geriye uyum); karar eşikleri; karar yalnız E8/E9'u değiştiriyor |
| **Risk** | Orta: `dj_clips` imzası (varsayılanlı). CPU: render finally'de kilidi ~3 dk tutar; golden dışı olduğu için IG drain etkilenmez |
| **Süre** | ~1,5 gün |

### Aşama 4 — DJ kesit entegrasyonu ve otomatik türevler (E7, E8 kiti, E9)

| | |
|---|---|
| **Dosyalar** | `dj_clips.yayina_uygun_mu(set_dir, simdi=None, st=None, takvim_kapisi=None)`: varsayılan `None` → bugünkü davranış; `dj_famous_process._kesit_yayini` `turev_takvimi.kesit_kapisi`'ni geçer (bant + haftalık ortak sayaç). `ILK_DAKIKA_YASAGI_SN = 360` (telif, set başı). Analytics tepe anı seçimi (enerji sırasına fail-soft düşer). `tiktok_yayin_kiti._tempo_engeli(durumlar, t, ek_damgalar=())`. `ek_platform_backfill._damga_anahtarlari` türev damgalarını da sayar. TG/BS metin hatırlatması. DJ bölümlerinin ilk yüklemede açıklamaya yazılması (`build_snippet` DJ dalı) |
| **Testler** | `test_dj_kesit_yapisal_sinir` hâlâ geçiyor (set başına 1). İlk 6 dk kesidi elenir. Bant içinde kesit gitmez. Takvim kapısı çökerse kesit gitmez (fail-closed). Kit tavanı türevle dolunca ana kit bekler. TG/BS günlük tavanı türev + backfill toplamını sayar. `dj_famous_process` ast sırası (kapı `supur` içinde) |
| **Risk** | **Yüksek**: yayın yapan yol, gerçek kişi içeriği, Content ID. Önce `--yayin-kuru` ile bir hafta kuru koşu |
| **Süre** | ~2 gün + 1 hafta kuru gözlem |

### Aşama 5 — Opsiyonel, 09 Eki ölçümünden ve K-D kararından sonra

- Instagram Carousel'in API ile otomatik yayını. `instagram_upload` Netlify barındırma deseni;
  çocuk konteynerler + `CAROUSEL`; 23 sa konteyner ömrü kuralı aynen.
- Şarkı kesitinin YouTube'a açılması: yalnız K-D "Shorts kalsın" derse.

---

## 7. Kullanıcıya sorulacak kararlar

1. **Just Relax kesidi 18 Eylül Cuma 18:0x'te bugünkü kodla otomatik yüklenecek** (5:32 anı,
   küratörlüksüz seçim, ≈21 Eyl 18:05 public). İzin mi, durdurma mı?
   **Önerim: durdur** (Aşama 0, `yayin_beklet`). Kesit, anket + Analytics tepe anı ile ilk 6 dk
   dışından seçilip bir sonraki haftaya kalsın. `haftalik_is_akisi.md` "dj_clips kapalı" kararıyla da tutarlı.
2. **Türevler 52 saatlik tabana sayılmasın mı** (günde 1, haftada 1 YouTube türevi, yeni şarkıya
   ±24 sa bant ile)?
   **Önerim: sayılmasın**, bu ayrı tavanlarla.
3. **Şarkılar için YouTube'a ikinci kesit Short** 09 Ekim ölçümüne ve Shorts kararına (K-D) kadar kapalı kalsın mı?
   **Önerim: kapalı.** İkinci kesit yalnız TikTok'a ve yalnız D+7 "aç" kararıyla.
4. **Topluluk gönderisi ve Instagram Carousel elle mi** (Telegram kiti + "yayınladım" onayı), yoksa
   Carousel API ile otomatik mi?
   **Önerim: ilk ay elle.** Topluluk için zaten API yok; Carousel otomasyonu ölçümden sonra.
5. **Kulis gönderileri** (söz yazım süreci, reddedilen taslaklar) herkese açık paylaşılabilir mi? DJ
   Famous için gerçek kişinin ayrıca onayı alınsın mı?
   **Önerim: ana katalogda evet, her metin elle onaylı. DJ Famous'ta ayrı onay gelene kadar yok.**
6. **TikTok ikinci kesit ve TG/BS hatırlatması mevcut günlük tavanlara (1) dahil olsun mu?** Bu,
   geri doldurmayı birkaç gün yavaşlatabilir.
   **Önerim: dahil.** "Günlük desen" riski tavanı yükseltmekten pahalı.

---

## 8. Doğrulanmayanlar

- Yeni biçimde 45 sn dikey kesit render süresi (~3 dk bugünkü tek ölçümden orantı). Bugünkü 17 dk'nın ne kadarı kapak/backdrop.
- `find_highlights`'ın 41 dk'lık set sesindeki süresi.
- Analytics `elapsedVideoTimeRatio` eğrisinin 7 günlük veriyle bir sette anlamlı olup olmadığı ve Analytics kota tüketimi.
- `notify`'da Telegram'a video/belge gönderen fonksiyonun varlığı (yalnız `send_photo`/`send_text` doğrulandı, CLAUDE.md (f)).
- Meta'nın aynı sesin ikinci Reels'ini "özgün olmayan içerik" sayıp saymadığı.
- YouTube'un aynı uzun videodan birden çok Shorts'u nasıl değerlendirdiği: resmî politika bu durumu açıkça anmıyor (§9).
- Sabah Senin playlist eklemesinin sonraki koşularda yeniden denenmesi (denetimde de belirsiz).
- D+7 medyan eşiğinin anlamlılığı (gürültü tabanı 21,2 puan; eşik bir **sınıflandırma** kolaylığı, ölçüm değil).
- `upload_clip`'in kapak (`thumbnails.set`) çağırıp çağırmadığı; kesit kotası buna göre 51 ya da 101 birim.

## 9. Kaynaklar (resmî, 2026-09-13'te okundu)

- **YouTube kanal para kazanma politikası — reused / inauthentic content:** <https://support.google.com/youtube/answer/1311392>
  - Reused: "without adding significant original commentary, substantive modifications".
  - Inauthentic: "content that is repetitive or mass-produced".
  - Klip/derleme: "reviews content like commentary, clips, compilations, and reaction videos".
  - Aynı videodan çoklu Shorts'u **ayrıca anmıyor**.
- **YouTube Data API v3 kaynak listesi:** <https://developers.google.com/youtube/v3/docs>
  - 21 kaynak arasında Topluluk/Posts kaynağı **yok**, yani gönderi API'den oluşturulamıyor.
- **YouTube Posts (Topluluk) yardım sayfası:** <https://support.google.com/youtube/answer/9409631>
  - Studio'da zamanlama var: "scheduled posts for a future publish date".
  - Çocuklara özel ya da gözetimli kanalda yok.
- **Instagram içerik yayınlama:** <https://developers.facebook.com/docs/instagram-platform/content-publishing/>
  - "up to 10 images, videos, or a combination".
  - "Carousels count as a single post".
  - 24 saatte 100 API gönderisi.
- **IG User Media (Carousel konteyneri):** <https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media>
  - `media_type=CAROUSEL`, `children` ≤10.
  - "Reels cannot appear in carousels."
- **Kota maliyetleri:** <https://developers.google.com/youtube/v3/determine_quota_cost>
- **YouTube Data API revizyon geçmişi** (insert ayrı kova): <https://developers.google.com/youtube/v3/revision_history>
- **Shorts ilgili video:** <https://support.google.com/youtube/answer/14075157>
- **Bölümler (chapters):** <https://support.google.com/youtube/answer/9884579>
- **AI beyanı:** <https://support.google.com/youtube/answer/14328491>
