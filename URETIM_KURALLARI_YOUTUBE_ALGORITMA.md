# ÜRETİM KURALLARI — YouTube Algoritması Blueprint Entegrasyonu
**Famous Music Studio — Otomasyon Pipeline İçin Zorunlu Kurallar**

> **Kaynak:** `youtube_algorithm_blueprint.md` (12 Madde + Notlar)  
> **Durum:** KESİN KURAL — Pipeline her adımında kontrol edilecek  
> **Versiyon:** 2026-10-20 v1.0  
> **Entegrasyon:** `auto_process.py`, `dj_famous_process.py`, `render.py`, `validate_project.py`, `uyumluluk.py`

---

## 📋 KURAL KATEGORİLERİ

| Kategori | Prefix | Açıklama |
|----------|--------|----------|
| **Metadata** | `META-` | Video başlığı, açıklama, etiketler, bölümler |
| **İçerik Yapısı** | `CONTENT-` | Hook, retention, session extension,章节 |
| **Teknik Üretim** | `TECH-` | Render kalitesi, formatlar, dosya isimlendirme |
| **Yayın Stratejisi** | `PUBLISH-` | Zamanlama, platform, Shorts/uzun video ilişki |
| **Kanal Sağlığı** | `CHANNEL-` | Playlist, trailer, banner, community |
| **Güvenlik/Politika** | `SAFETY-` | Clickbait koruması, telif, AI beyanı |
| **Ölçüm/Geri Besleme** | `MEASURE-` | Analytics entegrasyonu, iteratif iyileştirme |

---

## 🔴 META KURALLARI (Zorunlu — Pipeline Durdurur)

### META-001: Başlık Formatı — Mobil İlk 35 Karakter
```python
# KURAL: Başlık = {Artist} + {Parça Adı} + {Tür/Stil Kısa}
# Örnek: "Famous Music Studio - Gece Sürüsü (Turkish Pop R&B)"
# UZUNLUK: ≤ 60 karakter (mobil truncation önleme)
# YASAK: Clickbait mismatch (başlık-İçerik uyuşmazlığı)
```
**Kontrol:** `validate_project.validate_title()` → `len(title) <= 60` VE `title.startswith("Famous Music Studio")`

### META-002: Açıklama — İlk 2 Satır = SEO + CTA
```python
# ZORUNLU SATIR 1: "🎵 Famous Music Studio — AI-assisted Turkish music production"
# ZORUNLU SATIR 2: "🌙 Gece Masalları album · Night Drive DJ sets · Melodic Techno · Arabesk · Trap"
# ZORUNLU SATIR 3: "🎧 Listen everywhere: https://distrokid.com/hyperfollow/famousmusicstudio/gece-masallar"
# ZORUNLU SATIR 4: "☕ Support: https://ko-fi.com/famousmusicstudio"
# ZORUNLU SATIR 5: "📱 TikTok: @famousmusicstudio | Instagram: @famous_music_studio"
# ZORUNLU SATIR 6: "📧 Booking: booking@famousmusicstudio.com"
# SONRA: Timestamps (bölümler), hashtags, creditler
```
**Kontrol:** `validate_project.validate_description()` → 6 satır şablon eşleşmeli

### META-003: Etiketler — 8-10 Specific + 3 Broad
```python
# SPECIFIC (8-10): "turkish pop", "arabesk trap", "melodic techno mix", "ai music", "night drive", "dj famous", "gece masallari", "turkish r&b"
# BROAD (3): "music", "youtube music", "new music 2026"
# YASAK: İrrelevant tag stuffing
```
**Kontrol:** `validate_project.validate_tags()` → `len(specific) >= 8` VE `len(broad) == 3`

