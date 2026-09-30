#!/usr/bin/env python3
"""90 günlük içerik takvim — profesyonel şirket planlaması.

Kullanım:
    python content_calendar.py --dry-run    # raporla, yazma
    python content_calendar.py --apply      # state'e yaz
    python content_calendar.py --dugün      # bugünün planını göster

Çıktı:
    - Aylık tema + haftalık alt konu + günlük format rotasyonu
    - Her gönderi için: tarih, saat, platform, format, başlık, CTA
    - 80/20 kuralı: %80 değer, %20 promocional
    - %10-15 trend slot, geri kalan pillar
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config

# ================================================================
# AYLIK TEMALAR
# ================================================================

# Her ayın ana teması — içerik üretimini kolaylaştırır
AYLIK_TEMALAR = {
    1: "Yılbaşı yeni başlangıç",
    2: "Aşk & müzik",
    3: "İlkbahar enerjisi",
    4: "Gece atmosferi",
    5: "Doğa & serbest",
    6: "Yaz hazırlığı",
    7: "Yaz doruk noktası",
    8: "Gece sürüşü",
    9: "Autumn vibes",
    10: "Halloween & karanlık",
    11: "Sonbahar melankoli",
    12: "Yıl sonu derleme",
}

# Haftalık alt konular (her hafta farklı)
HAFTALIK_KONULAR = [
    "Müşteri hikayesi / kullanıcı geri bildirimi",
    "Ürün tanıtımı / yeni şarkı",
    "Sektörel ipucu / müzik eğitimi",
    "Eğlence / trend / challenge",
    "Arka sahne / yapım süreci",
    "Karşılaştırma / vs.",
    "Tip / en iyi listesi",
]

# Günlük format rotasyonu
GUNLUK_FORMAT = {
    "Pazartesi": "bilgilendirici post",
    "Salı": "Reel/Video",
    "Çarşamba": "ürün/hizmet paylaşımı",
    "Perşembe": "tartışma/soru",
    "Cuma": "eğlence/trend",
    "Cumartesi": "kullanıcı oluşturmuş içerik",
    "Pazar": "hafta özeti/özet",
}

# Platform kadans (gün)
PLATFORM_KADANS = {
    "YouTube": {"uzun": 7, "shorts": 3},
    "TikTok": {"shorts": 1},
    "Instagram": {"reels": 1, "story": 3},
    "Facebook": {"post": 1},
}

# SERI YAPISI - Profesyonel shirketler binge-worthy series kurar
SERILER = {
    "Gece Serisi": [],
    "Yaz Serisi": [],
    "Melankoli": [],
    "Enerji": [],
    "Akustik": [],
}

SERI_HEDEF = 4  # 4 video = binge tamamlanasi icin ideal

# ================================================================
# 80/20 KURALI
# ================================================================

# İçerik türleri ve dağılım
ICERIK_DAGILIMI = {
    "eğitici": 40,      # %40 değer katan
    "eğlenceli": 20,    # %20 eğlence
    "ilham verici": 10, # %10 ilham
    "promosyonel": 10,  # %10 satış odaklı
    "trend": 10,        # %10 trend slot
    "arsiv": 10,        # %10 eski içerik tekrar
}

# ================================================================
# TAKVİM ÜRETECİ
# ================================================================

def takvim_uret(
    baslangic: datetime,
    gun_sayisi: int = 90,
    tema: str = "Müzik",
) -> list[dict]:
    """90 günlük içerik takvimi üretir.

    Returns:
        [{"tarih": ..., "saat": ..., "platform": ..., "format": ...,
          "baslik": ..., "icerik_turu": ..., "cta": ..., "slug": ...}, ...]
    """
    takvim = []
    tarih = baslangic
    gun = 0

    while gun < gun_sayisi:
        gun_adi = tarih.strftime("%A")
        gun += 1

        # Haftalık alt konu
        konu_idx = (gun - 1) % len(HAFTALIK_KONULAR)
        konu = HAFTALIK_KONULAR[konu_idx]

        # Günlük format
        format_tur = GUNLUK_FORMAT.get(gun_adi, "post")

        # Platformlar için gönderiler
        for platform, kadans in PLATFORM_KADANS.items():
            for format_tip, freq in kadans.items():
                # Her N günde bir gönderi
                if gun % freq == 0:
                    # İçerik türü seç (80/20 kuralı)
                    icerik_turu = _icerik_turu_sec(gun)

                    # Başlık üret
                    baslik = _baslik_uret(tema, konu, format_tip, icerik_turu)

                    # CTA
                    cta = _cta_uret(icerik_turu)

                    takvim.append({
                        "tarih": tarih.strftime("%Y-%m-%d"),
                        "gun": gun_adi,
                        "saat": _saat_sec(platform, format_tip),
                        "platform": platform,
                        "format": format_tip,
                        "baslik": baslik,
                        "icerik_turu": icerik_turu,
                        "cta": cta,
                        "konu": konu,
                    })

        tarih += timedelta(days=1)

    return takvim


def _icerik_turu_sec(gun: int) -> str:
    """80/20 kuralına göre içerik türü seçer."""
    import random
    random.seed(gun)  # deterministik

    r = random.random() * 100
    cumulative = 0
    for tur, yuzde in ICERIK_DAGILIMI.items():
        cumulative += yuzde
        if r <= cumulative:
            return tur
    return "eğitici"


def _baslik_uret(tema: str, konu: str, format_tip: str, icerik_turu: str) -> str:
    """Başlık üretir."""
    # Tema + konu + format bazlı başlık
    if icerik_turu == "trend":
        return f"#{tema} trend — {konu[:30]}"
    elif icerik_turu == "promosyonel":
        return f"Yeni {tema} şarkısı — {konu[:30]}"
    elif icerik_turu == "eğitici":
        return f"{konu[:40]} | {format_tip}"
    else:
        return f"{konu[:40]} — {tema}"


def _cta_uret(icerik_turu: str) -> str:
    """İçerik türüne göre CTA üretir."""
    ctalar = {
        "eğitici": "Simpleyi kaydet 🔖",
        "eğlenceli": "Arkadaşına gönder 📤",
        "ilham verici": "Abone ol 🔔",
        "promosyonel": "Şimdi dinle ▶️",
        "trend": "Yorum yaz 💬",
        "arsiv": "Tekrar izle 🔁",
    }
    return ctalar.get(icerik_turu, "Abone ol 🔔")


def _saat_sec(platform: str, format_tip: str) -> str:
    """Platforma göre optimal saat seçer."""
    # Türkiye saati (UTC+3)
    saatler = {
        "YouTube": {"uzun": "19:00", "shorts": "12:00"},
        "TikTok": {"shorts": "19:00"},
        "Instagram": {"reels": "18:00", "story": "12:00"},
        "Facebook": {"post": "14:00"},
    }
    return saatler.get(platform, {}).get(format_tip, "19:00")


# ================================================================
# RAPOR
# ================================================================

def rapor_olustur(takvim: list[dict], gun_sayisi: int) -> str:
    """Takvimi okunabilir rapora dönüştürür."""
    satirlar = [
        "=" * 60,
        "90 GÜNLÜK İÇERİK TAKVİMİ",
        f"Başlangıç: {takvim[0]['tarih'] if takvim else '-'}",
        f"Bitiş: {takvim[-1]['tarih'] if takvim else '-'}",
        f"Toplam gönderi: {len(takvim)}",
        "=" * 60,
        "",
        "-- Aylık Tema --",
    ]

    # Aylık tema özetleri
    for ay in range(1, 13):
        if ay in AYLIK_TEMALAR:
            satirlar.append(f"  {ay}. ay: {AYLIK_TEMALAR[ay]}")

    satirlar.append("")
    satirlar.append("-- Haftalık Konu Döngüsü --")
    for i, konu in enumerate(HAFTALIK_KONULAR, 1):
        satirlar.append(f"  Hafta {i}: {konu}")

    satirlar.append("")
    satirlar.append("-- Platform Kadans --")
    for platform, kadans in PLATFORM_KADANS.items():
        for format_tip, freq in kadans.items():
            satirlar.append(f"  {platform} {format_tip}: {freq} günde 1")

    satirlar.append("")
    satirlar.append("-- İlk 14 Gün --")
    for g in takvim[:14]:
        satirlar.append(
            f"  {g['tarih']} {g['saat']} | {g['platform']:<12} "
            f"| {g['format']:<8} | {g['baslik'][:40]}"
        )

    satirlar.append("")
    satirlar.append("-- İçerik Türü Dağılımı --")
    for tur, yuzde in ICERIK_DAGILIMI.items():
        satirlar.append(f"  {tur}: %{yuzde}")

    satirlar.append("")
    satirlar.append("-- Kural --")
    satirlar.append("  %80 değer veren içerik, %20 promocional")
    satirlar.append("  %10-15 trend slot, geri kalan pillar")
    satirlar.append("  %20 boşluk (trend/esneklik için)")

    return "\n".join(satirlar)


# ================================================================
# STATE GÜNCELLEME
# ================================================================

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "durum.json")


def state_guncelle(takvim: list[dict]):
    """Son content calendar sonuçlarını durum.json'a yazar."""
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}

    state["content_calendar"] = {
        "olusturma": datetime.now(timezone.utc).isoformat(),
        "gun_sayisi": len(takvim),
        "toplam_gonderi": len(takvim),
        "ilk_14_gun": takvim[:14],
    }

    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ================================================================
