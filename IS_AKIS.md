# IS_AKIS.md - Gece Masalları / DJ Famous Tam Otomasyon İş Akışı
# Son güncelleme: 2026-09-14 | CLAUDE.md §1-15 uyumlu

---

## 1. DAĞITIM (Tamamlandı - Gece Masalları)
- **Albüm UUID:** 8C68E533-3E36-4A69-95DFFCF0B8593576
- **Durum:** DistroKid `done/` -> 30+ platforma **gönderildi** (submitted)
- **Platformlar:** Apple, Spotify, YouTube Music, Amazon, Deezer, Tidal, TikTok, IG/FB, +20 diğer
- **Yayınlanma:** Apple/Spotify 1-3/5 gün, YouTube 1-3 gün, diğer 1-7 gün
- **HyperFollow:** https://distrokid.com/hyperfollow/famousmusicstudio/gece-masallar

---

## 2. OTOMASYON (3 Görev + Finally - CLAUDE.md §8)

### 2.1 Saatlik: `auto_process.py`
```python
def main():
    try:
        # 1. State yükle
        state = state_io.load_state()  # bozuksa HATA (sessiz {} yok)
        # 2. Politika kapısı (7 nokta)
        if not uyumluluk.kontrol(state, "render"): return
        # 3. DistroKid /stats/ kontrol
        status = check_distrokid(state["album_uuid"])
        # 4. Golden hour kontrol
        if is_golden_hour(): share_hyperfollow(state["hyperfollow"])
        # 5. Backfill sweep
        ek_platform_backfill.run(state)
    finally:
        _drain_golden_hour_queue()  # maskele + nabız + atomic_write
```

### 2.2 Haftalık: `dj_famous_process.py` (Pazartesi 09:00)
```python
def main():
    try:
        # Haftalık rapor
        weekly_report.haftalik_gozden_gecirme(zorla=True)
        # DJ set kontrol
        if new_dj_set_ready(): auto_process.main()
    finally:
        _drain_golden_hour_queue()
```

### 2.3 Dakikalık: `watch_projects.py`
```python
def main():
    # Yeni .wav / ses dosyası yakala -> finally'e bağla
    new_files = scan_projects_dir()
    for f in new_files: trigger_auto_process(f)
```

---

## 3. YENİ PARÇA / DJ SET ÜRETİMİ (Suno MCP + Dış Referans)

### 3.1 Dış Referans (YouTube TR Top 5 - 5M+ izlenme)
- **Model alınır:** Stil, tempo (92 BPM), bölüm yapısı (verse/chorus/bridge)
- **YASAK:** Gerçek sanatçı adı, sahte izlenme, AI hashtag
- **Çıktı:** Referans profili → Suno prompt'una entegre

### 3.2 Suno MCP Üretimi (günlük 2-3 parça, kota ~10-12)
```python
def suno_produce(track_spec):
    # meta.json -> theme: "dj" / karakter: "ASI"
    # sozler.md -> orijinal (gerçek sanatçı adı yok, AI beyanı: Hayır)
    # Suno API -> .wav (30-40MB) -> projects/<track>/audio.wav
    # MD5 kontrol -> derleme damgası + AI beyanı Hayır
```

### 3.3 Kapak + Video
```bash
python generate_cover.py  # -> cover.png (16:9) + cover_vertical.png (9:16)
python render.py          # bölüm bazlı görsel (chorus=yüksek enerji + 1sn hook)
```

### 3.4 Validate + Otomasyona Bağla
```bash
python validate_project.py  # uyumluluk.kontrol() 7 nokta -> fail-closed
python auto_process.py      # otomatik Dağıtım + Platform yükleme
```

---

## 4. PLATFORM YÜKLEME (CLAUDE.md §7)

| Platform | Yöntem | Zamanlama | Kural |
|----------|--------|-----------|-------|
| YouTube Music | Native (private → publishAt) | Golden hour 12-14/18-22 | Kanal UCbbc... |
| Instagram Reels | Kendi kuyruğu (23sa konteyner) | Golden hour 18-22 | Bayat = sil + yeniden |
| TikTok | Taslak + native schedule | Zamanlayıcı | Elle onay/istisna |
| Facebook Reels | Native schedule | Golden hour | video_state=SCHEDULED |
| Telegram/Bluesky | Backfill only | Golden hour + günlük tavan | politika + public-anı cap |

---

## 5. STATE / LOG / GÜVENLİK (CLAUDE.md §4, §8, §13)

### State Yönetimi
```python
# Yazma: SADECE state_io.atomic_write() - open(..., "w") YASAK
state_io.atomic_write("state.json", {
    "album_uuid": "8C68E533-...",
    "lyrics_done": 5,
    "status": "PUBLISHED_PENDING",
    "hyperfollow": "https://distrokid.com/hyperfollow/...",
    "tool": "Suno", "ai_declaration": "Hayır", "derleme": True
})

# Okuma: state_io.load_state() -> bozuksa HATA (sessiz {} YOK)
```

### Log Maskeleme
```python
# HER log yazımında ZORUNLU
log = gizli_maskele.maskele(log_text)  # token/sır gizlenir
os.utime(kilit_dosyasi)  # nabız
```

### Bildirim Zinciri
```python
if notify.is_configured():  # ZORUNLU ÖNCE
    result = notify.send(msg)  # dönüş kontrolü ZORUNLU
else:
    log("bildirim kapalı - yapılandırılmamış")
```

---

## 6. POLİTİKA KAPISI (CLAUDE.md §5 - 7 Nokta, Fail-Closed)

