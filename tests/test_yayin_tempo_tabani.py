# -*- coding: utf-8 -*-
"""52 saatlik YENİ YAYIN tabanı GERİ DOLDURMA damgasından sayılmamalı.

NEDEN AYRI BİR DOSYA: `_auto_pace_count`'un muafiyet mantığı bugüne kadar iki
kez düzeltildi (2026-09-11: `pending[0]` yerine batch'in tamamı) ve ikisinde de
gözden kaçan şey AYNI yerdi: muafiyet YALNIZCA "bu proje tabana takılsın mı"
sorusuna uygulanıyor, tabanın ÖLÇÜLDÜĞÜ saate uygulanmıyordu.

Arızanın şekli tam olarak deponun belgelenmiş sınıfı: hiçbir istisna atmıyor,
log satırı bile MEŞRU görünüyor ("kural: yeni yayın tabanı, gerekli ara ~52.0
saat"). Tek belirtisi yayın temposunun sessizce yarıya düşmesi — 2026-09-12'de
ölçüldü: son GERÇEK yeni yayın 8 Eylül 21:19 iken taban 12 Eylül 13:05'teki bir
Instagram geri doldurmasından sayılıyordu.

Ağa ÇIKMAZ, üretim dosyalarına yazmaz (her şey tmp_path'te).
"""

import json
import os
import sys
import time

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)

import auto_process as ap


SAAT = 3600.0


def _proje(tmp_path, ad, **damgalar):
    """Verilen damgalarla bir proje klasörü kurar."""
    d = tmp_path / ad
    d.mkdir()
    (d / "meta.json").write_text(
        json.dumps({"title": ad, "theme": "rock"}), encoding="utf-8")
    if damgalar:
        (d / "state.json").write_text(json.dumps(damgalar), encoding="utf-8")
    return str(d)


def _damga(saat_once):
    return time.strftime("%Y-%m-%dT%H:%M:%S",
                         time.localtime(time.time() - saat_once * SAAT))


# --- 1) ASIL ARIZA -----------------------------------------------------------

def test_geri_doldurma_yeni_yayin_tabanini_SIFIRLAMAZ(tmp_path):
    """Kırmızı/yeşil çekirdeği.

    Kurulum gerçek kuyruğun birebir eşi: YouTube'a 100 saat önce çıkmış bir
    şarkı (52 saatlik taban ÇOKTAN doldu) + 26 saat önce yapılmış bir Instagram
    GERİ DOLDURMASI. Düzeltmeden önce ikinci damga tabanı sıfırdan başlatıyordu
    ve fonksiyon 0 dönüyordu."""
    eski = _proje(tmp_path, "Eski Sarki",
                  youtube_video_id="VID1",
                  youtube_uploaded_at=_damga(100))
    # Geri doldurma: YouTube'da ZATEN var, sadece Instagram'ı yeni tamamlandı
    backfill = _proje(tmp_path, "Geri Doldurma",
                      youtube_video_id="VID2",
                      youtube_uploaded_at=_damga(100),
                      instagram_uploaded_at=_damga(26))
    yeni = _proje(tmp_path, "Yeni Sarki")   # state.json YOK -> yeni yayın

    assert ap._auto_pace_count([yeni], [eski, backfill, yeni], 1) == 1


def test_gercek_yeni_yayin_tabani_HALA_TUTUYOR(tmp_path):
    """Düzeltme tabanı kaldırmıyor — sadece doğru saatten ölçüyor.

    Bu test olmasaydı "geri doldurmayı yok say" yaması tabanı tamamen
    delebilirdi ve kimse fark etmezdi."""
    eski = _proje(tmp_path, "Eski Sarki",
                  youtube_video_id="VID1",
                  youtube_uploaded_at=_damga(10))   # 10 < 52
    yeni = _proje(tmp_path, "Yeni Sarki")
    assert ap._auto_pace_count([yeni], [eski, yeni], 1) == 0


def test_taban_sinirinda_52_saat(tmp_path):
    """Sınır davranışı çivilensin: 51,9 saat bekletir, 52,1 saat serbest."""
    yeni = _proje(tmp_path, "Yeni Sarki")
    for saat, beklenen in ((51.9, 0), (52.1, 1)):
        eski = _proje(tmp_path, "Eski %s" % saat,
                      youtube_video_id="V",
                      youtube_uploaded_at=_damga(saat))
        assert ap._auto_pace_count([yeni], [eski, yeni], 1) == beklenen, saat


# --- 2) GÜNLÜK PENCERE DEĞİŞMEDİ --------------------------------------------

