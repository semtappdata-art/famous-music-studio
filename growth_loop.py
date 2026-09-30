# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""Growth loop — rekabet taraması + outlier tespiti + keyword validation.

Profesyonel şirketler haftada 1 kez bu döngüyü çalıştırır:
1. Rekabet analizi (5 rakip, son 30 gün)
2. Outlier tespiti (2x-3x atasayan videolar)
3. Keyword validation (arama talebi)
4. Paketleme değerlendirmesi (CTR + retention)

Kullanım:
    python growth_loop.py --dry-run    # sadece raporla, yazma
    python growth_loop.py --apply       # state'e yaz
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# --- repo root ekle ---
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'upload'))

import config
import youtube_auth

# ================================================================
# SABITLER
# ================================================================

# Rekabet kanalı listesi — bu kanalların videoları outlier karşılaştırması için referans
REKABET_KANALLARI = getattr(config, "GROWTH_REKABET_KANALLARI", [])

# Outlier eşiği — kanal ortalamasının kaç katı üstü outlier
OUTLIER_CARPAN = getattr(config, "GROWTH_OUTLIER_CARPAN", 2.0)

# Minimal izlenme sayısı — bu altındaki videolar outlier olarak değerlendirilmez
MIN_VIEWS = getattr(config, "GROWTH_MIN_VIEWS", 1000)

# Keyword validation için arama sonucu tabanı
# (kelime, arama_miktarı, rekabet_derecesi)
KEYWORD_TABANI = getattr(config, "GROWTH_KEYWORDS", [])


# ================================================================
# YOUTUBE API
# ================================================================

def _youtube_service():
    """YouTube Data API servisi döndürür."""
    try:
        from googleapiclient.discovery import build
        creds = youtube_auth.get_authenticated_service()
        if creds is None or not creds.valid:
            return None
        return build("youtube", "v3", credentials=creds, cache_discovery=False)
    except Exception:
        return None


def _channel_id(youtube, handle: str) -> str | None:
    """@handle -> channelId."""
    try:
        r = youtube.channels().list(
            part="id", forUsername=handle.lstrip("@")
        ).execute()
        items = r.get("items", [])
        return items[0]["id"] if items else None
    except Exception:
        return None


def _kanal_videolari(youtube, channel_id: str, max_results: int = 30):
    """Kanalın son max_results videosunu liste olarak döndürür."""
    try:
        r = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            type="video",
            order="date",
            maxResults=max_results,
        ).execute()
        videos = []
        for item in r.get("items", []):
            videos.append({
                "video_id": item["id"]["videoId"],
                "baslik": item["snippet"]["title"],
                "yayin_tarihi": item["snippet"]["publishedAt"],
            })
        return videos
    except Exception:
        return []


def _video_istatistik(youtube, video_id: str) -> dict | None:
    """Videonun istatistiklerini döndürür."""
    try:
        r = youtube.videos().list(
            part="statistics,snippet,contentDetails",
            id=video_id,
        ).execute()
        items = r.get("items", [])
        if not items:
            return None
        s = items[0]["statistics"]
        return {
            "views": int(s.get("viewCount", 0)),
            "likes": int(s.get("likeCount", 0)),
            "comments": int(s.get("commentCount", 0)),
            "subscribers": int(s.get("subscriberCount", 0)) if "subscriberCount" in s else 0,
            "baslik": items[0]["snippet"]["title"],
            "duration": items[0]["contentDetails"].get("duration", ""),
        }
    except Exception:
        return None


# ================================================================
# REKABET ANALİZİ
# ================================================================

def rekabet_taramasi(youtube, kanal_listesi: list[str], max_video: int = 30) -> list[dict]:
    """Rekabet kanallarının son videolarını tarar.

    Returns:
        [{"kanal": str, "video_id": str, "baslik": str, "views": int, ...}, ...]
    """
    sonuclar = []
    for handle in kanal_listesi:
        cid = _channel_id(youtube, handle)
        if not cid:
            continue
        videolar = _kanal_videolari(youtube, cid, max_videos=max_videos)
        for v in videolar:
            istat = _video_istatistik(youtube, v["video_id"])
            if istat:
                istat["kanal"] = handle
                istat["video_id"] = v["video_id"]
                istat["baslik"] = v["baslik"]
                sonuclar.append(istat)
    return sonuclar


# ================================================================
# OUTLIER TESPİTİ
# ================================================================

