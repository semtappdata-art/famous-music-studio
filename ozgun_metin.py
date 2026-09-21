# -*- coding: utf-8 -*-
"""Özgün metin alanları: hikâye paragrafı, "neden bu şarkı" notu, YouTube başlık kalıbı
rotasyonu (ozgunluk_plani.md §2c ve §2e, onaylanan kararlar 2 ve 3, 2026-09-13).

HİKÂYE (`meta.json`):
  * `hikaye`: 2-4 cümle — şarkının çıktığı an, reddedilen taslak, değişen bir satır ve nedeni.
  * `neden_bu_sarki`: 1 cümle.
  * Yasak: "Suno"/üretim aracı adı, AI vurgusu ("yapay zeka", "AI"), dış link. Zorunlu AI
    beyanı (YouTube `containsSyntheticMedia`, TikTok/IG/FB beyan satırı) bu alanlardan
    BAĞIMSIZ ve dokunulmaz.
  * Yalnız YouTube UZUN açıklamasına girer (`youtube_upload.build_snippet`); Shorts, TikTok,
    Instagram, Facebook kısa metinlerine girmez. Yasak içerik taşıyan hikâye açıklamaya HİÇ
    girmez (kapı uyarı düzeyindeyken bile).
  * KAPI (`uyumluluk.kontrol(..., "yukleme")`): yalnız ana katalogdaki YENİ şarkı
    (`youtube_video_id` yok; derleme ve DJ hariç). `config.HIKAYE_KAPISI_TARIHI` öncesi
    UYARI, o gün ve sonrası HATA → fail-closed kapı yayını durdurur.

BAŞLIK KALIBI (`config.YOUTUBE_BASLIK_KALIPLARI`):
  * "Sözleri" her kalıpta (arama niyeti, 2026-09-06 kararı).
  * Yalnız YENİ yüklemede (`youtube_upload.upload_video`, `youtube_video_id` yokken) seçilir ve
    state'e `youtube_baslik_kalibi` olarak yazılır; `fix_description` o kaydı okur, kaydı
    olmayan eski videolar K1'de kalır (geçmiş başlıklara dokunulmaz).
  * Seçim deterministik (başlık sha1'i) ve bir önceki yeni yayının kalıbı aday DEĞİL; kalıp
    kaydı olmayan eski yayın K1 sayılır (20/20 eski başlık K1, plan §1.2).

ÜÇ SORU: çağıranlar `youtube_upload.build_snippet/upload_video/fix_description` ve
`uyumluluk.kontrol`; saatlik `auto_process.py` (yükleme) — yeni görev yok; kapı uyarı/hatası
`uyumluluk.rapor_yaz` ile log'a düşer, koruma `tests/test_hikaye_ve_baslik.py`.
"""

import datetime
import hashlib
import json
import os
import re
import time

import config

YASAK_RE = re.compile(r"yapay\s*zek[aâ]|\bai\b|\ba\.i\.|suno|https?://|www\.|\b[\w-]+\.(com|net|org|io)\b",
                      re.IGNORECASE)
_CUMLE_RE = re.compile(r"[^.!?…]+[.!?…]+|[^.!?…]+$")

VARSAYILAN_KALIPLAR = (
    {"id": "K1", "sablon": "{title} (Sözleri) | Türkçe {tur} Şarkısı"},
    {"id": "K2", "sablon": "{title} — Sözleri | Famous Music Studio"},
    {"id": "K3", "sablon": "{title} (Sözleri) · {baslik_eki}", "gerekli": "baslik_eki"},
)
VARSAYILAN_KALIP = "K1"


# --------------------------------------------------------------------------
# Hikâye
# --------------------------------------------------------------------------

def yasak_bul(metin) -> list:
    return [m.group(0) for m in YASAK_RE.finditer(str(metin or ""))]


def cumle_sayisi(metin) -> int:
    return sum(1 for c in _CUMLE_RE.findall(str(metin or "").strip()) if c.strip(" .!?…"))


def hikaye_hatalari(meta) -> list:
    """Boş liste = `hikaye` + `neden_bu_sarki` geçerli. Metinler kullanıcıya okunur."""
    meta = meta or {}
    hatalar = []
    hikaye = meta.get("hikaye")
    neden = meta.get("neden_bu_sarki")
    if not isinstance(hikaye, str) or not hikaye.strip():
        hatalar.append("`hikaye` eksik (2-4 cümle)")
    else:
        n = cumle_sayisi(hikaye)
        if not 2 <= n <= 4:
            hatalar.append("`hikaye` 2-4 cümle olmalı (şu an %d)" % n)
        if yasak_bul(hikaye):
            hatalar.append("`hikaye` yasak ifade içeriyor (%s)" % ", ".join(yasak_bul(hikaye)))
    if not isinstance(neden, str) or not neden.strip():
        hatalar.append("`neden_bu_sarki` eksik (1 cümle)")
    else:
        if cumle_sayisi(neden) != 1:
            hatalar.append("`neden_bu_sarki` 1 cümle olmalı (şu an %d)" % cumle_sayisi(neden))
        if yasak_bul(neden):
            hatalar.append("`neden_bu_sarki` yasak ifade içeriyor (%s)"
                           % ", ".join(yasak_bul(neden)))
    return hatalar


