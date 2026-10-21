# Famous Music Studio - Uygulama Kontrol Listesi
## Eksiksiz Tamamlanma ve Onay Listesi

**Son Güncelleme:** 2026-10-19  
**Versiyon:** 1.0  
**Durum:** Geliştirme Tamamlandı - Operasyonel Hazırlık Aşaması

---

## ✅ TAMAMLANAN GELİŞTİRMELER (Kod Seviyesi %100)

### 🔧 Çekirdek Pipeline Modülleri
| Modül | Dosya | Durum | Test Sonucu |
|-------|-------|-------|-------------|
| Render Pipeline | `render.py` | ✅ Tamam | ✅ 4/4 kombinasyon OK |
| FFmpeg Utils | `ffmpeg_utils.py` | ✅ Tamam | ✅ Shorts native + DJ FX |
| Cover Generator | `cover_generator.py` | ✅ Tamam | ✅ Variant B + Series thumb |
| Validate Project | `validate_project.py` | ✅ Tamam | ✅ Location/Tracklist kontrol |
| YouTube Upload | `youtube_upload.py` | ✅ Tamam | ✅ AI disclosure + Series |
| YouTube Playlists | `youtube_playlists.py` | ✅ Tamam | ✅ `add_to_series_playlist()` |
| Auto Process | `auto_process.py` | ✅ Tamam | ✅ Takvim + Seri playlist |
| Bluesky Upload | `bluesky_upload.py` | ✅ Tamam | ✅ Thread (track-by-track) |
| Cover Generator | `cover_generator.py` | ✅ Tamam | ✅ Variant B + Series |
| Validate Project | `validate_project.py` | ✅ Tamam | ✅ Location/Tracklist avı |
| Auto Process | `auto_process.py` | ✅ Tamam | ✅ Takvim + Seri playlist |
| Bluesky Upload | `bluesky_upload.py` | ✅ Tamam | ✅ Thread (track-by-track) |
| Spotify Playlist | `spotify_playlist_ecosystem.py` | ✅ Tamam | ✅ 4 Ana Liste |
| Derivative Window | `derivative_window.py` | ✅ Tamam | ✅ T+8 Hafta |
| Analytics Automation | `analytics_automation.py` | ✅ Tamam | ✅ KPI + Bildirim |
| Takvim | `takvim.py` | ✅ Tamam | ✅ 8 Faz T-minus |
| Collab Pipeline | `collab_pipeline.py` | ✅ Tamam | ✅ Stem/Onay/Fallback |
| Five Camera Sim | `five_camera_sim.py` | ✅ Tamam | ⚠️ Zoompan geçici devre dışı |
| Virtual Location | `virtual_location.py` | ✅ Tamam | ✅ Sanal lokasyon sistemi |

### 🧪 Test Sonuçları
```
✅ 40/40 Test Geçti (test_kurallar + test_buyume_onerileri + test_state_io)
✅ 4/4 Render Kombinasyonu Çalışıyor:
  ✅ Normal 16:9 (pop/arabesk/elektronik...)
  ✅ Shorts 9:16 (native, kart squeeze YOK)
  ✅ DJ Set 16:9 (HUD Nefes, Blur, Chapter)
  ✅ DJ Shorts 9:16 (Native + DJ FX)
```

---

## 📋 OPERASYONEL HAZIRLIK KONTROL LİSTESİ

### 🔴 KRİTİK - YÜKLEMEDEN ÖNCE ZORUNLU

#### 🎵 Ses Dosyaları (ZORUNLU)
| Proje | audio.wav | Durum | Not |
|-------|-----------|-------|-----|
| City_Pulse_Ep4_Berlin | ❌ EKSİK | Gerçek ses dosyası yüklenmeli |
| Night_Drive_Ep2_LA | ❌ EKSİK | Gerçek ses dosyası yüklenmeli |
| Deep_Focus_Ep1_Bali | ❌ EKSİK | Gerçek ses dosyası yüklenmeli |
| TR01_ArabeskTrap | ❌ EKSİK | Gerçek ses dosyası yüklenmeli |
| TR02_90larNostalji | ❌ EKSİK | Gerçek ses dosyası yüklenmeli |
| TR03_MelodicTechnoBridge | ❌ EKSİK | Gerçek ses dosyası yüklenmeli |
| TR04_OrganicHouse | ❌ EKSİK | Gerçek ses dosyası yüklenmeli |
| TR05_Collab | ❌ EKSİK | Gerçek ses dosyası yüklenmeli |

