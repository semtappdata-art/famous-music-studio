# VİDEO TASARIM & KAPAK MODELİ — GERÇEKÇİ KARŞILAŞTIRMA ANALİZİ

**Tarih:** 2026-10-19 | **Mevcut Sistem:** `render.py` + `ffmpeg_utils.py` + `cover_generator.py`  
**Referanslar:** Cercle, Boiler Room, HÖR, Mixmag Lab, Anjunadeep, Bytemounts, Rikodisco, Virtual Clubbing Life, Mahmut Orhan, Burak Yeter, Netd Müzik

---

## 1. MEVCUT TASARIM MODELİMİZ — TEKNİK ÖZET

### 1.1 Uzun Format (16:9) — `render.py` + `ffmpeg_utils.py`

| Bileşen | Mevcut Uygulama | Teknik Detay |
|---------|----------------|--------------|
| **Ana Görsel** | Spotify "Now Playing" kart modeli | Yuvarlak köşeli kart (%45 ekran) + arkadaki aynı görselin blur+pan+hue |
| **Kart Boyutu** | `min(w,h) * 0.45` | 1920x1080'de 864px kare |
| **Kart Köşe** | `CARD_CORNER_RATIO = 0.08` | 8% yuvarlaklık |
| **Arka Plan** | Art.jpg varsa: blur(σ=4.5%) + brightness=-0.12 + sat=1.15 + pan + hue | Pan: sin/cos (0.12Hz/0.08Hz), Hue: ±35° (0.025Hz) |
| **Fallback Arka Plan** | Tema rengine radial gradient + bokeh blob (turkuaz/magenta) | Aynı pan+hue animasyonu |
| **Kayan Yazı (Marquee)** | Kartın ALTINDA, kart genişliğinde, 60px/s | `title + tema etiketleri` tekrar |
| **Sabit Marka Satırı** | "Famous Music Studio" | Kartın altında, aynı font/boyut, beyaz@0.95 |
| **İlerleme Çubuğu** | Ekran altında, genişlik %84, h=%0.8 | Dolgu: 235, Boş: 70 (gri ton) |
| **Kapak (Thumbnail)** | 16:9 + 9:16 otomatik | Başlık alt 1/3'te (h*0.75), max %14 punkt, beyaz+3px siyah outline+gölge |
| **Dikey Hook** | İlk 1sn: "🔊 Sesini Aç" animasyonu | Sadece Shorts/Reels/TikTok |
| **Bölüm Bazlı Görsel** | Verse/Chorus/Bridge = farklı zoom/pan/hue | `caption_align` entegrasyonu (söz varsa) |

### 1.2 DJ Set (16:9 + HDR + Shorts) — `dj_set_video.py`

| Bileşen | Mevcut Uygulama |
|---------|----------------|
| **Format** | Tek parça sürekli video (SDR libx264 + HDR libx265 Main10 + Shorts 9:16) |
| **Arka Plan** | art.jpg → blur + pan + hue (2190x1230 kaynak → 1920x1080 crop) |
| **Overlay** | Set başlığı (sağ üst) + İlerleme çubuğu (alt, tek çizgi, toplam süre) |
| **Chapter** | `segments.json` varsa YouTube chapter timestamp'leri |
| **Çıktılar** | youtube_16x9.mp4, youtube_16x9_hdr.mp4, shorts_9x16.mp4 |

### 1.3 Kapak Üretimi — `cover_generator.py`

| Özellik | Uygulama |
|---------|----------|
| **Çıktılar** | cover.png (16:9) + cover_vertical.png (9:16) + art.jpg (1:1) |
| **Kaynak** | 1) Karakter portresi 2) Elle art.jpg 3) Pexels stok 4) Prosedürel (radial+bokeh) |
| **Başlık Yerleşimi** | Fotoğraf varsa %13 (portre) / %75 (stok) / Prosedürel %50 |
| **Tipografi** | Beyaz + 3px siyah outline + gölge, max %14 punkt, alt 1/3'te |
| **Logo** | Sağ alt, %15 opaklık |
| **Variant B (A/B test)** | Farklı accent2 rengi, sol üst logo, sağ alt başlık |