# ANA
# ================================================================

def main():
    parser = argparse.ArgumentParser(description="90 günlük içerik takvimi")
    parser.add_argument("--dry-run", action="store_true", help="Sadece raporla")
    parser.add_argument("--apply", action="store_true", help="State'e yaz")
    parser.add_argument("--bugun", action="store_true", help="Bugünün planını göster")
    args = parser.parse_args()

    baslangic = datetime.now(timezone.utc) + timedelta(days=1)
    baslangic = baslangic.replace(hour=0, minute=0, second=0, microsecond=0)

    # Mevcut aylık tema
    ay = baslangic.month
    tema = AYLIK_TEMALAR.get(ay, "Müzik")

    print("=" * 60)
    print(f"90 GÜNLÜK İÇERİK TAKVİMİ — {tema}")
    print("=" * 60)

    takvim = takvim_uret(baslangic, gun_sayisi=90, tema=tema)

    if args.bugun:
        # Bugünün gönderileri
        bugun = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        gunluk = [g for g in takvim if g["tarih"] == bugun]
        if gunluk:
            print(f"\n[TARIH] {bugun} planı:")
            for g in gunluk:
                print(
                    f"  {g['saat']} | {g['platform']:<12} "
                    f"| {g['format']:<8} | {g['baslik'][:50]}"
                )
        else:
            print(f"\n[TARIH] {bugun} için plan yok (boşluk günü)")
        return

    rapor = rapor_olustur(takvim, 90)
    print("\n" + rapor)

    if args.apply:
        state_guncelle(takvim)
        print(f"\n[OK] State güncellendi ({STATE_PATH})")

    return takvim


if __name__ == "__main__":
    main()
