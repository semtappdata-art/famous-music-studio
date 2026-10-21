#!/usr/bin/env python3
"""
Günlük YouTube Analytics Çekici — Famous Music Studio

Kullanım:
    python daily_analytics.py
    python daily_analytics.py --gun 1  (dün)
    python daily_analytics.py --gun 7 --json

Çalışır:
- youtube_analytics.py rapor fonksiyonunu çağırır
- Sonuçları logs/daily_views_YYYY-MM-DD.json olarak kaydeder
- Elle_islem.py defterine "analitik_rapor" işlemi olarak kaydeder
- Haftalık/aylık özetler için veri tabanı oluşturur

Zamanlayıcı: Windows Görev Zamanlayıcı → Her gece 02:00
"""

import argparse
import datetime
import json
import os
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

LOGS_DIR = os.path.join(REPO, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

TZ = datetime.timezone(datetime.timedelta(hours=3))


def gunluk_rapor_yukle(gun_offset: int = 0) -> dict:
    """youtube_analytics.rapor() fonksiyonunu çağır"""
    try:
        # youtube_analytics modülünü import et
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload"))
        from youtube_analytics import rapor as yt_rapor
        return yt_rapor()
    except ImportError as e:
        return {"hata": f"youtube_analytics import hatası: {e}"}
    except Exception as e:
        return {"hata": f"Analytics çekme hatası: {e}"}


def rapor_kaydet(rapor: dict, gun_offset: int = 0) -> str:
    """Raporu logs/daily_views_YYYY-MM-DD.json olarak kaydet"""
    hedef_tarih = datetime.datetime.now(TZ) - datetime.timedelta(days=gun_offset)
    dosya_adi = f"daily_views_{hedef_tarih.strftime('%Y-%m-%d')}.json"
    dosya_yolu = os.path.join(LOGS_DIR, dosya_adi)

    # Metadata ekle
    rapor_kayit = {
        "tarih": (datetime.datetime.now(TZ) - datetime.timedelta(days=gun_offset)).strftime("%Y-%m-%d"),
        "olusturma_zamani": datetime.datetime.now(TZ).isoformat(),
        "veri": rapor
    }

    with open(dosya_yolu, "w", encoding="utf-8") as f:
        json.dump(rapor_kayit, f, ensure_ascii=False, indent=2)

    return dosya_yolu


def elle_islem_kaydet(rapor_ozet: str, dosya_yolu: str, kaynak: str = "cli") -> dict:
    """elle_islemler.jsonl'ye analitik_rapor işlemi olarak kaydet"""
    try:
        from elle_islem import ekle
        return ekle(
            platform="youtube",
            islem="analitik_rapor",
            ayrinti=f"Günlük analytics raporu: {rapor_ozet}",
            proje=None,
            zaman=None,
            kaynak=kaynak,
            kanit=os.path.basename(dosya_yolu),
            zaman_yaklasik=False,
        )
    except Exception as e:
        return {"hata": f"Elle işlem kaydetme hatası: {e}"}


def site_ziyaret_ozeti(gun_offset: int = 0) -> dict:
    """Site analitik verisinden ozet (Madde 28 — self-hosted, cookie-less).

    Veri: analytics_data/site/site_visits.jsonl (site/api/analytics.py yazar).
    """
    import datetime
    import config as _config

    veri_yolu = os.path.join(
        REPO, _config.ANALITIK_VERI_KLASORU, _config.ANALITIK_RAPOR_DOSYASI
    )
    if not os.path.isfile(veri_yolu):
        return {"hata": f"site ziyaret verisi yok: {veri_yolu}"}

    tz = datetime.timezone(datetime.timedelta(hours=3))
    hedef = (datetime.datetime.now(tz) - datetime.timedelta(days=gun_offset)).date().isoformat()
    kayitlar = []
    try:
        with open(veri_yolu, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    k = json.loads(line)
                except ValueError:
                    continue
                if k.get("ts", "").startswith(hedef):
                    kayitlar.append(k)
    except OSError as e:
        return {"hata": f"okunamadi: {e}"}

    yollar, cihazlar, referrer = {}, {}, {}
    for k in kayitlar:
        yollar[k.get("path", "/")] = yollar.get(k.get("path", "/"), 0) + 1
        c = k.get("device", "bilinmiyor")
        cihazlar[c] = cihazlar.get(c, 0) + 1
        r = k.get("ref", "-")
        referrer[r] = referrer.get(r, 0) + 1
    return {
        "tarih": hedef,
        "toplam_ziyaret": len(kayitlar),
        "sayfalar": dict(sorted(yollar.items(), key=lambda x: -x[1])[:10]),
        "cihazlar": cihazlar,
        "referrer": dict(sorted(referrer.items(), key=lambda x: -x[1])[:10]),
    }


def metrik_ozet_cikar(rapor: dict) -> str:
    """Rapor metriklerinden özet metin çıkar"""
    if not rapor or "hata" in rapor:
        return "Analytics verisi alınamadı"

    video_sayisi = rapor.get("video", 0)
    proje_sayisi = rapor.get("proje", 0)
    istek = rapor.get("istek", 0)

    if isinstance(rapor.get("detay"), list) and rapor["detay"]:
        # En çok izlenen videoyu bul
        en_cok = max(rapor["detay"], key=lambda x: x.get("goruntulenme", 0))
        en_cok_baslik = en_cok.get("baslik", "Bilinmiyor")[:50]
        en_cok_goruntulenme = en_cok.get("goruntulenme", 0)
        return f"{video_sayisi} video, {proje_sayisi} proje, en çok: {en_cok_baslik} ({en_cok_goruntulenme:,} gör.)"

    return f"{video_sayisi} video, {proje_sayisi} proje, {istek} API isteği"


def main():
    parser = argparse.ArgumentParser(
        description="Günlük YouTube Analytics Çekici — Famous Music Studio"
    )
    parser.add_argument("--gun", type=int, default=0,
                        help="Kaç gün öncesi (0=bugün, 1=dün, 7=hafta önce)")
    parser.add_argument("--json", action="store_true", help="JSON çıktı")
    parser.add_argument("--kaydet", action="store_true", default=True,
                        help="Raporu logs/ klasörüne kaydet (varsayılan: True)")
    parser.add_argument("--elle-islem", action="store_true", default=True,
                        help="elle_islemler.jsonl'ye kaydet (varsayılan: True)")
    args = parser.parse_args()

    # 1. Analytics çek
    rapor = gunluk_rapor_yukle(args.gun)
    # 1b. Site ziyaretleri (Madde 28 — self-hosted)
    site_ozet = site_ziyaret_ozeti(args.gun)

    if "hata" in rapor:
        sonuc = {"durum": "hata", "hata": rapor["hata"]}
    else:
        # 2. Özet çıkar
        ozet = metrik_ozet_cikar(rapor)
        if "hata" not in site_ozet:
            ozet += f" | site: {site_ozet.get('toplam_ziyaret', 0)} ziyaret"

        # 3. Dosyaya kaydet
        dosya_yolu = ""
        if args.kaydet:
            dosya_yolu = rapor_kaydet(rapor, args.gun)
            # site verisini de ayni dosyaya ekle
            try:
                with open(dosya_yolu, encoding="utf-8") as f:
                    mevcut = json.load(f)
                mevcut["site"] = site_ozet
                with open(dosya_yolu, "w", encoding="utf-8") as f:
                    json.dump(mevcut, f, ensure_ascii=False, indent=2)
            except (OSError, ValueError) as e:
                ozet += f" (site verisi yazilamadi: {e})"

        # 4. Elle işlem defterine kaydet
        elle_sonuc = {}
        if args.elle_islem:
            ozet_metin = metrik_ozet_cikar(rapor)
            if "hata" not in site_ozet:
                ozet_metin += f" | site: {site_ozet.get('toplam_ziyaret', 0)} ziyaret"
            elle_sonuc = elle_islem_kaydet(ozet_metin, dosya_yolu, kaynak="cli")

        sonuc = {
            "durum": "tamam",
            "gun_offset": args.gun,
            "ozet": ozet,
            "dosya": dosya_yolu,
            "elle_islem": elle_sonuc,
            "site": site_ozet,
            "metrikler": {
                "video_sayisi": rapor.get("video", 0),
                "proje_sayisi": rapor.get("proje", 0),
                "api_istek": rapor.get("istek", 0),
                "site_ziyaret": site_ozet.get("toplam_ziyaret", 0),
            }
        }

    # Çıktı
    if args.json:
        print(json.dumps(sonuc, ensure_ascii=True, indent=2))
    else:
        if "hata" in sonuc:
            print(f"❌ HATA: {sonuc['hata']}")
        else:
            print(f"[OK] Günlük analytics tamam: {sonuc['ozet']}")
            if sonuc.get("dosya"):
                print(f"  📁 Dosya: {sonuc['dosya']}")

    return 0 if "hata" not in sonuc else 1


if __name__ == "__main__":
    import json
    sys.exit(main())