---

## 2. DIŞ REFERANS ANALİZİ — GLOBAL LİDERLER

### 2.1 Cercle — "Music Meets Cinema" (En Yüksek RPM)

| Özellik | Cercle | Bizim Model | Fark |
|---------|--------|-------------|------|
| **Ort. İzlenme/Set** | **~5.5M** | ~10-50K (tahmin) | **100x+** |
| **Üretim** | 10-20 kişi, 4-8 kamera, 1-4 drone, 1 ay post | 1 kişi, 1 render, dakikalar | **Üretim kalitesi abissi** |
| **Mekan** | Piramitler, Eiffel, Kapadokya balon, Salar de Uyuni | Sanal/mekan yok (sadece art.jpg) | **Hikaye = Mekan** |
| **Thumbnail** | Artist foto + **İkonik Landmark** + Cercle logo | Title + Logo + Art.jpg | **Landmark = CTR motoru** |
| **Başlık** | `Artist @ Location, Country for Cercle` | `Title (Type) | Türkçe X Şarkısı` | **Lokasyon = Marka** |
| **Video İçi** | Multi-cam (drone, steadycam, close-up), color grade sinematik | Tek kamera simülasyonu (pan+hue) | **Kamera dili yok** |
| **Açıklama** | Hook → Tracklist(timestamp) → GPS+Story → Credits → Links | Hook → Tracklist → Location Story → AI Disclosure | **Hikaye derinliği az** |
| **Chapter** | Her track = YouTube chapter (timestamp) | ✅ Var (tracklist varsa) | **Eşleşiyor** |
| **Cross-promo** | IG Reel + TikTok draft + Newsletter + Discord | Plan var, otomasyon eksik | **Manuel vs Otomatik** |

**Cercle Formülü:** `Artist + İkonik Mekan + Sinematik Üretim = 5.5M/set`

---

### 2.2 Boiler Room — "Ham Enerji + Crowd" (En Yüksek Toplam Volume)

| Özellik | Boiler Room | Bizim Model | Fark |
|---------|-------------|-------------|------|
| **Ort. İzlenme/Set** | ~216K | ~10-50K | **10x** |
| **Toplam Volume** | **5.1M abone, 1.77B görüntü** | Düşük | **Arşiv derinliği** |
| **Görsel** | Tek kamera, crowd arkasında, raw | Sanitize, "temiz" | **Enerji vs Estetik** |
| **Thumbnail** | DJ action close-up + Crowd blur + Kırmızı logo | Title + Logo + Art.jpg | **Crowd = Enerji** |
| **Başlık** | `Artist \| Boiler Room: City` | `Title (Type) | Türkçe X Şarkısı` | **Basit, marka odaklı** |
| **Açıklama** | "Instantly iconic..." + Subscribe + Apple Music + Shop | Hook + Tracklist + Links | **CTA zayıf** |
| **Crowd** | **Video’nın yarısı crowd** | Crowd YOK | **İzleyici izole** |
| **Kamera** | Sabit, fish-eye yakın | Simüle pan/hue | **Hareket dili farklı** |

---

### 2.3 HÖR Berlin — "Sabit Cadre + Değişen İçerik" (En Tutarlı)

| Özellik | HÖR Berlin | Bizim Model | Fark |
|---------|------------|-------------|------|
| **Ort. İzlenme/Set** | ~25K | ~10-50K | **Benzer seviye** |
| **Günlük Set** | **4-5 set/gün, 365 gün** | Haftada 3 set | **Ritim farkı 10x** |
| **Cadre** | **Sabit**: Beyaz kare + yeşil neon + pencere | Her set farklı art.jpg | **Marka tanınırlığı yüksek** |
| **Thumbnail** | Artist in booth (fisheye) + Green neon + White tiles | Title + Logo + Art.jpg | **Cadre = Marka** |
| **Kamera** | Tek, fish-eye, sabit | Simüle pan/hue | **Statik vs Dinamik** |
| **Crowd** | **YOK** (sadece DJ) | YOK | **Eşleşiyor** |
| **Arşiv** | **Mükemmel** (tarih bazlı arama) | Takvim.json var | **Arşiv potansiyeli var** |