### META-004: Bölümler (Chapters) — Minimum 3, Açıklayıcı
```python
# UZUN VİDEO (>5dk): Minimum 3 chapter
# FORMAT: "0:00 Intro", "0:30 Verse 1", "1:15 Chorus", "2:00 Bridge", "2:45 Outro"
# YASAK: "Track 1", "Part 1", "Bölüm 1" gibi generic başlıklar
# DJ SET: Her track için chapter + timestamp
```
**Kontrol:** `render.py` → `chapters.ffmeta` üretilmeli + `meta.json`'da `chapters` array dolu olmalı

### META-005: Hashtags — Açıklamada 3-5 Niche + 1 Broad
```python
# ÖRNEK: "#FamousMusicStudio #TurkishPop #ArabeskTrap #MelodicTechno #NightDrive #AIAssistedMusic #NewMusic2026"
# YASAK: 15+ hashtag (spam sinyali)
```
**Kontrol:** `validate_project.validate_hashtags()` → `3 <= count <= 5` niche + 1 broad

---

## 🟠 İÇERİK YAPISI KURALLARI (Zorunlu — Kalite Kapısı)

### CONTENT-001: Hook — İlk 30 Saniye %70+ Retention Hedefi
```python
# UZUN VİDEO: 0:00-0:30 arası "Cold Open" (highlight'tan 4sn ön tat) → sonra tam şarkı
# SHORTS: İlk 1sn = En yüksek enerjili chorus kesiti + "🔊 Sesini Aç" animasyonu
# KURAL: İlk 30sn'de sözel/ görsel vaat (ne dinleyecekleri) NET olmalı
```
**Kontrol:** `render.py` → `COLD_OPEN_SURE_SN = 4.0` aktif + `DIKEY_HOOK_SURE_SN = 2.5` aktif

### CONTENT-002: Retention Grafiği — Ortalama %50+ Hedef
```python
# HEDEF: Average Percentage Viewed (APV) ≥ 50%
# YÖNTEM: 
#   - Verse/Chorus/Bridge = farklı zoom/pan/hue (söz zamanlaması varsa)
#   - Görsel nabız: ~25sn'de hue/pan vurgusu (GORSEL_NABIZ_SURE_SN)
#   - Progress bar YOK, marquee YOK
#   - Bölüm geçişlerinde 0.5sn sessizlik + görsel geçiş
```
**Kontrol:** `validate_project.validate_retention_structure()` → Söz zamanlaması varsa bölüm bazlı görsel değişim doğrulanmalı

### CONTENT-003: Session Extension — Video Bitiş Sonrası Kullanıcı YouTube'da Kalmalı
```python
# END CARD: meta.json'da `end_card_text` varsa son 15sn'de (END_CARD_SURE_SN)
# KART İÇERİĞİ: "Sonraki: [İlgili Parça Adı]" + Thumbnail + Link
# PLAYLIST: Her video en az 1 playlist'te olmalı (session extension)
# UP NEXT: Kanal sayfasında "Öne Çıkan Video" doğru ayarlanmalı
```
**Kontrol:** `auto_process.py` → `end_card_text` dolu mu? Playlist ataması var mı?

### CONTENT-004: Engagement Hooks — 3 Nokta Zorunlu
```python
# NOKTA 1 (0:30-1:00): "Favori bölümün hangisi? Dakikasıyla yaz 👇"
# NOKTA 2 (Orta): "Bu şarkı sana neyi hatırlattı? Yorumda yaz 💬"
# NOKTA 3 (Bitiş -15sn): "Abone ol, her yeni paragraftan önce haberdar ol 🔔"
# SHORTS: Açıklamada "Bu sesi videolarında kullan 👇" + Tam video linki
```
**Kontrol:** `render.py` → Lower-third / overlay olarak eklenmeli (pikselde AI rozeti YASAK)

