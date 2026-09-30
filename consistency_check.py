#!/usr/bin/env python3
"""Cross-platform consistency - marka ses tutarlılığı kontrolü.

Profesyonel şirketler tüm platformlarda tutarlı ses kullanır:
1. Ton kontrolü (samimi mi, profesyonel mi?)
2. Kelime kontrolü (kullan/kaynak kelimeler)
3. CTA tutarlılığı
4. Hashtag tutarlılığı

Kullanım:
    python consistency_check.py --dry-run    # raporla
    python consistency_check.py --apply       # state'e yaz
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'upload'))

import config
import social_text

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "durum.json")
CONSISTENCY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "consistency_check.jsonl")


# ================================================================
# TUTARLILIK KONTROLÜ
# ================================================================

def tutarlilik_kontrol(meta: dict, caption: str, platform: str) -> dict:
    """Tek bir caption'ın tutarlılığını kontrol eder.

    Kontroller:
    1. Marka sesi: ton uygun mu?
    2. Kullan/kaynak kelimeler: uygun mu?
    3. CTA tutarlılığı: fayda-based mi?
    4. Hashtag sayısı: platform uygun mu?

    Returns:
        {
            "platform": str,
            "ton_uygun": bool,
            "kelime_uygun": bool,
            "cta_uygun": bool,
            "hashtag_uygun": bool,
            "toplam_puan": int,  # 0-4
            "sorunlar": list[str],
        }
    """
    sorunlar = []
    puan = 0

    # 1. Ton kontrolü
    ton = config.MARKA_SES.get("ton", "")
    if ton:
        # Ton kelimesi caption'da var mi? (en az 1 kelime bulunsun)
        ton_words = [w.lower() for w in ton.split() if len(w) > 3]
        ton_match = sum(1 for w in ton_words if w in caption.lower())
        if ton_match >= 1:
            puan += 1
        else:
            # Ton kelimesi yok ama caption varsa yaris puan
            # (caption hook satirlari tarafindan uretilir, MARKA_SES tonu
            #  yonlendiricidir, kesin eslesme beklenmez)
            puan += 0.5

    # 2. Kullan/kaynak kelimeler
    kullan_kelimesi = config.MARKA_SES.get("kullan", [])
    kacin_kelimesi = config.MARKA_SES.get("kacin", [])

    kullan_varmi = any(k.lower() in caption.lower() for k in kullan_kelimesi)
    kacin_var_mi = any(k.lower() in caption.lower() for k in kacin_kelimesi)

    if kullan_varmi:
        puan += 1
    else:
        sorunlar.append("Kullan kelimesi yok")

    if kacin_var_mi:
        sorunlar.append("Kacin kelimesi var!")
    else:
        puan += 1

    # 3. CTA kontrolü
    cta_kural = config.MARKA_SES.get("cta_kural", "")
    if cta_kural:
        # CTA'nın fayda-based olduğunu kontrol et
        # "abone ol" gibi generic CTA'lar sorunlu
        generic_cta = ["abone ol", "follow", "like", "subscribe"]
        is_generic = any(g in caption.lower() for g in generic_cta)
        if not is_generic:
            puan += 1
        else:
            sorunlar.append("Generic CTA kullanildi")

    # 4. Hashtag sayısı (platform uygunluğu)
    hashtag_sayisi = caption.count("#")
    platform_hashtag_limit = {
        "instagram": 30,
        "tiktok": 5,
        "youtube": 15,
        "facebook": 5,
        "twitter": 3,
        "telegram": 5,
        "bluesky": 5,
    }
    limit = platform_hashtag_limit.get(platform, 10)
    if hashtag_sayisi <= limit:
        puan += 1
    else:
        sorunlar.append(f"Hashtag fazla: {hashtag_sayisi} (limit: {limit})")

    return {
        "platform": platform,
        "ton_uygun": puan >= 2,
        "kelime_uygun": not any("Kacin" in s for s in sorunlar),
        "cta_uygun": not any("Generic CTA" in s for s in sorunlar),
        "hashtag_uygun": puan >= 3,
        "toplam_puan": puan,
        "sorunlar": sorunlar,
    }


def tum_platformlari_kontrol(meta: dict) -> list[dict]:
    """Tüm platformlar için tutarlılık kontrolü yapar.

    Returns:
        [{"platform": ..., "puan": ..., "sorunlar": [...]}, ...]
    """
    sonuclar = []

    for platform in ["youtube", "tiktok", "instagram", "facebook", "twitter", "telegram", "bluesky"]:
        try:
            caption = social_text.build_caption(meta, ai_beyani=True, platform=platform)
            sonuc = tutarlilik_kontrol(meta, caption, platform)
            sonuclar.append(sonuc)
        except Exception as e:
            sonuclar.append({
                "platform": platform,
                "puan": 0,
                "sorunlar": [f"Hata: {str(e)[:50]}"],
            })

    return sonuclar


# ================================================================
# RAPOR
# ================================================================

def rapor_olustur(sonuclar: list[dict]) -> str:
    """Tutarlılık sonuçlarından rapor oluşturur."""
    if not sonuclar:
        return "Consistency check yok."

    satirlar = [
        "=" * 60,
        "CONSISTENCY CHECK RAPORU",
        f"Tarih: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "=" * 60,
        "",
    ]

    # Platform bazlı puanlar
    for s in sonuclar:
        platform = s.get("platform", "-")
        puan = s.get("toplam_puan", 0)
        sorunlar = s.get("sorunlar", [])

        # Puan emoji
        if puan >= 3:
            emoji = "[OK]"
        elif puan >= 2:
            emoji = "[UYARI]"
        else:
            emoji = "[HATA]"

        satirlar.append(f"{emoji} {platform}: {puan}/4")
        for sorun in sorunlar:
            satirlar.append(f"   - {sorun}")
        satirlar.append("")

    # Genel değerlendirme
    ortalama_puan = sum(s.get("toplam_puan", 0) for s in sonuclar) / len(sonuclar) if sonuclar else 0

    satirlar.append("-- Genel Değerlendirme --")
    satirlar.append(f"  Ortalama puan: {ortalama_puan:.1f}/4")

    if ortalama_puan >= 3:
        satirlar.append("  [OK] Marka ses tutarlı")
    elif ortalama_puan >= 2:
        satirlar.append("  [UYARI] Marka ses kısmı tutarsız")
    else:
        satirlar.append("  [HATA] Marka ses önemli ölçüde tutarsız")

    satirlar.append("")
    satirlar.append("-- Öneriler --")

    # En sık sorun
    tum_sorunlar = []
    for s in sonuclar:
        tum_sorunlar.extend(s.get("sorunlar", []))

    if tum_sorunlar:
        from collections import Counter
        sayac = Counter(tum_sorunlar)
        for sorun, sayi in sayac.most_common(3):
            satirlar.append(f"  -> {sorun} ({sayi} platformda)")
    else:
        satirlar.append("  -> Tüm platformlar tutarlı")

    return "\n".join(satirlar)


# ================================================================
# STATE GÜNCELLEME
# ================================================================

def state_guncelle(sonuclar: list[dict]):
    """Son consistency sonuçlarını durum.json'a yazar."""
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}

    state["consistency_check"] = {
        "son_calısma": datetime.now(timezone.utc).isoformat(),
        "ortalama_puan": round(sum(s.get("toplam_puan", 0) for s in sonuclar) / len(sonuclar), 1) if sonuclar else 0,
        "sonuclar": sonuclar,
    }

    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ================================================================
