#!/usr/bin/env python3
"""Analytics dashboard - YouTube performans ölçümü ve raporlama.

Profesyonel şirketler haftada bir kez bu dashboard'u çalıştırır:
1. İzlenme süresi, CTR, retention, abone kazanımı
2. Hangi video abone kazandı? (subs/1K views)
3. Hangi format eğlence mi, satış mı?
4. Sonraki hafta strateji kararları

Kullanım:
    python analytics_dashboard.py --dry-run    # raporla, yazma
    python analytics_dashboard.py --apply      # state'e yaz
    python analytics_dashboard.py --video ID   # tek video detayı
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'upload'))

# YouTube analytics
try:
    from youtube_analytics import get_service, yetkilendir, _video_idler, rapor
    YT_ANALYTICS_OK = True
except Exception:
    YT_ANALYTICS_OK = False

# State
STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "durum.json")

# ================================================================
# METRIKLER
# ================================================================

def hesapla_metrikler(rapor_data: dict) -> dict:
    """YouTube analytics raporundan ana metrikleri hesaplar.

    Returns:
        {
            "toplam_izlenme": int,
            "toplam_abone": int,
            "watch_saat": float,
            "ctr_ort": float,
            "retention_ort": float,
            "subs_per_1k_views": float,
            "en_iyi_video": {"title": ..., "subs": ...},
            "en_cok_gorusen": {"title": ..., "views": ...},
            "format_performansi": {"uzun": ..., "shorts": ...},
        }
    """
    if not rapor_data:
        return {}

    videolar = rapor_data.get("videos", [])
    if not videolar:
        return {}

    toplam_izlenme = sum(v.get("views", 0) for v in videolar)
    toplam_abone = sum(v.get("subscribers", 0) for v in videolar)
    toplam_watch = sum(v.get("watch_time", 0) for v in videolar)

    # CTR ortalama (likes/views * 100)
    ctr_values = []
    for v in videolar:
        views = v.get("views", 0)
        likes = v.get("likes", 0)
        if views > 0:
            ctr_values.append(likes / views * 100)
    ctr_ort = round(sum(ctr_values) / len(ctr_values), 2) if ctr_values else 0

    # Retention ortalama (watch_time / views * 100)
    retention_values = []
    for v in videolar:
        views = v.get("views", 0)
        watch = v.get("watch_time", 0)
        if views > 0:
            retention_values.append(watch / views * 100)
    retention_ort = round(sum(retention_values) / len(retention_values), 2) if retention_values else 0

    # Subs per 1K views (kalite metriği)
    subs_per_1k = round(toplam_abone / toplam_izlenme * 1000, 2) if toplam_izlenme > 0 else 0

    # En iyi video (abone kazanımı)
    en_iyi = max(videolar, key=lambda v: v.get("subscribers", 0)) if videolar else {}

    # En çok görüntülenen
    en_cok = max(videolar, key=lambda v: v.get("views", 0)) if videolar else {}

    # Format performansı (uzun vs shorts)
    uzun_views = sum(v.get("views", 0) for v in videolar if v.get("duration", 0) > 60)
    shorts_views = sum(v.get("views", 0) for v in videolar if v.get("duration", 0) <= 60)

    return {
        "toplam_izlenme": toplam_izlenme,
        "toplam_abone": toplam_abone,
        "watch_saat": round(toplam_watch / 3600, 1),
        "ctr_ort": ctr_ort,
        "retention_ort": retention_ort,
        "subs_per_1k_views": subs_per_1k,
        "en_iyi_video": {
            "title": en_iyi.get("title", ""),
            "subs": en_iyi.get("subscribers", 0),
            "views": en_iyi.get("views", 0),
        },
        "en_cok_gorusen": {
            "title": en_cok.get("title", ""),
            "views": en_cok.get("views", 0),
        },
        "format_performansi": {
            "uzun_format_views": uzun_views,
            "shorts_views": shorts_views,
            "uzun_yuzde": round(uzun_views / max(uzun_views + shorts_views, 1) * 100, 1),
        },
    }


def rapor_olustur(metrikler: dict) -> str:
    """Metriklerden okunabilir rapor oluşturur."""
    if not metrikler:
        return "Veri yok - YouTube Analytics token kontrol edin."

    satirlar = [
        "=" * 60,
        "ANALYTICS DASHBOARD",
        f"Tarih: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "=" * 60,
        "",
        "── Ana Metrikler ──",
        f"  Izlenme: {metrikler['toplam_izlenme']:,}",
        f"  Abone: {metrikler['toplam_abone']:,}",
        f"  Watch-time: {metrikler['watch_saat']} sn",
        f"  CTR (ort): %{metrikler['ctr_ort']}",
        f"  Retention (ort): %{metrikler['retention_ort']}",
        f"  Subs/1K views: {metrikler['subs_per_1k_views']}",
        "",
        "── En İyi Video ──",
        f"  {metrikler['en_iyi_video']['title'][:50]}...",
        f"  Abone kazandı: {metrikler['en_iyi_video']['subs']:,}",
        f"  Izlenme: {metrikler['en_iyi_video']['views']:,}",
        "",
        "── En Çok Görüntülenen ──",
        f"  {metrikler['en_cok_gorusen']['title'][:50]}...",
        f"  Izlenme: {metrikler['en_cok_gorusen']['views']:,}",
        "",
        "── Format Performansı ──",
        f"  Uzun format: %{metrikler['format_performansi']['uzun_yuzde']}",
        f"  Shorts: %{round(100 - metrikler['format_performansi']['uzun_yuzde'], 1)}",
        "",
        "── Karar Önerileri ──",
    ]

    # Karar önerileri
    spk = metrikler.get("subs_per_1k_views", 0)
    if spk < 1:
        satirlar.append("  ⚠ Subs/1K views düşük → içerik kalitesi sorunlu")
        satirlar.append("    → Thumbnail + title iyileştir")
        satirlar.append("    → Hook 5 saniyede değer sun")
    elif spk > 5:
        satirlar.append("  ✓ Subs/1K views yüksek → formatı tekrarla")
        satirlar.append("    → Aynı yapıda yeni video üret")
        satirlar.append("    → Playlist'e ekle")
    else:
        satirlar.append("  → Subs/1K views orta → A/B test yap")
        satirlar.append("    → Farklı thumbnail'lar dene")
        satirlar.append("    → Farklı hook'lar dene")

    ctr = metrikler.get("ctr_ort", 0)
    if ctr < 2:
        satirlar.append("  ⚠ CTR düşük → packaging problemi")
        satirlar.append("    → Başlık + thumbnail revizyonu")
    elif ctr > 8:
        satirlar.append("  ✓ CTR yüksek → konu doğru")
        satirlar.append("    → Aynı konuyla devam et")

    ret = metrikler.get("retention_ort", 0)
    if ret < 30:
        satirlar.append("  ⚠ Retention düşük → pacing sorunlu")
        satirlar.append("    → Hook güçlendir")
        satirlar.append("    → İlk 30 sn'de değer sun")
    elif ret > 60:
        satirlar.append("  ✓ Retention yüksek → içerik kaliteli")
        satirlar.append("    → Seri formatı dene")

    return "\n".join(satirlar)


# ================================================================
# STATE GÜNCELLEME
# ================================================================

def state_guncelle(metrikler: dict):
    """Son analytics sonuçlarını durum.json'a yazar."""
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}

    state["analytics_dashboard"] = {
        "son_calısma": datetime.now(timezone.utc).isoformat(),
        "metrikler": metrikler,
    }

    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ================================================================