def aciklama_paragrafi(meta) -> str:
    """Uzun açıklamaya girecek hikâye metni; alan yoksa ya da yasak ifade taşıyorsa ""."""
    hikaye = (meta or {}).get("hikaye")
    if not isinstance(hikaye, str) or not hikaye.strip() or yasak_bul(hikaye):
        return ""
    return hikaye.strip()


def _bugun():
    return datetime.datetime.now(getattr(config, "TR_TZ", None)).date()


def kapi_tarihi():
    deger = getattr(config, "HIKAYE_KAPISI_TARIHI", "2026-09-21")
    try:
        return datetime.date.fromisoformat(str(deger))
    except ValueError:
        return datetime.date(2026, 9, 21)       # bozuk config: daha ERKEN kapı değil, karar tarihi


def kapi_zorunlu_mu() -> bool:
    return _bugun() >= kapi_tarihi()


def kapsamda_mi(proje, meta, durum) -> bool:
    kok = os.path.basename(os.path.dirname(os.path.abspath(proje)))
    return (kok == "projects" and not (meta or {}).get("derleme")
            and (meta or {}).get("theme") != "dj"
            and not (durum or {}).get("youtube_video_id"))


def kapi_kontrol(proje, meta, durum):
    """(hatalar, uyarilar) — `uyumluluk.kontrol` "yukleme" aşamasından çağrılır."""
    if not kapsamda_mi(proje, meta, durum):
        return [], []
    eksik = hikaye_hatalari(meta)
    if not eksik:
        return [], []
    tarih = kapi_tarihi().isoformat()
    metin = ("hikâye kapısı: %s — `meta.json`'a söz yazarı ajanıyla hazırlanıp onaylanmış "
             "`hikaye` (2-4 cümle) ve `neden_bu_sarki` (1 cümle) eklenmeli" % "; ".join(eksik))
    if kapi_zorunlu_mu():
        return [metin + " (%s itibarıyla ZORUNLU, yayın durduruldu)" % tarih], []
    return [], [metin + " (%s itibarıyla zorunlu olacak; şimdilik uyarı)" % tarih]


# --------------------------------------------------------------------------
# Başlık kalıbı
# --------------------------------------------------------------------------

def rotasyon_aktif() -> bool:
    return bool(getattr(config, "YOUTUBE_BASLIK_ROTASYONU_AKTIF", False))


def baslik_kaliplari() -> list:
    kaliplar = getattr(config, "YOUTUBE_BASLIK_KALIPLARI", None) or VARSAYILAN_KALIPLAR
    return [dict(k) for k in kaliplar if isinstance(k, dict) and k.get("id") and k.get("sablon")]


def kalip(kalip_id):
    for k in baslik_kaliplari():
        if k["id"] == kalip_id:
            return k
    return None


def uygun_kaliplar(meta) -> list:
    meta = meta or {}
    return [k for k in baslik_kaliplari()
            if not k.get("gerekli") or str(meta.get(k["gerekli"]) or "").strip()]


def kalip_sec(meta, onceki):
    adaylar = [k["id"] for k in uygun_kaliplar(meta)]
    farkli = [a for a in adaylar if a != onceki] or adaylar
    if not farkli:
        return VARSAYILAN_KALIP
    anahtar = hashlib.sha1(str((meta or {}).get("title", "")).encode("utf-8")).hexdigest()
    return farkli[int(anahtar, 16) % len(farkli)]


def baslik_uret(meta, kalip_id, tur_etiketi):
    k = kalip(kalip_id) or kalip(VARSAYILAN_KALIP) or dict(VARSAYILAN_KALIPLAR[0])
    meta = meta or {}
    alanlar = {"title": meta.get("title", "Untitled"), "tur": tur_etiketi,
               "baslik_eki": str(meta.get("baslik_eki") or "").strip()}
    if k.get("gerekli") and not alanlar.get(k["gerekli"]):
        k = kalip(VARSAYILAN_KALIP) or dict(VARSAYILAN_KALIPLAR[0])
    return k["sablon"].format(**alanlar)


def _durum_oku(proje):
    try:
        with open(os.path.join(proje, "state.json"), "r", encoding="utf-8") as f:
            v = json.load(f)
        return v if isinstance(v, dict) else {}
    except (OSError, ValueError):
        return {}


def onceki_kalip(klasorler, haric=None):
    """En son YENİ şarkı yüklemesinin kalıbı (`youtube_uploaded_at` en geç olan ana katalog
    projesi). Kaydı olmayan eski yayın K1 (bugünkü 20/20 başlık). Hiç yayın yoksa None."""
    haric_n = os.path.normcase(os.path.abspath(haric)) if haric else None
    en_son, en_ts = None, None
    for p in klasorler:
        if haric_n and os.path.normcase(os.path.abspath(p)) == haric_n:
            continue
        if os.path.basename(os.path.dirname(os.path.abspath(p))) != "projects":
            continue
        st = _durum_oku(p)
        if not st.get("youtube_video_id"):
            continue
        try:
            ts = time.mktime(time.strptime(str(st.get("youtube_uploaded_at") or "")[:19],
                                           "%Y-%m-%dT%H:%M:%S"))
        except ValueError:
            ts = 0.0
        if en_ts is None or ts > en_ts:
            en_ts, en_son = ts, st.get("youtube_baslik_kalibi") or VARSAYILAN_KALIP
    return en_son
