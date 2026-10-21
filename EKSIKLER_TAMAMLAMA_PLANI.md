# EKSİKLERİN TAMAMLANMASI VE GÜÇLENDİRME PLANI — DETAYLI YAPILACAKLAR LİSTESİ

**Tarih:** 2026-10-19 | **Durum:** Hafta 1 tamamlandı (8 proje render edildi), Altyapı %90 hazır  
**Hedef:** Tüm eksikleri kapatmak, video tasarımını profesyonel seviyeye taşımak, ölçeklenebilir hale getirmek

---

## 📋 YAPILACAKLAR LİSTESİ — ÖNCELİK SIRALI (P0 → P1 → P2)

---

## 🔴 P0 — BU HAFTA (Kritik Risk Kapatma + Temel Özellikler)

### 1. MEKÂN/HİKAYE META ALANLARI (validate_project.py + meta.json)
- [ ] `validate_project.py`'de `location` objesi zorunlu alanları kontrol et:
  - `landmark` (string, boş olamaz)
  - `city` + `country` (string)
  - `gps` (format: "lat,lon" regex kontrolü)
  - `story` (EN, en az 50 karakter)
  - `story_tr` (TR, en az 50 karakter) — **yeni zorunlu**
  - `route` (opsiyonel, night_drive için)
- [ ] Eksikse **HATA** (render durdur), sadece UYARI değil
- [ ] Test: `python validate_project.py --project dj_sets/City_Pulse_Ep4_Berlin` → HATA 0

### 2. SERİ-BAZLI THUMBNAIL (cover_generator.py)
- [ ] `SERIES_THUMBNAIL_TEMPLATES` her seri için landmark silüeti + logo konumu tanımla
- [ ] `location.landmark` → otomatik landmark silüeti arama (Pexels/Unsplash `landmark silhouette` sorgusu)
- [ ] Landmark metni ≤4 kelimeye kısaltma (mobil CTR için)
- [ ] Variant B: Landmark silüeti + farklı accent2 rengi
- [ ] Test: `python cover_generator.py --project dj_sets/City_Pulse_Ep4_Berlin` → cover.png + cover_vertical.png + variant_B

### 3. SHORTS 9:16 NATIVE FİLTER (ffmpeg_utils.py) — **KART SQUEEZE KALDIR**
- [ ] `_build_shorts_filter_complex` tamamen yeniden yaz:
  - **Tam ekran art.jpg** (blur + pan + hue) — kart YOK
  - **Hook** (ilk 2.5sn): "🔊 Sesini Aç" — üst %12, beyaz+gölge
  - **Lower-third** (alt %33): Şarkı adı + Sanatçı — yarı saydam siyah (0.6 alpha)
  - **İlerleme çubuğu** (alt, ince): beyaz, %84 genişlik
  - **Kart, marquee, marka satırı YOK** — tam ekran deneyim
- [ ] `render.py` → `is_shorts=True` parametresi zaten var, filtre çağrısını doğrula
- [ ] Test: `python render.py --project projects/TR01_ArabeskTrap` → shorts_9x16.mp4 (kart yok, tam ekran)

### 4. CONTENT ID ALLOWLIST PROSEDÜRÜ (SOP_yukleme.md §8)
- [ ] DistroKid ilk yayını sonrası:
  1. Kanal ID alma scripti (`python3 -c "..."`)
  2. DistroKid Dashboard → Content ID → Whitelist Channel
  2. Mevcut claim'leri temizleme (Release claim / Dispute)
- [ ] Yeni video öncesi kontrol listesi:
  1. 10sn unlisted test yükle → claim varsa allowlist işlenmemiş
  2. Claim yoksa → golden-hour'da public
- [ ] Canlı yayını için ayrı `live stream allowlist` notu
- [ ] `SOP_yukleme.md` §8-i tam doldur (yazıldı, kontrol et)

### 5. TEST & COMPARE (A/B TEST) DESTEĞİ
- [ ] `cover_generator.py` → Variant B otomatik üretimi (zaten var, test et)
- [ ] YouTube Studio A/B Test rehberi: `docs/AB_TEST_REHBERI.md` oluştur:
  - 3 varyant (A, B, C) yükleme sırası
  - 2 hafta test süresi
  - Kazanan = en yüksek izlenme süresi (istatistiksel anlamlılık)
  - 720p+ yükleme zorunluluğu
- [ ] Otomasyon: Ayda 1 eski videoda A/B testi (cron/Task Scheduler)

---

## 🟠 P1 — 2 HAFTA İÇİNDE (Orta Maliyet, Yüksek Etki)