**HÖR Formülü:** `Sabit Cadre + Günlük Ritim + Arşiv Derinliği = Marka Sadakati`

---

### 2.4 Mixmag Lab — "Pro Stüdyo Haftalık" (En Yüksek Üretim Kalitesi/Tutarlılık)

| Özellik | Mixmag Lab | Bizim Model |
|---------|------------|-------------|
| **Ort. İzlenme/Set** | ~239K | ~10-50K |
| **Üretim** | Pro stüdyo, multi-cam, ışık tasarımı | Tek render pipeline |
| **Thumbnail** | Artist in studio + Purple/pink Lab branding | Title + Logo + Art.jpg |
| **Açıklama** | Full tracklist + timestamps + social + Mixmag article link | Hook + Tracklist + Links |
| **Cross-promo** | Mixmag editorial + newsletter + social clips | Plan var, otomasyon eksik |

---

### 2.5 Anjunadeep / Anjunabeats — "Label Gücü + Progressive Brand"

| Özellik | Anjunadeep | Bizim Model |
|---------|------------|-------------|
| **Playlist Gücü** | Kendi playlist'leri (millionlarca takipçi) | Playlist planı var, henüz yok |
| **Release Pipeline** | Single → Remix EP → Album → Tour | Tek parça odaklı |
| **Artist Development** | Uzun vadeli, marka ortaklığı | Yok |
| **Visual Identity** | Tutarlı, minimalist, marka rengi | Variant B var ama sistematik değil |

---

## 3. TÜRKİYE PAZARI REFERANSLARI

### 3.1 Bytemounts — "Gece Sürüşü POV" (En Yerel + En Doğal)

| Özellik | Bytemounts | Bizim Model |
|---------|------------|-------------|
| **Konsept** | **Dashboard POV + Gece sürüşü** | Statik kart + pan |
| **Thumbnail** | Dashboard/Drone görüntü + Türkçe başlık | Title + Logo + Art.jpg |
| **Video İçi** | Dashboard kamera + yolda görüş + minimal overlay | Simüle pan/hue |
| **Başlık** | `Track Adı \| Turkish Deep House / Melodic Techno` | `Title (Type) | Türkçe X Şarkısı` |
| **Kanal Stratejisi** | "Gece sürüşleri, uzun yollar" + **Türkçe vokal ayrı kanal** | Tek kanal |
| **Kültür Kodu** | **"Gece sürüşü" = Yaşam tarzı** | Yok |

**Bytemounts Formülü:** `POV + Yerel Bağlam + Yaşam Tarzı = Doğal Büyüme`

---

### 3.2 Rikodisco — "Mekân Hikayesi" (En Estetik + Mekân Odaklı)

| Özellik | Rikodisco | Bizim Model |
|---------|-----------|-------------|
| **Mekân** | **Rooftop / Balcony / Boat** (İstanbul Boğazı, Göcek, Alaçatı) | Sanal/mekan yok |
| **Thumbnail** | Mekân fotoğrafı + Artist + Doğal ışık | Title + Logo + Art.jpg |
| **Video İçi** | **Multi-cam (drone, DJ close-up, crowd/mekan)** | Tek kamera simülasyonu |
| **Başlık** | `Artist \| Rooftop DJ Set - Istanbul` | `Title (Type) | Türkçe X Şarkısı` |
| **Mekân Hikayesi** | **İstanbul Boğazı, Göcek, Alaçatı = "Gitmek istediğim yer"** | Hikaye yok |

---

### 3.3 Cafe De Anatolia — "Label Gücü + Oriental House Niche"

| Özellik | Cafe De Anatolia | Bizim Model |
|---------|------------------|-------------|
| **Thumbnail** | Sanat eseri/çizim + Oriental House branding | Title + Logo + Art.jpg |
| **Video İçi** | Statik görsel + minimal animasyon (particle/ambient) | Dinamik pan/hue |
| **Label Gücü** | **300+ artist,playlist ekosistemi** | Tek artist (DJ Famous) |

