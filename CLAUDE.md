# CLAUDE.md — Famous Music Studio (KURALLAR)

Bu dosya **tek yetkili kural kümesidir**. Eski tüm kurallar silinmiştir. Bu plan onaylanmıştır.

---

## 1. MİMARİ (Basit, Dayanıklı, Ölçeklenebilir)

```
audio.wav → generate_cover.py → validate_project.py → render.py → auto_process.py
                                                              ↓
                                          upload/*.py (YouTube, TikTok, IG, FB, Telegram, Bluesky)
```

**Ayrı hatlar:** `dj_famous_process.py` (DJ setleri + derlemeler), `watch_projects.py` (klasör izleyici).

**Zamanlayıcı:** 3 görev — `pythonw.exe gorev_sarmalayici.py <script>` (saatlik auto_process, haftalık dj_famous, dakikalık watch_projects).

---

## 2. YASAKLAR (Kırmızı Çizgi — CI'da Test Edilir)

❌ `state.json` yazmak için `open(..., "w")` — **sadece `state_io.atomic_write()`**
❌ `_is_fully_done()`'a platform eklemek — **`finally` bloğuna bağla (`_drain_golden_hour_queue`)**
❌ Yeni Görev Zamanlayıcı görevi — **mevcut 3 görev `finally` bloğuna ekle**
❌ `notify.send()` dönüşünü kontrol etmeden çağırmak — **`notify.is_configured()` zorunlu**
❌ `uyumluluk.kontrol()` olmadan dış API çağırma — **render/yükleme öncesi ZORUNLU**
❌ `git reset --hard` / `git clean -f` **üretim checkout'unda** — `git status` önce

---

## 3. KRİTİK YOLLAR (Kim Ne Zaman Çağırır)

| Dosya/Fonksiyon | Ne Yapar | Tetikleyici |
|-----------------|----------|-------------|
| `auto_process.main()` | Ana orkestrasyon | Saatlik görev (`gorev_sarmalayici`) |
| `validate_project.validate()` | Sağlık + politika (render) | `render.py` her render öncesi |
| `uyumluluk.kontrol(proje, "render" \| "yukleme")` | Fail-closed politika kapısı | 7 nokta: validate, auto_process, dj_famous, ek_platform_backfill, facebook_backfill, dj_clips.yayina_uygun_mu, dj_clips.kesit_yayinla |
| `state_io.atomic_write()` | Tek atomik state yazıcısı | **Her state yazan yer** |
| `_drain_golden_hour_queue()` | Tamamlama süpürgesi | `auto_process.main()` finally |
| `gorev_sarmalayici.calistir()` | Görev wrapper (log, nabız, maske) | 3 zamanlayıcı görevi |

---

## 4. STATE YÖNETİMİ

- **Tek yazıcı:** `state_io.atomic_write()` — `.tmp` + `flush` + `fsync` + `os.replace`
- **Okuma:** `state_io.load_state()` — bozuksa `{}`, HATA (sessizce `{}` YOK)
- **Alanlar:** Sadece tanımllanmış alanlar yazılır. Yeni alan → `state_io` şeması güncellenir.

---

## 5. POLİTİKA KAPISI (`uyumluluk.py`)

- **Fail-closed:** HATA = proje atlanır, boru hattı devam eder
- **7 çağrı noktası** — hepsi `try/except` ayrı, karar veren `try` rapor yazandan bağımsız
- **Kurallar:** telif işareti, md5 kopya (dar muafiyet), derleme damgası, AI beyanı, günlük yükleme uyarısı (3)
- **Bozuk state.json = HATA**, bozuk meta.json = UYARI

---

## 6. KAPAK / VİDEO KALİTESİ (Zorunlu Standartlar)

