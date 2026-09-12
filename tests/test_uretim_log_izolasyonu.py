# -*- coding: utf-8 -*-
"""Testler ÜRETİM log'una/kilidine yazmasın — `tests/conftest.py`'nin bekçisi.

NEDEN (2026-09-11, canlı): `auto_process.log`'da 18:03:20 damgalı, gerçek
katalogda karşılığı OLMAYAN "Otomatik zamanlama: 7/9/2/1 proje bekliyor"
satırları bulundu — `test_auto_pace_count.py`'nin fikstürleri. `log()` modül
düzeyindeki sabit `LOG_PATH`'e yazıyor.

Asıl zarar kozmetik değil: `watch_projects.py`'nin nabız gözcüsü
(`_heartbeat_check`) makine arızasını haber verecek TEK mekanizma ve
`auto_process.log`'un MTIME'ına bakıyor. Testler dosyayı tazelediği sürece
"4 saattir güncellenmedi" koşulu hiç sağlanmaz — yani test paketini çalıştırmak
üretimin emniyet ağını kapatıyordu.

Bu dosya korumanın KENDİSİNİ test ediyor: conftest fixture'ı bir gün
kaldırılır/bozulursa burası kırmızı yanar, sessizce geri dönmez.
"""

import os
import time

import pytest

import auto_process as ap
import watch_projects as wp

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GERCEK_LOG = os.path.join(_REPO, "auto_process.log")
_GERCEK_KILIT = os.path.join(_REPO, ".auto_process.lock")


def _parmak_izi(yol):
    """(var_mi, boyut, mtime) — dosyaya dokunulup dokunulmadığının kanıtı."""
    if not os.path.exists(yol):
        return (False, None, None)
    d = os.stat(yol)
    return (True, d.st_size, d.st_mtime)


def test_log_yollari_repo_disina_cekilmis():
    """Fixture çalıştıysa hiçbir yol repo köküne bakmıyor olmalı."""
    for yol in (ap.LOG_PATH, ap.LOCK_PATH, wp.LOG_PATH,
                wp.AUTO_PROCESS_LOG_PATH, wp.HEARTBEAT_MARKER_PATH):
        assert not os.path.abspath(yol).startswith(_REPO + os.sep), yol


def test_log_cagrisi_gercek_auto_process_logunu_tazelemiyor():
    """ASIL REGRESYON: mtime değişirse nabız gözcüsü körelir."""
    once = _parmak_izi(_GERCEK_LOG)
    ap.log("test izolasyon kontrolu — bu satir uretim logunda GORUNMEMELI")
    assert _parmak_izi(_GERCEK_LOG) == once
    # Satır gerçekten bir yere yazıldı (log fonksiyonu sessizce kırılmadı).
    with open(ap.LOG_PATH, "r", encoding="utf-8") as f:
        assert "izolasyon kontrolu" in f.read()


def test_auto_pace_count_gercek_loga_yazmiyor(tmp_path):
    """Log'u gerçekten kirleten çağrı yolu buydu (fikstür sayıları oradan)."""
    import json
    d = tmp_path / "proje"
    d.mkdir()
    ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 3600))
    (d / "state.json").write_text(json.dumps({"youtube_uploaded_at": ts}))

    once = _parmak_izi(_GERCEK_LOG)
    ap._auto_pace_count(pending=[str(d)], ready=[str(d)])
    assert _parmak_izi(_GERCEK_LOG) == once


def test_gercek_kilide_dokunulmuyor():
    """`log()` içindeki nabız `os.utime(LOCK_PATH)` üretim kilidine gitmemeli."""
    once = _parmak_izi(_GERCEK_KILIT)
    ap._KILIT_BIZDE = True          # nabzı bilerek etkinleştir
    try:
        ap.log("kilit nabzi izolasyon kontrolu")
    finally:
        ap._KILIT_BIZDE = False
    assert _parmak_izi(_GERCEK_KILIT) == once
    assert not os.path.exists(_GERCEK_KILIT) or once[0]


@pytest.mark.parametrize("ad", ["LOG_PATH", "LOCK_PATH"])
def test_conftest_korunan_adlari_kapsiyor(ad):
    import conftest
    assert ad in conftest.KORUNAN_YOL_ADLARI
