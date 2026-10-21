# BAGLANTI_KURAL.md — Tüm MCP/API/Platform Bağlantı Hafızası (Otomatik Kayıt Kuralı)
# CLAUDE.md §15 uyumlu — Otomatik kaydet, komut bekleme
# Son güncelleme: 2026-09-14 | Otomatik üretildi

---

## KURAL: BAĞLANTI OTOMATİK HAFIZA (Kesin)

**Her MCP/API/Platform bağlantısı anında kaydedilir — komut beklenmez.**

---

## KAYIT FORMATI (JSON)

```json
{
  "baganti_tipi": "mcp|api|platform",
  "ad": "postwire|chrome_devtools|instagram|facebook|bluesky|suno|yt_studio|distrokid",
  "endpoint": "url|server",
  "durum": "bagli|baglanmamis|hata",
  "yetki": "tam|okuma|yazma|planlama",
  "son_kullanim": "2026-09-14T18:30:00Z",
  "notlar": "HyperFollow paylasim icin kullanilacak"
}
```

---

## KAYIT TETİKLEYİCİLER (Otomatik)

| Olay | Eylem |
|------|-------|
| MCP bağlantısı açıldığında | baganti_kaydet("mcp", ...) |
| API çağrısı yapıldığında | baganti_kaydet("api", ...) |
| Platform sayfası açıldığında | baganti_kaydet("platform", ...) |
| Token/key kullanıldığında | baganti_kaydet("api", ...) |
| Hata alındığında | baganti_guncelle("hata", ...) |

---

## KAYIT FONKSİYONLARI (state_io entegreli)

```python
# baganti_kaydet.py - Otomatik kayıt modülü
import json, os
from datetime import datetime
from state_io import atomic_write, load_state

BAGLANTI_DOSYA = "baglanti_hafiza.json"

def baganti_kaydet(tipi: str, ad: str, endpoint: str, durum: str, yetki: str = "tam", notlar: str = "") -> None:
    """Bağlantıyı atomik kaydet (komut beklemez)."""
    try:
        mevcut = load_state(BAGLANTI_DOSYA)
    except:
        mevcut = {}
    
    anahtar = f"{tipi}:{ad}"
    mevcut[anahtar] = {
        "tipi": tipi,
        "ad": ad,
        "endpoint": endpoint,
        "durum": durum,
        "yetki": yetki,
        "son_kullanim": datetime.utcnow().isoformat() + "Z",
        "notlar": notlar
    }
    from state_io import atomic_write
    atomic_write(BAGLANTI_DOSYA, mevcut)

def baganti_getir(ad: str = None) -> dict:
    """Bağlantı(ları) getir."""
    try:
        return load_state("baglanti_hafiza.json")
    except:
        return {}

def baganti_temizle(eski_gun: int = 30) -> None:
    """Eski kayıtları temizle (>30 gün)."""
    try:
        veri = load_state("baglanti_hafiza.json")
    except:
        return
    simdi = datetime.utcnow()
    yeni = {}
    for k, v in veri.items():
        son = datetime.fromisoformat(v["son_kullanim"].replace("Z", "+00:00"))
        if (simdi - son).days <= eski_gun:
            yeni[k] = v
    from state_io import atomic_write
    atomic_write("baglanti_hafiza.json", yeni)
```

---

## MEVCUT BAĞLANTILAR (Otomatik Kaydedildi)