### CONTENT-005: AI Beyanı — Sadece Metadata, Pikselde YOK
```python
# YOUTUBE UPLOAD: `containsSyntheticMedia = True` (checkbox)
# AÇIKLAMA SATIRI: "Söz: Famous Music Studio · Müzik ve vokal: AI destekli (Suno)"
# YASAK: Video üzerine "AI Generated" rozeti, watermark, overlay
# CI TEST: `tests/test_kurallar.py` → AI rozeti tespiti = FAIL
```
**Kontrol:** `uyumluluk.kontrol(proje, "yukleme")` → `containsSyntheticMedia=True` doğrulaması

---

## 🟡 TEKNİK ÜRETİM KURALLARI (Zorunlu — Render/Upload Öncesi)

### TECH-001: Kapak — İki Oran Zorunlu
```python
# cover.png: 16:9 (1920x1080) — YouTube uzun video
# cover_vertical.png: 9:16 (1080x1920) — Shorts/Reels/TikTok
# TİPOGRAFİ: Başlık alt 1/3'te (h*0.75), max %14 punkt, beyaz + 3px siyah outline + gölge
# LOGO: Sağ alt, %15 opaklık, küçük — YAZI YOK ("Famous Music Studio" yazmaz)
# ART: Metinsiz, Pexels (LLM query + aesthetic score) veya prosedürel bokeh fallback
# RENK HARMONİSİ: Art.jpg dominant rengi → başlık outline/gölge rengi
```
**Kontrol:** `generate_cover.py` → İki dosya üretilmeli + `validate_project.validate_covers()`

### TECH-002: Video Kalitesi — Platform Bazlı
```python
# YOUTUBE 16:9: 1920x1080, 30fps, H.264 High Profile, 15-20 Mbps CBR
# SHORTS 9:16: 1080x1920, 30fps, H.264, 8-12 Mbps
# SES: AAC 256kbps, -14 LUFS (YouTube normalizasyonu)
# KODLAMA: 2-pass CBR (ffmpeg2pass)
```
**Kontrol:** `render.py` → `ffmpeg_utils.py` parametreleri doğrulanmalı

### TECH-003: Dosya İsimlendirme — Standart
```python
# FORMAT: {project_id}_{platform}_{timestamp}.{ext}
# ÖRNEK: gece-surusu_youtube_16x9_20261020_143000.mp4
# META: {project_id}_meta.json
# STATE: {project_id}_state.json
```
**Kontrol:** `state_io.atomic_write()` → Dosya adı formatı regex ile doğrulanmalı

### TECH-004: DJ Set Özel Kuralları
```python
# TRACKLIST: Her track için {start_time, end_time, title, artist, bpm, key}
# CHAPTER: ffmeta + YouTube chapters (timestamp satırları)
# VISUAL: 5 kamera simülasyonu (verse/chorus/bridge = farklı kamera)
# HUD: Nefes efekti (8sn), Sahne modu, Arka plan blur (sigma=14)
# HOOK: İlk 1sn = En yüksek enerji drop + "🔊 Sesini Aç"
```
**Kontrol:** `dj_famous_process.py` → `validate_project.validate_dj_set()`

---

## 🟢 YAYIN STRATEJİSİ KURALLARI (Zorunlu — Upload Pipeline)

### PUBLISH-001: YouTube Native Scheduling — Golden Hour
```python
# GOLDEN HOUR (TR): 12:00-14:00 VE 18:00-22:00
# UPLOAD: `private` + `publishAt` (ISO 8601)
# SHORTS: Aynı video ID ile `shorts_9x16` render → ayrı upload (native Shorts)
# FUNNEL: Shorts açıklamasında "Tam sürüm: [Uzun Video URL]" ZORUNLU
```
**Kontrol:** `auto_process.py` → `schedule_in_golden_hour()` + `upload_youtube.py` native schedule

### PUBLISH-002: Instagram Reels — Container + Publish
```python
# ADIM 1: Container oluştur (media_id) — 23 saat ömrü
# ADIM 2: Golden Hour'da `media_publish`
# ADIM 3: Bayat container (23sa) → Sil + Manuel yeniden (bildirim gönder)
# KAPAK: `cover_vertical.png` (9:16)
```
**Kontrol:** `upload_instagram.py` → Container create + publish ayrı fonksiyonlar

