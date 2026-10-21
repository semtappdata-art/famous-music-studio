# Set Stili: `arabesk_trap` — Kültür-Kod Serisi

**Durum:** Aktif (`config.SET_STILLERI`) · **Referans set:** `projects/TR01_ArabeskTrap`
**Ekleyen:** Büyüme Motoru Madde 15 (kültür-kod stilleri) · **Tarih:** 2026-10-19

---

## 1. Neden Bu Stil Var

Türkçe YouTube'da **tür bazlı arama trafiği** en güvenilir keşif kanalı. `arabesk`
temi katalogda en yüksek ortalamayı taşıyor (285 izlenme/video, 24 videoda
en iyi 2. sıra) — ama **"Arabesk Trap"** etiketiyle yeni bir niş açmak iki şeyi
birleştiriyor:

1. **Arama hacmi** — "arabesk trap", "arabesk remix", "damar arabesk" gibi
   sorgular TR kitlesinde yüksek ve rakip yoğunluğu düşük.
2. **Kültür kodu** — DJ Muharrem / Ali Taş örneğindeki gibi yerel referans
   ("90'lar arabesk", "damar mix") kültürel aidiyet kurar; saf "AI şarkı"
   etiketi taşımaz.

**Hedef:** TR kitlede "acı" ve "nostalji" duygusunu paylaşan kesime ulaşmak.

---

## 2. Ses Kimliği (Suno Prompt)

```
arabesk trap fusion, emotional turkish string melody, deep 808 bass,
slow tempo 140 bpm half-time, late night damar mood, turkish vocal
```

| Parametre | Değer | Neden |
|-----------|-------|-------|
| BPM | 140 (half-time) | Arabesk'in ağır, yavaş hissi; trap 808 ile buluşunca "damar" |
| Melodi | Türk bağlama | Kanun/harmonyum tınısı — arabesk ayırt edici |
| Vokal | Türkçe | Arama niyeti + duygusal bağ |
| Mood | "Late night damar" | Gece 00:00-04:00 kültür kodu |

---

## 3. Görsel Dil (Video Sorgusu)

```
rainy istanbul street night neon reflections
car interior night drive city lights bokeh
smoke dark background slow motion gold
bosporus bridge night lights long exposure
```

- **Renk:** Koyu + altın/amber vurgular (`accent` sarı-amber ailesi)
- **Mekân:** İstanbul (Boğaz, arabesk mahallesi, yağmurlu cadde)
- **Hareket:** Yavaş pan + hafif hue salınımı (nabız 25sn'de)

---

## 4. Caption/Hashtag Kuralları

- **Marka:** `#FamousMusicStudio` (her zaman ilk)
- **Keşif:** `#keşfet #fyp #viral` (3 tane — `DISCOVERY_HASHTAG_COUNT`)
- **Kültür-kod:** `#ArabeskTrap` (Title Case, videoda mavi overlay olarak görünür)
- **Ton:** Türkçe, samimi, "damar" kelimesi türe özgü

### Yasak (Kural §2 / test_kurallar.py)

- ❌ `yapay zeka` / `ai generated` gibi hashtag'ler — `#AIGenerated` **sadece**
  açıklama metninde, etiket olarak **değil**
- ❌ "keşfet/fyp" dışında 3'ten fazla keşif hashtag'i

---

## 5. Platform Kuralları

| Platform | Kural |
|----------|-------|
| YouTube | Başlık: `{title} (Sözleri) \| Türkçe Arabesk Şarkısı`; açıklamada credits + playlist linki |
| Shorts | 45sn highlight, native 9:16, **mavi Title Case hashtag overlay** |
| TikTok | Taslak olarak yükle, **elle yayınla** (`tiktok_publish_plan.py`) |
| Instagram | Reels konteyneri (23 saat ömür) — bayat olursa sil + yeniden |
| Facebook | Native schedule (`video_state=SCHEDULED`) |
| Telegram/Bluesky | Yalnız `ek_platform_backfill.py` (golden hour + politika kapısı) |

---

## 6. Yayın Ritmi

- **Yayın günleri:** Pazartesi / Çarşamba / Cuma
- **Saatler:** 12:00 ve 18:00 TR (golden hour)
- **Tempo tabanı:** Yeni yayınlar arası **en az 52 saat**
- **Kanal takvimi:** `takvim.py` → `planlar/`

---

## 7. Referans Set: `projects/TR01_ArabeskTrap`

Bu set, stilin "kültür-kod" boyutunun kanıtıdır:

| Alan | Değer |
|------|-------|
| `set_style` | `arabesk_trap` |
| `theme` | `arabesk` |
| `art_query` | (stilin sorgu havuzundan) |
| `marquee_text` | `DJ Famous • ...` |
| `segments.json` | 6 bölüm (bölüm bazlı görsel: verse/chorus farklı zoom/hue) |
| `tracklist` | 6 bölüm → YouTube chapter üretilebilir |
| `chapters.ffmeta` | Render sırasında otomatik üretilir |

**Öğrenilen dersler (bu setten):**
- Yavaş tempo + 808 = arabesk-trap harmanı çalışıyor
- Bölüm bazlı görsel (chorus'ta hue/zoom vurgusu) izlenme süresini artırdı
- Title Case hashtag overlay Shorts keşfini belirginleştirdi

---

## 8. Ölçüm (BÜYÜME Madde 17)

Bu stil değişikliği **tek değişiklik** olarak yapıldı. Ölçüm:

```bash
python olcum_temel_cizgi.py --cek
```

Değişiklik öncesi/sonrası karşılaştırması `olcum_temel_cizgi.json`'da tutulur.
Kültür-kod serisinin 3 aylık hedefi: **ort. izlenme 150 → 500**.

---

## İlgili Dosyalar

| Dosya | Rol |
|-------|-----|
| `config.py` → `SET_STILLERI["arabesk_trap"]` | Stil tanımı (etiketler, sorgular, Suno prompt) |
| `projects/TR01_ArabeskTrap/` | Referans set |
| `validate_project.py` | `set_style` zorunlu alan kontrolü |
| `tests/test_buyume_onerileri.py::test_kultur_kod_stilleri` | Stilin varlık testi |
