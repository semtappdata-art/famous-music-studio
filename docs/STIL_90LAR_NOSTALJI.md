# Set Stili: `nineties_nostalji` — Kültür-Kod Serisi

**Durum:** Aktif (`config.SET_STILLERI`) · **Referans set:** `projects/TR02_90larNostalji`
**Ekleyen:** Büyüme Motoru Madde 15 (kültür-kod stilleri) · **Tarih:** 2026-10-19

---

## 1. Neden Bu Stil Var

"90'lar" Türkçe pop kültüründe **kültür kodu** — Ali Taş, Sezen Aksu, Nilüfer
Yumlu dönemi. Bu kodu taşıyan içerik:

1. **Paylaşılabilirlik** — "90'lar Türkçe Pop" etiketi nostalji tetikler,
   paylaşım motivasyonu yüksektir.
2. **Arama hacmi** — "90'lar Türkçe pop", "eski Türkçe pop", "nostalji"
   sorguları sürekli arama hacmine sahip.
3. **Yapay zeka ile "bilinmeyen" değil** — yeni bir arka plan değil, tanıdık
   bir çağrışım. AI müzik ile nostalji kombinasyonu 2024-2026'da yükselen
   bir içerik türü.

**Hedef:** Nostalji paylaşımıyla erişimi (reach) genişletmek, beğeni
oranını yükseltmek.

---

## 2. Ses Kimliği (Suno Prompt)

```
90s turkish pop revival, bright synth brass, nostalgic melody,
danceable 118 bpm, retro production with modern mix, turkish vocal
```

| Parametre | Değer | Neden |
|-----------|-------|-------|
| BPM | 118 | 90'lar Türkçe pop dans temposu (hızlı değil, groove'lu) |
| Enstrüman | Synth brass + parlak akorlar | Dönemin imza sound'u |
| Prodüksiyon | "Retro production with modern mix" | Sadece lo-fi değil — temiz |
| Vokal | Türkçe | Arama niyeti |

---

## 3. Görsel Dil (Video Sorgusu)

```
vintage tv static retro living room
cassette tape close up warm light
retro istanbul street 90s film grain
neon retro arcade night glow
```

- **Renk:** Sıcak amber / CRT mavisi karışımı, film grain dokusu
- **Mekân:** 90'lar İstanbul'u, CRT TV, kaset, oyun salonu
- **Hareket:** Yavaş pan + hafif hue (analog sıcaklık hissi)

---

## 4. Caption/Hashtag Kuralları

- **Marka:** `#FamousMusicStudio` (her zaman ilk)
- **Keşif:** `#keşfet #fyp #viral` (3 tane)
- **Kültür-kod:** `#90larTurkcePop` (Title Case, videoda mavi overlay)
- **Ton:** Nostaljik, paylaşıma davet eden

### Yasak (Kural §2 / test_kurallar.py)

- ❌ `yapay zeka` / `ai generated` hashtag'i — `#AIGenerated` yalnız açıklamada
- ❌ "90'lar" ifadesini yazarken kesme işareti/emoji karışımı — düz metin

---

## 5. Platform Kuralları

| Platform | Kural |
|----------|-------|
| YouTube | Başlık: `{title} (Sözleri) \| Türkçe Pop Şarkısı`; credits + playlist linki |
| Shorts | 45sn highlight, native 9:16, **mavi Title Case hashtag overlay** |
| TikTok | Taslak, elle yayın |
| Instagram | Reels konteyneri — 23 saat ömür |
| Facebook | Native schedule |
| Telegram/Bluesky | `ek_platform_backfill.py` (golden hour + politika kapısı) |

---

## 6. Yayın Ritmi

- **Yayın günleri:** Pazartesi / Çarşamba / Cuma
- **Saatler:** 12:00 ve 18:00 TR
- **Tempo tabanı:** Yeni yayınlar arası **en az 52 saat**

---

## 7. Referans Set: `projects/TR02_90larNostalji`

| Alan | Değer |
|------|-------|
| `set_style` | `nineties_nostalji` |
| `theme` | `pop` (90'lar Türkçe pop) |
| `segments.json` | 6 bölüm |
| `tracklist` | 6 bölüm → chapter üretilebilir |

**Öğrenilen dersler:**
- "90'lar" etiketi nostalji paylaşımını tetikler
- Sıcak amber görsel dil + dans temposu birlikte çalışır
- Bölüm bazlı görsel (chorus'ta zoom/hue) izlenme süresini artırdı

---

## 8. Ölçüm (BÜYÜME Madde 17)

```bash
python olcum_temel_cizgi.py --cek
```

3 aylık hedef: **ort. izlenme 150 → 500**, **like oranı %2.4 → %3.5+**

---

## İlgili Dosyalar

| Dosya | Rol |
|-------|-----|
| `config.py` → `SET_STILLERI["nineties_nostalji"]` | Stil tanımı |
| `projects/TR02_90larNostalji/` | Referans set |
| `tests/test_buyume_onerileri.py::test_kultur_kod_stilleri` | Stilin varlık testi |