### PUBLISH-003: TikTok — Taslak + Elle Yayın
```python
# UPLOAD: Draft (taslak) modunda
# PLAN: `tiktok_publish_plan.py` CLI → Kit/Doğrulama/Onay akışı
# ELLE YAYIN: Insan onayı ile "Post" butonu
# KAPAK: `cover_vertical.png` + Trending ses seçimi
```
**Kontrol:** `upload_tiktok.py` → Draft upload + `tiktok_publish_plan.py` entegrasyonu

### PUBLISH-004: Facebook Reels — Native Schedule
```python
# video_state=SCHEDULED + publish_time (ISO 8601)
# KAPAK: `cover_vertical.png`
```
**Kontrol:** `upload_facebook.py` → `video_state=SCHEDULED`

### PUBLISH-005: Telegram / Bluesky — Sadece Backfill
```python
# `ek_platform_backfill.py` çalıştırır
# Golden Hour + Günlük tavan (3) + Politika kapısı + Public-ani kapısı
# KAPAK: `cover_vertical.png` (Telegram), `cover.png` (Bluesky)
```
**Kontrol:** `ek_platform_backfill.py` → Tüm kapılar geçmeli

---

## 🔵 KANAL SAĞLIĞI KURALLARI (Haftalık/Manuel — Otomasyon Destekli)

### CHANNEL-001: Oynatma Listeleri — 4 Ana Kategori
```python
# PLAYLIST 1: "🎧 Gece Sürüşleri" — Melodic techno, night drive (DJ setler + instrumental)
# PLAYLIST 2: "🌙 Arabesk & Trap Vibes" — Türkçe arabesk, trap, R&B
# PLAYLIST 3: "🎛️ DJ Setler" — Tüm DJ mix videoları
# PLAYLIST 4: "🆕 Yeni Çıkanlar" — Son 10 yükleme (auto-update via YouTube API)
# KURAL: Her yeni video EN AZ 1 playlist'e eklenmeli (auto_process.py içinde)
```
**Kontrol:** `auto_process.py` → `add_to_playlists(video_id, playlist_ids)`

### CHANNEL-002: Kanal Trailer / Öne Çıkan Video
```python
# ABONE OLMAYANLAR: "Night Drive - DJ Cut" 30-60sn trailer edit
# ABONELER: En yeni mix/parça
# GÜNCELLEME: Her yeni DJ set'te trailer güncellenmeli
```
**Kontrol:** `elle_islem.py` → `youtube_update_featured_video()`

### CHANNEL-003: Kanal Banner — 2560×1440 Safe Area
```python
# SAFE AREA: 1546×423 (merkez)
# İÇERİK: Logo + "AI-assisted music production from Turkey" + "Gece Masalları — Out Now"
# GÜNCELLEME: Her albüm/değişiklikte
```
**Kontrol:** `elle_islem.py` → `youtube_update_banner()`

### CHANNEL-004: Community Tab — Haftalık Etkileşim
```python
# PAZARTESİ: Anket ("Haftanın ruh hali? Gece Sürüşü / Arabesk / Chill")
# ÇARŞAMBA: Yeni parça teaser (15sn) + "Tam sürüm yarın"
# CUMA: DJ set hatırlatması + "Canlı yayında buluşalım"
# OTOMASYON: `weekly_community_post.py` (gelecek)
```

---

## 🟣 GÜVENLİK/POLİTİKA KURALLARI (Fail-Closed — Pipeline Durdurur)

