# HAFTALIK OPERASYON PLANI — PAZARTESİ 00:00 BAŞLANGIÇ

**Kural:** Her hafta Pazartesi 00:00'den itibaren, 4 ajan (Analist, Stratejist, Üretmen, Dağıtımcı) paralel çalışır. Cuma 23:59'a kadar bitmezse plan başarısız sayılır. İstisna YOK.

---

## AJAN TANIMLARI VE YETKİLERİ

| Ajan | Görev Alanı | KPI | Otomasyon Bağlantısı |
|------|-------------|-----|---------------------|
| **A1 — GLOBAL ANALİST** | Global DJ set istihbaratı, trend haritalama, referans kırma | Haftalık 5 global set analizi raporu (Pazartesi 06:00 teslim) | `web_search_exa`, `youtube_stats`, `videojam` tarama |
| **A2 — TÜRKİYE STRATEJİST** | TR YouTube top 10 lider analizi, kültür-kod haritalama, boşluk avcılığı | Haftalık TR top 10 derin analizi + 3 boşluk fırsatı (Pazartesi 08:00 teslim) | `uyumluluk.py` (kültür-kod), `validate_project` (yer tutucu avı) |
| **A3 — ÜRETİM MÜHENDİSİ** | 3 DJ set + 5 parça üretim hattı, Suno prompt mühendisliği, kalite kapıları | 3 DJ set (48-60dk) + 5 parça (3-4dk) Cuma 18:00'a kadar render hazır | `takvim.py` (T-minus), `auto_process.py`, `cover_generator`, `render.py` |
| **A4 — DAĞITIM KOMUTANI** | Upload, playlist, Shorts, topluluk, analitik, Content ID, allowlist | Pazartesi 12:00'ye kadar haftalık dağıtım planı onayı, Cuma 23:59'a kadar %100 yükleme | `auto_process.py`, `youtube_upload.py`, `youtube_playlists.py`, `SOP_yukleme.md` |

**Koordinasyon:** Her ajan çıktıyı bir sonraki ajan girdisi olarak kullanır. Çakışma YOK. Hata toleransı: %0.

---

## PAZARTESİ 00:00 — 06:00 | FAZ 0: VERİ TOPLAMA VE İSTİHBARAT

### A1 — GLOBAL DJ SET İSTİHBARATI (Son 30 Gün)

**Kaynaklar:** Videojam W39-W42, Cercle/Boiler Room/HÖR/Mixmag son yüklemeler, ReachRanking/SPEAKRJ velocity verileri

