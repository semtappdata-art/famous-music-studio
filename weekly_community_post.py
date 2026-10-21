#!/usr/bin/env python3
"""
Haftalık YouTube Community Post Otomasyonu — Famous Music Studio

Kullanım:
    python weekly_community_post.py --tip anket
    python weekly_community_post.py --tip teaser --proje "projects/Gece Sürüşü"
    python weekly_community_post.py --tip duyuru --metin "Yeni albüm tarihi belli oldu!"

Çalışma prensibi:
- Pazartesi: Anket (haftanın ruh hali)
- Çarşamba: Teaser (yeni parça önizleme)
- Cuma: DJ set hatırlatması / Canlı yayım duyurusu
- Diğer günler: Duyuru / Quiz

Elle_islem.py defterine kaydeder (platform=youtube, islem=youtube_community_post).
"""

import argparse
import datetime
import json
import os
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

from elle_islem import ekle, ElleIslemHatasi

TZ = datetime.timezone(datetime.timedelta(hours=3))

# Şablonlar
SABLONLAR = {
    "anket": {
        "metin": "🎵 Haftanın ruh hali?\n\n🎧 Gece Sürüşü (Melodic Techno)\n🌙 Arabesk & Trap Vibes\n😴 Chill / Organic House\n🎸 Rock / Alternative\n\nYorumda seçin veya kendiniz yazın! 👇",
        "ayrinti": "Pazartesi anketi: Haftanın ruh hali",
        "tur": "anket",
    },
    "teaser": {
        "metin": "🎶 Yeni parça yakında... 👀\n\n\"{parca_adi}\" — {tur_aciklamasi}\n\nTam sürüm bu hafta {gun_adi} çıkıyor! 🔔\n\n#FamousMusicStudio #NewMusic #TurkishMusic",
        "ayrinti": "Çarşamba teaser: {parca_adi} önizlemesi",
        "tur": "teaser",
    },
    "dj_set_hatirlatma": {
        "metin": "🎛️ Bu Cuma gece canlıyız! 🌙\n\nDJ Famous — {set_adi}\n🕐 {saat}:00 TR | YouTube Live\n\nÖnceden bildirim almak için kanala abone ol 🔔\n\n#DJFamous #NightDrive #MelodicTechno #LiveSet",
        "ayrinti": "Cuma DJ set hatırlatması: {set_adi}",
        "tur": "duyuru",
    },
    "duyuru": {
        "metin": "{metin}\n\n#FamousMusicStudio #TurkishMusic #AIAssistedMusic",
        "ayrinti": "Duyuru: {metin[:50]}...",
        "tur": "duyuru",
    },
    "quiz": {
        "metin": "🧠 Bilgi testi!\n\n{soru}\n\nA) {secenek_a}\nB) {secenek_b}\nC) {secenek_c}\n\nDoğru cevabı yorumda yazın! 👇\n\n#FamousMusicStudio #Quiz #TurkishMusicTrivia",
        "ayrinti": "Quiz: {soru[:40]}...",
        "tur": "quiz",
    },
}


def gun_adi_turkce(gun_idx: int) -> str:
    """0=Pazartesi, 6=Pazar"""
    gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    return gunler[gun_idx % 7]


def gun_hesapla(hedef_gun: str) -> str:
    """Hedef gün adından (örn. 'Cuma') gün adını döndür"""
    return hedef_gun


def community_post_olustur(**kwargs) -> dict:
    """Verilen tipten community post içeriği üretir"""
    tip = kwargs.get('tip')
    if tip not in SABLONLAR:
        raise ValueError(f"Bilinmeyen tip: {tip}. Geçerli: {list(SABLONLAR.keys())}")

    sablon = SABLONLAR[tip]
    metin = sablon["metin"].format(**kwargs)
    ayrinti = sablon["ayrinti"].format(**kwargs)
    tur = sablon["tur"]

    return {"metin": metin, "ayrinti": ayrinti, "tur": tur}


def kaydet(proje: str, metin: str, ayrinti: str, tur: str,
           kaynak: str = "otomasyon", kanit: str = None) -> dict:
    """elle_islem.py ekle fonksiyonunu çağırarak deftere yazar"""
    from elle_islem import ekle

    return ekle(
        platform="youtube",
        islem="youtube_community_post",
        ayrinti=f"Community post ({tur}): {metin[:80]}... — {ayrinti}",
        proje=proje,
        zaman=None,
        kaynak=kaynak,
        kanit=kanit,
        zaman_yaklasik=False,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Haftalık YouTube Community Post Otomasyonu — Famous Music Studio"
    )
    parser.add_argument("--tip", required=True,
                        choices=list(SABLONLAR.keys()),
                        help="Post tipi")
    parser.add_argument("--proje", default=None, help="İlgili proje klasörü (opsiyonel)")
    parser.add_argument("--parca-adi", default="Yeni Parça", help="Parça adı (teaser için)")
    parser.add_argument("--tur-aciklamasi", default="Turkish Pop / R&B", help="Tür açıklaması (teaser için)")
    parser.add_argument("--gun-adi", default=None, help="Çıkış günü (teaser için)")
    parser.add_argument("--set-adi", default="Night Drive", help="DJ set adı (dj_set_hatirlatma için)")
    parser.add_argument("--saat", default="22", help="Canlı yayın saati (dj_set_hatirlatma için)")
    parser.add_argument("--metin", default="", help="Özel metin (duyuru için)")
    parser.add_argument("--soru", default="", help="Soru (quiz için)")
    parser.add_argument("--secenek-a", default="", help="A şıkkı (quiz için)")
    parser.add_argument("--secenek-b", default="", help="B şıkkı (quiz için)")
    parser.add_argument("--secenek-c", default="", help="C şıkkı (quiz için)")
    parser.add_argument("--kaynak", default="cli", help="Kaynak etiketi (telegram, pano, claude, backfill, cli)")
    parser.add_argument("--kanit", default=None, help="Kanıt URL'i (opsiyonel)")
    parser.add_argument("--json", action="store_true", help="JSON çıktı")

    args = parser.parse_args()

    try:
        # Post içeriği üret
        kwargs = vars(args)
        post = community_post_olustur(**kwargs)

        # Deftere kaydet
        sonuc = kaydet(
            proje=args.proje,
            metin=post["metin"],
            ayrinti=post["ayrinti"],
            tur=post["tur"],
            kaynak=args.kaynak,
            kanit=args.kanit,
        )

        # Çıktı
        if args.json:
            # Windows konsolu için ASCII-safe JSON
            print(json.dumps(sonuc, ensure_ascii=True, indent=2))
        else:
            # Windows konsolu için emoji güvenli yazdırma
            mesaj = sonuc['mesaj'].replace('✅', '[OK]').replace('📝', '[TIP]').replace('❌', '[HATA]')
            print(f"{mesaj}")
            print(f"Tip: {post['tur']} | İçerik: {post['metin'][:100]}...")

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"durum": "hata", "hata": str(e)}, ensure_ascii=False))
        else:
            print(f"❌ HATA: {e}")
        return 1


if __name__ == "__main__":
    import json
    sys.exit(main())