### SAFETY-001: Clickbait Koruması — Başlık/İçerik Uyumu
```python
# KURAL: Başlıkta geçen vaat (ör: "En iyi drop") → Videoda o an MEVCUT olmalı
# TEST: `validate_project.validate_clickbait()` → Söz/akor/enerji analizi ile doğrulama
# CEZA: Uyuşmazlık varsa → Pipeline DURDUR + Bildirim
```
**Entegrasyon:** `uyumluluk.kontrol(proje, "render")` içinde

### SAFETY-002: Telif / MD5 Kopya Kapısı
```python
# MD5: Aynı ses dosyası → Kopya şüphesi (dar muafiyet: aynı proje farklı platform)
# TELİF İŞARETİ: Suno/üretim aracı lisans kontrolü
# DERLEME DAMGASı: Compilation olarak işaretlenmiş mi?
# AI BEYANI: `containsSyntheticMedia=True` + açıklama satırı
```
**Entegrasyon:** `uyumluluk.kontrol(proje, "render" | "yukleme")` — 7 çağrı noktası

### SAFETY-003: AI Hashtag YASAK Listesi
```python
# YASAK: #AIgenerated, #AImusic, #ArtificialIntelligence, #MachineLearning
# İZİN VERİLEN: #AIAssistedMusic, #SunoAI, #AICreativity (marka uyumlu)
# KONTROL: `validate_project.validate_hashtags()` → Yasaklı liste cross-check
```
**CI Test:** `tests/test_kurallar.py` → Yasak hashtag tespiti = FAIL

### SAFETY-004: Günlük Yükleme Tavanı — Max 3
```python
# KURAL: Günlük toplam yükleme (tüm platformlar) ≤ 3
# SAYIM: YouTube (uzun) + Shorts + Instagram + TikTok + Facebook + Telegram + Bluesky
# BACKFILL: `ek_platform_backfill.py` → Günlük sayaç kontrolü
```
**Entegrasyon:** `state_io.load_state()` → `daily_upload_count` takibi

---

## 📊 ÖLÇÜM/GERİ BESLEME KURALLARI (Sürekli İyileştirme)

### MEASURE-001: Temel Çizgi Ölçümü — Her Değişiklik Öncesi/Sonrası
```python
# ARAÇ: `python olcum_temel_cizgi.py --cek` (kapak/video değişikliği etkisi)
# METRİKLER: CTR, APV, EWT, Subscribe rate, Share rate
# KARŞILAŞTIRMA: Değişiklik öncesi 7 gün vs sonrası 7 gün
# KAYIT: `BUYUME_ONERILERI.md` madde 17 — Değişiklik + Etki + Durum
```
**Zorunlu:** 2026-10-09 tarihi itibarıyla her kapak/video değişikliğinde

### MEASURE-002: Günlük İzlenme Raporu
```python
# ÇALIŞMA: `weekly_report.gunluk_izlenme_raporu()` — Her gece 02:00
# ÇIKTI: `logs/daily_views_YYYY-MM-DD.json`
# METRİK: Views, Watch time, Subscribers, Traffic sources
```

### MEASURE-003: Haftalık Gözden Geçirme
```python
# ZAMAN: Her Pazartesi 09:00+
# ARAÇ: `weekly_report.haftalik_gozden_gecirme()`
# ÇIKTI: `logs/weekly_report_YYYY-WW.md`
# İÇERİK: Top 3 video, Bottom 3 video, Trend analizi, Aksiyon öğeleri
```

### MEASURE-004: Elle İşlem Defteri
```python
# KURAL: Yapılan HER manuel iş `elle_islem.py ekle ...` ile kaydedilmeli
# KOMUT: `elle_islem.py ekle --tur "youtube_banner" --aciklama "Yeni albüm bannerı yüklendi" --video-id "xyz"`
# KAYIT: `elle_islemler.jsonl` (append-only)
```

---

## 🔧 PIPELINE ENTEGRASYON NOKTALARI