### Kapak (`generate_cover.py`)
- **İki oran:** `cover.png` (16:9) + `cover_vertical.png` (9:16)
- **Tipografi:** Başlık **alt 1/3'te** (`h*0.75`), max `%14` punkt, **beyaz + 3px siyah outline + gölge**
- **Logo:** Sağ alt, `%15` opaklık, küçük — yazı YOK ("Famous Music Studio" yazmaz)
- **Art.jpg:** Metinsiz, Pexels (LLM query + aesthetic score) veya prosedürel bokeh fallback
- **Renk harmonisi:** Art.jpg dominant rengi → başlık outline/gölge rengi

### Video (`ffmpeg_utils.py` + `render.py`)
- **Progress bar YOK**, marquee YOK
- **Bölüm bazlı görsel:** Verse/Chorus/Bridge = farklı zoom/pan/hue (söz zamanlaması varsa)
- **Dikey hook:** İlk 1sn = en yüksek enerjili chorus kesiti + "🔊 Sesini Aç" animasyonu

---

## 7. PLATFORM STRATEJİSİ

| Platform | Zamanlama | Not |
|----------|-----------|-----|
| YouTube (uzun + Shorts) | Native (`private` + `publishAt`) | Golden hour penceresinde public |
| Instagram Reels | Kendi kuyruğu (konteyner + `media_publish`) | 23sa konteyner ömrü, bayat = sil + manuel yeniden |
| TikTok | Taslak + **Elle yayın** | `tiktok_publish_plan.py` CLI, kit/doğrulama/onay akışı |
| Facebook Reels | Native schedule | `video_state=SCHEDULED` |
| Telegram / Bluesky | Sadece `ek_platform_backfill.py` | Golden hour + günlük tavan + politika kapısı + public-anı kapısı |

---

## 8. GÖREV ZAMANLAYICI / LOG / MASKELEME

- **Wrapper:** `gorev_sarmalayici.py` — `BAŞLADI / ÇÖKTÜ+traceback / BİTTİ rc+süre` → `gorev_izleri/<script>.log`
- **Maskeleme:** `gizli_maskele.maskele()` **her log yazımında** — token/sır gizlenir
- **Nabız:** `log()` içinde `os.utime(kilit_dosyasi)` — adım listesi gerekmez
- **Bayat kilit:** `LOCK_STALE_SECONDS = 4 saat` — `O_CREAT|O_EXCL` ile atomik devralma
- **Log rotasyon:** 7 gün, `log_rotate.trim_log()` — arşiv yok

---

## 9. YENİ MODÜL / ÖZELLİK EKLERKEN (3 Soru + Test)

**Kod yazmadan önce cevapla:**
1. **Kim çağıracak?** (dosya + fonksiyon)
2. **Hangi görevden?** (3 görevden biri `finally` bloğu)
3. **Çalışmadığını nasıl anlarız?** (log satırı VEYA test)

**Sonra:** `tests/test_<kural>.py` yaz → CI gate (`tests/test_kurallar.py`)

---

## 10. TEST / CI (Windows Uyumlu)

```bash
# Tek komut (geçici klasör ayrı)
python -m pytest -q -p no:cacheprovider --basetemp="C:\pytest_tmp"

# Zorunlu testler (test_kurallar.py):
# - state_io tek yazıcı
# - _is_fully_done yasak platform
# - fail-closed 7 nokta
# - notify.is_configured kontrolü
# - gizli_maskele log içinde
# - yasak AI hashtag yok
# - kapak iki oran üretiliyor
```

**CI:** GitHub Actions — `windows-latest`, `ruff`, `mypy --strict`, `trufflehog`, `pytest` (basetemp).

---

## 11. PARA KAZANMA (Gerçekçi, Bu Yıl)

| Strateji | Başlangıç | İlk Gelir | Hedef |
|----------|-----------|-----------|-------|
| **Ko-fi + Dijital Ödül** | 2 saat | 1-2 hafta | 200$/ay |
| **DistroKid → Spotify/Apple** | 22$/yıl + 4 saat | 2-3 ay | 50$/ay |
| **Suno Referral** | 0$ | 1 ay | Kredi tasarrufu |
| **Otomasyon Şablon Satışı** | 1 hafta doküman | 1-2 ay | **1000$+/ay** |