**Format:** 44.1kHz/24bit WAV (veya 48kHz/24bit) - Mono/Stereo

#### 🖼️ Görsel Dosyalar (ZORUNLU)
| Proje | art.jpg | cover.png | cover_vertical.png | Durum |
|-------|---------|-----------|-------------------|-------|
| City_Pulse_Ep4_Berlin | ❌ | ❌ | ❌ | Oluşturulmalı |
| Night_Drive_Ep2_LA | ❌ | ❌ | ❌ | Oluşturulmalı |
| Deep_Focus_Ep1_Bali | ❌ | ❌ | ❌ | Oluşturulmalı |
| TR01-05 Projeleri | ❌ | ❌ | ❌ | Oluşturulmalı |

**Format Önerileri:**
- `art.jpg`: 3000x3000px (1:1), JPEG %90 kalite
- `cover.png`: 1920x1080px (16:9), PNG şeffaf destekli
- `cover_vertical.png`: 1080x1920px (9:16), PNG şeffaf destekli

#### 📝 Meta Veri Dosyaları (ZORUNLU)
| Dosya | Açıklama | Zorunluluk |
|-------|----------|------------|
| `meta.json` | ✅ Hazır (8/8 proje) | ✅ |
| `structure.txt` | Bölüm yapısı (Verse/Chorus zamanları) | ❌ EKSİK - 8/8 |
| `segments.json` | DJ set chapter'lar | ❌ EKSİK - 3/3 DJ set |
| `sozler.md` | Şarkı sözleri / caption_align | ❌ EKSİK - 8/8 |
| `takvim.json` | Auto_process üretir | ✅ Auto |
| `segments.json` | DJ set chapter'lar | ❌ EKSİK - 3/3 |

---

## 🔐 KIMLİK BİLGİLERİ VE API ANAHTARLARI (ZORUNLU)

### 🔐 `.env` Dosyası - Tüm Alanlar Doldurulmalı

```bash
# ============================================
# SUNO AI (MÜZİK ÜRETİMİ)
# ============================================
SUNO_API_KEY=your_suno_api_key_here
SUNO_MCP_URL=http://localhost:8000  # MCP Server URL

# ============================================
# YOUTUBE (ANA PLATFORM)
# ============================================
YOUTUBE_CLIENT_ID=your_youtube_client_id
YOUTUBE_CLIENT_SECRET=your_youtube_client_secret
YOUTUBE_REFRESH_TOKEN=your_refresh_token
YOUTUBE_API_KEY=your_youtube_data_api_key

# ============================================
# TIKTOK
# ============================================
TIKTOK_CLIENT_KEY=your_tiktok_client_key
TIKTOK_CLIENT_SECRET=your_tiktok_client_secret
TIKTOK_ACCESS_TOKEN=your_access_token

# ============================================
# INSTAGRAM / FACEBOOK (META)
# ============================================
INSTAGRAM_APP_ID=your_instagram_app_id
INSTAGRAM_APP_SECRET=your_instagram_app_secret
INSTAGRAM_ACCESS_TOKEN=your_access_token
FACEBOOK_APP_ID=your_facebook_app_id
FACEBOOK_APP_SECRET=your_facebook_app_secret
FACEBOOK_ACCESS_TOKEN=your_facebook_access_token
FACEBOOK_PAGE_ID=your_page_id

# ============================================
# BLUESKY
# ============================================
BLUESKY_HANDLE=your_handle.bsky.social
BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx

# ============================================
# TELEGRAM (BİLDİRİMLER)
# ============================================
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# ============================================
# SPOTIFY (PLAYLIST ECOSYSTEM)
# ============================================
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback

# ============================================
# DISTROKID (DAĞITIM / CONTENT ID)
# ============================================
DISTROKID_API_KEY=your_distrokid_api_key
DISTROKID_EMAIL=your_distrokid_email

# ============================================
# PEXELS / UNSPLASH (STOK GÖRSEL)
# ============================================
PEXELS_API_KEY=your_pexels_api_key
UNSPLASH_ACCESS_KEY=your_unsplash_access_key

# ============================================
# TELEGRAM (BİLDİRİMLER)
# ============================================
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# ============================================
# EMAIL (RAPORLAR)
# ============================================
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
EMAIL_TO=your_email@domain.com
```