| Pipeline Aşaması | Çağrılan Doğrulama | Hata Durumu |
|------------------|-------------------|-------------|
| **Proje Oluşturma** | `validate_project.validate_meta()` | Durdur |
| **Kapak Üretimi** | `generate_cover.py` → `validate_project.validate_covers()` | Durdur |
| **Render Öncesi** | `uyumluluk.kontrol(proje, "render")` | Fail-closed → Atla |
| **Render Sonrası** | `validate_project.validate_render_output()` | Durdur |
| **Upload Öncesi** | `uyumluluk.kontrol(proje, "yukleme")` | Fail-closed → Atla |
| **Upload Sonrası** | `state_io.atomic_write()` → `state.json` güncelle | Hata logla |
| **Golden Hour Süpürgesi** | `_drain_golden_hour_queue()` (finally bloğu) | Logla devam |
| **Haftalık Backfill** | `ek_platform_backfill.py` → Tüm kapılar | Atla + Bildirim |

---

## ✅ KONTROL LİSTESİ — Her Proje İçin (Başlangıçta)

```bash
# Çalıştır: python validate_project.py --preflight <proje_klasoru>
# KONTROLLER:
☐ meta.json eksiksizliği (title, theme, set_style, marquee_text="DJ Famous", art_query)
☐ sozler.md varlığı
☐ structure.txt varlığı
☐ state.json temizliği (render_kilit yok)
☐ Kapak iki oran (cover.png + cover_vertical.png)
☐ YouTube video ID'si (MUSIC_DATA / DJ_SETS içinde)
☐ Hero preview MP3 (varsa)
☐ Bölümler (chapters) verisi (tracklist varsa)
☐ AI beyanı metni (description şablonunda)
☐ Politika kapısı temiz (telif, MD5, derleme, AI beyanı)
```

**EKSİK BİR MADDE VARSA → PROSES DURDURULUP BİLDİRİM VERİLMELİ** (CLAUDE.md §13)

---

## 📝 DEĞİŞİKLİK YÖNETİMİ

| İşlem | Kural |
|-------|-------|
| **Bu dosya güncellenirse** | Tek commit: `git add URETIM_KURALLARI_YOUTUBE_ALGORITMA.md && git commit -m "rule: <kısa açıklama>"` |
| **Yeni kural eklendiğinde** | `tests/test_kurallar.py` güncellenmeli (CI gate) |
| **CI geçmezse** | Merge YOK (GitHub Actions: windows-latest, ruff, mypy --strict, trufflehog, pytest) |

---

## 🎯 ÖZET: KESİN KURAL ÖZETİ (Hafıza İçin)

```
META:     Başlık≤60ch + "Famous Music Studio" ile başla | Açıklama 6 satır şablon | Tag 8+3 | Chapter≥3 | Hashtag 3-5
CONTENT:  Hook 30sn %70+ | APV ≥50% | Session extension (end card + playlist) | 3 engagement nokta | AI beyanı sadece metadata
TECH:     Kapak 16:9 + 9:16 | Video 1920x1080/1080x1920 30fps | Dosya isim standardı | DJ set: tracklist+chapter+HUD
PUBLISH:  YouTube native schedule (Golden Hour) | IG container+publish | TikTok draft+elle | FB scheduled | TG/Bluesky backfill
CHANNEL:  4 playlist | Trailer güncel | Banner güncel | Community haftalık
SAFETY:   Clickbait koruması | Telif/MD5/AI beyanı | Yasak AI hashtag | Günlük ≤3 yükleme
MEASURE:  Temel çizgi (olcum_temel_cizgi.py) | Günlük rapor | Haftalık gözden geçirme | Elle işlem defteri
```

**BU KURALLAR `auto_process.py`, `dj_famous_process.py`, `render.py`, `validate_project.py`, `uyumluluk.py`, `state_io.py` İÇİNDE KOD OLARAK ZORUNLU KILINMIŞTIR.**

---

**Son Güncelleme:** 2026-10-20 — YouTube Algoritması Blueprint (12 Madde) tam entegrasyonu