---

### 3.4 Virtual Clubbing Life (VCL) — "Kurumsal Prodüksiyon + Lokasyon"

| Özellik | VCL | Bizim Model |
|---------|-----|-------------|
| **Prodüksiyon** | **Kontrast.Film** (drone, kamera ekibi, GPS, ekip kredileri) | Tek kişi render |
| **Thumbnail** | 4K Drone + Location + Artist overlay | Title + Logo + Art.jpg |
| **Mekân** | Herakleia, Kapadokya, Bodrum, Kapadokya | Sanal |
| **Başlık** | `Artist - Live @ Venue, Location [Style] Mix` | `Title (Type) | Türkçe X Şarkısı` |

---

### 3.5 Türkçe Pop/Visualiser Liderleri — Mahmut Orhan, Burak Yeter, Tarkan

| Özellik | Liderler | Bizim Model |
|---------|----------|-------------|
| **Visualiser Formatı** | **Albüm kapağı + hafif animasyon** (Tarkan Darmaduman) | Dinamik video render |
| **TikTok Estetiği** | Dikey, hızlı, altyazılı, emoji (Semicenk/Reynmen) | Shorts native var |
| **Sinematik Klip** | Yüksek bütçe, label destekli (Mahmut Orhan, Burak Yeter) | Düşük bütçe, AI |

---

## 4. KARŞILAŞTIRMA MATRİSİ — ÖZET

