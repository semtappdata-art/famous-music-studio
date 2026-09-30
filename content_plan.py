#!/usr/bin/env python3
"""Content plan - trending topic'a gore icerik planlari.

Profesyonel şirketler trendleri takip eder ve hizlanir:
1. AI music - TikTok trending
2. Electronic - TikTok trending
3. Night drive - Instagram trending
4. Viral sound - TikTok trending
5. Reels - Instagram trending

Kullanım:
    python content_plan.py --plan     # Plan olustur
    python content_plan.py --execute  # Plani calistir
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "durum.json")
PLAN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "content_plan.jsonl")


# ================================================================
# ICERIK PLANI
# ================================================================

def plan_olustur() -> list[dict]:
    """Trending topic'a gore icerik plani olusturur.

    Returns:
        [{"konu": ..., "platform": ..., "tur": ..., "oncelik": ...}, ...]
    """
    planlar = [
        # AI music - TikTok trending, cok hizli
        {
            "konu": "AI music",
            "platform": "tiktok",
            "tur": "short",
            "oncelik": "yuksek",
            "hiz": "cok-hizli",
            "aciklama": "AI uretimi elektronik short - 15-30 sn",
            "hook": "AI destekli elektronik, senin icin yazildi",
            "hashtag": "#AIMusic #electronic #AI",
        },
        # Electronic - TikTok trending, hizli
        {
            "konu": "electronic",
            "platform": "tiktok",
            "tur": "short",
            "oncelik": "yuksek",
            "hiz": "hizli",
            "aciklama": "Electronic beat short - 15-30 sn",
            "hook": "Elektronik beat, AI melodi",
            "hashtag": "#electronic #AI #music",
        },
        # Night drive - Instagram trending, hizli
        {
            "konu": "night drive",
            "platform": "instagram",
            "tur": "reel",
            "oncelik": "yuksek",
            "hiz": "hizli",
            "aciklama": "Night drive reel - 30-60 sn",
            "hook": "Night drive vibes AI destekli",
            "hashtag": "#nightdrive #AI #music",
        },
        # Viral sound - TikTok trending, cok hizli
        {
            "konu": "viral sound",
            "platform": "tiktok",
            "tur": "sound",
            "oncelik": "yuksek",
            "hiz": "cok-hizli",
            "aciklama": "Viral sound effect - 5-15 sn",
            "hook": "Viral sound AI uretimi",
            "hashtag": "#viralsound #AI #fyp",
        },
        # Reels - Instagram trending, hizli
        {
            "konu": "reels",
            "platform": "instagram",
            "tur": "reel",
            "oncelik": "yuksek",
            "hiz": "hizli",
            "aciklama": "Reels format short - 15-30 sn",
            "hook": "Reels AI music",
            "hashtag": "#reels #AI #music",
        },
        # Melancholy - YouTube trending, normal
        {
            "konu": "melancholy",
            "platform": "youtube",
            "tur": "long",
            "oncelik": "orta",
            "hiz": "normal",
            "aciklama": "Melancholy long format - 3-5 dk",
            "hook": "Melancholy AI music",
            "hashtag": "#melancholy #AI #music",
        },
        # Lofi beats - YouTube trending, normal
        {
            "konu": "lofi beats",
            "platform": "youtube",
            "tur": "long",
            "oncelik": "orta",
            "hiz": "normal",
            "aciklama": "Lofi beats long format - 3-5 dk",
            "hook": "Lofi beats AI destekli",
            "hashtag": "#lofi #AI #music",
        },
    ]

    return planlar


def execute_plan(plan: dict) -> dict:
    """Bir plani calistirir.

    Args:
        plan: plan_olustur() dan gelen plan dict

    Returns:
        {"durum": "basarili" | "basarisiz", "sebep": str}
    """
    konu = plan.get("konu", "")
    platform = plan.get("platform", "")
    tur = plan.get("tur", "")

    # Platform dogrulama
    valid_platforms = ["tiktok", "instagram", "youtube", "facebook", "twitter"]
    if platform not in valid_platforms:
        return {"durum": "basarisiz", "sebep": f"Geçersiz platform: {platform}"}

    # Tur dogrulama
    valid_turler = ["short", "reel", "long", "sound"]
    if tur not in valid_turler:
        return {"durum": "basarisiz", "sebep": f"Geçersiz tur: {tur}"}

    # Oncelik kontrolü
    oncelik = plan.get("oncelik", "")
    if oncelik == "yuksek":
        # Yüksek öncelikli planları önce çalıştır
        pass  # Gerçek üretimde buraya üretim kodları gelir

    return {
        "durum": "basarili",
        "konu": konu,
        "platform": platform,
        "tur": tur,
        "yurutme_zamani": datetime.now(timezone.utc).isoformat(),
    }


# ================================================================
# STATE GÜNCELLEME
# ================================================================

def state_guncelle(plan: dict, sonuc: dict):
    """Son plan sonuçlarini durum.json'a yazar."""
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}

    state["content_plan"] = {
        "son_calısma": datetime.now(timezone.utc).isoformat(),
        "plan_sayisi": len(plan_olustur()),
        "son_durum": sonuc.get("durum", "bilinmiyor"),
        "son_konu": plan.get("konu", ""),
    }

    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ================================================================