**Odaklan:** Ko-fi + DistroKid + Şablon README (bu ay).

---

## 12. TARİHLİ ZORUNLULUKLAR

- **2026-10-09:** `python olcum_temel_cizgi.py --cek` (kapak/video değişikliği etkisi)
- **Her Pazartesi 09:00+:** Haftalık rapor (`weekly_report.haftalik_gozden_gecirme`)
- **Günde 1:** Günlük izlenme raporu (`weekly_report.gunluk_izlenme_raporu`)
- **Elle işlem:** `elle_islem.py ekle ...` — **yapılan her manuel iş deftere**

---

## 13. KOD YAZIM KURALLARI

- **Dosya yazma:** `chr(92)` veya `Write` aracı — ters eğik çizgi kaçışı YASAK
- **drawtext satır sonu:** `DRAWTEXT_SATIR_SONU = chr(10)` (0x0A) — `"\n"` YASAK
- **Türkçe lower:** `İ→i, I→ı` ÖNCE, sonra `lower()` — `caption_align._norm_word` deseni
- **Atomik yazım:** Her `state.json` yazımı `state_io` — `ast` kontrolü CI'da
- **Import sırası:** stdlib → third-party → local — `ruff` zorlar
- **Art zorunluluğu:** Her proje için `meta.json` içinde `art_query` alanı zorunlu ve boş olmamalı.
- **Ştir belgesi zorunluluğu:** Her DJ seti için `config.SET_STILLERI` altına yeni stil eklenirse, o stilin belgesi ve örnek bir referans seti olmalı.
- **Agent zorunluluğu:** Eğer ekipte lyric‑yazar, melodi‑üretmeni veya mix‑master yetkisi yoksa, ilgili AI‑agent (lyric_agent, melody_agent, mix_agent) tanımlanmalı ve kullanım kuralı olarak projeye eklenmelidir.
- **Ön‑kontrol listesi:** Her proje başlamadan önce aşağıdaki maddeleri kontrol etmelidir: `meta.json` eksiksizliği (title, theme, set_style, marquee_text‑“DJ Famous”, art_query), `sozler.md` varlığı, `structure.txt` varlığı, `state.json` temizliği (render_kilit yok). Eksik bir madde varsa proses durdurulup bildirim verilmelidir.

---

## 14. ACRONYM / TERMİNLER

| Terim | Anlam |
|-------|-------|
| **Suno** | AI müzik üretimi (kota: günlük ~10-12) |
| **Golden Hour** | TR 12:00-14:00 / 18:00-22:00 — yayın penceresi |
| **Fail-closed** | Hata = kapı kapanır, proje atlanır |
| **Backfill** | Eski eksik yüklemeleri tamamlayan süpürge |
| **Konteyner** | Instagram `creation_id` (23sa ömürlü) |
| **MD5 kapısı** | Aynı ses = kopya şüphesi, dar muafiyet |
| **Tempo tabanı** | 52 saat minimum ara (yeni yayınlar) |

---

## 15. BU DOSYA GÜNCELLENİRSE

1. Değişiklik **tek commit** — `git add CLAUDE.md && git commit -m "rule: <kısa açıklama>"`
2. İlgili `tests/test_kurallar.py` güncellenir
3. CI geçmeli — geçmezse merge YOK

---

## 16. BÜYÜME MOTORU (İzlenme × Kalma × Abone — Kalıcı, Bayraklı)

Kayıt: `BUYUME_ONERILERI.md` (17 madde, durum+kod+test tablosu). Kilit testler:
`tests/test_buyume_onerileri.py`. Yeni madde = kayıt satırı + test (kural §9).
Kapatmak silmek değil — `config.py` BÜYÜME bayrağını `False` yapmaktır.