def outlier_tespiti(videolar: list[dict], carpan: float = 2.0, min_views: int = 1000) -> list[dict]:
    """Kanal bazlı ortalamanın `carpan` katı üstü videoları outlier olarak bulur.

    Returns:
        [{"kanal": ..., "baslik": ..., "views": ..., "ortalama": ..., "carpan": ...}, ...]
    """
    # Kanal bazlı grupla
    from collections import defaultdict
    kanal_videolar = defaultdict(list)
    for v in videolar:
        kanal_videolar[v["kanal"]].append(v)

    outlierlar = []
    for kanal, vlist in kanal_videolar.items():
        views_list = [v["views"] for v in vlist if v["views"] >= min_views]
        if not views_list:
            continue
        ortalama = sum(views_list) / len(views_list)
        eşik = ortalama * carpan
        for v in vlist:
            if v["views"] >= eşik and v["views"] >= min_views:
                outlierlar.append({
                    "kanal": kanal,
                    "video_id": v.get("video_id", ""),
                    "baslik": v.get("baslik", ""),
                    "views": v["views"],
                    "ortalama": round(ortalama),
                    "carpan": round(v["views"] / ortalama, 1) if ortalama > 0 else 0,
                })

    # Çoklu olarak sırala (en yüksek carpan önce)
    outlierlar.sort(key=lambda x: x["carpan"], reverse=True)
    return outlierlar


# ================================================================
# KEYWORD VALIDATION
# ================================================================

def keyword_validate(outlierlar: list[dict], keyword_tabani: list[tuple]) -> list[dict]:
    """Outlier videolar için keyword validation yapar.

    Her outlier için keyword_tabani'ndaki terimlerle eşleşme kontrolü.
    Eşleşen keyword'ler ve arama miktarı eklenir.

    Returns:
      outlierların içine "keyword_eslesme" ve "arama_miktarı" alanları eklenir.
    """
    for o in outlierlar:
        baslik = o.get("baslik", "").lower()
        eslesmeler = []
        for kelime, arama_miktarı, rekabet in keyword_tabani:
            if kelime.lower() in baslik:
                eslesmeler.append({
                    "kelime": kelime,
                    "arama_miktarı": arama_miktarı,
                    "rekabet": rekabet,
                })
        o["keyword_eslesme"] = eslesmeler
        o["arama_miktarı_toplam"] = sum(e["arama_miktarı"] for e in eslesmeler)
    return outlierlar


# ================================================================
# PAKETLEME DEĞERLENDİRME
# ================================================================

def paketleme_degerlendirme(outlierlar: list[dict]) -> list[dict]:
    """Outlier videoların paketleme kalitesini değerlendirir.

    - CTR hesaplama (beğeni/izlenme)
    - Yorum oranı (yorum/izlenme)
    - Süre/izlenme oranı (retention proxy)

    Returns:
      outlierlara "ctr", "yorum_orani", "sure_orani" alanları eklenir.
    """
    for o in outlierlar:
        views = o.get("views", 1)
        likes = o.get("likes", 0)
        comments = o.get("comments", 0)
        o["ctr"] = round(likes / views * 100, 2) if views > 0 else 0
        o["yorum_orani"] = round(comments / views * 100, 2) if views > 0 else 0

        # Süre/izlenme oranı proxy (daha uzun süre izleme = daha iyi retention)
        duration_str = o.get("duration", "")
        if duration_str:
            try:
                # PT1M30S gibi format -> saniye
                import re
                match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", duration_str)
                if match:
                    h = int(match.group(1) or 0)
                    m = int(match.group(2) or 0)
                    s = float(match.group(3) or 0)
                    total_sn = h * 3600 + m * 60 + s
                    o["sure_sn"] = total_sn
                    o["sure_orani"] = round(total_sn / max(views, 1) * 1000, 2)  # sn per 1000 views
                else:
                    o["sure_sn"] = 0
                    o["sure_orani"] = 0
            except Exception:
                o["sure_sn"] = 0
                o["sure_orani"] = 0
        else:
            o["sure_sn"] = 0
            o["sure_orani"] = 0

    return outlierlar


def subscriber_conversion(outlierlar: list[dict]) -> list[dict]:
    """Subscriber conversion tracking.
    
    subs/1K views = kalite metriği
    Profesyonel shirketler abone sayisi degil, abone kazanim oranini takip eder.
    """
    for o in outlierlar:
        views = o.get("views", 1)
        subscribers = o.get("subscribers", 0)
        o["subs_per_1k"] = round(subscribers / views * 1000, 2) if views > 0 else 0
        o["conversion_orani"] = (
            "yuksek" if o["subs_per_1k"] > 5 else
            ("orta" if o["subs_per_1k"] > 1 else "dusuk")
        )
    return outlierlar


# ================================================================
# RAPOR
# ================================================================