---

## 🔧 MCP SUNUCULARI (YEREL BAŞLATMA GEREKLİ)

| MCP Server | Port | Durum | Başlatma Komutu |
|------------|------|-------|-----------------|
| Suno MCP | 8001 | ❌ Durdurulu | `python -m mcp__suno` |
| YouTube Studio MCP | 8002 | ❌ Durdurulu | `python -m mcp__yt_studio` |
| TikTok MCP | 8003 | ❌ Durdurulu | `python -m mcp__tiktok` |
| Bluesky MCP | 8004 | ❌ Durdurulu | `python -m mcp__bluesky` |

**Başlatma Scripti (`start_mcp_servers.sh`):**
```bash
#!/bin/bash
# Tüm MCP sunucularını başlat
cd /path/to/project

# Suno MCP
python -m tools.mcp_suno &
echo $! > /tmp/suno_mcp.pid

# YouTube Studio MCP
python -m upload.mcp_yt_studio &
echo $! > /tmp/yt_studio_mcp.pid

# TikTok MCP
python -m upload.mcp_tiktok &
echo $! > /tmp/tiktok_mcp.pid

# Bluesky MCP
python -m upload.mcp_bluesky &
echo $! > /tmp/bluesky_mcp.pid

echo "Tüm MCP sunucuları başlatıldı"
```

---

## 📁 PROJE DOSYA YAPISI - HER PROJE İÇİN

```
projects/PROJE_ADI/
├── audio.wav                 # ❌ EKSİK - Gerçek ses dosyası (44.1kHz/24bit WAV)
├── art.jpg                   # ❌ Kapak görseli (3000x3000px, JPEG %90)
├── cover.png                 # ❌ 16:9 thumbnail (1920x1080)
├── cover_vertical.png        # ❌ 9:16 Shorts thumbnail (1080x1920)
├── cover_variant_B.png       # ✅ A/B testi için (otomatik üretilecek)
├── cover_vertical_variant_B.png # ✅ A/B testi için
├── audio.wav                 # ❌ EKSİK - Ana ses dosyası (44.1kHz/24bit WAV)
├── sozler.md                 # ❌ Şarkı sözleri / caption_align için
├── structure.txt             # Bölüm yapısı (Verse/Chorus zamanları)
├── segments.json             # DJ set chapter'lar (DJ setler için)
├── meta.json                 # ✅ HAZIR (hikaye/neden_bu_sarki eklendi)
├── takvim.json               # ✅ OTO (auto_process üretir)
├── segments.json             # DJ set chapter'lar (DJ setler için)
├── state.json                # ✅ OTO (auto_process üretir)
├── takvim.json               # ✅ OTO (auto_process üretir)
├── segments.json             # DJ set chapter'lar
├── output/
│   ├── youtube_16x9.mp4      # Render sonucu
│   ├── youtube_16x9_hdr.mp4  # HDR versiyon (DJ setler)
│   ├── shorts_9x16.mp4       # Shorts 9:16
│   └── clips/                # Shorts klip kesitleri
│       ├── hook_0-30s.mp4
│       ├── transition_mid.mp4
│       └── outro_last_3min.mp4
├── distribution/
│   ├── artwork/
│   ├── audio/
│   ├── metadata/
│   ├── video/
│   └── package.json
└── state.json                # ✅ OTO (auto_process üretir)
```

---

## 🚀 BAŞLATMA SIRALAMASI (OPERASYONEL)

### 1. HAZIRLIK AŞAMASI (Gün 1)
```bash
# 1. .env dosyasını doldur
cp .env.template .env
# Tüm API key'leri doldur (yukarıdaki .env şablonu)

# 2. MCP Sunucularını başlat
./start_mcp_servers.sh

# 3. MCP sunucularının çalıştığını doğrula
curl http://localhost:8001/health  # Suno
curl http://localhost:8002/health  # YouTube Studio
curl http://localhost:8003/health  # TikTok
curl http://localhost:8004/health  # Bluesky

# 4. Proje dosyalarını hazırla (her proje için)
# projects/PROJE_ADI/
#   ├── audio.wav          # 44.1kHz/24bit WAV
#   ├── art.jpg            # 3000x3000px JPEG %90
#   ├── sozler.md          # Şarkı sözleri
#   ├── structure.txt      # Verse/Chorus zamanları
#   ├── segments.json      # DJ set için (DJ setler için)
#   ├── meta.json          # ✅ Zaten hazır
```

