"""Yayın T-minus takvimi — profesyonel label disiplini (PROFESYONEL_LABEL_YOUTUBE_ANALIZI.md §1).

Tek şarkı = tek upload DEĞİL, 8 haftalık operasyondur: DJ promo cascade (T-5),
distribütör + Spotify pitch (T-4/5), geniş liste (T-3/4), içerik yığını (T-2),
pre-save (T-1), yayın günü, büyüme (T+1/3), derivative penceresi (T+8hf).

Uydu paketi kuralı: her yayın = 1 uzun + 3 Shorts + 2 topluluk postu + playlist.
Bu modül kütüphanedir (ağ yok, state yazmaz); proje takvimi `takvim.json`
olarak proje klasörüne yazılır (`olustur`), kapısı `validate_project`'tedir
(meta'da `yayin_tarihi` varsa `takvim.json` yokluğu UYARI verir).
"""

import json
import os
from datetime import datetime, timedelta, timezone

TR_TZ = timezone(timedelta(hours=3))

# (hafta_ofseti, kod, başlık, işler[]) — negatif = yayın öncesi.
FAZLAR = [
    (-5, "dj_promo_dar", "Dar DJ listesi (10-20 isim)", [
        "promo havuzundan türdaş 10-20 DJ seç",
        "özel link + kısa not gönder (PROMO_DM_SABLONU)",
        "destekleyen isimleri kaydet (ikinci dalga cümlesi için)",
    ]),
    (-4, "dagitim_pitch", "Distribütör + Spotify pitch", [
        "distribütöre yükle (ISRC/UPC doğrula)",
        "Spotify for Artists pitch: tür + hikaye + şehir + plan (4 hafta kala)",
        "kanal allowlist talebi distribütöre (Content ID claim önlemi)",
    ]),
    (-3, "dj_promo_genis", "Geniş DJ listesi (onay damgalı)", [
        '"Supported by [X]" cümlesiyle ikinci dalga gönder',
        "Beatport penceresiyle aynı haftaya kilitle (cross-feed)",
    ]),
    (-2, "icerik_yigini", "Uydu paketi üretimi (1+3+2)", [
        "3 Shorts kırp (hook / geçiş anı / outro)",
        "2 topluluk postu taslağı (anket şablonları)",
        "kapak A/B 2. varyantı üret (cover_varyant_B)",
    ]),
    (-1, "presave", "Pre-save + son hatırlatma", [
        "SmartLink/pre-save akışı açık mı?",
        "DJ listesine son özet + Beatport butonları",
        "topluluk ısınma postu (yayın öncesi 24-48sa)",
    ]),
    (0, "yayin", "Yayın günü (golden-hour)", [
        "uzun format + Shorts (tam sürüm linkli)",
        "playlist'e ekle (niyet listesi)",
        "ilk yorumu sabitle (soru + timestamp)",
    ]),
    (2, "buyume", "Büyüme (T+1/3 hafta)", [
        "klip + DJ cascade devam",
        "Discover Weekly / Release Radar sinyallerini izle",
        "Test & Compare sonucu işle",
    ]),
    (8, "derivative", "Derivative penceresi (T+8 hafta)", [
        "tutmuş parça mı? remix/edit paketi ya da collab kararı",
        "ikinci basın + ikinci editoryal kapı",
    ]),
]


def faz_tarihi(yayin_tarihi: datetime, hafta_ofset: int) -> datetime:
    """Fazın takvim tarihi (yayın tarihinden hafta ofseti)."""
    if yayin_tarihi.tzinfo is None:
        yayin_tarihi = yayin_tarihi.replace(tzinfo=TR_TZ)
    return yayin_tarihi + timedelta(weeks=hafta_ofset)


def kontrol_listesi(yayin_tarihi: datetime) -> list:
    """Tüm fazlar: [(kod, başlık, tarih_iso, işler[])] — yayın operatörü bunu tikler."""
    return [
        (kod, baslik, faz_tarihi(yayin_tarihi, ofset).isoformat(), isler)
        for ofset, kod, baslik, isler in FAZLAR
    ]


def olustur(project_dir: str, yayin_tarihi_iso: str) -> str:
    """Projeye takvim.json yazar, yolunu döner (varsa üzerine yazar)."""
    try:
        yayin_tarihi = datetime.fromisoformat(yayin_tarihi_iso)
    except ValueError:
        raise ValueError(f"yayin_tarihi ISO formatında olmalı: {yayin_tarihi_iso!r}")
    veri = {
        "yayin_tarihi": yayin_tarihi_iso,
        "fazlar": [
            {"kod": kod, "baslik": baslik, "tarih": tarih, "isler": isler, "tamam": False}
            for kod, baslik, tarih, isler in kontrol_listesi(yayin_tarihi)
        ],
    }
    yol = os.path.join(project_dir, "takvim.json")
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
    return yol


def promo_dm_merhaba(dj_adi: str, parca_basligi: str, ozel_link: str) -> str:
    """Promo havuzu ilk-dalga DM metni (config.PROMO_DM_SABLONU'ndan)."""
    import config
    sablon = getattr(config, "PROMO_DM_SABLONU", "Merhaba {dj} — yeni parçamız: {parca} {link}")
    return sablon.format(dj=dj_adi, parca=parca_basligi, link=ozel_link)
