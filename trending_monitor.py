#!/usr/bin/env python3
"""Trending content monitor - trendleri yakala ve hizala.

Profesyonel şirketler trendleri takip eder:
1. Platform trendleri
2. Hashtag trendleri
3. Konu trendleri
4. Hızlı adaptasyon

Kullanım:
    python trending_monitor.py --check     # Trendleri kontrol et
    python trending_monitor.py --adapt      # Trende uyarla
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "durum.json")
TREND_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trendler.jsonl")


# ================================================================
# TREND VERİLERİ
# ================================================================

def platform_trendleri() -> dict:
    """Platform trendlerini döndürür.

    Returns:
        {
            "youtube": [...],
            "tiktok": [...],
            "instagram": [...],
            ...
        }
    """
    # Bu fonksiyon gerçek zamanlı trend verisi getirir
    # Şimdilik statik liste (gerçek veriler için API lazım)
    return {
        "youtube": [
            {"konu": "AI music", "hitap": "yüksek", "hız": "hızlı"},
            {"konu": "lofi beats", "hitap": "orta", "hız": "normal"},
            {"konu": "night drive", "hitap": "yüksek", "hız": "hızlı"},
        ],
        "tiktok": [
            {"konu": "electronic", "hitap": "yüksek", "hız": "hızlı"},
            {"konu": "viral sound", "hitap": "yüksek", "hız": "çok hızlı"},
            {"konu": "cover", "hitap": "orta", "hız": "normal"},
        ],
        "instagram": [
            {"konu": "reels", "hitap": "yüksek", "hız": "hızlı"},
            {"konu": "behind the scenes", "hitap": "orta", "hız": "normal"},
        ],
    }


def hashtag_trendleri() -> list[dict]:
    """Hashtag trendlerini döndürür."""
    return [
        {"hashtag": "#AIMusic", "platform": "tiktok", "popülerlik": "yüksek"},
        {"hashtag": "#lofi", "platform": "youtube", "popülerlik": "orta"},
        {"hashtag": "#nightdrive", "platform": "instagram", "popülerlik": "yüksek"},
        {"hashtag": "#electronic", "platform": "tiktok", "popülerlik": "yüksek"},
        {"hashtag": "#melancholy", "platform": "youtube", "popülerlik": "orta"},
    ]


# ================================================================
# UYARLAMA
# ================================================================

def trend_uyarlamasi(trend: dict) -> dict:
    """Bir trend için içerik uyarlaması önerir.

    Returns:
        {
            "trend": str,
            "platform": str,
            "oneri": str,
            "öncelik": str,
            "hız": str,
        }
    """
    konu = trend.get("konu", "")
    platform = trend.get("platform", "")
    hitap = trend.get("hitap", "")
    hiz = trend.get("hız", "")

    # Öneri üret
    oneri = f"'{konu}' temalı {platform} içeriği üret"
    if hitap == "yüksek":
        oneri += " (öncelikli)"

    # Hız değerlendirmesi
    if hiz == "çok hızlı":
        oneri += " - hemen üret!"
    elif hiz == "hızlı":
        oneri += " - bu hafta üret"
    else:
        oneri += " - normal zamanlama"

    # Öncelik
    if hitap == "yüksek" and hiz in ["hızlı", "çok hızlı"]:
        öncelik = "yüksek"
    elif hitap == "orta":
        öncelik = "orta"
    else:
        öncelik = "düşük"

    return {
        "trend": konu,
        "platform": platform,
        "oneri": oneri,
        "öncelik": öncelik,
        "hız": hiz,
    }


# ================================================================
# RAPOR
# ================================================================

def rapor_olustur(trendler: dict, hashtag_trendleri: list) -> str:
    """Trend raporu oluşturur."""
    satirlar = [
        "=" * 60,
        "TRENDING MONITOR RAPORU",
        f"Tarih: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "=" * 60,
        "",
        "-- Platform Trendleri --",
    ]

    for platform, trendler_listesi in trendler.items():
        satirlar.append(f"  {platform}:")
        for t in trendler_listesi[:3]:
            emoji = "[ISI]" if t.get("hitap") == "yüksek" else "[ARTI]"
            satirlar.append(
                f"    {emoji} {t['konu']} ({t['hitap']}, {t['hız']})"
            )

    satirlar.append("")
    satirlar.append("-- Hashtag Trendleri --")
    for ht in hashtag_trendleri[:5]:
        emoji = "[ISI]" if ht.get("popülerlik") == "yüksek" else "[ARTI]"
        satirlar.append(f"  {emoji} {ht['hashtag']} ({ht['platform']})")

    satirlar.append("")
    satirlar.append("-- Uyarlamalar --")

    # Trend uyarlamaları
    for platform, trendler_listesi in trendler.items():
        for t in trendler_listesi[:2]:
            uyarlama = trend_uyarlamasi(t)
            satirlar.append(f"  {uyarlama['oneri']}")

    satirlar.append("")
    satirlar.append("-- Önemli Not --")
    satirlar.append("  Trendler değişir, haftalık kontrol zorunlu")
    satirlar.append("  Yüksek hitap + hızlı = hemen üret")
    satirlar.append("  Düşük hitap = normal zamanlama")

    return "\n".join(satirlar)


# ================================================================
# STATE GÜNCELLEME
# ================================================================

def state_guncelle(trendler: dict):
    """Son trend sonuçlarını durum.json'a yazar."""
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}

    state["trending_monitor"] = {
        "son_calısma": datetime.now(timezone.utc).isoformat(),
        "trend_sayisi": sum(len(v) for v in trendler.values()),
    }

    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ================================================================
# ANA
# ================================================================

def main():
    parser = argparse.ArgumentParser(description="Trending monitor")
    parser.add_argument("--check", action="store_true", help="Trendleri kontrol et")
    parser.add_argument("--adapt", action="store_true", help="Trende uyarla")
    parser.add_argument("--report", action="store_true", help="Rapor göster")
    args = parser.parse_args()

    print("=" * 60)
    print("TRENDING MONITOR")
    print("=" * 60)

    # Trend verileri
    trendler = platform_trendleri()
    hashtag_trendleri_list = hashtag_trendleri()

    if args.check:
        # Trendleri göster
        print("\n[Trendler] Platform trendleri:")
        for platform, trendler_listesi in trendler.items():
            print(f"  {platform}:")
            for t in trendler_listesi[:3]:
                emoji = "[ISI]" if t.get("hitap") == "yüksek" else "[ARTI]"
                print(f"    {emoji} {t['konu']} ({t['hitap']})")

        print("\n[Hashtagler] Hashtag trendleri:")
        for ht in hashtag_trendleri_list[:5]:
            emoji = "[ISI]" if ht.get("popülerlik") == "yüksek" else "[ARTI]"
            print(f"  {emoji} {ht['hashtag']} ({ht['platform']})")

    elif args.adapt:
        # Trende uyarla
        print("\n[Uyarlama] Trende uyarlanıyor...")
        for platform, trendler_listesi in trendler.items():
            for t in trendler_listesi[:2]:
                uyarlama = trend_uyarlamasi(t)
                print(f"  {uyarlama['oneri']}")

        state_guncelle(trendler)
        print(f"\n[OK] State guncellendi ({STATE_PATH})")

    elif args.report:
        # Rapor göster
        rapor = rapor_olustur(trendler, hashtag_trendleri_list)
        print("\n" + rapor)

    else:
        print("Kullanim:")
        print("  python trending_monitor.py --check")
        print("  python trending_monitor.py --adapt")
        print("  python trending_monitor.py --report")


if __name__ == "__main__":
    main()