def test_gunluk_pencere_TUM_damgalari_saymaya_devam_ediyor(tmp_path):
    """Pencere kuralının sorusu farklı: 'az önce bir şey paylaştık mı'.

    Geri doldurma DA bir paylaşımdır, o yüzden pencere onu SAYMALI. Yama bunu
    bozarsa aynı gün arka arkaya iki paylaşım yapılabilir hâle gelir."""
    # Taban dolmuş (100 saat), ama 1 saat önce bir geri doldurma yapılmış.
    # Tek bekleyen var -> pencere 24 saat; pencere onu tutmalı.
    eski = _proje(tmp_path, "Eski Sarki",
                  youtube_video_id="VID1", youtube_uploaded_at=_damga(100))
    backfill = _proje(tmp_path, "Geri Doldurma",
                      youtube_video_id="VID2", youtube_uploaded_at=_damga(100),
                      instagram_uploaded_at=_damga(1))
    yeni = _proje(tmp_path, "Yeni Sarki")
    assert ap._auto_pace_count([yeni], [eski, backfill, yeni], 1) == 0


def test_bekleyen_coksa_pencere_kisalir_ama_taban_kisalmaz(tmp_path):
    """24/N bölüşümü tabanı AŞAMAZ — kuralın varlık sebebi buydu."""
    eski = _proje(tmp_path, "Eski Sarki",
                  youtube_video_id="VID1", youtube_uploaded_at=_damga(3))
    # 12 bekleyen -> pencere 2 saat; 3 saat geçmiş, yani pencere DOLDU.
    # Ama taban (52 sa) dolmadı ve sırada yeni yayın var -> 0 dönmeli.
    bekleyenler = [_proje(tmp_path, "Yeni %d" % i) for i in range(12)]
    assert ap._auto_pace_count(bekleyenler, [eski] + bekleyenler, 1) == 0


# --- 3) MUAFİYET: sırada yeni yayın YOKSA taban hiç uygulanmaz ---------------

def test_sadece_geri_doldurma_bekliyorsa_taban_UYGULANMAZ(tmp_path):
    """CLAUDE.md'nin sözü: geri doldurma yarım kalmış işin tamamlanmasıdır."""
    eski = _proje(tmp_path, "Eski Sarki",
                  youtube_video_id="VID1", youtube_uploaded_at=_damga(3))
    backfill = _proje(tmp_path, "Geri Doldurma",
                      youtube_video_id="VID2", youtube_uploaded_at=_damga(3),
                      instagram_uploaded_at=_damga(25))
    # Pencere: 1 bekleyen -> 24 saat; son paylaşım 3 saat önce -> pencere TUTAR.
    assert ap._auto_pace_count([backfill], [eski, backfill], 1) == 0

    # Pencere de dolduğunda taban ARANMAMALI (geri doldurma muaf) — 30 saat
    # önceki bir yayın 52 saatlik tabanı doldurmaz ama bu proje muaf.
    eski2 = _proje(tmp_path, "Eski 2",
                   youtube_video_id="VID3", youtube_uploaded_at=_damga(30))
    backfill2 = _proje(tmp_path, "Geri Doldurma 2",
                       youtube_video_id="VID4", youtube_uploaded_at=_damga(30),
                       instagram_uploaded_at=_damga(25))
    assert ap._auto_pace_count([backfill2], [eski2, backfill2], 1) == 1


# --- 4) Hiç yükleme yoksa ----------------------------------------------------

def test_hic_yukleme_yoksa_hemen_baslar(tmp_path):
    yeni = _proje(tmp_path, "Yeni Sarki")
    assert ap._auto_pace_count([yeni], [yeni], 1) == 1


def test_youtube_damgasi_hic_yoksa_taban_ENGEL_OLMAZ(tmp_path):
    """Kanalda hiç YouTube yüklemesi yoksa taban ölçülemez — bloke ETMEMELİ.

    Aksi hâlde ilk şarkı sonsuza kadar beklerdi."""
    tuhaf = _proje(tmp_path, "Tuhaf",
                   youtube_video_id="V", instagram_uploaded_at=_damga(30))
    yeni = _proje(tmp_path, "Yeni Sarki")
    assert ap._auto_pace_count([yeni], [tuhaf, yeni], 1) == 1


# --- 5) Sabitin kendisi ------------------------------------------------------

def test_yeni_yayin_anahtari_genis_listenin_ALT_KUMESI():
    """İki sabit ayrışırsa (ör. anahtar yeniden adlandırılırsa) burada kırılsın:
    dar liste geniş listenin içinde OLMAK ZORUNDA, yoksa taban hiç ölçülmez."""
    assert set(ap.YENI_YAYIN_TIMESTAMP_KEYS) <= set(ap.UPLOAD_TIMESTAMP_KEYS)
    assert ap.YENI_YAYIN_TIMESTAMP_KEYS, "dar liste bos birakilirsa taban olur"
    # Geri doldurmanın yazdığı damga dar listede OLMAMALI — arızanın kendisi.
    assert "instagram_uploaded_at" not in ap.YENI_YAYIN_TIMESTAMP_KEYS
