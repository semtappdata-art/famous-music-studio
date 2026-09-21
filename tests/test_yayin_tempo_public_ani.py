# -*- coding: utf-8 -*-
"""52 saatlik YENİ YAYIN tabanı, videonun PUBLIC OLDUĞU anı da saymalı.

NEDEN (2026-09-12): `Bu Gece Kazandık` 8 Eylül'de yüklendi ama YouTube'da
unlisted kaldı; bir sonraki golden-hour'da (13 Eylül 12:00) public olacak
şekilde zamanlandı. Taban yalnız `youtube_uploaded_at`'ten ölçülseydi sayaç
8 Eylül'ü görürdü — yani `Sabah Senin` aynı gün, public olan şarkının hemen
arkasından çıkabilirdi. Kanalın izleyiciye görünen yayın deseni YÜKLEME anı
değil, PUBLIC olma anıdır.

Kural: yeni yayın anı = max(youtube_uploaded_at, youtube_publish_at).
Public anı GELECEKTEYSE taban oradan ölçülür — sıradaki yeni şarkı o andan
itibaren 52 saat bekler. Günlük pencere kuralı DEĞİŞMEZ (tüm yükleme
damgaları, publish_at dahil değil).

Ağa ÇIKMAZ, üretim dosyalarına yazmaz (her şey tmp_path'te).
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)

import auto_process as ap


def _proje(tmp_path, ad, **alanlar):
    d = tmp_path / ad
    d.mkdir()
    (d / "meta.json").write_text(
        json.dumps({"title": ad, "theme": "pop"}), encoding="utf-8")
    if alanlar:
        (d / "state.json").write_text(json.dumps(alanlar), encoding="utf-8")
    return str(d)


def _yerel_damga(saat_once):
    """youtube_uploaded_at biçimi: yerel saat, saniye hassasiyeti."""
    return time.strftime("%Y-%m-%dT%H:%M:%S",
                         time.localtime(time.time() - saat_once * 3600))


def _utc_z(saat_sonra):
    """youtube_publish_at biçimi (youtube_upload._compute_publish_at): UTC '...Z'."""
    an = datetime.now(timezone.utc) + timedelta(hours=saat_sonra)
    return an.replace(microsecond=0).isoformat().replace("+00:00", "Z")


# --- 1) ASIL SENARYO ----------------------------------------------------------

def test_gelecege_zamanlanmis_public_ani_siradaki_yeni_yayini_BEKLETIR(tmp_path):
    """Kırmızı/yeşil çekirdeği — Bu Gece Kazandık'ın birebir eşi.

    Yükleme 100 saat önce (taban yüklemeden ölçülse ÇOKTAN dolmuş), ama video
    14 saat SONRA public olacak. Sıradaki yeni şarkı çıkmamalı."""
    zamanli = _proje(tmp_path, "Zamanli",
                     youtube_video_id="VID1",
                     youtube_uploaded_at=_yerel_damga(100),
                     youtube_publish_at=_utc_z(+14))
    yeni = _proje(tmp_path, "Yeni Sarki")
    assert ap._auto_pace_count([yeni], [zamanli, yeni], 1) == 0


def test_gelecekteki_public_anindan_52_saat_sonrasina_kadar_bekletir(tmp_path):
    """Sayaç public anından BAŞLAR: o an + 51,9 sa hâlâ bekletir.

    Geleceği taklit etmek yerine eşdeğer geçmiş kurulum: public anı 51,9 saat
    önce -> tutar; 52,1 saat önce -> serbest (yükleme her ikisinde de 100 sa)."""
    yeni = _proje(tmp_path, "Yeni Sarki")
    for saat, beklenen in ((51.9, 0), (52.1, 1)):
        eski = _proje(tmp_path, "Eski %s" % saat,
                      youtube_video_id="V",
                      youtube_uploaded_at=_yerel_damga(100),
                      youtube_publish_at=_utc_z(-saat))
        assert ap._auto_pace_count([yeni], [eski, yeni], 1) == beklenen, saat


def test_gecmisteki_public_ani_da_SAYILIR(tmp_path):
    """Yükleme 100 sa önce, public anı 10 sa önce -> taban public anından."""
    eski = _proje(tmp_path, "Eski",
                  youtube_video_id="VID1",
                  youtube_uploaded_at=_yerel_damga(100),
                  youtube_publish_at=_utc_z(-10))
    yeni = _proje(tmp_path, "Yeni Sarki")
    assert ap._auto_pace_count([yeni], [eski, yeni], 1) == 0


# --- 2) GEÇ OLAN KAZANIR, ERKEN OLAN TABANI KISALTAMAZ -------------------------

def test_publish_at_yuklemeden_ONCEYSE_yukleme_ani_gecerli(tmp_path):
    """Tuhaf kayıt: publish_at yüklemeden eski. max() yüklemeyi seçmeli —
    publish_at tabanı KISALTAMAZ."""
    eski = _proje(tmp_path, "Eski",
                  youtube_video_id="VID1",
                  youtube_uploaded_at=_yerel_damga(10),
                  youtube_publish_at=_utc_z(-200))
    yeni = _proje(tmp_path, "Yeni Sarki")
    assert ap._auto_pace_count([yeni], [eski, yeni], 1) == 0


def test_okunamayan_publish_at_yok_sayilir_yukleme_ani_kalir(tmp_path):
    eski = _proje(tmp_path, "Eski",
                  youtube_video_id="VID1",
                  youtube_uploaded_at=_yerel_damga(100),
                  youtube_publish_at="yarin aksam")
    yeni = _proje(tmp_path, "Yeni Sarki")
    assert ap._auto_pace_count([yeni], [eski, yeni], 1) == 1


def test_zamanlamasiz_yukleme_davranisi_DEGISMEDI(tmp_path):
    """publish_at None (bugünkü kataloğun çoğu) -> eski davranış birebir."""
    for saat, beklenen in ((51.9, 0), (52.1, 1)):
        d = tmp_path / ("k%s" % saat)
        d.mkdir()
        eski = _proje(d, "Eski", youtube_video_id="V",
                      youtube_uploaded_at=_yerel_damga(saat),
                      youtube_publish_at=None)
        yeni = _proje(d, "Yeni Sarki")
        assert ap._auto_pace_count([yeni], [eski, yeni], 1) == beklenen, saat


# --- 3) DEĞİŞMEMESİ GEREKENLER ------------------------------------------------

def test_sadece_geri_doldurma_bekliyorsa_gelecekteki_public_ani_ENGEL_OLMAZ(tmp_path):
    """Muafiyet korunuyor: sırada yeni yayın yoksa taban hiç aranmaz.

    Bu Gece Kazandık'ın KENDİ Instagram geri doldurması, kendi public anına
    takılıp bekletilmemeli."""
    zamanli = _proje(tmp_path, "Zamanli",
                     youtube_video_id="VID1",
                     youtube_uploaded_at=_yerel_damga(100),
                     youtube_publish_at=_utc_z(+14))
    assert ap._auto_pace_count([zamanli], [zamanli], 1) == 1


def test_gunluk_pencere_publish_at_i_SAYMAZ():
    """Pencere kuralı 'en son ne zaman bir şey PAYLAŞTIK' sorusu; damga
    listesi değişmedi."""
    assert "youtube_publish_at" not in ap.UPLOAD_TIMESTAMP_KEYS
    assert ap.UPLOAD_TIMESTAMP_KEYS == (
        "youtube_uploaded_at", "youtube_shorts_uploaded_at",
        "tiktok_uploaded_at", "instagram_uploaded_at",
    )
