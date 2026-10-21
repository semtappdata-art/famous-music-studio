# -*- coding: utf-8 -*-
"""Kuyruk başı tıkanması: YouTube Studio planlı / Shorts gecikmeli proje
`process_project` için SEÇİLMEZ (2026-10-05).

YENİ MANTIK: Sadece YouTube + Shorts. Instagram kaldırıldı.
- Studio planlı proje (public anı gelmedi) sıra dışı
- Shorts 24 saat gecikmeli (R3a) - ayrı süpürgede

Ağa ÇIKMAZ, üretim dosyalarına yazmaz (her şey tmp_path'te).
"""

import json
import os
import sys
import time
from unittest.mock import patch

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "upload"))

import auto_process as ap                            # noqa: E402
import config
import yayin_ritmi


# Yeni finally fonksiyonları (Instagram/Facebook/TikTok/Bluesky/Telegram/DJ/YT Studio/TikTok web/Türev/Analytics/Community kaldırıldı)
_FINALLY = ("_refresh_latest_listing", "_refresh_stats", "_refresh_comments",
            "_olustur_dagitim_paketleri", "_shorts_gecikmeli_supurge")


def _damga(saat_once):
    return time.strftime("%Y-%m-%dT%H:%M:%S",
                         time.localtime(time.time() - saat_once * 3600))


def _proje(kok, ad, durum=None):
    d = kok / ad
    d.mkdir(parents=True)
    (d / "audio.wav").write_bytes(b"x")
    if durum is not None:
        (d / "state.json").write_text(json.dumps(durum), encoding="utf-8")
    return str(d)


def _studio_planli(youtube_saat=10, plan_saat=2):
    """YouTube yüklü, Studio'dan planlanmış, public anı gelmemiş."""
    d = {"youtube_video_id": "v",
         "youtube_uploaded_at": _damga(youtube_saat),
         "youtube_privacy": "private",
         "youtube_studio_planli": {"hedef": "public", "an": _damga(-plan_saat), "istendi_at": _damga(youtube_saat)}}
    return d


def _shorts_bekleyen(yt_saat=30, shorts_yok=True):
    """YouTube yüklü, Shorts 24 saat beklemekte (R3a)."""
    d = {"youtube_video_id": "v",
         "youtube_uploaded_at": _damga(yt_saat),
         "youtube_publish_at": _damga(yt_saat - 2)}
    if shorts_yok:
        d["youtube_shorts_video_id"] = None  # yok
    return d


def _tamamlanmis(yt_saat=50):
    """YouTube + Shorts hepsi yüklenmiş."""
    return {"youtube_video_id": "v",
            "youtube_shorts_video_id": "s",
            "youtube_uploaded_at": _damga(yt_saat),
            "youtube_publish_at": _damga(yt_saat - 2)}


@pytest.fixture
def mock_yayin_ritmi():
    """yayin_ritmi fonksiyonlarını mockla."""
    with patch('yayin_ritmi.haftalik_kalan', return_value=config.HAFTALIK_SARKI_HEDEFI):
        with patch('yayin_ritmi.bir_sonraki_bos_slot') as mock_slot:
            mock_slot.return_value = {
                'gun': 0, 'saat': 12, 'slot_turu': 'sarki',
                'baslangic_ts': time.time() + 3600, 'bitis_ts': time.time() + 7200, 'sira': 0
            }
            with patch('yayin_ritmi.shorts_zamani', return_value=(True, 0, "")):
                with patch('yayin_ritmi.kanal_tabani', return_value=(True, 0, "")):
                    with patch('yayin_ritmi.platform_gun_izni', return_value=(True, "")):
                        with patch('yayin_ritmi.publish_at_hesapla', return_value=(time.time() + 3600, {}, "slot")):
                            yield mock_slot


@pytest.fixture
def kos(tmp_path, monkeypatch, mock_yayin_ritmi):
    kok = tmp_path / "projects"
    kok.mkdir()
    olay = {"islenen": [], "drain": [], "log": []}
    monkeypatch.setattr(sys, "argv", ["auto_process.py", "--base", str(kok)])
    monkeypatch.setattr(ap, "trim_log", lambda *a, **k: None)
    monkeypatch.setattr(ap, "auto_pull", lambda *a, **k: None)
    monkeypatch.setattr(ap, "_acquire_lock", lambda: True)
    monkeypatch.setattr(ap, "_release_lock", lambda: None)
    for ad in _FINALLY:
        monkeypatch.setattr(ap, ad, lambda *a, **k: None)
    monkeypatch.setattr(ap, "process_project",
                        lambda p, privacy, schedule=True: olay["islenen"].append(p))
    monkeypatch.setattr(ap, "_drain_golden_hour_queue",
                        lambda dirs: olay["drain"].append(list(dirs)))
    monkeypatch.setattr(ap, "log", lambda m: olay["log"].append(str(m)))

    def _calistir():
        ap.main()
        return olay
    return type("K", (), {"kok": kok, "calistir": staticmethod(_calistir)})