# RAPOR
# ================================================================

def rapor_olustur(planlar: list) -> str:
    """Icerik plani raporu olusturur."""
    satirlar = [
        "=" * 60,
        "CONTENT PLAN RAPORU",
        f"Tarih: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "=" * 60,
        "",
        "-- Oncelikli Planlar --",
    ]

    for p in planlar:
        emoji = "[ISI]" if p.get("oncelik") == "yuksek" else "[ARTI]"
        satirlar.append(f"  {emoji} {p['konu']} ({p['platform']}) - {p['tur']}")

    satirlar.append("")
    satirlar.append("-- Oncelik Sirasi --")
    oncelik_sira = sorted(planlar, key=lambda x: {"yuksek": 0, "orta": 1, "dusuk": 2}.get(x.get("oncelik", 2), 2))
    for i, p in enumerate(oncelik_sira, 1):
        satirlar.append(f"  {i}. {p['konu']} ({p['platform']}) - {p['hiz']}")

    satirlar.append("")
    satirlar.append("-- Not --")
    satirlar.append("  Yüksek oncelikli planlari önce calistir")
    satirlar.append("  Cok-hizli trendler icin hemen üret")
    satirlar.append("  Normal trendler icin bu hafta üret")

    return "\n".join(satirlar)


# ================================================================
# ANA
# ================================================================

def main():
    parser = argparse.ArgumentParser(description="Content plan")
    parser.add_argument("--plan", action="store_true", help="Plan olustur")
    parser.add_argument("--execute", action="store_true", help="Plan calistir")
    parser.add_argument("--konu", type=str, help="Calistirilacak konu")
    parser.add_argument("--report", action="store_true", help="Rapor göster")
    args = parser.parse_args()

    print("=" * 60)
    print("CONTENT PLAN")
    print("=" * 60)

    planlar = plan_olustur()

    if args.plan:
        # Plan olustur
        print(f"\n[Plan] {len(planlar)} plan olusturuldu")
        for p in planlar:
            emoji = "[ISI]" if p.get("oncelik") == "yuksek" else "[ARTI]"
            print(f"  {emoji} {p['konu']} ({p['platform']}) - {p['tur']}")

        # State guncelle
        state_guncelle(planlar[0], {"durum": "planlandi"})
        print(f"\n[OK] State guncellendi ({STATE_PATH})")

    elif args.execute and args.konu:
        # Plan calistir
        plan = next((p for p in planlar if p.get("konu") == args.konu), None)
        if plan:
            sonuc = execute_plan(plan)
            print(f"\n[Calistir] {args.konu} -> {sonuc.get('durum')}")
            state_guncelle(plan, sonuc)
            print(f"[OK] State guncellendi")
        else:
            print(f"\n[HATA] Konu bulunamadi: {args.konu}")

    elif args.report:
        # Rapor göster
        rapor = rapor_olustur(planlar)
        print("\n" + rapor)

    else:
        print("Kullanim:")
        print("  python content_plan.py --plan")
        print("  python content_plan.py --execute --konu 'AI music'")
        print("  python content_plan.py --report")


if __name__ == "__main__":
    main()