- **Cold-open:** Uzun videonun başına highlight'tan ön tat (`COLD_OPEN_SURE_SN`, varsayılan 4sn) — ses concat, chapter'lar aynı süre ötelenir. Sadece `youtube_16x9`, highlight kırpmasına YOK.
- **Görsel nabız:** Bölüm verisi olmasa bile ~25sn'de hue/pan vurgusu (`GORSEL_NABIZ_SURE_SN`) — ana + Shorts filtresinde.
- **Abone CTA:** Videonun %40'ında 1 kez 4sn, emir kipi YOK — rutin vaat (`ABONE_CTA_METIN`: dj → "Her Cuma yeni şehir", diğer → "Her hafta yeni şarkı").
- **Bitiş kartı:** `meta.json`'da `end_card_text` varsa son 15sn'de (`END_CARD_SURE_SN`) — yoksa çizilmez.
- **Chapter:** `tracklist` varsa `chapters.ffmeta` üretilir + tam boy videoya gömülür + açıklamada timestamp satırları (YouTube chapter'ı). Yer tutucu başlık (`Track 3`) = UYARI, render durmaz.
- **Seri kapağı:** `series` varsa `SERIES_THUMBNAIL_TEMPLATES` şablonu — `{Brand} • Ep01` + landmark (≤4 kelime) + logo.
- **Shorts native:** `shorts_9x16` = tam ekran art + hook + lower-third — kart squeeze YOK.
- **Başlık:** Seri kalıbı `{artist}` ile başlar (mobil ilk 35 karakter). **Funnel:** Shorts, uzun video ID'siyle yüklenir (tam sürüm linki şart).
- **AI beyanı videoya YAKILMAZ (kırmızı çizgi):** Sadece `containsSyntheticMedia=True` bayrağı + açıklama satırı. Pikselde rozet/overlay YASAK — CI'da test edilir.
- **Kültür-kod:** `SET_STILLERI`'ne yeni stil eklenebilir (`arabesk_trap`, `nineties_nostalji` örnek) — belge + referans set şartı (§13) aynen geçerli.
- **Ölçüm:** Tek seferde tek değişiklik; öncesi `olcum_temel_cizgi.py --cek`.

---

## 17. SITE BÜYÜME MOTORU (2026-10-20) — Madde 25-28

YouTube Studio 5 manuel görev (banner, trailer, 4 playlist, açıklama, bağlantılar)
API + tarayıcı ile **otomatikleştirildi**. `site/index.html` production-ready
hale getirildi. Kayıt: `BUYUME_ONERILERI.md` §"Site Büyüme Motoru".

- **Madde 25 — AI Tarz Seçici:** `config.TARZ_SECICI_ACIK` + `TARZ_SECICI_TONUZLER` (6 ruh hali) → `site/index.html` `#tarz-secici`. **Otomatik oynatma YOK** (spam sinyali) — tıklayınca çalar. config↔site senkron kilitli.
- **Madde 26 — Kanal bağlantıları (5):** `youtube_studio_setup_api.py::CHANNEL_LINKS`. **DIKKAT:** `brandingSettings.channel.links` Data API'de **yazılmıyor** (sessizce yok sayılıyor) → UI gerekli.
- **Madde 27 — Kanal açıklaması:** `youtube_studio_setup_api.py::CHANNEL_DESCRIPTION` (6 satır). `channels.update(part=snippet)` → **400 ERROR_PART_UNEXPECTED**; `brandingSettings.channel.description` ile yazılır.
- **Madde 28 — Site analitik:** `site/analytics.js` + `site/api/analytics.py` — **cookie-less, PII-yok, first-party**. `text/plain` beacon (preflight yok) + `credentials:'omit'`. Veri: `analytics_data/site/site_visits.jsonl`. `config.py` tek kaynak → `python sync_site_analytics.py`.
- **Madde 29 — Topluluk:** 3 kanal: **Discord** (webhook) + **Telegram** (bot token) + **ntfy** (token gerektirmez, telefona anlik push, bu agdan erisilebilir — Discord bu agdan engelli, Telegram icin gercek token gerekli). `topluluk.py` + `netlify/functions/topluluk.js` + `site/api/topluluk.py`. Topluluk verisi analitikten **AYRI** (`analytics_data/topluluk/`). Placeholder Telegram token tespit edilir (404 yerine net mesaj). `python topluluk.py durum | bildir | disa-aktar`.
- **Madde 29b — Otomatik bildirim:** `auto_process.py` + `dj_famous_process.py`, `upload_video` başarılı olunca `_topluluk_bildir()` çağırır (yeni görev YOK). **FAIL-SAFE:** bildirim hatası yayını geri almaz — fail-closed kuralı YAYIN içindir, bildirim fail-OPEN olmalıdır.
- **Madde 30 — Site deploy:** ✅ **CANLIDA** — statik: `https://semtappdata-art.github.io/famous-music-studio/` (GitHub Pages) · statik+API: `https://famous-music-studio.netlify.app` (Netlify). ⚠️ **Netlify Lambda Python desteklemiyor** → fonksiyonlar JS (`netlify/functions/`) + Netlify Blobs v1; Python surumler yerel icin `site/api/`. `netlify.toml` (publish=`site`, functions=`site/api`) + `/api/*` redirect'leri + `privacy.html` / `404.html` / `epk/bio.html` + CSP/güvenlik başlıkları + `.github/workflows/deploy-site.yml`. **GitHub Pages alt-yol servis eder** → mutlak yollar 404 verir, iç linkler **göreli** olmalı. API ucu `window.FMS_API_BASE` ile ayarlanabilir. **GitHub Pages statiktir** → API fonksiyonları için Netlify/Vercel şart. Repo 4.4 GB → `git push` timeout verir; `publish_site_github.py` (GitHub API, blob→tree→commit) kullanılır. Rehber: `site/DEPLOY.md`. **Deploy:** `python deploy_site.py` (tek komut: test → Netlify → smoke test → GitHub Pages). GitHub Actions PAT'te `workflow` scope olmadığı için kullanılamıyor; `deploy_site.py` onun yerini alır.
- **Madde 31 — Dil toggle (TR/EN):** `site/i18n.js` (sözlük) + `index.html` `data-i18n` + sağ üstte TR/EN düğmesi. Varsayılan TR; tarayıcı dili EN ise ilk açılışta EN. Secim `localStorage`'da (`fms_dil`) — **yalnızca kullanıcı tercihi**, analitik toplamaz. JS ile üretilen içerik (tarz seçici) `dil:degisti` olayında yeniden çizilir. **REGRESYON:** i18n sırasında fazla `}` ile ana script çöktü (testler yeşil, sayfa ölü) → `check_js_braces.py` + `test_site_js_dengesi_bozulmamis` kilitler.

**REGRESYON (2026-10-20) — 3 sessiz hata, testle kilitli:**
1. `<title>` `</meta>` ile kapanmıştı → 57KB `<head>`'e gömüldü, **sayfa tamamen beyaz** render oldu. → `test_site_html_yapisi_dengeli`
2. `window.MUSIC_DATA` → top-level `const` window'a eklenmez → **4 müzik kartı hiç oluşmadı** (konsolda hata yok). → `test_site_music_data_window_hatasi_yok`
3. `sendBeacon` + `application/json` → preflight + `credentials:'include'` → `Access-Control-Allow-Origin: *` ile **CORS reddi**, POST hiç ulaşmadı. → `text/plain` + `credentials:'omit'`

**DERS:** Testler yeşil olsa bile **tarayıcıda görsel doğrulama** yap — DOM boş kalabilir.

---

**Son güncelleme:** 2026-10-20 — §17 Site Büyüme Motoru eklendi (Madde 25-31, 4 regresyon kilitli). Site canlıda.