### 6. MEKÂN GÖRSELLEŞTİRME (cover_generator.py + config.py)
- [ ] `location.landmark` → otomatik landmark silüeti:
  - Pexels/Unsplash sorgusu: `"{landmark} silhouette black background"`
  - `stock_art.py` ile indir → `cover_generator.py` ile kapakta kullan
- [ ] GPS koordinatları → Google Maps Static API / OpenStreetMap static map → harita küçük görseli kapakta
- [ ] `story_tr` → kapakta alt kısımda 2 satırlık hikaye özeti (küçük font, beyaz%0.8)
- [ ] GPS koordinatları → QR kod (küçük, sağ alt) → tarayınca Google Maps açılır

### 7. SHORTS/REELS OTOMATİK KLİP KESME (dj_famous_process.py)
- [ ] `dj_famous_process.py` → `create_shorts_clips()` fonksiyonu:
  - **Hook clip** (0-30sn): En yüksek enerji + hook yazısı
  - **Transition clip** (orta): En dramatik geçiş/beat drop
  - **Outro clip** (son 3dk): Çözülüş + end_card_text
- [ ] Her clip: 9:16 native, hook yazısı, progress bar, lower-third
- [ ] Dosya isimlendirme: `{proje}_hook.mp4`, `{proje}_transition.mp4`, `{proje}_outro.mp4`
- [ ] Otomatik upload kuyruğuna ekleme (auto_process.py entegrasyonu)

### 8. BLUESKY THREAD OTOMATİK (bluesky_upload.py)
- [ ] `create_track_thread()` fonksiyonu:
  - Tweet 1: Set/parça tanıtımı + kapak görseli
  - Tweet 2-6: Her track için (timestamp + başlık + sanatçı + BPM/Key)
  - Son tweet: Cross-promo linkleri (YouTube + Spotify + Instagram)
- [ ] Taslak modu → onay sonrası yayın
- [ ] Zamanlama: Yayın +1 saat sonra

### 9. KÜLTÜR-KOD SERİLERİ (config.py + cover_generator.py)
- [ ] `SET_STILLERI` genişletildi (arabesk_trap, nineties_nostalji) — **yapıldı**
- [ ] Her kültür-kod için thumbnail şablonu:
  - **arabesk_trap**: Gece İstanbul + neon + trafik ışıkları + "ARABESK TRAP" büyük yazı
  - **nineties_nostalji**: Kaset/TV statik + retro renkler + "90'LAR" büyük yazı
  - **roman_havasi**: Davul/zurna silüeti + "ROMAN HAVASI" yazı
  - **turkce_pop_remix**: Disco ışıkları + "REMIX" yazı
- [ ] Her şablon için `SERIES_THUMBNAIL_TEMPLATES` girdisi

### 10. DJ SET SAHNE MODU (dj_set_video.py + ffmpeg_utils.py)
- [ ] `DJ_SAHNE_MODU=True` → `dj_set_video.py`'de aktif et:
  - **HUD Nefes**: Sol üstte nefes göstergesi (dalga formu, 8sn periyot)
  - **Sahne Zoom**: Chorus'ta %8 zoom-in, verse'ta normal
  - **Arka Plan Blur**: Chorus'ta blur azalır (netlik artar)
  - **Eğri**: `DJ_SAHNE_EGRISI` → renk/kontrast animasyonu
- [ ] `ffmpeg_utils.py` → `build_dj_set_filter_complex()` yeni fonksiyon

### 11. KENDİ SPOTIFY PLAYLIST'LERİ (config.py + youtube_upload.py)
- [ ] `config.py` → `SPOTIFY_CALMA_LISTELERI` doldur:
  ```python
  SPOTIFY_CALMA_LISTELERI = {
      "City Pulse Sessions": "https://open.spotify.com/playlist/...",
      "Night Drive Series": "https://open.spotify.com/playlist/...",
      "Deep Focus Sessions": "https://open.spotify.com/playlist/...",
      "DJ Famous Essentials": "https://open.spotify.com/playlist/..."
  }
  ```
- [ ] `youtube_upload.py` → DJ set açıklamasına otomatik ekle (boşsa ekleme)
- [ ] Haftalık güncelleme: Yeni set/parça → playlist'e ekle (youtube_playlists.py entegrasyonu)

### 12. SERİ PLAYLIST OTOMATİK EKLEME (youtube_playlists.py + auto_process.py)
- [ ] `add_to_series_playlist()` fonksiyonu **yapıldı** — test et:
  ```bash
  python -c "
  from upload.youtube_playlists import get_authenticated_service, add_to_series_playlist
  yt = get_authenticated_service()
  add_to_series_playlist(yt, 'dj_sets/City_Pulse_Ep4_Berlin', 'VIDEO_ID')
  "
  ```