```json
{
  "mcp:chrome_devtools": {
    "tipi": "mcp",
    "ad": "chrome_devtools",
    "endpoint": "pageId:1",
    "durum": "bagli",
    "yetki": "tam",
    "son_kullanim": "2026-09-14T18:45:00Z",
    "notlar": "Instagram/Facebook/Bluesky/HyperFollow/DistroKid sayfalari acildi"
  },
  "mcp:postwire": {
    "tipi": "mcp",
    "ad": "postwire",
    "endpoint": "postwire.io",
    "durum": "bagli_ama_oturum_acik_degil",
    "yetki": "planlama_yayin",
    "son_kullanim": "2026-09-14T18:50:00Z",
    "notlar": "Oturum acik degil - /mcp signin gerekli"
  },
  "mcp:yt_studio": {
    "tipi": "mcp",
    "ad": "yt_studio",
    "endpoint": "youtube.com",
    "durum": "bagli",
    "yetki": "kanal_bilgisi_okuma",
    "son_kullanim": "2026-09-14T15:00:00Z",
    "notlar": "Kanal ID: UCbbcH8rtQTtz8R66jfKoSZG alindi"
  },
  "mcp:suno": {
    "tipi": "mcp",
    "ad": "suno",
    "endpoint": "suno.ai",
    "durum": "bagli",
    "yetki": "uretim_kotasi_gunluk_12",
    "son_kullanim": "2026-09-14T10:00:00Z",
    "notlar": "Gunluk kota 10-12, gunluk hedef 2-3 tamamlanmis"
  },
  "api:distrokid": {
    "tipi": "api",
    "ad": "distrokid",
    "endpoint": "distrokid.com",
    "durum": "bagli",
    "yetki": "yayin_yukleme_istatistik",
    "son_kullanim": "2026-09-14T18:30:00Z",
    "notlar": "Album: 8C68E533-... Gece Masallari - 30+ platforma gonderildi"
  },
  "platform:instagram": {
    "tipi": "platform",
    "ad": "instagram",
    "endpoint": "instagram.com/famous_music_studio",
    "durum": "bagli",
    "yetki": "paylasim_story_reels",
    "son_kullanim": "2026-09-14T18:55:00Z",
    "notlar": "HyperFollow paylasim icin hazir"
  },
  "platform:facebook": {
    "tipi": "platform",
    "ad": "facebook",
    "endpoint": "facebook.com/famousmusicstudio",
    "durum": "bagli",
    "yetki": "paylasim_sayfa",
    "son_kullanim": "2026-09-14T18:55:00Z",
    "notlar": "Sayfa paylasimi, HyperFollow linki"
  },
  "platform:bluesky": {
    "tipi": "platform",
    "ad": "bluesky",
    "endpoint": "bsky.app/profile/famousmusicstudio.bsky.social",
    "durum": "bagli",
    "yetki": "paylasim_post",
    "son_kullanim": "2026-09-14T18:55:00Z",
    "notlar": "HyperFollow linki paylasim icin hazir"
  },
  "api:suno": {
    "tipi": "api",
    "ad": "suno",
    "endpoint": "api.suno.ai",
    "durum": "bagli",
    "yetki": "muzik_uretimi",
    "son_kullanim": "2026-09-14T10:00:00Z",
    "notlar": "Gunluk kota 10-12, gunluk hedef 2-3 parca"
  }
}
```

---

## ENTEGRASYON NOKTALARI (Otomatik Çalışır)

### 1. `gorev_sarmalayici.py` - Her görev başında/sonunda
```python
from baganti_kaydet import baganti_kaydet, baganti_getir

def gorev_basladi(gorev_adi):
    baganti_kaydet("sistem", f"gorev:{gorev_adi}", "local", "basladi", "calisiyor", "Gorev basladi")

def gorev_bitti(gorev_adi, durum):
    baganti_kaydet("sistem", f"gorev:{gorev_adi}", "local", durum, "tamamlandi", f"Gorev bitti: {durum}")
```

### 2. `auto_process.py` - Her çalışmada
```python
# DistroKid kontrol sonrası
baganti_kaydet("api", "distrokid", "distrokid.com", "bagli", "istatistik", "Album durumu kontrol edildi")
```

### 3. `gizli_maskele.py` - Her log yazımında
```python
# Log yazdıktan sonra
baganti_kaydet("sistem", "log_yazildi", "local", "yazildi", "log", f"Satir sayisi: {len(metin)}")
```

---

## KURAL: UNUTMA / KOMUT BEKLEME

> **Her bağlantı anında kaydedilir. Kullanıcı "kaydet" demeden önce sistem kaydeder.**

```python
# Her MCP/API/Platform fonksiyonu başında/sonunda:
try:
    sonuc = mcp_cagir(...)
    baganti_kaydet("mcp", "postwire", "postwire.io", "bagli", "planlama")
    return sonuc
except Exception as e:
    baganti_kaydet("mcp", "postwire", "postwire.io", "hata", "hata", str(e))
    raise
```

---

## DOSYA: `baglanti_hafiza.json` (State.io ile atomik)

```json
{
  "mcp:chrome_devtools": {...},
  "mcp:postwire": {...},
  "mcp:yt_studio": {...},
  "mcp:suno": {...},
  "api:distrokid": {...},
  "platform:instagram": {...},
  "platform:facebook": {...},
  "platform:bluesky": {...},
  "api:suno": {...}
}
```

---

## KURAL KAYIT (CLAUDE.md §15)

```bash
git add baganti_kaydet.py BAGLANTI_KURAL.md baglanti_hafiza.json
git commit -m "rule: baglanti otomatik hafiza kurali eklendi"
```

---

**Kural:** Bu dosya `IS_AKIS.md` içine referans eklenir. Her çalışma başında `baganti_getir()` ile yüklenir, her bağlantı anında `baganti_kaydet()` ile güncellenir. Komut beklenmez.