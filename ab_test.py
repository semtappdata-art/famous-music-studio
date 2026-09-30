#!/usr/bin/env python3
"""A/B Testing framework - farklı caption'ları test et ve en iyi performansı bul.

Profesyonel şirketler her şeyi A/B test eder:
- Başlık A vs Başlık B
- Thumbnail A vs Thumbnail B
- CTA A vs CTA B
- Hashtag seti A vs B

Kullanım:
    python ab_test.py --create --video ID --variant-a "..." --variant-b "..."
    python ab_test.py --result --video ID --winner a|b
    python ab_test.py --report
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "durum.json")
AB_TEST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ab_testleri.jsonl")


# ================================================================
# TEST OLUŞTURMA
# ================================================================

def test_olustur(video_id: str, varianta: str, variantb: str, test_turu: str = "caption") -> dict:
    """Yeni A/B testi oluşturur.

    Args:
        video_id: YouTube video ID
        varianta: A varyantı (kontrol)
        variantb: B varyantı (test)
        test_turu: "caption" | "baslik" | "thumbnail" | "cta" | "hashtag"

    Returns:
        Test bilgisini döndürür
    """
    test = {
        "test_id": f"AB-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "video_id": video_id,
        "test_turu": test_turu,
        "varianta": varianta,
        "variantb": variantb,
        "baslangic": datetime.now(timezone.utc).isoformat(),
        "sonuc": None,
        "winner": None,
        "notes": "",
    }

    # JSONL dosyaya ekle
    with open(AB_TEST_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(test, ensure_ascii=False) + "\n")

    return test


# ================================================================
# SONUC KAYDEME
# ================================================================

def test_sonuc_kaydet(test_id: str, winner: str, notes: str = ""):
    """Test sonucunu kaydeder.

    Args:
        test_id: Test ID
        winner: "a" | "b" | "draw"
        notes: Yorum
    """
    with open(AB_TEST_PATH, "r", encoding="utf-8") as f:
        testler = [json.loads(line) for line in f if line.strip()]

    for test in testler:
        if test["test_id"] == test_id:
            test["sonuc"] = "tamamlandi"
            test["winner"] = winner
            test["notes"] = notes
            test["bitis"] = datetime.now(timezone.utc).isoformat()
            break

    # Dosyayı yaz again
    with open(AB_TEST_PATH, "w", encoding="utf-8") as f:
        for test in testler:
            f.write(json.dumps(test, ensure_ascii=False) + "\n")


# ================================================================
# RAPOR
# ================================================================

def rapor_olustur() -> str:
    """Tüm A/B testlerinin raporunu oluşturur."""
    if not os.path.exists(AB_TEST_PATH):
        return "Henüz A/B testi yok."

    with open(AB_TEST_PATH, "r", encoding="utf-8") as f:
        testler = [json.loads(line) for line in f if line.strip()]

    if not testler:
        return "Henüz A/B testi yok."

    satirlar = [
        "=" * 60,
        "A/B TEST RAPORU",
        f"Toplam test: {len(testler)}",
        "=" * 60,
        "",
    ]

    # Tamamlanan testler
    tamamlanan = [t for t in testler if t.get("sonuc") == "tamamlandi"]
    devam_ediyor = [t for t in testler if t.get("sonuc") != "tamamlandi"]

    satirlar.append(f"Tamamlanan: {len(tamamlanan)}")
    satirlar.append(f"Devam ediyor: {len(devam_ediyor)}")
    satirlar.append("")

    if tamamlanan:
        satirlar.append("-- Tamamlanan Testler --")
        for t in tamamlanan[-10:]:  # Son 10
            satirlar.append(
                f"  {t['test_id']}: {t['test_turu']}"
            )
            satirlar.append(f"    Winner: {t.get('winner', '-')}")
            if t.get("notes"):
                satirlar.append(f"    Not: {t['notes'][:60]}")
            satirlar.append("")

    if devam_ediyor:
        satirlar.append("-- Devam Ediyor --")
        for t in devam_ediyor[-5:]:  # Son 5
            satirlar.append(
                f"  {t['test_id']}: {t['test_turu']}"
            )
            satirlar.append(f"    Video: {t['video_id'][:20]}...")
            satirlar.append("")

    # Öğrenciler
    satirlar.append("-- Öğrenciler --")
    kazanilan_a = sum(1 for t in tamamlanan if t.get("winner") == "a")
    kazanilan_b = sum(1 for t in tamamlanan if t.get("winner") == "b")
    berabere = sum(1 for t in tamamlanan if t.get("winner") == "draw")

    satirlar.append(f"  A kazandı: {kazanilan_a}")
    satirlar.append(f"  B kazandı: {kazanilan_b}")
    satirlar.append(f"  Beraber: {berabere}")

    if kazanilan_a > kazanilan_b:
        satirlar.append("  → Varsayılan A daha iyi performans gösterdi")
    elif kazanilan_b > kazanilan_a:
        satirlar.append("  → Varsayılan B daha iyi performans gösterdi")
    else:
        satirlar.append("  → A ve B eşit performans")

    return "\n".join(satirlar)


# ================================================================
# STATE GÜNCELLEME
# ================================================================

def state_guncelle():
    """Son A/B test sonuçlarını durum.json'a yazar."""
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}

    state["ab_test"] = {
        "son_calısma": datetime.now(timezone.utc).isoformat(),
        "toplam_test": len(_test_oku()),
    }

    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _test_oku() -> list:
    """Tüm testleri oku."""
    if not os.path.exists(AB_TEST_PATH):
        return []
    with open(AB_TEST_PATH, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# ================================================================
# ANA
# ================================================================

def main():
    parser = argparse.ArgumentParser(description="A/B Testing framework")
    parser.add_argument("--create", action="store_true", help="Yeni test oluştur")
    parser.add_argument("--result", action="store_true", help="Sonucu kaydet")
    parser.add_argument("--report", action="store_true", help="Rapor göster")
    parser.add_argument("--video", type=str, help="Video ID")
    parser.add_argument("--variant-a", type=str, help="A varyantı")
    parser.add_argument("--variant-b", type=str, help="B varyantı")
    parser.add_argument("--type", type=str, default="caption", help="Test türü")
    parser.add_argument("--winner", type=str, help="Kazanan (a/b/draw)")
    parser.add_argument("--notes", type=str, help="Yorum")
    args = parser.parse_args()

    if args.create:
        if not args.video or not args.variant_a or not args.variant_b:
            print("Kullanim: --create --video ID --variant-a ... --variant-b ...")
            return
        test = test_olustur(args.video, args.variant_a, args.variant_b, args.type)
        print(f"Test olusturuldu: {test['test_id']}")
        print(f"  Video: {args.video}")
        print(f"  Tur: {args.type}")
        print(f"  A: {args.variant_a[:50]}...")
        print(f"  B: {args.variant_b[:50]}...")
        state_guncelle()

    elif args.result:
        if not args.video or not args.winner:
            print("Kullanim: --result --video ID --winner a|b|draw")
            return
        # Test ID'yi bul
        testler = _test_oku()
        test = next((t for t in testler if t["video_id"] == args.video and t.get("sonuc") != "tamamlandi"), None)
        if test:
            test_sonuc_kaydet(test["test_id"], args.winner, args.notes or "")
            print(f"Sonuc kaydedildi: {test['test_id']} -> {args.winner}")
            state_guncelle()
        else:
            print("Aktif test bulunamadi")

    elif args.report:
        print(rapor_olustur())

    else:
        print("Kullanim:")
        print("  python ab_test.py --create --video ID --variant-a ... --variant-b ...")
        print("  python ab_test.py --result --video ID --winner a|b|draw")
        print("  python ab_test.py --report")


if __name__ == "__main__":
    main()
