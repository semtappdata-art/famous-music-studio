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

**Son güncelleme:** 2026-09-14 — Tüm eski kurallar silindi, bu plan onaylandı.