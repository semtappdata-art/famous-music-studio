# -*- coding: utf-8 -*-
"""Feedback loop — haftalık performans analizi + stil önerisi.

Her şarkının izlenme/süre/tıklama verisini okur, en iyi 3'ü analiz eder,
başarı faktörlerini (tempo, tema, vokal cinsiyeti) biriktirir.
Sonraki şarkılarda bu faktörlere uygun stil etiketi öneren sistem.

Kullanım:
    python feedback_loop.py analiz          # haftalık analiz
    python feedback_loop.py öneri "Şarkı Adı"  # stil önerisi
    python feedback_loop.py dashboard       # özet tablo
"""

import os, json, time, sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import state_io
import uyumluluk

RAPOR_KOK = os.path.join(os.path.dirname(__file__), "raporlar")
HISTORY_FILE = os.path.join(RAPOR_KOK, "feedback_tarih.json")
STYLE_WEIGHTS_FILE = os.path.join(RAPOR_KOK, "stil_agirliklari.json")

# Haftalık izlenme okur — weekly_report.gunluk_izlenme_raporu() bırakır.
# Biz sadece state.json'tan okuruz.

def _projeleri_oku():
    """Tüm projelerin state.json oku."""
    projeler = []
    kokler = uyumluluk.KOKLER
    for kok in kokler:
        if not os.path.isdir(kok):
            continue
        for d in os.listdir(kok):
            state_path = os.path.join(kok, d, "state.json")
            if not os.path.isfile(state_path):
                continue
            try:
                with open(state_path, encoding="utf-8") as f:
                    state = json.load(f)
            except Exception:
                continue
            meta_path = os.path.join(kok, d, "meta.json")
            meta = {}
            if os.path.isfile(meta_path):
                try:
                    with open(meta_path, encoding="utf-8") as f:
                        meta = json.load(f)
                except Exception:
                    pass
            projeler.append({"proje": d, "kok": os.path.basename(kok),
                             "state": state, "meta": meta})
    return projeler


