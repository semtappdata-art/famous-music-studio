#!/usr/bin/env python3
"""Subscriber tracking - abone kazanim takibi.

Profesyonel şirketler abone kazanimini takip eder:
1. Abone sayisi gunlugu
2. Subs/1K views (kalite metriği)
3. Kazanan video hangisi?
4. Trend analizi

Kullanım:
    python subscriber_tracker.py --daily     # Gunluk rapor
    python subscriber_tracker.py --trend     # Trend analizi
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "durum.json")
SUB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subscriber_takip.jsonl")


# ================================================================
# ABONE TAKİBİ
# ================================================================

def gunluk_rapor(subs: int, izlenme: int, video_sayisi: int) -> dict:
    """Gunluk abone raporu olusturur.

    Returns:
        {
            "tarih": str,
            "abone_sayisi": int,
            "izlenme": int,
            "video_sayisi": int,
            "subs_per_1k_views": float,
            "kazanan_video": str,
        }
    """
    subs_per_1k = round(subs / max(izlenme, 1) * 1000, 2) if izlenme > 0 else 0

    return {
        "tarih": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "abone_sayisi": subs,
        "izlenme": izlenme,
        "video_sayisi": video_sayisi,
        "subs_per_1k_views": subs_per_1k,
        "kazanan_video": "",  # analytics_dashboard'dan gelsin
    }


def trend_analizi(tarihsel: list[dict]) -> dict:
    """Abone趋势 analizi yapar.

    Returns:
        {
            "gunluk_ortalama": float,
            "haftalik_orantalama": float,
            "en_cok_kazanan_gun": str,
            "yon": "yukseliyor" | "dusen" | "sabit",
        }
    """
    if len(tarihsel) < 2:
        return {"yonalma": "yetersiz_veri"}

    # Gunluk ortalama
    gunluk_artilar = []
    for i in range(1, len(tarihsel)):
        artis = tarihsel[i].get("abone_sayisi", 0) - tarihsel[i-1].get("abone_sayisi", 0)
        gunluk_artilar.append(artis)

    gunluk_ort = round(sum(gunluk_artilar) / len(gunluk_artilar), 2) if gunluk_artilar else 0

    # Haftalik ortalama (7 gun)
    if len(tarihsel) >= 7:
        haftalik_artilar = []
        for i in range(1, len(tarihsel)):
            artis = tarihsel[i].get("abone_sayisi", 0) - tarihsel[i-1].get("abone_sayisi", 0)
            haftalik_artilar.append(artis)
        haftalik_ort = round(sum(haftalik_artilar[-7:]) / 7, 2) if haftalik_artilar else 0
    else:
        haftalik_ort = gunluk_ort

    # Yon analizi
    son_7_gun = [t.get("abone_sayisi", 0) for t in tarihsel[-7:]]
    ilk_7_gun = [t.get("abone_sayisi", 0) for t in tarihsel[:7]]

    if len(son_7_gun) >= 3 and len(ilk_7_gun) >= 3:
        son_ort = sum(son_7_gun) / len(son_7_gun)
        ilk_ort = sum(ilk_7_gun) / len(ilk_7_gun)
        if son_ort > ilk_ort + 1:
            yon = "yukseliyor"
        elif son_ort < ilk_ort - 1:
            yon = "dusen"
        else:
            yon = "sabit"
    else:
        yon = "yetersiz_veri"

    # En cok kazanan gun
    en_cok_idx = 0
    en_cok_artis = 0
    for i in range(1, len(tarihsel)):
        artis = tarihsel[i].get("abone_sayisi", 0) - tarihsel[i-1].get("abone_sayisi", 0)
        if artis > en_cok_artis:
            en_cok_artis = artis
            en_cok_idx = i

    return {
        "gunluk_ortalama": gunluk_ort,
        "haftalik_ortalama": haftalik_ort,
        "en_cok_kazanan_gun": tarihsel[en_cok_idx].get("tarih", "") if en_cok_idx < len(tarihsel) else "",
        "yon": yon,
    }


# ================================================================
# STATE GUNCELLEME
# ================================================================

def state_guncelle(rapor: dict):
    """Son abone raporunu durum.json'a yazar."""
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}

    state["subscriber_tracker"] = {
        "son_calısma": datetime.now(timezone.utc).isoformat(),
        "abone_sayisi": rapor.get("abone_sayisi", 0),
        "subs_per_1k_views": rapor.get("subs_per_1k_views", 0),
        "yon": rapor.get("yon", "bilinmiyor"),
    }

    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ================================================================
# ANA
# ================================================================

def main():
    parser = argparse.ArgumentParser(description="Subscriber tracker")
    parser.add_argument("--daily", action="store_true", help="Gunluk rapor")
    parser.add_argument("--trend", action="store_true", help="Trend analizi")
    parser.add_argument("--subs", type=int, help="Abone sayisi")
    parser.add_argument("--views", type=int, help="Izlenme sayisi")
    parser.add_argument("--videos", type=int, help="Video sayisi")
    args = parser.parse_args()

    print("=" * 60)
    print("SUBSCRIBER TRACKER")
    print("=" * 60)

    if args.daily and args.subs is not None:
        # Gunluk rapor
        rapor = gunluk_rapor(args.subs, args.views or 0, args.videos or 0)
        print(f"\n[Gunluk Rapor] {rapor['tarih']}")
        print(f"  Abone: {rapor['abone_sayisi']:,}")
        print(f"  Izlenme: {rapor['izlenme']:,}")
        print(f"  Video: {rapor['video_sayisi']}")
        print(f"  Subs/1K views: {rapor['subs_per_1k_views']}")

        # State guncelle
        state_guncelle(rapor)
        print(f"\n[OK] State guncellendi ({STATE_PATH})")

    elif args.trend:
        # Trend analizi
        try:
            with open(SUB_PATH, "r", encoding="utf-8") as f:
                tarihler = [json.loads(line) for line in f if line.strip()]
        except FileNotFoundError:
            tarihler = []

        if len(tarihler) >= 2:
            analiz = trend_analizi(tarihler)
            print(f"\n[Trend Analizi]")
            print(f"  Gunluk ortalama: {analiz.get('gunluk_ortalama', 0):+.1f} abone/gun")
            print(f"  Haftalik ortalama: {analiz.get('haftalik_ortalama', 0):+.1f} abone/gun")
            print(f"  Yonalma: {analiz.get('yon', 'bilinmiyor')}")
            print(f"  En cok kazanan gun: {analiz.get('en_cok_kazanan_gun', 'N/A')}")
        else:
            print("\n[UYARI] Yetersiz veri (en az 2 gun gerekli)")

    else:
        print("Kullanim:")
        print("  python subscriber_tracker.py --daily --subs 100 --views 5000 --videos 20")
        print("  python subscriber_tracker.py --trend")


if __name__ == "__main__":
    main()