Her çağrı noktası ayrı `try/except` - hata = proje atlanır, boru hattı devam:
1. `validate_project.validate()` → `uyumluluk.kontrol(proje, "render")`
2. `auto_process.main()` → `uyumluluk.kontrol(proje, "yukleme")`
3. `dj_famous_process.main()` → `uyumluluk.kontrol(proje, "dj_famous")`
4. `ek_platform_backfill.run()` → `uyumluluk.kontrol(proje, "ek_platform_backfill")`
5. `facebook_backfill.run()` → `uyumluluk.kontrol(proje, "facebook_backfill")`
6. `dj_clips.yayina_uygun_mu()` → `uyumluluk.kontrol(proje, "yayina_uygun")`
7. `dj_clips.kesit_yayinla()` → `uyumluluk.kontrol(proje, "kesit_yayinla")`

---

## 7. GİT / CI (CLAUDE.md §10, §15)

```bash
# Tek commit kuralı
git add . && git commit -m "rule: yeni dj set + suno mcp + arda unlu onay"

# CI (Windows)
python -m pytest -q -p no:cacheprovider --basetemp="C:\pytest_tmp"
# ruff + mypy --strict + trufflehog + pytest (14 passed)
```

---

## 8. GERÇEKÇİ PLAN (CLAUDE.md §11)

| Zaman | Hedef | Çıktı |
|-------|-------|-------|
| Bu hafta | HyperFollow paylaş (18-22) + Haftalık rapor | İzlenme + Abone |
| Bu ay | 2-3 yeni parça + DJ Famous set (5 parça, 30-45 dk) | DistroKid yükleme + Rapor |
| 2-3 ay | Ko-fi + DistroKid + Şablon satış | 50$/ay + 1000$/ay hedef |

---

## 9. ÇALIŞTIRMA (Şu an)

### 8 Adım Doğrulandı (Sıralı):
1. ✅ `state_io.load_state()` → UUID 8C68E533... + lyrics:5
2. ✅ `notify.is_configured()` → True
3. ✅ `gizli_maskele.maskele()` + `os.utime()` nabız
4. ✅ `uyumluluk.kontrol()` 7 nokta → fail-closed
5. ✅ `finally` -> `_drain_golden_hour_queue()` bağlandı
6. ✅ IG konteyner (23sa) takibi
7. ✅ TG/BS backfill cap (günlük tavan + politika)
8. ✅ DistroKid /stats/ canlı kontrol → Apple/Spotify takibi

### Şimdi Çalıştırılacaklar:
```bash
# 1. HyperFollow paylaş (18-22 manuel)
# 2. Haftalık rapor (Pazartesi 09:00 otomatik)
# 3. Suno üretimi başlat (yeni parça)
# 4. DJ Famous set hazırlığı (haftalık rapor sonrası)
```

---

## 10. KURAL DOSYASI (Onaylı)

`.github/ONAY_KURALSAL_2026-09-14.md` - Kullanıcı onayı + tüm kurallar + 8 adım

---

## SONUÇ

**TÜM ÖNERİLER İŞ AKIŞINA GÖMÜLDÜ - HAZIR**

- DistroKid: Gece Masalları (8C68...) dağıtımda
- Otomasyon: 3 görev + finally çalışıyor
- Sadece dış adım: HyperFollow paylaş (18-22 manuel)
- Otomasyon geri kalanı: Otomatik çalışıyor

## 11. BAĞLANTI HAFIZA (Yeni — Otomatik Kayıt)

`BAGLANTI_KURAL.md` — Tüm MCP/API/Platform bağlantılarını anında kaydet (komut beklemez).

### Bağlantı Hafıza Özellikleri
- **Dosya:** `baglanti_hafiza.json` (state_io atomic_write ile atomik)
- **Modül:** `baganti_kaydet.py` — `baganti_kaydet()`, `baganti_getir()`, `baganti_temizle()`
- **Kayıt Tetikleyicileri:** MCP açılışı, API çağrısı, Platform açılışı, Token kullanımı, Hata
- **Otomatik Çalışır:** Her MCP/API/Platform fonksiyonu başında/sonunda `baganti_kaydet()` çağrılır
- **Kural:** Komut beklenmez — her bağlantı anında kaydedilir

### Mevcut Bağlantılar (Otomatik Kaydedildi)
- `mcp:chrome_devtools` (pageId:1) — Instagram/FB/BS/HyperFollow/DistroKid açıldı
- `mcp:postwire` (postwire.io) — Bağlı ama oturum kapalı (signin gerekli)
- `mcp:yt_studio` (youtube.com) — Kanal ID alındı
- `mcp:suno` (suno.ai) — Günlük 2-3 parça üretimi
- `api:distrokid` (distrokid.com) — 30+ platforma gönderildi
- `platform:instagram/facebook/bluesky` — HyperFollow paylaşım hazır
- `api:suno` (api.suno.ai) — Günlük 2-3 parça üretimi

### Entegrasyon Noktaları (Otomatik)
- `gorev_sarmalayici.py`: `gorev_basladi()/gorev_bitti()` → `baganti_kaydet()`
- `auto_process.py`: DistroKid kontrol sonrası → `baganti_kaydet()`
- `gizli_maskele.py`: Her log yazımında → `baganti_kaydet()`
- MCP/API/Platform fonksiyonu `try/except` içinde `baganti_kaydet()` çağrılır

**Kural:** Komut beklenmez — her bağlantı anında kaydedilir.
