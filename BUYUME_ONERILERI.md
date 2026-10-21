# Büyüme Önerileri — Kayıt ve Sabitleme

17 maddelik güç listesinin uygulama kaydı. Kural: yeni madde eklenirken
buraya satır + `tests/test_buyume_onerileri.py`'ye test eklenir.
Test kızarmadan davranış değişmez. Bayraklar `config.py` BÜYÜME bölümünde —
kapatmak silmek değil, `False` yapmak.

| # | Madde | Durum | Kod | Test |
|---|-------|-------|-----|------|
| 1 | Başlık `{artist}` ile başlar | ✅ sabit | `config.py DJ_SERIES.title_format` | `test_seri_basliklari_sanatciyla_baslar` |
| 2 | Sabitlenmiş yorum soru+timestamp | ✅ süreç | `yorum_gonder.py` + `ILK_YORUM_SORULARI` | — (operasyonel) |
| 3 | Shorts→uzun video funnel | ✅ sabit | `auto_process.py` `upload_short(..., youtube_video_id, ...)` | `test_shorts_funnel_kablolu` |
| 4 | AI beyanı videoda YOK, metadata+a can açıklamada VAR | ✅ sabit | `youtube_upload.py` (`containsSyntheticMedia` + `AI DISCLOSURE`), videoda overlay yok | `test_videoda_ai_pikseli_yok`, `test_aciklamada_ai_beyani_var` |
| 5 | Yükleme golden-hour'da | ✅ süreç | `config.next_golden_publish_time`, `--no-schedule` sadece acil | — (operasyonel) |
| 6 | Cold-open: ilk saniyelere highlight ön tadı | ✅ sabit | `render.py` + `ffmpeg_utils.render_video(cold_open=...)`, `COLD_OPEN_*` | `test_cold_open_concat_kablosu`, `test_chapters_ffmeta_icerik_ve_ofset` |
| 7 | Görsel nabız (~25sn'de vurgu) | ✅ sabit | `ffmpeg_utils` nabız ifadesi (ana + shorts), `GORSEL_NABIZ_*` | `test_gorsel_nabiz_iki_filtrede` |
| 8 | Thumbnail 3 eleman, landmark ≤4 kelime | ✅ sabit | `cover_generator._add_series_title_text` | — (görsel; kural burada kayıtlı) |
| 9 | Chapter başlıkları duygulu, yer tutucu yok | ✅ sabit | `validate_project` UYARI (render durmaz) | `test_yer_tutucu_tracklist_uyarisi` |
| 10 | Bitiş kartı son 15sn (`end_card_text` varsa) | ✅ sabit | `ffmpeg_utils` `end_card_text`, `END_CARD_SURE_SN` | `test_cta_ve_end_card_kosullu` |
| 11 | Abone CTA %40'ta 1 kez, rutin vaat | ✅ sabit | `ffmpeg_utils` `cta_text`, `ABONE_CTA_*` + `ABONE_CTA_METIN` | `test_cta_ve_end_card_kosullu` |
| 12 | Seri takvimi şaşmaz | ✅ süreç | `yayin_ritmi.py`, `DJ_SERIES.schedule` | — (operasyonel) |
| 13 | İlk 2 saat yorum cevabı | ✅ süreç | operasyonel (üretici aktif sinyali) | — (operasyonel) |
| 14 | Türkçe mekan hikayesi (`story_tr`) | ✅ sabit | `youtube_upload.build_dj_set_snippet` `MEKAN HİKAYESİ` | `test_story_tr_aciklamada` |
| 15 | Kültür-kod stilleri | ✅ sabit | `config.SET_STILLERI`: `arabesk_trap`, `nineties_nostalji` | `test_kultur_kod_stilleri` |
| 16 | TikTok/IG'ye ses olarak açılma | ✅ süreç | `USE_LINES` havuzu caption'larda | — (operasyonel) |
| 17 | Tek değişiklik + ölçüm | ✅ süreç | `olcum_temel_cizgi.py --cek` her değişiklik öncesi | — (operasyonel) |

P0 altyapısı (rapor): chapter gömme (`render.py`+`ffmpeg_utils`), seri kapağı
(`cover_generator.py`), Shorts native filtre (`ffmpeg_utils`), açıklama AI satırları.

## Gelişime açık kapılar
- `end_card_text`: meta'ya yazılınca otomatik çıkar (şu an opsiyonel).
- `story_tr`: DJ set lokasyonlarına eklendikçe açıklamaya düşer.
- Cold-open süresi `COLD_OPEN_SURE_SN` ile, nabız `GORSEL_NABIZ_*` ile ayarlanır.
- Yeni seri eklenince: `DJ_SERIES` + `SERIES_THUMBNAIL_TEMPLATES` + buraya satır + test.

---

## Abone Motoru (2026-10-20) — 18–24

Kanalın en büyük eksikliği abone: 47 abone / 9.408 izlenme (%0.5 dönüşüm).
Depoda birbirinden BAĞIMSIZ çalışan abone kaldıraçları vardı; hepsi tek
akışta birleştirildi. Kaldıraçlar birbirinin yerine geçmez, birbirini
TAMAMLAR.

| # | Madde | Durum | Kod | Test |
|---|-------|-------|-----|------|
| 18 | Kanal watermark'ı (abone butonu, sağ alt) | ✅ sabit | `upload/youtube_abone.py::watermark_uygula` — `watermarks.set` | `test_watermark_kanal_seviyesinde`, `test_watermark_gorseli_uretilir` |
| 19 | Sabitlenen ilk yorum (soru + abone) | ✅ sabit | `upload/youtube_ilk_yorum.py::gonder` + `social_text.build_ilk_yorum` | `tests/test_youtube_ilk_yorum.py` (7) |
| 20 | Açıklamada @handle (tıklanabilir) | ✅ sabit | `social_text.aciklama_abone_bloku` → `youtube_upload` (uzun/Shorts/DJ) | `test_aciklama_abone_bloku_handle_icerir`, `test_uzun_video_aciklamasinda_handle`, `test_shorts_aciklamasinda_handle`, `test_dj_set_aciklamasinda_handle` |
| 21 | Playlist linkleri açıklamada | ✅ sabit | `social_text.aciklama_abone_bloku` (playlist_ids.json'dan) | `test_aciklama_abone_bloku_playlist_linkleri` |
| 22 | Kanal bölümü "Abonelik" | ✅ sabit | `upload/youtube_abone.py::kanal_bolumu_kur` — `channelSections.insert` | `test_aciklama_abone_bloku_playlist_ids_dosyasindan` |
| 23 | Kanal banner'ı (abone mesajı) | ✅ sabit | `upload/youtube_abone.py::kanal_banneri_kur` — `channelBanners.insert` | — (görsel; kural burada kayıtlı) |
| 24 | Yabancı kanal handle'ı yasak | ✅ sabit | `config.SOCIAL_LINKS['youtube']` (9 modül düzeltildi) | `test_youtube_linki_yabanci_sanatci_handle_iceermez` |

### Uygulanan API çağrıları (2026-10-20)
- `watermarks.set` — **kanal seviyesi** (video başına değil). 1 çağrı = 24 video.
  Gövde şeması `InvideoBranding` (imageBytes + timing + targetChannelId), `media_body` zorunlu.
- `commentThreads.insert` — 21 videoya ilk yorum gönderildi (3 video silinmiş, işaretlendi).
- `channelSections.insert` — "Abonelik" bölümü oluşturuldu (`multiplePlaylists` + `contentDetails.playlists`).

---

## Site Büyüme Motoru (2026-10-20) — 25–27

YouTube Studio 5 manuel görevi API + tarayıcı ile otomatikleştirildi. Aynı
gün "site/index.html" production-ready hale getirildi ve 3 yeni büyüme kaldıracı
eklendi.

| # | Madde | Durum | Kod | Test |
|---|-------|-------|-----|------|
| 25 | AI Tarz Seçici ("hangi ruh halindesin?") | ✅ sabit | `config.TARZ_SECICI_ACIK` + `TARZ_SECICI_TONUZLER`, `site/index.html` `#tarz-secici` | `test_tarz_secici_config_ve_site` |
| 26 | YouTube kanal bağlantıları (5 link) | ✅ sabit | `youtube_studio_setup_api.py::CHANNEL_LINKS` (UI gerekliydi, `brandingSettings` yazmıyor) | `test_kanal_baglantilari_tam` |
| 27 | Kanal açıklaması 6-satır şablon | ✅ sabit | `youtube_studio_setup_api.py::CHANNEL_DESCRIPTION` | `test_kanal_aciklamasi_sablonu` |
| 28 | Site analitik (cookie-less, self-hosted) | ✅ sabit | `site/analytics.js` + `site/api/analytics.py` + `config.ANALITIK_*` | `test_site_analytics_config_eslesik`, `test_site_analytics_privacy_kurallari`, `test_site_analytics_endpoint_dosyasi_var`, `test_daily_analytics_site_verisini_okur` |
| 29 | Topluluk (Discord + Telegram + abonelik listesi) | ✅ sabit | `topluluk.py` + `site/api/topluluk.py` + `config.TOPLULUK_*` | `test_topluluk_modulu_calisiyor`, `test_topluluk_endpoint_dosyasi_var`, `test_topluluk_site_baglanti`, `test_topluluk_ayri_veri_klasoru` |
| 30 | Site deploy (Netlify + GitHub Pages) | ✅ canlida | `netlify.toml` + `netlify/functions/*.js` + `site/*` + `publish_site_github.py` | `test_netlify_toml_gecerli`, `test_site_deploy_dosyalari_var`, `test_site_icer_linkleri_hedefleri_var`, `test_api_cors_kisitli`, `test_site_api_base_yapilandirilabilir` |
| 31 | Dil toggle (TR/EN) | ✅ sabit | `site/i18n.js` + `config.SITE_DIL_*` + `site/index.html` `data-i18n` | `test_site_i18n_dosyasi_var`, `test_site_i18n_anahtar_sayilari_esit`, `test_site_i18n_data_anahtarlari_sozlukte_var`, `test_site_i18n_toggle_butonlari_var`, `test_site_js_dengesi_bozulmamis` |

### Kural notları (31) — Dil toggle (TR/EN)
- **Varsayilan TR** (hedef kitle). Tarayici dili `en` ise ilk ziyarette EN
  acilir; secim `localStorage`'da (`fms_dil`) saklanir.
- **`localStorage` yalnizca KULLANICI TERCİHI icindir** (dil secimi) — Madde 28
  analitigi bu veriyi toplamaz. Bu bir "takip" degildir.
- Sözlük: `site/i18n.js` → `S.tr` / `S.en`. **İki tabloda aynı anahtarlar
  olmalı** → `test_site_i18n_anahtar_sayilari_esit` kilitler.
- `index.html`'deki her `data-i18n` anahtarı sözlükte olmalı →
  `test_site_i18n_data_anahtarlari_sozlukte_var` kilitler.
- **JS ile üretilen içerik otomatik çevrilmez** (data-i18n yalnız DOM
  elementlerini kapsar). Tarz seçici butonları `_tarzButonlariCiz()` ile
  `dil:degisti` olayında **yeniden çizilir**.
- **REGRESYON (2026-10-21):** i18n eklenirken bir fazla `}` ile TÜM ana
  script çöktü → tarayıcı `SyntaxError`, sayfa boş, konsolda hata vardı ama
  testler yeşildi. → `check_js_braces.py` modülü + `test_site_js_dengesi_bozulmamis`
  kilitler. **DERS: JS değişikliğinde `node --check` + tarayıcı doğrulaması.**

### Kural notları (30) — Deploy
- ✅ **CANLI:** `https://semtappdata-art.github.io/famous-music-studio/`
  (GitHub Pages, kaynak `main` → `/docs`).
- **GitHub Pages ALT-YOL servis eder** (`/famous-music-studio/`) → mutlak
  yollar 404 verir. Bu yüzden tüm iç linkler **GÖRELİ** (`privacy.html`,
  `epk/bio.html`). → `test_site_icer_linkleri_hedefleri_var` kilitler.
- **API ucu yapılandırılabilir:** `window.FMS_API_BASE` (index.html head).
  Boş = ayni-origin (Netlify root). Dolu = ayrı domain.
  → `test_site_api_base_yapilandirilabilir` kilitler.
- **GitHub Pages STATİKTİR** → `site/api/*.py` fonksiyonları ÇALIŞMAZ.
  Analitik + topluluk için Netlify/Vercel şart (login gerekir).
- **PUSH SORUNU:** repo 4.4 GB → `git push` HTTP 408 (timeout). Çözüm:
  `publish_site_github.py` — sadece `docs/` dosyalarını GitHub API ile
  yükler (blob → tree → commit → ref). Büyük pack gönderilmez, geçmiş
  değişmez. → `python publish_site_github.py [--dry-run]`
- **Netlify:** `netlify.toml` (publish=`site`, functions=`netlify/functions`).
  - **Netlify Lambda'da Python DESTEKLENMIYOR** (resmi: "you can deploy functions
    built with TypeScript, JavaScript, and Go"). Bu yuzden analitik + topluluk
    fonksiyonlari **JS** olarak yazildi (`netlify/functions/*.js`, Netlify Blobs
    v1 ile kalici depolama). Python surumleri **yerel gelistirme** icin korunur:
    `site/api/*.py`.
  - Blobs v1.6.1 API: `new Blobs({ authentication, siteID, context })` +
    `store.get(key, {type:"json"})` / `store.set(key, val, {type:"json"})`
    (`getStore` / `setJSON` v1'de KALDIRILDI).
  - Function context'inde `context.blobs` otomatik GELMIYOR -> env var gerekli:
    `NETLIFY_SITE_ID` + `NETLIFY_BLOBS_TOKEN` (secret).
  - `req.json()` text/plain govdeyle CALISMAZ -> `req.text()` + `JSON.parse()`.
  - Team varsayilani "Private for new projects" idi -> ziyaretci 401 aliyordu.
    Cozum: site `sso_login=false` (API) + team visibility "Public" (UI).
- **Canli dagitim:**
  - Statik: `https://semtappdata-art.github.io/famous-music-studio/` (GitHub Pages)
  - Statik + API: `https://famous-music-studio.netlify.app` (Netlify)
  - Site `window.FMS_API_BASE` ile API'yi Netlify'e yonlendirir.
  `/api/analytics` → `/.netlify/functions/analytics` redirect'leri.
- **CORS kısıtlı:** `Access-Control-Allow-Origin: *` yerine izinli origin
  listesi (`_cors_origin()`). Kötü origin → **boş header** (tarayıcı reddeder).
- **GitHub Actions:** `.github/workflows/deploy-site.yml` — her `main` push'unda
  otomatik deploy + **post-deploy smoke test** (sayfa 200 + `/api/analytics`
  204 kontrolu). Secret'lar: `NETLIFY_AUTH_TOKEN`, `NETLIFY_SITE_ID`.
- **Canli dagitim:**
  - Statik: `https://semtappdata-art.github.io/famous-music-studio/` (GitHub Pages)
  - Statik + API: `https://famous-music-studio.netlify.app` (Netlify)
  - Site `window.FMS_API_BASE` ile API'yi Netlify'e yonlendirir.
- **TEK KOMUTLU DEPLOY (2026-10-21):** `python deploy_site.py`
  1. Testler (62) — hata varsa DURUR
  2. JS/HTML brace denetimi
  3. `config` -> `analytics.js` senkronu
  4. Netlify deploy (statik + API fonksiyonlari)
  5. Post-deploy smoke test (sayfalar 200 + API 204/200)
  6. GitHub Pages publish (`docs/`)
  Sure: ~110 sn. **GitHub Actions'a GEREK YOK.**
- **GITHUB ACTIONS KULLANILAMAZ (2026-10-21):** PAT'te `workflow` scope yok ->
  GitHub workflow dosyasi push'unu reddediyor ("refusing to allow an OAuth App to
  create or update workflow ... without `workflow` scope"). Cozum: PAT'e
  `workflow` scope ekle VEYA `gh auth refresh -s workflow` (device flow).
  `deploy_site.py` bu gereksinimi **ortadan kaldirir**.
- **PUSH ENGELI (cozuldu):** repo 4.4 GB + 872 MB `audio.wav` -> GitHub'in
  100 MB/dosya limitini asiyordu. `git filter-branch` ile gecmisten uretim
  medyasi + credential dosyalari (`upload/token.json`, `.env*`) temizlendi.
  Artik `git push` calisiyor.
- **`.gitignore` TUZAKI (2026-10-21):** `.github/` kalibi workflow
  dosyalarinin hic commit edilmesine yol aciyordu (CI hic calismadi).
- **`pytest.ini` SINIRI:** INI formatinda cok satirlı deger desteklemez ->
  `collect_ignore` `pytest.ini`'de CALISMAZ; `conftest.py`'ye tasindi.
- **GIZLI ANAHTAR SIZINTISI (2026-10-21):** `.env.template` icinde 13 gercek
  API anahtari vardi (OpenRouter, Together, Google, HF, Runway, Higgsfield,
  Stability, Luma, Pika, Kling, MiniMax, Haiper, Postwire) + history'de
  YouTube OAuth token'i. Hepsi placeholder yapildi, gecmisten temizlendi.
  **!! Bu anahtarlar rotate EDILMELI (dashboard'dan yenisi alin).**

- **OTOMATIK DEPLOY TETIKLEYICISI (2026-10-21):** `site_deploy_watch.py`
  `watch_projects.py` gorevine baglandi (dakikalik calisan mevcut gorev —
  **YENI GOREV OLUSTURULMADI**, CLAUDE.md §2'ye uygun).
  - `site/` veya `netlify/functions/` degistiginde `deploy_site.py` calisir
  - Korumalar: gunde maks 12 deneme · 30 dk kilit · debounce · ilk calistirmada
    sadece imza kaydeder (deploy yapmaz) · basarisizlikta sonraki dakikada
    yeniden denenir
  - Log: `logs/site_deploy.log` · imza: `logs/site_deploy_imza.txt`
- **GUVENLIK (2026-10-21) — SIZAN ANAHTARLAR ROTATE EDILMELI:**
  `.env.template` icinde 13 gercek API anahtari vardi (OpenRouter, Together,
  Google, HuggingFace, Runway, Higgsfield, Stability, Luma, Pika, Kling, MiniMax,
  Haiper, Postwire) + history'de YouTube OAuth token'i. Hepsi placeholder yapildi
  ve gecmisten temizlendi, ama **anahtarlar hala gecerli olabilir**.
  Dashboard'dan yenisini alip degistir:
    OpenRouter  : https://openrouter.ai/keys
    Together   : https://api.together.xyz/settings/api-keys
    Google     : https://aistudio.google.com/app/apikey
    HuggingFace: https://huggingface.co/settings/tokens
    Postwire   : https://app.postwire.io
    Runway / Higgsfield / Stability / Luma / Pika / Kling / MiniMax / Haiper

- **Madde 31 (2026-10-21) — TÜM SAYFALAR TR/EN:** `site/privacy.html`,
  `site/epk/bio.html`, `site/404.html` artık `i18n.js` + `i18n.css` ile
  iki dilli; ana sayfada 96 olan anahtar sayısı **177**'ye çıktı (TR/EN eşit).
  - Ortak `site/i18n.css` (toggle tek kaynak) + her sayfaya dil toggle
  - `i18n.js` artık `textContent` değil **güvenli HTML** yazıyor:
    `<strong>/<a>/<br>` render edilir, `&amp;` çözülür;
    `script`/`on*`/`javascript:` temizlenir (XSS koruması)
  - `epk/bio.html` `../i18n.js` kullanır (alt klasör yolu)
  - Test: `tests/test_i18n_pages.py` (yeni sayfa eklenince kırılır)
- **Madde 32 (2026-10-21) — MODÜL KURTARMA:** 7 kritik modül
  (`generate_cover`, `derleme`, `saglik_kontrol`, `stock_art`, `dj_clips`,
  `dj_tarama_kontrol`, `weekly_report`) + 49 test dosyası (22.270 satır)
  `git filter-branch` sırasında silinmişti → geri getirildi.
  - `conftest.py` artık **dinamik**: eksik modül VE eksik attribute tespiti
  - `tests/test_kurtarma_kurallari.py` (15 kural) regresyon koruması
  - Düzeltilen uyumsuzluklar: sentry opsiyonel, `find_highlights` (çoklu),
    `ApprovalResult.__getitem__`, tempo tabanı 28→**52 saat** (CLAUDE.md §14),
    `UPLOAD_TIMESTAMP_KEYS` 4 platform, günlük pencere yeni şarkıda da

- **Madde 33 (2026-10-21) — TRUE-PEAK LIMITER + RENDER BÜTÜNLÜĞÜ:**
  YouTube algoritması için iki kritik özellik uygulandı (eksik API listesi
  20 → 11'e indi):
  - `ffmpeg_utils.ses_olc()` — ebur128 ölçümü (LUFS/TP/LRA). Değerler
    **"Summary:" bloğundan** okunur (ara satırlar anlamsız). `-inf` (sessiz
    dosya) geçersiz sayılır.
  - `ffmpeg_utils.limiter_filtresi()` — `aresample=192000,alimiter=limit=-2dB:
    level=false:attack=5:release=50,aresample=48000`. **loudnorm/dynaudnorm
    KULLANILMAZ** (tek geçişli loudnorm pompalamaya yol açar).
  - `render.limiter_gerekli()` — `tp > SES_TP_ESIK_DBTP` **KATI** (-1.0 dBTP);
    tam sınırda limiter alınmaz. Ölçüm yoksa limiter **GİRMEZ** (iyileştirme,
    kapı değil) ama UYARI **görünür**.
  - Ölçüm **MD5 ile önbelleklenir**; `state.json` **yoksa oluşturulmaz**,
    bozuksa **üstüne yazılmaz**.
  - `render.video_butun_mu()` — 0 bayt kapısı + ffprobe süre doğrulaması.
    "Çalıştıramadım" (FileNotFoundError → zarif düşüş, **tek** uyarı) ile
    "çalıştırdım, bozuk" (RuntimeError → bozukluk kanıtı) **ayrı**.
  - `auto_process._is_rendered()` / `dj_famous_process._is_rendered()` —
    iki üretim girişinde **aynı ölçüt** (kopya mantık yok).
  - `render.find_highlight()` — **HİÇBİR ZAMAN tanımlı değilmişti**,
    `render_project` çağırıyordu → NameError. Artık var (enerji penceresi).
  - `render.PARCALI_SONEK` + `os.replace` — ffmpeg **nihai adı hiç görmüyor**;
    yarım render diskte `youtube_16x9.mp4` adıyla kalmıyor.
  - Test: `tests/test_kurtarma_kurallari.py` (+10 kural)

- **Madde 34 (2026-10-21) — KESİT YAYIN HATTI + AÇILIŞ ÖLÇÜMÜ:**
  Eksik API listesi **20 → 7**'ye indi.
  - `youtube_upload.build_clip_snippet()` — kesit başlığı **dakika damgasıyla**
    ("5:32") setin kendi Shorts'undan **FARKLI** → "inauthentic content"
    riski kapatılır. Video id yoksa **kırık link basılmaz**.
  - `youtube_upload._dakika_damgasi()` — saniye → "M:SS" (kesme, negatif→0:00)
  - `youtube_upload.upload_clip()` — kesiti **ertelenmiş golden hour**'a yükler
  - `youtube_upload._golden_publish_at(gun)` — **None tuzağı** engellendi:
    golden-hour içindeki bir an "zamanlama yok"a çevrilirse kesit BUGÜN
    yayınlanır ve 3 günlük erteleme **tamamen** kaybolur.
  - `dj_clips.kesit_sec()` / `kesit_yayinla()` / `supur()` — en enerjili
    kesit seçimi, **tekrar gönderimi engelleyen** state (ayrı anahtar ailesi:
    `youtube_clip_*`), iki kapının (küresel tempo + set) bağımsızlığı
  - `ffmpeg_utils.bastaki_sessizlik()` — `INTRO_SESSIZLIK_PAY` (0.12 sn)
    düşülür, `INTRO_SESSIZLIK_MAKS` (3 sn) tavanı; bozuk dosyada **0.0**
  - `render.find_intro_cover()` — orana göre `cover.png` / `cover_vertical.png`

- **Madde 35 (2026-10-21) — AÇILIŞ INTRO'SU (kapak + sessizlik kırpma):**
  İzleyici kaybının büyük kısmı videonun **ilk %1-%3'ünde** (≈2.-7. saniye)
  yoğunlaşıyor (ölçüm: `olcum_temel_cizgi.json`). Bu aralık artık kapatıldı:
  - `ffmpeg_utils.bastaki_sessizlik()` — `PAY` (0.12 sn) düşülür, `MAKS` (3 sn)
    tavanı; ölçüm arızalıysa **kırpma yapılmaz** (şarkının başı yemez)
  - `render.find_intro_cover()` — orana göre `cover.png` / `cover_vertical.png`
  - `ffmpeg_utils._build_filter_complex(intro_index, hud_index)` — kapak
    dalı: `trim → fade(in) → fade(out, alpha=1) → overlay(eof_action=pass)`.
    **Etiket dengesi** zorunlu (her ara etiket tam 2 kez) — dengesizlik
    ffmpeg'de "Cannot find a matching stream" verir ve TÜM render'ları öldürür
  - Çok kısa parçada kapak video'nun yarısından fazlasını kaplayacağı için
    **intro atlanır** (`intro_sure * 2 <= duration`)
  - `render_video(intro_cover=...)` + başındaki sessizliğin `-ss` ile kesilmesi
  - `backdrop_video` — DJ setlerinde (backdrop.mp4) Shorts highlight
    **kullanılmaz**, tam ekran long format çalışır (2026-09-24 kararı)

- Detayli rehber: `site/DEPLOY.md`.

### Kural notları (29) — Topluluk
- **3 KANAL:** `discord` + `telegram` + `ntfy` (sirasi `config.TOPLULUK_KANALLAR`).
  - **Discord = WEBHOOK** (token yok, kanal yonetimi gerekmez). Kurulum:
    `Settings > Integrations > Webhooks > New Webhook` → URL'i
    `topluluk_config.json`'a yaz.
  - **Telegram** mevcut bot token'ini kullanir (`upload/telegram_client_secrets.json`).
  - **ntfy** (2026-10-21) — **Discord bu agdan TAMAMEN erisilemez**
    (`ERR_CERT_AUTHORITY_INVALID` / `ERR_CONNECTION_TIMED_OUT`), Telegram icin
    gercek bot token'i gerekir (BotFather + 2FA). ntfy ise: erisilebilir,
    **token gerektirmez**, telefona **anlik push** gonderir, projede zaten
    kuruludur (`notify.py` + `notify_config.json`).
    - Topic: `fms-t38y77gjd6r7a7h649mb16w2` (`config.TOPLULUK_NTFY_TOPIC`)
    - Site'de **"Anlik Bildirim"** karti: tiklayinca tarayici bildirim izni
      ister + ntfy sayfasi acilir (abonelik). Kurulum gerekmez.
  - **NTFY BASLIK ASCII'YE CEVRILIR** — HTTP header'lar latin-1'dir; Turkce
    karakter/em-dash header'da `UnicodeEncodeError` patlatir. Gorunen metin
    degismez, sadece header temizlenir.
- **Telegram** mevcut bot token'ini kullanir (`upload/telegram_client_secrets.json`).
  **PLACEHOLDER token tespiti:** `123456789:AA...` gibi sahte token 404 doner →
  `topluluk.py` bunu algilayip token'i bos sayar ve net mesaj yazar.
- **PII ayrimi:** topluluk listesi (`analytics_data/topluluk/`) analitik ziyaret
  verisinden (`analytics_data/site/`) **AYRI** tutulur. Analitik PII toplamaz;
  topluluk listesi SADECE e-posta tutar.
- Cift kayit engellendi (aynı e-posta tekrar yazılmaz).
- Disa aktarim: `python topluluk.py disa-aktar --bicim csv|json`.
- Bildirim: `python topluluk.py bildir --baslik "..." --mesaj "..."`
  → Discord webhook + Telegram + abone logu.
- **OTOMATIK BAGLANTI (Madde 29 devam):** `auto_process.py` ve
  `dj_famous_process.py`, `upload_video` **BASARILI** olduktan hemen sonra
  `_topluluk_bildir(...)` çağırır. Yeni görev YOK — mevcut görevlerin
  upload adımına bağlandı (CLAUDE.md §2).
- **FAIL-SAFE (önemli):** bildirim hatası **yayını geri almaz**. CLAUDE.md §2
  "fail-closed" kuralı YAYIN içindir; bildirim yan etki (side-effect)
  alanıdır ve fail-OPEN olmalıdır — webhook/token kapalıysa yayın yine de
  başarılı olmalıdır. → `test_topluluk_bildirimi_fail_safe`

### Kural notları (28) — Analitik
- **PII YOK, cookie YOK, fingerprint YOK.** Sadece: tarih, sayfa yolu, referrer
  host, cihaz tipi, dil, saat dilimi, viewport. IP **kaydedilmez** (sadece
  rate-limit icin bakilir).
- **`text/plain` gonderilir** — "simple" content type oldugu icin tarayici
  PREFLIGHT (OPTIONS) yapmaz. `application/json` preflight tetikler, `sendBeacon`
  `credentials:'include'` ile gonderir ve sunucu `Access-Control-Allow-Origin: *`
  verirse **CORS reddedilir** (POST hiç ulaşmaz). Bu, ilk denemede yaşandı.
  Ders: `credentials: 'omit'` + `text/plain` = preflight yok, CORS basit.
- **Cift yazma korumasi:** ayni `path` icin 5 dakika icinde tekrar sayilmaz.
- `config.py` tek dogruluk kaynagi. Degisiklik sonrasi
  `python sync_site_analytics.py` calistir (test kilitli — senkron degilse
  `test_site_analytics_config_eslesik` kizar).
- Saglayici secimi: `self_hosted` (varsayilan) | `plausible` | `umami` | `yok`.
  Plausible/Umami icin `config.ANALITIK_PLAUSIBLE_DOMAIN` /
  `ANALITIK_UMAMI_SCRIPT` ayarla.
- Veri: `analytics_data/site/site_visits.jsonl` (30 gun saklanir).
  `daily_analytics.py` bunu okur ve gunluk rapora ekler.
- Yerel gelistirmede `config.ANALITIK_ENDPOINT = 'http://127.0.0.1:8792/'`
  gerekir (site ile endpoint farkli portta). Uretimde goreli yol yeter.

### Kural notları (25)
- **Otomatik oynatma YOK.** Suno/Chime örneğinde ses kendiliğinden çalar; bizde
  bu "spam sinyali" riski + kullanıcı şikâyeti demek. Tıklayınca çalar.
- `TARZ_SECICI_TONUZLER` **config.py** ile **site/index.html** arasında birebir
  aynı olmalı — `test_tarz_secici_config_ve_site` bunu kilitler. Sadece birini
  değiştirmek testi kırar.
- Playlist ID'leri `youtube_studio_setup_api.py` ile eşleşir
  (`PLF6EYJF61MQo`, `PLJDcZ7R6VDCY`, `PLBeK6HwnUbQ4`, `PLVkx5uln1zg8`).

### Regresyon kayıtları (2026-10-20) — iki sessiz hata
1. **`<title>` `</meta>` ile kapanmıştı.** Tarayıcı 57 KB'ın tamamını `<head>`
   içine aldı, `<body>` boş kaldı, sayfa **tamamen beyaz** render oldu. Konsolda
   hata yok. → `test_site_html_yapisi_dengeli` kilitler.
2. **`window.MUSIC_DATA` undefined.** Top-level `const` window'a eklenmez (sadece
   `var` ekler). Guard sessizce atladı → **müzik kartları hiç oluşmadı** (4 kart
   eksikti, konsolda hata yok). → `test_site_music_data_window_hatasi_yok` kilitler.
   DERS: sayfa JS'i değişikliğinde **tarayıcıda görsel doğrulama** yap —
   testler yeşil olsa bile DOM boş kalabilir.

- `channelBanners.insert` — banner güncellendi (`media_body` ile, base64 gövde DEĞİL).

### BUGFIX: `upload/http_bug_fix.py`
httplib2, GZIP'li **boş** yanıt gövdesinde `ValueError: range() arg 3 must
not be zero` fırlatıyordu. YouTube'un `watermarks.set` ucu 200 + boş gövde
döndüğü için işlem sunucuda başarılı olmasına rağmen istemcide patlıyordu.
Düzeltme: `ZlibDecoder/DeflateDecoder/LimitDecoder/DecoderProtocol.consume_bytes`
içinde `chunk_size` 0 iken 1'e sabitleniyor. Idempotent, dar kapsamlı.

### Ek kazançlar (abone dışı)
- `create_meta_files.py` artık `KeyError: location` ile TR01–TR04'te çökmüyordu.
- 50 projeye `end_card_text` eklendi → madde 10 (bitiş kartı) artık gerçekten çalışıyor.

---

## YouTube Shorts Efektleri (2026-10-20) — 25–28

Shorts'ta "müzikle uyum" YouTube'un en belirgin özelliği. Cercle / Boiler Room /
HÖR referans videolarının tamamı görselleri ritme bağlar. Depoda tek bir
görsel (art.jpg) pan + hue ile dönüyordu — ritme bağlı DEĞİLDI.

| # | Madde | Durum | Kod | Test |
|---|-------|-------|-----|------|
| 25 | Beat tespiti (librosa, cache'li) | ✅ sabit | `beat_sync.py` (`analiz_et`, `.beat_cache.json`) | `test_librosa_yoksa_hata_yok` |
| 26 | Beat sync: parlaklık flaşı + renk/pan snap | ✅ sabit | `ffmpeg_utils._build_shorts_filter_complex` (`beat_times`, `beat_period`) | `test_beat_flash_filteri_enable_icerir` |
| 27 | Hız rampası (yavaş → beat'te hızlan) | ✅ sabit | `beat_sync.hiz_rampasi_planla` + `ffmpeg_utils._build_speed_ramp_video/audio` | `test_ramp_plani_beat_e_kilitli`, `test_video_zinciri_setpts_bolme_kullanir` |
| 28 | Beat zoom punch (cut-on-beat görünümü) | ✅ sabit | `scale(eval=frame)` + sabit `crop` | `test_beat_zoom_punch_scale_eval_frame_kullanir` |

### Ölçülen doğrulama (ffmpeg + librosa ile)
- Beat flaşı ↔ ses onset farkı: **0.021 sn** (1 kare = 0.033 sn) → SENKRON.
- Hız rampası hareket oranı: yavaş 2.87 / hızlı 5.34 → **1.86x**
  (beklenen 1/0.55 = 1.82x) → doğru.
- Beat flash ölçümü: parlaklık 59.4 → 89.3 (0.14 alfa beklendiğiyle birebir).

### Öğrenilen tuzaklar (düzeltildi)
1. **`setpts='T*kat'` HIZLANDIRIR**, `atempo=kat` YAVAŞLATIR — ters yönler.
   Doğrusu: video `setpts='T/kat'` + ses `atempo=kat`.
2. **`crop` w/h ifadesi FFmpeg 9'da per-frame değerlendirilmiyor** → beat zoom
   için `scale(eval=frame)` + sabit `crop` kullanıldı (`zoompan` değil:
   zinciri yeniden yazıyor ve repoda sorun çıkarmıştı).
3. **Ramp zaman cizgisini kaydiriyor** → beat'ler de aynı eşlemeden geçirilmeli
   (`beat_sync.beatleri_zaman_esle`), yoksa flaş müzikten ayrılır.
4. **Ses zinciri de warp edilmeli** → yoksa video yavaşlar, ses hızlanır.
5. `atempo` aralığı [0.5, 2.0] — `SHORTS_SPEED_RAMP_YAVAS_KAT` bu aralıkta.

### Kapılar (config, False yapmak = kapatmak)
`SHORTS_BEAT_SYNC_AKTIF`, `SHORTS_BEAT_FLASH_AKTIF`, `SHORTS_BEAT_HUE_AKTIF`,
`SHORTS_BEAT_PAN_AKTIF`, `SHORTS_BEAT_ZOOM_AKTIF`, `SHORTS_SPEED_RAMP_AKTIF`.
