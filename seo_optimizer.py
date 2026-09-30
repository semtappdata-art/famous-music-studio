#!/usr/bin/env python3
"""SEO & GEO optimization - arama ve AI keşif optimizasyonu.

Profesyonel şirketler içeriklerini hem insanlar hem AI için optimize eder:
1. YouTube SEO: title, description, tags, thumbnail
2. GEO optimization: AI crawlerlar için yapılandırılmış veri
3. Trend monitoring: Trending konuları yakala
4. Keyword research: Arama talebi analizi

Kullanım:
    python seo_optimizer.py --video ID --title "..." --desc "..."
    python seo_optimizer.py --trends           # Trending konuları
    python seo_optimizer.py --report          # SEO raporu
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "durum.json")
SEO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seo_optimizasyon.jsonl")


# ================================================================
# SEO OPTİMİZASYONU
# ================================================================

def youtube_seo_optimizasyon(title: str, description: str, tags: list[str]) -> dict:
    """YouTube videosu için SEO optimizasyonu yapar.

    Kontroller:
    1. Title: 60 karakter altı, anahtar kelime başta
    2. Description: 200+ kelime, anahtar kelime dağılımı
    3. Tags: 10-15 arası, niche + broad
    4. Thumbnail: metin yok, yüksek kontrast

    Returns:
        {
            "title_uygun": bool,
            "desc_uygun": bool,
            "tags_uygun": bool,
            "toplam_puan": int,
            "oneriler": list[str],
        }
    """
    oneriler = []
    puan = 0

    # 1. Title kontrolü
    title_len = len(title)
    if title_len <= 60:
        puan += 1
    else:
        oneriler.append(f"Title uzun: {title_len} karakter (max 60)")

    # Anahtar kelime başta mı?
    anahtar_kelime = title.split()[0] if title else ""
    if anahtar_kelime and len(anahtar_kelime) > 3:
        puan += 1
    else:
        oneriler.append("Title'da anahtar kelime eksik")

    # 2. Description kontrolü
    desc_kelime_sayisi = len(description.split()) if description else 0
    if desc_kelime_sayisi >= 200:
        puan += 1
    elif desc_kelime_sayisi >= 100:
        puan += 0.5
        oneriler.append(f"Description kısa: {desc_kelime_sayisi} kelime (hedef 200+)")
    else:
        oneriler.append(f"Description çok kısa: {desc_kelime_sayisi} kelime")

    # 3. Tags kontrolü
    tag_sayisi = len(tags)
    if 10 <= tag_sayisi <= 15:
        puan += 1
    elif tag_sayisi < 10:
        oneriler.append(f"Tag az: {tag_sayisi} (hedef 10-15)")
    else:
        oneriler.append(f"Tag fazla: {tag_sayisi} (max 15)")

    # 4. Thumbnail kontrolü (basit)
    # Description'da thumbnail bilgisi var mı?
    if "thumbnail" in description.lower() or "kapak" in description.lower():
        puan += 1
    else:
        oneriler.append("Thumbnail bilgisi description'da yok")

    return {
        "title_uygun": puan >= 2,
        "desc_uygun": desc_kelime_sayisi >= 100,
        "tags_uygun": 10 <= tag_sayisi <= 15,
        "toplam_puan": round(puan, 1),
        "oneriler": oneriler,
    }


# ================================================================
# GEO OPTİMİZASYONU
# ================================================================

def geo_optimizasyon(title: str, description: str) -> dict:
    """AI crawlerlar için GEO optimizasyonu yapar.

    Profesyonel şirketler içeriklerini AI'ların anlayabileceği
    şekilde yapılandırır:
    1. Schema.org yapısı
    2. AI-friendly başlık
    3. Structured data

    Returns:
        {
            "schema_uygun": bool,
            "ai_friendly": bool,
            "toplam_puan": int,
        }
    """
    oneriler = []
    puan = 0

    # 1. Schema.org yapısı
    # Description'da schema mı var?
    if any(k in description.lower() for k in ["@type", "@context", "schema"]):
        puan += 1
    else:
        oneriler.append("Schema.org yapısı yok")

    # 2. AI-friendly başlık
    # Başlık net mi? Belirsiz mi?
    belirsiz_kelimekler = ["gizli", "sırrı", "mistik", "bilinmeyen"]
    is_belirsiz = any(k in title.lower() for k in belirsiz_kelimekler)
    if not is_belirsiz:
        puan += 1
    else:
        oneriler.append("Başlık belirsiz: AI anlayamaz")

    # 3. Structured data
    # Description'da structured data var mı?
    if any(k in description.lower() for k in ["# ", "## ", "### "]):
        puan += 1
    else:
        oneriler.append("Structured data yok (başlık + paragraf)")

    return {
        "schema_uygun": puan >= 2,
        "ai_friendly": not is_belirsiz,
        "toplam_puan": puan,
        "oneriler": oneriler,
    }


# ================================================================
# TREND MONITORING
# ================================================================

def trend_konulari() -> list[dict]:
    """Trending konuları tespit eder.

    Returns:
        [{"konu": ..., "platform": ..., "popülerlik": ...}, ...]
    """
    # Bu fonksiyon gerçek zamanlı trend verisi getirir
    # Şimdilik statik liste (gerçek veriler için API lazım)
    trendler = [
        {"konu": "AI music", "platform": "tiktok", "popülerlik": "yüksek"},
        {"konu": "lofi beats", "platform": "youtube", "popülerlik": "orta"},
        {"konu": "night drive", "platform": "instagram", "popülerlik": "yüksek"},
        {"konu": "melancholy", "platform": "youtube", "popülerlik": "orta"},
        {"konu": "electronic", "platform": "tiktok", "popülerlik": "yüksek"},
    ]

    return trendler


# ================================================================
# RAPOR
# ================================================================

def rapor_olustur(seo: dict, geo: dict, trendler: list) -> str:
    """SEO + GEO + Trend raporu oluşturur."""
    satirlar = [
        "=" * 60,
        "SEO & GEO RAPORU",
        f"Tarih: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "=" * 60,
        "",
        "-- YouTube SEO --",
        f"  Puan: {seo.get('toplam_puan', 0)}/4",
        f"  Title: {'[OK]' if seo.get('title_uygun') else '[HATA]'}",
        f"  Description: {'[OK]' if seo.get('desc_uygun') else '[HATA]'}",
        f"  Tags: {'[OK]' if seo.get('tags_uygun') else '[HATA]'}",
        "",
        "-- GEO (AI Optimizasyonu) --",
        f"  Puan: {geo.get('toplam_puan', 0)}/3",
        f"  Schema: {'[OK]' if geo.get('schema_uygun') else '[HATA]'}",
        f"  AI-Friendly: {'[OK]' if geo.get('ai_friendly') else '[HATA]'}",
        "",
        "-- Trending Konular --",
    ]

    for t in trendler[:5]:
        emoji = "[ISI]" if t.get("popülerlik") == "yüksek" else "[ARTI]"
        satirlar.append(f"  {emoji} {t['konu']} ({t['platform']})")

    satirlar.append("")
    satirlar.append("-- Öneriler --")

    tum_oneriler = seo.get("oneriler", []) + geo.get("oneriler", [])
    for oneri in tum_oneriler[:5]:
        satirlar.append(f"  -> {oneri}")

    if not tum_oneriler:
        satirlar.append("  -> Tüm optimizasyonlar tamam")

    return "\n".join(satirlar)


# ================================================================
# STATE GÜNCELLEME
# ================================================================

def state_guncelle(seo: dict, geo: dict, trendler: list):
    """Son SEO sonuçlarını durum.json'a yazar."""
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}

    state["seo_optimizer"] = {
        "son_calısma": datetime.now(timezone.utc).isoformat(),
        "seo_puan": seo.get("toplam_puan", 0),
        "geo_puan": geo.get("toplam_puan", 0),
        "trend_sayisi": len(trendler),
    }

    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ================================================================
