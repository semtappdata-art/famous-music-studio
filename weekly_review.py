#!/usr/bin/env python3
"""Weekly review - profesyonel şirketler haftalık performans değerlendirmesi yapar.

Her hafta:
1. Önceki hafta metrikleri topla
2. Hangi video abone kazandı?
3. Hangi format daha iyi?
4. Sonraki hafta strateji kararları
5. Öğrenilenleri backlog'a ekle

Kullanım:
    python weekly_review.py --dry-run    # raporla
    python weekly_review.py --apply       # state'e yaz
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "durum.json")


# ================================================================
# VERİ TOPLAMA
# ================================================================

def haftalik_metrik_oku() -> dict:
    """Durum.json'dan haftalık metrikleri okur.

    Returns:
        {
            "analytics_dashboard": {...},
            "growth_loop": {...},
            "community_mgmt": {...},
            "ab_test": {...},
        }
    """
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}

    return {
        "analytics": state.get("analytics_dashboard", {}),
        "growth": state.get("growth_loop", {}),
        "community": state.get("community_mgmt", {}),
        "ab_test": state.get("ab_test", {}),
    }


def video_metrikleri_oku() -> list:
    """projects/*/state.json'dan video metriklerini okur.

    Returns:
        [{"proje": ..., "youtube_video_id": ..., "views": 0, ...}, ...]
    """
    videolar = []
    projects_dir = "projects"

    if not os.path.isdir(projects_dir):
        return videolar

    for d in os.listdir(projects_dir):
        state_file = os.path.join(projects_dir, d, "state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, encoding="utf-8") as f:
                    s = json.load(f)

                yt_id = s.get("youtube_video_id", "")
                if yt_id:
                    videolar.append({
                        "proje": d,
                        "youtube_video_id": yt_id,
                        "youtube_shorts_video_id": s.get("youtube_shorts_video_id", ""),
                        "youtube_publish_at": s.get("youtube_publish_at", ""),
                        "youtube_uploaded_at": s.get("youtube_uploaded_at", ""),
                    })
            except Exception:
                pass

    return videolar


# ================================================================
# ANALİZ
# ================================================================

def haftalik_analiz(metrikler: dict, videolar: list) -> dict:
    """Haftalık analiz yapar.

    Returns:
        {
            "toplam_izlenme": int,
            "toplam_abone": int,
            "en_iyi_video": str,
            "format_performansi": {"uzun": ..., "shorts": ...},
            "community_kalite": str,
            "ab_test_kazanan": str,
            "oncelikler": list[str],
        }
    """
    # Analytics metrikleri
    analytics = metrikler.get("analytics", {}).get("metrikler", {})

    # Growth loop outlierları
    growth = metrikler.get("growth", {})
    en_iyi_video = growth.get("en_iyi_video", {})

    # Community kalitesi
    community = metrikler.get("community", {})
    komsu_analizleri = community.get("yorum_analizleri", {})
    kalite_puanlari = []
    for v, a in komsu_analizleri.items():
        kalite = a.get("yorum_kalitesi", "yok")
        if kalite == "yüksek":
            kalite_puanlari.append(3)
        elif kalite == "orta":
            kalite_puanlari.append(2)
        else:
            kalite_puanlari.append(1)

    ort_kalite = round(sum(kalite_puanlari) / len(kalite_puanlari), 1) if kalite_puanlari else 0

    # A/B test kazananı
    ab_test = metrikler.get("ab_test", {})
    ab_test_count = ab_test.get("toplam_test", 0)

    # Format performansı
    format_perf = analytics.get("format_performansi", {})

    # Öncelikler
    oncelikler = []

    # Subscriber conversion düşükse
    spk = analytics.get("subs_per_1k_views", 0)
    if spk < 1:
        oncelikler.append("Subs/1K düşük -> thumbnail + title iyileştir")
    elif spk > 5:
        oncelikler.append("Subs/1K yüksek -> aynı formatı tekrarla")

    # CTR düşükse
    ctr = analytics.get("ctr_ort", 0)
    if ctr < 2:
        oncelikler.append("CTR düşük -> packaging revizyonu")

    # Retention düşükse
    ret = analytics.get("retention_ort", 0)
    if ret < 30:
        oncelikler.append("Retention düşük -> hook güçlendir")

    # Topluluk zayıfsa
    if ort_kalite < 1.5:
        oncelikler.append("Topluluk zayıf -> CTA'da soru sor")

    # A/B test yapılmadıysa
    if ab_test_count == 0:
        oncelikler.append("A/B testi yok -> ilk test oluştur")

    return {
        "toplam_izlenme": analytics.get("toplam_izlenme", 0),
        "toplam_abone": analytics.get("toplam_abone", 0),
        "en_iyi_video": en_iyi_video.get("title", "-"),
        "format_performansi": format_perf,
        "community_kalite": ort_kalite,
        "ab_test_sayisi": ab_test_count,
        "oncelikler": oncelikler,
    }


# ================================================================
# RAPOR
# ================================================================

def rapor_olustur(analiz: dict, videolar: list) -> str:
    """Haftalık rapor oluşturur."""
    satirlar = [
        "=" * 60,
        "HAFTALIK REVIEW",
        f"Tarih: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "=" * 60,
        "",
        "-- Ana Metrikler --",
        f"  Izlenme: {analiz['toplam_izlenme']:,}",
        f"  Abone: {analiz['toplam_abone']:,}",
        f"  En iyi video: {analiz['en_iyi_video'][:40]}",
        "",
        "-- Format Performansı --",
    ]

    fp = analiz.get("format_performansi", {})
    satirlar.append(f"  Uzun format: %{fp.get('uzun_yuzde', 0)}")
    satirlar.append(f"  Shorts: %{round(100 - fp.get('uzun_yuzde', 0), 1)}")

    satirlar.append("")
    satirlar.append(f"  Community kalite: {analiz['community_kalite']}/3")
    satirlar.append(f"  A/B test: {analiz['ab_test_sayisi']}")

    satirlar.append("")
    satirlar.append("-- Öncelikler --")
    for oncelik in analiz.get("oncelikler", []):
        satirlar.append(f"  -> {oncelik}")

    if not analiz.get("oncelikler"):
        satirlar.append("  -> Tüm metrikler iyi -> Sürürden çık, yeni format dene")

    satirlar.append("")
    satirlar.append("-- Video Listesi --")
    for v in videolar[:10]:
        yt_id = v.get("youtube_video_id", "")
        proje = v.get("proje", "-")
        satirlar.append(f"  {proje}: {yt_id[:20]}...")

    satirlar.append("")
    satirlar.append("-- Sonraki Hafta --")
    satirlar.append("  1. En iyi videoyu tekrarla")
    satirlar.append("  2. A/B test yap")
    satirlar.append("  3. Yeni format dene")
    satirlar.append("  4. Toplulukla etkileşime geç")

    return "\n".join(satirlar)


# ================================================================
# STATE GÜNCELLEME
# ================================================================

def state_guncelle(analiz: dict):
    """Son review sonuçlarını durum.json'a yazar."""
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}

    state["weekly_review"] = {
        "son_calısma": datetime.now(timezone.utc).isoformat(),
        "analiz": analiz,
    }

    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ================================================================
# ANA
# ================================================================

def main():
    parser = argparse.ArgumentParser(description="Weekly review")
    parser.add_argument("--dry-run", action="store_true", help="Sadece raporla")
    parser.add_argument("--apply", action="store_true", help="State'e yaz")
    args = parser.parse_args()

    print("=" * 60)
    print("HAFTALIK REVIEW")
    print("=" * 60)

    # Veri topla
    metrikler = haftalik_metrik_oku()
    videolar = video_metrikleri_oku()

    print(f"\n[Veri] {len(videolar)} video, {len(metrikler)} metrik kaynagi")

    # Analiz
    analiz = haftalik_analiz(metrikler, videolar)

    # Rapor
    rapor = rapor_olustur(analiz, videolar)
    print("\n" + rapor)

    # State güncelle
    if args.apply:
        state_guncelle(analiz)
        print(f"\n[OK] State guncellendi ({STATE_PATH})")

    return analiz



def haftalık_produkyon_plani() -> dict:
    """
    Haftalık üretim planı oluşturur.

    KULLANICI ŞARTI:
    - Pazartesi, Çarşamba, Cuma günlerinde
    - Günlük 2 yeni parça + 1 DJ seti
    - Haftalık toplam: 6 yeni parça + 3 DJ seti

    RETURNS:
        dict with:
        - "hedef_parça": 6
        - "hedef_dj_seti": 3
        - "günlük_plan": {gün: {"parça": 2, "dj_seti": 1}}
        - "eksik": planlanan_toplam - zaten_var
    """
    import os
    from datetime import datetime, timedelta

    # Hedefler
    hedef_parça = 6
    hedef_dj_seti = 3

    # Haftanın günleri (Pazartesi=0, Cuma=4)
    hafta_günleri = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    target_günler = ["Pazartesi", "Çarşamba", "Cuma"]

    # Projeler klasöründen already-produced'ı say
    projects_dir = "projects"
    already_parça = 0
    already_dj_seti = 0

    if os.path.isdir(projects_dir):
        # Sadece ana kataloğundaki (dj_sets dışı) parça say
        for d in os.listdir(projects_dir):
            p = os.path.join(projects_dir, d)
            if not os.path.isdir(p):
                continue
            # DJ setlerini saymıyoruz buraya
            if d.startswith("dj_sets") or d.startswith("derlemeler"):
                continue
            state_file = os.path.join(p, "state.json")
            if os.path.exists(state_file):
                try:
                    with open(state_file, encoding="utf-8") as f:
                        state = json.load(f)
                    # Yeni parça mı kontrolü (youtube_video_id varsa say)
                    if state.get("youtube_video_id"):
                        already_parça += 1
                except:
                    pass

    # Basit hesap: hedef - already = eksik
    eksik_parça = max(0, hedef_parça - already_parça)
    eksik_dj_seti = max(0, hedef_dj_seti - already_dj_seti)

    plan = {
        "hedef_parça": hedef_parça,
        "hedef_dj_seti": hedef_dj_seti,
        "already_parça": already_parça,
        "already_dj_seti": already_dj_seti,
        "eksik_parça": eksik_parça,
        "eksik_dj_seti": eksik_dj_seti,
        "günlük_plan": {},
        "tarih": datetime.now().strftime("%Y-%m-%d"),
    }

    # Günlük planı oluştur (Pazartesi, Çarşamba, Cuma)
    for gün in target_günler:
        plan["günlük_plan"][gün] = {"parça": 2, "dj_seti": 1}

    return plan


if __name__ == "__main__":
    main()
