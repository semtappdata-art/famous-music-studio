#!/usr/bin/env python3
"""Community management - yorum takibi ve etkileşim analizi.

Profesyonel şirketler yorumları ölçek olarak kullanır:
1. Yorum sayısı = ilgi göstergesi
2. Yorum kalitesi = içerik uyumu
3. Yanıt süresi = topluluk sağlığı
4. Yorum içerikleri = gelecek içerik fikirleri

Kullanım:
    python community_mgmt.py --dry-run    # raporla
    python community_mgmt.py --apply       # state'e yaz
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'upload'))

# YouTube
try:
    from youtube_auth import get_authenticated_service
    from googleapiclient.discovery import build
    YT_OK = True
except Exception:
    YT_OK = False

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "durum.json")


# ================================================================
# YORUM ANALİZİ
# ================================================================

def yorum_al(youtube, video_id: str, max_results: int = 50) -> list[dict]:
    """Videonun son yorumlarını çeker.

    Returns:
        [{"yazar": ..., "yorum": ..., "beğeni": ..., "tarih": ...}, ...]
    """
    yorumlar = []
    try:
        r = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=max_results,
            order="relevance",
        ).execute()

        for item in r.get("items", []):
            snippet = item["snippet"]["topLevelComment"]["snippet"]
            yorumlar.append({
                "yazar": snippet["authorDisplayName"],
                "yorum": snippet["textDisplay"],
                "beğeni": snippet.get("likeCount", 0),
                "tarih": snippet["publishedAt"],
            })
    except Exception:
        pass

    return yorumlar


def yorum_analizi(yorumlar: list[dict]) -> dict:
    """Yorumları analiz eder.

    Returns:
        {
            "toplam": int,
            "ortalama_begenme": float,
            "pozitif_yuzde": float,
            "sorulan_soru": list[str],
            "yorum_kalite": "yuksek" | "orta" | "düşuk",
        }
    """
    if not yorumlar:
        return {"toplam": 0, "yorum_kalite": "yok"}

    toplam = len(yorumlar)
    toplam_beğeni = sum(y.get("beğeni", 0) for y in yorumlar)
    ortalama_begenme = round(toplam_beğeni / toplam, 1) if toplam > 0 else 0

    # Pozitif yorum oranı
    pozitif_kelimekler = ["sevgili", "harika", "mükemmel", "çok güzel", "abone", "alıntı", "keşke", "özledim"]
    pozitif = 0
    for y in yorumlar:
        yorum = y.get("yorum", "").lower()
        if any(k in yorum for k in pozitif_kelimekler):
            pozitif += 1
    pozitif_yuzde = round(pozitif / toplam * 100, 1) if toplam > 0 else 0

    # Sorulan sorular (yorumlarda soru işareti var mı)
    sorular = []
    for y in yorumlar:
        yorum = y.get("yorum", "")
        if "?" in yorum or "?" in yorum:
            sorular.append(yorum[:80])

    # Kalite puanı
    if ortalama_begenme > 5 and pozitif_yuzde > 50:
        kalite = "yüksek"
    elif ortalama_begenme > 2:
        kalite = "orta"
    else:
        kalite = "düşük"

    return {
        "toplam": toplam,
        "ortalama_begenme": ortalama_begenme,
        "pozitif_yuzde": pozitif_yuzde,
        "sorulan_soru": sorular[:5],  # İlk 5 soru
        "yorum_kalite": kalite,
    }


# ================================================================
# RAPOR
# ================================================================

def rapor_olustur(video_idler: dict, yorum_analizleri: dict) -> str:
    """Yorum analizlerinden rapor oluşturur."""
    satirlar = [
        "=" * 60,
        "COMMUNITY MANAGEMENT RAPORU",
        f"Tarih: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "=" * 60,
        "",
        "── Video Başına Yorum ──",
    ]

    for video_id, analiz in yorum_analizleri.items():
        satirlar.append(f"  {video_id[:20]}...")
        satirlar.append(f"    Toplam: {analiz.get('toplam', 0)}")
        satirlar.append(f"    Ort beğeni: {analiz.get('ortalama_begenme', 0)}")
        satirlar.append(f"    Pozitif: %{analiz.get('pozitif_yuzde', 0)}")
        satirlar.append(f"    Kalite: {analiz.get('yorum_kalite', '-')}")
        sorular = analiz.get("sorulan_soru", [])
        if sorular:
            satirlar.append(f"    Sorular: {len(sorular)}")
            for s in sorular[:2]:
                satirlar.append(f"      - {s[:60]}...")
        satirlar.append("")

    # Genel değerlendirme
    toplam_yorum = sum(a.get("toplam", 0) for a in yorum_analizleri.values())
    ortalama_kalite = []
    for a in yorum_analizleri.values():
        kalite = a.get("yorum_kalite", "yok")
        if kalite == "yüksek":
            ortalama_kalite.append(3)
        elif kalite == "orta":
            ortalama_kalite.append(2)
        else:
            ortalama_kalite.append(1)

    ort_kalite = round(sum(ortalama_kalite) / len(ortalama_kalite), 1) if ortalama_kalite else 0

    satirlar.append("── Genel Değerlendirme ──")
    satirlar.append(f"  Toplam yorum: {toplam_yorum}")
    satirlar.append(f"  Ortalama kalite: {ort_kalite}/3")

    if ort_kalite >= 2.5:
        satirlar.append("  ✓ Topluluk sağlıklı")
        satirlar.append("    → Yanıtları hızlandır")
        satirlar.append("    → Soruları video konu olarak kullan")
    elif ort_kalite >= 1.5:
        satirlar.append("  → Topluluk gelişimi gerekiyor")
        satirlar.append("    → CTA'da soru sor")
        satirlar.append("    → Pinli yorum ekle")
    else:
        satirlar.append("  ⚠ Topluluk zayıf")
        satirlar.append("    → İçerik uyumu sorunlu")
        satirlar.append("    → Hedef kitleyi tekrar belirle")

    return "\n".join(satirlar)


# ================================================================
# STATE GÜNCELLEME
# ================================================================

def state_guncelle(yorum_analizleri: dict):
    """Son community sonuçlarını durum.json'a yazar."""
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}

    state["community_mgmt"] = {
        "son_calısma": datetime.now(timezone.utc).isoformat(),
        "yorum_analizleri": yorum_analizleri,
    }

    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ================================================================