# ANA
# ================================================================

def main():
    parser = argparse.ArgumentParser(description="Analytics dashboard")
    parser.add_argument("--dry-run", action="store_true", help="Sadece raporla")
    parser.add_argument("--apply", action="store_true", help="State'e yaz")
    parser.add_argument("--video", type=str, help="Tek video ID'si")
    args = parser.parse_args()

    print("=" * 60)
    print("ANALYTICS DASHBOARD")
    print("=" * 60)

    # YouTube Analytics servisi
    if not YT_ANALYTICS_OK:
        print("[UYARI] youtube_analytics modulu yuklenemedi")
        print("  -> pip install google-api-python-client")
        return

    try:
        service = get_service()
        print("[OK] YouTube Analytics baglantisi")
    except Exception as e:
        print(f"[HATA] Analytics API hatasi: {e}")
        print("  -> python upload/youtube_analytics.py --auth ile yetkilendir")
        return

    # Video ID'leri
    video_idler = _video_idler()
    if not video_idler:
        print("[UYARI] Video ID bulunamadi")
        return

    if args.video:
        video_idler = {args.video: video_idler.get(args.video, "")}

    # Rapor
    print(f"\n[Rapor] {len(video_idler)} video analiz ediliyor...")
    rapor_data = rapor()

    if not rapor_data:
        print("[UYARI] Analytics verisi yok")
        return

    # Metrik hesapla
    metrikler = hesapla_metrikler(rapor_data)

    # Rapor yazdır
    rapor_metin = rapor_olustur(metrikler)
    print("\n" + rapor_metin)

    # State güncelle
    if args.apply and metrikler:
        state_guncelle(metrikler)
        print(f"\n[OK] State guncellendi ({STATE_PATH})")

    return metrikler


if __name__ == "__main__":
    main()