| Boyut | Bizim Model | Cercle (Global #1) | HÖR (Tutarlılık #1) | Bytemounts (TR #1) | Rikodisco (TR Mekân) | Mahmut Orhan (TR Hit) |
|-------|-------------|---------------------|----------------------|---------------------|----------------------|----------------------|
| **Mekân/Hikaye** | ❌ Yok (soyut art.jpg) | ✅ **Her set benzersiz yer** | ⚠️ Sabit stüdyo | ✅ Dashboard POV (gece yolu) | ✅ Rooftop/Boat (İstanbul/Göcek) | ✅ Sinematik klip lokasyonları |
| **Thumbnail Çeşitliliği** | ⚠️ Şablon (başlık+logo) | ✅ **Landmark değişir** | ✅ Cadre sabit, DJ değişir | ✅ Dashboard/Drone değişir | ✅ Mekân değişir | ✅ Her klip benzersiz |
| **Video İçi Çeşitlilik** | ✅ Pan+hue+bölüm zoom | ✅ Multi-cam, drone, crane | ❌ Tek kamera (fisheye) | ⚠️ Dashboard sabit | ✅ Multi-cam + drone | ✅ Tam klip prodüksiyonu |
| **Chapter/Tracklist** | ✅ Var (tracklist varsa) | ✅ Her track chapter | ❌ (Web'de var) | ❌ | ⚠️ Açıklamada | ✅ YouTube Music |
| **Açıklama SEO** | ⚠️ Temel + AI disclosure | ✅ **Tam şablon** | ⚠️ Minimal | ⚠️ Temel | ✅ Detaylı (GPS, ekip) | ✅ Label standardı |
| **Dikey Platform (Shorts)** | ✅ Hook var, ama 16:9 squeeze | ✅ Native kırpma (drone→drop) | ❌ Shorts az | ✅ Dashboard POV native 9:16 | ✅ Drone/POV native | ❌ Klip kırpması |
| **Cross-Promo** | ❌ Manuel | ✅ Otomatik (Reel/TikTok/Newsletter) | ⚠️ Web/App odaklı | ⚠️ Manuel | ⚠️ Manuel | ✅ Label ekibi |
| **AI Şeffaflığı** | ✅ Sadece metadata/açıklamada | ❌ AI yok (insan DJ) | ❌ AI yok | ✅ "Özgün üretim" vurgusu | ❌ AI yok | ❌ AI yok |
| **Üretim Maliyeti** | ✅ **Düşük (otomatik)** | ❌ Çok yüksek (10-20 kişi, 1 ay) | ✅ Düşük (tek kamera) | ✅ Orta (1-2 kişi) | ❌ Yüksek (ekip+drone) | ❌ Çok yüksek (label) |
| **Ölçeklenebilirlik** | ✅ **Sınırsız** | ❌ Lokasyon darboğazı | ✅ Günlük 4-5 set | ✅ Haftalık 1 set | ❌ Mekân/ekip darboğazı | ❌ Label darboğazı |

---

## 5. EKSİKLİKLERİMİZ — KRİTİK BOŞLUKLAR

### 5.1 Mekân/Hikaye Yok — **En Büyük Fark**
| Referans | Ne Yapıyor | Biz Ne Eksik |
|----------|------------|--------------|
| Cercle | Her set = **benzersiz ikonik mekan** (Piramitler, Eiffel, Kapadokya balon) | **Soyut art.jpg** — mekan yok, hikaye yok |
| Bytemounts | **Dashboard POV = "Gece sürüşü" hissi** | Statik kart |
| Rikodisco | **İstanbul Boğazı, Göcek, Alaçatı = "Gitmek istediğim yer"** | Mekân yok |
| Cercle | **GPS + Story + Location Story** açıklamada | `location.story_tr` var ama görselde yok |

**Etki:** CTR ↓, Paylaşım ↓, Algılama ↓, Abone olma nedeni zayıf

---

### 5.2 Thumbnail Fatigue — **Şablon Yorgunluğu**
| Sorun | Detay | Etki |
|-------|-------|------|
| Aynı şablon | Her videoda: `Başlık (alt 1/3) + Logo (sağ alt) + Art.jpg arka plan` | 10 videodan sonra "bunları biliyorum" → CTR düşüşü |
| Landmark yok | Cercle: landmark değişir; Bytemounts: dashboard değişir | Tanınabilirlik düşük |
| Kültür kodu yok | DJ Muharrem: "ROMAN HAVASI MIX 2025" = kültür kodu | Türkçe kitlede viral potansiyel düşük |

---

### 5.3 Shorts Native Değil — **Squeeze Etkisi**
| Sorun | Detay | Referans Yaklaşımı |
|-------|-------|-------------------|
| 16:9 kart → 9:16 squeeze | Kart dikeyde daralıyor, boşluklar siyah | Cercle: Drone establishing → Drop → Location reveal |
| Hook zayıf | "🔊 Sesini Aç" yazı | Cercle: Drone + Beat drop; Bytemounts: Dashboard POV anında kurar |
| Lower-third yok | Alt 1/3'te marquee + marka satırı | Cercle/Boiler Room: Lower-third minimal |

---

### 5.4 Cross-Promo Otomasyonu Yok
| Eksik | Referans | Etki |
|-------|----------|------|
| Shorts klibi otomatik çıkarma | Cercle: Her set için Reel + TikTok draft + Newsletter | Manuel = zaman kaybı, tutarsızlık |
| Instagram Reel konteyneri otomatik | Cercle: Otomatik 30s vertical hook | Eksik |
| Bluesky thread otomatik | Plan var, kod yok | Eksik |
| TikTok draft otomatik | Plan var, kod yok | Eksik |

---

### 5.5 AI Şeffaflığı — Sadece Metadata'da
| Durum | Detay | Risk |
|-------|-------|------|
| Videoda AI badge YOK | `containsSyntheticMedia: True` + açıklamada "AI DISCLOSURE" | Platform politikası değişirse (zorunlu AI etiketi) retrofit zor |
| Cercle/Boiler Room | AI yok (insan DJ) | N/A |
| Bytemounts | "Özgün üretim" vurgusu | Şeffaflık marka değerli |

---

### 5.6 DJ Set "Sahne Modu" Görselleştirme Eksik
| Config Var | Kodda Kullanılmıyor | Etki |
|------------|---------------------|------|
| `DJ_SAHNE_MODU=True` | `dj_set_video.py`'de kullanılmıyor | Cercle benzeri "drone+steadycam+close-up" hissiyatsiz |
| `DJ_HUD_NEFES`, `DJ_SAHNE_ZOOM` | Render'e geçmiyor | Dinamik hissiyat eksik |

---

### 5.6 Kültür-Kod Etiketleri Eksik (TR Pazarı)
| Referans | Kültür Kodu | Viral Potansiyel |
|----------|-------------|------------------|
| DJ Muharrem | "ROMAN HAVASI MIX 2025" | Milyonlarca izlenme |
| Ali Taş | "90'lar Türkçe Pop" | Nostalji = Paylaşım |
| DJ Famous | **YOK** (sadece tür etiketi) | **Boşluk** |

---

## 6. ÖNCELİKLİ DÜZELTME PLANI (ROI SIRALI)

### P0 — Bu Hafta (Düşük Maliyet, Yüksek Etki)

| # | Aksiyon | Modül | Etki |
|---|---------|-------|------|
| 1 | **Mekân/Hikaye Meta Alanları** — `location{story_tr, landmark, gps}` zorunlu | `validate_project.py`, `meta.json` | Hikayeleştirme↑, CTR↑, SEO↑ |
| 2 | **Series-based Thumbnail** — Landmark + Silüet + Logo şablonu | `cover_generator.py` | CTR %20-30↑ |
| 3 | **Shorts Native Filter** — Tam ekran art + Lower-third (kart squeeze KALDIR) | `ffmpeg_utils.py` | Shorts retention↑, Viral potansiyel↑ |
| 4 | **Content ID Allowlist Prosedürü** — DistroKid günü prosedürü | `SOP_yukleme.md` §8 | Risk sıfırlama |
| 5 | **Test & Compare (A/B Test)** — Variant B otomatik + YouTube Studio entegrasyon rehberi | `cover_generator.py` | CTR optimizasyonu |

---

### P1 — 2 Hafta (Orta Maliyet)

| # | Aksiyon | Modül | Etki |
|---|---------|-------|------|
| 6 | **Mekân/Hikaye Görselleştirme** — `location.landmark` → Kapakta landmark silüeti + GPS | `cover_generator.py` + `config.py` | Cercle benzeri "mekân = kahraman" |
| 7 | **Shorts/Reels Otomatik Klibi** — Hook/Transition/Outro klip kesme | `dj_famous_process.py` | Cross-platform volume↑ |
| 8 | **Bluesky Thread Otomatik** — Track-by-track breakdown | `bluesky_upload.py` | Keşif↑, Topluluk↑ |
| 9 | **Kültür-Kod Serisi** — `arabesk_trap`, `nineties_nostalji` set stilleri + yerel thumbnail | `config.py` + `cover_generator.py` | TR viral potansiyel↑ |
| 10 | **DJ Set Sahne Modu** — `DJ_HUD_NEFES`, `DJ_SAHNE_ZOOM` render'e aktarma | `dj_set_video.py` + `ffmpeg_utils.py` | Cercle benzeri dinamik |

---

### P2 — 1 Ay (Stratejik)

| # | Aksiyon | Modül | Etki |
|---|---------|-------|------|
| 11 | **Sanal Lokasyon Sistemi** — `art_query` → Pexels/Unsplash → "Virtual [City] Rooftop" hikayesi | `stock_art.py` + `config.py:DJ_SERIES` | Cercle modelini "sanal + AI" ile ölçeklenebilir hale getirme |
| 12 | **5-Kamera Simülasyonu** — Art.jpg'den master/tight/detail/wide/gimbal crop zones | `ffmpeg_utils.py` (INDIE_FLAGSHIP_5CAM) | Prodüksiyon kalitesi↑, HDR değer↑ |
| 13 | **Kendi Spotify Playlist'leri** — "City Pulse Sessions" + "Night Drive" | `config.py:SPOTIFY_CALMA_LISTELERI` | Anjunadeep doktrini: "Önce kendi pazarın" |
| 14 | **Collab Pipeline** — Rikodisco/Bytemounts/yerel DJ ile split single | `dj_famous_process.py` + `takvim.py` | Cross-promo motoru |

---

## 7. BEKLENEN METRİK ETKİLERİ (Tahmini)

| Metrik | Mevcut | P0 Sonrası | P1 Sonrası | P2 Sonrası | Referans Hedef |
|--------|--------|------------|------------|------------|----------------|
| **CTR (Thumbnail)** | ~2-3% | **4-5%** | **5-7%** | **7-10%** | Cercle 8-12% |
| **Ort. İzlenme Süresi** | ~40% | **50%** | **55%** | **60%+** | Cercle 55-65% |
| **Shorts Retention (0-3sn)** | ~60% | **75%** | **80%** | **85%+** | Bytemounts 70%+ |
| **Abone Dönüşüm/View** | ~0.1% | **0.2%** | **0.3%** | **0.5%+** | Cercle 0.5%+ |
| **Cross-Platform Volume** | Sadece YT | YT+Shorts | YT+Shorts+Reels+TikTok+Bluesky | Tam ekosistem | Cercle/Mixmag |
| **Haftalık Üretim** | 3 set + 5 parça | Aynı | Aynı + 3-5 klib | Aynı + 10+ klib | HÖR günlük, Cercle haftalık |

---

## 8. SONUÇ VE YOL HARİTASİ

### En Büyük Fırsat: **"Ölçeklenebilir Cercle" Modeli**
> **Gerçek drone/ekip maliyeti olmadan** `art_query` + Pexels/Unsplash + `DJ_SERIES` şablonları ile  
> **"Virtual Istanbul Rooftop", "Virtual Cappadocia Sunrise"** hikayeleri üretilebilir.  
> Bu, **sıfır ek maliyetle Cercle benzeri "lokasyon hikayesi"** verir.

### Türkiye Pazarı İçin: **Bytemounts + Rikodisco Hibriti**
> "Gece sürüşü POV" (düşük maliyet, yüksek native hissiyat) +  
> "İstanbul mekan hikayeleri" (duygusal bağ) +  
> `SET_STILLERI` genişletilip `arabesk`, `roman`, `90lar_nostalji` stilleri → **Türkçe kitlede viral potansiyel**

### Öncelik Sırası (Etki/Maliyet):
1. **P0 (Bu hafta):** Mekân meta alanları + Series thumbnail + Shorts native + Content ID prosedürü + A/B test
2. **P1 (2 hafta):** Mekân görselleştirme + Shorts otomatik klibi + Bluesky thread + Kültür-kod serisi + Sahne modu
3. **P2 (1 ay):** Sanal lokasyon sistemi + 5-kamera simülasyonu + Kendi Spotify playlist'leri + Collab pipeline

---

## 9. BAŞLANGIÇ KONTROL LİSTESİ (Bu Hafta İçin)

```
[ ] config.py → SPOTIFY_CALMA_LISTELERI playlist ID'leri doldur
[ ] config.py → PROMO_DM_SABLONU / PROMO_HAVUZ_BOYUTU ayarla
[ ] DistroKid allowlist aktif mi? (10sn unlisted test)
[ ] takvim.py import + olustur() çalışıyor mu?
[ ] cover_generator.py variant B derlenebiliyor mu?
[ ] validate_project.py 3000x3000 uyarısı + tracklist yer tutucu avı çalışıyor mu?
[ ] youtube_upload.py SPOTIFY_CALMA_LISTELERI okuyor mu?
[ ] youtube_playlists.py add_to_series_playlist fonksiyonu var mı?
[ ] auto_process.py takvim + seri playlist entegre mi?
[ ] SOP_yukleme.md §8 Content ID allowlist prosedürü ekipçe okundu mu?
[ ] promo_havuzu.json (15 DJ) güncel mi?
[ ] YouTube Studio erişimi (Premiere/Topluluk/Analytics) açık mı?
```

**Tümü ✅ → Bu hafta planı `python auto_process.py --count 8` ile başlat.**

---

*Rapor: `VIDEO_TASARIM_KARSILASTIRMA_RAPORU.md` + `PROFESYONEL_LABEL_YOUTUBE_ANALIZI.md` + `HAFTALIK_OPERASYON_PLANI.md` + `BUYUME_ONERILERI.md` — 4 belge, tek tutarlı strateji.*