def _gunluk_izlenme_oku():
    """gunluk_izlenme.json'dan son okuma."""
    yol = os.path.join(os.path.dirname(__file__), "upload", "gunluk_izlenme.json")
    if not os.path.isfile(yol):
        return {}
    try:
        with open(yolon, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def analiz(yazi=True):
    """Haftalık analiz: en iyi 3 şarkı, stil faktörleri."""
    projeler = _projeleri_oku()
    gunluk = _gunluk_izlenme_oku()
    simdi = time.time()
    hafta_enson = simdi - 7 * 86400

    sonuclar = []
    for p in projeler:
        s = p["state"]
        meta = p["meta"]
        ad = p["proje"]
        # Yayın tarihi
        yayin = s.get("youtube_publish_at") or s.get("instagram_creation_id") or ""
        if yayin:
            try:
                yayin_ts = datetime.fromisoformat(yayin.replace("Z", "+00:00")).timestamp()
            except Exception:
                continue
            if yayin_ts < hafta_enson:
                continue

        # İzlenme
        izl = int(s.get("youtube_izlenme") or 0)
        izl += int(s.get("instagram_izlenme") or 0)
        izl += int(s.get("tiktok_izlenme") or 0)

        # Gunluk izlenme dosyasından fark
        g = gunluk.get(ad, {})
        izl_gunluk = int(g.get("izlenme", 0))
        artis = int(g.get("artis", 0))

        sonuclar.append({
            "ad": ad,
            "tema": meta.get("theme", "bilinmiyor"),
            "vokal": meta.get("vokal_cinsiyeti") or meta.get("ses_tipi") or "bilinmiyor",
            "tempo": meta.get("tempo", "bilinmiyor"),
            "izl_toplam": izl,
            "izl_gunluk": izl_gunluk,
            "artis": artis,
            "yayin": yayin[:10] if yayin else "",
        })

    # Sırala: günlük artışa göre
    sonuclar.sort(key=lambda x: x["artis"], reverse=True)
    en_iyi = sonuclar[:3]

    # Stil faktörleri
    faktörler = {"tema": {}, "vokal": {}, "tempo": {}}
    for s in sonuclar:
        t = s["tema"]
        faktörler["tema"][t] = faktörler["tema"].get(t, 0) + (1 if s["artis"] > 0 else 0)
        v = s["vokal"]
        faktörler["vokal"][v] = faktörler["vokal"].get(v, 0) + (1 if s["artis"] > 0 else 0)
        tmp = s["tempo"]
        faktörler["tempo"][tmp] = faktörler["tempo"].get(tmp, 0) + (1 if s["artis"] > 0 else 0)

    rapor = {
        "tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "en_iyi_3": en_iyi,
        "stil_faktörler": faktörler,
        "toplam_analiz": len(sonuclar),
    }

    # Kaydet
    os.makedirs(RAPOR_KOK, exist_ok=True)
    tarih = datetime.now().strftime("%Y-%m-%d")
    dosya = os.path.join(RAPOR_KOK, f"feedback_{tarih}.json")
    with open(dosya, "w", encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=2)

    # Tarihçeye ekle
    tarihce = []
    if os.path.isfile(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, encoding="utf-8") as f:
                tarihce = json.load(f)
        except Exception:
            tarihce = []
    tarihce.append(rapor)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(tarihce, f, ensure_ascii=False, indent=2)

    if yazi:
        print(f"  Feedback analiz: {len(sonuclar)} şarkı, en iyi 3:")
        for i, s in enumerate(en_iyi, 1):
            print(f"    {i}. {s['ad']} — izl: {s['izl_toplam']} (+{s['artis']}/gün) "
                  f"tema:{s['tema']} vokal:{s['vokal']}")
        print(f"  Stil faktörler: {json.dumps(faktörler, ensure_ascii=False)}")
    return rapor


def öneri(şarkı_adı=None):
    """Stil önerisi: en iyi şarkıların faktörlerine göre."""
    tarihce = []
    if os.path.isfile(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, encoding="utf-8") as f:
                tarihce = json.load(f)
        except Exception:
            return {"hatalar": ["tarihce yok"]}

    if not tarihce:
        return {"hatalar": ["henüz analiz yok"], "öneri": "tempo ve tema belirt"}

    son = tarihce[-1]
    faktörler = son.get("stil_faktörler", {})

    # En başarılı faktörler
    en_iyi_tema = max(faktörler.get("tema", {}).items(), key=lambda x: x[1], default=("belirsiz", 0))
    en_iyi_vokal = max(faktörler.get("vokal", {}).items(), key=lambda x: x[1], default=("belirsiz", 0))
    en_iyi_tempo = max(faktörler.get("tempo", {}).items(), key=lambda x: x[1], default=("belirsiz", 0))

    return {
        "şarkı": şarkı_adı,
        "önerilen_tema": en_iyi_tema[0],
        "önerilen_vokal": en_iyi_vokal[0],
        "önerilen_tempo": en_iyi_tempo[0],
        "gerekçe": f"Son haftada {en_iyi_tema[0]} tema, {en_iyi_vokal[0]} vokal, {en_iyi_tempo[0]} tempo en yüksek başarı",
        "kaynak": "feedback_loop.py",
    }


def dashboard():
    """Özet tablo."""
    rapor = analiz(yazi=False)
    print(f"\n  Feedback Dashboard — {rapor.get('tarih', '?')}")
    print(f"  Analizlenen: {rapor.get('toplam_analiz', 0)}")
    print(f"  En iyi 3:")
    for i, s in enumerate(rapor.get("en_iyi_3", []), 1):
        print(f"    {i}. {s['ad']} (+{s['artis']}/gün)")
    print(f"  Stil faktörler: {json.dumps(rapor.get('stil_faktörler', {}), ensure_ascii=False)}")
    return rapor


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("komut", choices=["analiz", "öneri", "dashboard"])
    ap.add_argument("--şarkı", default=None)
    args = ap.parse_args()

    if args.komut == "analiz":
        analiz()
    elif args.komut == "öneri":
        print(json.dumps(öneri(args.şarkı), ensure_ascii=False, indent=2))
    elif args.komut == "dashboard":
        dashboard()
