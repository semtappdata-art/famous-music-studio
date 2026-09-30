#!/usr/bin/env python3
"""Content audit - eski içeriği değerlendir, arşivle, tekrarla.

Profesyonel şirketler düzenli içerik denetimi yapar:
1. Her videonun performansını kontrol et
2. En iyi performing videoları tekrarla
3. Performansı düşük videoları arşivle
4. Eski içerikleri yeni platformlara yeniden kullan

Kullanım:
    python content_audit.py --dry-run    # raporla
    python content_audit.py --apply       # state'e yaz
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "durum.json")
AUDIT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "content_audit.jsonl")


# ================================================================
# İÇERİK DEĞERLENDİRME
# ================================================================

def proje_degerlendir(proje_dir: str) -> dict:
    """Bir projeyi değerlendir.

    Args:
        proje_dir: proje klasörü yolu

    Returns:
        {
            "proje": str,
            "youtube_video_id": str,
            "youtube_shorts_video_id": str,
            "youtube_publish_at": str,
            "youtube_uploaded_at": str,
            "tarih": str,
            "sure_ay": float,
            "durum": "yayinda" | "private" | "archived",
        }
    """
    state_file = os.path.join(proje_dir, "state.json")
    if not os.path.exists(state_file):
        return {}

    try:
        with open(state_file, encoding="utf-8") as f:
            s = json.load(f)
    except Exception:
        return {}

    yt_id = s.get("youtube_video_id", "")
    if not yt_id:
        return {}

    # Yayın tarihi
    publish_at = s.get("youtube_publish_at", "")
    uploaded_at = s.get("youtube_uploaded_at", "")

    # Süre hesapla (aylar)
    sure_ay = 0
    if publish_at:
        try:
            yayin_tarih = datetime.fromisoformat(publish_at.replace("Z", "+00:00"))
            simdi = datetime.now(timezone.utc)
            sure_ay = round((simdi - yayin_tarih).days / 30, 1)
        except Exception:
            pass

    # Durum
    privacy = s.get("youtube_privacy", "public")
    if privacy == "public":
        durum = "yayinda"
    elif privacy == "unlisted" or privacy == "private":
        durum = "private"
    else:
        durum = "yayinda"

    return {
        "proje": os.path.basename(proje_dir),
        "youtube_video_id": yt_id,
        "youtube_shorts_video_id": s.get("youtube_shorts_video_id", ""),
        "youtube_publish_at": publish_at,
        "youtube_uploaded_at": uploaded_at,
        "tarih": s.get("created", ""),
        "sure_ay": sure_ay,
        "durum": durum,
        "theme": s.get("theme", ""),
        "title": s.get("title", ""),
    }


def tum_projelari_degerlendir() -> list[dict]:
    """Tüm projeleri değerlendir.

    Returns:
        [{"proje": ..., "youtube_video_id": ..., ...}, ...]
    """
    projeler = []
    projects_dir = "projects"

    if not os.path.isdir(projects_dir):
        return projeler

    for d in sorted(os.listdir(projects_dir)):
        proje_dir = os.path.join(projects_dir, d)
        if os.path.isdir(proje_dir):
            degerlendirme = proje_degerlendir(proje_dir)
            if degerlendirme:
                projeler.append(degerlendirme)

    return projeler


# ================================================================
# ARŞİV KARARLARI
# ================================================================

def arsiv_kararlari(projeler: list[dict]) -> list[dict]:
    """Her proje için arşiv kararı verir.

    Karar kriterleri:
    - 12+ aydır yayınlanmamış -> arşivle
    - 6+ aydır yayınlanmış ama izlenme düşük -> tekrarla
    - 3+ aydır yayınlanmış ve izlenme iyi -> koru

    Returns:
        [{"proje": ..., "karar": "arsivle" | "tekrarla" | "koru", "gerekce": ...}, ...]
    """
    kararlar = []

    for p in projeler:
        sure = p.get("sure_ay", 0)
        durum = p.get("durum", "yayinda")
        proje = p.get("proje", "-")

        if durum != "yayinda":
            continue  # Zaten archivlenmiş

        if sure >= 12:
            kararlar.append({
                "proje": proje,
                "karar": "arsivle",
                "gerekce": f"{sure} ay yayınlandı, izlenme ölçülmedi",
                "oncelik": "dusuk",
            })
        elif sure >= 6:
            kararlar.append({
                "proje": proje,
                "karar": "tekrarla",
                "gerekce": f"{sure} ay yayınlandı, izlenme kontrol edilmeli",
                "oncelik": "orta",
            })
        else:
            kararlar.append({
                "proje": proje,
                "karar": "koru",
                "gerekce": f"{sure} ay yayınlandı, henüz erken",
                "oncelik": "yuksek",
            })

    # Öncelik sırasına göre sırala
    oncelik_sira = {"yuksek": 0, "orta": 1, "dusuk": 2}
    kararlar.sort(key=lambda x: oncelik_sira.get(x.get("oncelik", "dusuk"), 2))

    return kararlar


# ================================================================
# RAPOR
# ================================================================

def rapor_olustur(kararlar: list[dict]) -> str:
    """Arşiv kararlarından rapor oluşturur."""
    if not kararlar:
        return "İçerik audit yok - projen yok."

    satirlar = [
        "=" * 60,
        "CONTENT AUDIT RAPORU",
        f"Tarih: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "=" * 60,
        "",
        f"Toplam yayinda: {len(kararlar)}",
        "",
    ]

    # Karar özetleri
    arsivle = sum(1 for k in kararlar if k["karar"] == "arsivle")
    tekrarla = sum(1 for k in kararlar if k["karar"] == "tekrarla")
    koru = sum(1 for k in kararlar if k["karar"] == "koru")

    satirlar.append(f"  Arsivle: {arsivle}")
    satirlar.append(f"  Tekrarla: {tekrarla}")
    satirlar.append(f"  Koru: {koru}")
    satirlar.append("")

    # Detaylı liste
    satirlar.append("-- Kararlar --")
    for k in kararlar[:15]:  # İlk 15
        emoji = {"arsivle": "[ARSIV]", "tekrarla": "[TEKRAR]", "koru": "[OK]"}
        emoji_str = emoji.get(k["karar"], "?")
        satirlar.append(f"  {emoji_str} {k['proje']}: {k['karar']}")
        satirlar.append(f"     {k['gerekce']}")
        satirlar.append("")

    # Öneriler
    satirlar.append("-- Öneriler --")
    if arsivle > 0:
        satirlar.append(f"  [ARSIV] {arsivle} video arşivlenebilir")
        satirlar.append("    -> Playlist'den çıkar, state'de archive标记la")
    if tekrarla > 0:
        satirlar.append(f"  [TEKRAR] {tekrarla} video tekrarlanmalı")
        satirlar.append("    -> Aynı konuyla yeni video üret")
        satirlar.append("    -> Farklı açılımla yeniden paketle")
    if koru > 0:
        satirlar.append(f"  [OK] {koru} video korunmalı")
        satirlar.append("    -> Mevcut durumda bırak")

    return "\n".join(satirlar)


# ================================================================
# STATE GÜNCELLEME
# ================================================================

def state_guncelle(kararlar: list[dict]):
    """Son audit sonuçlarını durum.json'a yazar."""
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}

    state["content_audit"] = {
        "son_calısma": datetime.now(timezone.utc).isoformat(),
        "karar_sayisi": len(kararlar),
        "arsivle": sum(1 for k in kararlar if k["karar"] == "arsivle"),
        "tekrarla": sum(1 for k in kararlar if k["karar"] == "tekrarla"),
        "koru": sum(1 for k in kararlar if k["karar"] == "koru"),
        "kararlar": kararlar,
    }

    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ================================================================
# ANA
# ================================================================

def main():
    parser = argparse.ArgumentParser(description="Content audit")
    parser.add_argument("--dry-run", action="store_true", help="Sadece raporla")
    parser.add_argument("--apply", action="store_true", help="State'e yaz")
    args = parser.parse_args()

    print("=" * 60)
    print("CONTENT AUDIT")
    print("=" * 60)

    # Projeleri değerlendir
    print("\n[Değerlendirme] Projeler analiz ediliyor...")
    projeler = tum_projelari_degerlendir()
    print(f"  {len(projeler)} video bulundu")

    # Arşiv kararları
    kararlar = arsiv_kararlari(projeler)
    print(f"  {len(kararlar)} karar")

    # Rapor
    rapor = rapor_olustur(kararlar)
    print("\n" + rapor)

    # State güncelle
    if args.apply and kararlar:
        state_guncelle(kararlar)
        print(f"\n[OK] State guncellendi ({STATE_PATH})")

    return kararlar


if __name__ == "__main__":
    main()
