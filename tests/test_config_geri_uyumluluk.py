"""GERI UYUMLULUK — config.py render cekirdegine indirgendi (2026-10-09).

Garanti: `import config` tek basina tum alan sabitlerini verir; dolgu mevcut
degerleri EZMEZ. Bozulursa saatlik kosuda Turev/TikTok/YouTube dallari HATA verir.
"""

import config


def test_turev_sabitleri_var():
    assert config.TUREV_PLAN_T0_SAAT == 72
    assert config.TUREV_GUNLUK_TAVAN == 1
    assert config.TUREV_KOSU_BASINA_PLAN == 3


def test_yeni_tavan_sabiti_var():
    assert config.GUNLUK_MAKS_YENI_SARKI == 2


def test_youtube_tiktok_sabitleri_var():
    assert isinstance(config.YOUTUBE_BASLIK_KALIPLARI, list | dict | str | tuple)
    assert config.TIKTOK_KIT_GUNLUK_TAVAN >= 1


def test_dolgu_ezme_yapmaz():
    assert config.GOLDEN_HOURS == [(12, 14), (18, 22)]
    assert "derleme" not in config.TEMA_KESIF_ETIKETLERI


def test_turev_saatlik_supurge_acilir():
    import turev_takvimi
    kayit = []
    sonuc = turev_takvimi.sirasi(log=kayit.append, klasorler=[])
    assert sonuc["hata"] == 0


def test_tiktok_yayin_api_butun():
    import tiktok_upload
    assert callable(tiktok_upload._load_meta)
    assert callable(tiktok_upload.yayin_kodu)
    assert callable(tiktok_upload.upload_video)
    assert callable(tiktok_upload.notify_pending_publish)
    assert tiktok_upload.yayin_kodu(None) is None