- [ ] `auto_process.py` → yükleme sonrası otomatik çağrı (yapıldı, test et)

---

## 🟢 P2 — 1 AY İÇİNDE (Stratejik, Ölçeklenebilirlik)

### 13. SANAL LOKASYON SİSTEMİ (stock_art.py + config.py:DJ_SERIES)
- [ ] `DJ_SERIES` her seri için `locations[]` dizisi (zaten var)
- [ ] `stock_art.py` → `fetch_location_image(landmark, style)` fonksiyonu:
  - Pexels sorgusu: `"{landmark} {style} cinematic 4k"`
  - Aesthetic score ile en iyisini seç
  - İndir → `cover_generator.py` için kaynak olarak kullan
- [ ] `config.py` → `DJ_SERIES[series]["visual_concept"]` alanı:
  ```python
  "visual_concept": "drone_establishing → rooftop_dj → city_timelapse"
  ```
- [ ] `cover_generator.py` → `visual_concept` okur → sahneleri sırayla render eder (montaj)

### 14. 5-KAMERA SİMÜLASYONU (ffmpeg_utils.py — INDIE_FLAGSHIP_5CAM)
- [ ] `config.py` → `INDIE_FLAGSHIP_5CAM["camera_roles"] = ["master", "tight", "detail", "wide", "gimbal"]`
- [ ] `ffmpeg_utils.py` → `build_5cam_filter_complex()`:
  - **Master**: Tam ekran art.jpg (ana kamera)
  - **Tight**: %110 zoom, DJ yüz/el odaklı
  - **Detail**: %150 zoom, eq/knob/fader detay
  - **Wide**: %80 zoom, mekan geniş açı
  - **Gimbal**: Hafif sallantı + hareket (simüle)
- [ ] Kesitler arası geçiş: `xfade` filtresi (0.5sn cross-dissolve)
- [ ] Enerji eğrisine göre kamera seçimi:
  - Verse → Wide + Master
  - Chorus → Tight + Gimbal
  - Bridge → Detail + Wide
  - Drop → Gimbal + Tight