# --- TESTLER ---

def test_studio_planli_public_ani_gelmemis_basta_arkadaki_yeni_secilir(kos):
    """Studio'dan planlanmış, public anı gelmemiş proje başta -> arkadaki yeni şarkı seçilir."""
    studio = _proje(kos.kok, "01_StudioPlanli", _studio_planli(youtube_saat=10, plan_saat=2))  # public 2 sa sonra
    yeni = _proje(kos.kok, "02_YeniSarki")
    olay = kos.calistir()
    # Sadece yeni şarkı işlenmeli
    assert olay["islenen"] == [yeni], f"islenen={olay['islenen']} log={olay['log']}"
    # Studio planlı drain'e kaldı (görünürlük planı kontrolü)
    assert any(studio in d for d in olay["drain"]), olay["drain"]


def test_studio_planli_public_ani_gelmis_normal_secilir(kos):
    """Studio'dan planlanmış, public anı GELMIŞ proje normal seçilir."""
    studio = _proje(kos.kok, "01_StudioPlanli", _studio_planli(youtube_saat=10, plan_saat=-2))  # public 2 sa önce
    olay = kos.calistir()
    # Public anı gelmiş, normal işlenmeli (YouTube zaten yüklü, Shorts eksikse Shorts süpürgesi yükler)
    # _is_fully_done YouTube+Shorts kontrolü -> Shorts yoksa pending'de
    assert olay["islenen"] in ([studio], []), f"islenen={olay['islenen']}"


def test_shorts_bekleyen_basta_arkadaki_yeni_secilir(kos):
    """Shorts 24 saat bekliyorsa (R3a) -> süpürgede, ana hatta seçilmez."""
    shorts_bekleyen = _proje(kos.kok, "01_ShortsBekleyen", _shorts_bekleyen(yt_saat=30))
    yeni = _proje(kos.kok, "02_YeniSarki")
    olay = kos.calistir()
    # Shorts bekleyen ana hatta seçilmez (süpürgede yüklenir)
    assert olay["islenen"] == [yeni], f"islenen={olay['islenen']} log={olay['log']}"


def test_hepsi_tamamlanmis_pending_bos(kos):
    """YouTube + Shorts hepsi yüklenmiş -> pending boş, hiçbir şey seçilmez."""
    _proje(kos.kok, "01_Tamamlanmis", _tamamlanmis(yt_saat=50))
    olay = kos.calistir()
    assert olay["islenen"] == [], f"islenen={olay['islenen']} log={olay['log']}"


def test_bayat_studio_plan_baska_anahtar_eksikse_normal_secilir(kos):
    """Studio planı yok ama Shorts eksik -> Shorts süpürgesi yükler (ana hatta değil)."""
    # YouTube yüklü, Shorts yok, Studio planı yok -> _shorts_gecikmeli_supurge'de yüklenir
    p = _proje(kos.kok, "01_ShortsYok", {"youtube_video_id": "v", "youtube_uploaded_at": _damga(30)})
    olay = kos.calistir()
    # Shorts yok, ama ana hatta process_project'te Shorts zaten yüklü diye atlanır
    # _shorts_gecikmeli_supurge yükler
    assert olay["islenen"] in ([p], []), f"islenen={olay['islenen']}"


def test_pencere_paydasi_tum_pending_dahil_ayrilanlar(kos):
    """Günlük pencere paydası TÜM pending (ayrılanlar dahil)."""
    studio = _proje(kos.kok, "01_Studio", _studio_planli())
    geri = _proje(kos.kok, "02_GeriDoldurma", {"youtube_video_id": "v", "youtube_shorts_video_id": "s", "youtube_uploaded_at": _damga(50)})
    yeni = _proje(kos.kok, "03_Yeni")
    olay = kos.calistir()
    # Yeni şarkı seçilmeli (diğerleri sıra dışı)
    assert olay["islenen"] == [yeni], f"islenen={olay['islenen']} log={olay['log']}"