def rapor_olustur(outlierlar: list[dict], rekabet_sayisi: int) -> str:
    """Outlier sonuçlarından okunabilir rapor oluşturur."""
    satirlar = [
        "=" * 60,
        "GROWTH LOOP RAPORU",
        f"Tarih: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Rekabet kanalı sayısı: {rekabet_sayisi}",
        f"Outlier bulunan video: {len(outlierlar)}",
        "=" * 60,
        "",
    ]

    if not outlierlar:
        satirlar.append("Outlier bulunamadı. Rekabet kanal listesini güncelle.")
        return "\n".join(satirlar)

    satirlar.append("-- En yüksek outlier videolar --")
    for i, o in enumerate(outlierlar[:10], 1):
        satirlar.append(
            f"{i}. [{o['carpan']}x] {o['baslik'][:50]}..."
            f" | {o['views']:,} izlenme"
            f" | CTR: %{o['ctr']}"
            f" | Keyword: {o.get('arama_miktarı_toplam', 0):,}"
        )

    satirlar.append("")
    satirlar.append("-- Keyword eşleşmeleri --")
    for o in outlierlar[:5]:
        for e in o.get("keyword_eslesme", []):
            satirlar.append(
                f"  {o['baslik'][:40]}: '{e['kelime']}' "
                f"(arama: {e['arama_miktarı']:,}, rekabet: {e['rekabet']})"
            )

    satirlar.append("")
    satirlar.append("-- Öncelik önerisi --")
    if outlierlar:
        best = outlierlar[0]
        satirlar.append(
            f"  En iyi outlier: {best['baslik'][:50]}..."
            f" ({best['carpan']}x kanal ortalaması)"
        )
        if best.get("keyword_eslesme"):
            satirlar.append(
                f"  Bu video için keyword: '{best['keyword_eslesme'][0]['kelime']}'"
            )
            satirlar.append("  -> Aynı konuyla yeni video üret")
        else:
            satirlar.append("  -> Keyword eşleşmesi yok, konu araştırması yapıl")

    return "\n".join(satirlar)


# ================================================================
# STATE GÜNCELLEME
# ================================================================

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "durum.json")


def state_guncelle(rapor: str, outlierlar: list[dict]):
    """Son growth loop sonuçlarını durum.json'a yazar."""
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}

    state["growth_loop"] = {
        "son_calısma": datetime.now(timezone.utc).isoformat(),
        "outlier_sayisi": len(outlierlar),
        "en_yuksek_carpan": outlierlar[0]["carpan"] if outlierlar else 0,
        "en_iyi_video": outlierlar[0].get("baslik", "") if outlierlar else "",
        "rapor": rapor,
    }

    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ================================================================
# ANA
# ================================================================

def main():
    parser = argparse.ArgumentParser(description="Growth loop — rekabet + outlier + keyword")
    parser.add_argument("--dry-run", action="store_true", help="Sadece raporla, state yazma")
    parser.add_argument("--apply", action="store_true", help="State'e yaz")
    args = parser.parse_args()

    print("=" * 60)
    print("GROWTH LOOP — Rekabet taraması + outlier + keyword")
    print("=" * 60)

    # YouTube servisi
    try:
        youtube = _youtube_service()
        print("[OK] YouTube API bağlantısı")
    except Exception as e:
        print(f"[HATA] YouTube API hatası: {e}")
        return

    # Rekabet listesi
    kanal_listesi = REKABET_KANALLARI
    if not kanal_listesi:
        print("[UYARI] REKABET_KANALLARI boş — config.py'a ekle")
        return

    # Rekabet taraması
    print(f"\n[KANAL] Rekabet taraması: {len(kanal_listesi)} kanal...")
    videolar = rekabet_taramasi(youtube, kanal_listesi)
    print(f"  {len(videolar)} video tarandı")

    if not videolar:
        print("[UYARI] Video bulunamadı")
        return

    # Outlier tespiti
    print(f"\n[ARASTIRMA] Outlier tespiti (carpan: {OUTLIER_CARPAN}x, min: {MIN_VIEWS} views)...")
    outlierlar = outlier_tespiti(videolar, carpan=OUTLIER_CARPAN, min_views=MIN_VIEWS)
    print(f"  {len(outlierlar)} outlier bulundu")

    # Keyword validation
    if KEYWORD_TABANI:
        print(f"\n[KEYWORD] Keyword validation ({len(KEYWORD_TABANI)} terim)...")
        outlierlar = keyword_validate(outlierlar, KEYWORD_TABANI)
    else:
        print("\n[UYARI] KEYWORD_TABANI boş — config.py'ya ekle")

    # Paketleme değerlendirmesi
    print("\n[RAPOR] Paketleme değerlendirmesi...")
    outlierlar = paketleme_degerlendirme(outlierlar)

    # Rapor
    rapor = rapor_olustur(outlierlar, len(kanal_listesi))
    print("\n" + rapor)

    # State güncelle
    if args.apply and outlierlar:
        state_guncelle(rapor, outlierlar)
        print(f"\n[OK] State güncellendi ({STATE_PATH})")
    elif args.apply and not outlierlar:
        print("\n[UYARI] Outlier yok, state güncellenmedi")

    return outlierlar


if __name__ == "__main__":
    main()
