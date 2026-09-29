# -*- coding: utf-8 -*-
"""Analytics dashboard — günlük KPI takibi.

Her platformdan izlenme, süre, CTR, yeni abone, gelir.
En iyi performing içerik → o tarza odaklan.
"""

import os, json, time, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DASHBOARD_FILE = os.path.join(os.path.dirname(__file__), "raporlar", "dashboard.json")


def oku():
    """Mevcut dashboard'u oku."""
    if os.path.isfile(DASHBOARD_FILE):
        try:
            with open(DASHBOARD_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"güncel": None, "gunler": []}


def yaz(dashboard):
    os.makedirs(os.path.dirname(DASHBOARD_FILE), exist_ok=True)
    dashboard["güncel"] = datetime.now().isoformat()
    # Son 30 günce tut
    dashboard["gunler"] = (dashboard.get("gunler") or [])[-30:]
    with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(dashboard, f, ensure_ascii=False, indent=2)


def guncelle():
    """State.json'dan KPI oku, dashboard'a ekle."""
    import uyumluluk
    import state_io

    dashboard = oku()
    simdi = time.time()

    toplam_izl = 0
    toplam_sure = 0
    platformlar = {}
    projeler = []

    for kok in uyumluluk.KOKLER:
        if not os.path.isdir(kok):
            continue
        for d in os.listdir(kok):
            state_path = os.path.join(kok, d, "state.json")
            if not os.path.isfile(state_path):
                continue
            try:
                with open(state_path, encoding="utf-8") as f:
                    s = json.load(f)
            except Exception:
                continue

            ad = d
            izl = int(s.get("youtube_izlenme") or 0)
            izl += int(s.get("instagram_izlenme") or 0)
            izl += int(s.get("tiktok_izlenme") or 0)
            sure = int(s.get("youtube_izlenme_suresi") or 0)

            toplam_izl += izl
            toplam_sure += sure

            p = s.get("platform", "youtube")
            platformlar[p] = platformlar.get(p, 0) + izl

            projeler.append({
                "ad": ad,
                "izl": izl,
                "sure_sn": sure,
                "platform": p,
                "theme": s.get("theme", ""),
                "yayin": s.get("youtube_publish_at", "")[:10],
            })

    # Sırala
    projeler.sort(key=lambda x: x["izl"], reverse=True)

    entry = {
        "tarih": datetime.now().strftime("%Y-%m-%d"),
        "zaman": datetime.now().strftime("%H:%M"),
        "toplam_izl": toplam_izl,
        "toplam_sure_sn": toplam_sure,
        "platformlar": platformlar,
        "en_iyi_5": projeler[:5],
    }

    dashboard["gunler"].append(entry)
    dashboard["toplam_izl"] = toplam_izl
    dashboard["toplam_sure_sn"] = toplam_sure
    dashboard["platformlar"] = platformlar
    yaz(dashboard)

    print(f"  Dashboard: {toplam_izl} izlenme, {toplam_sure//3600}h {toplam_sure%3600//60}m")
    for p, v in platformlar.items():
        print(f"    {p}: {v}")
    if projeler:
        print(f"  En iyi: {projeler[0]['ad']} ({projeler[0]['izl']})")
    return dashboard


def karsilastir(gun=7):
    """Son N günlük karşılaştırma."""
    dashboard = oku()
    gunler = dashboard.get("gunler", [])[-gun:]
    if len(gunler) < 2:
        print("  Yeterli veri yok")
        return

    ilk = gunler[0]["toplam_izl"]
    son = gunler[-1]["toplam_izl"]
    artis = son - ilk
    yuzde = (artis / ilk * 100) if ilk else 0

    print(f"  Son {gun} gün: {ilk} → {son} (+{artis}, %{yuzde:.1f})")
    for g in gunler:
        print(f"    {g['tarih']}: {g['toplam_izl']}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("komut", choices=["guncelle", "karsilastir", "durum"])
    ap.add_argument("--gun", type=int, default=7)
    args = ap.parse_args()

    if args.komut == "guncelle":
        guncelle()
    elif args.komut == "karsilastir":
        karsilastir(args.gun)
    elif args.komut == "durum":
        d = oku()
        print(json.dumps(d.get("gunler", [])[-1], ensure_ascii=False, indent=2))