**Çıktı:** `raporlar/global_istihbarat_YYYY_WW.md` (Pazartesi 06:00'e kadar)

**Analiz Şablonu (her set için):**
```markdown
## SET #X: [Artist] @ [Venue/Location] for [Series/Brand]
- **Yayın tarihi / Kanal / Görünüm / Beğeni / Yorum** (kesin sayı)
- **Süre / BPM aralığı / Anahtar tonalite dağılımı**
- **Mekan tipi:** Rooftop / Club / Open Air / Studio / Unique Location
- **Üretim kalitesi:** Multi-cam / Drone / Single-cam / Visualiser
- **Hook stratejisi (ilk 90sn):** Mekan establishing → Güven veren tanıdık → Keşif
- **Tracklist yapısı:** Kaç parça, ort. süre, tanıdık/ID oranı, edit/remix ağırlığı
- **Thumbnail formülü:** Artist + Landmark + Logo / Studio cadre / Silüet
- **Açıklama iskeleti:** Hook → Tracklist(timestamp) → Location Story → Credits → Links
- **Shorts kırpma:** Kaç klip, hangi anlar (hook/geçiş/outro), native mı squeeze mi
- **Cross-promo:** IG Reel / TikTok / Bluesky / Newsletter / Discord
- **SİZİN İÇİN ÇIKARILAN DERS:** [Tek cümlelik, uygulanabilir kural]
```

**Filtre:** Sadece **melodic techno / progressive house / deep house / organic house** — diğer türler dışarıda.

**Kaldırılanlar:** Tekrar eden artistler, 100K altı görüntü (velocity düşük), pure techno/minimal (bizim lane'imiz değil).

---

### A2 — TÜRKİYE YOUTUBE TOP 10 LİDER ANALİZİ

**Kaynak:** `videojam.live/charts` (son 4 hafta), ReachRanking TR kanalları, kworb.net TR, SocialBlade TR top music.

**Hedef 10 Kanal (örnek — güncel veriyle güncellenir):**
1. Netd Müzik (major label)
2. Mahmut Orhan / Burak Yeter / Emrah Karaduman (artist kanalları)
3. Bytemounts / Rikodisco / Cafe De Anatolia (indie elektronik)
4. DJ Muharrem / Ali Taş (kültür-kod)
5. Virtual Clubbing Life / Virtual DJ Mixes (aggregator)
6. Yeni yükselen: [haftalık tespit]

**Analiz Şablonu (her kanal için):**
```markdown
## KANAL: [Ad] — [Abone / Toplam Görüntü / Ort. Görüntü/Video]
- **İçerik Miks:** %XX Single / %XX DJ Set / %XX Remix / %XX Shorts
- **Thumbnail Stratejisi:** [Artist+Landmark / Studio Cadre / Kültür-Kod Yazı / Visualiser]
- **Başlık Formülü:** [Artist - Title (Type) / Seri Formatı / Kültür-Kod]
- **Açıklama İskeleti:** [Tracklist / Hikaye / Linkler / AI Beyanı / Hashtag]
- **Yayın Ritim:** [Haftada X / Günlük / Festival Sonrası]
- **Shorts Stratejisi:** [Native / Squeeze / Clip / Visualiser]
- **Topluluk Kullanımı:** [Anket / BTS / Kapak A/B / Sıradaki]
- **Kültür-Kod Kullanımı:** [Arabesk / Roman / 90'lar / Anadolu / Yok]
- **Content ID / Allowlist:** [Kendi kanalda claim yiyor mu?]
- **BOŞLUK / FIRSAT:** [Bizim girebileceğimiz boş alan]
```

**Kritik Çıktı:** `raporlar/tr_boluk_analizi_YYYY_WW.md` — **3 tane "girebileceğimiz boşluk"** netleştirilir (ör: "Arabesk-trap sunrise set serisi yok", "90'lar nostalji rooftop serisi yok", "Anadolu enstrümantallı organic house gap").

---

## PAZARTESİ 06:00 — 12:00 | FAZ 1: STRATEJİ KARARLARI VE PLANLAMA

### Toplantı: 06:00-07:00 (Ajan Senkronizasyonu)

**Girdi:** A1 global rapor + A2 TR boşluk analizi
**Çıktı:** `planlar/haftalik_operasyon_YYYY_WW.json` (tek kaynak gerçeği)

### Karar Matrisi (Her hafta yeniden):

| Alan | Karar | Gerekçe | Metrik |
|------|-------|---------|--------|
| **DJ Set 1 (City Pulse)** | Şehir: [Berlin/İstanbul/Tokyo/NYC/London] / Mekan: [TV Tower/Hagia Sophia/...] | Global istihbarattaki en güçlü mekan hikayesi | CTR > 5% |
| **DJ Set 2 (Night Drive)** | Rota: [Mulholland/Sheikh Zayed/Shuto] / Zaman: Gece 22:00 | Bytemounts modeli + City Pulse farklılaşması | Retention > 55% |
| **DJ Set 3 (Deep Focus / Yeni Seri)** | Seri: [Deep Focus / Organic Morning / Boiler Room Style] | TR boşluk analizinden çıkan fırsat | İlk hafta 10K views |
| **Parça 1 (Ana Single)** | Tema: [Aşk/Yalnızlık/Umutsuzluk/Umut] / Tür: [Pop/Arabesk/Elektro/Akustik] | TR boşluk + Suno prompt uygunluğu | İlk 48sa 5K views |
| **Parça 2 (Kültür-Kod)** | Tür: [Arabesk-Trap / 90'lar Nostalji / Anadolu Organic] | TR boşluk analizi | 7 gün 10K views |
| **Parça 3 (Club/İnstrumental)** | Tür: [Melodic Techno / Progressive House / Organic House] | DJ set bridge parçası | Setlerde kullanım |
| **Parça 4 (Vokal/Emosyonel)** | Tema: [Gün doğumu / Gece sürüşü / Hasret] | Playlist bridge | Playlist retention |
| **Parça 5 (Deneysel/Collab)** | Collab hedefi: [Rikodisco / Bytemounts / Yerel DJ] | Cross-promo potansiyeli | Cross-trafik > 5% |

**Kural:** Aynı haftada aynı tür tekrarlanmaz. Aynı tema tekrarlanmaz. Her seri için en az 1 benzersiz mekan/hikaye.

### Çıktı: `planlar/haftalik_operasyon_YYYY_WW.json`

```json
{
  "hafta": "2026-W42",
  "baslangic": "2026-10-19T00:00:00+03:00",
  "bitis": "2026-10-24T23:59:59+03:00",
  "dj_setler": [
    {"id": "CP04", "seri": "city_pulse", "sehir": "Berlin", "mekan": "TV Tower", "gps": "52.5200,13.4050", "hikaye_tr": "Tekno başkenti, beton ve neon, her vuruşta tarih...", "playlist_id": "PL_CityPulse"},
    {"id": "ND02", "seri": "night_drive", "rota": "Mulholland Drive", "sehir": "Los Angeles", "gps": "34.1033,-118.3275", "hikaye_tr": "Şehir ışıkları aşağıda, yıldızlar yukarısında...", "playlist_id": "PL_NightDrive"},
    {"id": "DF01", "seri": "deep_focus", "mekan": "Bali Rice Terraces", "sehir": "Ubud", "gps": "-8.4095,115.1889", "hikaye_tr": "Sabah püskülü Tegallalang, gamelan fısıltısı...", "playlist_id": "PL_DeepFocus"}
  ],
  "parcalar": [
    {"id": "TR01", "tema": "Gece sürüşünde hasret", "tur": "arabesk_trap", "bpm": 140, "ton": "Fm", "sure_sn": 210},
    {"id": "TR02", "tema": "90'lar nostalji rooftop", "tur": "nineties_nostalji", "bpm": 118, "ton": "Am", "sure_sn": 195},
    {"id": "TR03", "tema": "Gece sürüşü bridge", "tur": "melodic_techno", "bpm": 124, "ton": "Cm", "sure_sn": 240},
    {"id": "TR04", "tema": "Gün doğumu umudu", "tur": "organic_house", "bpm": 118, "ton": "G", "sure_sn": 220},
    {"id": "TR05", "tema": "Collab: Rikodisco", "tur": "progressive_house", "bpm": 126, "ton": "Dm", "sure_sn": 250}
  ],
  "takvim": {
    "CP04": {"yayin": "2026-10-24T18:00:00+03:00", "t_minus_5": "2026-10-13", "t_minus_4": "2026-10-14"},
    "ND02": {"yayin": "2026-10-31T22:00:00+03:00", "t_minus_5": "2026-10-20"},
    "DF01": {"yayin": "2026-11-07T10:00:00+03:00", "t_minus_5": "2026-10-27"}
  }
}
```

---

## PAZARTESİ 12:00 — 18:00 | FAZ 2: ÜRETİM BAŞLATMA (A3 LİDERLİĞİNDE)

### 12:00-14:00 — SUNO PROMPT MÜHENDİSLİĞİ VE SES ÜRETİMİ

**Her parça/set için (paralel 5 thread):**

```python
# Örnek Suno Prompt Şablonu (config.py SET_STILLERI + plan JSON'dan)
prompt = f"""
{plan['tur']}, {plan['tema']}, {plan['bpm']} bpm, {plan['ton']},
{suno_stil_ekleri[plan['tur']]},
duration: {plan['sure_sn']}s, structure: intro-verse-chorus-verse-chorus-bridge-chorus-outro,
no vocals (instrumental) / with vocals (vokal varsa),
high quality production, professional mix, mastering ready
"""
```

**Kontrol Noktaları (her üretilen ses için):**
- [ ] BPM ±2 tolerans
- [ ] Ton doğrulaması (librosa)
- [ ] RMS -18dB ile -12dB arası
- [ ] Peak -1dBFS altı
- [ ] 44.1kHz / 24-bit WAV
- [ ] Yapay tespit (Suno artifact kontrolü) — varsa yeniden üret

**Çıktı:** `dj_sets/{SET_ID}/track01.wav` ... `projects/{TR_ID}/audio.wav` — `state.json`'a `audio_ready: true`

---

### 14:00-16:00 — KAPAK VE VİDEO RENDER BAŞLATMA

**Paralel işlemler:**

| Görev | Araç | Süre | Bağımlılık |
|-------|------|------|------------|
| Series thumbnail (A + Variant B) | `cover_generator.py` | 5 dk/set | `meta.json` (series, episode, location) |
| Normal kapak (A + Variant B) | `cover_generator.py` | 3 dk/parça | `meta.json` (title, theme, art_query) |
| DJ set render (16:9 + HDR + Shorts) | `render.py` / `dj_famous_process.py` | 45-90 dk/set | `audio.wav`, `art.jpg`, `segments.json` |
| Parça render (16:9 + Shorts) | `render.py` | 10-15 dk/parça | `audio.wav`, `cover.png`, `art.jpg` |

**Kontrol:** `auto_process.py --count 0 --base dj_sets` (sadece render, upload YOK)

---

### 16:00-18:00 — METADOVALAR VE KALİTE KAPILARI

**Her proje için `meta.json` tamamlama:**

```json
{
  "title": "DJ Famous @ TV Tower, Berlin for City Pulse Sessions",
  "series": "city_pulse",
  "episode": 4,
  "theme": "dj",
  "set_style": "melodic_techno",
  "marquee_text": "City Pulse Sessions • Ep04 • #DJFamous",
  "art_query": "berlin tv tower blue hour rooftop cinematic",
  "location": {
    "city": "Berlin", "country": "Germany", "landmark": "TV Tower",
    "gps": "52.5200,13.4050",
    "story": "Techno capital, concrete and neon, history in every beat",
    "story_tr": "Tekno başkenti, beton ve neon, her vuruşta tarih..."
  },
  "tracklist": [...],
  "end_card_text": "Sıradaki durak: Tokyo",
  "end_card_text_tr": "Sıradaki durak: Tokyo",
  "cross_promo": {
    "shorts_clips": ["hook_0-30s", "transition_mid", "outro_last_3min"],
    "instagram_reel": "30s_vertical_hook",
    "tiktok_draft": "60s_best_moment",
    "bluesky_thread": "track_by_track_breakdown"
  },
  "yayin_tarihi": "2026-10-24T18:00:00+03:00"
}
```

**Validate:** `python validate_project.py --project dj_sets/City_Pulse_Ep4_Berlin` — **HATA sayısı 0 olmalı**

---

## SALI — PERŞEMBE | FAZ 3: ÜRETİM TAMAMLAMA VE KALİTE KONTROLÜ

### Günlük KPI (Her gün 09:00 stand-up):

| Metrik | Hedef | Araç |
|--------|-------|------|
| Suno üretim başarı oranı | %90+ (10 denemede 9) | `audio_highlight.py` + manuel |
| Render başarılı | %100 (hata 0) | `validate_project --all` |
| Kapak varyantları | 100% (A + B her format) | `cover_generator.py --all` |
| Chapter gömülü | %100 (tracklist varsa) | `ffprobe -show_chapters` |
| Metadata eksiksiz | `meta.json` 100% dolu | `validate_project --all` |

### Çarşamba 18:00 — ORTA HAFTA KONTROLÜ

**Rapor:** `raporlar/orta_hafta_kontrol_YYYY_WW.md`

| Proje | Ses | Render | Kapak | Meta | Takvim | Durum |
|-------|-----|--------|-------|------|--------|-------|
| CP04 | ✅ | 🔄 | ✅ | ✅ | ✅ | Render devam |
| ND02 | ✅ | ⏳ | ✅ | ✅ | ✅ | Ses hazır |
| DF01 | ⏳ | ⏳ | ⏳ | ⏳ | ✅ | Suno kuyruğu |
| TR01 | ✅ | ✅ | ✅ | ✅ | ✅ | **HAZIR** |
| TR02 | ✅ | ✅ | ✅ | ✅ | ✅ | **HAZIR** |
| TR03 | ✅ | 🔄 | ✅ | ✅ | ✅ | Render |
| TR04 | ⏳ | ⏳ | ⏳ | ⏳ | ✅ | Suno kuyruğu |
| TR05 | ⏳ | ⏳ | ⏳ | ⏳ | ✅ | Suno kuyruğu |

**Eylem:** Eksiklikler için acil müdahale (Suno yeniden üret, render yeniden başlat).

---

## CUMA | FAZ 4: YÜKLEME VE DAĞITIM (A4 KOMUTANLIĞİNDE)

### 09:00-12:00 — ÖN YÜKLEME KONTROLLERİ

**Her proje için (paralel):**

```bash
# 1. Content ID allowlist testi
python3 upload/test_content_id.py --project dj_sets/City_Pulse_Ep4_Berlin
# → 10sn unlisted test → claim YOK olmalı

# 2. Thumbnail varyantları mevcut mu?
ls dj_sets/City_Pulse_Ep4_Berlin/cover*.png
# → cover.png, cover_vertical.png, cover_variant_B.png, cover_vertical_variant_B.png

# 3. Metadata tam mı?
python validate_project.py --project dj_sets/City_Pulse_Ep4_Berlin
# → HATA: 0, UYARI: kabul edilebilir

# 4. Takvim.json mevcut mu?
cat dj_sets/City_Pulse_Ep4_Berlin/takvim.json

# 4b. Seri playlist ID state'te mi?
grep "youtube_playlists" dj_sets/City_Pulse_Ep4_Berlin/state.json
```

---

### 12:00-18:00 — SIRALI YÜKLEME (A4 KOMUTANLIĞI)

**Sıra (BAĞIMLILIK SIRASI):**

| Sıra | Proje | Platform | Zamanlama | Bağımlılık |
|------|-------|----------|-----------|------------|
| 1 | TR01 (Arabesk-Trap) | YouTube (Shorts + Uzun) | Cuma 12:00 (Golden Hour) | Hazır |
| 2 | TR02 (90'lar Nostalji) | YouTube + Shorts | Cuma 18:00 (Golden Hour) | Hazır |
| 3 | CP04 (City Pulse Ep04) | YouTube + Shorts + Playlist | Cuma 18:00 (Seri saati) | TR01/TR02 bittikten sonra |
| 4 | TR03 (Melodic Techno Bridge) | YouTube + Shorts | Cumartesi 10:00 | CP04 sonrası |
| 5 | TR04 (Organic House) | YouTube + Shorts | Cumartesi 18:00 | TR03 sonrası |
| 6 | CP04 Shorts | YouTube Shorts | Cuma 18:00 (+24sa gecikme) | CP04 uzun yüklendikten 24sa |
| 7 | ND02 (Night Drive) | YouTube + Shorts | Pazar 22:00 (Seri saati) | Gelecek hafta planı |
| 8 | DF01 (Deep Focus) | YouTube + Shorts | Cumartesi 10:00 | Gelecek hafta planı |
| 9 | TR05 (Collab) | YouTube + Shorts | Gelecek hafta | Collab onayı sonrası |

**Her yükleme için `auto_process.py` tetikleyicisi:**
```bash
python auto_process.py --project dj_sets/City_Pulse_Ep4_Berlin --privacy public --no-schedule
# → upload_video → takvim.json oluştur → seri playlist ekle → Shorts 24sa sonra
```

**Hata toleransı:** Yükleme başarısız olursa → `state.json`'a `yukleme_hatasi` yaz, 1 saat sonra 1 kez retry, sonra manuel müdahale.

---

### 18:00-23:59 — DAĞITIM TAMAMLAMA VE KAPANIŞ

**Kontrol Listesi (Hepsi ✅ olmalı):**

- [ ] 3 DJ set YouTube + Shorts yüklendi
- [ ] 5 parça YouTube + Shorts yüklendi
- [ ] Seri playlist'lere eklendi (City Pulse, Night Drive, Deep Focus)
- [ ] Ana playlist (`_tum_sarkilar` + tür playlist'leri) güncellendi
- [ ] `takvim.json` her projeye yazıldı
- [ ] `segments.json` (DJ set) / `chapters.ffmeta` (parça) gömüldü
- [ ] Shorts 24sa gecikmeli kuyruğa alındı
- [ ] Topluluk postları zamanlandı (anket + kapak A/B)
- [ ] Bluesky thread'ler taslak olarak hazırlandı
- [ ] Instagram Reel klip kuyruğuna alındı
- [ ] TikTok draft'lar hazırlandı
- [ ] Content ID allowlist testi geçti (claim 0)
- [ ] End screen kontrolü (uyumluluk.end_screen_kontrol)
- [ ] Analitik raporu: `raporlar/haftalik_kapanis_YYYY_WW.md`

---

## CUMARTESİ — PAZAR | FAZ 5: BÜYÜME MOTORU ÇALIŞTIRIM

### Otomatik (auto_process.py saatlik tetikleyicisi):

- Shorts 24sa gecikmeli süpürge
- Golden-hour kuyruğu boşaltma
- YouTube Analytics raporu
- Kota kontrolü
- End screen kontrolü
- Topluluk postları (anket + kapak A/B) gönderimi
- Bluesky thread'leri yayınlama
- Instagram Reel klip yükleme
- TikTok draft onayı/planlama

### Manuel (Cumartesi 10:00-14:00 — A1/A2 Analiz):

- **A1:** Yeni global setler taraması (son 7 gün) → `global_istihbarat` güncellemesi
- **A2:** TR kanal velocity takibi (son 7 gün) → Hangi kanal hangi formatta büyüdü?
- **Çıktı:** `raporlar/haftalik_büyüme_YYYY_WW.md` — Bir sonraki haftanın planına girdi.

---

## PAZAR | FAZ 6: HAFTALIK KAPANIŞ VE SIRADAKİ HAFTA HAZIRLIĞI

### 18:00-22:00 — KAPANIŞ RAPORU VE SIRADAKİ HAFTA PLANI

**Zorunlu Çıktılar:**

1. `raporlar/haftalik_kapanis_YYYY_WW.md` — KPI tablosu, başarılar/başarısızlıklar, dersler
2. `planlar/haftalik_operasyon_YYYY_WW+1.json` — Bir sonraki hafta planı (taslak)
3. `raporlar/gelecek_hafta_oncelikleri.md` — Öncelik sıralaması + riskler

**KPI Tablosu (Gerçek vs Hedef):**

| Metrik | Hedef | Gerçek | Sapma | Eylem |
|--------|-------|--------|-------|-------|
| DJ Set sayısı | 3 | X | ± | |
| Parça sayısı | 5 | X | ± | |
| YouTube yükleme sayısı | 8 (3 set × 2 + 5 × 1 + Shorts) | X | ± | |
| Shorts 45sn limiti | %100 | X | ± | |
| Content ID claim | 0 | X | ± | |
| CTR (ortalama) | > 4% | X | ± | Kapak A/B testi sonucu |
| AVD (ortalama izlenme) | > 50% | X | ± | |
| Abone artışı | > 50/hafta | X | ± | |
| Cross-promo trafiği | > 5% | X | ± | Bluesky/IG/TikTok |
| Collab başlatılan | 1 | X | ± | TR05 onayı |

---

## TEKNİK ALTYAPI GEREKLİLİKLER (Bir kez kurulum, sonra otomatik)

| Bileşen | Durum | Aksiyon |
|---------|-------|---------|
| `takvim.py` | ✅ Kodlandı | `auto_process.py` entegre edildi |
| `cover_generator.py` variant B | ✅ Kodlandı | `--project` ile test edilecek |
| `validate_project` 3000x3000 + yer tutucu | ✅ Kodlandı | Test edilecek |
| `youtube_upload.py` Spotify playlist | ✅ Kodlandı | `SPOTIFY_CALMA_LISTELERI` config'e eklenecek |
| `youtube_playlists.py` `add_to_series_playlist` | ✅ Kodlandı | Test edilecek |
| `auto_process.py` takvim + seri playlist | ✅ Kodlandı | Test edilecek |
| `takvim.py` | ✅ Kodlandı | `promo_dm_merhaba` şablonu config'te |
| `SOP_yukleme.md` §8 | ✅ Yazıldı | DistroKid günü için hazır |
| `takvim.py` | ✅ `FAZLAR` tanımlandı | `PROMO_DM_SABLONU` config'te |

---

## RİSK YÖNETİMİ VE ACİL DURUM PROTOKOLLERİ

| Risk | Olasılık | Etki | Önlem | Acil Plan |
|------|----------|------|-------|-----------|
| Suno API down / yavaş | Orta | Yüksek | 3 saatlik buffer + manuel prompt | Manuel ses dosyası (yedek stem) |
| Render hata (ffmpeg) | Düşük | Yüksek | `validate_project` öncesi | Farklı codec/preset dene |
| Content ID claim | Orta | Kritik | 10sn unlisted test | Allowlist talep + claim dispute |
| YouTube quota exceeded | Düşük | Yüksek | Kota takibi + erken uyarı | Ertesi güne ertele / unlisted |
| Suno kalite düşük (artifact) | Orta | Orta | 3 deneme kuralı | Farklı prompt varyantı |
| Collab onayı gelmez | Yüksek | Orta | TR05 sonraya bırak | Solo versiyon üret |
| Kapak A/B test sonucu belirsiz | Orta | Düşük | İlk varyant kalır | Manuel seçim |
| DistroKid allowlist gecikme | Orta | Yüksek | 10sn test + manuel Studio | Unlisted + manuel claim release |

---

## SÜREKLİLİK KURALLARI (KESİN)

1. **Pazartesi 00:00** = sıfır noktası. Plan o an kilitlenir. Değişiklik YOK.
2. **Her ajan kendi çıktısını** bir sonraki ajan girdisi olarak teslim eder. Geç teslim = o hafta o alan boş.
3. **Cuma 23:59** = kesin bitiş. Yüklenmemiş = ertesi haftaya ertelenmez, **silinir**.
3. **Veri gizliliği:** API key/token `.env` ve `.secrets/` — repoda YOK.
4. **Test zorunluluğu:** Yeni kod = test + CI geçmeli. Test yazmadan kod yazılmaz.
5. **Belge güncelleme:** Kod değiştiyse `CLAUDE.md`, `SOP`, `BUYUME_ONERILERI.md` aynı commit'te güncellenir.

---

## BAŞLANGIÇ KONTROL LİSTESİ (Bu hafta için — Pazartesi 00:00'da kontrol)

- [ ] `config.py` → `SPOTIFY_CALMA_LISTELERI` dolduruldu mu? (playlist_id'ler)
- [ ] `config.py` → `PROMO_DM_SABLONU` / `PROMO_HAVUZ_BOYUTU` ayarlandı mı?
- [ ] `config.py` → `SPOTIFY_CALMA_LISTELERI` boş değil mi?
- [ ] DistroKid allowlist aktif mi? (10sn test)
- [ ] `takvim.py` import edilebiliyor mu? (`python -c "import takvim"`)
- [ ] `cover_generator.py` variant B derlenebiliyor mu?
- [ ] `validate_project.py` 3000x3000 uyarısı veriyor mu?
- [ ] `youtube_upload.py` `SPOTIFY_CALMA_LISTELERI` okuyor mu?
- [ ] `youtube_playlists.py` `add_to_series_playlist` fonksiyonu var mı?
- [ ] `auto_process.py` takvim + seri playlist entegre mi?
- [ ] `takvim.py` import + `olustur` fonksiyonu çalışıyor mu?
- [ ] `SOP_yukleme.md` §8 Content ID allowlist prosedürü ekipçe okundu mu?
- [ ] `promo_havuzu.json` (15 DJ) güncel mi?
- [ ] `SPOTIFY_CALMA_LISTELERI` playlist ID'leri geçerli mi?
- [ ] YouTube Studio erişimi (Premiere/Topluluk/Analytics) açık mı?

**Tümü ✅ ise → Plan o hafta çalışır. Herhangi biri ❌ ise → O hafta plan YAPILMAZ, eksiklik giderilene kadar bekler.**

---

**Bu plan değiştirilmez. Uygulanır. Her Pazartesi 00:00'da yeni kopya üretilir, eskisi arşivlenir.**

---

*Son güncelleme: 2026-10-19 | Versiyon: 1.0 | Onay: A1-A2-A3-A4 senkron*