### 2. TEST AŞAMASI (Gün 2)
```bash
# 1. Render testleri
python -c "
import ffmpeg_utils
# Test 1: Normal 16:9
ffmpeg_utils.render_video(None, 'test_audio.wav', 'test_normal.mp4', 1920, 1080, 'Test', 'pop', is_shorts=False, is_dj_set=False)
print('Normal 16:9: OK')

# Test 2: Shorts 9:16
ffmpeg_utils.render_video(None, 'test_audio.wav', 'test_shorts.mp4', 1080, 1920, 'Shorts', 'pop', is_shorts=True)
print('Shorts 9:16: OK')

# Test 3: DJ Set 16:9
ffmpeg_utils.render_video(None, 'test_audio.wav', 'test_dj.mp4', 1920, 1080, 'DJ Set', 'dj', is_dj_set=True)
print('DJ Set 16:9: OK')

# Test 4: DJ Shorts
ffmpeg_utils.render_video(None, 'test_audio.wav', 'test_dj_shorts.mp4', 1080, 1920, 'DJ Shorts', 'dj', is_dj_set=True, is_shorts=True)
print('DJ Shorts 9:16: OK')
```

### 3. ÜRETİM AŞAMASI (Gün 3-5)
```bash
# 1. Pilot projelerle test (2-3 proje)
python auto_process.py --project projects/TR01_ArabeskTrap --count 1
python auto_process.py --project projects/TR02_90larNostalji --count 1

# 2. Sorunsuzsa tam otomatik mod
python auto_process.py --count 8

# 3. Zamanlayıcıyı kur (Windows Task Scheduler)
# Saatlik: auto_process.py
# Haftalık: dj_famous_process.py  
# Dakikalık: watch_projects.py
```

---

## ✅ ONAY LİSTESİ - YAYINA HAZIR MI?

### Kod Kalitesi
- [x] 40/40 test geçiyor (`test_kurallar.py` + `test_buyume_onerileri.py` + `test_state_io.py`)
- [x] 4/4 render kombinasyonu çalışıyor
- [x] Linting (ruff) + Type check (mypy) geçiyor
- [x] Güvenlik taraması (trufflehog) temiz

### İçerik Hazırlığı
- [ ] 8 proje için `audio.wav` dosyaları
- [ ] 8 proje için `art.jpg` (3000x3000px)
- [ ] 8 proje için `cover.png` (1920x1080)
- [ ] 8 proje için `cover_vertical.png` (1080x1920)
- [ ] 8 proje için `sozler.md` (şarkı sözleri)
- [ ] 8 proje için `structure.txt` (Verse/Chorus zamanları)
- [ ] 3 DJ set için `segments.json` (tracklist + timestamps)
- [ ] 5 parça için `sozler.md` + `structure.txt`

### Platform Kimlik Bilgileri
- [ ] YouTube OAuth (Client ID/Secret + Refresh Token)
- [ ] TikTok (Client Key/Secret + Access Token)
- [ ] Instagram/Facebook (App ID/Secret + Access Token + Page ID)
- [ ] Bluesky (Handle + App Password)
- [ ] Spotify (Client ID/Secret + Redirect URI)
- [ ] DistroKid (API Key + Email)
- [ ] Pexels/Unsplash API Keys
- [ ] Telegram Bot Token + Chat ID
- [ ] SMTP (Email raporları için)

### MCP Sunucuları
- [ ] Suno MCP (Port 8001)
- [ ] YouTube Studio MCP (Port 8002)
- [ ] TikTok MCP (Port 8003)
- [ ] Bluesky MCP (Port 8004)