# ANA
# ================================================================

def main():
    parser = argparse.ArgumentParser(description="Consistency check")
    parser.add_argument("--dry-run", action="store_true", help="Sadece raporla")
    parser.add_argument("--apply", action="store_true", help="State'e yaz")
    parser.add_argument("--project", type=str, help="Proje klasörü")
    args = parser.parse_args()

    print("=" * 60)
    print("CONSISTENCY CHECK")
    print("=" * 60)

    # Meta bilgisi
    if args.project:
        proje_dir = args.project
    else:
        # İlk projeyi al
        projects_dir = "projects"
        if os.path.isdir(projects_dir):
            proje_dir = os.path.join(projects_dir, os.listdir(projects_dir)[0])
        else:
            print("[UYARI] Proje klasörü yok")
            return

    # Meta.json oku
    meta_file = os.path.join(proje_dir, "meta.json")
    if not os.path.exists(meta_file):
        print("[UYARI] meta.json bulunamadi")
        return

    try:
        with open(meta_file, encoding="utf-8") as f:
            meta = json.load(f)
    except Exception as e:
        print(f"[HATA] meta.json okunamadi: {e}")
        return

    print(f"\n[Proje] {meta.get('title', '-')}")

    # Tutarlılık kontrolü
    print("[Kontrol] Platformlar kontrol ediliyor...")
    sonuclar = tum_platformlari_kontrol(meta)

    # Rapor
    rapor = rapor_olustur(sonuclar)
    print("\n" + rapor)

    # State güncelle
    if args.apply and sonuclar:
        state_guncelle(sonuclar)
        print(f"\n[OK] State guncellendi ({STATE_PATH})")

    return sonuclar


if __name__ == "__main__":
    main()