# ANA
# ================================================================

def main():
    parser = argparse.ArgumentParser(description="Community management")
    parser.add_argument("--dry-run", action="store_true", help="Sadece raporla")
    parser.add_argument("--apply", action="store_true", help="State'e yaz")
    args = parser.parse_args()

    print("=" * 60)
    print("COMMUNITY MANAGEMENT")
    print("=" * 60)

    # YouTube servisi
    if not YT_OK:
        print("[UYARI] youtube_auth modulu yuklenemedi")
        return

    try:
        creds = get_authenticated_service()
        if creds is None:
            print("[UYARI] YouTube auth gerekli")
            print("  python upload/youtube_auth.py --auth")
            return
        # creds.valid check is unreliable for service accounts
        youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
        print("[OK] YouTube baglantisi")
    except Exception as e:
        print(f"[HATA] YouTube API hatasi: {e}")
        return

    # Video ID'leri - projects klasöründen al
    video_idler = {}
    projects_dir = "projects"
    if os.path.isdir(projects_dir):
        for d in os.listdir(projects_dir):
            state_file = os.path.join(projects_dir, d, "state.json")
            if os.path.exists(state_file):
                try:
                    with open(state_file, encoding="utf-8") as f:
                        s = json.load(f)
                    yt_id = s.get("youtube_video_id")
                    if yt_id:
                        video_idler[d] = yt_id
                except Exception:
                    pass

    if not video_idler:
        print("[UYARI] Video ID bulunamadi")
        return

    print(f"\n[Analiz] {len(video_idler)} video icin yorum çekiliyor...")

    # Yorum analizi
    yorum_analizleri = {}
    for proyek, video_id in video_idler.items():
        yorumlar = yorum_al(youtube, video_id, max_results=20)
        analiz = yorum_analizi(yorumlar)
        analiz["video_id"] = video_id
        yorum_analizleri[proyek] = analiz
        print(f"  {proyek}: {analiz.get('toplam', 0)} yorum, kalite: {analiz.get('yorum_kalite', '-')}")

    # Rapor
    rapor_metin = rapor_olustur(video_idler, yorum_analizleri)
    print("\n" + rapor_metin)

    # State güncelle
    if args.apply and yorum_analizleri:
        state_guncelle(yorum_analizleri)
        print(f"\n[OK] State guncellendi ({STATE_PATH})")

    return yorum_analizleri


if __name__ == "__main__":
    main()