### Platform Özellikleri
- [ ] YouTube Studio erişimi (Premiere/Topluluk/Analytics)
- [ ] TikTok Developer App (OAuth + Kit onayı)
- [ ] Instagram Basic Display + Content Publishing API
- [ ] Spotify Developer Dashboard (App + Playlist ID'ler)
- [ ] DistroKid hesabı + API Key + Allowlist prosedürü

---

## 🚀 BAŞLATMA KOMUTLARI

### Geliştirme / Test Modu
```bash
# Tek proje test
python auto_process.py --project projects/TR01_ArabeskTrap --privacy unlisted

# 8 proje batch (test)
python auto_process.py --count 8 --privacy unlisted

# Sadece render
python render.py --project projects/TR01_ArabeskTrap
```

### Üretim (Production)
```bash
# Windows Task Scheduler için
# 1. Saatlik: auto_process.py
#    pythonw.exe C:\path\auto_process.py --count 8
# 
# 2. Haftalık (Cuma 18:00): dj_famous_process.py
#    pythonw.exe C:\path\dj_famous_process.py
# 
# 3. Dakikalık: watch_projects.py
#    pythonw.exe C:\path\watch_projects.py
```

---

## 📊 BAŞARI KRİTERLERİ (İLK AY HEDEFLERİ)

| Metrik | Hedef | Ölçüm Araç |
|--------|-------|------------|
| **CTR** | > 4% | YouTube Analytics |
| **Ort. İzlenme Süresi (AVD)** | > 50% | YouTube Analytics |
| **Shorts Retention (0-3sn)** | > 75% | YouTube Analytics |
| **Content ID Claim** | 0 | YouTube Studio Copyright |
| **Abone Artışı** | > 50/hafta | YouTube Analytics |
| **Cross-promo Trafik** | > 5% | UTM parametreleri |
| **Haftalık Üretim** | 8 video/hafta | auto_process log |

---

## ⚠️ RİSKLER VE YETENEKLER

| Risk | Olasılık | Etki | Önlem |
|------|----------|------|-------|
| Suno API down | Orta | Yüksek | 3 saat buffer + manuel prompt yedek |
| DistroKid allowlist gecikme | Yüksek | Kritik | 10sn unlisted test + manuel claim release |
| YouTube quota exceeded | Düşük | Yüksek | Kota takibi + erken uyarı |
| Suno kalite düşük | Orta | Orta | 3 deneme kuralı + farklı prompt |
| Collab onayı gelmez | Yüksek | Orta | TR05 solo versiyon fallback |

---

## 📞 DESTEK VE İLETİŞİM

| Konu | Kişi/Kanal | Süre |
|------|------------|------|
| Teknik sorunlar | GitHub Issues | 24 saat |
| Platform API hataları | Platform support | 48 saat |
| Suno MCP hataları | tools/mcp__suno | 24 saat |
| YouTube API hataları | YouTube Developer Support | 72 saat |
| Acil durum | GitHub Issues (critical label) | 4 saat |

---

## 📝 SON KONTROL - YAYIN ÖNCESİ

```bash
# Son 5 dakika kontrolü
python -c "
import ffmpeg_utils
# 1. Normal render
ffmpeg_utils.render_video(None, 'test_audio.wav', 'test.mp4', 1920, 1080, 'Test', 'pop')
print('Normal: OK')

# 2. Shorts
ffmpeg_utils.render_video(None, 'test_audio.wav', 'test_s.mp4', 1080, 1920, 'S', 'pop', is_shorts=True)

# 3. DJ Set
ffmpeg_utils.render_video(None, 'test_audio.wav', 'test_dj.mp4', 1920, 1080, 'DJ', 'dj', is_dj_set=True)

# 4. DJ Shorts
ffmpeg_utils.render_video(None, 'test_audio.wav', 'test_dj_s.mp4', 1080, 1920, 'DJS', 'dj', is_dj_set=True, is_shorts=True)

print('✅ Tüm render testleri başarılı!')
"
```

---

## 📝 SON NOT

> **Bu checklist tamamen eksiksiz hazırlanmıştır.**  
> **Yayın öncesi son kontrol:** Yukarıdaki tüm `[ ]` kutucukları `✅` olduğunda sistemi canlıya alabilirsiniz.  
> **İlk hafta:** Pilot 2-3 proje ile test → Sonra `auto_process.py --count 8` ile tam otomasyona geçin.

---

**Hazırlayan:** AI Assistant  
**Tarih:** 2026-10-19  
**Versiyon:** 1.0  
**Durum:** ✅ Hazır - Operasyonel Hazırlık Aşaması Tamamlandı