### 15. COLLAB PIPELINE (dj_famous_process.py + takvim.py)
- [ ] `takvim.py` → `FAZLAR` içine `"collab_approval"` fazı (T-3 hafta)
- [ ] `dj_famous_process.py` → `initiate_collab(partner, track_id)`:
  - Stem dosyalarını hazırla (stems/ klasörü)
  - Ortak klasör (Google Drive / Dropbox) paylaş
  - Geri dönüş takibi (state.json'da `collab_status`)
- [ ] Onay gelmezse → T-1 hafta solo versiyon (TR05b) otomatik üret

### 16. KENDİ SPOTIFY PLAYLIST EKOSİSTEMİ
- [ ] 4 ana playlist oluştur (Spotify for Artists):
  1. **City Pulse Sessions** (melodic techno/progressive)
  2. **Night Drive Series** (driving/late night)
  3. **Deep Focus Sessions** (organic house/ambient)
  4. **DJ Famous Essentials** (tüm katalog, cronological)
- [ ] Her yeni set/parça → ilgili playlist'e otomatik ekleme
- [ ] Açıklamalara playlist linkleri otomatik ekleniyor (yapıldı)
- [ ] Haftalık: "Bu hafta eklenenler" topluluk postu

### 17. DERIVATIVE/REMIX PENCERESİ (takvim.py + plan)
- [ ] `takvim.py` FAZLAR'a `"derivative"` (T+8 hafta) **eklendi**
- [ ] Plan: Tutulan parça (AVD > 55%, CTR > 5%) → T+8 hafta:
  - **Remix paketi**: 3-4 farklı Künstler (club edit, radio edit, extended)
  - **Collab**: Farklı Künstler ile yeniden üretim
  - **Acoustic/Live versiyon**: Studio live kaydı
- [ ] İkinci basın + ikinci editoryal kapı (Spotify pitch tekrarı)

### 18. ANALİTİK VE OTOMATİK RAPORLAMA
- [ ] `youtube_analytics.py` → Haftalık rapor:
  - CTR, AVD, Abone artışı, Cross-promo trafiği
  - En iyi 3 video / en kötü 3 video
  - Kapak A/B test sonuçları
- [ ] `auto_process.py` → Haftalık rapor otomatik e-posta/Telegram
- [ ] Dashboard: `docs/latest.html` (latest_release.py) güncelleme

---

## 🔧 ALTYAPI GELİŞTİRMELERİ (Kalıcı, Kalıcı)

### 19. TEST KAPSAMI GENİŞLETME
- [ ] `tests/test_video_tasarim.py` yeni dosya:
  - Shorts native filter testi (kart yok mu?)
  - Variant B üretimi testi
  - Chapter gömme testi
  - Series thumbnail testi (landmark silüeti)
  - Cold-open chapter öteleme testi
- [ ] `tests/test_content_id.py` — Allowlist testi (mock DistroKid)
- [ ] CI: GitHub Actions → `pytest -q` + `ruff` + `mypy --strict`

### 20. DOKÜMANTASYON VE BİLGİ YÖNETİMİ
- [ ] `docs/VIDEO_TASARIM_SISTEMI.md` — Teknik mimari belgesi
- [ ] `docs/AB_TEST_REHBERI.md` — YouTube Studio A/B test rehberi
- [ ] `docs/CONTENT_ID_PROSEDUR.md` — DistroKid allowlist adım adım
- [ ] `docs/COLLAB_PIPELINE.md` — Collab süreci adım adım
- [ ] `CLAUDE.md` güncelleme: Her yeni kural + test + CI

---

## 📊 TAMAMLAMA TAKVİMİ

| Hafta | Odak | Teslimatlar |
|-------|------|-------------|
| **Hafta 1 (Bu hafta)** | P0: Mekân meta, Series thumbnail, Shorts native, Content ID prosedürü, A/B test | 5/5 P0 tamam |
| **Hafta 2-3** | P1: Mekân görselleştirme, Shorts klip kesme, Bluesky thread, Kültür-kod serileri, Sahne modu, Spotify playlist, Seri playlist | 7/7 P1 tamam |
| **Hafta 4-5** | P2: Sanal lokasyon, 5-kamera simülasyonu, Collab pipeline, Spotify ekosistemi, Derivative penceresi, Analitik raporlama | 6/6 P2 tamam |
| **Hafta 6** | Altyapa: Test kapsamı, Dokümantasyon, CI/CD | Altyapı tam |

---

## ✅ KONTROL LİSTESİ — HER HAFTA BAŞLANGICINDA

```
[ ] Plan JSON onaylandı mı? (haftalik_operasyon_YYYY_WW.json)
[ ] Config ayarları dolu mu? (SPOTIFY_CALMA_LISTELERI, PROMO_DM_SABLONU, vb.)
[ ] DistroKid allowlist aktif mi? (10sn test)
[ ] Takvim modülü çalışıyor mu?
[ ] Cover generator variant B derleniyor mu?
[ ] Validate project 3000x3000 uyarısı veriyor mu?
[ ] YouTube Studio erişimi açık mı?
[ ] Promo havuzu (15 DJ) güncel mi?
[ ] Spotify playlist ID'leri geçerli mi?
[ ] YouTube Studio erişimi (Premiere/Topluluk/Analytics) açık mı?
```

---

## 🎯 BAŞARI KRİTERLERİ (Bu Ay Sonu)

| Metrik | Hedef | Ölçüm |
|--------|-------|-------|
| **CTR** | > 4% | YouTube Analytics |
| **AVD** | > 50% | YouTube Analytics |
| **Shorts Retention (0-3sn)** | > 75% | YouTube Analytics |
| **Content ID Claim** | 0 | YouTube Studio Copyright |
| **Abone Artışı** | > 50/hafta | YouTube Analytics |
| **Cross-promo Trafik** | > 5% | UTM parametreleri |
| **Haftalık Üretim** | 3 set + 5 parça | Plan JSON vs Gerçek |

---

## 📁 DOKÜMANLAR (Hepsi Güncel)

| Dosya | Açıklama |
|-------|----------|
| `HAFTALIK_OPERASYON_PLANI.md` | 4 ajan, 6 faz, 10 bileşen DNA |
| `PROFESYONEL_LABEL_YOUTUBE_ANALIZI.md` | Label + YouTube lider davranışları |
| `SUNO_ONCESI_HAZIRLIK_DJSET.md` | Ep04 Berlin paketi (6 parça blueprint) |
| `BUYUME_ONERILERI.md` | 17 madde durum/kod/test tablosu |
| `VIDEO_TASARIM_KARSILASTIRMA_DETAYLI.md` | 8 kategori, 6 referans karşılaştırması |
| `EKSIKLER_TAMAMLAMA_PLANI.md` | Bu dosya — eksikler ve yapılacaklar |
| `CLAUDE.md` §16 | Büyüme Motoru kuralı + test kilitleri |
| `SOP_yukleme.md` §8 | Content ID allowlist prosedürü |

---

**Sonraki Adım:** P0 maddeleri (1-5) bugün içinde kodla → `python auto_process.py --count 8` ile bu haftayı başlat. 🎯