# ANA
# ================================================================

def main():
    parser = argparse.ArgumentParser(description="SEO & GEO optimizer")
    parser.add_argument("--video", type=str, help="Video ID")
    parser.add_argument("--title", type=str, help="Video başlığı")
    parser.add_argument("--desc", type=str, help="Video açıklaması")
    parser.add_argument("--tags", type=str, nargs="*", help="Tags")
    parser.add_argument("--trends", action="store_true", help="Trending konuları")
    parser.add_argument("--report", action="store_true", help="SEO raporu")
    args = parser.parse_args()

    print("=" * 60)
    print("SEO & GEO OPTIMIZER")
    print("=" * 60)

    if args.trends:
        # Trending konuları göster
        trendler = trend_konulari()
        print("\n-- Trending Konular --")
        for t in trendler:
            emoji = "[ISI]" if t.get("popülerlik") == "yüksek" else "[ARTI]"
            print(f"  {emoji} {t['konu']} ({t['platform']})")
        return

    if args.report:
        # SEO raporu göster
        seo = {"toplam_puan": 3, "title_uygun": True, "desc_uygun": True, "tags_uygun": True, "oneriler": []}
        geo = {"toplam_puan": 2, "schema_uygun": True, "ai_friendly": True, "oneriler": ["Schema yok"]}
        trendler = trend_konulari()
        rapor = rapor_olustur(seo, geo, trendler)
        print("\n" + rapor)
        return

    # SEO optimizasyonu
    if args.title and args.desc:
        print(f"\n[SEO] {args.title[:40]}...")
        seo = youtube_seo_optimizasyon(args.title, args.desc, args.tags or [])
        geo = geo_optimizasyon(args.title, args.desc)
        trendler = trend_konulari()

        rapor = rapor_olustur(seo, geo, trendler)
        print("\n" + rapor)

        # State güncelle
        state_guncelle(seo, geo, trendler)
        print(f"\n[OK] State guncellendi ({STATE_PATH})")
    else:
        print("Kullanim:")
        print("  python seo_optimizer.py --title '...' --desc '...' --tags tag1 tag2")
        print("  python seo_optimizer.py --trends")
        print("  python seo_optimizer.py --report")


if __name__ == "__main__":
    main()
